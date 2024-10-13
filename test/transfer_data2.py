import sys

from udsoncan import MemoryLocation, DataFormatIdentifier
from udsoncan.exceptions import NegativeResponseException, InvalidResponseException
from udsoncan import DidCodec, Dtc, DataIdentifier
from udsoncan.common.dids import *
from udsoncan.services import *
from udsoncan.client import Client
from doipclient.connectors import DoIPClientUDSConnector
from doipclient import DoIPClient

import json
with open("../diag-config.json") as f:
    diag_config = json.loads(f.read())
    client = DoIPClient(diag_config['server']['ip_address'], 57344, client_logical_address=0x0e80)
    print(client.request_entity_status())

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

file_path = sys.argv[1]
max_number_of_block_length = 0x0fa2 - 2
uds_connection = DoIPClientUDSConnector(client)

with Client(uds_connection, config=config) as uds_client:
    try:
        with open(file_path, 'rb') as file:
            block_sequence_counter = 1  # Initialize the data block sequence counter
            while True:
                data_to_transfer = file.read(max_number_of_block_length)  # Read the file content according to the maximum length
                if not data_to_transfer:
                    break  # If there is no data, end the loop

                # Send a request to transfer data
                response = uds_client.transfer_data(block_sequence_counter, data_to_transfer)
                block_sequence_counter += 1  # Update the data block sequence counter

                # Check the response
                if not response.positive:
                    print("Data transfer failed")
                    break  # If the transfer files, end the loop

        print("Data transfer successful")

    except NegativeResponseException as e:
        print(f"Server responded with a negative response: {e.response.code_name}")
    except InvalidResponseException as e:
        print("Server responded with an invalid response")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
