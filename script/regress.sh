#!/bin/bash

# Quick sanity check for A10 LB driver; tested on Icehouse.

if [ ! -f README.md ]; then
  echo "ERROR: must be run from root of a10 driver git directory"
  exit 1
fi

t=/tmp/regress.$USER

# Get the local Neutron/Openstack/Ax settings

. test/local.env

# Now we create an INI file with that info

echo TODO_CREATE_INI

# Finally, make sure everything is installed and restarted

# script/install.sh 2>&1 | tee $t
# if [ $(grep -c TODO $t) -ne 0 ]; then
#   echo "ERROR: install.sh must run clean before testing"
# fi

# # Give the restart time to settle
# sleep 5
# XXX: instead of that sleep, more efficient to wait for this log:
#  "Neutron service started, listening on 0.0.0.0:9696"

wait_for_completion() {
  i=0
  while [ $i -lt 200 ]; do
    sleep 0.5
    eval "$1" | tee $t
    if [ $(grep -c PENDING $t) -eq 0 ]; then
      break
    fi
    i=$((i+1))
  done

  if [ $(grep -c ACTIVE $t) -eq 0 ]; then
    echo "ERROR: $1: failed"
    exit 1
  fi
}

# Get non-admin tenant permissions

. $PATH_TO_DEMO_OPENRC

pool_name="pool_$(openssl rand -hex 6)"
subnet_id=$(neutron net-show $PRIVATE_NETWORK_NAME | grep 'subnets' | \
  awk '{print $4}')

# Create pool

neutron lb-pool-create --lb-method ROUND_ROBIN --name $pool_name \
  --protocol HTTP --subnet-id $subnet_id

wait_for_completion "neutron lb-pool-show $pool_name"


# Create VIP

vip_name="vip_$(openssl rand -hex 6)"

neutron lb-vip-create --name $vip_name --protocol-port 80 --protocol HTTP \
  --subnet-id $subnet_id $pool_name

wait_for_completion "neutron lb-vip-show $vip_name"

echo TODO_MAYBE_ASSIGN_VIP_FLOAT


# Add members

for ip in $MEMBER1_IP $MEMBER2_IP; do
  neutron lb-member-create --address $ip --protocol-port 80 \
    $pool_name | tee $t
  member_id=$(egrep '^\| id' $t | awk '{print $4}')

  wait_for_completion "neutron lb-member-show $member_id"
done


# Create monitor

neutron lb-healthmonitor-create --delay 5 --max-retries 5 --timeout 5 \
  --type HTTP | tee $t
hm_id=$(egrep '^\| id' $t | awk '{print $4}')


# Associate monitor

neutron lb-healthmonitor-associate $hm_id $pool_name


# Validate AX config

echo TODO_VALIDATE_AX
# printf "en\r\n\r\nshow run | exc \\!\r\nexit\r\nexit\r\ny\r\n" | ssh admin@10.10.100.20


# Pass traffic through the LB

echo TODO_PULL_LB_TRAFFIC
#curl http://${vip_ip}/

####

# update tests
# delete tests
# loop for float vs non-float
# loop for partition vs shared




