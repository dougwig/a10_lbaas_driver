# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013,  Doug Wiegley,  A10 Networks.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import ConfigParser
import json
import logging
import os
import sys

from neutron.services.loadbalancer.drivers.a10networks import a10_exceptions

config_dir = "/etc/neutron/services/loadbalancer/a10networks"


LOG = logging.getLogger(__name__)


class A10Config(object):

    def __init__(self):
        config_path = os.path.join(config_dir, "config.py")
        real_sys_path = sys.path
        sys.path = [config_dir]
        try_ini = False
        try:
            import config
            self.config = config
            self.devices = self.config.devices
        except ImportError:
            try_ini = True
        finally:
            sys.path = real_sys_path
        if try_ini:
            try:
                self._parse_old_style_ini()
            except Exception:
                LOG.error("A10Driver: missing config file at: %s", config_path)
                raise a10_exceptions.A10ThunderException()
        LOG.debug("A10Config, devices=%s", self.devices)

    def _parse_old_style_ini(self):
        ini_path = os.path.join(config_dir, 'a10networks_config.ini')
        self.config = ConfigParser.ConfigParser()
        self.config.read(ini_path)
        self._get_devices()

    def _get_devices(self):
        self.devices = {}

        for key, j in self.config.items('a10networks'):
            h = json.loads(j.replace("\n", "", len(key)))

            if 'True' in h['autosnat']:
                h['autosnat'] = True
            if 'True' in h['use_float']:
                h['use_float'] = True

            status = False
            if 'status' in h:
                s = str(h['status'])
                if s[0].upper() == 'T' or s[0] == '1':
                    status = True
            else:
                status = True

            if status:
                self.devices[key] = h
