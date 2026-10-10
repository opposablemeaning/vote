"""Track audition synthesis engines for VOTE. THEM. OUT.

Four distinct creative directions at 135 BPM, D minor:
1. Industrial (Justice / Gesaffelstein / Trent Reznor)
2. Cyberpunk Darksynth (Carpenter Brut / Kavinsky / The Prodigy)
3. Cinematic Hybrid Trailer (Hans Zimmer / Junkie XL / Woodkid)
4. Heavy Electro-Rock (The Prodigy / Death From Above 1979)

All engines produce phone-speaker-optimized audio (rich 150-1000 Hz harmonic content)
using 100% CC0 samples and programmatic DSP.
"""

from functools import lru_cache
from pathlib import Path
import numpy as np
import scipy.signal as sps
import soundfile as sf

SR = 48_000
BPM = 135
BEAT = 60.0 / BPM
BAR = BEAT * 4
E = BEAT / 2
S = BEAT / 4

ROOT = Path(__file__).resolve().parent.parent
CC0_DIR = ROOT / "assets" / "audio" / "cc0"
DRUMS_CC0 = CC0_DIR / "drums"
TR808_CC0 = CC0_DIR / "tr808"
TIDAL_CELLO = Path.home() / "tidal" / "samples" / "clean" / "samples-cello-bowed"
TIDAL_BASS = Path.home() / "tidal" / "samples" / "clean" / "samples-flbass"

# Note frequencies (Hz) in D minor
NOTES = {
    "D1": 36.71, "F1": 43.65, "G1": 49.00, "A1": 55.00, "Bb1": 58.27, "C2": 65.41,
    "D2": 73.42, "F2": 87.31, "G2": 98.00, "A2": 110.00, "Bb2": 116.54, "C3": 130.81,
    "D3": 146.83, "F3": 174.61, "G3": 196.00, "A3": 220.00, "Bb3": 233.08, "C4": 261.63,
    "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00, "A4": 440.00, "Bb4": 466.16, "C5": 523.25,
    "D5": 587.33,
}


# ==============================================================================
# CORE DSP PRIMITIVES
# ==============================================================================

def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def env_exp(dur, decay, attack=0.002):
    t = t_axis(dur)
    a = np.clip(t / attack, 0, 1) if attack > 0 else 1.0
    return a * np.exp(-t / decay)


def env_ahdsr(dur, a=0.005, h=0.0, d=0.1, s=0.5, r=0.05):
    t = t_axis(dur)
    env = np.zeros_like(t)
    ia, ih, id_ = int(a * SR), int(h * SR), int(d * SR)
    if ia > 0:
        env[:ia] = np.linspace(0, 1, ia)
    env[ia:ia + ih] = 1.0
    decay_len = min(id_, len(env) - (ia + ih))
    if decay_len > 0:
        env[ia + ih:ia + ih + decay_len] = np.linspace(1, s, decay_len)
    env[ia + ih + decay_len:] = s
    ir = int(r * SR)
    if ir > 0 and len(env) > ir:
        env[-ir:] *= np.linspace(1, 0, ir)
    return env


def soft_saturate(x, drive_amt=2.0):
    """Asymmetric saturation: produces even and odd harmonics for warmth on phone speakers."""
    y = x * drive_amt
    y_asym = y + 0.15 * (y ** 2)
    return np.tanh(y_asym) / np.tanh(drive_amt)


def bandpass(x, lo, hi, order=3):
    sos = sps.butter(order, [max(10, lo), min(SR / 2 - 100, hi)], btype="band", fs=SR, output="sos")
    return sps.sosfilt(sos, x)


def lowpass(x, fc, order=3):
    sos = sps.butter(order, min(SR / 2 - 100, max(20, fc)), btype="low", fs=SR, output="sos")
    return sps.sosfilt(sos, x)


def highpass(x, fc, order=3):
    sos = sps.butter(order, max(10, min(SR / 2 - 100, fc)), btype="high", fs=SR, output="sos")
    return sps.sosfilt(sos, x)


def place(x, at, total):
    """Place mono or stereo x starting at `at` seconds inside a buffer of `total` seconds."""
    is_stereo = x.ndim > 1
    out = np.zeros((int(total * SR), 2)) if is_stereo else np.zeros(int(total * SR))
    i = int(at * SR)
    if i >= len(out):
        return out
    seg = x[: max(0, len(out) - i)]
    out[i:i + len(seg)] += seg
    return out


def stereo_spread(x_mono, width=0.4, delay_ms=12.0):
    """Mono-safe width: a delayed, high-passed copy is added to the left channel and subtracted
    from the right, so L+R is exactly the dry sound. Phones and Bluetooth speakers that sum to mono
    get no comb filtering, the image stays centered, and everything under ~250 Hz stays in the middle.
    (A plain left/right delay cost the kick and bass ~6 dB at 60-150 Hz in mono and pulled the
    image toward the left.)"""
    x = np.asarray(x_mono, dtype=np.float64)
    if width <= 0:
        return np.stack([x, x], axis=1)
    d = int(delay_ms * 0.001 * SR)
    mid = np.pad(x, (0, d))
    side = highpass(np.pad(x, (d, 0)), 250.0) * width
    return np.stack([mid + side, mid - side], axis=1)


def reverb(x, size=1.0, wet=0.25, seed=11):
    """Fast convolution room reverb."""
    is_stereo = x.ndim > 1
    t = t_axis(size)
    rng = np.random.default_rng(seed)
    ir = rng.uniform(-1, 1, int(size * SR)) * np.exp(-t / (size / 4.0))
    ir = lowpass(ir, 5500)
    ir /= np.sqrt(np.sum(ir ** 2) + 1e-12)
    if is_stereo:
        ir_r = rng.uniform(-1, 1, int(size * SR)) * np.exp(-t / (size / 4.0))
        ir_r = lowpass(ir_r, 5500)
        ir_r /= np.sqrt(np.sum(ir_r ** 2) + 1e-12)
        wl = sps.fftconvolve(x[:, 0], ir)[: len(x)]
        wr = sps.fftconvolve(x[:, 1], ir_r)[: len(x)]
        w = np.stack([wl, wr], axis=1)
    else:
        w = sps.fftconvolve(x, ir)[: len(x)]
    return x * (1.0 - wet) + w * wet


def saw_osc(freq, dur, detune_cents=0.0):
    """Band-limited summation saw oscillator."""
    t = t_axis(dur)
    f = freq * (2.0 ** (detune_cents / 1200.0))
    harmonics = int(min(28, (SR / 2) // max(1.0, f)))
    sig = np.zeros_like(t)
    for h in range(1, harmonics + 1):
        sig += (1.0 / h) * np.sin(2 * np.pi * f * h * t)
    return sig * (2.0 / np.pi)


def square_osc(freq, dur, detune_cents=0.0):
    t = t_axis(dur)
    f = freq * (2.0 ** (detune_cents / 1200.0))
    harmonics = int(min(28, (SR / 2) // max(1.0, f)))
    sig = np.zeros_like(t)
    for h in range(1, harmonics + 1, 2):
        sig += (1.0 / h) * np.sin(2 * np.pi * f * h * t)
    return sig * (4.0 / np.pi)


@lru_cache(maxsize=128)
def load_sample(path_str, pitch_semitones=0):
    path = Path(path_str)
    if not path.exists():
        return np.zeros(100)
    x, sr = sf.read(path)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != SR:
        x = sps.resample_poly(x, SR, sr)
    # Trim leading silence
    idx = np.argmax(np.abs(x) > 0.05 * np.max(np.abs(x)))
    x = x[max(0, idx - 16):]
    if pitch_semitones != 0:
        factor = 2.0 ** (-pitch_semitones / 12.0)
        x = sps.resample(x, max(16, int(len(x) * factor)))
    m = np.max(np.abs(x))
    return x / m if m > 0 else x


# ==============================================================================
# ENGINE 1: RELENTLESS INDUSTRIAL (Justice / Gesaffelstein / Reznor)
# ==============================================================================

def kick_ind(hard=1.0, seed=0):
    dur = 0.45
    t = t_axis(dur)
    f_sub = 48 + 140 * np.exp(-t / 0.032)
    sub = np.sin(2 * np.pi * np.cumsum(f_sub) / SR) * env_exp(dur, 0.24, 0.001)
    # 135 Hz chest knock
    f_knock = 135 * np.exp(-t / 0.02)
    knock = np.sin(2 * np.pi * np.cumsum(f_knock) / SR) * env_exp(dur, 0.05, 0.001)
    knock = soft_saturate(knock * 1.8, 2.5) * 0.75
    # Click
    rng = np.random.default_rng(seed)
    click = bandpass(rng.uniform(-1, 1, int(0.015 * SR)), 2500, 7500) * env_exp(0.015, 0.003, 0.0002)
    click = np.pad(click, (0, len(sub) - len(click))) * 0.5 * hard
    return soft_saturate(sub * 1.1 + knock + click, 2.0 + 0.4 * hard)


def snare_ind(seed=0):
    dur = 0.45
    t = t_axis(dur)
    rng = np.random.default_rng(seed)
    f_body = 195 + 40 * np.exp(-t / 0.015)
    body = (np.sin(2 * np.pi * np.cumsum(f_body) / SR) * 0.8 +
            np.sin(2 * np.pi * 340 * t) * 0.3) * env_exp(dur, 0.05, 0.001)
    noise_raw = rng.uniform(-1, 1, int(dur * SR))
    wires = bandpass(noise_raw, 1800, 8500) * env_exp(dur, 0.12, 0.001)
    snap = highpass(noise_raw[:int(0.01 * SR)], 3500) * env_exp(0.01, 0.002, 0.0001) * 0.6
    snap = np.pad(snap, (0, len(body) - len(snap)))
    dry = soft_saturate(body * 1.4 + wires * 0.85 + snap, 2.0)
    tail = bandpass(noise_raw, 800, 4000) * env_exp(dur, 0.18, 0.02) * 0.35
    gate = np.clip(1.5 - t / 0.22, 0, 1)
    return stereo_spread(dry + tail * gate, width=0.35)


OSC_FREQS = [205.3, 304.4, 369.6, 522.7, 540.0, 800.0]


def hat_ind(open_=False, velocity=0.8, seed=0):
    dur = 0.25 if open_ else 0.055
    t = t_axis(dur)
    cluster = sum(sps.square(2 * np.pi * f * t + (seed + i) * 0.2) for i, f in enumerate(OSC_FREQS)) / len(OSC_FREQS)
    shaped = highpass(bandpass(cluster, 6500, 13000), 7000)
    env = env_exp(dur, 0.08 if open_ else 0.016, 0.0003)
    return shaped * env * velocity * 1.1


def reese_ind(freq, dur, cutoff=650, drive_amt=3.2):
    t = t_axis(dur)
    s1 = saw_osc(freq, dur, -9)
    s2 = saw_osc(freq, dur, 9)
    sub = np.sin(2 * np.pi * (freq / 2.0) * t) * 0.8
    raw = (s1 + s2) * 0.5 + sub
    filtered = lowpass(raw, cutoff, order=3)
    return soft_saturate(filtered, drive_amt) * env_exp(dur, dur * 0.9, 0.005)


def braam_ind(freq, dur=1.6):
    t = t_axis(dur)
    pitch_mod = 1.0 + 0.12 * np.exp(-t / 0.04)
    saws = (saw_osc(freq * pitch_mod[0], dur, -12) +
            saw_osc(freq * pitch_mod[0], dur, 0) +
            saw_osc(freq * pitch_mod[0], dur, 12)) / 3.0
    filtered = lowpass(saws, 1200, order=2)
    driven = soft_saturate(filtered * 1.6, 3.8)
    return stereo_spread(driven * env_exp(dur, 0.9, 0.008), width=0.5)


def arp_ind(freq, dur=0.18):
    t = t_axis(dur)
    sig = (saw_osc(freq, dur) * 0.6 + square_osc(freq, dur) * 0.4)
    filtered = bandpass(sig, 500, 2400, order=2)
    return soft_saturate(filtered * env_exp(dur, 0.045, 0.001), 2.2) * 0.45


def anthem_lead_ind(freq, dur=0.45):
    t = t_axis(dur)
    vib = 1.0 + 0.012 * np.sin(2 * np.pi * 5.5 * t)
    sig = (saw_osc(freq * vib[0], dur, -8) + saw_osc(freq * vib[0], dur, 8)) * 0.5
    filtered = lowpass(sig, 3400, order=2)
    env = env_ahdsr(dur, a=0.015, h=0.05, d=0.1, s=0.8, r=0.1)
    return stereo_spread(soft_saturate(filtered * env, 1.8), width=0.45)


def render_industrial_bar(section, idx, seed=0):
    """Render a single 4/4 bar for Engine 1."""
    dur = BAR + 0.8
    out = np.zeros((int(dur * SR), 2))
    
    # 8th note driving bass riff
    riff_notes = [NOTES["D2"], NOTES["D2"], NOTES["D2"], NOTES["F2"],
                  NOTES["G2"], NOTES["D2"], NOTES["Bb2"], NOTES["A2"]]

    # Tension/Groove (bars 1-4)
    if section in ("tension", "groove"):
        # Kick on 1 and 3 (groove only)
        if section == "groove":
            for b in (0, 2):
                out += place(stereo_spread(kick_ind(hard=1.0, seed=seed + b)), b * BEAT, dur)
            # Snare on 2 and 4
            for b in (1, 3):
                out += place(snare_ind(seed=seed + b) * 0.85, b * BEAT, dur)
            # 8th hats
            for i in range(8):
                out += place(stereo_spread(hat_ind(velocity=0.6 if i % 2 else 0.8, seed=seed + i)), i * E, dur)
        # Saturated Reese bass
        for i, n in enumerate(riff_notes):
            if section == "tension" and i not in (0, 4):
                continue
            b = reese_ind(n, E * 0.92, cutoff=450 if section == "tension" else 650)
            out += place(stereo_spread(b, width=0.25) * 0.8, i * E, dur)

    # Drive (bars 5-8)
    elif section == "drive":
        # Kick on 1, 2.5, 3
        for k in (0, 1.5, 2.0, 3.5):
            out += place(stereo_spread(kick_ind(hard=1.1, seed=seed + int(k))), k * BEAT, dur)
        for b in (1, 3):
            out += place(snare_ind(seed=seed + b) * 0.95, b * BEAT, dur)
        # 16th metallic hats
        for i in range(16):
            open_ = (i % 4 == 2)
            out += place(stereo_spread(hat_ind(open_=open_, velocity=0.5 if i % 2 else 0.85, seed=seed + i)), i * S, dur)
        # Saturated Reese bass with higher filter cutoff
        for i, n in enumerate(riff_notes):
            b = reese_ind(n, E * 0.92, cutoff=850)
            out += place(stereo_spread(b, width=0.3) * 0.85, i * E, dur)
        # 16th clockwork arpeggio
        arp_scale = [NOTES["D3"], NOTES["F3"], NOTES["A3"], NOTES["C4"], NOTES["Bb3"], NOTES["A3"], NOTES["F3"], NOTES["D3"]]
        for i in range(16):
            note = arp_scale[i % 8]
            out += place(stereo_spread(arp_ind(note), width=0.4) * 0.65, i * S, dur)

    # Climax / Anthem (bars 10-12)
    elif section == "anthem":
        # Four on the floor kick
        for b in range(4):
            out += place(stereo_spread(kick_ind(hard=1.3, seed=seed + b) * 1.1), b * BEAT, dur)
        for b in (1, 3):
            out += place(snare_ind(seed=seed + b) * 1.05, b * BEAT, dur)
        for i in range(16):
            out += place(stereo_spread(hat_ind(open_=(i % 4 == 2), velocity=0.85, seed=seed + i)), i * S, dur)
        # Harmonic progression: Bb -> C -> Dm
        prog = [NOTES["Bb2"], NOTES["Bb2"], NOTES["C3"], NOTES["C3"], NOTES["D2"], NOTES["D2"], NOTES["D2"], NOTES["D2"]]
        for i, n in enumerate(prog):
            b = reese_ind(n, E * 0.92, cutoff=1200, drive_amt=3.8)
            out += place(stereo_spread(b, width=0.4) * 0.9, i * E, dur)
        # Anthemic lead theme
        lead_notes = [NOTES["D4"], NOTES["F4"], NOTES["G4"], NOTES["A4"], NOTES["Bb4"], NOTES["A4"], NOTES["F4"], NOTES["D4"]]
        for i, n in enumerate(lead_notes):
            out += place(anthem_lead_ind(n, E * 0.9) * 0.75, i * E, dur)

    return out[:int(BAR * SR)]


# ==============================================================================
# ENGINE 2: CYBERPUNK / DARKSYNTH THRILLER (Carpenter Brut / Kavinsky)
# ==============================================================================

def kick_cyber(hard=1.0, seed=0):
    dur = 0.4
    t = t_axis(dur)
    f_sub = 55 + 160 * np.exp(-t / 0.028)
    sub = np.sin(2 * np.pi * np.cumsum(f_sub) / SR) * env_exp(dur, 0.22, 0.001)
    click = bandpass(np.random.default_rng(seed).uniform(-1, 1, int(0.012 * SR)), 2800, 8000) * env_exp(0.012, 0.002, 0.0001) * 0.6
    click = np.pad(click, (0, len(sub) - len(click)))
    return soft_saturate(sub * 1.3 + click * hard, 2.4)


def snare_cyber(seed=0):
    dur = 0.5
    t = t_axis(dur)
    rng = np.random.default_rng(seed)
    body = np.sin(2 * np.pi * 220 * t) * env_exp(dur, 0.06, 0.001) * 0.8
    noise_raw = rng.uniform(-1, 1, int(dur * SR))
    wires = bandpass(noise_raw, 1200, 7500) * env_exp(dur, 0.16, 0.001) * 1.1
    # 80s gated reverb burst
    verb = lowpass(noise_raw, 4500) * env_exp(dur, 0.25, 0.02) * 0.6
    gate = np.clip(1.8 - t / 0.24, 0, 1)
    combined = soft_saturate(body + wires + verb * gate, 2.2)
    return stereo_spread(combined, width=0.45)


def bass_cyber_seq(freq, dur=0.12, cutoff=800):
    t = t_axis(dur)
    s1 = saw_osc(freq, dur, -6)
    s2 = saw_osc(freq, dur, 6)
    filt = lowpass((s1 + s2) * 0.5, cutoff, order=3)
    env = env_exp(dur, 0.07, 0.002)
    return soft_saturate(filt * env, 2.6) * 0.85


def brass_cyber(freq, dur=0.5):
    t = t_axis(dur)
    s = (saw_osc(freq, dur, -10) + saw_osc(freq, dur, 0) + saw_osc(freq * 2, dur, 10)) / 3.0
    filt = lowpass(s, 1600, order=2)
    env = env_ahdsr(dur, a=0.02, h=0.08, d=0.15, s=0.7, r=0.1)
    return stereo_spread(soft_saturate(filt * env, 2.0), width=0.5)


def render_cyberpunk_bar(section, idx, seed=0):
    dur = BAR + 0.8
    out = np.zeros((int(dur * SR), 2))

    # 16th note bass sequencer pattern in D minor
    seq_notes = [NOTES["D2"], NOTES["D2"], NOTES["F2"], NOTES["D2"],
                 NOTES["G2"], NOTES["D2"], NOTES["Bb2"], NOTES["A2"],
                 NOTES["D2"], NOTES["D2"], NOTES["C3"], NOTES["D2"],
                 NOTES["Bb2"], NOTES["A2"], NOTES["G2"], NOTES["F2"]]

    if section in ("tension", "groove"):
        if section == "groove":
            for b in (0, 2):
                out += place(stereo_spread(kick_cyber(seed=seed + b)), b * BEAT, dur)
            for b in (1, 3):
                out += place(snare_cyber(seed=seed + b) * 0.85, b * BEAT, dur)
            for i in range(8):
                out += place(stereo_spread(hat_ind(velocity=0.6 if i % 2 else 0.85, seed=seed + i)), i * E, dur)
        # Bass on 8ths or 16ths
        step = E if section == "tension" else S
        n_steps = 8 if section == "tension" else 16
        for i in range(n_steps):
            n = seq_notes[i % 16]
            b = bass_cyber_seq(n, step * 0.85, cutoff=500 if section == "tension" else 750)
            out += place(stereo_spread(b, width=0.3), i * step, dur)

    elif section == "drive":
        # Four on the floor kick
        for b in range(4):
            out += place(stereo_spread(kick_cyber(hard=1.2, seed=seed + b)), b * BEAT, dur)
        for b in (1, 3):
            out += place(snare_cyber(seed=seed + b) * 0.95, b * BEAT, dur)
        for i in range(16):
            open_ = (i % 2 == 1)
            out += place(stereo_spread(hat_ind(open_=open_, velocity=0.85, seed=seed + i)), i * S, dur)
        # Driving 16th bass
        for i in range(16):
            n = seq_notes[i]
            b = bass_cyber_seq(n, S * 0.88, cutoff=1100)
            out += place(stereo_spread(b, width=0.35), i * S, dur)
        # Dark brass stabs on beats 1 and 3.5
        for b_pos in (0, 2.5):
            out += place(brass_cyber(NOTES["D3"], dur=0.45) * 0.65, b_pos * BEAT, dur)

    elif section == "anthem":
        for b in range(4):
            out += place(stereo_spread(kick_cyber(hard=1.4, seed=seed + b) * 1.15), b * BEAT, dur)
        for b in (1, 3):
            out += place(snare_cyber(seed=seed + b) * 1.1, b * BEAT, dur)
        for i in range(16):
            out += place(stereo_spread(hat_ind(open_=(i % 2 == 1), velocity=0.9, seed=seed + i)), i * S, dur)
        # Anthem chord bass: Bb -> C -> Dm
        prog = [NOTES["Bb2"]] * 4 + [NOTES["C3"]] * 4 + [NOTES["D2"]] * 8
        for i in range(16):
            b = bass_cyber_seq(prog[i], S * 0.88, cutoff=1600)
            out += place(stereo_spread(b, width=0.4), i * S, dur)
        # Screaming lead synth
        lead_scale = [NOTES["D4"], NOTES["F4"], NOTES["A4"], NOTES["D5"], NOTES["C5"], NOTES["Bb4"], NOTES["A4"], NOTES["G4"]]
        for i, n in enumerate(lead_scale):
            l = anthem_lead_ind(n, E * 0.9) * 0.8
            out += place(l, i * E, dur)

    return out[:int(BAR * SR)]


# ==============================================================================
# ENGINE 3: CINEMATIC HYBRID TRAILER / CLOCKWORK (Zimmer / Woodkid / Junkie XL)
# ==============================================================================

def taiko_boom(dur=1.2, hard=1.0, seed=0):
    t = t_axis(dur)
    f_drop = 60 * np.exp(-t / 0.06) + 38
    body = np.sin(2 * np.pi * np.cumsum(f_drop) / SR) * env_exp(dur, 0.45, 0.002)
    # Anvil/metal hit
    metal = bandpass(np.random.default_rng(seed).uniform(-1, 1, int(0.04 * SR)), 1400, 5000) * env_exp(0.04, 0.008, 0.0003) * 0.7
    metal = np.pad(metal, (0, len(body) - len(metal))) * hard
    return stereo_spread(soft_saturate(body * 1.5 + metal, 2.0), width=0.5)


def clock_tick_sound(seed=0):
    dur = 0.06
    t = t_axis(dur)
    click = np.sin(2 * np.pi * 3200 * t) * env_exp(dur, 0.008, 0.0001)
    wood = bandpass(np.random.default_rng(seed).uniform(-1, 1, int(dur * SR)), 800, 3000) * env_exp(dur, 0.012, 0.0002) * 0.6
    return stereo_spread(click + wood, width=0.2) * 0.5


def cello_note(semitone_from_c2, dur=0.35):
    """Real cello bowed spiccato note using CC0 Clean Samples."""
    sample_path = TIDAL_CELLO / "08_C2_bowed_short_hammered.wav"
    raw = load_sample(str(sample_path), pitch_semitones=semitone_from_c2)
    cut = raw[:int(dur * SR)].copy()
    f = int(0.04 * SR)
    if len(cut) > f:
        cut[-f:] *= np.linspace(1, 0, f)
    # Lowpass warmth + stereo room
    shaped = lowpass(cut, 3800)
    return stereo_spread(shaped * 1.2, width=0.4)


def brass_braam_trailer(freq, dur=1.8):
    t = t_axis(dur)
    s = (saw_osc(freq, dur, -12) + saw_osc(freq, dur, 0) + saw_osc(freq, dur, 12)) / 3.0
    f_env = 300 + 1600 * np.exp(-t / 0.3)
    filt = lowpass(s, 1200, order=2)
    driven = soft_saturate(filt * 1.8, 3.5)
    return stereo_spread(driven * env_exp(dur, 0.9, 0.005), width=0.6)


def render_cinematic_bar(section, idx, seed=0):
    dur = BAR + 0.8
    out = np.zeros((int(dur * SR), 2))

    # Cello pitches relative to C2 (0 = C2, 2 = D2, 5 = F2, 7 = G2, 9 = A2, 10 = Bb2, 12 = C3, 14 = D3)
    cello_riff = [2, 2, 2, 5, 7, 2, 10, 9]  # D, D, D, F, G, D, Bb, A

    # Clock ticking mechanism on 16ths
    for i in range(16):
        out += place(clock_tick_sound(seed=seed + i) * (0.8 if i % 4 == 0 else 0.4), i * S, dur)

    if section in ("tension", "groove"):
        if section == "groove":
            for b in (0, 2):
                out += place(taiko_boom(dur=1.0, hard=0.9, seed=seed + b) * 0.9, b * BEAT, dur)
        # Cello spiccato on 8ths
        for i, semi in enumerate(cello_riff):
            if section == "tension" and i not in (0, 4):
                continue
            c = cello_note(semi, dur=E * 0.85)
            out += place(c * 0.75, i * E, dur)

    elif section == "drive":
        # Big Taiko on 1, 2.5, 3
        for k in (0, 1.5, 2.0, 3.5):
            out += place(taiko_boom(dur=1.2, hard=1.2, seed=seed + int(k)), k * BEAT, dur)
        for b in (1, 3):
            # Heavy snare/metal rim
            out += place(snare_ind(seed=seed + b) * 0.8, b * BEAT, dur)
        # Driving 16th cello ostinato
        for i in range(16):
            semi = cello_riff[i % 8]
            c = cello_note(semi, dur=S * 0.85)
            out += place(c * 0.7, i * S, dur)
        # Brass swell on beat 1
        out += place(brass_braam_trailer(NOTES["D1"], dur=1.2) * 0.65, 0, dur)

    elif section == "anthem":
        # Massive battle march
        for b in range(4):
            out += place(taiko_boom(dur=1.2, hard=1.4, seed=seed + b) * 1.1, b * BEAT, dur)
        for b in (1, 3):
            out += place(snare_ind(seed=seed + b) * 1.0, b * BEAT, dur)
        # Full brass braam choir: Bb -> C -> Dm
        prog_semi = [10, 10, 12, 12, 14, 14, 14, 14]
        for i, semi in enumerate(prog_semi):
            c = cello_note(semi, dur=E * 0.85)
            out += place(c * 0.9, i * E, dur)
        out += place(brass_braam_trailer(NOTES["D1"], dur=1.7) * 0.85, 0, dur)

    return out[:int(BAR * SR)]


# ==============================================================================
# ENGINE 4: HEAVY ELECTRO-ROCK / RIOT (The Prodigy / Death From Above)
# ==============================================================================

def rock_kick(seed=0):
    sample_path = DRUMS_CC0 / "Kick_4.wav"
    raw = load_sample(str(sample_path))
    # Layer with 50 Hz sub thump
    t = t_axis(0.4)
    sub = np.sin(2 * np.pi * 52 * t) * env_exp(0.4, 0.2, 0.001)
    combined = soft_saturate(raw[:len(sub)] * 1.1 + sub * 0.7, 2.2)
    return stereo_spread(combined, width=0.2)


def rock_snare(seed=0):
    sample_path = DRUMS_CC0 / ("Snare_1.wav" if seed % 2 == 0 else "Snare_2.wav")
    raw = load_sample(str(sample_path))
    driven = soft_saturate(raw * 1.3, 2.0)
    return stereo_spread(driven, width=0.4)


def rock_hat(open_=False, seed=0):
    sample_path = DRUMS_CC0 / ("High_Hat_Open_Close_2.wav" if open_ else "High_Hat_1.wav")
    raw = load_sample(str(sample_path))
    dur = 0.22 if open_ else 0.07
    cut = raw[:int(dur * SR)].copy()
    f = int(0.02 * SR)
    if len(cut) > f:
        cut[-f:] *= np.linspace(1, 0, f)
    return stereo_spread(cut * 0.7, width=0.3)


def fuzz_bass_rock(freq, dur=0.25):
    """Overdriven electric bass guitar with amp cabinet saturation."""
    sample_path = TIDAL_BASS / "05_c2_pick_short.wav"
    # Pitch shift relative to C2
    semi = int(round(12 * np.log2(freq / NOTES["C2"])))
    raw = load_sample(str(sample_path), pitch_semitones=semi)
    cut = raw[:int(dur * SR)].copy()
    # High-gain fuzz drive
    fuzz = soft_saturate(cut * 2.8, 4.0)
    # Speaker cabinet bandpass emulation (100 Hz - 4.5 kHz)
    cab = bandpass(fuzz, 110, 4200, order=3)
    return stereo_spread(cab * 1.1, width=0.3)


def render_electro_rock_bar(section, idx, seed=0):
    dur = BAR + 0.8
    out = np.zeros((int(dur * SR), 2))

    # Gritty rock riff notes in D minor
    riff_notes = [NOTES["D2"], NOTES["D2"], NOTES["D2"], NOTES["F2"],
                  NOTES["G2"], NOTES["D2"], NOTES["Bb2"], NOTES["A2"]]

    if section in ("tension", "groove"):
        if section == "groove":
            for b in (0, 2):
                out += place(rock_kick(seed=seed + b), b * BEAT, dur)
            for b in (1, 3):
                out += place(rock_snare(seed=seed + b) * 0.85, b * BEAT, dur)
            for i in range(8):
                out += place(rock_hat(open_=(i == 6), seed=seed + i), i * E, dur)
        for i, n in enumerate(riff_notes):
            if section == "tension" and i not in (0, 4):
                continue
            b = fuzz_bass_rock(n, dur=E * 0.9)
            out += place(b * 0.8, i * E, dur)

    elif section == "drive":
        # Driving rock groove with snare ghost notes
        for b in (0, 1.5, 2.0, 3.0):
            out += place(rock_kick(seed=seed + int(b)), b * BEAT, dur)
        for b in (1, 3):
            out += place(rock_snare(seed=seed + b) * 0.95, b * BEAT, dur)
        for i in range(8):
            out += place(rock_hat(open_=(i % 2 == 1), seed=seed + i) * 0.85, i * E, dur)
        for i, n in enumerate(riff_notes):
            b = fuzz_bass_rock(n, dur=E * 0.92)
            out += place(b * 0.88, i * E, dur)
        # Power chord saw stabs
        for b in (0, 2):
            chord = (saw_osc(NOTES["D3"], 0.3) + saw_osc(NOTES["A3"], 0.3) + saw_osc(NOTES["D4"], 0.3)) / 3.0
            out += place(stereo_spread(soft_saturate(chord, 2.5) * 0.5, width=0.5), b * BEAT, dur)

    elif section == "anthem":
        for b in range(4):
            out += place(rock_kick(seed=seed + b) * 1.1, b * BEAT, dur)
        for b in (1, 3):
            out += place(rock_snare(seed=seed + b) * 1.1, b * BEAT, dur)
        for i in range(8):
            out += place(rock_hat(open_=True, seed=seed + i) * 0.9, i * E, dur)
        prog = [NOTES["Bb2"], NOTES["Bb2"], NOTES["C3"], NOTES["C3"], NOTES["D2"], NOTES["D2"], NOTES["D2"], NOTES["D2"]]
        for i, n in enumerate(prog):
            b = fuzz_bass_rock(n, dur=E * 0.95)
            out += place(b * 0.95, i * E, dur)

    return out[:int(BAR * SR)]


# ==============================================================================
# AUDITION CLIP RENDERERS (16 BARS EACH = ~29s)
# ==============================================================================

ENGINES = {
    "1-industrial": render_industrial_bar,
    "2-cyberpunk": render_cyberpunk_bar,
    "3-cinematic-hybrid": render_cinematic_bar,
    "4-electro-rock": render_electro_rock_bar,
}

# 16-bar audition structure: 2 tension, 2 groove, 4 drive, 1 hit duck, 3 anthem, 4 tail
AUDITION_ARRANGEMENT = [
    ("tension", 2),
    ("groove", 2),
    ("drive", 4),
    ("anthem", 4),
    ("tension", 4),
]


def render_audition_clip(engine_name, seed=42):
    """Render a ~29s audition clip for the given engine, with a simulated card hit at bar 9."""
    engine_fn = ENGINES[engine_name]
    total_bars = sum(bars for _, bars in AUDITION_ARRANGEMENT)
    total_dur = total_bars * BAR + 1.5
    full_audio = np.zeros((int(total_dur * SR), 2))
    
    current_time = 0.0
    bar_idx = 0
    for section, n_bars in AUDITION_ARRANGEMENT:
        for b in range(n_bars):
            bar_audio = engine_fn(section, bar_idx, seed=seed + bar_idx)
            full_audio += place(bar_audio, current_time, total_dur)
            current_time += BAR
            bar_idx += 1

    # Add a simulated card slam impact on bar 9 (beat 32 = 8 * BAR)
    hit_time = 8 * BAR
    from sfx import LIBRARY
    impact_hit = LIBRARY["impact_mid"]()
    # Duck music around hit
    hit_idx = int(hit_time * SR)
    duck_len = int(0.3 * SR)
    duck_curve = np.linspace(0.45, 1.0, duck_len)
    full_audio[hit_idx:hit_idx + duck_len] *= duck_curve[:, None]
    full_audio += place(stereo_spread(impact_hit * 0.75, width=0.4), hit_time, total_dur)

    return full_audio
