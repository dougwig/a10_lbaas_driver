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
import ssl
import traceback
import urllib3

import request_struct_v2
import a10_exceptions as a10_ex

from ConfigParser import ConfigParser
from neutron.openstack.common import log as logging

# Neutron logs
LOG=logging.getLogger(__name__)

# # Mixin logs from subsystems that are handy for debugging
# class ForwardingHandler(logging.Handler):
#     def __init__(self, destination_logger):
#         logging.Handler.__init__(self)
#         self.destination_logger = destination_logger
#     def emit(self, record):
#         self.destination_logger.handle(record)

# urllib3_logger = logging.getLogger('urllib3')
# urllib3_logger.addHandler(ForwardingHandler(LOG))

device_config = ConfigParser()
device_config.read('/etc/neutron/services/loadbalancer/'
                                    'a10networks/a10networks_config.ini')

class A10Client():

    def __init__(self, tenant_id= ""):
        LOG.info("A10Client init: tenant_id=%s", tenant_id)
        self.device_info=self.select_device(tenant_id = tenant_id)
        self.set_base_url()

        self.force_tlsv1 = False
        self.session_id = None
        self.get_session_id()
        if self.session_id == None:
            msg = _("A10Client: unable to get session_id from ax")
            LOG.error(msg)
            raise a10_ex.A10ThunderNoSession()

        self.tenant_id = tenant_id
        LOG.info("A10Client init: successfully connected, session_id=%s", 
                  self.session_id)


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

        url = self.base_url + api_url
        payload = json.dumps(params, encoding='utf-8')
        r = http.urlopen(method, url, body=payload, headers=headers)

        LOG.debug("axapi_http: data = %s", r.data)

        xmlok = '<?xml version="1.0" encoding="utf-8" ?><response status="ok"></response>'
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
            if self.force_tlsv1 == False and str(e).find(tlsv1_error) >= 0:
                # workaround ssl version
                self.force_tlsv1 = True
                self.get_session_id()
            else:
                LOG.debug("get_session_id failed: %s", e)
                LOG.debug(traceback.format_exc())
                self.session_id = None


    def partition(self, tenant_id = ""):
        if self.device_info['v_method'].lower() == 'adp':
            try:
                p_search=self.partition_search(tenant_id = tenant_id)
                if p_search is True:
                    try:
                        self.partition_active(tenant_id = tenant_id)
                    except:
                        LOG.debug(traceback.format_exc())
                        raise a10_ex.PartitionActiveError(
                           partition = tenant_id[0:13])
                else:
                    try:
                        self.partition_create(tenant_id = tenant_id)
                    except:
                        LOG.debug(traceback.format_exc())
                        raise a10_ex.PartitionCreateError(
                           partition = tenant_id[0:13])
                    finally:
                        try:
                            self.partition_active(tenant_id = tenant_id)
                        except:
                            LOG.debug(traceback.format_exc())
                            raise a10_ex.PartitionActiveError(
                               partition = tenant_id[0:13])
            except:
                LOG.debug(traceback.format_exc())
                raise a10_ex.SearchError(term = "Partition Discovery for %s"
                                               % tenant_id[0:13])

    def send(self, tenant_id="", method="", url="", body={}, new_session=0):
        if self.session_id is None and new_session != 2:
            self.get_session_id()
        if new_session != 2 and new_session !=4 and new_session != 3:
            self.partition(tenant_id=tenant_id)

        if url.find('%') >= 0 and self.session_id != None:
            url = url % self.session_id

        r = self.axapi_http(method, url, body)

        if new_session == 0 or new_session == 1 or new_session == 3:
            LOG.debug("about to close session after req")
            self.close_session(tenant_id= tenant_id)
            LOG.debug("session closed")

        LOG.debug('response = %s', r)
        return r


    def close_session(self, tenant_id = ""):
        response = self.partition_active(tenant_id=tenant_id, default=True)
        if "response" in response:
            if 'status' in response['response']:
                if response['response']['status'] == "OK":
                    results = self.send(tenant_id = tenant_id,
                                method = "POST",url = "/services/rest/"
                                "v2.1/?format=json&method=session"
                                ".close&session_id=%s"%self.session_id,
                                body={"session_id":self.session_id},
                                new_session = 2)
                    if results['response']['status'] == "OK":
                        self.session_id=None


    def write_memory(self, tenant_id = ""):
        return self.send(tenant_id = tenant_id,
                         method = "GET",
                         url = (
                         "/services/rest/v2.1/?format=json&method=system"
                         ".action"
                         ".write_memory&session_id=%s" % self.session_id),
                         new_session = 4)

    def partition_search(self, tenant_id = ""):
        req_info = (request_struct_v2.PARTITION_OBJ.call.search.toDict()
                    .items())
        response = self.send(tenant_id = tenant_id, method = req_info[0][0],
                             url = req_info[0][1] % self.session_id,
                             body = {"name": self.tenant_id[0:13]},
                             new_session = 4)
        if 'response' in response:
            if "err" in response['response']:
                if response['response']['err'] == 520749062:
                    return False
        elif "partition" in response:
            return True

    def partition_create(self, tenant_id = ""):
        req_info = (request_struct_v2.PARTITION_OBJ.call.create.toDict()
                    .items())
        obj = request_struct_v2.PARTITION_OBJ.ds.toDict()
        obj['partition']['name'] = tenant_id[0:13]
        return self.send(tenant_id = tenant_id, method = req_info[0][0],
                         url = req_info[0][1] % self.session_id,
                         body = obj,
                         new_session = 4)


    def partition_delete(self, tenant_id = "", new_session = 3):
        req_info = (request_struct_v2.PARTITION_OBJ.call.delete.toDict()
                    .items())
        self.close_session(tenant_id=self.tenant_id)
        self.get_session_id()
        return self.send(tenant_id = tenant_id, method = req_info[0][0],
                         url = req_info[0][1] % self.session_id,
                         body = {"name": self.tenant_id[0:13]},
                         new_session = new_session)


    def partition_active(self, tenant_id = "", default = False,
                         new_session = 4):
        req_info = (request_struct_v2.PARTITION_OBJ.call.active.toDict()
                    .items())
        if default is True:
            name = "shared"
        else:
            name = tenant_id[0:13]
        return self.send(tenant_id = tenant_id,method = req_info[0][0],
                         url = req_info[0][1] % self.session_id,
                         body = {"name": name}, new_session = new_session)


    def select_device(self, tenant_id = ""):
        devices = {}
        for i in device_config.items('a10networks'):
            devices[i[0]] = i[1].replace("\n", "", len(i[1]))
        LOG.debug("DEVICES_DICT--->", devices)
        nodes = 256
        #node_prefix = "a10"
        node_list = []
        x = 0
        while x < nodes:
            node_list.insert(x, (x, []))
            x += 1
        z = 0
        key_list = devices.keys()
        LOG.debug("THIS IS THE KEY LIST", key_list)
        while z < nodes:
            for key in key_list:
                key_index = int(hashlib.sha256(key).hexdigest(), 16)
                result = key_index % nodes

                if result == nodes:
                    result = 0
                else:
                    result = result + 1
                stored_obj = json.loads(devices[key])
                LOG.debug("THIS IS THE STORE OBJECT---->", repr(stored_obj))
                node_list[result][1].insert(result, stored_obj)

            z += 1
        tenant_hash = int(hashlib.sha256(tenant_id).hexdigest(), 16)
        limit = 256
        th = tenant_hash
        for i in range(0, limit):
            LOG.debug("NODE_LENGTH------>", len(node_list[th % nodes][1]))
            if len(node_list[th % nodes][1]) > 0:
                node_tenant_mod = tenant_hash % len(node_list[th % nodes][1])
                LOG.debug("node_tenant_mod--->",node_tenant_mod)
                device_info = node_list[th % nodes][1][node_tenant_mod]
                LOG.debug("DEVICE_INFO---->", device_info['host'])
                device_info['tenant_id'] = tenant_id
                break
            th = th + 1
        return device_info






