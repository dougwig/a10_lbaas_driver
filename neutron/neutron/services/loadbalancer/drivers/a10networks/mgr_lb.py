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

    def create(self, context, load_balancer):
        with A10WriteStatusContext(self, context, load_balancer) as c:
            c.client.slb.virtual_server.create(blah)

            for listener in load_balancer.listeners:
                try:
                    self.driver._listener._create(c, context, listener)
                except acos_errors.Exists:
                    pass

    def update(self, context, old_load_balancer, load_balancer):
        with A10WriteStatusContext(self, context, pool) as c:
            c.client.slb.virtual_server.update(blah)

    def delete(self, context, load_balancer):
        with A10DeleteContext(self, context, pool) as c:
            c.client.slb.virtual_server.delete(blah)

    def refresh(self, context, lb_obj, force=False):
        # This is intended to trigger the backend to check and repair
        # the state of this load balancer and all of its dependent objects
        LOG.debug("LB pool refresh %s, force=%s", lb_obj.id, force)
        with A10Context(self, context, pool) as c:
            todo

    def stats(self, context, lb_obj):
        with A10Context(self, context, pool) as c:
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


