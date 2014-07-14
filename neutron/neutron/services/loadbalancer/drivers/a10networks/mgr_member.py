# Copyright 2014, Doug Wiegley (dougwig), A10 Networks
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

from neutron.db import l3_db
from neutron.db.loadbalancer import loadbalancer_db as lb_db
from neutron.services.loadbalancer.drivers import driver_base
import a10_context as a10


class MemberManager(driver_base.BaseMemberManager):

    def _get_ip(self, context, member, use_float=False):
        ip_address = member['address']
        if use_float:
            fip_qry = context.session.query(l3_db.FloatingIP)
            if (fip_qry.filter_by(fixed_ip_address=ip_address).count() > 0):
                float_address = fip_qry.filter_by(
                    fixed_ip_address=ip_address).first()
                ip_address = str(float_address.floating_ip_address)
        return ip_address

    def _get_name(self, member, ip_address):
        tenant_label = member['tenant_id'][:5]
        addr_label = str(ip_address).replace(".", "_", 4)
        server_name = "_%s_%s_neutron" % (tenant_label, addr_label)
        return server_name

    def _count(self, context, member):
        return context._session.query(lb_db.MemberV2).filter_by(
            tenant_id=member['tenant_id'],
            address=member['address']).count()

    def create(self, context, member):
        with A10WriteStatusContext(self, context, pool) as c:
            server_ip = self._get_ip(context, member,
                                     c.device_cfg['use_float'])
            server_name = self._get_name(member, server_ip)

            status = c.client.slb.service_group.member.UP
            if not member["admin_state_up"]:
                status = c.client.slb.service_group.member.DOWN

            try:
                c.client.server_create(server_name, ip_address)
            except acos_errors.Exists:
                pass

            c.client.slb.member.create(member.pool_id, server_name,
                                       member.protocol_port, status=status)

    def update(self, context, old_obj, obj):
        with A10WriteStatusContext(self, context, pool) as c:
            server_ip = self._get_ip(context, member,
                                     c.device_cfg['use_float'])
            server_name = self._get_name(member, server_ip)

            status = c.client.slb.UP
            if not member["admin_state_up"]:
                status = c.client.slb.DOWN

            c.client.slb.service_group.member.update(member.pool_id,
                                                     server_name,
                                                     member.protocol_port,
                                                     status)

    def _delete(self, c, context, member):
        server_ip = self._get_ip(context, member, todo,
                                 c.device_cfg['use_float'])
        server_name = self._get_name(member, server_ip)

        if self._count(context, member) > 1:
            c.client.slb.service_group.member.delete(member.pool_id,
                                                     server_name,
                                                     member.protocol_port)
        else:
            c.client.slb.server.delete(server_name)

    def delete(self, context, member):
        with A10DeleteContext(self, context, pool) as c:
            self._delete(c, context, member)
