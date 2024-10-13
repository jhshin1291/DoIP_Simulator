from doipclient import DoIPClient
import json
with open("../diag-config.json") as f:
    diag_config = json.loads(f.read())

address, announcement = DoIPClient.get_entity(eid=b'\x02\x00\x00\x00\x10\x01', ecu_ip_address=diag_config['client']['broadcast_address'])
logical_address = announcement.logical_address
ip, port = address
vin = announcement.vin
gid = announcement.gid
eid = announcement.eid
ip, port = address
print(ip, port)
print(f"Logical Address: {hex(logical_address)}")
print(f"VIN: {vin}")
print(f"GID: {''.join(f'{i:02x}' for i in gid)}")
print(f"EID: {''.join(f'{i:02x}' for i in eid)}")
