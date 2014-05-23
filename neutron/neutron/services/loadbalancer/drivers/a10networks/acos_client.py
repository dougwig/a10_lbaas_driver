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

"""
This file is specifically for managing the API connection to
"""

import hashlib
import json
import re
import ssl
import traceback
import urllib3

import request_struct_v2
import a10_exceptions as a10_ex

from ConfigParser import ConfigParser
from neutron.openstack.common import log as logging

# Neutron logs
LOG = logging.getLogger(__name__)


class A10Client():

    def __init__(self, config, tenant_id="", dev_info=None,
                 version_check=False):
        self.config = config
        self.tenant_id = tenant_id

        self.device_info = dev_info or self.select_device(tenant_id=tenant_id)
        self.set_base_url()

        LOG.debug("A10Client init: connecting %s", self.base_url)

        self.force_tlsv1 = False

        self.session_id = None
        self.get_session_id()
        if self.session_id is None:
            msg = _("A10Client: unable to get session_id from ax")
            LOG.error(msg)
            raise a10_ex.A10ThunderNoSession()

        if version_check:
            self.check_version()

        LOG.debug("A10Client init: connected, session_id=%s", self.session_id)

    def set_base_url(self):
        protocol = "https"
        host = ""
        port = "443"

        if "protocol" in self.device_info:
            protocol = self.device_info['protocol']
        elif port == "80":
            protocol = "http"

        host = self.device_info['host']

        if "port" in self.device_info:
            port = self.device_info['port']

        port = int(port)

        self.base_url = "%s://%s:%d" % (protocol, host, port)

    def axapi_http(self, method, api_url, params={}):
        if self.force_tlsv1:
            http = urllib3.PoolManager(ssl_version=ssl.PROTOCOL_TLSv1,
                                       cert_reqs='CERT_NONE',
                                       assert_hostname=False)
        else:
            http = urllib3.PoolManager()

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OS-LBaaS-AGENT"
        }

        LOG.debug("axapi_http: start")
        LOG.debug("axapi_http: url = %s", api_url)
        LOG.debug("axapi_http: params = %s", params)

        url = self.base_url + api_url
        if params:
            payload = json.dumps(params, encoding='utf-8')
        else:
            payload = None

        r = http.urlopen(method, url, body=payload, headers=headers)

        LOG.debug("axapi_http: data = %s", r.data)

        xmlok = ('<?xml version="1.0" encoding="utf-8" ?>'
                 '<response status="ok"></response>')
        if r.data == xmlok:
            return {'response': {'status': 'OK'}}

        return json.loads(r.data)

    def get_session_id(self):
        auth_url = "/services/rest/v2.1/?format=json&method=authenticate"
        params = {
            "username": self.device_info['username'],
            "password": self.device_info['password']
        }

        try:
            r = self.axapi_http("POST", auth_url, params)
            self.session_id = r['session_id']

        except Exception, e:
            tlsv1_error = "SSL23_GET_SERVER_HELLO:tlsv1 alert protocol version"
            if self.force_tlsv1 is False and str(e).find(tlsv1_error) >= 0:
                # workaround ssl version
                self.force_tlsv1 = True
                self.get_session_id()
            else:
                LOG.debug("get_session_id failed: %s", e)
                LOG.debug(traceback.format_exc())
                self.session_id = None

    def check_version(self):
        if 'skip_version_check' in self.device_info:
            if self.device_info['skip_version_check']:
                return

        info_url = ("/services/rest/v2.1/?format=json&session_id=%s"
                    "&method=system.information.get" % self.session_id)

        r = self.axapi_http("GET", info_url)

        x = r['system_information']['software_version'].split('.')
        major = int(x[0])
        minor = int(x[1])
        dot = 0
        m = re.match("^(\d+)", x[2])
        if m is not None:
            dot = int(m.group(1))

        if major < 2 or minor < 7 or dot < 2:
            LOG.error(_("A10Client: driver requires ACOS version 2.7.2+"))
            raise a10_ex.A10ThunderVersionMismatch()

    def partition(self, tenant_id=""):
        if self.device_info['v_method'].lower() == 'adp':
            try:
                p_search = self.partition_search(tenant_id=tenant_id)
                if p_search is True:
                    try:
                        self.partition_active(tenant_id=tenant_id)
                    except:
                        raise a10_ex.PartitionActiveError(
                            partition=tenant_id[0:13])
                else:
                    try:
                        self.partition_create(tenant_id=tenant_id)
                    except:
                        raise a10_ex.PartitionCreateError(
                            partition=tenant_id[0:13])
                    finally:
                        try:
                            self.partition_active(tenant_id=tenant_id)
                        except:
                            raise a10_ex.PartitionActiveError(
                                partition=tenant_id[0:13])
            except:
                raise a10_ex.SearchError(term="Partition Discovery for %s"
                                         % tenant_id[0:13])

    def send(self, tenant_id="", method="", url="", body={},
             close_session_after_request=True,
             partition_ax=True):
        if self.session_id is None:
            self.get_session_id()
        if partition_ax:
            self.partition(tenant_id=tenant_id)

        if url.find('%') >= 0 and self.session_id is not None:
            url = url % self.session_id

        r = self.axapi_http(method, url, body)

        if close_session_after_request:
            LOG.debug("about to close session after req")
            self.close_session(tenant_id=tenant_id)
            LOG.debug("session closed")

        return r

    def close_session(self, tenant_id=""):
        response = self.partition_active(tenant_id=tenant_id, default=True)
        if "response" in response:
            if 'status' in response['response']:
                if response['response']['status'] == "OK":
                    url = ("/services/rest/v2.1/?format=json&method=session"
                           ".close&session_id=%s" % self.session_id)

                    results = self.axapi_http("POST", url,
                                              {"session_id": self.session_id})

                    if results['response']['status'] == "OK":
                        self.session_id = None

    def write_memory(self, tenant_id=""):
        return self.send(tenant_id=tenant_id,
                         method="GET",
                         url=(
                             "/services/rest/v2.1/?format=json&method=system"
                             ".action"
                             ".write_memory&session_id=%s" % self.session_id),
                         partition_ax=False,
                         close_session_after_request=False)

    def partition_search(self, tenant_id=""):
        req_info = (request_struct_v2.PARTITION_OBJ.call.search.toDict()
                    .items())
        response = self.send(tenant_id=tenant_id, method=req_info[0][0],
                             url=req_info[0][1] % self.session_id,
                             body={"name": self.tenant_id[0:13]},
                             partition_ax=False,
                             close_session_after_request=False)
        if 'response' in response:
            if "err" in response['response']:
                if response['response']['err'] == 520749062:
                    return False
        elif "partition" in response:
            return True

    def partition_create(self, tenant_id=""):
        req_info = (request_struct_v2.PARTITION_OBJ.call.create.toDict()
                    .items())
        obj = request_struct_v2.PARTITION_OBJ.ds.toDict()
        obj['partition']['name'] = tenant_id[0:13]
        return self.send(tenant_id=tenant_id, method=req_info[0][0],
                         url=req_info[0][1] % self.session_id,
                         body=obj,
                         partition_ax=False,
                         close_session_after_request=False)

    def partition_delete(self, tenant_id=""):
        req_info = (request_struct_v2.PARTITION_OBJ.call.delete.toDict()
                    .items())
        self.close_session(tenant_id=self.tenant_id)
        self.get_session_id()
        r = self.send(tenant_id=tenant_id, method=req_info[0][0],
                      url=req_info[0][1] % self.session_id,
                      body={"name": self.tenant_id[0:13]},
                      partition_ax=False)
        if self.inspect_response(r) is not True:
            raise a10_ex.ParitionDeleteError(partition=tenant_id[0:13])

    def partition_active(self, tenant_id="", default=False):
        req_info = (request_struct_v2.PARTITION_OBJ.call.active.toDict()
                    .items())
        if default is True:
            name = "shared"
        else:
            name = tenant_id[0:13]
        return self.send(tenant_id=tenant_id, method=req_info[0][0],
                         url=req_info[0][1] % self.session_id,
                         body={"name": name},
                         partition_ax=False,
                         close_session_after_request=False)

    def select_device(self, tenant_id=""):
        nodes = 256
        # node_prefix = "a10"
        node_list = []
        x = 0
        while x < nodes:
            node_list.insert(x, (x, []))
            x += 1
        z = 0
        key_list = self.config.devices.keys()
        LOG.debug("THIS IS THE KEY LIST %s", key_list)
        while z < nodes:
            for key in key_list:
                key_index = int(hashlib.sha256(key).hexdigest(), 16)
                result = key_index % nodes

                if result == nodes:
                    result = 0
                else:
                    result = result + 1
                node_list[result][1].insert(result, self.config.devices[key])

            z += 1
        tenant_hash = int(hashlib.sha256(tenant_id).hexdigest(), 16)
        limit = 256
        th = tenant_hash
        for i in range(0, limit):
            # LOG.debug("NODE_LENGTH------> %d", len(node_list[th % nodes][1]))
            if len(node_list[th % nodes][1]) > 0:
                node_tenant_mod = tenant_hash % len(node_list[th % nodes][1])
                LOG.debug("node_tenant_mod---> %s", node_tenant_mod)
                device_info = node_list[th % nodes][1][node_tenant_mod]
                LOG.debug("DEVICE_INFO----> %s", device_info['host'])
                device_info['tenant_id'] = tenant_id
                break
            th = th + 1
        return device_info

    def inspect_response(self, response, func=None):
        LOG.debug("inspect_response: %s", response)
        if 'response' in response:
            true_in = [
                "src_ip_persistence_template",
                "vport",
                "virtual_server",
                "service_group",
                "server",
                "health_monitor"
            ]
            not_found = [
                33619968,
                67305473,
                1023
            ]
            magic_codes_good = [
                67239937,
                2941
            ]
            if 'err' in response['response']:
                c = response['response']['err']['code']

            # indicates configuration already exist continue processing.
            if response['response']['status'] == "OK":
                return True
            elif any([x in response for x in true_in]):
                return True
            elif any([x for x in not_found if x == c]):
                if func is 'delete':
                    # delete and 'not found', be silent
                    return True
                else:
                    return False
            elif any([x for x in magic_codes_good if x == c]):
                return True
            elif 'such' in response:
                LOG.debug('FOUND SUCH IN RESPONSE')
                return True
            else:
                return False

        return False

    def persistence_exists(self, persist_type, name):
        if persist_type == 'SOURCE_IP':
            req = (request_struct_v2.SOURCE_IP_TEMP_OBJ.call.search
                   .toDict().items())
        elif persist_type == 'HTTP_COOKIE':
            req = (request_struct_v2.COOKIE_PER_TEMP_OBJ.call.search
                   .toDict().items())
        else:
            raise a10_ex.TemplateCreateError(template=name)

        r = self.send(tenant_id=self.tenant_id,
                      method=req[0][0],
                      url=req[0][1],
                      body={"name": name})
        return self.inspect_response(r)

    def persistence_create(self, persist_type, name):
        if persist_type == 'SOURCE_IP':
            args = request_struct_v2.SOURCE_IP_TEMP_OBJ.ds.toDict()
            args["src_ip_persistence_template"]['name'] = name
            req = (request_struct_v2.SOURCE_IP_TEMP_OBJ.call
                   .create.toDict().items())
        elif persist_type == 'HTTP_COOKIE':
            args = request_struct_v2.COOKIE_PER_TEMP_OBJ.ds.toDict()
            args["cookie_persistence_template"]['name'] = name
            req = (request_struct_v2.COOKIE_PER_TEMP_OBJ
                   .call.create.toDict().items())
        else:
            raise a10_ex.TemplateCreateError(template=name)

        r = self.send(tenant_id=self.tenant_id,
                      method=req[0][0],
                      url=req[0][1],
                      body=args)

        if self.inspect_response(r) is not True:
            raise a10_ex.TemplateCreateError(template=name)

    def persistence_delete(self, persist_type, name):
        if persist_type == "SOURCE_IP":
            delete_per_temp = (request_struct_v2
                               .SOURCE_IP_TEMP_OBJ.call.delete
                               .toDict().items())
        elif persist_type == 'HTTP_COOKIE':
            delete_per_temp = (request_struct_v2
                               .COOKIE_PER_TEMP_OBJ.call.delete
                               .toDict().items())
        else:
            LOG.debug("Unknown persistence type passed to delete: %s",
                      persist_type)
            return None

        r = self.send(tenant_id=self.tenant_id,
                      method=delete_per_temp[0][0],
                      url=delete_per_temp[0][1],
                      body={'name': name})
        if self.inspect_response(r) is not True:
            LOG.debug("Tempalte %s will be orphaned", name)

    def virtual_server_get(self, name):
        service_group_search_req = (request_struct_v2.service_group_json_obj
                                    .call.search.toDict().items())

        r = self.send(tenant_id=self.tenant_id,
                      method=service_group_search_req[0][0],
                      url=service_group_search_req[0][1],
                      body={'name': name})
        return r

    def virtual_server_create(self, name, ip_address, protocol, port,
                              service_group_id,
                              s_pers=None,
                              c_pers=None,
                              status=1):

        create_vip_req = (request_struct_v2.virtual_server_object.call
                          .create.toDict().items())
        vs = request_struct_v2.virtual_server_object.ds.toDict()

        vs['virtual_server']['address'] = ip_address
        vs['virtual_server']['name'] = name
        vs['virtual_server']['status'] = status

        if protocol == "HTTP":
            vport_obj = request_struct_v2.vport_HTTP_obj.ds.toDict()
        else:
            vport_obj = request_struct_v2.vport_TCP_obj.ds.toDict()

        vport_obj['service_group'] = service_group_id
        vport_obj['port'] = port
        vport_obj['name'] = name + "_VPORT"

        if s_pers is not None:
            vport_obj['source_ip_persistence_template'] = s_pers
        else:
            vport_obj['source_ip_persistence_template'] = ""

        if c_pers is not None:
            vport_obj['cookie_persistence_template'] = c_pers
        else:
            vport_obj['cookie_persistence_template'] = ""

        if self.device_info['autosnat']:
            vport_obj['source_nat_auto'] = 1
        vs['vport_list'] = [vport_obj]

        r = self.send(tenant_id=self.tenant_id,
                      method=create_vip_req[0][0],
                      url=create_vip_req[0][1],
                      body=vs)

        if self.inspect_response(r) is not True:
            raise a10_ex.VipCreateError(vip=name)

    def virtual_port_get(self, name, protocol):
        vport_name = name + "_VPORT"
        if protocol is "HTTP":
            vport_obj_req = (request_struct_v2.vport_HTTP_obj.call.search
                             .toDict().items())
        else:
            vport_obj_req = (request_struct_v2.vport_TCP_obj.call
                             .search.toDict().items())

        r = self.send(tenant_id=self.tenant_id,
                      method=vport_obj_req[0][0],
                      url=vport_obj_req[0][1],
                      body={"name": vport_name})
        return r

    def virtual_port_update(self, name, protocol, service_group_id,
                            source_ip_persistence_template=None,
                            cookie_persistence_template=None,
                            status=1):
        vport_name = vip['id'] + "_VPORT"
        if vip['protocol'] is "HTTP":
            vport_update_req = (request_struct_v2.vport_HTTP_obj.call.update
                                .toDict().items())
        else:
            vport_update_req = (request_struct_v2.vport_TCP_obj.call.update
                                .toDict().items())

        # First, grab the current port config
        vport_res = self.virtual_port_get(name, protocol)
        if 'virtual_service' not in vport_res:
            raise a10_ex.SearchError(term="vPort Object %s" % name)

        # Now apply the changes
        if s_pers is not None:
            vport_obj['source_ip_persistence_template'] = s_pers
        elif c_pers is not None:
            vport_obj['cookie_persistence_template'] = c_pers

        vport_res['service_group'] = service_group_id
        vport_res['status'] = status

        # Write the changes to the port
        r = self.send(tenant_id=self.tenant_id,
                      method=vport_update_req[0][0],
                      url=vport_update_req[0][1],
                      body=vport_res)

        if self.inspect_response(r) is not True:
            raise a10_ex.VipUpdateError(vip=name)

    def virtual_server_delete(self, name):
        vs_delete_req = (request_struct_v2.virtual_server_object.call.
                         delete.toDict().items())

        r = self.send(tenant_id=self.tenant_id,
                      method=vs_delete_req[0][0],
                      url=vs_delete_req[0][1],
                      body={'name': name})
        if self.inspect_response(r) is not True:
            raise a10_ex.VipDeleteError(vip=name)

    def service_group_get(self, name):
        pool_search_req = (request_struct_v2.service_group_json_obj.call
                           .search.toDict().items())

        return self.send(tenant_id=self.tenant_id,
                         method=pool_search_req[0][0],
                         url=pool_search_req[0][1],
                         body={'name': name})

    def service_group_create(self, name, lb_method='3'):
        pool_create_req = (request_struct_v2.service_group_json_obj.call
                           .create.toDict().items())

        pool_ds = (request_struct_v2.service_group_json_obj.ds.toDict())
        pool_ds['service_group']['protocol'] = "2"
        pool_ds['service_group']['name'] = name
        pool_ds['service_group']['lb_method'] = lb_method

        r = self.send(tenant_id=self.tenant_id,
                      method=pool_create_req[0][0],
                      url=pool_create_req[0][1],
                      body=pool_ds)

        if self.inspect_response(r) is not True:
            raise a10_ex.SgCreateError(sg=name)

    def service_group_update(self, name, lb_method='3'):
        pool_update_req = (request_struct_v2.service_group_json_obj.call
                           .update.toDict().items())

        r = self.service_group_get(name)
        r['service_group']['protocol'] = "2"
        r['service_group']['name'] = name
        r['service_group']['lb_method'] = lb_method

        r = self.send(tenant_id=self.tenant_id,
                      method=pool_update_req[0][0],
                      url=pool_update_req[0][1],
                      body=r)

        if self.inspect_response(r) is not True:
            raise a10_ex.SgUpdateError(sg=name)

    def service_group_update_hm(self, name, mon=""):
        pool_update_req = (request_struct_v2.service_group_json_obj.call
                           .update.toDict().items())
        args = {"service_group": {"name": name, "health_monitor": mon}}

        r = self.send(tenant_id=self.tenant_id,
                      method=pool_update_req[0][0],
                      url=pool_update_req[0][1],
                      body=args)

        if self.inspect_response(r, func='delete') is not True:
            raise a10_ex.SgUpdateError(sg=name)

    def service_group_delete(self, name):
        pool_delete_req = (request_struct_v2.service_group_json_obj.call
                           .delete.toDict().items())

        r = self.send(tenant_id=self.tenant_id,
                      method=pool_delete_req[0][0],
                      url=pool_delete_req[0][1],
                      body={'name': name})

        if self.inspect_response(r, func='delete') is not True:
            raise a10_ex.SgDeleteError(sg="sg delete failure")

    def stats(self, name):
        stats_req = (request_struct_v2.virtual_server_object.call
                     .fetchstatistics
                     .toDict().items().items())

        return self.send(tenant_id=self.tenant_id,
                         method=stats_req[0][0],
                         url=stats_req[0][1],
                         body={"name": name})

    def server_get(self, server_name):
        server_search_req = (request_struct_v2.server_json_obj.call.search
                             .toDict().items())

        return self.send(tenant_id=self.tenant_id,
                         method=server_search_req[0][0],
                         url=server_search_req[0][1],
                         body={'name': server_name})

    def server_create(self, server_name, ip_address):
        server_create_req = (request_struct_v2.server_json_obj.call.create
                             .toDict().items())
        server_ds = (request_struct_v2.server_json_obj.ds.toDict())
        server_ds['server']['name'] = server_name
        server_ds['server']['host'] = ip_address

        r = self.send(tenant_id=self.tenant_id,
                      method=server_create_req[0][0],
                      url=server_create_req[0][1],
                      body=server_ds)

        if self.inspect_response(r) is not True:
            raise a10_ex.MemberCreateError(member=server_name)

    def server_delete(self, server_name):
        server_delete_req = (request_struct_v2.server_json_obj.call.delete
                             .toDict().items())
        server_ds = {"server": {"name": server_name}}

        r = self.send(tenant_id=self.tenant_id,
                      method=server_delete_req[0][0],
                      url=server_delete_req[0][1],
                      body=server_ds)

        if self.inspect_response(r) is not True:
            raise a10_ex.MemberDeleteError(member=server_name)

    def member_create(self, name, server_name, port, status=1):
        member_create_req = (request_struct_v2.service_group_member_obj
                             .call.create.toDict().items())
        member_ds = (request_struct_v2.service_group_member_obj
                     .ds.toDict())

        member_ds['name'] = name
        member_ds['member']['server'] = server_name
        member_ds['member']['port'] = port
        member_ds['member']['status'] = status

        r = self.send(tenant_id=self.tenant_id,
                      method=member_create_req[0][0],
                      url=member_create_req[0][1],
                      body=member_ds)

        if self.inspect_response(r) is not True:
            raise a10_ex.MemberCreateError(member=server_name)

    def member_update(self, name, server_name, port, status=1):
        member_update_req = (request_struct_v2.service_group_member_obj
                             .call.update.toDict().items())
        member_ds = (request_struct_v2.service_group_member_obj
                     .ds.toDict())

        member_ds['name'] = name
        member_ds['member']['server'] = server_name
        member_ds['member']['port'] = port
        member_ds['member']['status'] = status

        r = self.send(tenant_id=self.tenant_id,
                      method=member_update_req[0][0],
                      url=member_update_req[0][1],
                      body=member_ds)

        if self.inspect_response(r) is not True:
            raise a10_ex.MemberUpdateError(member=server_name)

    def member_delete(self, name, server_name, server_port):
        member_delete_req = (request_struct_v2.service_group_member_obj
                             .call.delete.toDict().items())
        member_ds = {
            "name": name,
            "member": {
                "server": server_name,
                "port": server_port
            }
        }

        r = self.send(tenant_id=self.tenant_id,
                      method=member_delete_req[0][0],
                      url=member_delete_req[0][1],
                      body=member_ds)

        if self.inspect_response(r, func='delete') is not True:
            LOG.debug("response is %s", r)
            raise a10_ex.MemberDeleteError(member=name)

    def _health_monitor_set(self, request_struct_root, mon_type, name,
                            interval, timeout, max_retries,
                            method=None, url=None, expect_code=None):

        hm_req = request_struct_root.toDict().items()
        if mon_type == 'TCP':
            hm_obj = request_struct_v2.TCP_HM_OBJ.ds.toDict()
        elif mon_type == 'PING':
            hm_obj = request_struct_v2.ICMP_HM_OBJ.ds.toDict()
        elif mon_type == 'HTTP':
            hm_obj = request_struct_v2.HTTP_HM_OBJ.ds.toDict()
        elif mon_type == 'HTTPS':
            hm_obj = request_struct_v2.HTTPS_HM_OBJ.ds.toDict()
        else:
            raise a10_ex.HealthMonitorUpdateError(hm=name)

        hm_obj['name'] = name
        hm_obj['interval'] = interval
        hm_obj['timeout'] = timeout
        hm_obj['consec_pass_reqd'] = max_retries

        mt = mon_type.lower()
        hm_obj[mt]['url'] = "%s %s" % (method, url)
        hm_obj[mt]['expect_code'] = expect_code

        r = self.send(tenant_id=self.tenant_id,
                      method=hm_req[0][0],
                      url=hm_req[0][1],
                      body=hm_obj)

        if self.inspect_response(r) is not True:
            raise a10_ex.HealthMonitorUpdateError(hm=name)

    def health_monitor_create(self, mon_type, name,
                              interval, timeout, max_retries,
                              method=None, url=None, expect_code=None):
        self._health_monitor_set(request_struct_v2.TCP_HM_OBJ.call.create,
                                 mon_type, name,
                                 interval, timeout, max_retries,
                                 method, url, expect_code)

    def health_monitor_update(self, mon_type, name,
                              interval, timeout, max_retries,
                              method=None, url=None, expect_code=None):
        self._health_monitor_set(request_struct_v2.TCP_HM_OBJ.call.update,
                                 mon_type, name,
                                 interval, timeout, max_retries,
                                 method, url, expect_code)

    def health_monitor_delete(self, healthmon_id):
        hm_del_req = (request_struct_v2.HTTP_HM_OBJ.call.delete
                      .toDict().items())

        r = self.send(tenant_id=self.tenant_id,
                      method=hm_del_req[0][0],
                      url=hm_del_req[0][1],
                      body={"name": healthmon_id})

        if self.inspect_response(r, func='delete') is not True:
            raise a10_ex.HealthMonitorDeleteError(hm=healthmon_id)
