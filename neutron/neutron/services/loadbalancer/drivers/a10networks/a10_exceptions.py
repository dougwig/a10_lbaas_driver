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

from neutron.common import exceptions


class A10ThunderException(exceptions.NeutronException):
    msg = _('An unknown exception'
            'occurred in A10LBaaS provider.')


class A10ThunderNoSession(exceptions.NeutronException):
    msg = _('Unable to get session id from appliance')


class UnsupportedFeatureAppCookie(exceptions.NeutronException):
    msg = _(
        'This version of the driver does not support this'
        ' feature in this release.')


class VipCreateError(exceptions.NeutronException):
    msg = _(
        'VIP %(vip) could not be created.')


class VipUpdateError(exceptions.NeutronException):
    msg = _(
        'VIP %(vip) could not be Updated.')


class VipDeleteError(exceptions.NeutronException):
    msg = _(
        'VIP %(vip) could not be Deleted.')


class SgCreateError(exceptions.NeutronException):
    msg = _(
        'ServiceGroup %(sg) could not be created.')


class SgUpdateError(exceptions.NeutronException):
    msg = _(
        'ServiceGroup %(sg) could not be Updated.')


class SgDeleteError(exceptions.NeutronException):
    msg = _(
        'ServiceGroup %(sg) could not be Deleted.')


class MemberCreateError(exceptions.NeutronException):
    msg = _(
        'Member %(member) could not be created.')


class MemberUpdateError(exceptions.NeutronException):
    msg = _(
        'Member %(member) could not be Updated.')


class MemberDeleteError(exceptions.NeutronException):
    msg = _(
        'Member %(member) could not be Deleted.')


class ParitionCreateError(exceptions.NeutronException):
    msg = _(
        'Parition %(parition) could not be created.')


class ParitionUpdateError(exceptions.NeutronException):
    msg = _(
        'Parition %(parition) could not be Updated.')


class ParitionDeleteError(exceptions.NeutronException):
    msg = _(
        'Parition %(parition) could not be Deleted.')


class ParitionActiveError(exceptions.NeutronException):
    msg = _(
        'Parition %(parition) could not be made active.')


class HealthMonitorCreateError(exceptions.NeutronException):
    msg = _(
        'HealthMonitor %(hm) could not be created.')


class HealthMonitorUpdateError(exceptions.NeutronException):
    msg = _(
        'HealthMonitor %(hm) could not be Updated.')


class HealthMonitorDeleteError(exceptions.NeutronException):
    msg = _(
        'HealthMonitor %(hm) could not be Deleted.')


class TemplateCreateError(exceptions.NeutronException):
    msg = _(
        'Template %(template) could not be created.')


class TemplateUpdateError(exceptions.NeutronException):
    msg = _(
        'Template %(template) could not be Updated.')


class TemplateDeleteError(exceptions.NeutronException):
    msg = _(
        'Template %(template) could not be Deleted.')


class SearchError(exceptions.NeutronException):
    msg = _(
        'Search Error: %(term)')
