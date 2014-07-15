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

import mock
import sys

from neutron import context
from neutron.services.loadbalancer.drivers.a10networks import thunder
from neutron.tests.unit.db.loadbalancer import test_db_loadbalancerv2


class FakeModel(object):
    def __init__(self, id):
        self.id = id
        self.address = '1.1.1.1'
        self.tenant_id = "tennant-was-a-great-doctor"


class ManagerTest(object):
    def __init__(self, parent, manager, model, mocked_root):
        self.parent = parent
        self.context = parent.context
        self.driver = parent.driver
        self.manager = manager
        self.model = model
        self.mocked_root = mocked_root

        self.create(model)
        self.update(model, model)
        self.delete(model)

    def create(self, model):
        self.manager.create(self.context, model)
        self.mocked_root.create.assert_called_with(self.context, model)

    def update(self, old_model, model):
        self.manager.update(self.context, old_model, model)
        self.mocked_root.update.assert_called_with(self.context,
                                                   old_model, model)

    def delete(self, model):
        self.manager.delete(self.context, model)
        self.mocked_root.delete.assert_called_with(self.context, model)

    def refresh(self):
        self.manager.refresh(self.context, self.model)
        self.mocked_root.refresh.assert_called_with(self.context, self.model,
                                                    False)

    def stats(self):
        self.manager.stats(self.context, self.model)
        self.mocked_root.stats.assert_called_with(self.context, self.model)

    def _total(self):
        n = self.manager._total(self.context, tenant_id="whatareyoudoingdave")
        self.parent.assertEqual(n, 0)

    def _get_ip(self, use_float=False):
        z = self.manager._get_ip(self.context, self.model, use_float)
        self.parent.assertEqual(z, '1.1.1.1')

    def _count(self):
        n = self.manager._count(self.context, self.model)
        self.parent.assertEqual(n, 0)


class TestA10ThunderDriver(test_db_loadbalancerv2.LbaasPluginDbTestCase):

    def setUp(self):
        super(TestA10ThunderDriver, self).setUp()
        self.context = context.get_admin_context()
        self.plugin = mock.Mock()
        self.driver = thunder.ThunderDriver(self.plugin)
        self.driver.a10 = mock.Mock()

    def test_load_balancer_ops(self):
        m = ManagerTest(self, self.driver.load_balancer,
                        FakeModel("loadbalancer-a10"), self.driver.a10.lb)
        m.refresh()
        m.stats()
        m._total()

    def test_listener_ops(self):
        m = ManagerTest(self, self.driver.listener, FakeModel("listener-a10"),
                        self.driver.a10.listener)
        m._total()

    def test_pool_ops(self):
        m = ManagerTest(self, self.driver.pool, FakeModel("pool-10"),
                        self.driver.a10.pool)
        m._total()

    def test_member_ops(self):
        m = ManagerTest(self, self.driver.member, FakeModel("member-a10"),
                        self.driver.a10.member)
        m._get_ip()
        m._get_ip(use_float=True)
        m._count()

    def test_health_monitor_ops(self):
        m = ManagerTest(self, self.driver.health_monitor, FakeModel("hm-a10"),
                        self.driver.a10.hm)
        m._total()
