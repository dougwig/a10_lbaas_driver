#!/bin/bash

changes_needed=0

if [ ! -f etc/a10networks_config.ini.sample ]; then
  echo "ERROR: must be run from root of a10 driver git directory"
  exit 1
fi

NEUTRON_IMPORT=` printf "import neutron\nprint neutron.__file__\n" | python`
NEUTRON_DIR=`dirname $NEUTRON_IMPORT`
if [ -z “$NEUTRON_DIR” ]; then
  echo “ERROR: python could not find neutron”
  exit 1
else
  echo "Installing neutron driver into $NEUTRON_DIR"
  cd neutron/neutron/services/loadbalancer/drivers
  sudo mkdir -p $neutron_dir/services/loadbalancer/drivers/
  sudo cp -r a10networks/ $neutron_dir/services/loadbalancer/drivers/
  cd - >/dev/null
fi

ini_dir="/etc/neutron/services/loadbalancer/a10networks"
ini_file="a10networks_config.ini"

if [ ! -f "$ini_dir/$ini_file" ]; then
  echo "Installing sample INI file into $ini_dir"
  sudo mkdir -p "$ini_dir"
  sudo cp etc/a10networks_config.ini.sample "$ini_dir/$ini_file"
  echo "TODO: Edit for your site: $ini_dir/$ini_file"
  changes_needed=1
else
  echo "Leaving existing $ini_file in place"
fi

n=`sudo cat /etc/neutron/neutron.conf | egrep -c '^service_provider.*ThunderDriver\:default'`
if [ $n -eq 0 ]; then
  echo "TODO: Enable ThunderDriver in neutron.conf (see README)"
  changes_needed=1
fi

if [ $changes_needed -ne 0 ]; then
  echo "TODO: Restart neutron-server after making the changes above."
else
  echo "Restarting neutron server"
  sudo service neutron-server restart
fi
echo "Install complete"

