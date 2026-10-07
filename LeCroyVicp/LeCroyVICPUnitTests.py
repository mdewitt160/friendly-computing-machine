import sys
import os
import time
import unittest
import numpy as np
from LeCroyVICP import LeCroyVICP

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ScopeSessions.WaveformReader import WaveformReader  # pyright: ignore[reportMissingImports]

class Test_LeCroyVICPUnitTests(unittest.TestCase):
    def setUp(self):
        self.Scope = LeCroyVICP("192.168.23.1")
        self.Scope.Connect()

    def tearDown(self):
        self.Scope.Disconnect()
    
    def test_BasicArrayOperation(self):
        data_array = np.array([1, 2, 3, 4, 5])
        threshold = 3
        data_logic = data_array > threshold
        strobe_array = np.array([0, 1, 2, 3, 4])
        strobe_logic = strobe_array > threshold                                 
        clock = np.asarray(np.bitwise_xor(data_logic, strobe_logic), dtype=np.float64)
        np.testing.assert_array_equal(clock, [0.0, 1.0, 1.0, 0.0, 0.0])
    



    def test_BasicIdn(self):
        self.Scope.Write("COMM_HEADER OFF")  # Optional: Disable communication header for cleaner responses
        self.Scope.Write("*IDN?")
        idn = self.Scope.Read()
        self.assertEqual(idn, "LECROY,SDA8330HD,CHE-LMDEWITT,11.4.0")  # Replace with expected IDN response

    def test_GetC1Trace(self):
        self.Scope.Write("vbs? 'return = app.Acquisition.C1.Out.Result.Samples'")
        samples = self.Scope.Read()
        reader = WaveformReader(self.Scope)
        startTime = time.time()
        waveform = reader.GetScaledWaveformData("Acquisition","C1", "WORD")
        print(f"\nTime taken to read waveform: {time.time() - startTime:.2f} seconds")
        self.assertEqual(int(samples), len(waveform))
        self.Scope.Write("vbs? 'return = app.Cursors.StdCursOfC1.Y1.Result.Value'")
        cursorValue = self.Scope.Read()
        point = int((50e-6 + 85e-9)/100e-6 * (int(samples)))  # Calculate the index corresponding to 50us + 85ns
        # Compare the cursor value to the middle sample of the waveform, allowing for a small tolerance
        self.assertAlmostEqual(float(cursorValue), waveform[point], delta=0.0005)

if __name__ == '__main__':
    unittest.main()