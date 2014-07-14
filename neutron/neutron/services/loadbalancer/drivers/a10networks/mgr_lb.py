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






    # def _persistence_create(self, a10, vip):
    #     persist_type = vip['session_persistence']['type']
    #     name = vip['id']

    #     try:
    #         if a10.persistence_exists(persist_type, name):
    #             return name
    #         a10.persistence_create(persist_type, name)
    #     except Exception:
    #         raise a10_ex.TemplateCreateError(template=name)

    #     return name

    # def _setup_vip_args(self, a10, vip):
    #     s_pers = None
    #     c_pers = None
    #     LOG.debug("_setup_vip_args vip=%s", vip)
    #     if ('session_persistence' in vip and
    #             vip['session_persistence'] is not None):
    #         LOG.debug("creating persistence template")
    #         pname = self._persistence_create(a10, vip)
    #         if vip['session_persistence']['type'] is "HTTP_COOKIE":
    #             c_pers = pname
    #         elif vip['session_persistence']['type'] == "SOURCE_IP":
    #             s_pers = pname
    #     status = 1
    #     if vip['admin_state_up'] is False:
    #         status = 0
    #     LOG.debug("_setup_vip_args = %s, %s, %d", s_pers, c_pers, status)
    #     return s_pers, c_pers, status

    # def create_vip(self, context, vip):
    #     a10 = self._device_context(tenant_id=vip['tenant_id'])
    #     s_pers, c_pers, status = self._setup_vip_args(a10, vip)

    #     try:
    #         a10.virtual_server_create(vip['id'], vip['address'],
    #                                   vip['protocol'], vip['protocol_port'],
    #                                   vip['pool_id'],
    #                                   s_pers, c_pers, status)
    #         self._active(context, lb_db.Vip, vip['id'])

    #     except Exception:
    #         self._failed(context, lb_db.Vip, vip['id'])
    #         raise a10_ex.VipCreateError(vip=vip['id'])

    # def update_vip(self, context, old_vip, vip):
    #     a10 = self._device_context(tenant_id=vip['tenant_id'])
    #     s_pers, c_pers, status = self._setup_vip_args(a10, vip)

    #     try:
    #         a10.virtual_port_update(vip['id'], vip['protocol'],
    #                                 vip['pool_id'],
    #                                 s_pers, c_pers, status)
    #         self._active(context, lb_db.Vip, vip['id'])

    #     except Exception:
    #         self._failed(context, lb_db.Vip, vip['id'])
    #         raise a10_ex.VipUpdateError(vip=vip['id'])

    # def delete_vip(self, context, vip):
    #     a10 = self._device_context(tenant_id=vip['tenant_id'])
    #     try:
    #         if vip['session_persistence'] is not None:
    #             a10.persistence_delete(vip['session_persistence']['type'],
    #                                    vip['id'])
    #     except Exception:
    #         pass

    #     try:
    #         a10.virtual_server_delete(vip['id'])
    #         self.plugin._delete_db_vip(context, vip['id'])
    #     except Exception:
    #         self._failed(context, lb_db.Vip, vip['id'])
    #         raise a10_ex.VipDeleteError(vip=vip['id'])



