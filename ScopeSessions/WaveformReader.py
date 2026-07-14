import sys
import os
import re   # regular expressions or Regex
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ScopeSessions.AbstractScopeSession import ScopeSession  # pyright: ignore[reportMissingImports]

class WaveformReader:
    def __init__(self, scope: ScopeSession):
        self.Scope = scope

    def __ParseNumber(self, s):     # "vbs 1.234", "vbs 5002", or "vbs 1234.5e-02" or "1234" (w/out the vbs)
        match = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', s)
        if match:
            return float(match.group(0))
        raise ValueError("No number found in string")

    def __GetNumberOfSamples(self, traceType, trace):
        self.Scope.Write(f"vbs? 'return = app.{traceType}.{trace}.Out.Result.Samples'")
        return int(self.__ParseNumber(self.Scope.Read()))

    def __GetVerticalOffset(self, traceType, trace):
        self.Scope.Write(f"vbs? 'return = app.{traceType}.{trace}.Out.Result.VerticalOffset'")
        return self.__ParseNumber(self.Scope.Read())

    def __GetVerticalGain(self, traceType, trace):
        self.Scope.Write(f"vbs? 'return = app.{traceType}.{trace}.Out.Result.VerticalPerStep'")
        return self.__ParseNumber(self.Scope.Read())

    def __ConfigureTransfer(self, samples, binFormat):
        # Set to transfer all points
        self.Scope.Write(f"WFSU SP,0,NP,{samples},FP,0,SN,0")
        self.Scope.Write(f"COMM_ORDER HI") #big endian
        self.Scope.Write(f"CHDR OFF")  # data only.  no command prefix
        self.Scope.Write(f"COMM_FORMAT DEF9,{binFormat},BIN")

    def __GetRawData(self, trace, samples):
        self.Scope.Write(f"{trace}:WF? DAT1") 
        return self.Scope.ReadRaw(samples)

    def __NormalizeBinFormat(self, binFormat):
        normalized = str(binFormat).strip().upper()
        if normalized not in ("WORD", "BYTE"):
            raise ValueError(f"Unsupported bin format: {binFormat}")
        return normalized
    
    def __RemoveHeaderFromTheRawData(self, rawData):
        # Parse IEEE 488.2-style binary block: DAT1,#<n><len><payload>
        headerRegex = rb'^(?:[A-Z0-9]+:WF ?)?(?:DAT[12]|TIME),#(\d)'
        headerMatch = re.match(headerRegex, rawData)
        if not headerMatch:
            raise ValueError("Header not found or invalid format")

        lengthDigits = int(headerMatch.group(1))
        lengthStart = headerMatch.end()
        lengthEnd = lengthStart + lengthDigits
        if len(rawData) < lengthEnd:
            raise ValueError("Incomplete waveform header length field")

        payloadLength = int(rawData[lengthStart:lengthEnd])
        payloadStart = lengthEnd
        payloadEnd = payloadStart + payloadLength
        if len(rawData) < payloadEnd:
            raise ValueError("Incomplete waveform payload")

        return rawData[payloadStart:payloadEnd]
    
    def __ConvertRawDataToInts(self, rawData, binFormat):
        if np is not None:
            if binFormat == "WORD":
                return np.frombuffer(rawData, dtype='>i2')  # convert big endian 2-BYTE words to 16-bit integers
            return np.frombuffer(rawData, dtype=np.int8).astype(np.int16) * 256.0  # expand signed BYTE samples to 16-bit scale

    def __ScaleData(self, intData, verticalGain, verticalOffset):
        if np is not None:
            return intData * verticalGain + verticalOffset
        return [sample * verticalGain + verticalOffset for sample in intData]


    # traceType is 'Acquisition, Math, Zoom, or Memory'; 
    # trace is 'C1-Cn, F1-Fn, Z1-Zn, M1-Mn'
    # binFormat is 'WORD' or 'BYTE'
    def GetScaledWaveformData(self, traceType, trace, binFormat):
       binFormat = self.__NormalizeBinFormat(binFormat)
       samples = self.__GetNumberOfSamples(traceType, trace)
       verticalOffset = self.__GetVerticalOffset(traceType, trace)
       verticalGain = self.__GetVerticalGain(traceType, trace)
       self.__ConfigureTransfer(samples, binFormat)
       bytesPerSample = 2 if binFormat == "WORD" else 1
       rawData = self.__GetRawData(trace, samples * bytesPerSample)
       binaryData = self.__RemoveHeaderFromTheRawData(rawData) 
       expectedPayloadLength = samples * bytesPerSample
       if len(binaryData) != expectedPayloadLength:
           raise ValueError(
               f"Payload length mismatch for {trace}: expected {expectedPayloadLength} bytes, got {len(binaryData)}"
           )
       intData = self.__ConvertRawDataToInts(binaryData, binFormat)
       return self.__ScaleData(intData, verticalGain, verticalOffset)
