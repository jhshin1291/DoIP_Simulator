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

config = {
    'exception_on_negative_response': True,
    'exception_on_invalid_response': True,
    'tolerate_zero_padding': True,
    'ignore_all_zero_dtc': True,
    'data_identifiers': {
        DataIdentifier.VIN: DidCodec('17s'),  # Assume we want to read the vehicle identification number (VIN)
        DataIdentifier.ActiveDiagnosticSession: DidCodec('B')  # Assume we want to read the current diagnostic session
    }
}

# Assume this is your key calculation function
def calculate_key(seed):
    # This should be your key calculation logic
    # As an example, we simply return the seed value as the key
    return seed

uds_connection = DoIPClientUDSConnector(client)
with Client(uds_connection, config=config) as uds_client:
    try:
        # Request a seed
        response = uds_client.request_seed(level=1)  # security_level is set according to the actual situation
        seed = response.service_data.seed
        print(f"Received seed: {seed}")

        # Calculate the key
        key = calculate_key(seed)
        print(f"Calculated key: {key}")

        # Send key
        uds_client.send_key(level=1, key=key)  # security_level needs to be the same as request_seed
        print("Access granted")

    except NegativeResponseException as e:
        print(f"Server responded with a negative response: {e.response.code_name}")
    except InvalidResponseException as e:
        print(f"Server responded with an invalid response")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
