#!/usr/bin/env python

import neutron.services.loadbalancer.drivers.a10networks.acos_client \
    as acos_client

a = acos_client.A10Client()

info_url = ("/services/rest/v2.1/?format=json&session_id=%s"
            "&method=slb.virtual_server.getAll" % a.session_id)

r = a.axapi_http("GET", info_url)

print r
