import sys
import os
import pyvisa

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ScopeSessions.AbstractScopeSession import ScopeSession # pyright: ignore[reportMissingImports]

class LeCroyVISA(ScopeSession):
    def __init__(self, ip_address):
        self.ip_address = ip_address
        self.resource_manager = pyvisa.ResourceManager()
        self.instrument = None

    def Connect(self):
        try:
            self.instrument = self.resource_manager.open_resource(f'TCPIP0::{self.ip_address}::INSTR')
        except Exception as e:
            print(f"Failed to connect to LeCroy oscilloscope: {e}")

    def Write(self, command):
        if self.instrument:
            try:
                self.instrument.write(command) # type: ignore
            except Exception as e:
                print(f"Failed to send command: {e}")

    def Read(self):
        if self.instrument:
            try:
               response = self.instrument.read() #type: ignore
               return response.strip()
            except Exception as e:
                print(f"Read Failed: {e}")
                return None
            
    def ReadRaw(self, samples):
        if self.instrument:
            try:
               response = self.instrument.read_raw() #type: ignore
               return response
            except Exception as e:
                print(f"Read Failed: {e}")
                return None

    def Disconnect(self):
        if self.instrument:
            try:
                self.instrument.close()
            except Exception as e:
                print(f"Failed to close connection: {e}")
  