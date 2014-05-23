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

import logging
import os
import sys


LOG = logging.getLogger(__name__)


class A10Config(object):

    def __init__(self):
        config_dir = "/etc/neutron/services/loadbalancer/a10networks"
        config_path = os.path.join(config_dir, "config.py")
        real_sys_path = sys.path
        sys.path = [config_dir]
        try:
            import config
        except ImportError, e:
            LOG.error("A10Driver: missing config file at: %s", config_path)
            raise e
        finally:
            sys.path = real_sys_path
        self.config = config
        self.devices = self.config.devices
        LOG.debug("A10Config, devices=%s", self.devices)
