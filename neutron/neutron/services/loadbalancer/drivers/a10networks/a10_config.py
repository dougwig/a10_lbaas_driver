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

ini = '/etc/neutron/services/loadbalancer/a10networks/a10networks_config.ini'


class A10Config(object):

    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        self.config.read(ini)
        self._get_devices()

    def _get_devices(self):
        self.devices = {}

        for key, j in self.config.items('a10networks'):
            h = json.loads(j.replace("\n", "", len(j)))

            status = False
            if 'status' in h:
                s = str(h['status'])
                if s[0].upper() == 'T' or s[0] == '1':
                    status = True
            else:
                status = True

            if status:
                self.devices[key] = h
