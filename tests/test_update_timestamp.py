"""Exercise timestamp lifecycle without requiring a Home Assistant installation.

Compile the production coordinator and sensor getter with minimal framework
stand-ins. These tests cover integration logic, not Home Assistant scheduling.
"""
import __future__
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock


ROOT = Path(__file__).resolve().parents[1] / "custom_components/ckw_dynamic_pricing"


class UpdateFailed(Exception):
    """Stand-in for the coordinator update exception."""


class CoordinatorBase:
    def __init__(self, *args, **kwargs):
        self.data = None

    def async_set_updated_data(self, data):
        self.data = data


def load_class(filename, name, namespace):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
    module = ast.Module(body=[node], type_ignores=[])
    exec(compile(module, filename, "exec", flags=__future__.annotations.compiler_flag), namespace)
    return namespace[name]


class TimestampTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 13, 8, tzinfo=timezone.utc)
        self.clock = SimpleNamespace(now=lambda: self.now, utcnow=lambda: self.now)
        session = MagicMock()
        coordinator_class = load_class("__init__.py", "CKWPricingCoordinator", {
            "DataUpdateCoordinator": CoordinatorBase, "_LOGGER": None,
            "DOMAIN": "ckw_dynamic_pricing", "SCAN_INTERVAL": None,
            "dt_util": self.clock, "timedelta": timedelta,
            "aiohttp": SimpleNamespace(ClientSession=session, ClientError=OSError),
            "UpdateFailed": UpdateFailed,
        })
        self.coordinator = coordinator_class(None, SimpleNamespace(data={}, options={}))
        self.coordinator._fetch_day = AsyncMock(return_value=[{"price": 1}])
        self.coordinator._process_data = MagicMock(return_value={"prices_tomorrow": [1]})

    async def test_initial_value_and_sensor_read(self):
        self.assertIsNone(self.coordinator.last_update_success_time)
        sensor_class = load_class("sensor.py", "CKWPriceSensor", {
            "CoordinatorEntity": type("CoordinatorEntity", (), {}),
            "SensorEntity": type("SensorEntity", (), {}),
        })
        sensor = object.__new__(sensor_class)
        sensor.coordinator = self.coordinator
        sensor.entity_description = SimpleNamespace(key="last_api_update")
        self.assertIsNone(sensor.native_value)
        self.coordinator.data = await self.coordinator._async_update_data()
        self.assertEqual(sensor.native_value, self.now)
        self.assertIsNotNone(sensor.native_value.utcoffset())

    async def test_success_advances_timestamp_and_midnight_preserves_it(self):
        self.coordinator.data = await self.coordinator._async_update_data()
        previous = self.now
        self.now += timedelta(hours=6)
        await self.coordinator._async_midnight_refresh(self.now)
        self.assertEqual(self.coordinator.last_update_success_time, previous)
        await self.coordinator._async_update_data()
        self.assertEqual(self.coordinator.last_update_success_time, self.now)

    async def test_failures_preserve_timestamp(self):
        for previous in (None, self.now):
            for failure in ("empty", "processing", "network", "timeout"):
                with self.subTest(previous=previous, failure=failure):
                    self.coordinator.last_update_success_time = previous
                    self.coordinator._fetch_day = AsyncMock(return_value=[1])
                    self.coordinator._process_data = MagicMock(return_value={})
                    if failure == "empty":
                        self.coordinator._fetch_day.return_value = []
                    elif failure == "processing":
                        self.coordinator._process_data.side_effect = UpdateFailed("invalid")
                    else:
                        self.coordinator._fetch_day.side_effect = (
                            OSError("offline") if failure == "network" else TimeoutError()
                        )
                    with self.assertRaises((UpdateFailed, TimeoutError)):
                        await self.coordinator._async_update_data()
                    self.assertEqual(self.coordinator.last_update_success_time, previous)


if __name__ == "__main__":
    unittest.main()
