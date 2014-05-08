
import pytest
import re
import subprocess
import time
import uuid

from local_env import *


def find(str, regex):
    m = re.search(regex, str, re.MULTILINE)
    if m is not None:
        return m.group(1)
    else:
        return ""


class NeutronLB(object):

    def __init__(self):
        self.subnet_id = self.subnet_id(PRIVATE_NETWORK_NAME)
        self.pool_name = self._random_hex()
        self.lb_pool_create(self.pool_name, self.subnet_id)

    def _random_hex(self):
        return uuid.uuid4().hex[0:12]

    def _neutron(self, cmd):
        print "NEUTRON: ", cmd
        z = subprocess.check_output(["neutron"] + cmd)
        print "result:\n", z
        return z

    def _wait_for_completion(self, cmd):
        start = time.time()
        now = start
        r = ''
        while ((now-start) < 10):
            r = self._neutron(cmd)
            if find(r, "(PENDING)") != "PENDING":
                break

        if find(r, "(ACTIVE)") == "":
            raise "error: action did not complete successfully"

    def subnet_id(self, network_name):
        r = self._neutron(['net-show', network_name])
        return find(r, "^\| subnets.*\| ([^\s]+)")

    def lb_pool_create(self, pool_name, subnet_id, method='ROUND_ROBIN',
                       protocol='HTTP'):
        self._neutron(['lb-pool-create', '--name', pool_name,
                       '--lb-method', method, '--protocol', protocol,
                       '--subnet-id', subnet_id])
        self._wait_for_completion(['lb-pool-show', pool_name])

    def pool_delete(self):
        r = self._neutron(['lb-pool-delete', self.pool_name])
        assert r, "Deleted pool: %s" % self.pool_name


#
# Tests
#

demo_creds()


def test_pool_create():
    lb = NeutronLB()


def test_pool_delete():
    lb = NeutronLB()
    lb.pool_delete()


def test_lb():
    lb = NeutronLB()
    raise 'incomplete'


# Create pool

# neutron lb-pool-create --lb-method ROUND_ROBIN --name $pool_name \
#   --protocol HTTP --subnet-id $subnet_id

# wait_for_completion "neutron lb-pool-show $pool_name"


# Create VIP

# vip_name="vip_$(openssl rand -hex 6)"

# neutron lb-vip-create --name $vip_name --protocol-port 80 --protocol HTTP \
#   --subnet-id $subnet_id $pool_name

# wait_for_completion "neutron lb-vip-show $vip_name"

# echo TODO_MAYBE_ASSIGN_VIP_FLOAT


# Add members

# for ip in $MEMBER1_IP $MEMBER2_IP; do
#   neutron lb-member-create --address $ip --protocol-port 80 \
#     $pool_name | tee $t
#   member_id=$(egrep '^\| id' $t | awk '{print $4}')

#   wait_for_completion "neutron lb-member-show $member_id"
# done


# Create monitor

# neutron lb-healthmonitor-create --delay 5 --max-retries 5 --timeout 5 \
#   --type HTTP | tee $t
# hm_id=$(egrep '^\| id' $t | awk '{print $4}')


# Associate monitor

# neutron lb-healthmonitor-associate $hm_id $pool_name
