#!/usr/bin/env python

import logging
import sys

sys.path.insert(0, "./neutron/neutron/services/loadbalancer/drivers")

from a10networks.acos_client import A10Client

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

c = A10Client()
