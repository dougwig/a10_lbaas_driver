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

import traceback

import a10_exceptions as a10_ex
import request_struct_v2

from neutron.db import l3_db
from neutron.db.loadbalancer import loadbalancer_db as lb_db
from neutron.openstack.common import log as logging
from neutron.plugins.common import constants
from neutron.services.loadbalancer.drivers import abstract_driver

from acos_client import A10Client


LOG = logging.getLogger(__name__)


class ThunderDriver(abstract_driver.LoadBalancerAbstractDriver):

    def __init__(self, plugin):
        self.plugin = plugin

    def _device_context(self, tenant_id=""):
        return A10Client(tenant_id=tenant_id)

    def _active(self, a, b, c):
        self.plugin.update_status(a, b, c, constants.ACTIVE)

    def _failed(self, a, b, c):
        self.plugin.update_status(a, b, c, constants.ERROR)

    def create_vip(self, context, vip):
        """
        Contruct the Device Context First.
        """
        a10 = self._device_context(tenant_id=vip['tenant_id'])
        vs = request_struct_v2.virtual_server_object.ds.toDict()
        vs['virtual_server']['address'] = vip['address']
        vs['virtual_server']['name'] = vip['id']
        if vip['admin_state_up'] is False:
            vs['virtual_server']['status'] = 0

        if vip['protocol'] == "HTTP":
            vport_obj = request_struct_v2.vport_HTTP_obj.ds.toDict()
        else:
            vport_obj = request_struct_v2.vport_TCP_obj.ds.toDict()
        vport_obj['service_group'] = vip['pool_id']
        vport_obj['port'] = vip['protocol_port']
        vport_obj['name'] = vip['id'] + "_VPORT"
        temp_name = self.persistence_create(vip)
        if temp_name is not None and vip['session_persistence'] is not None:
            if vip['session_persistence']['type'] is "HTTP_COOKIE":
                vport_obj["cookie_persistence_template"] = temp_name
            elif vip['session_persistence']['type'] == "SOURCE_IP":
                vport_obj['source_ip_persistence_template'] = temp_name
            vport_obj['name'] = vip['id']
        if 'True' in self.device.device_info['autosnat']:
            vport_obj['source_nat_auto'] = 1
        vs['vport_list'] = [vport_obj]
        service_group_search_req = (request_struct_v2.service_group_json_obj
                                    .call.search.toDict().items())
        service_group_search_res = (self.device.send(
            tenant_id=vip['tenant_id'],
            method=service_group_search_req[0][0],
            url=service_group_search_req[0][1],
            body={'name': vip['pool_id']}))

        if "service_group" in service_group_search_res:
            create_vip_req = (request_struct_v2.virtual_server_object.call
                              .create.toDict().items())
            try:
                if (self.inspect_response(self.device.send(
                        tenant_id=vip['tenant_id'],
                        method=create_vip_req[0][0],
                        url=create_vip_req[0][1],
                        body=vs))) is True:
                    self.plugin.update_status(context, lb_db.Vip,
                                              vip['id'], constants.ACTIVE)
                else:
                    self.plugin.update_status(context, lb_db.Vip,
                                              vip['id'], constants.ERROR)
                    LOG.debug(traceback.format_exc())
                    raise a10_ex.VipCreateError(vip=vip['id'])

            except:
                LOG.debug(traceback.format_exc())
                raise a10_ex.VipCreateError(vip=vip['id'])

        else:
            LOG.debug(traceback.format_exc())
            self.plugin.update_status(context, lb_db.Vip,
                                      vip['id'], constants.ERROR)
            raise a10_ex.VipCreateError(vip=vip['id'])

    def update_vip(self, context, old_vip, vip):
        self.device_context(tenant_id=vip['tenant_id'])
        vport_name = vip['id'] + "_VPORT"
        if vip['protocol'] is "HTTP":
            vport_obj_req = (request_struct_v2.vport_HTTP_obj.call.search
                             .toDict().items())
            vport_update_req = (request_struct_v2.vport_HTTP_obj.call.update
                                .toDict().items())

        else:
            vport_obj_req = (request_struct_v2.vport_TCP_obj.call
                             .search.toDict().items())
            vport_update_req = (request_struct_v2.vport_TCP_obj.call.update
                                .toDict().items())
        try:
            vport_res = self.device.send(tenant_id=vip['tenant_id'],
                                         method=vport_obj_req[0][0],
                                         url=vport_obj_req[0][1],
                                         body={"name": vport_name})
        except:
            LOG.debug(traceback.format_exc())
            raise a10_ex.SearchError(term="vPort Object")

        if 'virtual_service' in vport_res:
            if vip['session_persistence'] is not None:
                temp_name = self.persistence_create(vip)
                if (vip['session_persistence']['type'] is
                        "HTTP_COOKIE"):
                    vport_res["cookie_persistence_template"] = temp_name
                elif (vip['session_persistence']['type'] is "SOURCE_IP"):
                    vport_res['source_ip_persistence_template'] = temp_name

            vport_res['service_group'] = vip['pool_id']
            if vip['admin_state_up'] is False:
                vport_res['status'] = 0

            try:
                if (self.inspect_response(self.device.send(
                        tenant_id=vip['tenant_id'],
                        method=vport_update_req[0][0],
                        url=vport_update_req[0][1],
                        body=vport_res))) is True:
                    self.plugin.update_status(context, lb_db.Vip,
                                              vip['id'], constants.ACTIVE)
                else:
                    self.plugin.update_status(context, lb_db.Vip,
                                              vip['id'], constants.ERROR)
                    LOG.debug(traceback.format_exc())
                    raise a10_ex.VipUpdateError(vip=vip['id'])
            except:
                self.plugin.update_status(context, lb_db.Vip,
                                          vip['id'], constants.ERROR)
                LOG.debug(traceback.format_exc())
                raise a10_ex.VipUpdateError(vip=vip['id'])

    def delete_vip(self, context, vip):
        self.device_context(tenant_id=vip['tenant_id'])
        vs_name = vip['id']
        vs_delete_req = (request_struct_v2.virtual_server_object.call.
                         delete.toDict().items())
        try:
            if vip['session_persistence'] is not None:
                if vip['session_persistence']['type'] == "SOURCE_IP":
                    temp_name = "Type Source_IP named %s" % vip['id']
                    delete_per_temp = (request_struct_v2
                                       .SOURCE_IP_TEMP_OBJ.call.delete
                                       .toDict().items())
                elif vip['session_persistence']['type'] == 'HTTP_COOKIE':
                    delete_per_temp = (request_struct_v2
                                       .COOKIE_PER_TEMP_OBJ.call.delete
                                       .toDict().items())
                    temp_name = "Type COOKIE named %s" % vip['id']
                if (self.inspect_response(self.device.send(
                        tenant_id=vip['tenant_id'],
                        method=delete_per_temp[0][0],
                        url=delete_per_temp[0][1],
                        body={'name': vip['id']})) is not True):
                    msg = "Template %s will be orphaned." % temp_name
                    LOG.debug(_(msg))
        except:
            LOG.debug(_("No Virtual Server Port Present"))
        finally:
            try:
                if (self.inspect_response(self.device.send(
                        tenant_id=vip['tenant_id'],
                        method=vs_delete_req[0][0],
                        url=vs_delete_req[0][1],
                        body={'name': vs_name}))) is True:
                    self.plugin._delete_db_vip(context, vip['id'])
                else:
                    LOG.debug(traceback.format_exc())
                    self.plugin._delete_db_vip(context, vip['id'])
                    raise a10_ex.VipDeleteError(vip=vs_name)

            except:
                LOG.debug(traceback.format_exc())
                self.plugin.update_status(context, lb_db.Vip, vip['id'],
                                          constants.ERROR)
                raise a10_ex.VipDeleteError(vip=vs_name)

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
        except:
            self._failed(context, lb_db.Pool, pool['id'])
            LOG.debug(traceback.format_exc())
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
        except:
            self._failed(context, lb_db.Pool, pool['id'])
            LOG.debug(traceback.format_exc())
            raise a10_ex.SgUpdateError(sg=pool['id'])

    def delete_pool(self, context, pool):
        LOG.debug('delete_pool context=%s, pool=%s' % (context, pool))
        a10 = self._device_context(tenant_id=pool['tenant_id'])

        for members in pool['members']:
            self.delete_member(context, self.plugin.get_member(
                context, members))

        for hm in pool['health_monitors_status']:
            self.delete_pool_health_monitor(context, self.get_health_monitor(
                context, hm['monitor_id']), pool['id'])

        removed_a10 = False
        try:
            a10.service_group_delete(pool['id'])
            removed_a10 = True
            self.plugin._delete_db_pool(context, pool['id'])

        except:
            if removed_a10:
                raise a10_ex.SgDeleteError(sg="SG was REMOVED from ACOS "
                                           "entity but cloud not be removed "
                                           "from OS DB.")
            else:
                raise a10_ex.SgDeleteError(sg="SG was not REMOVED from an "
                                           "ACOS entity please contact your "
                                           "admin.")

        finally:
            if self.device.device_info['v_method'].lower() == 'adp':
                tpool = context._session.query(lb_db.Pool)
                n = tpool.filter_by(tenant_id=pool['tenant_id']).count()
                if n == 0:
                    try:
                        a10.partition_delete(tenant_id=pool['tenant_id'])
                    except:
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
        except:
            s = {
                "bytes_in": 0,
                "bytes_out": 0,
                "active_connections": 0,
                "total_connections": 0
            }
        return s

    def _get_member_ip(self, context, member):
        ip_address = member['address']
        if 'True' in self.device.device_info['use_float']:
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

        ip_address = self._get_member_ip(context, member)
        server_name = self._get_member_server_name(member, ip_address)

        try:
            if 'server' not in a10.server_get(server_name):
                a10.server_create(server_name, ip_address)
        except:
            LOG.debug(traceback.format_exc())
            self._failed(context, lb_db.Member, member["id"])
            raise a10_ex.MemberCreateError(member=server_name)

        try:
            status = 1
            if member["admin_state_up"] is False:
                status = 0

            a10.member_create(member['pool_id'], server_name,
                              member['protocol_port'], status)
            self._active(context, lb_db.Member, member["id"])
        except:
            LOG.debug(traceback.format_exc())
            self._failed(context, lb_db.Member, member["id"])
            raise a10_ex.MemberCreateError(member=server_name)

    def update_member(self, context, old_member, member):
        a10 = self._device_context(tenant_id=member['tenant_id'])

        ip_address = self._get_member_ip(context, member)
        server_name = self._get_member_server_name(member, ip_address)

        try:
            status = 1
            if member["admin_state_up"] is False:
                status = 0

            a10.member_update(member['pool_id'], server_name,
                              member['protocol_port'], status)
            self._active(context, lb_db.Member, member["id"])
        except:
            LOG.debug(traceback.format_exc())
            self._failed(context, lb_db.Member, member["id"])
            raise a10_ex.MemberUpdateError(member=server_name)

    def delete_member(self, context, member):
        a10 = self._device_context(tenant_id=member['tenant_id'])

        member_count = context._session.query(lb_db.Member).filter_by(
            tenant_id=member['tenant_id'],
            address=member['address']).count()

        ip_address = self._get_member_ip(context, member)
        server_name = self._get_member_server_name(member, ip_address)

        try:
            if member_count > 1:
                a10.member_delete(member['pool_id'], server_name,
                                  member['protocol_port'])
                self.plugin._delete_db_member(context, member['id'])
            else:
                a10.server_delete(server_name)
                self.plugin._delete_db_member(context, member['id'])
        except:
            LOG.debug(traceback.format_exc())
            self._failed(context, lb_db.Member, member["id"])
            raise a10_ex.MemberDeleteError(member=member["id"])

    def update_pool_health_monitor(self, context,
                                   old_health_monitor,
                                   health_monitor,
                                   pool_id):
        self.device_context(tenant_id=health_monitor['tenant_id'])
        if health_monitor['type'] == "TCP":
            hm_update_req = (request_struct_v2.TCP_HM_OBJ.call.update
                             .toDict().items())
            hm_obj = request_struct_v2.TCP_HM_OBJ.ds.toDict()
            hm_obj['name'] = health_monitor['id'][0:28]
            hm_obj['interval'] = health_monitor['delay']
            hm_obj['timeout'] = health_monitor['timeout']
            hm_obj['consec_pass_reqd'] = health_monitor['max_retries']

        elif health_monitor['type'] == "PING":
            hm_update_req = (request_struct_v2.HTTP_HM_OBJ.call.update
                             .toDict().items())
            hm_obj = request_struct_v2.ICMP_HM_OBJ.ds.toDict()
            hm_obj['name'] = health_monitor['id'][0:28]
            hm_obj['interval'] = health_monitor['delay']
            hm_obj['timeout'] = health_monitor['timeout']
            hm_obj['consec_pass_reqd'] = health_monitor['max_retries']

        elif health_monitor['type'] == "HTTP":
            hm_update_req = (request_struct_v2.HTTP_HM_OBJ.call.update
                             .toDict().items())
            hm_obj = request_struct_v2.HTTP_HM_OBJ.ds.toDict()
            hm_obj['name'] = health_monitor['id'][0:28]
            hm_obj['interval'] = health_monitor['delay']
            hm_obj['timeout'] = health_monitor['timeout']
            hm_obj['consec_pass_reqd'] = health_monitor['max_retries']
            url = "%s %s" % (
                health_monitor['http_method'], health_monitor["url_path"])
            hm_obj['http']['url'] = url
            hm_obj['http']['expect_code'] = health_monitor[
                'expected_codes']
        elif health_monitor['type'] == "HTTPS":
            hm_update_req = (request_struct_v2.HTTPS_HM_OBJ.call.update
                             .toDict().items())
            hm_obj = request_struct_v2.HTTPS_HM_OBJ.ds.toDict()
            hm_obj['name'] = health_monitor['id'][0:28]
            hm_obj['interval'] = health_monitor['delay']
            hm_obj['timeout'] = health_monitor['timeout']
            hm_obj['consec_pass_reqd'] = health_monitor['max_retries']
            url = "%s %s" % (health_monitor['http_method'],
                             health_monitor["url_path"])
            hm_obj['https']['url'] = url
            hm_obj['https']['expect_code'] = health_monitor['expected_codes']

        try:
            if (self.inspect_response(self.device.send(
                tenant_id=health_monitor['tenant_id'],
                method=hm_update_req[0][0],
                url=hm_update_req[0][1],
                body=hm_obj))
                    is True):
                self.plugin.update_pool_health_monitor(context,
                                                       health_monitor[
                                                           "id"],
                                                       pool_id,
                                                       constants.ACTIVE)
            else:
                raise a10_ex.HealthMonitorUpdateError(hm=hm_obj['name'])

        except:
            LOG.debug(traceback.format_exc())
            raise a10_ex.HealthMonitorUpdateError(hm=hm_obj['name'])

    def create_pool_health_monitor(self, context,
                                   health_monitor,
                                   pool_id):
        a10 = self._device_context(tenant_id=health_monitor['tenant_id'])
        if health_monitor['type'] == "TCP":
            hm_update_req = (request_struct_v2.TCP_HM_OBJ.call.create
                             .toDict().items())
            hm_obj = request_struct_v2.TCP_HM_OBJ.ds.toDict()
            hm_obj['name'] = health_monitor['id'][0:28]
            hm_obj['interval'] = health_monitor['delay']
            hm_obj['timeout'] = health_monitor['timeout']
            hm_obj['consec_pass_reqd'] = health_monitor['max_retries']
            send_hm = True
        elif health_monitor['type'] == "PING":
            hm_update_req = (request_struct_v2.ICMP_HM_OBJ.call.create
                             .toDict().items())
            hm_obj = request_struct_v2.ICMP_HM_OBJ.ds.toDict()
            hm_obj['name'] = health_monitor['id'][0:28]
            hm_obj['interval'] = health_monitor['delay']
            hm_obj['timeout'] = health_monitor['timeout']
            hm_obj['consec_pass_reqd'] = health_monitor['max_retries']

        elif health_monitor['type'] == "HTTP":
            hm_update_req = (request_struct_v2.HTTP_HM_OBJ.call.create
                             .toDict().items())
            hm_obj = request_struct_v2.HTTP_HM_OBJ.ds.toDict()
            hm_obj['name'] = health_monitor['id'][0:28]
            hm_obj['interval'] = health_monitor['delay']
            hm_obj['timeout'] = health_monitor['timeout']
            hm_obj['consec_pass_reqd'] = health_monitor['max_retries']
            url = "%s %s" % (
                health_monitor['http_method'], health_monitor["url_path"])
            hm_obj['http']['url'] = url
            hm_obj['http']['expect_code'] = health_monitor['expected_codes']

        elif health_monitor['type'] == "HTTPS":
            hm_update_req = (request_struct_v2.HTTPS_HM_OBJ.call.update
                             .toDict().items())
            hm_obj = request_struct_v2.HTTPS_HM_OBJ.ds.toDict()
            hm_obj['name'] = health_monitor['id'][0:28]
            hm_obj['interval'] = health_monitor['delay']
            hm_obj['timeout'] = health_monitor['timeout']
            hm_obj['consec_pass_reqd'] = health_monitor['max_retries']
            url = "%s %s" % (
                health_monitor['http_method'], health_monitor["url_path"])
            hm_obj['https']['url'] = url
            hm_obj['https']['expect_code'] = health_monitor['expected_codes']

        try:
            if (self.inspect_response(self.device.send(
                tenant_id=health_monitor['tenant_id'],
                method=hm_update_req[0][0],
                url=hm_update_req[0][1],
                body=hm_obj))
                    is True):
                sg_update_obj = (request_struct_v2
                                 .service_group_json_obj.
                                 call.update.toDict().items())
                for pool in health_monitor['pools']:
                    sg_obj = {
                        "service_group": {
                            "name": pool['pool_id'],
                            "health_monitor": hm_obj['name']
                        }
                    }
                    if (self.inspect_response(self.device.send(
                        tenant_id=health_monitor['tenant_id'],
                        method=sg_update_obj[0][0],
                        url=sg_update_obj[0][1],
                        body=sg_obj))
                            is not True):
                        self.plugin.update_pool_health_monitor(
                            context, health_monitor["id"], pool_id,
                            constants.ERROR)
                        raise a10_ex.HealthMonitorUpdateError(hm=pool[
                            'pool_id'])
                    else:
                        self.plugin.update_pool_health_monitor(context,
                                                               health_monitor[
                                                                   "id"],
                                                               pool_id,
                                                               constants
                                                               .ACTIVE)

            else:
                self.plugin.update_pool_health_monitor(context,
                                                       health_monitor[
                                                           "id"],
                                                       pool_id,
                                                       constants.ERROR)
                self.plugin._delete_db_pool_health_monitor(context,
                                                           health_monitor[
                                                               'id'],
                                                           pool_id)
                raise a10_ex.HealthMonitorUpdateError(hm=hm_obj['name'])

        except:
            LOG.debug(traceback.format_exc())
            self.plugin.update_pool_health_monitor(context,
                                                   health_monitor[
                                                       "id"],
                                                   pool_id,
                                                   constants.ERROR)
            self.plugin._delete_db_pool_health_monitor(context,
                                                       health_monitor[
                                                           'id'],
                                                       pool_id)
            raise a10_ex.HealthMonitorUpdateError(hm=hm_obj['name'])

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
        except:
            LOG.debug(traceback.format_exc())
            self._failed(context, health_monitor["id"], pool_id)
