from lib.client import DoIPClient

from doipclient.connectors import DoIPClientUDSConnector
from udsoncan.client import Client
from udsoncan.services import *
from udsoncan.common.dids import *
from udsoncan import DidCodec
from udsoncan import Dtc
from udsoncan import DataIdentifier
from udsoncan import Routine
from udsoncan.exceptions import NegativeResponseException, InvalidResponseException
from udsoncan import MemoryLocation
from udsoncan import DataFormatIdentifier

import time
import os
import json
import sys
import pdb

from pathlib import Path

script_path = Path(__file__).resolve()
script_dir = script_path.parent

# E/E config
with open(f"{script_dir}/diag-config.json") as f:
    diag_config = json.loads(f.read())

# DoIP/UDS config
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

def calculate_key(seed):
    # This should be your key calculation logic
    # As an example, we simply return the seed value as the key
    return seed


client = DoIPClient(diag_config['server']['ip_address'], 57344, client_logical_address=0x0e80)
print(client.request_entity_status())
uds_connection = DoIPClientUDSConnector(client)

# [1] Session Control
def sess_change(session):
    with Client(uds_connection) as uds_client:
        uds_client.change_session(session)
        if session == 1:
            print("Change a Session to defaultSession")
        elif session == 2:
            print("Change a Session to programmingSession")
        elif session == 3:
            print("Change a Session to extendedSession")


# [2] Security Access
def security_access(subfn, seed=None):
    # Assume this is your key calculation function
    with Client(uds_connection, config=config) as uds_client:
        try:
            if subfn == 'request_seed':
                # Request a seed
                response = uds_client.request_seed(level=1)  # security_level is set according to the actual situation
                seed = response.service_data.seed
                print(f"Received seed: {seed}")
                return seed

            if subfn == 'send_key':
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


# [3] Routine
def routine():
    with Client(uds_connection, config=config) as uds_client:
        try:
            # Execute the diagnostic routine. the routine ID and options need to be determined according to the specific situation
            routine_id = Routine.EraseMemory  # Assumed routine ID
            #routine_option = random.randbytes(8)  # Hypothetical routine option
            routine_option = os.urandom(8)  # Assumed routine option
            
            # start the routine
            response = uds_client.start_routine(routine_id, routine_option)
            if response.positive:
                print("Routine start request completed succesesfully")
            else:
                print("Routine start request failed")

        except NegativeResponseException as e:
            print(f"Server responded with a negative response: {e.response.code_name}")
        except InvalidResponseException as e:
            print("Server responded with an invalid response")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

def requeset_download(pkg_size):
    with Client(uds_connection, config=config) as uds_client:
        try:
            # The memory address and size
            #memory_location = MemoryLocation(address=0x1234, memorysize=0x1000, address_format=32, memorysize_format=32)
            print(f"Package size: {hex(pkg_size)}")
            memory_location = MemoryLocation(address=0x1234, memorysize=pkg_size, address_format=32, memorysize_format=32)

            # Data format
            data_format = DataFormatIdentifier(compression=0, encryption=0)

            # Send download request
            response = uds_client.request_download(memory_location, data_format)

            # Check the response
            if response.positive:
                print("Download request accepted")
                # perform data transfer ...
            else:
                print("Download request was not accepted")

        except NegativeResponseException as e:
            print(f"Server responded with a negative response: {e.response.code_name}")
        except InvalidResponseException as e:
            print(f"Server responded with an invalid response")
        except Exception as e:
            print(f"An error occurred: {str(e)}")


def transfer_data():
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

def transfer_data2(pkg_file_path):
    config['request_timeout'] = 2  # Request timeout(seconds)
    #max_number_of_block_length = 0x0fa2 - 2
    max_number_of_block_length = 0x1000 - 2  # 4K
    #max_number_of_block_length = 0x4000 - 2   # 16K
    #max_number_of_block_length = 0x10000 - 2 # 64K
    with Client(uds_connection, config=config) as uds_client:
        print("Data transfer start !")
        try:
            with open(pkg_file_path, 'rb') as file:
                block_sequence_counter = 1  # Initialize the data block sequence counter
                t_s = time.time()
                while True:
                    data_to_transfer = file.read(max_number_of_block_length)  # Read the file content according to the maximum length
                    if not data_to_transfer:
                        break  # If there is no data, end the loop

                    # Send a request to transfer data
                    response = uds_client.transfer_data(block_sequence_counter, data_to_transfer)
                    block_sequence_counter += 1  # Update the data block sequence counter

                    # block_sequence_counter => [00~FF]
                    if block_sequence_counter > 255:
                        block_sequence_counter = 0

                    # Check the response
                    if not response.positive:
                        print("Data transfer failed")
                        break  # If the transfer files, end the loop

            print("Data transfer successful")
            t_e = time.time()
            print(f"Transfer data file: {pkg_file_path}")
            print(f"Transfer data elapsed time(s): {t_e-t_s}")

        except NegativeResponseException as e:
            print(f"Server responded with a negative response: {e.response.code_name}")
        except InvalidResponseException as e:
            print("Server responded with an invalid response")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

def transfer_data_exit():
    config['request_timeout'] = 2  # Request timeout(seconds)
    with Client(uds_connection, config=config) as uds_client:
        try:
            response = uds_client.request_transfer_exit()
            
            if response.positive:
                print("Transfer completed successfully")
            else:
                print("Transfer and request failed")

        except NegativeResponseException as e:
            print(f"Server responded with a negative response: {e.response.code_name}")
        except InvalidResponseException as e:
            print("Server responded with an invalid response")
        except Exception as e:
            print(f"An error occurred: {str(e)}")


def main():
    # [1] Session Control (default[1] -> extended[3])
    sess_change(DiagnosticSessionControl.Session.extendedDiagnosticSession)
    time.sleep(1)

    # [2] Security Access (request seed, send key)
    security_access()
    time.sleep(1)

    # [3] Routine (start routine)
    routine()
    time.sleep(1)

    #pkg_file_path = f'{script_dir}/ota/cluster_ota-20M.bin'
    pkg_file_path = f'{script_dir}/ota/cluster_ota-10M.bin'
    if not os.path.exists(pkg_file_path):
        print(f"File not found.. [{pkg_file_path}]")
        exit(-1)

    file_size = os.path.getsize(pkg_file_path)

    # [4] Request download
    requeset_download(file_size)
    time.sleep(1)

    # [5] Transfer data
    transfer_data2(pkg_file_path)
    time.sleep(1)

    # [6] Transfer data exit
    transfer_data_exit()
    time.sleep(1)

    # [99] Session Control (extended[3] -> default[1])
    sess_change(DiagnosticSessionControl.Session.defaultSession)


def main_security_access_unlocked_server():
    seed = security_access('request_seed')
    time.sleep(1)

    security_access('send_key', seed)
    time.sleep(1)

    seed = security_access('request_seed')
    time.sleep(1)


def main_debug():
    #pkg_file_path = f'{script_dir}/ota/cluster_ota-20M.bin'
    pkg_file_path = f'{script_dir}/ota/cluster_ota-10M.bin'
    if not os.path.exists(pkg_file_path):
        print(f"File not found.. [{pkg_file_path}]")
        exit(-1)

    file_size = os.path.getsize(pkg_file_path)

    # [4] Request download
    requeset_download(file_size)
    time.sleep(1)

    # [5] Transfer data
    transfer_data2(pkg_file_path)
    time.sleep(1)

    # [6] Transfer data exit
    transfer_data_exit()
    time.sleep(1)




if __name__ == "__main__":
    #main()
    main_debug()
