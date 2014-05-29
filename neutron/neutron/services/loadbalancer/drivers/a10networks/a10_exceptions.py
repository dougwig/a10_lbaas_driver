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

import sys

from neutron.common import exceptions
from neutron.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class A10BaseException(exceptions.NeutronException):
    def __init__(self, **kwargs):
        LOG.debug("A10BaseException", exc_info=sys.exc_info())
        super(A10BaseException, self).__init__(**kwargs)


class A10ThunderException(A10BaseException):
    message = _('An unknown exception occurred in A10LBaaS provider.')


class A10ThunderNoSession(A10BaseException):
    message = _('Unable to get session id from appliance')


class A10ThunderNoDevices(A10BaseException):
    message = _('No configured and active devices')


class A10ThunderVersionMismatch(A10BaseException):
    message = _("A10Client: driver requires ACOS version 2.7.2+")


class UnsupportedFeatureAppCookie(A10BaseException):
    message = _(
        'This version of the driver does not support this'
        ' feature in this release.')


class VipCreateError(A10BaseException):
    message = _(
        'VIP %(vip) could not be created.')


class VipUpdateError(A10BaseException):
    message = _(
        'VIP %(vip) could not be Updated.')


class VipDeleteError(A10BaseException):
    message = _(
        'VIP %(vip) could not be Deleted.')


class SgCreateError(A10BaseException):
    message = _(
        'ServiceGroup %(sg) could not be created.')


class SgUpdateError(A10BaseException):
    message = _(
        'ServiceGroup %(sg) could not be Updated.')


class SgDeleteError(A10BaseException):
    message = _(
        'ServiceGroup %(sg) could not be Deleted.')


class MemberCreateError(A10BaseException):
    message = _(
        'Member %(member) could not be created.')


class MemberUpdateError(A10BaseException):
    message = _(
        'Member %(member) could not be Updated.')


class MemberDeleteError(A10BaseException):
    message = _(
        'Member %(member) could not be Deleted.')


class ParitionCreateError(A10BaseException):
    message = _(
        'Parition %(parition) could not be created.')


class ParitionUpdateError(A10BaseException):
    message = _(
        'Parition %(parition) could not be Updated.')


class ParitionDeleteError(A10BaseException):
    message = _(
        'Parition %(parition) could not be Deleted.')


class ParitionActiveError(A10BaseException):
    message = _(
        'Parition %(parition) could not be made active.')


class HealthMonitorCreateError(A10BaseException):
    message = _(
        'HealthMonitor %(hm) could not be created.')


class HealthMonitorUpdateError(A10BaseException):
    message = _(
        'HealthMonitor %(hm) could not be Updated.')


class HealthMonitorDeleteError(A10BaseException):
    message = _(
        'HealthMonitor %(hm) could not be Deleted.')


class TemplateCreateError(A10BaseException):
    message = _(
        'Template %(template) could not be created.')


class TemplateUpdateError(A10BaseException):
    message = _(
        'Template %(template) could not be Updated.')


class TemplateDeleteError(A10BaseException):
    message = _(
        'Template %(template) could not be Deleted.')


class SearchError(A10BaseException):
    message = _(
        'Search Error: %(term)')
