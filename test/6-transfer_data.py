from doipclient import DoIPClient
import json
with open("../diag-config.json") as f:
    diag_config = json.loads(f.read())
    #client = DoIPClient("192.168.10.30", 57344, client_logical_address=0x0e80)
    client = DoIPClient(diag_config['server']['ip_address'], 57344, client_logical_address=0x0e80)
    print(client.request_entity_status())

from doipclient.connectors import DoIPClientUDSConnector
from udsoncan.client import Client
from udsoncan.services import *
from udsoncan.common.dids import *
from udsoncan import DidCodec, Dtc, DataIdentifier
from udsoncan.exceptions import NegativeResponseException, InvalidResponseException
from udsoncan import MemoryLocation, DataFormatIdentifier

config = {
    'exception_on_negative_response': True,
    'exception_on_invalid_response': True,
    'tolerate_zero_padding': True,
    'ignore_all_zero_dtc': True,
    'request_timeout': 2,  # Request timeout(seconds)
    'data_identifiers': {
        DataIdentifier.VIN: DidCodec('17s'),  # Assume we want to read the vehicle identification number (VIN)
        DataIdentifier.ActiveDiagnosticSession: DidCodec('B')  # Assume we want to read the current diagnostic session
    }
}

uds_connection = DoIPClientUDSConnector(client)
with Client(uds_connection, config=config) as uds_client:
    try:
        block_sequence_counter = 1  # Data block sequence counter, adjust as needed
        data_to_transfer = b'\x01\x02\x03\x04\x05'  # Data to be transmitted

        # Send a request to transfer data
        response = uds_client.transfer_data(block_sequence_counter, data_to_transfer)

        # Chcek the response
        if response.positive:
            print("Data transfer successful")
            # continue transferring more chunks if necessary ...
        else:
            print("Data transfer failed")

    except NegativeResponseException as e:
        print(f"Server responded with a negative response: {e.response.code_name}")
    except InvalidResponseException as e:
        print(f"Server responded with an invalid response")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

