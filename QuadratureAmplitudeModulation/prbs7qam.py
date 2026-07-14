import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
symbol_rate = 2e9          # 2 Gbaud
sps = 8                    # samples per symbol
num_symbols = 100000

sample_rate = symbol_rate * sps

# ---------------------------------------------------------------------
# PRBS15 Generator (x^15 + x^14 + 1)
# Period: 2^15 - 1 = 32767 bits
# Recommended for filling 256QAM constellation uniformly
# ---------------------------------------------------------------------
def prbs15(n_bits, seed=0x7FFF):
    state = seed & 0x7FFF
    bits = np.empty(n_bits, dtype=np.uint8)

    for i in range(n_bits):
        bits[i] = state & 1

        # taps at bits 15 and 14
        new_bit = ((state >> 14) ^ (state >> 13)) & 1

        state = ((state << 1) & 0x7FFE) | new_bit

    return bits

# ---------------------------------------------------------------------
# Gray-coded 16-PAM mapper
# Levels: ±1, ±3, ±5, ..., ±15
# Normalized to unit average power.
# ---------------------------------------------------------------------
pam16_gray = np.array([
    -15, -13, -9, -11,
     -1,  -3, -7,  -5,
     15,  13,  9,  11,
      1,   3,  7,   5
], dtype=float)

# Normalize 256QAM average power to 1
pam16_gray /= np.sqrt(170)

# ---------------------------------------------------------------------
# Generate bits
# ---------------------------------------------------------------------
bits_per_symbol = 8
num_bits = num_symbols * bits_per_symbol

bits = prbs15(num_bits)

# Group into symbols
bit_groups = bits.reshape((-1, 8))

# First 4 bits -> I
# Last 4 bits  -> Q
I_idx = (
    (bit_groups[:,0] << 3) |
    (bit_groups[:,1] << 2) |
    (bit_groups[:,2] << 1) |
     bit_groups[:,3]
)

Q_idx = (
    (bit_groups[:,4] << 3) |
    (bit_groups[:,5] << 2) |
    (bit_groups[:,6] << 1) |
     bit_groups[:,7]
)

I_symbols = pam16_gray[I_idx]
Q_symbols = pam16_gray[Q_idx]

# Complex 256QAM symbols
qam_symbols = I_symbols + 1j * Q_symbols

# ---------------------------------------------------------------------
# Create oversampled waveform (rectangular pulse shaping)
# ---------------------------------------------------------------------
iq_waveform = np.repeat(qam_symbols, sps)

# Separate I and Q waveforms
I_waveform = np.real(iq_waveform)
Q_waveform = np.imag(iq_waveform)

# Time vector
t = np.arange(len(iq_waveform)) / sample_rate

# ---------------------------------------------------------------------
# Example plots
# ---------------------------------------------------------------------
plt.figure(figsize=(10,4))
plt.plot(I_waveform[:200], label='I')
plt.plot(Q_waveform[:200], label='Q')
plt.title('2 Gbaud 256QAM PRBS15 Waveform')
plt.xlabel('Sample')
plt.ylabel('Amplitude')
plt.legend()
plt.grid(True)

plt.figure(figsize=(6,6))
plt.plot(I_symbols[:5000], Q_symbols[:5000], '.', ms=2)
plt.title('256QAM Constellation')
plt.xlabel('I')
plt.ylabel('Q')
plt.grid(True)
plt.axis('equal')

plt.show()

print(f"Symbol Rate : {symbol_rate/1e9:.1f} Gbaud")
print(f"Sample Rate : {sample_rate/1e9:.1f} GS/s")
print(f"Samples     : {len(iq_waveform)}")