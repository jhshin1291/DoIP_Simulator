from doipclient import DoIPClient
import pdb
import time
import json

with open("../diag-config.json") as f:
    diag_config = json.loads(f.read())
    #client = DoIPClient("192.168.10.30", 57344, client_logical_address=0x0e80)
    client = DoIPClient(diag_config['server']['ip_address'], 57344, client_logical_address=0x0e80)
    print(client.request_entity_status())

from doipclient.connectors import DoIPClientUDSConnector
from udsoncan.client import Client
from udsoncan.services import *

uds_connection = DoIPClientUDSConnector(client)
with Client(uds_connection) as uds_client:
    pdb.set_trace()
    print("[Session Change] defaultSession(1) -> ProgrammingSession(2)")
    uds_client.change_session(DiagnosticSessionControl.Session.programmingSession)
    time.sleep(1)

    print("[Session Change] ProgrammingSession(2) -> extendedDiagnosticSession(3)")
    uds_client.change_session(DiagnosticSessionControl.Session.extendedDiagnosticSession)
    time.sleep(1)

    print("[Session Change] extendedDiagnosticSession(3) -> defaultSession(1)")
    uds_client.change_session(DiagnosticSessionControl.Session.defaultSession)
    time.sleep(1)
