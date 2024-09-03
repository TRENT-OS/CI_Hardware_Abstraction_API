#
# Copyright (C) 2024, HENSOLDT Cyber GmbH
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# For commercial licensing, contact: info.cyber@hensoldt.net
#


import json
import os

from .uart_proxy import Device

config = None


class Config:
    def __init__(self, config_file):
        if not os.path.exists(config_file):
            print(f"ERROR: Config file at {config_file} not found")
            exit(-1)

        with open(config_file, "r") as file:
            self.config = json.load(file)
            self.ip = self.config["ip"]
            self.port = self.config["port"]

    async def get_devices(self):
        return {dev["name"]: Device(dev, self.config) for dev in self.config["devices"]}

    # Returns a safe copy of the config without credentials
    def get_clean_config(self):
        return {
            **self.config,
            "poe_switch": {**self.config["poe_switch"], "password": "********"},
        }


def init_config(config_file="/etc/uart_proxy.json"):
    global config
    config = Config(config_file)


def get_config():
    if config is None:
        init_config()
    return config
