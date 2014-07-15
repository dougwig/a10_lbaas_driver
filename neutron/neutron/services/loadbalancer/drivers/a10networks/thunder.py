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
from neutron.db.loadbalancer import loadbalancer_dbv2 as lb_db
from neutron.openstack.common import log as logging
from neutron.services.loadbalancer.drivers import driver_base

VERSION = "J1.0.0"
LOG = logging.getLogger(__name__)


class ThunderDriver(driver_base.LoadBalancerBaseDriver):

    def __init__(self, plugin):
        super(ThunderDriver, self).__init__(plugin)

        self.load_balancer = LoadBalancerManager(self)
        self.listener = ListenerManager(self)
        self.pool = PoolManager(self)
        self.member = MemberManager(self)
        self.health_monitor = HealthMonitorManager(self)

        self.a10 = None
        try:
            # Attempt import here, so unit tests can replace self.a10
            import a10_neutron_lbaas
            import acos_client

            LOG.info("A10Driver: initializing, version=%s, lbaas_manager=%s, "
                     "acos_client=%s", VERSION, a10_neutron_lbaas.VERSION,
                     acos_client.VERSION)

            self.a10 = a10_neutron_lbaas.LbaasManager(self)
        except ImportError:
            pass

        if self.a10 is None:
            LOG.error(_("A10Driver: Failed to import a10_neutron_lbaas; "
                        "please 'pip install a10_neutron_lbaas' and restart "
                        "neutron."))


# Most driver calls below are straight passthroughs to the A10 package
# 'a10_neutron_lbaas'.  Any function that has not been fully abstracted
# into the openstack driver/plugin interface is NOT passed through, to
# make it obvious which hidden interfaces/db calls that we rely on.


class LoadBalancerManager(driver_base.BaseLoadBalancerManager):

    def _total(self, context, tenant_id):
        return context.session.query(lb_db.LoadBalancer).filter_by(
            tenant_id=tenant_id).count()

    def create(self, context, lb):
        self.driver.a10.lb.create(context, lb)

    def update(self, context, old_lb, lb):
        self.driver.a10.lb.update(context, old_lb, lb)

    def delete(self, context, lb):
        self.driver.a10.lb.delete(context, lb)

    def refresh(self, context, lb, force=False):
        self.driver.a10.lb.refresh(context, lb, force)

    def stats(self, context, lb):
        return self.driver.a10.lb.stats(context, lb)


class ListenerManager(driver_base.BaseListenerManager):

    def _total(self, context, tenant_id):
        return context.session.query(lb_db.Listener).filter_by(
            tenant_id=tenant_id).count()

    def create(self, context, listener):
        self.driver.a10.listener.create(context, listener)

    def update(self, context, old_listener, listener):
        self.driver.a10.listener.update(context, old_listener, listener)

    def delete(self, context, listener):
        self.driver.a10.listener.delete(context, listener)


class PoolManager(driver_base.BasePoolManager):

    def _total(self, context, tenant_id):
        return context.session.query(lb_db.PoolV2).filter_by(
            tenant_id=tenant_id).count()

    def create(self, context, pool):
        self.driver.a10.pool.create(context, pool)

    def update(self, context, old_pool, pool):
        self.driver.a10.pool.update(context, old_pool, pool)

    def delete(self, context, pool):
        self.driver.a10.pool.delete(context, pool)


class MemberManager(driver_base.BaseMemberManager):

    def _get_ip(self, context, member, use_float=False):
        ip_address = member.address
        if use_float:
            fip_qry = context.session.query(l3_db.FloatingIP)
            if (fip_qry.filter_by(fixed_ip_address=ip_address).count() > 0):
                float_address = fip_qry.filter_by(
                    fixed_ip_address=ip_address).first()
                ip_address = str(float_address.floating_ip_address)
        return ip_address

    def _count(self, context, member):
        return context.session.query(lb_db.MemberV2).filter_by(
            tenant_id=member.tenant_id,
            address=member.address).count()

    def create(self, context, member):
        self.driver.a10.member.create(context, member)

    def update(self, context, old_member, member):
        self.driver.a10.member.update(context, old_member, member)

    def delete(self, context, member):
        self.driver.a10.member.delete(context, member)


class HealthMonitorManager(driver_base.BaseHealthMonitorManager):

    def _total(self, context, tenant_id):
        return context.session.query(lb_db.HealthMonitorV2).filter_by(
            tenant_id=tenant_id).count()

    def create(self, context, hm):
        self.driver.a10.hm.create(context, hm)

    def update(self, context, old_hm, hm):
        self.driver.a10.hm.update(context, old_hm, hm)

    def delete(self, context, hm):
        self.driver.a10.hm.delete(context, hm)
