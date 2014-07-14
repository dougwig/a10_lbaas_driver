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

from neutron.services.loadbalancer.drivers import driver_base
import a10_context as a10


class ListenerManager(driver_base.BaseListenerManager):

    # SESSION_PERSISTENCE_SOURCE_IP = 'SOURCE_IP'
    # SESSION_PERSISTENCE_HTTP_COOKIE = 'HTTP_COOKIE'
    # SESSION_PERSISTENCE_APP_COOKIE = 'APP_COOKIE'

    def _set(self, set_method, context, listener):
        protocols = {
            'TCP': c.client.slb.virtual_server.vport.protocol.TCP,
            'UDP': c.client.slb.virtual_server.vport.protocol.UDP,
            'HTTP': c.client.slb.virtual_server.vport.protocol.HTTP,
            'HTTPS': c.client.slb.virtual_server.vport.protocol.HTTPS
        }

        set_method(listener.load_balander_id, listener.id,
                   protocol=protocols[listener.protocol],
                   port=listener.port,
                   service_group_name=listener.pool_id,
                   s_pers_name=spers,
                   c_pers_name=cpers,
                   status=status)

    def create(self, context, listener):
        with a10.A10WriteStatusContext(self, context, pool) as c:
            self._set(c.client.slb.virtual_server.vport.create, context,
                      listener)

    def update(self, context, old_listener, listener):
        with a10.A10WriteStatusContext(self, context, pool) as c:
            self._set(c.client.slb.virtual_server.vport.update, context,
                      listener)

    def delete(self, context, listener):
        with a10.A10DeleteContext(self, context, pool) as c:
            try:
                if vip['session_persistence'] is not None:
                    c.client.persistence_delete(
                        vip['session_persistence']['type'],
                        vip['id'])
            except Exception:
                pass

            c.client.slb.virtual_server.vport.delete(
                listener.load_balancer_id,
                listener.id,
                protocol=protocols[listener.protocol],
                port=listener.port)
