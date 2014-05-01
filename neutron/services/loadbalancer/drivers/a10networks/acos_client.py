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
import httplib
import json
import request_struct_v2
import a10_exceptions as a10_ex

from ConfigParser import ConfigParser
from neutron.openstack.common import log as logging



DEBUG=True
LOG=logging.getLogger(__name__)
device_config = ConfigParser()
device_config.read('/etc/neutron/services/loadbalancer/'
                                    'a10networks/a10networks_config.ini')

class A10Client():

    def __init__(self, tenant_id= ""):
        self.device_info=self.select_device(tenant_id = tenant_id)
        self.get_session_id(tenant_id=tenant_id)
        self.tenant_id = tenant_id

    def get_session_id(self, tenant_id= ""):
        try:
            response = self.send(method = "POST",
                                 url = "/services/rest/v2.1/?"
                                       "format=json&method=authenticate",
                                 body = {"username":
                                             self.device_info['username'],
                                         "password":
                                             self.device_info['password']},
                                 new_session = 2)

            self.session_id = response['session_id']
        except:
            self.session_id = None

    def partition(self, tenant_id = ""):
        if self.device_info['v_method'].lower() == 'adp':
            try:
                p_search=self.partition_search(tenant_id = tenant_id)
                if p_search is True:
                    try:
                        self.partition_active(tenant_id = tenant_id)
                    except:
                       raise a10_ex.ParitionActiveError(
                           partition = tenant_id[0:13])
                else:
                    try:
                        self.partition_create(tenant_id = tenant_id)
                    except:
                        raise a10_ex.ParitionCreateError(
                           partition = tenant_id[0:13])
                    finally:
                        try:
                            self.partition_active(tenant_id = tenant_id)
                        except:
                            raise a10_ex.ParitionActiveError(
                               partition = tenant_id[0:13])
            except:
               raise a10_ex.SearchError(term = "Partition Discovery for %s"
                                               % tenant_id[0:13])

    def send(self, tenant_id= "", method = "", url = "", body = "",
             new_session = 0):
        if self.session_id is None and new_session != 2:
            self.get_session_id(tenant_id=tenant_id)
        if new_session != 2 and new_session !=4 and new_session != 3:
            self.partition(tenant_id=tenant_id)

        header = {"Content-Type": "application/json",
                  "User-Agent": "OS-LBaaS-AGENT"}

        if 'port' in self.device_info:
            axapi_port = int(self.device_info['port'])
        elif DEBUG is True:
            axapi_port = 80
        else:
            axapi_port = 443

        req = httplib.HTTPConnection(self.device_info['host'], axapi_port)

        try:
            url = url % self.session_id
        except:
           LOG.debug(_("Could not get Session ID"))
        if len(body) == 0:
            data = None
        else:
            data = json.dumps(body, encoding='utf-8')
        req.request(method, url, data, header)
        response = req.getresponse().read()
        print "HOST--->", self.device_info['host']
        print "URL---->", url
        print "BODY---->", body
        print "new_SESSION--->", new_session
        print "RESPONSE---->", response
        try:
            r_obj = json.loads(response, encoding = 'utf-8')

        except:
            r_obj = response

        finally:
            if new_session == 0 or new_session == 1 or new_session == 3:
                self.close_session(tenant_id= tenant_id)

            return r_obj



    def close_session(self, tenant_id = ""):
        response = self.partition_active(tenant_id = tenant_id, default =
        True)
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
        self.get_session_id(tenant_id = self.tenant_id)
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
        #print "DEVICES_DICT--->", devices
        nodes = 256
        #node_prefix = "a10"
        node_list = []
        x = 0
        while x < nodes:
            node_list.insert(x, (x, []))
            x += 1
        z = 0
        key_list = devices.keys()
        #print "THIS IS THE KEY LIST", key_list
        while z < nodes:
            for key in key_list:
                key_index = int(hashlib.sha256(key).hexdigest(), 16)
                result = key_index % nodes

                if result == nodes:
                    result = 0
                else:
                    result = result + 1
                stored_obj = json.loads(devices[key])
                #print "THIS IS THE STORE OBJECT---->", stored_obj
                node_list[result][1].insert(result, stored_obj)

            z += 1
        tenant_hash = int(hashlib.sha256(tenant_id).hexdigest(), 16)
        limit = 256
        th = tenant_hash
        for i in range(0, limit):
            print "NODE_LENGTH------>", len(node_list[th % nodes][1])
            if len(node_list[th % nodes][1]) > 0:
                node_tenant_mod = tenant_hash % len(node_list[th % nodes][1])
                print "node_tenant_mod--->",node_tenant_mod
                device_info = node_list[th % nodes][1][node_tenant_mod]
                print "DEVICE_INFO---->", device_info
                device_info['tenant_id'] = tenant_id
                break
            th = th + 1
        return device_info






