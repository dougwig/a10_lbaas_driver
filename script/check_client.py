#!/usr/bin/env python

import logging
import sys

sys.path.insert(0, "./neutron/neutron/services/loadbalancer/drivers")

from a10networks.acos_client import A10Client
import a10networks.a10_config as a10_config

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

config = a10_config.A10Config()
c = A10Client(config, version_check=True)
