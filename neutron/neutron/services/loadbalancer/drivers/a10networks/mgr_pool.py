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
import a10_exceptions as a10_ex


class PoolManager(driver_base.BasePoolManager):

    def _total(self, context, tenant_id):
        return context._session.query(lb_db.PoolV2).filter_by(
            tenant_id=member['tenant_id']).count()

    def _set(self, c, set_method, context, pool):
        lb_algorithms = {
            'ROUND_ROBIN': c.client.slb.service_group.ROUND_ROBIN,
            'LEAST_CONNECTIONS': c.client.slb.service_group.LEAST_CONNECTION,
            'SOURCE_IP': c.client.slb.service_group.WEIGHTED_LEAST_CONNECTION
        }
        protocols = {
            'TCP': c.client.slb.service_group.TCP,
            'UDP': c.client.slb.service_group.UDP
        }

        set_method(pool.id,
                   protocol=protocols[pool.protocol],
                   lb_method=algoritms[pool.lb_algorithm])

        if pool.sessionpersistence:
            PersistenceManager(self, c, pool).create()

    def create(self, context, pool):
        with a10.A10WriteStatusContext(self, context, pool) as c:
            self._set(c, c.client.slb.service_group.create, context, pool)

    def update(self, context, old_pool, pool):
        with a10.A10WriteStatusContext(self, context, pool) as c:
            self._set(c, c.client.slb.service_group.update, context, pool)

    def delete(self, context, pool):
        with a10.A10DeleteContext(self, context, pool) as c:
            for member in pool.members:
                self.driver.member._delete(c, context, member)

            if pool.health_monitor:
                self.driver.health_monitor._delete(c, context,
                                                   pool.health_monitor)

            c.client.slb.service_group.delete(pool.id)

            if pool.sessionpersistence:
                PersistenceManager(self, c, pool).delete()


class PersistenceManager(object):

    def __init__(self, mgr, c, context, pool):
        self.mgr = mgr
        self.c = c
        self.context = context
        self.pool = pool
        self.sp = pool.sessionpersistence
        self.name = pool.id

    def create(self):
        methods = {
            'HTTP_COOKIE':
                self.c.client.slb.template.cookie_persistence.create,
            'SOURCE_IP':
                self.c.client.slb.template.source_ip_persistence.create,
        }
        if self.sp.type in methods:
            try:
                methods[self.sp.type](self.name)
            except acos_errors.Exists:
                pass
        else:
            raise a10_ex.UnsupportedFeature()

        if pool.listener:
            self.mgr.driver.listener._update(c, context, pool.listener)

    def delete(self):
        methods = {
            'HTTP_COOKIE':
                self.c.client.slb.template.cookie_persistence.delete,
            'SOURCE_IP':
                self.c.client.slb.template.source_ip_persistence.delete,
        }
        if self.sp.type in methods:
            try:
                methods[self.sp.type](self.name)
            except Exception:
                pass

        if pool.listener:
            self.mgr.driver.listener._update(c, context, pool.listener)
