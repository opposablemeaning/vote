"""Drum kits for the music bed. Same groove, different instruments (music.py picks one).

A  current: the original synth kit (white-noise hats, phonk cowbell)
B  punchy:  layered kick (sub + knock + click), tuned-body snare, TR-808-style metallic hats
C  heavy:   saturated kick, metallic clank snare (modal partials), crushed hats, anvil perc
D  taiko:   cinematic drums (membrane modes) in a big hall, shaker instead of hats
E  acoustic: CC0 acoustic one-shots (Fractanimal kit, Freesound pack 32722) + a sub under the kick
F  808:     real Roland TR-808 samples (Michael Fischer set, CC0, tidalcycles/sounds-tr808-fischer)

Each kit: kick(seed, hard), snare(seed), hat(seed, open_), perc(seed), plus `glue`, the
drum-bus chain (compression, saturation, room) applied per bar before the 808 bass is added,
and `level` (dB fader after the glue) so every kit's drums sit equally loud above 150 Hz,
where phone speakers actually play.
"""

from functools import lru_cache

import numpy as np
import soundfile as sf
from scipy import signal

from sfx import ROOT, SR, bandpass, drive, env_exp, highpass, lowpass, mix, noise, reverb, sweep, t_axis

DRUMS_CC0 = ROOT / "assets" / "audio" / "cc0" / "drums"
TR808 = ROOT / "assets" / "audio" / "cc0" / "tr808"


# ---------- bus processing ----------

def compress(x, thresh_db=-16.0, ratio=3.0, window=0.01, smooth=0.005):
    """Feed-forward RMS compressor (symmetric detector is plenty for bus glue)."""
    a = np.exp(-1.0 / (window * SR))
    env = np.sqrt(np.maximum(signal.lfilter([1 - a], [1, -a], x * x), 1e-12))
    thr = 10 ** (thresh_db / 20)
    gain = np.where(env > thr, (env / thr) ** (1 / ratio - 1), 1.0)
    b = np.exp(-1.0 / (smooth * SR))
    gain = signal.lfilter([1 - b], [1, -b], gain)
    return x * gain


def glue(x, room=0.35, wet=0.12, sat=1.3, thresh_db=-16.0):
    y = compress(x, thresh_db, 3.0)
    y = np.tanh(y * sat) / np.tanh(sat)
    return reverb(y, room, wet, seed=31)[: len(x)] if wet > 0 else y


# ---------- A: current ----------

def kick_a(seed=0, hard=1.0):
    x = sweep(170 * hard, 42, 0.45) * env_exp(0.45, 0.12, 0.0008)
    click = highpass(noise(0.01, seed), 3000) * env_exp(0.01, 0.002, 0.0002) * 0.6
    return drive(mix(x * 1.2, click), 2.0 + hard)


def snare_a(seed=0):
    bursts = sum(_place(bandpass(noise(0.02, seed + i), 900, 6000) * env_exp(0.02, 0.006, 0.0003), i * 0.011, 0.3)
                 for i in range(3))
    tail = bandpass(noise(0.3, seed + 9), 900, 5000) * env_exp(0.3, 0.07, 0.001) * 0.7
    snap = sweep(240, 180, 0.12) * env_exp(0.12, 0.03, 0.0005) * 0.5
    return drive(mix(bursts, _place(tail, 0.03, 0.3), snap), 1.5)


def hat_a(seed=0, open_=False):
    d = 0.18 if open_ else 0.04
    return highpass(noise(d, seed), 7000) * env_exp(d, 0.06 if open_ else 0.01, 0.0003)


def perc_a(seed=0):
    t = t_axis(0.25)
    x = (signal.square(2 * np.pi * 540 * t) + signal.square(2 * np.pi * 800 * t)) * env_exp(0.25, 0.06, 0.0005)
    return bandpass(x, 500, 4000) * 0.4


def _place(x, at, total):
    out = np.zeros(int(total * SR))
    i = int(at * SR)
    seg = x[: max(0, len(out) - i)]
    out[i : i + len(seg)] += seg
    return out


# ---------- B: punchy layered ----------

def kick_b(seed=0, hard=1.0):
    dur = 0.6
    t = t_axis(dur)
    f_sub = 46 + 20 * np.exp(-t / 0.04)
    sub = np.sin(2 * np.pi * np.cumsum(f_sub) / SR) * env_exp(dur, 0.30, 0.001)
    knock = sweep(200 * hard, 70, dur) * env_exp(dur, 0.045, 0.0005)
    click = bandpass(noise(0.012, seed), 2500, 9000) * env_exp(0.012, 0.0025, 0.0001)
    return mix(sub, drive(knock * 1.6, 2.5) * 0.75, click * 0.45)


def snare_b(seed=0):
    dur = 0.45
    t = t_axis(dur)
    f = 185 + 45 * np.exp(-t / 0.012)
    body = (np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.8 + np.sin(2 * np.pi * 332 * t) * 0.3) * env_exp(dur, 0.055, 0.0005)
    wires = bandpass(noise(dur, seed), 1800, 9000) * env_exp(dur, 0.11, 0.001)
    crack = highpass(noise(0.01, seed + 1), 3500) * env_exp(0.01, 0.002, 0.0001)
    return reverb(mix(drive(body * 1.3, 1.8), wires * 0.75, crack * 0.5), 0.3, 0.2, seed=seed + 3)[: int(0.6 * SR)]


HAT_808 = [205.3, 304.4, 369.6, 522.7, 540.0, 800.0]  # TR-808's six square oscillators


def metal(dur, freqs=HAT_808, phase=0.0):
    t = t_axis(dur)
    return sum(signal.square(2 * np.pi * f * t + phase + k) for k, f in enumerate(freqs)) / len(freqs)


def hat_b(seed=0, open_=False):
    d = 0.3 if open_ else 0.06
    x = highpass(bandpass(metal(d, phase=seed * 0.1), 6000, 12500), 6500)
    return x * env_exp(d, 0.085 if open_ else 0.014, 0.0003) * 0.9


def perc_b(seed=0):
    """Woody rim click instead of the phonk cowbell."""
    t = t_axis(0.12)
    tone = (np.sin(2 * np.pi * 1650 * t) * 0.6 + np.sin(2 * np.pi * 520 * t) * 0.4) * env_exp(0.12, 0.018, 0.0003)
    return mix(tone, bandpass(noise(0.03, seed), 1000, 5000) * env_exp(0.03, 0.006, 0.0002) * 0.5) * 0.7


# ---------- C: heavy / industrial ----------

def modal(f0, ratios, decays, dur, amps=None, seed=0):
    t = t_axis(dur)
    amps = amps or [1.0 / (1 + k * 0.4) for k in range(len(ratios))]
    rng = np.random.default_rng(seed)
    return sum(a * np.sin(2 * np.pi * f0 * r * t + rng.uniform(0, 6.28)) * np.exp(-t / d)
               for r, d, a in zip(ratios, decays, amps))


def kick_c(seed=0, hard=1.0):
    k = kick_b(seed, hard) * 1.2
    clank = modal(95, [1, 2.71, 4.13, 6.02], [0.05, 0.03, 0.02, 0.015], 0.3, seed=seed) * 0.35
    return drive(mix(k, highpass(clank, 200)), 3.2)


def snare_c(seed=0):
    dur = 0.5
    sheet = modal(380, [1, 2.76, 4.55, 6.5, 8.45, 11.6], [0.16, 0.11, 0.08, 0.06, 0.045, 0.03], dur, seed=seed)
    hit = bandpass(noise(dur, seed + 2), 1200, 8000) * env_exp(dur, 0.07, 0.0005)
    body = sweep(210, 150, dur) * env_exp(dur, 0.05, 0.0005)
    x = drive(mix(sheet * 0.6, hit * 0.8, body * 0.7), 3.0)
    wet = reverb(x, 0.8, 0.5, seed=seed + 5)[: int(0.8 * SR)]
    gate = np.clip(1.6 - t_axis(0.8) / 0.18, 0, 1)  # gated verb: big, then chopped
    return wet * gate


def hat_c(seed=0, open_=False):
    d = 0.2 if open_ else 0.05
    x = bandpass(noise(d, seed), 3000, 11000)
    x = np.repeat(x[::6], 6)[: len(x)]  # sample-and-hold grit
    return highpass(x, 2500) * env_exp(d, 0.06 if open_ else 0.012, 0.0003) * 0.8


def perc_c(seed=0):
    return drive(modal(1180, [1, 2.4, 3.9, 5.6], [0.09, 0.06, 0.04, 0.03], 0.25, seed=seed), 1.8) * 0.45


# ---------- D: cinematic taiko / toms ----------

MEMBRANE = [1.0, 1.593, 2.136, 2.296, 2.653, 2.918, 3.156, 3.501]  # circular membrane mode ratios


def drum_hit(f0, dur, decay, seed=0, stick=0.5):
    t = t_axis(dur)
    bend = 1 + 0.12 * np.exp(-t / 0.03)  # pitch drops as the skin settles
    rng = np.random.default_rng(seed)
    body = sum((1 / (1 + 0.8 * k)) * np.sin(2 * np.pi * np.cumsum(f0 * r * bend) / SR + rng.uniform(0, 6.28))
               * np.exp(-t / (decay / (1 + 0.6 * k))) for k, r in enumerate(MEMBRANE))
    hit = bandpass(noise(0.015, seed + 1), 800, 4500) * env_exp(0.015, 0.004, 0.0002)
    return mix(drive(body * 0.9, 1.5), hit * stick)


def kick_d(seed=0, hard=1.0):
    return drum_hit(58 * (0.95 + 0.1 * hard), 1.2, 0.55, seed, stick=0.35)


def snare_d(seed=0):
    tom = drum_hit(150, 0.8, 0.28, seed + 4, stick=0.7)
    rim = bandpass(noise(0.03, seed + 6), 1500, 7000) * env_exp(0.03, 0.008, 0.0002)
    return mix(tom, rim * 0.6)


def hat_d(seed=0, open_=False):
    d = 0.12
    t = t_axis(d)
    shape = np.clip(t / 0.012, 0, 1) * np.exp(-t / (0.05 if open_ else 0.03))
    return bandpass(noise(d, seed), 4000, 9000) * shape * 0.55


def perc_d(seed=0):
    t = t_axis(0.1)
    block = np.sin(2 * np.pi * 880 * t) * env_exp(0.1, 0.02, 0.0003)
    return mix(block, bandpass(noise(0.02, seed), 700, 3000) * env_exp(0.02, 0.005, 0.0002) * 0.4) * 0.5


# ---------- E: CC0 acoustic one-shots ----------

@lru_cache(maxsize=None)
def sample(name, folder=None):
    x, sr = sf.read((folder or DRUMS_CC0) / f"{name}.wav")
    x = x.mean(axis=1) if x.ndim > 1 else x
    if sr != SR:
        x = signal.resample_poly(x, SR, sr)
    i = int(np.argmax(np.abs(x) > 0.05 * np.max(np.abs(x))))  # trim to the onset
    x = x[max(0, i - 24):]
    return x / np.max(np.abs(x))


def _cut(x, dur, fade=0.03):
    x = x[: int(dur * SR)].copy()
    f = min(int(fade * SR), len(x))
    x[-f:] *= np.linspace(1, 0, f)
    return x


def kick_e(seed=0, hard=1.0):
    acoustic = _cut(sample("Kick_4"), 0.5)
    t = t_axis(0.5)
    sub = np.sin(2 * np.pi * np.cumsum(48 + 14 * np.exp(-t / 0.03)) / SR) * env_exp(0.5, 0.22, 0.002)
    return mix(acoustic * 0.95, sub * 0.55 * hard)


def snare_e(seed=0):
    return _cut(sample("Snare_1" if seed % 2 == 0 else "Snare_2"), 0.6) * 0.9


def hat_e(seed=0, open_=False):
    if open_:
        return _cut(sample("High_Hat_Open_Close_2"), 0.3) * 0.55
    return _cut(sample(["High_Hat_1", "High_Hat_2"][seed % 2]), 0.12) * 0.5


def perc_e(seed=0):
    return _cut(sample("Cymbal_Centre_Bell"), 0.35, 0.1) * 0.3


# ---------- F: real TR-808 (CC0) ----------

def kick_f(seed=0, hard=1.0):
    return _cut(sample("BD2550", TR808), 0.7, 0.08) * (0.85 + 0.15 * hard)


def snare_f(seed=0):
    return mix(_cut(sample("SD5075", TR808), 0.4) * 0.75, _cut(sample("CP", TR808), 0.5, 0.1) * 0.6)


def hat_f(seed=0, open_=False):
    return _cut(sample("OH25", TR808), 0.35) * 0.5 if open_ else _cut(sample("CH", TR808), 0.12) * 0.45


def perc_f(seed=0):
    return _cut(sample("CB", TR808), 0.3, 0.08) * 0.35


# ---------- alternatives for kit A's cowbell slot (16ths 2, 7, 10, 13 of drive/frenzy bars) ----------
# gains match the current synth cowbell's loudness above 150 Hz, so the A/B is about timbre

def perc_cb808(seed=0):
    return _cut(sample("CB", TR808), 0.3, 0.08) * 1.48


def perc_rim808(seed=0):
    return _cut(sample("RS", TR808), 0.15, 0.03) * 2.2


def perc_clave808(seed=0):
    return _cut(sample("CL", TR808), 0.15, 0.03) * 1.3


def perc_tom808(seed=0):
    return _cut(sample("LT50", TR808), 0.35, 0.08) * 2.86


def perc_shaker808(seed=0):
    return _cut(sample("MA", TR808), 0.12, 0.03) * 1.49


PLUCK_NOTES = {2: 293.66, 7: 349.23, 10: 220.0, 13: 261.63}  # D4 F4 A3 C4: chord tones over the D-minor riff


def pluck(freq, dur=0.6, damp=0.995, seed=0):
    """Karplus-Strong plucked string: a noise burst circulating in a damped delay line."""
    n = int(round(SR / freq))
    burst = lowpass(noise(n / SR, seed), 3500)
    x = np.zeros(int(dur * SR))
    x[:n] = burst[:n]
    a = np.zeros(n + 2)
    a[0], a[n], a[n + 1] = 1.0, -0.5 * damp, -0.5 * damp
    y = signal.lfilter([1.0], a, x)
    y *= np.minimum(1.0, (dur - t_axis(dur)) / 0.05)  # short fade at the end
    return y / max(1e-9, np.max(np.abs(y)))


def perc_pluck(seed=0):
    return pluck(PLUCK_NOTES.get(seed % 16, 293.66), seed=seed) * 0.6


def perc_none(seed=0):
    return np.zeros(16)


PERC_OPTIONS = {
    "cowbell": perc_a,
    "cowbell808": perc_cb808,
    "rimshot808": perc_rim808,
    "clave808": perc_clave808,
    "lowtom808": perc_tom808,
    "shaker808": perc_shaker808,
    "pluck": perc_pluck,
    "none": perc_none,
}


KITS = {
    "A": dict(kick=kick_a, snare=snare_a, hat=hat_a, perc=perc_a, glue=None, hat_gain=1.0, level=0.0),
    "B": dict(kick=kick_b, snare=snare_b, hat=hat_b, perc=perc_b, glue=dict(room=0.35, wet=0.12), hat_gain=0.7, level=5.0),
    "C": dict(kick=kick_c, snare=snare_c, hat=hat_c, perc=perc_c, glue=dict(room=0.5, wet=0.15, sat=1.8, thresh_db=-18), hat_gain=0.8, level=4.7),
    "D": dict(kick=kick_d, snare=snare_d, hat=hat_d, perc=perc_d, glue=dict(room=1.8, wet=0.32, sat=1.2), hat_gain=0.6, hats_8ths=True, level=8.5),
    "E": dict(kick=kick_e, snare=snare_e, hat=hat_e, perc=perc_e, glue=dict(room=0.45, wet=0.14, sat=1.2), hat_gain=0.9, level=10.0),
    "F": dict(kick=kick_f, snare=snare_f, hat=hat_f, perc=perc_f, glue=dict(room=0.3, wet=0.08, sat=1.4), hat_gain=0.9, level=12.5),
}

# kit A with a different instrument in the cowbell slot, e.g. music.KIT = "A-clave808"
for _name, _fn in PERC_OPTIONS.items():
    KITS[f"A-{_name}"] = dict(KITS["A"], perc=_fn)
