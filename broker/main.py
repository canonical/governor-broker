#! /usr/bin/env python3

import argparse
import yaml

from juju.controller import Controller
from broker.unit_watcher import UnitWatcher
from juju import loop


async def connect_juju_components(endpoint, username, password, cacert, model_name):
    """ Connect to controller and model """
    ctrl = Controller()
    await ctrl.connect(
        endpoint=endpoint, username=username, password=password, cacert=cacert
    )

    model = await ctrl.get_model(model_name)

    return ctrl, model


def sync_unit_watcher(model, governor_charm, storage_path):
    """ Instanciate UnitWatcher and start watcher """
    uw = UnitWatcher(model, governor_charm, storage_path)
    loop.run(uw.start_watcher())


def govern_model(
    endpoint,
    username,
    password,
    cacert,
    model_name,
    governor_charm,
    storage_path,
):
    """ Connect to juju components and call watchers. """
    _, model = loop.run(
        connect_juju_components(endpoint, username, password, cacert, model_name)
    )

    sync_unit_watcher(model, governor_charm, storage_path)


def main():
    """ Read credentials and call Govern Model. """
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path")

    args = parser.parse_args()

    storage_path = args.path
    with open("{}/creds.yaml".format(storage_path), "r") as stream:
        creds = yaml.safe_load(stream)

    govern_model(
        creds["endpoint"],
        creds["username"],
        creds["password"],
        creds["cacert"],
        creds["model"],
        creds["governor-charm"],
        storage_path,
    )


if __name__ == "__main__":
    main()
