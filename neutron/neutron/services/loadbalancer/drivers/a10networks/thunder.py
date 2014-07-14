# Copyright 2014, Doug Wiegley (dougwig), A10 Networks
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

import acos_client
from neutron.openstack.common import log as logging
from neutron.services.loadbalancer.drivers import driver_base

import a10_config
import mgr_hm
import mgr_lb
import mgr_listener
import mgr_member
import mgr_pool

VERSION = "J1.0.0"
LOG = logging.getLogger(__name__)


class ThunderDriver(driver_base.LoadBalancerBaseDriver):

    def __init__(self, plugin):
        super(ThunderDriver, self).__init__(plugin)

        self.load_balancer = mgr_lb.LoadBalancerManager(self)
        self.listener = mgr_listener.ListenerManager(self)
        self.pool = mgr_pool.PoolManager(self)
        self.member = mgr_member.MemberManager(self)
        self.health_monitor = mgr_hm.HealthMonitorManager(self)

        LOG.info("A10Driver: initializing, version=%s, acos_client=%s",
                 VERSION, acos_client.VERSION)

        self.config = a10_config.A10Config()
        self.appliance_hash = acos_client.Hash(self.config.devices.keys())
        if self.config.get('verify_appliances', True):
            self._verify_appliances()

    def _select_a10_device(self, tenant_id):
        s = self.appliance_hash.get_server(tenant_id)
        return self.config.devices[s]

    def _get_a10_client(self, device_info):
        d = device_info
        protocol = d.get('protocol', 'https')
        port = {'http': 80, 'https': 443}[protocol]
        if 'port' in d:
            port = d['port']

        return acos_client.Client(d['host'],
                                  d.get('api_version', acos_client.AXAPI_21),
                                  d['username'], d['password'],
                                  port=port, protocol=protocol)

    def _verify_appliances(self):
        LOG.info("A10Driver: verifying appliances")

        if len(self.config.devices) == 0:
            LOG.error(_("A10Driver: no configured appliances"))

        for k, v in self.config.devices.items():
            try:
                LOG.info("A10Driver: appliance(%s) = %s", k,
                         self._get_a10_client(v).system.information())
            except Exception:
                LOG.error(_("A10Driver: unable to connect to configured"
                            "appliance, name=%s"), k)
