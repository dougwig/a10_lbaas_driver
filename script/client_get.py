#!/usr/bin/env python

import sys

sys.path.insert(0, "./neutron/neutron/services/loadbalancer/drivers")

from a10networks import acos_client

a = acos_client.A10Client()

info_url = ("/services/rest/v2.1/?format=json&session_id=%s"
            "&method=slb.virtual_server.getAll" % a.session_id)

r = a.axapi_http("GET", info_url)

print(r)
