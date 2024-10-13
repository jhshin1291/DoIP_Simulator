import random
import os

from udsoncan import MemoryLocation, DataFormatIdentifier
from udsoncan.exceptions import NegativeResponseException, InvalidResponseException
from udsoncan import DidCodec, Dtc, DataIdentifier
from udsoncan.common.dids import *
from udsoncan.services import *
from udsoncan.client import Client
from udsoncan import DataIdentifier, Routine
from doipclient.connectors import DoIPClientUDSConnector
from doipclient import DoIPClient

import json
with open("../diag-config.json") as f:
    diag_config = json.loads(f.read())
    #client = DoIPClient("192.168.10.30", 57344, client_logical_address=0x0e80)
    client = DoIPClient(diag_config['server']['ip_address'], 57344, client_logical_address=0x0e80)
    print(client.request_entity_status())

config = {
    'exception_on_negative_response': True,
    'exception_on_invalid_response': True,
    'tolerate_zero_padding': True,
    'ignore_all_zero_dtc': True,
    'request_timeout': 2,  # request timeout(s)
    'data_identifiers': {
        DataIdentifier.VIN: DidCodec('17s'),  # Assume we want to read the vehicle identificaion number (VIN)
        DataIdentifier.ActiveDiagnosticSession: DidCodec('B')  # Assume we want to read the current diagnostic session
    }
}


uds_connection = DoIPClientUDSConnector(client)
with Client(uds_connection, config=config) as uds_client:
    try:
        # Execute the diagnostic routine. the routine ID and options need to be determined according to the specific situation
        routine_id = Routine.EraseMemory  # Assumed routine ID
        #routine_option = random.randbytes(8)  # Hypothetical routine option
        routine_option = os.urandom(8)  # Assumed routine option
        
        # start the routine
        response = uds_client.start_routine(routine_id, routine_option)
        if response.positive:
            print("Transfer completed succesesfully")
        else:
            print("Transfer end request failed")

    except NegativeResponseException as e:
        print(f"Server responded with a negative response: {e.response.code_name}")
    except InvalidResponseException as e:
        print("Server responded with an invalid response")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
