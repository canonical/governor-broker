import logging
import pprint
import asyncio
import sqlite3

from governor.storage import GovernorStorage
from juju.client import client

class UnitWatcher:

    def __init__(self, model, governor_charm, storage_path):
        self.model = model
        self.storage_path = storage_path
        self.governor = governor_charm
        self.active_units = self.get_active_units()
        self.units = self.model.units
        self.event_list = []

        self.status_changes = {
            "active": self.status_active,
            "blocked": self.status_blocked,
            "error": self.status_error,
        }

    def get_active_units(self):
        active_units = set()

        for app_name, app in self.model.applications.items():
            if app_name == self.governor:
                continue
            for unit in app.units:
                if unit.workload_status == "active":
                    active_units.add(unit.entity_id)

        return active_units

    def status_active(self, delta):
        if delta.data["name"] not in self.active_units:
            logging.warning("New active unit {}".format(delta.data["name"]))
            self.active_units.add(delta.data["name"])

    def status_blocked(self, delta):
        logging.warning("Unit blocked {}".format(delta.data["name"]))
        was_active = delta.data["name"] in self.active_units
        if was_active:
            self.active_units.remove(delta.data["name"])

        event_data = {
            "event_name": "unit_blocked",
            "event_data": {
                "unit_name": delta.data["name"],
                "was_active": was_active,
                "message": delta.deltas[2]["workload-status"]["message"]
            },
        }

        self.event_list.append(event_data)

    def status_error(self, delta):
        logging.warning("Unit error {}".format(delta.data["name"]))
        was_active = delta.data["name"] in self.active_units
        if was_active:
            self.active_units.remove(delta.data["name"])

        event_data = {
            "event_name": "unit_error",
            "event_data": {
                "unit_name": delta.data["name"],
                "was_active": was_active,
                "message": delta.deltas[2]["workload-status"]["message"]
            },
        }

        self.event_list.append(event_data)

    async def start_watcher(self):
        """ Watch all changes in units """
        allwatcher = client.AllWatcherFacade.from_connection(self.model.connection())

        change = await allwatcher.Next()
    
        while True:
            units = self.model.units
            await asyncio.sleep(2)
            change = await allwatcher.Next()
            for delta in change.deltas:
                delta_entity = delta.entity
    
                if delta_entity == "unit":
                    if self.governor in delta.data["name"]:
                        continue

                    if delta.type == "change": 
                        if delta.data["name"] not in units:
                            logging.warning("New unit was added")
    
                            event_data = {
                                "event_name": "unit_added",
                                "event_data": {"unit_name": delta.data["name"]},
                            }
    
                            self.event_list.append(event_data)

                        workload_status = delta.deltas[2]["workload-status"]["current"]
                        if workload_status in self.status_changes:
                            status_change_function = self.status_changes[workload_status]
                            status_change_function(delta)

                    if delta.type == "remove":
                        logging.warning("Unit was removed")
                        event_data = {
                            "event_name": "unit_removed",
                            "event_data": {"unit_name": delta.data["name"]},
                        }
                        self.event_list.append(event_data)
                        logging.warning("Action executed")
    
                if self.event_list:
                    await self.events_to_storage()

    async def events_to_storage(self):
        """
        Store events to Governor Storage if unlocked and wake up governor charm with action.
        """
        try:
            gs = GovernorStorage("{}/gs_db".format(self.storage_path))
    
            for i in range(len(self.event_list)):
                gs.write_event_data(self.event_list[0])
                self.event_list.pop(0)
    
            await self.execute_action("governor-event")
    
            gs.close()
        except sqlite3.OperationalError:
            logging.warning("Waiting for DB to unlock")

    async def execute_action(self, action_name, **kwargs):
        """ Execute action on leader unit of application. """
        if not self.model.applications and self.governor not in self.model.applications:
            return
    
        application = self.model.applications[self.governor]

        for u in application.units:
            if await u.is_leader_from_status():
                unit = u

        await unit.run_action(action_name, **kwargs)
