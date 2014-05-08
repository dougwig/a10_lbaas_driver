
import pytest
import re
import requests
import subprocess
import tempfile
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
        assert r.strip() == "Deleted pool: %s" % self.pool_name

    def vip_create(self, port=80, protocol='HTTP'):
        self.vip_name = self._random_hex()
        self._neutron(['lb-vip-create', '--name', self.vip_name,
                       '--protocol', protocol, '--protocol-port', str(port),
                       '--subnet-id', self.subnet_id, self.pool_name])
        self._wait_for_completion(['lb-vip-show', self.vip_name])
        # echo TODO_MAYBE_ASSIGN_VIP_FLOAT

    def member_create(self, ip_address, port=80):
        r = self._neutron(['lb-member-create', '--address', ip_address,
                           '--protocol-port', str(port), self.pool_name])
        member_id = find(r, "^\| id.*\| ([^\s]+)")
        self._wait_for_completion(['lb-member-show', member_id])

    def monitor_create(self, delay=5, retries=5, timeout=5, mon_type='HTTP'):
        r = self._neutron(['lb-healthmonitor-create', '--delay', str(delay),
                           '--max-retries', str(retries),
                           '--timeout', str(timeout),
                           '--type', mon_type])
        self.monitor_id = find(r, "^\| id.*\| ([^\s]+)")

    def monitor_associate(self):
        r = self._neutron(['lb-healthmonitor-associate', self.monitor_id,
                           self.pool_name])
        assert r.strip() == "Associated health monitor %s" % self.monitor_id


class AxSSH(object):
    MORE_GARBAGE = '--MORE--\r        \x08\x08\x08\x08\x08\x08\x08\x08'

    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password

    def _ssh(self, commands):
        t = tempfile.TemporaryFile()
        ssh = subprocess.Popen(['sshpass', '-p', self.password,
                                'ssh', "%s@%s" % (self.user, self.host)],
                               close_fds=True,
                               shell=False,
                               stdin=subprocess.PIPE,
                               stdout=t)

        ssh.stdin.writelines(commands)
        ssh.wait()

        t.flush()
        t.seek(0)
        lines = t.readlines()
        t.close()

        fixed = []
        for line in lines:
            if line[0:len(AxSSH.MORE_GARBAGE)] == AxSSH.MORE_GARBAGE:
                fixed.append(line[len(AxSSH.MORE_GARBAGE):])
            else:
                fixed.append(line)

        return fixed[3:-3]

    def config_get(self):
        commands = ['en\r\n',
                    '\r\n',
                    'show run\r\n',
                    ' ',
                    ' ',
                    ' ',
                    ' ',
                    ' ',
                    ' ',
                    'exit\r\n',
                    'exit\r\n',
                    'y\r\n']

        lines = self._ssh(commands)
        trim = []
        for line in lines:
            x = line.strip()
            if x == '' or x[0] == '!':
                continue
            trim.append(line)
        return trim


ax = AxSSH("10.10.100.20", "admin", "a10")
r = ax.config_get()
print "acos return = ", r
raise "foo"


#
# Tests
#

demo_creds()

# def test_pool_create():
#     lb = NeutronLB()
# def test_pool_delete():
#     lb = NeutronLB()
#     lb.pool_delete()
# def test_vip_create():
#     lb = NeutronLB()
#     lb.vip_create()


def test_lb():

    # Step 1, setup LB via neutron

    lb = NeutronLB()
    lb.vip_create()

    member_list = [MEMBER1_IP, MEMBER2_IP]
    for ip in member_list:
        lb.member_create(ip)

    lb.monitor_create()
    lb.monitor_associate()

    # Step 2, grab the configuration from the AX and verify

    # Step 3, pull some data through the LB and verify

    members = {}
    for ip in member_list:
        members[ip] = requests.get("http://%s/" % ip).text

    lb_data = requests.get("http://%s/" % todo).text

    matching_data = False
    for ip, data in members:
        if data == lb_data:
            matching_data = True
            break

    assert matching_data

    print "hmm, we got all the way to the bogus exception!!!!"
    raise 'incomplete'

    # Whoa, all done, success.
