from unittest.mock import patch, PropertyMock
from unittest import TestCase
from juju.model import Model
from broker.unit_watcher import UnitWatcher


class FakeApplication:
    def __init__(self, entity_id, active):
        self.units = [FakeUnit(entity_id, active)]


class FakeUnit:
    def __init__(self, entity_id, active):
        self.entity_id = entity_id
        if active:
            self.workload_status = "active"
        else:
            self.workload_status = "not_active"


class FakeDelta:
    def __init__(self, data):
        self.data = data
        self.deltas = [{}, {}, {"workload-status": {"message": "message"}}]


class UnitWatcherTestCase(TestCase):
    @patch("broker.unit_watcher.UnitWatcher.get_active_units")
    def setUp(self, active_units_mock):
        self.unit_watcher = UnitWatcher(Model(), "governor-charm", "storage-path")

    def test_active_units(self):
        with patch.object(Model, "applications", new_callable=PropertyMock) as app_mock:
            app_mock.return_value = {
                    "governor-charm": FakeApplication("governor-charm", True),
                    "other-active-charm": FakeApplication("other-active-charm", True),
                    "other-not-active-charm": FakeApplication(
                        "other-not-active-charm", False),
            }
            active_units = self.unit_watcher.get_active_units()
            assert active_units == {"other-active-charm"}

    def test_no_active_units(self):
        with patch.object(Model, "applications", new_callable=PropertyMock) as app_mock:
            app_mock.return_value = {}
            active_units = self.unit_watcher.get_active_units()
            assert active_units == set()

    def test_status_active(self):
        delta = FakeDelta(data={"name": "new-active-unit"})
        self.unit_watcher.active_units = set()
        self.unit_watcher.status_active(delta)
        assert self.unit_watcher.active_units == {"new-active-unit"}
        self.unit_watcher.status_active(delta)
        assert self.unit_watcher.active_units == {"new-active-unit"}
        self.unit_watcher.status_active(delta)

    def test_status_blocked_was_active(self):
        delta = FakeDelta(data={"name": "previously-active-unit"})
        self.unit_watcher.active_units = {"previously-active-unit"}
        self.unit_watcher.event_list = []
        self.unit_watcher.status_blocked(delta)
        assert self.unit_watcher.active_units == set()
        assert self.unit_watcher.event_list == [{
            "event_name": "unit_blocked",
            "event_data": {
                "unit_name": "previously-active-unit",
                "was_active": True,
                "message": "message",
            }
        }]

    def test_status_blocked_was_not_active(self):
        delta = FakeDelta(data={"name": "not-active-unit"})
        self.unit_watcher.active_units = set()
        self.unit_watcher.event_list = []
        self.unit_watcher.status_blocked(delta)
        assert self.unit_watcher.active_units == set()
        assert self.unit_watcher.event_list == [{
            "event_name": "unit_blocked",
            "event_data": {
                "unit_name": "not-active-unit",
                "was_active": False,
                "message": "message",
            }
        }]

    def test_status_error_was_active(self):
        delta = FakeDelta(data={"name": "previously-active-unit"})
        self.unit_watcher.active_units = {"previously-active-unit"}
        self.unit_watcher.event_list = []
        self.unit_watcher.status_error(delta)
        assert self.unit_watcher.active_units == set()
        assert self.unit_watcher.event_list == [{
            "event_name": "unit_error",
            "event_data": {
                "unit_name": "previously-active-unit",
                "was_active": True,
                "message": "message",
            }
        }]

    def test_status_error_was_not_active(self):
        delta = FakeDelta(data={"name": "not-active-unit"})
        self.unit_watcher.active_units = set()
        self.unit_watcher.event_list = []
        self.unit_watcher.status_error(delta)
        assert self.unit_watcher.active_units == set()
        assert self.unit_watcher.event_list == [{
            "event_name": "unit_error",
            "event_data": {
                "unit_name": "not-active-unit",
                "was_active": False,
                "message": "message",
            }
        }]
