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
from neutron.services.loadbalancer.plugin import LoadBalancerPlugin

from acos_client import A10Client


LOG = logging.getLogger(__name__)


class ThunderDriver(LoadBalancerPlugin):

    def __init__(self, plugin):
        self.plugin = plugin

    def device_context(self, tenant_id=""):
        self.device = A10Client(tenant_id=tenant_id)

    def inspect_response(self, response):
        LOG.debug("inspect_response: %s", response)
        if 'response' in response:
            # indicates configuration already exist continue processing.
            if response['response']['status'] == "OK":
                return True
            elif "src_ip_persistence_template" in response:
                return True
            elif "vport" in response:
                return True
            elif "virtual_server" in response:
                return True
            elif "service_group" in response:
                return True
            elif "server" in response:
                return True
            elif "health_monitor" in response:
                return True
            elif 67239937 == response['response']['err']['code']:
                return True
            elif 67305473 == response['response']['err']['code']:
                return False
            elif 2941 == response['response']['err']['code']:
                return True
            elif 'such' in response:
                LOG.debug('FOUND SUCH IN RESPONSE')
                return True
            else:
                return False

        return False

    def persistence_create(self, vip):
        self.device_context(tenant_id=vip['tenant_id'])
        if vip['session_persistence'] is not None:
            temp_name = vip['id']
            if vip['session_persistence']['type'] == "SOURCE_IP":
                # Search to see if the template already exist.
                req = (request_struct_v2.SOURCE_IP_TEMP_OBJ.call.search
                       .toDict().items())
                try:
                    res = self.inspect_response(
                        self.device.send(tenant_id=vip['tenant_id'],
                                         method=req[0][0],
                                         url=req[0][1],
                                         body={"name": temp_name}))
                except:
                    LOG.debug(traceback.format_exc())
                    raise a10_ex.SearchError(term="SRC_IP_PER_TEMP")

                if res is not True:
                    src_ip_obj = (request_struct_v2.SOURCE_IP_TEMP_OBJ.ds
                                  .toDict())
                    src_ip_obj["src_ip_persistence_template"]['name'] = (
                        temp_name)
                    src_req = (request_struct_v2.SOURCE_IP_TEMP_OBJ.call
                               .create.toDict().items())
                    try:
                        src_res = (self.inspect_response(self.device.send(
                            tenant_id=vip['tenant_id'],
                            method=src_req[0][0],
                            url=src_req[0][1],
                            body={"name": temp_name})))
                    except:
                        LOG.debug(traceback.format_exc())
                        raise a10_ex.TemplateCreateError(template=temp_name)

                    if src_res is True:
                        return temp_name

                elif res is True:
                    return temp_name
                else:
                    return None

            elif vip['session_persistence']['type'] == 'HTTP_COOKIE':
                req = (request_struct_v2.COOKIE_PER_TEMP_OBJ.call.search
                       .toDict().items())
                try:
                    res = self.inspect_response(
                        self.device.send(
                            tenant_id=vip['tenant_id'],
                            method=req[0][0],
                            url=req[0][1],
                            body={"name": temp_name}))
                except:
                    LOG.debug(traceback.format_exc())
                    raise a10_ex.SearchError(term="COOKIE_PER_TEMP")

                if res is not True:
                    cookie_ip_obj = (request_struct_v2.COOKIE_PER_TEMP_OBJ
                                     .ds.toDict())
                    cookie_ip_obj["cookie_persistence_template"]['name'] = (
                        temp_name)
                    src_req = (request_struct_v2.COOKIE_PER_TEMP_OBJ
                               .call.create.toDict().items())
                    try:
                        src_res = (self.inspect_response(
                            self.device.send(tenant_id=vip['tenant_id'],
                                             method=src_req[0][0],
                                             url=src_req[0][1],
                                             body={"name": temp_name})))
                    except:
                        LOG.debug(traceback.format_exc())
                        raise a10_ex.TemplateCreateError(
                            template=temp_name)

                    if src_res is True:
                        return temp_name
                elif res is True:
                    return temp_name
                else:
                    return None

            elif vip['session_persistence']['type'] == "APP_COOKIE":
                LOG.debug(traceback.format_exc())
                raise a10_ex.UnsupportedFeatureAppCookie()
        else:
            return None

    def create_vip(self, context, vip):
        """
        Contruct the Device Context First.
        """
        self.device_context(tenant_id=vip['tenant_id'])
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
            vport_obj['source_nat'] = 'auto'
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
            vport_update_req = (request_struct_v2.vport_HTTP_obj.call.update
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
        self.device_context(tenant_id=pool['tenant_id'])
        pool_create_req = (request_struct_v2.service_group_json_obj.call
                           .create.toDict().items())
        pool_search_req = (request_struct_v2.service_group_json_obj.call
                           .search.toDict().items())
        pool_ds = (request_struct_v2.service_group_json_obj.ds
                   .toDict())
        try:

            if (self.inspect_response(self.device.send(
                    tenant_id=pool['tenant_id'],
                    method=pool_search_req[0][0],
                    url=pool_search_req[0][1],
                    body={'name': pool['id']}))) is False:
                pool_ds['service_group']['name'] = pool['id']
                pool_ds['service_group']['protocol'] = "2"
                if pool['lb_method'] == "ROUND_ROBIN":
                    pool_ds['service_group']['lb_method'] = "0"
                elif pool['lb_method'] == "LEAST_CONNECTIONS":
                    pool_ds['service_group']['lb_method'] = "2"
                else:
                    pool_ds['service_group']['lb_method'] = "3"

            if (self.inspect_response(self.device.send(
                    tenant_id=pool['tenant_id'],
                    method=pool_create_req[0][0],
                    url=pool_create_req[0][1],
                    body=pool_ds))) is True:
                self.plugin.update_status(context, lb_db.Pool,
                                          pool['id'], constants.ACTIVE)
            else:
                LOG.debug(traceback.format_exc())
                self.plugin.update_status(context, lb_db.Pool,
                                          pool['id'], constants.ERROR)
                raise a10_ex.SgCreateError(sg=pool['id'])

        except:
            LOG.debug(traceback.format_exc())
            self.plugin.update_status(context, lb_db.Pool,
                                      pool['id'], constants.ERROR)
            raise a10_ex.SgCreateError(sg=pool['id'])

    def update_pool(self, context, old_pool, pool):
        self.device_context(tenant_id=pool['tenant_id'])
        pool_update_req = (request_struct_v2.service_group_json_obj.call
                           .update.toDict().items())
        pool_search_req = (request_struct_v2.service_group_json_obj.call
                           .search.toDict().items())
        try:
            pool_ds = self.device.send(
                tenant_id=pool['tenant_id'],
                method=pool_search_req[0][0],
                url=pool_search_req[0][1],
                body={'name': pool['id']})
            if "service_group" in pool_ds:
                pool_ds['service_group']['name'] = pool['id']
                pool_ds['service_group']['protocol'] = "2"
                if pool['lb_method'] == "ROUND_ROBIN":
                    pool_ds['service_group']['lb_method'] = "0"
                elif pool['lb_method'] == "LEAST_CONNECTIONS":
                    pool_ds['service_group']['lb_method'] = "2"
                else:
                    pool_ds['service_group']['lb_method'] = "3"
            if (self.inspect_response(self.device.send(
                    tenant_id=pool['tenant_id'],
                    method=pool_update_req[0][0],
                    url=pool_update_req[0][1],
                    body=pool_ds))) is True:
                self.plugin.update_status(context, lb_db.Pool,
                                          pool['id'], constants.ACTIVE)
            else:
                LOG.debug(traceback.format_exc())
                self.plugin.update_status(context, lb_db.Pool,
                                          pool['id'], constants.ERROR)
                raise a10_ex.SgUpdateError(sg=pool['id'])

        except:
            LOG.debug(traceback.format_exc())
            self.plugin.update_status(context, lb_db.Pool,
                                      pool['id'], constants.ERROR)
            raise a10_ex.SgUpdateError(sg=pool['id'])

    def delete_pool(self, context, pool):
        LOG.debug('delete_pool context=%s, pool=%s' % (context, pool))
        self.device_context(tenant_id=pool['tenant_id'])
        for members in pool['members']:
            self.delete_member(context, self.plugin.get_member(
                context, members))
        for hm in pool['health_monitors_status']:
            self.delete_pool_health_monitor(context, self.get_health_monitor(
                context, hm['monitor_id']), pool['id'])
        pool_delete_req = (request_struct_v2.service_group_json_obj.call
                           .delete.toDict().items())
        try:
            if (self.inspect_response(self.device.send(
                    tenant_id=pool['tenant_id'],
                    method=pool_delete_req[0][0],
                    url=pool_delete_req[0][1],
                    body={'name': pool['id']}))) is True:
                try:
                    self.plugin._delete_db_pool(context, pool['id'])

                except:
                    self.plugin._delete_db_pool(context, pool['id'])
                    raise a10_ex.SgDeleteError(sg="SG was REMOVED "
                                               "from ACOS entity "
                                               "but cloud not be removed"
                                               "from OS DB.")
            else:
                self.plugin._delete_db_pool(context, pool['id'])
                raise a10_ex.SgDeleteError(sg="SG was not REMOVED "
                                           "from an ACOS entity "
                                           "please contact your "
                                           "administrator."
                                           )
        except:
            LOG.debug(traceback.format_exc())
            # self.plugin._delete_db_pool(context, pool['id'])
            raise a10_ex.SgDeleteError(sg=pool['id'])

        finally:

            if self.device.device_info['v_method'].lower() == 'adp':
                tpool = context._session.query(lb_db.Pool)
                n = tpool.filter_by(tenant_id=pool['tenant_id']).count()
                if n == 0:
                    try:
                        if (self.inspect_response(
                                self.device.partition_delete(
                                    tenant_id=pool['tenant_id'])
                        ) is not True):
                            raise a10_ex.ParitionDeleteError(
                                partition=pool['tenant_id'][0:13])
                    except:
                        raise a10_ex.ParitionDeleteError(
                            partition=pool['tenant_id'][0:13])

    def stats(self, context, pool_id):
        pool_qry = context._session.query(lb_db.Pool).filter_by(
            id=pool_id)
        vip_id = pool_qry.vip_id
        self.device_context(tenant_id=pool_qry.tenant_id)

        stats_req = (request_struct_v2.virtual_server_object.call
                     .fetchstatistics
                     .toDict().items().items())
        try:
            stats_res = (self.device.send(tenant_id=pool_qry.tenant_id,
                                          method=stats_req[0][0],
                                          url=stats_req[0][1],
                                          body={"name": vip_id}))
            if "virtual_server_stat" in stats_res:
                return {
                    "bytes_in": stats_res["virtual_server_stat"]["req_bytes"],
                    "bytes_out": stats_res["virtual_server_stat"][
                        "resp_bytes"],
                    "active_connections": stats_res["virtual_server_stat"][
                        "cur_conns"],
                    "total_connections": stats_res["virtual_server_stat"][
                        "tot_conns"]}

            else:
                return {"bytes_in": 0,
                        "bytes_out": 0,
                        "active_connections": 0,
                        "total_connections": 0}
        except:
            return {"bytes_in": 0,
                    "bytes_out": 0,
                    "active_connections": 0,
                    "total_connections": 0}

    def create_member(self, context, member):
        self.device_context(tenant_id=member['tenant_id'])
        member_create_req = (request_struct_v2.service_group_member_obj
                             .call.create.toDict().items())
        member_ds = (request_struct_v2.service_group_member_obj
                     .ds.toDict())
        server_create_req = (request_struct_v2.server_json_obj.call.create
                             .toDict().items())
        server_search_req = (request_struct_v2.server_json_obj.call.search
                             .toDict().items())
        server_ds = (request_struct_v2.server_json_obj.ds.toDict())
        member_ds['address'] = member['address']
        if 'True' in self.device.device_info['use_float']:
            fip_qry = context.session.query(l3_db.FloatingIP)
            if (fip_qry.filter_by(fixed_ip_address=member['address']).count()
                    > 0):
                float_address = fip_qry.filter_by(
                    fixed_ip_address=member['address']).first()
                member_ds['address'] = str(float_address.floating_ip_address)

        server_name = "_%s_%s_neutron" % (member['tenant_id'][:5],
                                          str(member_ds['address']).replace(
            ".", "_", 4))
        try:
            if 'server' not in self.device.send(
                    tenant_id=member['tenant_id'],
                    method=server_search_req[0][0],
                    url=server_search_req[0][1],
                    body={'name': server_name}):

                server_ds['server']['name'] = server_name
                server_ds['server']['host'] = member_ds['address']
                if (self.inspect_response(self.device.send(
                        tenant_id=member['tenant_id'],
                        method=server_create_req[0][0],
                        url=server_create_req[0][1],
                        body=server_ds)) is not True):
                    self.plugin.update_status(context, lb_db.Member,
                                              member["id"],
                                              constants.ERROR)
                    raise a10_ex.MemberCreateError(member=server_name)
        except:
            LOG.debug(traceback.format_exc())
            self.plugin.update_status(context, lb_db.Member,
                                      member["id"],
                                      constants.ERROR)
            raise a10_ex.MemberCreateError(member=server_name)

        finally:
            member_ds['name'] = member['pool_id']
            member_ds['member']['server'] = server_name
            member_ds['member']['port'] = member['protocol_port']

            if member["admin_state_up"] is False:
                member_ds['member']['status'] = 0

            try:
                if (self.inspect_response(self.device.send(
                        tenant_id=member['tenant_id'],
                        method=member_create_req[0][0],
                        url=member_create_req[0][1],
                        body=member_ds)) is True):
                    self.plugin.update_status(context, lb_db.Member, member[
                        "id"], constants.ACTIVE)
                else:
                    self.plugin.update_status(context, lb_db.Member,
                                              member["id"],
                                              constants.ERROR)
            except:
                LOG.debug(traceback.format_exc())
                self.plugin.update_status(context, lb_db.Member, member["id"],
                                          constants.ERROR)

    def update_member(self, context, old_member, member):
        self.device_context(tenant_id=member['tenant_id'])
        member_update_req = (request_struct_v2.service_group_member_obj
                             .call.update.toDict().items())
        member_ds = (request_struct_v2.service_group_member_obj
                     .ds.toDict())
        member_ds['address'] = member['address']
        if 'True' in self.device.device_info['use_float']:
            fip_qry = context.session.query(l3_db.FloatingIP)
            if (fip_qry.filter_by(fixed_ip_address=member['address']).count()
                    > 0):
                float_address = fip_qry.filter_by(
                    fixed_ip_address=member['address']).first()
                member_ds['address'] = str(float_address.floating_ip_address)

        server_name = "_%s_%s_neutron" % (member['tenant_id'][:5],
                                          str(member_ds['address']).replace(
            ".", "_", 4))
        try:
            member_ds['name'] = member['pool_id']
            member_ds['member']['server'] = server_name
            member_ds['member']['port'] = member['protocol_port']

            if member["admin_state_up"] is False:
                member_ds['member']['status'] = 0
            if (self.inspect_response(self.device.send(
                    tenant_id=member['tenant_id'],
                    method=member_update_req[0][0],
                    url=member_update_req[0][1],
                    body=member_ds)) is True):
                self.plugin.update_status(context, lb_db.Member, member[
                    "id"], constants.ACTIVE)
            else:
                self.plugin.update_status(context, lb_db.Member,
                                          member["id"],
                                          constants.ERROR)
        except:
            LOG.debug(traceback.format_exc())
            self.plugin.update_status(context, lb_db.Member,
                                      member["id"],
                                      constants.ERROR)
            raise a10_ex.MemberUpdateError(member=server_name)

    def delete_member(self, context, member):
        self.device_context(tenant_id=member['tenant_id'])
        member_delete_req = (request_struct_v2.service_group_member_obj
                             .call.delete.toDict().items())
        member_ds = (request_struct_v2.service_group_member_obj
                     .ds.toDict())
        server_delete_req = (request_struct_v2.server_json_obj.call.delete
                             .toDict().items())
        server_ds = (request_struct_v2.server_json_obj.ds.toDict())

        member_count = context._session.query(lb_db.Member).filter_by(
            tenant_id=member['tenant_id'],
            address=member['address']).count()

        if 'True' in self.device.device_info['use_float']:
            fip_qry = context.session.query(l3_db.FloatingIP)
            float_address = fip_qry.filter_by(
                fixed_ip_address=member['address']).first()
            if float_address is not None:
                if float_address.floating_ip_address is not None:
                    member_ds['address'] = str(float_address.
                                               floating_ip_address)
                else:
                    member_ds['address'] = member['address']
            else:
                member_ds['address'] = member['address']

        server_name = "_%s_%s_neutron" % (member['tenant_id'][:5],
                                          str(member_ds['address']).replace(
            ".", "_", 4))
        try:
            if member_count > 1:
                if (self.inspect_response(self.device.send(
                    tenant_id=member['tenant_id'],
                    method=member_delete_req[0][0],
                    url=member_delete_req[0][1],
                    body={"name": member['pool_id'], "member": {
                        "server": server_name, "port": member[
                            'protocol_port']}}))
                        is True):
                    self.plugin._delete_db_member(context, member['id'])
                else:
                    self.plugin.update_status(context, lb_db.Member,
                                              member["id"],
                                              constants.ERROR)
            else:
                if (self.inspect_response(self.device.send(
                    tenant_id=member['tenant_id'],
                    method=server_delete_req[0][0],
                    url=server_delete_req[0][1],
                    body={"server": {"name": server_name}}))
                        is True):
                    self.plugin._delete_db_member(context, member['id'])

                else:
                    self.plugin.update_status(context, lb_db.Member,
                                              member["id"],

                                              constants.ERROR)
        except:
            LOG.debug(traceback.format_exc())
            self.plugin.update_status(context, lb_db.Member, member["id"],
                                      constants.ERROR)
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
            url = "%s  %s" % (
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
            url = "%s  %s" % (health_monitor['http_method'],
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
        self.device_context(tenant_id=health_monitor['tenant_id'])
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
                    sg_obj = {"service_group": {"name": pool['pool_id'],
                                                "health_monitor": hm_obj[
                        'name']}}
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
        self.device_context(tenant_id=health_monitor['tenant_id'])
        sg_obj = {"service_group": {"name": pool_id, "health_monitor": ""}}
        sg_update_req = (request_struct_v2.service_group_json_obj.call.update
                         .toDict().items())
        try:
            if (self.inspect_response(self.device.send(
                tenant_id=health_monitor['tenant_id'],
                method=sg_update_req[0][0],
                url=sg_update_req[0][1],
                body=sg_obj))
                    is True):

                hm_binding_qty = (context.session.query(
                    lb_db.PoolMonitorAssociation
                ).filter_by(monitor_id=health_monitor['id']).join(lb_db.Pool)
                    .count())
                if hm_binding_qty == 1:
                    hm_del_req = (request_struct_v2.HTTP_HM_OBJ.
                                  call.delete.toDict().items())
                    if (self.inspect_response(self.device.send(
                        tenant_id=health_monitor['tenant_id'],
                        method=hm_del_req[0][0],
                        url=hm_del_req[0][1],
                        body={"name": health_monitor['id'][0:28]}))
                            is True):
                        self.plugin._delete_db_pool_health_monitor(
                            context, health_monitor['id'], pool_id)
                else:
                    self.plugin._delete_db_pool_health_monitor(context,
                                                               health_monitor[
                                                                   'id'],
                                                               pool_id)
        except:
            LOG.debug(traceback.format_exc())
            self.plugin.update_pool_health_monitor(context,
                                                   health_monitor["id"],
                                                   pool_id,
                                                   constants.ERROR)
