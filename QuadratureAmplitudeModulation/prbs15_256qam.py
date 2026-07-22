import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

sample_rate = 1.54e9    # 1.54 GS/s  because this is max IQ rate for the T3AWG6k
bits_per_symbol = 8        # 256QAM has 8 bits per symbol
sps = 4                    # baud rate = sample_rate / sps = 1.54e9 / 4 = 385 MBaud
symbol_rate = sample_rate / sps  # 385 MBaud

# enough for a little over 2 prbs15 periods (32767 bits/8 bits or about 4095 symbols) to fill the 256QAM constellation uniformly
num_symbols = 10000  

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
# Natural-binary 16-PAM mapper (non-Gray)
# Levels: ±1, ±3, ±5, ..., ±15
# Normalized to unit average power.
# ---------------------------------------------------------------------
pam16 = np.array([
    -15, -13, -11, -9,
     -7,  -5,  -3, -1,
      1,   3,   5,  7,
      9,  11,  13, 15
], dtype=float)

# Normalize 256QAM average power to 1
pam16 /= np.sqrt(170)

# ---------------------------------------------------------------------
# Generate bits
# ---------------------------------------------------------------------
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

I_symbols = pam16[I_idx]
Q_symbols = pam16[Q_idx]

# Complex 256QAM symbols
qam_symbols = I_symbols + 1j * Q_symbols

# ---------------------------------------------------------------------
# Root Raised Cosine (RRC) pulse shaping filter
# Provides continuous amplitude and phase when repeating
# ---------------------------------------------------------------------
def rrc_filter(sps, span_symbols=4, rolloff=0.22):
    """
    Design a root-raised-cosine filter.
    
    Parameters:
    - sps: samples per symbol
    - span_symbols: filter span in symbol periods (4-6 typical)
    - rolloff: roll-off factor (0 to 1)
    
    Returns: filter coefficients
    """
    span_samples = span_symbols * sps
    t = np.arange(-span_samples // 2, span_samples // 2) / sps
    
    # RRC formula
    numerator = np.sin(np.pi * t * (1 - rolloff)) + 4 * rolloff * t * np.cos(np.pi * t * (1 + rolloff))
    denominator = np.pi * t * (1 - (4 * rolloff * t) ** 2)
    
    # Handle the singularity at t=0
    h = np.where(np.abs(denominator) > 1e-10, numerator / denominator, 1 - 4 * rolloff)
    
    # Normalize
    h = h / np.sqrt(np.sum(h**2))
    return h

# Create RRC filter
rrc_h = rrc_filter(sps, span_symbols=5, rolloff=0.22)

# Apply RRC filter to the repeated symbols
iq_waveform = np.repeat(qam_symbols, sps)
#iq_waveform = np.convolve(iq_waveform_temp, rrc_h, mode='same')

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
plt.title(f'{symbol_rate/1e6:.2f} Mbaud 256QAM PRBS15 Waveform')
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

print(f"Symbol Rate : {symbol_rate/1e6:.2f} Mbaud")
print(f"Sample Rate : {sample_rate/1e9:.2f} GS/s")
print(f"Samples     : {len(iq_waveform)}")

# Save I and Q waveforms to separate txt files
np.savetxt(f'I_waveform 256QAM {symbol_rate/1e6:.2f} Mbaud no RRC no gray.txt', I_waveform, fmt='%.6e')
np.savetxt(f'Q_waveform 256QAM {symbol_rate/1e6:.2f} Mbaud no RRC no gray.txt', Q_waveform, fmt='%.6e')