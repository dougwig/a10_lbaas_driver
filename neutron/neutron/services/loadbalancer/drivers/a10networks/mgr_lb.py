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

from neutron.db.loadbalancer import loadbalancer_db as lb_db
from neutron.services.loadbalancer.drivers import driver_base
import a10_context as a10


class LoadBalancerManager(driver_base.BaseLoadBalancerManager):

    def _total(self, context, tenant_id):
        return context._session.query(lb_db.LoadBalancer).filter_by(
            tenant_id=member['tenant_id']).count()

    def _set(self, c, set_method, context, load_balancer):
        status = c.slb.UP
        if not load_balancer.admin_state_up:
            status = c.slb.DOWN

        set_method(load_balancer.name, load_balancer.address, status)

    def create(self, context, load_balancer):
        with A10WriteStatusContext(self, context, load_balancer) as c:
            self._set(c, c.client.slb.virtual_server.create, context,
                      load_balancer)

            for listener in load_balancer.listeners:
                try:
                    self.driver._listener._create(c, context, listener)
                except acos_errors.Exists:
                    pass

    def update(self, context, old_load_balancer, load_balancer):
        with A10WriteStatusContext(self, context, load_balancer) as c:
            self._set(c, c.client.slb.virtual_server.update, context,
                      load_balancer)

    def delete(self, context, load_balancer):
        with A10DeleteContext(self, context, load_balancer) as c:
            c.client.slb.virtual_server.delete(load_balancer.name)

    def refresh(self, context, lb_obj, force=False):
        raise a10_ex.UnsupportedFeature()

    def stats(self, context, lb_obj):
        with A10Context(self, context, lb_obj) as c:
            try:
                r = c.client.client.slb.virtual_server.stats(lb_obj.id)
                return {
                    "bytes_in": r["virtual_server_stat"]["req_bytes"],
                    "bytes_out": r["virtual_server_stat"]["resp_bytes"],
                    "active_connections": 
                        r["virtual_server_stat"]["cur_conns"],
                    "total_connections": r["virtual_server_stat"]["tot_conns"]
                }
            except Exception:
                return {
                    "bytes_in": 0,
                    "bytes_out": 0,
                    "active_connections": 0,
                    "total_connections": 0
                }


