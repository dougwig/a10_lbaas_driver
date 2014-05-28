# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013,  Mike Thompson,  A10 Networks.
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

from neutron.db import l3_db
from neutron.db.loadbalancer import loadbalancer_db as lb_db
from neutron.openstack.common import log as logging
from neutron.plugins.common import constants

# TODO(dougw) - not inheriting; causes issues with Havana
#from neutron.services.loadbalancer.drivers import abstract_driver

from neutron.services.loadbalancer.drivers.a10networks import (
    a10_exceptions as a10_ex
)
from neutron.services.loadbalancer.drivers.a10networks import a10_config
from neutron.services.loadbalancer.drivers.a10networks import acos_client

VERSION = "0.3.1"
LOG = logging.getLogger(__name__)


# TODO(dougw) - not inheriting; causes issues with Havana
#class ThunderDriver(abstract_driver.LoadBalancerAbstractDriver):
class ThunderDriver(object):

    def __init__(self, plugin):
        LOG.info("A10Driver: init version=%s", VERSION)
        self.plugin = plugin
        self.config = a10_config.A10Config()
        self._verify_appliances()

    def _verify_appliances(self):
        LOG.info("A10Driver: verifying appliances")
        for k, v in self.config.devices.items():
            acos_client.A10Client(self.config, dev_info=v,
                                  version_check=True)

    def _device_context(self, tenant_id=""):
        return acos_client.A10Client(self.config, tenant_id=tenant_id)

    def _active(self, context, model, vid):
        self.plugin.update_status(context, model, vid, constants.ACTIVE)

    def _failed(self, context, model, vid):
        self.plugin.update_status(context, model, vid, constants.ERROR)

    def _persistence_create(self, a10, vip):
        persist_type = vip['session_persistence']['type']
        name = vip['id']

        try:
            if a10.persistence_exists(persist_type, name):
                return name
            a10.persistence_create(persist_type, name)
        except Exception:
            raise a10_ex.TemplateCreateError(template=name)

        return name

    def _setup_vip_args(self, a10, vip):
        s_pers = None
        c_pers = None
        LOG.debug("_setup_vip_args vip=%s", vip)
        if ('session_persistence' in vip and
                vip['session_persistence'] is not None):
            LOG.debug("creating persistence template")
            pname = self._persistence_create(a10, vip)
            if vip['session_persistence']['type'] is "HTTP_COOKIE":
                c_pers = pname
            elif vip['session_persistence']['type'] == "SOURCE_IP":
                s_pers = pname
        status = 1
        if vip['admin_state_up'] is False:
            status = 0
        LOG.debug("_setup_vip_args = %s, %s, %d", s_pers, c_pers, status)
        return s_pers, c_pers, status

    def create_vip(self, context, vip):
        a10 = self._device_context(tenant_id=vip['tenant_id'])
        s_pers, c_pers, status = self._setup_vip_args(a10, vip)

        try:
            a10.virtual_server_create(vip['id'], vip['address'],
                                      vip['protocol'], vip['protocol_port'],
                                      vip['pool_id'],
                                      s_pers, c_pers, status)
            self._active(context, lb_db.Vip, vip['id'])

        except Exception:
            self._failed(context, lb_db.Vip, vip['id'])
            raise a10_ex.VipCreateError(vip=vip['id'])

    def update_vip(self, context, old_vip, vip):
        a10 = self._device_context(tenant_id=vip['tenant_id'])
        s_pers, c_pers, status = self._setup_vip_args(a10, vip)

        try:
            a10.virtual_port_update(vip['id'], vip['protocol'],
                                    vip['pool_id'],
                                    s_pers, c_pers, status)
            self._active(context, lb_db.Vip, vip['id'])

        except Exception:
            self._failed(context, lb_db.Vip, vip['id'])
            raise a10_ex.VipUpdateError(vip=vip['id'])

    def delete_vip(self, context, vip):
        a10 = self._device_context(tenant_id=vip['tenant_id'])
        try:
            if vip['session_persistence'] is not None:
                a10.persistence_delete(vip['session_persistence']['type'],
                                       vip['id'])
        except Exception:
            pass

        try:
            a10.virtual_server_delete(vip['id'])
            self.plugin._delete_db_vip(context, vip['id'])
        except Exception:
            self._failed(context, lb_db.Vip, vip['id'])
            raise a10_ex.VipDeleteError(vip=vip['id'])

    def create_pool(self, context, pool):
        a10 = self._device_context(tenant_id=pool['tenant_id'])
        try:
            if pool['lb_method'] == "ROUND_ROBIN":
                lb_method = "0"
            elif pool['lb_method'] == "LEAST_CONNECTIONS":
                lb_method = "2"
            else:
                lb_method = "3"

            a10.service_group_create(pool['id'], lb_method)
            self._active(context, lb_db.Pool, pool['id'])
        except Exception:
            self._failed(context, lb_db.Pool, pool['id'])
            raise a10_ex.SgCreateError(sg=pool['id'])

    def update_pool(self, context, old_pool, pool):
        a10 = self._device_context(tenant_id=pool['tenant_id'])
        try:
            if pool['lb_method'] == "ROUND_ROBIN":
                lb_method = "0"
            elif pool['lb_method'] == "LEAST_CONNECTIONS":
                lb_method = "2"
            else:
                lb_method = "3"

            a10.service_group_update(pool['id'], lb_method)
            self._active(context, lb_db.Pool, pool['id'])
        except Exception:
            self._failed(context, lb_db.Pool, pool['id'])
            raise a10_ex.SgUpdateError(sg=pool['id'])

    def delete_pool(self, context, pool):
        LOG.debug('delete_pool context=%s, pool=%s' % (context, pool))
        a10 = self._device_context(tenant_id=pool['tenant_id'])

        for members in pool['members']:
            self.delete_member(context, self.plugin.get_member(
                context, members))

        for hm in pool['health_monitors_status']:
            hmon = self.plugin.get_health_monitor(context, hm['monitor_id'])
            self.delete_pool_health_monitor(context, hmon, pool['id'])

        removed_a10 = False
        try:
            a10.service_group_delete(pool['id'])
            removed_a10 = True
            self.plugin._delete_db_pool(context, pool['id'])

        except Exception:
            if removed_a10:
                raise a10_ex.SgDeleteError(sg="SG was REMOVED from ACOS "
                                           "entity but cloud not be removed "
                                           "from OS DB.")
            else:
                raise a10_ex.SgDeleteError(sg="SG was not REMOVED from an "
                                           "ACOS entity please contact your "
                                           "admin.")

        finally:
            if a10.device_info['v_method'].lower() == 'adp':
                tpool = context._session.query(lb_db.Pool)
                n = tpool.filter_by(tenant_id=pool['tenant_id']).count()
                if n == 0:
                    try:
                        a10.partition_delete(tenant_id=pool['tenant_id'])
                    except Exception:
                        raise a10_ex.ParitionDeleteError(
                            partition=pool['tenant_id'][0:13])

    def stats(self, context, pool_id):
        pool_qry = context._session.query(lb_db.Pool).filter_by(id=pool_id)
        vip_id = pool_qry.vip_id
        a10 = self._device_context(tenant_id=pool_qry.tenant_id)
        try:
            r = a10.stats(vip_id)
            s = {
                "bytes_in": r["virtual_server_stat"]["req_bytes"],
                "bytes_out": r["virtual_server_stat"]["resp_bytes"],
                "active_connections": r["virtual_server_stat"]["cur_conns"],
                "total_connections": r["virtual_server_stat"]["tot_conns"]
            }
        except Exception:
            s = {
                "bytes_in": 0,
                "bytes_out": 0,
                "active_connections": 0,
                "total_connections": 0
            }
        return s

    def _get_member_ip(self, context, member, a10):
        ip_address = member['address']
        if a10.device_info['use_float']:
            fip_qry = context.session.query(l3_db.FloatingIP)
            if (fip_qry.filter_by(fixed_ip_address=ip_address).count() > 0):
                float_address = fip_qry.filter_by(
                    fixed_ip_address=ip_address).first()
                ip_address = str(float_address.floating_ip_address)
        return ip_address

    def _get_member_server_name(self, member, ip_address):
        tenant_label = member['tenant_id'][:5]
        addr_label = str(ip_address).replace(".", "_", 4)
        server_name = "_%s_%s_neutron" % (tenant_label, addr_label)
        return server_name

    def create_member(self, context, member):
        a10 = self._device_context(tenant_id=member['tenant_id'])

        ip_address = self._get_member_ip(context, member, a10)
        server_name = self._get_member_server_name(member, ip_address)

        try:
            if 'server' not in a10.server_get(server_name):
                a10.server_create(server_name, ip_address)
        except Exception:
            self._failed(context, lb_db.Member, member["id"])
            raise a10_ex.MemberCreateError(member=server_name)

        try:
            status = 1
            if member["admin_state_up"] is False:
                status = 0

            a10.member_create(member['pool_id'], server_name,
                              member['protocol_port'], status)
            self._active(context, lb_db.Member, member["id"])
        except Exception:
            self._failed(context, lb_db.Member, member["id"])
            raise a10_ex.MemberCreateError(member=server_name)

    def update_member(self, context, old_member, member):
        a10 = self._device_context(tenant_id=member['tenant_id'])

        ip_address = self._get_member_ip(context, member, a10)
        server_name = self._get_member_server_name(member, ip_address)

        try:
            status = 1
            if member["admin_state_up"] is False:
                status = 0

            a10.member_update(member['pool_id'], server_name,
                              member['protocol_port'], status)
            self._active(context, lb_db.Member, member["id"])
        except Exception:
            self._failed(context, lb_db.Member, member["id"])
            raise a10_ex.MemberUpdateError(member=server_name)

    def delete_member(self, context, member):
        a10 = self._device_context(tenant_id=member['tenant_id'])

        member_count = context._session.query(lb_db.Member).filter_by(
            tenant_id=member['tenant_id'],
            address=member['address']).count()

        ip_address = self._get_member_ip(context, member, a10)
        server_name = self._get_member_server_name(member, ip_address)

        try:
            if member_count > 1:
                a10.member_delete(member['pool_id'], server_name,
                                  member['protocol_port'])
                self.plugin._delete_db_member(context, member['id'])
            else:
                a10.server_delete(server_name)
                self.plugin._delete_db_member(context, member['id'])
        except Exception:
            self._failed(context, lb_db.Member, member["id"])
            raise a10_ex.MemberDeleteError(member=member["id"])

    def update_pool_health_monitor(self, context, old_health_monitor,
                                   health_monitor, pool_id):
        a10 = self._device_context(tenant_id=health_monitor['tenant_id'])
        hm_name = health_monitor['id'][0:28]
        try:
            a10.health_monitor_update(health_monitor['type'],
                                      hm_name,
                                      health_monitor['delay'],
                                      health_monitor['timeout'],
                                      health_monitor['max_retries'],
                                      health_monitor.get('http_method'),
                                      health_monitor.get('url_path'),
                                      health_monitor.get('expected_codes'))

            self.plugin.update_pool_health_monitor(context,
                                                   health_monitor["id"],
                                                   pool_id,
                                                   constants.ACTIVE)

        except Exception:
            raise a10_ex.HealthMonitorUpdateError(hm=hm_name)

    def create_pool_health_monitor(self, context, health_monitor, pool_id):
        a10 = self._device_context(tenant_id=health_monitor['tenant_id'])
        hm_name = health_monitor['id'][0:28]
        try:
            a10.health_monitor_create(health_monitor['type'],
                                      hm_name,
                                      health_monitor['delay'],
                                      health_monitor['timeout'],
                                      health_monitor['max_retries'],
                                      health_monitor.get('http_method'),
                                      health_monitor.get('url_path'),
                                      health_monitor.get('expected_codes'))

            for pool in health_monitor['pools']:
                a10.service_group_update_hm(pool['pool_id'], hm_name)

            self.plugin.update_pool_health_monitor(context,
                                                   health_monitor["id"],
                                                   pool_id,
                                                   constants.ACTIVE)
        except Exception:
            self.plugin.update_pool_health_monitor(context,
                                                   health_monitor["id"],
                                                   pool_id,
                                                   constants.ERROR)
            self.plugin._delete_db_pool_health_monitor(context,
                                                       health_monitor['id'],
                                                       pool_id)
            raise a10_ex.HealthMonitorUpdateError(hm=hm_name)

    def delete_pool_health_monitor(self, context, health_monitor, pool_id):
        a10 = self._device_context(tenant_id=health_monitor['tenant_id'])
        try:
            a10.service_group_update_hm(pool_id, "")

            hm_binding_qty = (context.session.query(
                lb_db.PoolMonitorAssociation
            ).filter_by(monitor_id=health_monitor['id']).join(lb_db.Pool)
                .count())
            if hm_binding_qty == 1:
                a10.health_monitor_delete(health_monitor['id'][0:28])

            self.plugin._delete_db_pool_health_monitor(context,
                                                       health_monitor['id'],
                                                       pool_id)
        except Exception:
            self.plugin.update_pool_health_monitor(context,
                                                   health_monitor["id"],
                                                   pool_id,
                                                   constants.ERROR)
