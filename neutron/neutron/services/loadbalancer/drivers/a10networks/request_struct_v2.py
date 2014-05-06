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
import copy


class wrapper(object):

    def __init__(self, d=None, create=True):
        if d is None:
            d = {}
        supr = super(wrapper, self)
        supr.__setattr__('_data', d)
        supr.__setattr__('__create', create)

    def __getattr__(self, name):
        try:
            value = self._data[name]
        except KeyError:
            if not super(wrapper, self).__getattribute__('__create'):
                raise
            value = {}
            self._data[name] = value

        if hasattr(value, 'items'):
            create = super(wrapper, self).__getattribute__('__create')
            return wrapper(value, create)
        return value

    def __setattr__(self, name, value):
        self._data[name] = value

    def toDict(self):

        return self.__dict__['_data']

    def __getitem__(self, key):
        try:
            value = self._data[key]
        except KeyError:
            if not super(wrapper, self).__getattribute__('__create'):
                raise
            value = {}
            self._data[key] = value

        if hasattr(value, 'items'):
            create = super(wrapper, self).__getattribute__('__create')
            return wrapper(value, create)
        return value

    def __setitem__(self, key, value):
        self._data[key] = value

    def __iadd__(self, other):
        if self._data:
            raise TypeError("only be replaced if it's empty")
        else:
            return other


server_json_obj = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "server.create&session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.server.update&session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.server.delete&session_id=%s"},
             "getall": {"GET": "/services/rest/v2.1/?format=json&"
                               "method=slb.server.getAll&session_id=%s"},
             "search": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.server.search&session_id=%s"},
             "deleteall": {"POST": "/services/rest/v2.1/?"
                                   "format=json&method=slb.server."
                                   "deleteAll&session_id=%s"},
             "fetchstatistics": {
                 "POST": "/services/rest/v2.1/?format=json&method=slb."
                         "server.fetchStatistics&session_id=%s"},
             "fetchallstatistics": {"GET": "/services/rest/v2.1/"
                                           "?format=json&method=slb."
                                           "server."
                                           "fetchAllStatistics&session_id=%s"}
             },
    "ds": {
        "server": {
            "name": "",
            "host": "",
            "gslb_external_address": "0.0.0.0",
            "weight": '',
            "health_monitor": "(default)",
            "status": 1,
            "conn_limit": '',
            "conn_limit_log": 1,
            "conn_resume": 0,
            "stats_data": 1,
            "extended_stats": 0,
            "slow_start": 0,
            "spoofing_cache": 0,
            "template": "default",
            "port_list": [

            ]
        }
    }
}))

server_port_list_obj = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?"
                                "format=json&method=slb.server.port."
                                "create&session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?"
                                "format=json&method=slb.server.port."
                                "update&session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.server.port.delete&"
                                "session_id=%s"},
             "deleteall": {"POST": "/services/rest/v2.1/?format=json&"
                                   "method=slb.server.port."
                                   "deleteAll&session_id=%s"},
             "updateall": {"POST": "/services/rest/v2.1/?format=json&"
                                   "method=slb.server.port."
                                   "updateAll&session_id=%s"}

             },
    "ds": {
        "port_num": '1-65535',
        "protocol": {'TCP': 2, 'UDP': 3},
        "status": 1,
        "weight": 1,
        "no_ssl": 0,
        "conn_limit": 8000000,
        "conn_limit_log": 1,
        "conn_resume": 0,
        "template": "default",
        "stats_data": 1,
        "health_monitor": "(default)",
        "extended_stats": 0
    }
}))

'''
This returns a service group dict object.
'''

service_group_json_obj = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "service_group.create&session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.service_group.update&"
                                "session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.service_group.delete&"
                                "session_id=%s"},
             "getall": {"GET": "/services/rest/v2.1/?format=json&"
                               "method=slb.service_group.getAll&"
                               "session_id=%s"},
             "search": {"POST": "/services/rest/v2.1/?format=json"
                                "&method=slb.service_group.search&"
                                "session_id=%s"},
             "deleteall": {"POST": "/services/rest/v2.1/?format=json&"
                                   "method=slb.service_group.deleteAll&"
                                   "session_id=%s"},
             "fetchstatistics": {
                 "POST": "/services/rest/v2.1/?format=json&method=slb."
                         "service_group.fetchStatistics&"
                         "session_id=%s"},
             "fetchallstatistics": {
                 "GET": "/services/rest/v2.1/?format=json&"
                        "method=slb.service_group."
                        "fetchAllStatistics&session_id=%s"}
             },
    "ds": {
        "service_group": {
            "name": "",
            "protocol": '',
            "lb_method": {'RoundRobin': 0,
                          'WeightedRoundRobin': 1,
                          'LeastConnection': 2,
                          'WeightedLeastConnection': 3,
                          'LeastConnectionOnServicePort': 4,
                          'WeightedLeastConnectionOnServicePort': 5,
                          'FastResponseTime': 6,
                          'LeastRequest': 7,
                          'StrictRoundRobin': 8,
                          'StateLessSourceIPHash': 9,
                          'StateLessSourceIPHashOnly': 10,
                          'StateLessDestinationIPHash': 11,
                          'StateLessSourceDestinationIPHash': 12,
                          'StateLessPerPackageRoundRobin': 13},
            "health_monitor": "",
            "min_active_member": {
                "status": 0,
                "number": 0,
                "priority_set": 0
            },
            "backup_server_event_log_enable": 0,
            "client_reset": 0,
            "stats_data": 1,
            "extended_stats": 0,
            "member_list": []
        }
    }
}))

'''
Format of service_group_create_member
'''
service_group_member_obj = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?format=json&method="
                                "slb.service_group.member.create&"
                                "session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.service_group.member."
                                "update&session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.service_group.member."
                                "delete&session_id=%s"},
             "deleteall": {"POST": "/services/rest/v2.1/?format=json&"
                                   "method=slb.service_group.member."
                                   "deleteAll&session_id=%s"},
             "updateall": {"POST": "/services/rest/v2.1/?format=json&"
                                   "method=slb.service_group.member."
                                   "updateAll&session_id=%s"}
             },
    "ds": {"name": "",
           "member": {"server": "", "port": "", "status": "1"}
           }
}))

'''
Virtual Server Format
'''
virtual_server_object = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?format=json&method="
                                "slb.virtual_server.create&session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.virtual_server.update&"
                                "session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.virtual_server.delete&"
                                "session_id=%s"},
             "getall": {"GET": "/services/rest/v2.1/?format=json&"
                               "method=slb.virtual_server.getAll&"
                               "session_id=%s"},
             "search": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.virtual_server.search&"
                                "session_id=%s"},
             "deleteall": {"POST": "/services/rest/v2.1/?format=json&"
                                   "method=slb.virtual_server."
                                   "deleteAll&session_id=%s"},
             "fetchstatistics": {
             "POST": "/services/rest/v2.1/?format=json&method=slb."
                     "virtual_server.fetchStatistics&session_id=%s"},
             "fetchallstatistics": {
                 "GET": "/services/rest/v2.1/?format=json&method=slb."
                        "virtual_server.fetchAllStatistics&"
                        "session_id=%s"}
             },
    "ds": {"virtual_server": {
        "status": 1,
        "disable_vserver_on_condition": 0,
        "name": "foa",
        "vip_template": "default",
        "pbslb_template": "",
        "redistribution_flagged": 0,
        "extended_stats": 0,
        "ha_group": {
            "status": 0,
            "ha_group_id": 0,
            "dynamic_server_weight": 0
        },
        "arp_status": 1,
        "address": "192.168.212.121",
        "vport_list": [

        ],
        "stats_data": 1
    }
    }
}))
'''
ICMP HM Object
'''

ICMP_HM_OBJ = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?format=json&"
                        "method=slb.hm.create&session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?format="
                        "json&method=slb.hm.update&"
                        "session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format="
                        "json&method=slb.hm.delete&session_id=%s"}
             },
    "ds": {
        'retry': 3,
        'name': u'http_foo3',
        'consec_pass_reqd': 1,
        'interval': 5,
        'timeout': 5,
        'disable_after_down': 0,
        'type': 0,
    }
}))

'''
TCP HM Object
'''

TCP_HM_OBJ = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?format=json&"
                        "method=slb.hm.create&session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?format="
                        "json&method=slb.hm.update&"
                        "session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format="
                        "json&method=slb.hm.delete&session_id=%s"}
             },
    "ds": {
        'retry': 3,
        'name': u'http_foo3',
        'consec_pass_reqd': 1,
        'interval': 5,
        'timeout': 5,
        'disable_after_down': 0,
        'type': 1,
    }
}))

'''
HTTP HM Object
'''
HTTP_HM_OBJ = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.hm.create&session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?format="
                                "json&method=slb.hm.update&"
                                "session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format="
                                "json&method=slb.hm.delete&session_id=%s"}
             },
    "ds": {
        'retry': 3,
        'http': {
            'port': 80,
            'url': u'GET /foo',
            'expect_code': u'200'
        },
        'name': u'http_foo3',
        'consec_pass_reqd': 1,
        'interval': 5,
        'timeout': 5,
        'disable_after_down': 0,
        'type': 3,
    }
}))
'''
HTTPS HM Object
'''

HTTPS_HM_OBJ = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.hm.create&session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?"
                                "format=json&method=slb.hm.update&"
                                "session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.hm.delete&session_id=%s"}
             },
    "ds": {
        'retry': 3,
        'https': {
            'url': 'GET /foo',
            'port': 80,
            'expect_code': '200'
        },
        'name': 'http_foo3',
        'consec_pass_reqd': 1,
        'interval': 5,
        'timeout': 5,
        'disable_after_down': 0,
        'type': 4,
    }
}))
'''
Cookie Persistance Template
'''
COOKIE_PER_TEMP_OBJ = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "template.cookie_persistence."
                                "create&session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.template.cookie_persistence."
                                "update&session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.template.cookie_persistence."
                                "delete&session_id=%s"},
             "search": {"POST": "/services/rest/v2.1/?format=json&"
                                "method=slb.template.cookie_persistence."
                                "search&session_id=%s"}
             },
    "ds": {
        "cookie_persistence_template": {
            "name": "",
            "expire_exist": 0,
            "expire": 3600,
            "cookie_name": "",
            "domain": "",
            "path": "",
            "match_type": 0,
            "match_all": 0,
            "insert_always": 0,
            "dont_honor_conn": 0
        }
    }
}))

'''
SOURCE_IP_TEMPLATE
'''

SOURCE_IP_TEMP_OBJ = wrapper(copy.deepcopy({
    "call": {
        "create": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                           "template.src_ip_persistence"
                           ".create&session_id=%s"},
        "update": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                           "template.src_ip_persistence.update&session_id=%s"},
        "delete": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                           "template.src_ip_persistence.delete&session_id=%s"},
        "search": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                           "template.src_ip_persistence.search&session_id=%s"}
    },
    "ds": {
        "src_ip_persistence_template": {
            "name": "src_ip",
            "match_type": 1,
            "match_all": 0,
            "timeout": 1800,
            "no_honor_conn": 0,
            "incl_sport": 0,
            "include_dstip": 0,
            "hash_persist": 0,
            "enforce_high_priority": 0,
            "netmask": "255.255.255.255",
            "netmask6": 96
        }
    }
}))

'''
paritionObject
'''
PARTITION_OBJ = wrapper(copy.deepcopy({
    "call": {
        "active": {"POST":
                   "/services/rest/v2.1/?format=json&method=system."
                   "partition.active&session_id=%s"},
        "create": {"POST": "/services/rest/v2.1/?format=json&method=system."
                           "partition.create&session_id=%s"},
        "update": {"POST": "/services/rest/v2.1/?format=json&method=system."
                           "partition.update&session_id=%s"},
        "delete": {"POST": "/services/rest/v2.1/?format=json&method=system."
                           "partition.delete&session_id=%s"},
        "search": {"POST": "/services/rest/v2.1/?format=json&method=system."
                           "partition.search&session_id=%s"}
    },
    "ds": {
        'partition': {
            'max_aflex_file': 32,
            'network_partition': 0,
            'name': ""}
    }
}))

"""
VPORT:HTTP
"""
vport_HTTP_obj = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "virtual_service.create&session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "virtual_service.update&session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "virtual_service.delete&session_id=%s"},
             "getall": {"GET": "/services/rest/v2.1/?format=json&method=slb."
                               "virtual_service.getAll&session_id=%s"},
             "search": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "virtual_service.search&session_id=%s"},
             "deleteall": {
                 "POST": "/services/rest/v2.1/?format=json&method=slb."
                         "virtual_service.deleteAll&session_id=%s"},
             "fetchstatistics": {
             "POST": "/services/rest/v2.1/?format=json&method=slb."
                     "virtual_service.fetchStatistics&session_id=%s"},
             "fetchallstatistics": {
                 "GET": "/services/rest/v2.1/?format=json&method=slb."
                        "virtual_service.fetchAllStatistics&session_id=%s"}
             },
    "ds": {
        "protocol": 11,
        "sync_cookie": {
            "sync_cookie": 0,
            "sack": 0
        },
        "snat_against_vip": 0,
        "received_hop": 0,
        "vport_template": "default",
        "send_reset": 0,
        "port": 80,
        "service_group": "",
        "vport_acl_id": 0,
        "auto_source_nat": 0,
        "extended_stats": 0,
        "server_ssl_template": "",
        "aflex_list": [],
        "status": 1,
        "default_selection": 1,
        "http_template": "",
        "source_nat": "",
        "cookie_persistence_template": "",
        "conn_reuse_template": "",
        "name": "",
        "tcp_proxy_template": "",
        "connection_limit": {
            "status": 0,
            "connection_limit_log": 0,
            "connection_limit": 8000000,
            "connection_limit_action": 0
        },
        "ram_cache_template": "",
        "pbslb_template": "",
        "stats_data": 1,
        "acl_natpool_binding_list": []
    }
}))

vport_HTTPS_obj = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "virtual_service.create&session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "virtual_service.update&session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "virtual_service.delete&session_id=%s"},
             "getall": {"GET": "/services/rest/v2.1/?format=json&method=slb."
                               "virtual_service.getAll&session_id=%s"},
             "search": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "virtual_service.search&session_id=%s"},
             "deleteall": {
                 "POST": "/services/rest/v2.1/?format=json&method=slb."
                         "virtual_service.deleteAll&session_id=%s"},
             "fetchstatistics": {
             "POST": "/services/rest/v2.1/?format=json&method=slb."
                     "virtual_service.fetchStatistics&session_id=%s"},
             "fetchallstatistics": {
                 "GET": "/services/rest/v2.1/?format=json&method=slb."
                        "virtual_service.fetchAllStatistics&session_id=%s"}
             },
    "ds": {
        "protocol": 12,
        "sync_cookie": {
            "sync_cookie": 0,
            "sack": 0
        },
        "snat_against_vip": 0,
        "received_hop": 0,
        "vport_template": "default",
        "send_reset": 0,
        "port": 443,
        "service_group": "",
        "auto_source_nat": 0,
        "vport_acl_id": 0,
        "extended_stats": 0,
        "server_ssl_template": "",
        "aflex_list": [],
        "status": 1,
        "client_ssl_template": "",
        "source_ip_persistence_template": "",
        "default_selection": 1,
        "http_template": "",
        "source_nat": "",
        "conn_reuse_template": "",
        "name": "",
        "tcp_proxy_template": "",
        "connection_limit": {
            "status": 0,
            "connection_limit_log": 0,
            "connection_limit": 8000000,
            "connection_limit_action": 0
        },
        "ram_cache_template": "",
        "pbslb_template": "",
        "stats_data": 1,
        "acl_natpool_binding_list": []
    }
}))

vport_TCP_obj = wrapper(copy.deepcopy({
    "call": {"create": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "virtual_service.create&session_id=%s"},
             "update": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "virtual_service.update&session_id=%s"},
             "delete": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "virtual_service.delete&session_id=%s"},
             "getall": {"GET": "/services/rest/v2.1/?format=json&method=slb."
                               "virtual_service.getAll&session_id=%s"},
             "search": {"POST": "/services/rest/v2.1/?format=json&method=slb."
                                "virtual_service.search&session_id=%s"},
             "deleteall": {
                 "POST": "/services/rest/v2.1/?format=json&method=slb."
                         "virtual_service.deleteAll&session_id=%s"},
             "fetchstatistics": {
             "POST": "/services/rest/v2.1/?format=json&method=slb."
                     "virtual_service.fetchStatistics&session_id=%s"},
             "fetchallstatistics": {
                 "GET": "/services/rest/v2.1/?format=json&method=slb."
                        "virtual_service.fetchAllStatistics&session_id=%s"}
             },
    "ds": {
        "protocol": 2,
        "sync_cookie": {
            "sync_cookie": 0,
            "sack": 0
        },
        "snat_against_vip": 0,
        "received_hop": 0,
        "vport_template": "default",
        "tcp_template": "",
        "send_reset": 0,
        "port": '',
        "service_group": "",
        "vport_acl_id": 0,
        "extended_stats": 0,
        "aflex_list": [],
        "status": 1,
        "auto_source_nat": 0,
        "direct_server_return": 0,
        "source_ip_persistence_template": "",
        "default_selection": 1,
        "source_nat": "",
        "name": "",
        "ha_connection_mirror": 0,
        "connection_limit": {
            "status": 0,
            "connection_limit_log": 0,
            "connection_limit": 8000000,
            "connection_limit_action": 0
        },
        "pbslb_template": "",
        "stats_data": 1,
        "acl_natpool_binding_list": []
    }
}))
