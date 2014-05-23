# A10 Networks LBaaS Driver for Thunder and AX Series Appliances

## Introduction:

This guide is for the A10 Networks LBaaS Driver, which is specifically designed to manage Thunder and AX Series Application Delivery Controller (ADC) appliances. 

In this installation guide, we will cover the architecture of the A10/OpenStack environment and the requirements for installing the A10 LBaaS Driver. Expectedly, an updated community-supported driver will be in the Juno release of OpenStack.  Note that the community version of this driver is different from what A10 supports—the current community version does not support the spin up of software instances. This feature will be available in the later Juno release, but should the user desire a greater degree of customization to extend Horizon and other components, we recommend using A10’s version as the community supported model will present less feature versatility than our in-house solution.

  > This driver only supports axAPI version 2.1. 
  >
  > The latest version of this document can be found at https://github.com/a10networks/a10_lbaas_driver/README.md

## Implementation:

![image2](https://cloud.githubusercontent.com/assets/1424573/2849597/47192238-d0df-11e3-9e1e-9e234be58412.png)

## Network Architecture:

You must configure the network elements of the Thunder appliance for OpenStack’s Havana and Icehouse releases. 

## SNATED:

![image3](https://cloud.githubusercontent.com/assets/1424573/2849593/4708b7ea-d0df-11e3-8ed7-f6bf73b31535.png)

## VLAN:

![image4](https://cloud.githubusercontent.com/assets/1424573/2849595/471863d4-d0df-11e3-87c7-2423aaaaedca.png)

## Installation steps:

### Step 1:

Make sure you have the neutron-lbaas-agent installed.

### Step 2: 

Download the driver from: <https://github.com/a10networks/a10_lbaas_driver>

![image5](https://cloud.githubusercontent.com/assets/1424573/2849598/4719501e-d0df-11e3-8408-4b06ce359a43.png)

### Step 3:

Move the directories and files to the appropriate locations.

`neutron/neutron/services/loadbalancer/drivers/a10networks -> your neutron directory`

#### Example:

```
NEUTRON_IMPORT=` printf "import neutron\nprint neutron.__file__\n" | python`
NEUTRON_DIR=`dirname $NEUTRON_IMPORT`
if [ -z “$NEUTRON_DIR” ]; then
echo “ERROR: neutron is not installed”
else
git clone https://github.com/a10networks/a10_lbaas_driver
cd a10_lbaas_driver/neutron/neutron/services/loadbalancer/drivers
sudo cp -r a10networks/ $neutron_dir/services/loadbalancer/drivers/
cd –
fi
```

![image6](https://cloud.githubusercontent.com/assets/1424573/2849600/47263414-d0df-11e3-81a8-f2fed20c2d01.png)

### Step 4:

Modify `/etc/neutron/neutron.conf`

In the “service_providers” section of the neutron.conf file, add the following line:

```
service_provider = LOADBALANCER:A10Networks:neutron.services.loadbalancer.drivers.a10networks.thunder.ThunderDriver:default
```

The service provider section, as it appears in the neutron.conf file, is displayed below for reference.

```
[service_providers]

# Specify service providers (drivers) for advanced services like loadbalancer, VPN, Firewall.
# Must be in form:
# service_provider=<service_type>:<name>:<driver>[:default]
# List of allowed service types includes LOADBALANCER, FIREWALL, VPN
# Combination of <service type> and <name> must be unique; <driver> must also be unique
# This is multiline option, example for default provider:
# service_provider=LOADBALANCER:name:lbaas_plugin_driver_path:default
# example of non-default provider:
# service_provider=FIREWALL:name2:firewall_driver_path
# --- Reference implementations ---
#service_provider=LOADBALANCER:Haproxy:neutron.services.loadbalancer.drivers.haproxy.plugin_driver.HaproxyOnHostPluginDriver:default
#service_provider=VPN:openswan:neutron.services.vpn.service_drivers.ipsec.IPsecVPNDriver:default
service_provider = LOADBALANCER:A10Networks:neutron.services.loadbalancer.drivers.a10networks.thunder.ThunderDriver:default #add to configuration here
```

### Step 5:

Create and configure the a10networks section of the a10networks_config.ini. The file is located in:

`/etc/neutron/services/loadbalancer/a10networks/a10networks_config.ini`

In the example given below, we show various configuration options for every device added to the network, specifying the maximum number of LSI objects and ADP partitions which can be issued per device. In this case, we configured two different nodes for LSI and ADP. Note that you can add up to 50 nodes.

#### Terminology:

* __LSI__ – Logical Service Instance. This configuration is realized by multiple tenant VIPs in the shared partition. 
* __ADP__ – Application Delivery Partition. This refers to the RBAC partitions on the Advanced Core Operating System (ACOS) on any Thunder/AX device.

```
# Instructions:
#     Add each device as a dictionary object in the Device Section.
#
#     Configuration options are as follows:
#
#         host:<IP|FQDN>
#         username:acos user
#         password:user password
#         skip_version_check: True if driver verification of ACOS version
#             should be skipped.  Default: false
#         status: True if ax should be used, false otherwise.  Default: True
#         autosnat: Source address translation is configured on the VIP.
#         api_version: API version
#         v_method: Choices in this version(ADP, LSI)
#         MAX LSI: Number of objects that can be added to system range(512-10k+) and is model dependant.
#         MAX ADP: 128 for all models except vThunder which is 32
#
#         Max L3V paritions for the device(currently not supported with the community version),
#         MAX L3V is modules specific 32-1023
#         'use_float': utilize the floating address of the member and not the actual interface ip.
#         "method": Placement policy. right now hash is th only thing supported. This is utilized if there ar more than one
#         acos device configured.

[a10networks]
ax1 = {"name":"ax1", "host": "192.168.212.120",
               "username": "admin",
               "password": "a10", "status": "1", "autosnat": "True",
      "api_version": "2.1", "v_method": "LSI",
               "max_instance": "5000" , "use_float": "True", "method": "hash"}
ax2 = {"name":"ax2", "host": "192.168.212.10",
      "username": "admin",
      "password": "a10", "status": "1", "autosnat": "True",
      "api_version": "2.1", "v_method": "ADP",
      "max_instance": "5000" , "use_float": "True", "method": "hash"}
```
### Step 6:

Restart Neutron to verify successful completion of driver installation.

#### Example:

```
service neutron-server restart
```

__Note:__ Make sure the user utilizes their own method to avoid service interruption.

## Validation:

Validate the configurations are correct and customize further settings if necessary.

### Step 1:

Login to the OpenStack dashboard.

![image7](https://cloud.githubusercontent.com/assets/1424573/2849592/46f86d4a-d0df-11e3-8b57-25d2d796f1cc.png)

### Step 2:

Under the “Network” menu, go to the “Load Balancers” tab and select “Add Pool”:

![image8](https://cloud.githubusercontent.com/assets/1424573/2849594/47169bda-d0df-11e3-9fda-af2da76cdb00.png)

Once you have added a pool, a success message should appear. 

![image9](https://cloud.githubusercontent.com/assets/1424573/2849599/471a7c14-d0df-11e3-918e-778dbea9be45.png)

### Step 3:

Login to the GUI on your Thunder or AX device, and validate which configuration was applied if the ADPs are set. The ADP name is the first 13 characters of the tenant ID. 

![image10](https://cloud.githubusercontent.com/assets/1424573/2849596/4718b0b4-d0df-11e3-9a6b-506bb832dcce.png)

_Repeat this for all configuration steps, then delete all resources if ADPs are configured. They should be deleted when the tenant has no more resources configured._

__Need further clarification on this.__

## Contributing

1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create new Pull Request

