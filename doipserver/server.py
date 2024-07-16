from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol, Factory, Protocol
import logging
import ipaddress
import socket
import struct
import time
import sys
import threading
import ssl
import yaml
from enum import IntEnum
from typing import Union
from constants import (
    A_DOIP_CTRL,
    TCP_DATA_UNSECURED,
    UDP_DISCOVERY,
    A_PROCESSING_TIME,
    LINK_LOCAL_MULTICAST_ADDRESS,
)
from messages import *

from udsoncan.Request import Request
from udsoncan.Response import Response
from udsoncan.services import *

logger = logging.getLogger("doipserver")
# 设置日志级别
logger.setLevel(logging.DEBUG)

# 创建一个流处理器并设置级别
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)

# （可选）设置日志格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)

# 将流处理器添加到logger
logger.addHandler(stream_handler)


class Parser:
    """Implements state machine for DoIP transport layer.

    See Table 16 "Generic DoIP header structure" of ISO 13400-2:2019 (E). While TCP transport
    is reliable, the UDP broadcasts are not, so the state machine is a little more defensive
    than one might otherwise expect. When using TCP, reads from the socket aren't guaranteed
    to be exactly one DoIP message, so the running buffer needs to be maintained across reads
    """

    class ParserState(IntEnum):
        READ_PROTOCOL_VERSION = 1
        READ_INVERSE_PROTOCOL_VERSION = 2
        READ_PAYLOAD_TYPE = 3
        READ_PAYLOAD_SIZE = 4
        READ_PAYLOAD = 5

    def __init__(self):
        self.reset()

    def reset(self):
        self.rx_buffer = bytearray()
        self.protocol_version = None
        self.payload_type = None
        self.payload_size = None
        self.payload = bytearray()
        self._state = Parser.ParserState.READ_PROTOCOL_VERSION

    def push_bytes(self, data_bytes):
        self.rx_buffer += data_bytes

    def read_message(self, data_bytes):
        self.rx_buffer += data_bytes
        if self._state == Parser.ParserState.READ_PROTOCOL_VERSION:
            if len(self.rx_buffer) >= 1:
                self.payload = bytearray()
                self.payload_type = None
                self.payload_size = None
                self.protocol_version = int(self.rx_buffer.pop(0))
                self._state = Parser.ParserState.READ_INVERSE_PROTOCOL_VERSION

        if self._state == Parser.ParserState.READ_INVERSE_PROTOCOL_VERSION:
            if len(self.rx_buffer) >= 1:
                inverse_protocol_version = int(self.rx_buffer.pop(0))
                if inverse_protocol_version != (0xFF ^ self.protocol_version):
                    logger.warning(
                        "Bad DoIP Header - Inverse protocol version does not match. Ignoring."
                    )
                    # Bad protocol version inverse - shift the buffer forward
                    self.protocol_version = inverse_protocol_version
                else:
                    self._state = Parser.ParserState.READ_PAYLOAD_TYPE

        if self._state == Parser.ParserState.READ_PAYLOAD_TYPE:
            if len(self.rx_buffer) >= 2:
                self.payload_type = self.rx_buffer.pop(0) << 8
                self.payload_type |= self.rx_buffer.pop(0)
                self._state = Parser.ParserState.READ_PAYLOAD_SIZE

        if self._state == Parser.ParserState.READ_PAYLOAD_SIZE:
            if len(self.rx_buffer) >= 4:
                self.payload_size = self.rx_buffer.pop(0) << 24
                self.payload_size |= self.rx_buffer.pop(0) << 16
                self.payload_size |= self.rx_buffer.pop(0) << 8
                self.payload_size |= self.rx_buffer.pop(0)
                self._state = Parser.ParserState.READ_PAYLOAD

        if self._state == Parser.ParserState.READ_PAYLOAD:
            remaining_bytes = self.payload_size - len(self.payload)
            self.payload += self.rx_buffer[:remaining_bytes]
            self.rx_buffer = self.rx_buffer[remaining_bytes:]
            if len(self.payload) == self.payload_size:
                self._state = Parser.ParserState.READ_PROTOCOL_VERSION
                logger.debug(
                    "Received DoIP Message. Type: 0x{:X}, Payload Size: {} bytes, Payload: {}".format(
                        self.payload_type,
                        self.payload_size,
                        " ".join(f"{byte:02X}" for byte in self.payload),
                    )
                )
                try:
                    return payload_type_to_message[self.payload_type].unpack(
                        self.payload, self.payload_size
                    )
                except KeyError:
                    return ReservedMessage.unpack(
                        self.payload_type, self.payload, self.payload_size
                    )


class DoIPVechileAnnouncementMessageBroadcast:
    def __init__(
        self,
        vin_gid_sync_status=None,
    ):
        self._vin_sync_status = vin_gid_sync_status

    @staticmethod
    def _pack_doip(protocol_version, payload_type, payload_data):
        data_bytes = struct.pack(
            "!BBHL",
            protocol_version,
            0xFF ^ protocol_version,
            payload_type,
            len(payload_data),
        )
        data_bytes += payload_data

        return data_bytes

    @classmethod
    def send_vehicle_announcement(
            cls, vin, logical_address, eid, gid, further_action_required, protocol_version=0x02, interval=1.0):
        # Create a raw socket
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        def send_message():
            message = VehicleIdentificationResponse(
                vin, logical_address, eid, gid, further_action_required)

            payload_data = message.pack()
            payload_type = payload_message_to_type[type(message)]

            data_bytes = cls._pack_doip(
                protocol_version, payload_type, payload_data)

            # Create UDP header
            source_port = UDP_DISCOVERY  # Replace with your source port
            dest_port = UDP_DISCOVERY
            length = 8 + len(data_bytes)  # UDP Header size + Data size
            checksum = 0  # Checksum (optional)

            udp_header = struct.pack(
                '!HHHH', source_port, dest_port, length, checksum)

            # Combine UDP header and data
            packet = udp_header + data_bytes

            # logger.debug(
            #     "Sending DoIP Vehicle Announment Message: Type: 0x{:X}, Payload Size: {}, Payload: {}".format(
            #         payload_type,
            #         len(payload_data),
            #         " ".join(f"{byte:02X}" for byte in payload_data),
            #     )
            # )
            sock.sendto(packet, ('<broadcast>', dest_port))

            # Reschedule the function after `interval` seconds
            # threading.Timer(interval, send_message).start()

        # Start the thread
        send_message()


def send_vehicle_announcement(vin, logical_address, eid, gid, further_action_required=0, protocol_version=0x02, interval=2.0):
    DoIPVechileAnnouncementMessageBroadcast.send_vehicle_announcement(
            vin, logical_address, eid, gid, further_action_required, protocol_version, interval)

def start_periodic_task_send_vehicle_announcement(vin, logical_address, eid, gid, further_action_required=0, protocol_version=0x02, interval=2.0):
    send_vehicle_announcement(vin, logical_address, eid, gid, further_action_required, protocol_version, interval)
    reactor.callLater(interval, start_periodic_task_send_vehicle_announcement, vin, logical_address, eid, gid, further_action_required, protocol_version, interval)

class DoIPUDPServer(DatagramProtocol):
    def __init__(self, vin, logical_address, eid, gid, further_action_required=0):
        self.host_ip = self.get_host_ip()
        logger.info(f"Host IP: {self.host_ip}")
        self.vin = vin
        self.logical_address = logical_address
        self.eid = eid
        self.gid = gid
        self.further_action_required = further_action_required

    def get_host_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.255.255.255', 1))  # 使用一个不存在的地址
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    @staticmethod
    def _pack_doip(payload_type, payload_data, protocol_version=0x02):
        data_bytes = struct.pack(
            "!BBHL",
            protocol_version,
            0xFF ^ protocol_version,
            payload_type,
            len(payload_data),
        )
        data_bytes += payload_data

        return data_bytes

    def startProtocol(self):
        # 当UDP服务器启动时调用
        logger.info("UDP Server started")

    def stopProtocol(self):
        # 当UDP服务器停止时调用
        logger.info("UDP Server stopped")

    def datagramReceived(self, datagram, addr):
        # 过滤指定源端口号的会话，例如源端口号为12345
        if addr[0] == self.host_ip:
            # logger.info(f"Ignored: {datagram} from {addr}")
            return  # 不处理来自此端口的数据
        # 当UDP服务器接收到数据时调用
        logger.info(f"Received: {datagram} from {addr}")
        parser = Parser()
        parser.reset()
        result = parser.read_message(datagram)
        flag = 0
        if result:
            if type(result) == VehicleIdentificationRequest:
                logger.info(f"Received VehicleIdentificationRequest: {result}")
                flag = 1
            elif type(result) == VehicleIdentificationRequestWithEID:
                logger.info(
                    f"Received VehicleIdentificationRequestWithEID: {result}")
                flag = 1
            elif type(result) == VehicleIdentificationRequestWithVIN:
                logger.info(
                    f"Received VehicleIdentificationRequestWithVIN: {result}")
                flag = 1
            elif type(result) == DoipEntityStatusRequest:
                logger.info(f"Received DoipEntityStatusRequest: {result}")
                flag = 2
            else:
                logger.info(f"Received Unknown Message: {result}")
                flag = 0
        if flag == 1:
            message = VehicleIdentificationResponse(
                self.vin, self.logical_address, self.eid, self.gid, self.further_action_required)
        elif flag == 2:
            message = EntityStatusResponse(0, 1, 1)
        else:
            message = GenericDoIPNegativeAcknowledge(1)

        payload_data = message.pack()
        payload_type = payload_message_to_type[type(message)]
        data_bytes = self._pack_doip(payload_type, payload_data)
        logger.debug(
            "Sending DoIP Vehicle Identification Request: Type: 0x{:X}, Payload Size: {}, Payload: {}".format(
                payload_type,
                len(payload_data),
                " ".join(f"{byte:02X}" for byte in payload_data),
            )
        )
        # 这里可以根据需要处理接收到的数据或者回复客户端
        self.transport.write(data_bytes, addr)

# TCP服务器逻辑


class DoIPTCPServer(Protocol):
    def __init__(self, vin, logical_address, eid, gid, further_action_required=0):
        self.vin = vin
        self.logical_address = logical_address
        self.eid = eid
        self.gid = gid
        self.further_action_required = further_action_required

    def connectionMade(self):
        peer = self.transport.getPeer()
        logger.info(f"TCP: Connection made from {peer.host}:{peer.port}")

    @staticmethod
    def _pack_doip(payload_type, payload_data, protocol_version=0x02):
        data_bytes = struct.pack(
            "!BBHL",
            protocol_version,
            0xFF ^ protocol_version,
            payload_type,
            len(payload_data),
        )
        data_bytes += payload_data

        return data_bytes

    def _send_routing_activation_response(self, client_logical_address, logical_address, code):
        message = RoutingActivationResponse(
            client_logical_address, logical_address, code)
        payload_data = message.pack()
        payload_type = payload_message_to_type[type(message)]
        data_bytes = self._pack_doip(payload_type, payload_data)
        logger.debug(
            "Sending DoIP Routing activation response: Type: 0x{:X}, Payload Size: {}, Payload: {}".format(
                payload_type,
                len(payload_data),
                " ".join(f"{byte:02X}" for byte in payload_data),
            )
        )
        self.transport.write(data_bytes)

    def _send_diagnostic_acknowledgement(self, source_address, target_address, ack_code):
        message = DiagnosticMessagePositiveAcknowledgement(
            source_address, target_address, ack_code)
        payload_data = message.pack()
        payload_type = payload_message_to_type[type(message)]
        data_bytes = self._pack_doip(payload_type, payload_data)
        logger.debug(
            "Sending DoIP DiagnosticMessagePositiveAcknowledge: Type: 0x{:X}, Payload Size: {}, Payload: {}".format(
                payload_type,
                len(payload_data),
                " ".join(f"{byte:02X}" for byte in payload_data),
            )
        )
        self.transport.write(data_bytes)
        self.transport.doWrite()


    def _send_diagnostic_message(self, source_address, target_address, user_data):
        message = DiagnosticMessage(
            source_address, target_address, user_data)
        payload_data = message.pack()
        payload_type = payload_message_to_type[type(message)]
        data_bytes = self._pack_doip(payload_type, payload_data)
        logger.debug(
            "Sending DoIP DiagnosticMessage: Type: 0x{:X}, Payload Size: {}, Payload: {}".format(
                payload_type,
                len(payload_data),
                " ".join(f"{byte:02X}" for byte in payload_data),
            )
        )
        self.transport.write(data_bytes)


    def _uds_request_handler(self, source_address, target_address, user_data):
        logger.info(f"Received UDS Message: {user_data}")
        request = Request.from_payload(user_data)
        if request is not None and request.service is not None and request.suppress_positive_response is not True:
            code = 0
            data = b'\x01'
            if request.service == ECUReset:
                logger.info(
                    f"Received ECUReset, request.subfunction: {request.subfunction}, suppress_positive_response: {request.suppress_positive_response}")
                code = 0
                data = b'\x01'

            elif request.service == TesterPresent:
                logger.info(
                    f"Received TesterPresent, request.subfunction: {request.subfunction}, suppress_positive_response: {request.suppress_positive_response}")
                code = 0
                data = b'\x00'
            elif request.service == DiagnosticSessionControl:
                logger.info(
                    f"Received DiagnosticSessionControl, request.subfunction: {request.subfunction}, suppress_positive_response: {request.suppress_positive_response}")
                code = 0
                data = b'\x02\x00\x19\x01\xf4'
            
            if request.suppress_positive_response is not True :
                logger.info(f"Sending UDS Response: {code}, {data}")
                uds_response = Response(request.service, code, data).get_payload()
                self._send_diagnostic_message(source_address, target_address, uds_response)

    def dataReceived(self, data):
        logger.info(f"TCP: Received {data}")
        parser = Parser()
        parser.reset()
        result = parser.read_message(data)
        if result:
            # 路由激活请求
            if type(result) == RoutingActivationRequest:
                logger.info(f"Received RoutingActivationRequest: {result}")
                source_address = result.source_address
                self._send_routing_activation_response(
                    source_address, self.logical_address, RoutingActivationResponse.ResponseCode.Success)

            # 诊断消息
            if type(result) == DiagnosticMessage:
                logger.info(f"Received DiagnosticMessage: {result}")
                source_address = result.source_address
                user_data = result.user_data  # uds message

                # 诊断消息回复
                self._send_diagnostic_acknowledgement(
                    self.logical_address, source_address, 0)

                # UDS MESSAGE 处理
                self._uds_request_handler(
                    self.logical_address, source_address, user_data)

class DoIPFactory(Factory):
    def __init__(self, vin, logical_address, eid, gid, further_action_required=0):
        self.vin = vin
        self.logical_address = logical_address
        self.eid = eid
        self.gid = gid
        self.further_action_required = further_action_required

    def buildProtocol(self, addr):
        return DoIPTCPServer(self.vin, self.logical_address, self.eid, self.gid, self.further_action_required)

def start_server(vin, logical_address, eid, gid, port=13400):
    reactor.listenUDP(port, DoIPUDPServer(vin, logical_address, eid, gid))
    logger.info(f"Listening on UDP port {port}")

    factory = DoIPFactory(vin, logical_address, eid, gid)
    reactor.listenTCP(port, factory)
    logger.info(f"Listening on TCP port {port}")

    reactor.callLater(0, start_periodic_task_send_vehicle_announcement, vin, logical_address, eid, gid, 0, 2, 2)
    reactor.run()

def load_ecu_conf():
    try:
        with open('yaml.conf', 'r') as file:
            ecu_conf = yaml.safe_load(file)
            logger.info(ecu_conf)
            return ecu_conf
    except FileNotFoundError:
        logger.error("File not found.")
        return None
    except PermissionError:
        logger.error("Permission denied.")
        return None
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return None


if __name__ == "__main__":
    ecu_conf = load_ecu_conf()
    if ecu_conf is None:
        exit(1)
    vin = ecu_conf['ECU']['vin']
    logical_address = ecu_conf['ECU']['logicalAddress']
    eid = ecu_conf['ECU']['eid']
    gid = ecu_conf['ECU']['gid']

    start_server(vin, logical_address, eid, gid)
