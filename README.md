### 1. doipserver supports header payload types

| DoIP packet grouping | Load Type | Load Type | Support | Transport Protocol |
|-------|-------|-------|-------|-------|
| Denial message | 0x0000 | Generic DoIP Header Negative Response | support | UDP |
| Node Management Message | 0x0001 | Vehicle identification request message | support | UDP |
| Node Management Message | 0x0002 | Vehicle identification request message with EID | support | UDP |
| Node Management Message | 0x0003 | Vehicle identification request message with VIN | support | UDP |
| Node Management Message | 0x0004 | Vehicle declaration message/Vehicle identification response message | support | UDP |
| Node Management Message | 0x0005 | Routing activation request message | support | TCP |
| Node Management Message | 0x0006 | Routing activation response message | support | TCP |
| Diagnostic message | 0x8001 | Diagnostic message | support | TCP |
| Diagnostic message | 0x8002 | Diagnostic message positive response | support | TCP |
| Vehicle information message | 0x4001 | Doip entity status request message | support | UDP |
| Vehicle information message | 0x4002 | Doip entity status response message | support | UDP |


### 2. UDS supported protocol types
| Major categories | SID(0x) | Diagnostic service name | Service | Support |
|-------|-------|-------|-------|-------|
| Diagnostics and communication management functional unit | 10 | Diagnostic Session Control | Diagnostic Session Control | support |
| Diagnostics and communication management functional unit | 11 | ECU reset | ECU Reset | support |
| Diagnostics and communication management functional unit | 27 | Secure Access | Security Access | support |
| Diagnostics and communication management functional unit | 28 | Communication control | Communication Control | Not supported |
| Diagnostics and communication management functional unit | 3E | Standby handshake | Tester Present | support |
| Data transmission | twenty two | Read data by ID | Read Data By Identifier | support |
| Routine function class | 31 | Routine control | Routine Control | support |
| Upload and download functional unit | 34 | Request Download | Request Download | support |
| Upload and download functional unit | 36 | Data Transfer | Transfer Data | support |
| Upload and download functional unit | 37 | Request to exit transfer | Transfer Data Exit | support |


### 3. doipserver supported service types

- UDP Broadcast Service
- UDP unicast service
- TCP unicast service

### 4. Support ECU Gateway information configuration

### 5. Instructions for use

```shell
cd doipserver
sudo python3 server.py
```

