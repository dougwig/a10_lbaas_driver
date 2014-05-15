# Configuration for this neutron network node!

import os

PATH_TO_ADMIN_OPENRC = os.path.join(os.environ['HOME'], 'admin-openrc.sh')
PATH_TO_DEMO_OPENRC = os.path.join(os.environ['HOME'], 'demo-openrc.sh')

INSTANCE_NETWORK_NAME = 'demo-net'
LB_NETWORK_NAME = 'ext-net'

MEMBER1_IP = '10.10.102.108'
MEMBER2_IP = '10.10.102.109'

AX21_HOST = '10.10.100.20'
AX21_PORT = '8443'
AX21_PROTOCOL = 'https'
AX21_USERNAME = 'admin'
AX21_PASSWORD = 'a10'

USE_FLOAT = True
AUTOSNAT = True

FTP_SERVER_URL = "ftp://ftp@10.10.102.2/"


def source_env(path):
    for line in open(path):
        name, value = line.split('=')
        if name[:7] == "export ":
            name = name[7:]
        os.environ[name] = value.rstrip()


def demo_creds():
    source_env(PATH_TO_DEMO_OPENRC)


def admin_creds():
    source_env(PATH_TO_ADMIN_OPENRC)
