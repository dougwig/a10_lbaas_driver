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

VERSION = "J1.0.0"
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


class A10Context(object):

    def __init__(self, mgr, context, lbaas_obj):
        self.mgr = mgr
        self.context = context
        self.lbaas_obj = lbaas_obj

    def __enter__(self):
        self.tenant_id = self.lbaas_obj.tenant_id
        self.device_cfg = self.mgr.driver._select_a10_device(self.tenant_id)
        self.client = self.mgr.driver._get_a10_client(self.device_cfg)
        self.select_appliance_partition()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.session.close()

        if exc_type is not None:
            todo_error

    def select_appliance_partition(self):
        # If we are not using appliance partitions, we are done.
        if self.device_cfg['v_method'].lower() != 'adp':
            return

        # Try to make the requested partition active
        try:
            self.client.system.partition.active(self.tenant_id)
            return
        except acos_errors.NotFound:
            pass

        # Create it if not found
        self.client.system.partition.create(self.tenant_id)
        self.client.system.partition.active(self.tenant_id)


class A10WriteContext(A10Context):

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.client.system.write_memory()

        super(A10WriteContext, self).__exit__(exc_type, exc_value, traceback)


class A10WriteStatusContext(A10WriteContext):

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.mgr.active(self.context, self.lbaas_obj.id)
        else:
            self.mgr.failed(self.context, self.baas_obj.id)

        super(A10CreateContext, self).__exit__(exc_type, exc_value, traceback)


class A10DeleteContext(A10WriteContext):

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.db_delete(self.context, self.baas_obj.id)
            self.partition_cleanup_check()

        super(A10DeleteContext, self).__exit__(exc_type, exc_value, traceback)

    def partition_cleanup_check(self):
        todo
        tloadbalander = context._session.query(lb_db.Pool)
        n = tpool.filter_by(tenant_id=pool['tenant_id']).count()

        tlistener = context._session.query(lb_db.Pool)
        n = tpool.filter_by(tenant_id=pool['tenant_id']).count()

        tpool = context._session.query(lb_db.Pool)
        n = tpool.filter_by(tenant_id=pool['tenant_id']).count()

        if n == 0 and n == 0 and n == 0:
                   try:
                        c.client.partition_delete(tenant_id=pool['tenant_id'])
                    except Exception:
                        raise a10_ex.ParitionDeleteError(
                            partition=pool['tenant_id'][0:13])


class LoadBalancerManager(driver_base.BaseLoadBalancerManager):

    def create(self, context, load_balancer):
        with A10WriteStatusContext(self, context, load_balancer) as c:
            c.client.slb.virtual_server.create(blah)

    def create(self, context, obj):
        with A10WriteStatusContext(self, context, pool) as c:
            c.client.slb.virtual_server.create(blah)

    def update(self, context, old_obj, obj):
        with A10WriteStatusContext(self, context, pool) as c:
            c.client.slb.virtual_server.update(blah)

    def delete(self, context, obj):
        with A10DeleteContext(self, context, pool) as c:
            c.client.slb.virtual_server.delete(blah)

    def refresh(self, context, lb_obj, force=False):
        # This is intended to trigger the backend to check and repair
        # the state of this load balancer and all of its dependent objects
        LOG.debug("LB pool refresh %s, force=%s", lb_obj.id, force)
        with A10Context(self, context, pool) as c:
            todo

    def stats(self, context, lb_obj):
        with A10Context(self, context, pool) as c:
            try:
                r = c.client.client.slb.virtual_server.stats(lb_obj.id)
                return {
                    "bytes_in": r["virtual_server_stat"]["req_bytes"],
                    "bytes_out": r["virtual_server_stat"]["resp_bytes"],
                    "active_connections": 
                        r["virtual_server_stat"]["cur_conns"],
                    "total_connections": r["virtual_server_stat"]["tot_conns"]
                }
            except Exception:
                return {
                    "bytes_in": 0,
                    "bytes_out": 0,
                    "active_connections": 0,
                    "total_connections": 0
                }


class ListenerManager(driver_base.BaseListenerManager):

    # SESSION_PERSISTENCE_SOURCE_IP = 'SOURCE_IP'
    # SESSION_PERSISTENCE_HTTP_COOKIE = 'HTTP_COOKIE'
    # SESSION_PERSISTENCE_APP_COOKIE = 'APP_COOKIE'

    def _set(self, set_method, context, listener):
        protocols = {
            'TCP': c.client.slb.virtual_server.vport.protocol.TCP,
            'UDP': c.client.slb.virtual_server.vport.protocol.UDP,
            'HTTP': c.client.slb.virtual_server.vport.protocol.HTTP,
            'HTTPS': c.client.slb.virtual_server.vport.protocol.HTTPS
        }

        set_method(listener.load_balander_id, listener.id,
                   protocol=protocols[listener.protocol],
                   port=listener.port,
                   service_group_name=listener.pool_id,
                   s_pers_name=spers,
                   c_pers_name=cpers,
                   status=status)

    def create(self, context, listener):
        with A10WriteStatusContext(self, context, pool) as c:
            self._set(c.client.slb.virtual_server.vport.create, context,
                      listener)

    def update(self, context, old_listener, listener):
        with A10WriteStatusContext(self, context, pool) as c:
            self._set(c.client.slb.virtual_server.vport.update, context,
                      listener)

    def delete(self, context, listener):
        with A10DeleteContext(self, context, pool) as c:
            try:
                if vip['session_persistence'] is not None:
                    c.client.persistence_delete(
                        vip['session_persistence']['type'],
                        vip['id'])
            except Exception:
                pass

            c.client.slb.virtual_server.vport.delete(
                listener.load_balancer_id,
                listener.id,
                protocol=protocols[listener.protocol],
                port=listener.port)


class PoolManager(driver_base.BasePoolManager):

    def _set(self, context, pool, c, set_method):
        lb_algorithms = {
            'ROUND_ROBIN': c.client.slb.service_group.ROUND_ROBIN,
            'LEAST_CONNECTIONS': c.client.slb.service_group.LEAST_CONNECTION,
            'SOURCE_IP': c.client.slb.service_group.WEIGHTED_LEAST_CONNECTION
        }
        protocols = {
            'TCP': c.client.slb.service_group.TCP,
            'UDP': c.client.slb.service_group.UDP
        }

        set_method(pool.id,
                   protocol=protocols[pool.protocol],
                   lb_method=algoritms[pool.lb_algorithm])

    def create(self, context, pool):
        with A10WriteStatusContext(self, context, pool) as c:
            self._set(context, pool, c, c.client.slb.service_group.create)

    def update(self, context, old_pool, pool):
        with A10WriteStatusContext(self, context, pool) as c:
            self._set(context, pool, c, c.client.slb.service_group.update)

    def delete(self, context, pool):
        with A10DeleteContext(self, context, pool) as c:
            for member in pool.members:
                todo  # delete member, call driver interface or api direct?
            if pool.health_monitor:
                todo  # delete hm, call driver interface or api direct?
            for members in pool['members']:
                self.delete_member(context, self.plugin.get_member(
                    context, members))

            for hm in pool['health_monitors_status']:
                hmon = self.plugin.get_health_monitor(context, hm['monitor_id'])
                self.delete_pool_health_monitor(context, hmon, pool['id'])
            c.client.slb.service_group.delete(pool.id)


class MemberManager(driver_base.BaseMemberManager):

    def _get_ip(self, context, member, use_float=False):
        ip_address = member['address']
        if use_float:
            fip_qry = context.session.query(l3_db.FloatingIP)
            if (fip_qry.filter_by(fixed_ip_address=ip_address).count() > 0):
                float_address = fip_qry.filter_by(
                    fixed_ip_address=ip_address).first()
                ip_address = str(float_address.floating_ip_address)
        return ip_address

    def _get_name(self, member, ip_address):
        tenant_label = member['tenant_id'][:5]
        addr_label = str(ip_address).replace(".", "_", 4)
        server_name = "_%s_%s_neutron" % (tenant_label, addr_label)
        return server_name

    def _count(self, context, member):
        return context._session.query(lb_db.Member).filter_by(
            tenant_id=member['tenant_id'],
            address=member['address']).count()

    def create(self, context, member):
        with A10WriteStatusContext(self, context, pool) as c:
            server_ip = self._get_ip(context, member,
                                     c.device_cfg['use_float'])
            server_name = self._get_name(member, server_ip)

            status = c.client.slb.service_group.member.UP
            if not member["admin_state_up"]:
                status = c.client.slb.service_group.member.DOWN

            try:
                c.client.server_create(server_name, ip_address)
            except acos_errors.Exists:
                pass

            c.client.slb.member.create(member.pool_id, server_name,
                                member.protocol_port, status=status)

    def update(self, context, old_obj, obj):
        with A10WriteStatusContext(self, context, pool) as c:
            server_ip = self._get_ip(context, member,
                                     c.device_cfg['use_float'])
            server_name = self._get_name(member, server_ip)

            status = c.client.slb.service_group.member.UP
            if not member["admin_state_up"]:
                status = c.client.slb.service_group.member.DOWN

            c.client.slb.service_group.member.update(member.pool_id, server_name,
                                              member.protocol_port, status)

    def delete(self, context, member):
        with A10DeleteContext(self, context, pool) as c:
            server_ip = self._get_ip(context, member, todo,
                                     c.device_cfg['use_float'])
            server_name = self._get_name(member, server_ip)

            if self._count(context, member) > 1:
                c.client.slb.service_group.member.delete(member.pool_id,
                                                  server_name,
                                                  member.protocol_port)
            else:
                c.client.slb.server.delete(server_name)


class HealthMonitorManager(driver_base.BaseHealthMonitorManager):

    def _set(self, context, hm, c, set_method):
        hm_map = {
            'PING': c.client.slb.hm.ICMP,
            'TCP': c.client.slb.hm.TCP,
            'HTTP': c.client.slb.hm.HTTP,
            'HTTPS': c.client.slb.hm.HTTPS
        }

        hm_name = hm.id[0:28]
        set_method(hm_name, hm_map[hm.type],
                   hm.delay, hm.timeout, hm.max_retries,
                   hm.http_method, hm.url_path, hm.expected_codes)

        if hm.pool:
            c.client.slb.service_group.update(hm.pool.id, health_monitor=hm_name)

    def create(self, context, hm):
        with A10WriteStatusContext(self, context, pool) as c:
            self._set(context, hm, c, c.client.slb.hm.create)

    def update(self, context, old_hm, hm):
        with A10WriteStatusContext(self, context, pool) as c:
            self._set(context, hm, c, c.client.slb.hm.update)

    def delete(self, context, hm):
        with A10DeleteContext(self, context, pool) as c:
            if hm.pool:
                c.client.slb.service_group.update(hm.pool.id, health_monitor="")
            c.client.slb.hm.delete(hm.id[0:28])
