import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

qam_order = 256            # 256 or 512
bits_per_symbol = int(np.log2(qam_order))
symbol_rate = 100e6        # 100 Mbaud
sps = 15                   # samples per symbol
sample_rate = symbol_rate * sps  # 1.5 GS/s, within the T3AWG6k max IQ rate

# enough for a little over 2 prbs15 periods to fill the constellation uniformly
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
def build_constellation(order):
    """Return complex points indexed by the natural-binary symbol value, normalized to unit average power."""
    if order == 256:
        levels = np.arange(-15, 16, 2, dtype=float)
        pts = np.array([i + 1j * q for i in levels for q in levels])
    elif order == 512:
        # 24x24 grid with the four 4x4 corners removed (cross constellation)
        levels = np.arange(-23, 24, 2, dtype=float)
        pts = np.array([i + 1j * q for i in levels for q in levels
                        if not (abs(i) > 15 and abs(q) > 15)])
    else:
        raise ValueError("qam_order must be 256 or 512")
    return pts / np.sqrt(np.mean(np.abs(pts) ** 2))

constellation = build_constellation(qam_order)

# ---------------------------------------------------------------------
# Generate bits
# ---------------------------------------------------------------------
num_bits = num_symbols * bits_per_symbol

bits = prbs15(num_bits)

# Group into symbols
bit_groups = bits.reshape((-1, bits_per_symbol)).astype(np.int64)

# MSB-first bits -> symbol index
sym_idx = np.zeros(len(bit_groups), dtype=np.int64)
for b in range(bits_per_symbol):
    sym_idx = (sym_idx << 1) | bit_groups[:, b]

qam_symbols = constellation[sym_idx]
I_symbols = qam_symbols.real
Q_symbols = qam_symbols.imag

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
plt.title(f'{symbol_rate/1e6:.2f} Mbaud {qam_order}QAM PRBS15 Waveform')
plt.xlabel('Sample')
plt.ylabel('Amplitude')
plt.legend()
plt.grid(True)

plt.figure(figsize=(6,6))
plt.plot(I_symbols[:5000], Q_symbols[:5000], '.', ms=2)
plt.title(f'{qam_order}QAM Constellation')
plt.xlabel('I')
plt.ylabel('Q')
plt.grid(True)
plt.axis('equal')

plt.show()

print(f"Symbol Rate : {symbol_rate/1e6:.2f} Mbaud")
print(f"Sample Rate : {sample_rate/1e9:.2f} GS/s")
print(f"Samples     : {len(iq_waveform)}")

# Save I and Q waveforms to separate txt files
np.savetxt(f'I_waveform {qam_order}QAM {symbol_rate/1e6:.2f} Mbaud no RRC no gray.txt', I_waveform, fmt='%.6e')
np.savetxt(f'Q_waveform {qam_order}QAM {symbol_rate/1e6:.2f} Mbaud no RRC no gray.txt', Q_waveform, fmt='%.6e')