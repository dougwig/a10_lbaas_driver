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

VERSION = "1.0.0"
LOG = logging.getLogger(__name__)


class ThunderDriver(driver_base.LoadBalancerBaseDriver):

    def __init__(self, plugin):
        super(ThunderDriver, self).__init__(plugin)

        self.load_balancer = LoadBalancerManager(self)
        self.listener = ListenerManager(self)
        self.pool = PoolManager(self)
        self.member = MemberManager(self)
        self.health_monitor = HealthMonitorManager(self)

        LOG.info("A10Driver: initializing, version=%s, acos_client=%s",
                 VERSION, acos_client.VERSION)

        self.config = a10_config.A10Config()
        self.appliance_hash = acos_client.Hash(self.config.devices.keys())
        if self.config.get('verify_appliances', True):
            self._verify_appliances()

    def _get_a10_client(self, tenant_id, device_info=None):
        if device_info is None:
            s = self.appliance_hash.get_server(tenant_id)
            d = self.config.devices[s]
        else:
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
                         self._get_a10_client(None, v).system.information())
            except Exception:
                LOG.error(_("A10Driver: unable to connect to configured"
                            "appliance, name=%s"), k)


class A10Context(object):

    def __init__(self, mgr, context, lbaas_obj):
        self.mgr = mgr
        self.context = context
        self.lbaas_obj = lbaas_obj

    def __enter__(self):
        self.client = self.a10_client(self.lbaas_obj.tenant_id)
        return self.client

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.session.close()

        if exc_type is not None:
            todo_error

    def a10_client(self, tenant_id):
        c = self.mgr.driver._get_a10_client(self.lbaas_obj.tenant_id)
        self.select_appliance_partition(c, tenant_id)
        return c

    def select_appliance_partition(self, client, tenant_id):
        # If we are not using appliance partitions, we are done.
        if self.device_info['v_method'].lower() != 'adp':
            return

        # Try to make the requested partition active
        try:
            client.system.partition.active(tenant_id)
            return
        except acos_errors.NotFound:
            pass

        # Create it if not found
        client.system.partition.create(tenant_id)
        client.system.partition.active(tenant_id)


class A10WriteContext(A10Context):

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.a10_client.system.write_memory()

        super(A10WriteContext, self).__exit__(exc_type, exc_value, traceback)


class A10WriteStatusContext(A10WriteContext):

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.active(self.context, self.obj_id)
        else:
            self.failed(self.context, self.obj_id)

        super(A10CreateContext, self).__exit__(exc_type, exc_value, traceback)


class A10DeleteContext(A10WriteContext):

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.db_delete(self.context, self.obj_id)

        super(A10DeleteContext, self).__exit__(exc_type, exc_value, traceback)


class LoadBalancerManager(driver_base.BaseLoadBalancerManager):
    # SESSION_PERSISTENCE_SOURCE_IP = 'SOURCE_IP'
    # SESSION_PERSISTENCE_HTTP_COOKIE = 'HTTP_COOKIE'
    # SESSION_PERSISTENCE_APP_COOKIE = 'APP_COOKIE'

    def create(self, context, load_balancer):
        with A10CreateContext(self, context, load_balancer) as c:
            c.slb.virtual_server.create(blah)

    def create(self, context, obj):
        with A10WriteStatusContext(self, context, pool) as c:
            a10.slb.virtual_service.create(blah)

    def update(self, context, old_obj, obj):
        with A10WriteStatusContext(self, context, pool) as c:
            a10.slb.virtual_service.update(blah)

    def delete(self, context, obj):
        with A10DeleteContext(self, context, pool) as c:
            a10.slb.virtual_service.delete(blah)

    def refresh(self, context, lb_obj, force=False):
        # This is intended to trigger the backend to check and repair
        # the state of this load balancer and all of its dependent objects
        LOG.debug("LB pool refresh %s, force=%s", lb_obj.id, force)
        with A10WriteStatusContext(self, context, pool) as c:
            todo

    def stats(self, context, lb_obj_id):
        with A10Context(self, context, pool) as c:
            LOG.debug("LB stats %s", lb_obj_id)
            return {
                "bytes_in": 0,
                "bytes_out": 0,
                "active_connections": 0,
                "total_connections": 0
            }


class ListenerManager(driver_base.BaseListenerManager):

    # class VirtualService(base.BaseV21):   # aka VirtualPort
    #     # Protocols
    #     TCP = 2
    #     UDP = 3
    #     HTTP = 11
    #     HTTPS = 12
    # PROTOCOL_TCP = 'TCP'
    # PROTOCOL_HTTP = 'HTTP'
    # PROTOCOL_HTTPS = 'HTTPS'
    # def create(self, name, ip_address, protocol, port, service_group_id,
    #            s_pers=None, c_pers=None, status=1):

    def create(self, context, listener):
        protocols = {
            'TCP': a10.slb.virtual_service.protocol.TCP,
            'UDP': a10.slb.virtual_service.protocol.UDP,
            'HTTP': a10.slb.virtual_service.protocol.HTTP,
            'HTTPS': a10.slb.virtual_service.protocol.HTTPS
        }

        a10.slb.virtual_service.create(listener.id,
                                       protocols[listener.protocol],
                                       listener.port,
                                       listener.pool_id,
                                       spers,
                                       cpers,
                                       status)

    def create(self, context, obj):
        with A10WriteStatusContext(self, context, pool) as c:
            a10.slb.virtual_server.create(blah)

    def update(self, context, old_obj, obj):
        with A10WriteStatusContext(self, context, pool) as c:
            a10.slb.virtual_server.update(blah)

    def delete(self, context, obj):
        with A10DeleteContext(self, context, pool) as c:
            a10.slb.virtual_server.delete(blah)


class PoolManager(driver_base.BasePoolManager):

    def _set(self, context, pool, c, set_method):
        lb_algorithms = {
            'ROUND_ROBIN': c.slb.service_group.ROUND_ROBIN,
            'LEAST_CONNECTIONS': c.slb.service_group.LEAST_CONNECTION,
            'SOURCE_IP': c.slb.service_group.WEIGHTED_LEAST_CONNECTION
        }
        protocols = {
            'TCP': c.slb.service_group.TCP,
            'UDP': c.slb.service_group.UDP
        }

        set_method(pool.id,
                   protocol=protocols[pool.protocol],
                   lb_method=algoritms[pool.lb_algorithm])

    def create(self, context, pool):
        with A10WriteStatusContext(self, context, pool) as c:
            self._set(context, pool, c, c.slb.service_group.create)

    def update(self, context, old_pool, pool):
        with A10WriteStatusContext(self, context, pool) as c:
            self._set(context, pool, c, c.slb.service_group.update)

    def delete(self, context, pool):
        with A10DeleteContext(self, context, pool) as c:
            for member in pool.members:
                todo  # delete member, call driver interface or api direct?
            if pool.health_monitor:
                todo  # delete hm, call driver interface or api direct?
            c.slb.service_group.delete(pool.id)


class MemberManager(driver_base.BaseMemberManager):

    def create(self, context, member):
        with A10WriteStatusContext(self, context, pool) as c:
            if member.admin_state_up:
                status = c.slb.service_group.member.UP
            else:
                status = c.slb.service_group.member.DOWN

            try:
                a10.server_create(server_name, ip_address)
            except acos_errors.Exists:
                pass

            a10.slb.member.create(member.pool_id,
                                  server_name, member.protocol_port,
                                  status=status)

    def update(self, context, old_obj, obj):
        with A10WriteStatusContext(self, context, pool) as c:
            a10.slb.service_group.member.update(blah)

    @lbaas_delete
    def delete(self, context, obj):
        with A10DeleteContext(self, context, pool) as c:
            a10.slb.service_group.member.delete(blah)


class HealthMonitorManager(driver_base.BaseHealthMonitorManager):

    def _set(self, context, hm, c, set_method):
        hm_map = {
            'PING': c.slb.hm.ICMP,
            'TCP': c.slb.hm.TCP,
            'HTTP': c.slb.hm.HTTP,
            'HTTPS': c.slb.hm.HTTPS
        }

        hm_name = hm.id[0:28]
        set_method(hm_name, hm_map[hm.type],
                   hm.delay, hm.timeout, hm.max_retries,
                   hm.http_method, hm.url_path, hm.expected_codes)

        if hm.pool:
            c.slb.service_group.update(hm.pool.id, health_monitor=hm_name)

    def create(self, context, hm):
        with A10WriteStatusContext(self, context, pool) as c:
            self._set(context, hm, c, c.slb.hm.create)

    def update(self, context, old_hm, hm):
        with A10WriteStatusContext(self, context, pool) as c:
            self._set(context, hm, c, c.slb.hm.update)

    def delete(self, context, hm):
        with A10DeleteContext(self, context, pool) as c:
            if hm.pool:
                c.slb.service_group.update(hm.pool.id, health_monitor="")
            c.slb.hm.delete(hm.id[0:28])
