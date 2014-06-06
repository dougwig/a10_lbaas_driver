
import os
import re
import subprocess
import tempfile
import time
import uuid

import local_env as e
import requests


def find(str, regex):
    m = re.search(regex, str, re.MULTILINE)
    if m is not None:
        return m.group(1)
    else:
        return ""


class NeutronLB(object):

    def __init__(self, lb_method='ROUND_ROBIN', protocol='HTTP'):
        self.instance_subnet_id = self.get_subnet_id(e.INSTANCE_NETWORK_NAME)
        self.lb_subnet_id = self.get_subnet_id(e.LB_NETWORK_NAME)
        self.pool_name = self._random_hex()
        self.lb_pool_create(self.pool_name, self.instance_subnet_id,
                            lb_method, protocol)
        self.members = {}

    def _random_hex(self):
        return uuid.uuid4().hex[0:12]

    def _neutron(self, cmd):
        print("NEUTRON: ", cmd)
        z = subprocess.check_output(["neutron"] + cmd)
        print("result:\n", z)
        return z

    def _wait_for_completion(self, cmd):
        start = time.time()
        now = start
        r = ''
        while ((now - start) < 10):
            r = self._neutron(cmd)
            if find(r, "(PENDING)") != "PENDING":
                break

        if find(r, "(ACTIVE)") == "":
            raise "error: action did not complete successfully"

    def get_subnet_id(self, network_name):
        r = self._neutron(['net-show', network_name])
        return find(r, "^\| subnets.*\| ([^\s]+)")

    # method: None, ROUND_ROBIN, LEAST_CONNECTIONS, SOURCE_IP
    # protocol: HTTP, HTTPS, TCP
    def lb_pool_create(self, pool_name, subnet_id, method='ROUND_ROBIN',
                       protocol='HTTP'):
        self._neutron(['lb-pool-create', '--name', pool_name,
                       '--lb-method', method, '--protocol', protocol,
                       '--subnet-id', subnet_id])
        self._wait_for_completion(['lb-pool-show', pool_name])

    def pool_delete(self):
        r = self._neutron(['lb-pool-delete', self.pool_name])
        assert r.strip() == "Deleted pool: %s" % self.pool_name

    # protocol: TCP, HTTP, HTTPS
    # persistence: None, HTTP_COOKIE, SOURCE_IP, APP_COOKIE
    def vip_create(self, port=80, protocol='HTTP', persistence=None):
        self.vip_name = self._random_hex()
        a = ['lb-vip-create', '--name', self.vip_name,
             '--protocol', protocol,
             '--protocol-port', str(port),
             '--subnet-id', self.lb_subnet_id, self.pool_name]
        if persistence is not None:
            a.append('--session-persistence')
            a.append('type=dict')
            if persistence is 'APP_COOKIE':
                a.append("type=%s,cookie_name=mycookie" % persistence)
            else:
                a.append("type=%s" % persistence)
        r = self._neutron(a)
        # port_id = find(r, "^\| port_id.*\| ([^\s]+)")
        self.vip_ip = find(r, "^\| address.*\| ([^\s]+)")
        print("INTERNAL VIP_IP ", self.vip_ip)
        self._wait_for_completion(['lb-vip-show', self.vip_name])

    def vip_destroy(self):
        self._neutron(['lb-vip-delete', self.vip_name])

    def member_create(self, ip_address, port=80):
        r = self._neutron(['lb-member-create', '--address', ip_address,
                           '--protocol-port', str(port), self.pool_name])
        member_id = find(r, "^\| id.*\| ([^\s]+)")
        self._wait_for_completion(['lb-member-show', member_id])
        self.members[ip_address] = member_id

    def member_destroy(self, ip_address):
        self._neutron(['lb-member-delete', self.members[ip_address]])

    # expected: 200, 200-299, 200,201
    # http_method: GET, POST
    # url_path: URL, "/"
    # mon_type: PING, TCP, HTTP, HTTPS
    def monitor_create(self, delay=5, retries=5, timeout=5, mon_type='HTTP'):
        r = self._neutron(['lb-healthmonitor-create', '--delay', str(delay),
                           '--max-retries', str(retries),
                           '--timeout', str(timeout),
                           '--type', mon_type])
        self.monitor_id = find(r, "^\| id.*\| ([^\s]+)")

    def monitor_destroy(self):
        self._neutron(['lb-healthmonitor-delete', self.monitor_id])

    def monitor_associate(self):
        r = self._neutron(['lb-healthmonitor-associate', self.monitor_id,
                           self.pool_name])
        assert r.strip() == "Associated health monitor %s" % self.monitor_id

    def monitor_disassociate(self):
        self._neutron(['lb-healthmonitor-disassociate', self.monitor_id,
                       self.pool_name])

    def destroy(self):
        self.monitor_disassociate()
        self.monitor_destroy()
        member_list = [e.MEMBER1_IP, e.MEMBER2_IP]
        for ip in member_list:
            self.member_destroy(ip)
        self.vip_destroy()
        self.pool_delete()


class AxSSH(object):

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

        return lines[4:-3]

    def config_get(self):
        commands = ['en\r\n',
                    '\r\n',
                    'terminal length 0\r\n',
                    'show run\r\n',
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

    def config_gets(self):
        return ''.join(self.config_get())

    def config_get_template(self, name):
        f = open("tests/conf/%s.config" % name)
        z = f.read()
        f.close()
        return z

    def config_get_and_compare_to_template(self, name):
        s = self.config_gets()
        f = open('/tmp/axcfg.out.%s' % os.environ['USER'], 'w')
        f.write(s)
        f.close()
        # TODO(dougw) assert self.config_get_template(name) == s


def verify_ax(template_name='base'):
    ax = AxSSH(e.AX21_HOST, e.AX21_USERNAME, e.AX21_PASSWORD)
    ax.config_get_and_compare_to_template('base')


#
# Tests
#

# def test_pool_create():
#     lb = NeutronLB()
# def test_pool_delete():
#     lb = NeutronLB()
#     lb.pool_delete()
# def test_vip_create():
#     lb = NeutronLB()
#     lb.vip_create()


def setup_lb(lb_method, protocol, persistence):
    lb = NeutronLB(lb_method=lb_method, protocol=protocol)
    lb.vip_create(protocol=protocol, persistence=persistence)

    member_list = [e.MEMBER1_IP, e.MEMBER2_IP]
    for ip in member_list:
        lb.member_create(ip)

    lb.monitor_create()
    lb.monitor_associate()
    return lb


def pull_data(url_base, vip_ip):
    member_list = [e.MEMBER1_IP, e.MEMBER2_IP]
    members = {}
    for ip in member_list:
        members[ip] = requests.get("http://%s/" % ip).text

    print("LB URL ", "%s%s/" % (url_base, vip_ip))
    lb_data = requests.get("%s%s/" % (url_base, vip_ip)).text
    print("DATA LB ++%s++" % lb_data)

    matching_data = False
    for ip, data in members.items():
        if data == lb_data:
            matching_data = True
            break

    assert matching_data


def end_to_end(lb_method, protocol, persistence, url_base):
    e.demo_creds()
    verify_ax()

    # Step 1, setup LB via neutron
    lb = setup_lb(lb_method, protocol, persistence)

    # Step 2, grab the configuration from the AX and verify
    verify_ax('lb')

    # Step 3, pull some data through the LB and verify
    pull_data(url_base, lb.vip_ip)

    # Whoa, all done, success.
    lb.destroy()

    # method: None, ROUND_ROBIN, LEAST_CONNECTIONS, SOURCE_IP
    # protocol: HTTP, HTTPS, TCP
    # protocol: TCP, HTTP, HTTPS
    # persistence: None, HTTP_COOKIE, SOURCE_IP, APP_COOKIE


def test_lb():
    end_to_end('ROUND_ROBIN', 'HTTP', None, 'http://')


def test_alt_lb():
    end_to_end('LEAST_CONNECTIONS', 'HTTP', 'HTTP_COOKIE', 'http://')


def test_lb_matrix():
    protocols = [
        ('HTTP', 'http://'),
        ('TCP', 'http://'),
        ('HTTPS', 'https://')
    ]
    methods = ['ROUND_ROBIN', 'LEAST_CONNECTIONS', 'SOURCE_IP']
    persists = [None, 'HTTP_COOKIE', 'SOURCE_IP']
    for protocol, url_base in protocols:
        for method in methods:
            for persistence in persists:
                end_to_end(method, protocol, persistence, url_base)
