import sys
import os
import socket
import struct
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ScopeSessions.AbstractScopeSession import ScopeSession  # pyright: ignore[reportMissingImports]

VICP_PORT = 1861
VICP_HEADER_LEN = 8
BINARY_CHUNK_SIZE = 16382

class LeCroyVICPError(Exception):
    pass


class LeCroyVICP(ScopeSession):

    def __init__(self, host, port=VICP_PORT, timeout=5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self._rx_buffer = b""
        self._msg_id = 1
        self.recv_thread = threading.Thread(target=self._recv_last_vicp_header)

    # ------------------------
    # Connection control
    # ------------------------

    def Connect(self):
        if self.sock:
            return
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))

    def Disconnect(self):
        if self.sock:
            try:
                self.sock.close()
            finally:
                self.sock = None

    # ------------------------
    # Low-level VICP I/O
    # ------------------------

    def _send_packet(self, payload: bytes):
        header = struct.pack(">BBBBI", 0x81, 0x01, 0x00, self._msg_id, len(payload))
        self._msg_id += 1
        self.sock.sendall(header + payload)

    def _recv_text(self):
        if(self.recv_thread.is_alive()):
            self.recv_thread.join(1.0)
        payloads = []
        while True:
            vicpHeader = self.sock.recv(VICP_HEADER_LEN)
            flags, version, msg_id, reserved, payloadLength = struct.unpack(
                    ">BBBBI", vicpHeader)
            # receive first payload and discard a /n if present
            payload = self.sock.recv(payloadLength)
            
            payloads.append(payload)
            # Heuristic: stop if no more data immediately available
            self.sock.settimeout(0.01)
            try:
                self.sock.recv(1, socket.MSG_PEEK)
            except Exception:
                break
            finally:
                self.sock.settimeout(self.timeout)

        return payloads
    
    def _recv_last_vicp_header(self):
        vicpHeader = self.sock.recv(VICP_HEADER_LEN)
        flags, version, msg_id, reserved, payloadLength = struct.unpack(
                    ">BBBBI", vicpHeader)
        payload = self.sock.recv(payloadLength)
        return

    def _recv_binary(self, binaryDataLength):
        if(self.recv_thread.is_alive()):
            self.recv_thread.join(1.0)

        chunks = 0

        self._rx_buffer = b""
        # [VICP hdr]
        # DAT1,
        # [VICP hdr]
        # #9<length>
        # [VICP hdr]
        # <binary waveform data chunk 1>  chunks are 16382 bytes long
        # [VICP hdr]
        # <binary waveform data chunk 2>
        # ...

        payloadChunks = []


        # receive VICP header
        vicpHeader = self.sock.recv(VICP_HEADER_LEN)
        flags, version, msg_id, reserved, payloadLength = struct.unpack(
                    ">BBBBI", vicpHeader)
        # receive first payload ... 'DAT1,'
        payload = self.sock.recv(payloadLength)
        #self._rx_buffer += payload
        payloadChunks.append(payload)
        # receive VICP header
        vicpHeader = self.sock.recv(VICP_HEADER_LEN)
        flags, version, msg_id, reserved, payloadLength = struct.unpack(
                    ">BBBBI", vicpHeader)

        # receive SCPI header payload ... '#9<length>'
        payload = self.sock.recv(payloadLength)
        #self._rx_buffer += payload
        payloadChunks.append(payload)
        
        binaryStart = time.perf_counter()

       
        dat1PlusScpiHeaderLength   = len(self._rx_buffer)
        #while len(self._rx_buffer) < dat1PlusScpiHeaderLength + binaryDataLength:
        while (chunks) * BINARY_CHUNK_SIZE < binaryDataLength:
            # receive VICP header
            vicpHeader = self.sock.recv(VICP_HEADER_LEN)
            flags, version, msg_id, reserved, payloadLength = struct.unpack(
                        ">BBBBI", vicpHeader)

            #receive binary chunck
            payload = b""
            #note:  receive the payload chuck until payloadLength have been received
            while(len(payload) != payloadLength):
                payload += self.sock.recv(payloadLength - len(payload))
            
           
            payloadChunks.append(payload)
            chunks += 1
            
        #receive last VICP header and /n and discard both
        self.recv_thread = threading.Thread(target=self._recv_last_vicp_header)
        self.recv_thread.start()
        return b"".join(payloadChunks)

    # ------------------------
    # VISA-like API
    # ------------------------

    def Write(self, command: str):
        """
        Send a SCPI command (no response expected).
        """
        if not self.sock:
            raise LeCroyVICPError("Not connected")
        payload = (command.rstrip() + "\n").encode("ascii")
        self._send_packet(payload)

    def Read(self) -> bytes:     
        if not self.sock:
            raise LeCroyVICPError("Not connected")
        payloads = self._recv_text()
        return b"".join(payloads).decode('ascii').strip()

    def ReadRaw(self, samples) -> bytes:
        if not self.sock:
            raise LeCroyVICPError("Not connected")
        data = self._recv_binary(samples)
        return data





