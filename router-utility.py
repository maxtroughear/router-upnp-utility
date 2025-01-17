# Script to open/close port via Upnp
# This script has been made for the DPC configuration
# The router must have upnp unable (often enable by default)
# It uses a config file (csv) to list the wanted devices and then is
# usable with python app.py [add|delete|list]
#
# If the router is not found (but has upnp enabled), this may be related to the linux firewall


import upnpy
import csv
import sys

# A mapping represent a port translation from a router to an host
# The redirection is done: from router (ext_port) to int_host at int_port (int stands for internal)
class Mapping:
    def __init__(self, service, description: str, protocol: str, ext_port: int, int_port: int, int_host: str):
        self.service = service
        self.description = description
        self.protocol = protocol
        self.ext_port = ext_port
        self.int_port = int_port
        self.int_host = int_host

    def add(self):
        self.service.AddPortMapping(
            NewRemoteHost='',
            NewExternalPort=self.ext_port,
            NewProtocol=self.protocol,
            NewInternalPort=self.int_port,
            NewInternalClient=self.int_host,
            NewEnabled=1,
            NewPortMappingDescription=self.description,
            NewLeaseDuration=0 # 0 means infinite
        )
        print(f" {self} added !")


    def delete(self):
        self.service.DeletePortMapping(
            NewRemoteHost='',
            NewExternalPort=self.ext_port,
            NewProtocol=self.protocol
        )
        print(f"{self} deleted !")

    def __str__(self):
        return f"Mapping rule: {self.ext_port}->{self.int_port} on {self.int_host} with {self.protocol} ({self.description})"

# Get the correct service to add mapping
# Every router has several services, which have several actions
# Since every router are naming them differently, we then search for the service
# having the UPnP AddPortMapping action
def get_upnp_service(services, requested_action: str):
    for service in services:
        for action in service.get_actions():
            if requested_action in action.name:
                return service
    raise Exception(f"Unable to get upnp service: {requested_action}\n")

# Get nat translations from csv file
def get_translations(filename, service) -> list[Mapping]:
    mappings = []
    with open(filename,'r') as csv_file:
        reader = csv.reader(csv_file)
        next(reader) # Skip the header, we only want the data here
        for r in reader:
            mappings.append(Mapping(service, *r)) # Create the Mapping object with the service and every fields

    return mappings


actions = {
    'add':'AddPortMapping',
    'delete': 'DeletePortMapping',
    'ls': 'GetListOfPortMappings',
}



if __name__ == '__main__':

    # App must be run with add, delete, or ls as args
    if len(sys.argv) != 2 or not sys.argv[1] in actions.keys():
        print("Use python router-utility.py [add|delete|ls]")
        exit()

    upnp = upnpy.UPnP()
    print("Discovering Upnp devices...")
    devices = upnp.discover(ST='urn:schemas-upnp-org:device:InternetGatewayDevice:1') # Needed in order to use get_igd
    device = devices[0]
    for d in devices:
      if "Gateway" not in d.get_friendly_name():
        continue
      device = d
      break
    print(f"Attempting to connect to {device}\n")
    services = device.get_services()
    # Get the needed service (which has the required action)
    service = get_upnp_service(services, actions[sys.argv[1]])
    print(f"Upnp device discovered: {device}\n")

    if sys.argv[1] == 'ls':
        print("> Listing rules:")
        for i in range(65655):
            try:
                entry = service.GetGenericPortMappingEntry(NewPortMappingIndex=i)
                print(Mapping(None,entry['NewPortMappingDescription'], entry['NewProtocol'], entry['NewExternalPort'], entry['NewInternalPort'], entry['NewInternalClient']))
            except:
                if i == 0:
                    print('No rules have been found')
                break
    else:
        for m in get_translations('services.csv', service):
            # Add every mapping in upnp (from the config file)
            if sys.argv[1] == 'add':
                print("> Adding rules...")
                m.add()
            elif sys.argv[1] == 'delete':
                print("> Removing rules...")
                m.delete()

    print("\ndone!")
