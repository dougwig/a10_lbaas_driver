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

import sys

from neutron.common import exceptions
from neutron.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class A10BaseException(exceptions.NeutronException):
    def __init__(self, **kwargs):
        LOG.debug("A10BaseException", exc_info=sys.exc_info())
        super(A10BaseException, self).__init__(**kwargs)


class UnsupportedFeature(A10BaseException):
    message = _(
        'The requested feature is not supported.')
