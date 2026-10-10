"""Synthesized sound design for VOTE. THEM. OUT.

Every sound is a pure function of its parameters (seeded noise), so renders are
reproducible. Run `python scripts/sfx.py` to write the SFX library to
assets/audio/sfx/. scripts/music.py and scripts/mix.py import these helpers.
"""

from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48_000
ROOT = Path(__file__).resolve().parent.parent
SFX_DIR = ROOT / "assets" / "audio" / "sfx"


# ---------- primitives ----------

def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def noise(dur, seed=0):
    return np.random.default_rng(seed).uniform(-1, 1, int(dur * SR))


def env_exp(dur, decay, attack=0.002):
    t = t_axis(dur)
    a = np.clip(t / attack, 0, 1) if attack > 0 else 1.0
    return a * np.exp(-t / decay)


def sweep(f0, f1, dur, curve="exp"):
    """Sine with a frequency glide from f0 to f1; returns samples."""
    t = t_axis(dur)
    if curve == "exp":
        f = f0 * (f1 / f0) ** (t / dur)
    else:
        f = f0 + (f1 - f0) * t / dur
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def bandpass(x, lo, hi, order=4):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lowpass(x, fc, order=4):
    return signal.sosfilt(signal.butter(order, fc, btype="low", fs=SR, output="sos"), x)


def highpass(x, fc, order=4):
    return signal.sosfilt(signal.butter(order, fc, btype="high", fs=SR, output="sos"), x)


def moving_band(x, centers, width_oct=0.6):
    """Time-varying band-pass via STFT masking. centers: array of Hz per frame."""
    f, _, Z = signal.stft(x, fs=SR, nperseg=1024)
    n = Z.shape[1]
    c = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(centers)), centers)
    logf = np.log2(np.maximum(f, 1))[:, None]
    mask = np.exp(-0.5 * ((logf - np.log2(c)[None, :]) / width_oct) ** 2)
    _, y = signal.istft(Z * mask, fs=SR, nperseg=1024)
    return y[: len(x)]


def drive(x, amount=2.0):
    return np.tanh(x * amount) / np.tanh(amount)


def norm(x, peak=0.95):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


def pad_to(x, n):
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def mix(*parts):
    n = max(len(p) for p in parts)
    return sum(pad_to(p, n) for p in parts)


def place(x, at, total):
    """Place x starting at `at` seconds inside a buffer of `total` seconds."""
    out = np.zeros(int(total * SR))
    i = int(at * SR)
    seg = x[: max(0, len(out) - i)]
    out[i : i + len(seg)] += seg
    return out


def stereo(x, width=0.0, seed=0):
    """Mono -> stereo. width>0 adds a tiny decorrelated delay for size."""
    if width <= 0:
        return np.stack([x, x], axis=1)
    d = int(0.012 * width * SR)
    r = np.concatenate([np.zeros(d), x])[: len(x)]
    return np.stack([x, (x * 0.6 + r * 0.4)], axis=1)


def reverb(x, size=1.2, wet=0.3, seed=7):
    """Cheap convolution reverb with an exponentially decaying noise IR."""
    ir = noise(size, seed) * np.exp(-t_axis(size) / (size / 5))
    ir = lowpass(ir, 6000)
    ir /= np.sqrt(np.sum(ir**2))
    w = signal.fftconvolve(x, ir)[: len(x) + int(size * SR)]
    return pad_to(x, len(w)) * (1 - wet) + w * wet


# ---------- sound effects ----------

def impact(escalate=0.0, seed=1):
    """Hard hit: transient crack + pitched thump + sub tail. escalate 0..1 brightens."""
    dur = 2.2
    f_top = 70 + 40 * escalate
    thump = sweep(f_top * 2.2, f_top * 0.55, dur) * env_exp(dur, 0.45, 0.001)
    sub = sweep(48, 32, dur) * env_exp(dur, 0.9, 0.004) * 0.8
    crack = highpass(noise(0.08, seed), 1500 - 600 * escalate) * env_exp(0.08, 0.012, 0.0005)
    body = bandpass(noise(0.6, seed + 1), 120, 900) * env_exp(0.6, 0.09, 0.001) * 0.7
    x = mix(drive(thump * 1.4, 2.5), sub, crack * (0.8 + 0.6 * escalate), body)
    return norm(reverb(x, 1.6, 0.18 + 0.1 * escalate))


def subdrop(dur=2.0):
    x = sweep(120, 28, dur) * env_exp(dur, dur / 2.5, 0.01)
    return norm(drive(x, 1.6))


def whoosh(dur=0.7, rising=True, seed=2):
    n = noise(dur, seed)
    c = np.geomspace(300, 6000, 32) if rising else np.geomspace(6000, 300, 32)
    y = moving_band(n, c, 0.5)
    t = t_axis(dur)
    shape = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** (0.6 if rising else 1.4)
    return norm(y * shape)


def stamp(seed=3):
    """Rubber stamp slam: low thud + papery slap + tiny rattle."""
    thud = sweep(160, 70, 0.25) * env_exp(0.25, 0.05, 0.0008)
    slap = lowpass(noise(0.15, seed), 3500) * env_exp(0.15, 0.025, 0.0005)
    rattle = bandpass(noise(0.12, seed + 1), 2000, 6000) * env_exp(0.12, 0.03, 0.01) * 0.25
    return norm(reverb(mix(drive(thud * 1.5, 2), slap, place(rattle, 0.02, 0.2)), 0.5, 0.12))


def card_slap(seed=4, pitch=1.0):
    """Paper card landing on a desk."""
    slap = bandpass(noise(0.12, seed), 400 * pitch, 5000) * env_exp(0.12, 0.018, 0.0004)
    thump = sweep(110 * pitch, 60 * pitch, 0.15) * env_exp(0.15, 0.03, 0.0005) * 0.6
    return norm(mix(slap, thump))


def tick(seed=5, pitch=1.0):
    x = bandpass(noise(0.02, seed), 2500 * pitch, 7000) * env_exp(0.02, 0.003, 0.0002)
    return norm(x)


def spin(dur=1.2, start_rate=10, end_rate=40, seed=6):
    """Slot reel spinning: ticks accelerating from start_rate to end_rate per second."""
    out = np.zeros(int(dur * SR))
    t, k = 0.0, 0
    while t < dur:
        rate = start_rate + (end_rate - start_rate) * (t / dur)
        x = tick(seed + k % 4, 1.0 + 0.05 * (k % 3)) * 0.8
        out += place(x, t, dur)
        t += 1.0 / rate
        k += 1
    return norm(out)


def kachunk(seed=8):
    """Slot reel locks: two clicks, a heavy thunk, and a metallic ping."""
    c1 = tick(seed, 0.8)
    c2 = tick(seed + 1, 0.6)
    thunk = sweep(140, 55, 0.3) * env_exp(0.3, 0.06, 0.0008)
    partials = [1.0, 2.76, 5.40, 8.93]
    ping = sum(np.sin(2 * np.pi * 820 * p * t_axis(0.9)) * env_exp(0.9, 0.25 / p, 0.001) / (i + 1)
               for i, p in enumerate(partials))
    x = mix(place(c1, 0, 1.0), place(c2, 0.045, 1.0), place(drive(thunk * 1.6, 2.2), 0.05, 1.0),
            place(ping * 0.35, 0.055, 1.0))
    return norm(reverb(x, 0.8, 0.15))


def register(seed=9):
    """Cash register: drawer clack + FM bell 'ching'."""
    t = t_axis(1.4)
    mod = np.sin(2 * np.pi * 1500 * 1.41 * t) * 4.0 * env_exp(1.4, 0.3)
    bell = np.sin(2 * np.pi * 1500 * t + mod) * env_exp(1.4, 0.35, 0.001)
    bell2 = np.sin(2 * np.pi * 2250 * t) * env_exp(1.4, 0.2, 0.001) * 0.3
    clack = bandpass(noise(0.1, seed), 800, 5000) * env_exp(0.1, 0.02, 0.0005)
    x = mix(clack, place(bell + bell2, 0.03, 1.5) * 0.7)
    return norm(reverb(x, 0.9, 0.2))


def glitch(src=None, seed=10, dur=0.5):
    """Stutter + bitcrush + sample-rate reduction of a source."""
    rng = np.random.default_rng(seed)
    if src is None:
        src = mix(sweep(300, 2400, dur) * 0.5, bandpass(noise(dur, seed), 200, 8000) * 0.6)
    out = np.zeros(int(dur * SR))
    pos = 0
    while pos < len(out):
        L = int(rng.choice([0.012, 0.024, 0.048]) * SR)
        start = int(rng.uniform(0, max(1, len(src) - L)))
        seg = src[start : start + L]
        for _ in range(int(rng.integers(1, 4))):
            n = min(len(seg), len(out) - pos)
            if n <= 0:
                break
            out[pos : pos + n] = seg[:n]
            pos += n
    bits = 2 ** 5
    out = np.round(out * bits) / bits
    hold = 6
    out = np.repeat(out[::hold], hold)[: len(out)]
    return norm(out * env_exp(dur, dur, 0.001))


def riser(dur=3.0, seed=11):
    n = moving_band(noise(dur, seed), np.geomspace(200, 9000, 64), 0.45)
    tone = sweep(110, 1760, dur) * 0.25 + sweep(110 * 1.5, 1760 * 1.5, dur) * 0.12
    t = t_axis(dur)
    shape = (t / dur) ** 2.2
    return norm(mix(n, tone) * shape)


def heartbeat(seed=12):
    def beat(a):
        return sweep(70, 40, 0.25) * env_exp(0.25, 0.06, 0.004) * a
    return norm(lowpass(mix(place(beat(1.0), 0, 0.9), place(beat(0.7), 0.22, 0.9)), 400))


def boom_tail(seed=13, dur=4.0):
    """Long cinematic boom for the YOU / finale moment."""
    x = mix(sweep(90, 26, dur) * env_exp(dur, 1.3, 0.002),
            lowpass(noise(dur, seed), 300) * env_exp(dur, 0.8, 0.002) * 0.6,
            highpass(noise(0.1, seed + 1), 2000) * env_exp(0.1, 0.02, 0.0005) * 0.5)
    return norm(reverb(drive(x, 1.8), 2.5, 0.35))


def static_wall(dur=2.0, seed=14):
    """White-noise wall for the overload, band-limited so it isn't painful."""
    x = bandpass(noise(dur, seed), 150, 9000) * 0.6
    crackle = (np.random.default_rng(seed).random(int(dur * SR)) > 0.9985) * 1.0
    return norm(mix(x, crackle * 0.8) * np.linspace(0.3, 1.0, int(dur * SR)))


def tapestop(x, dur=0.6):
    """Slow a buffer to a stop over `dur` seconds (applied to the tail)."""
    n = int(dur * SR)
    rate = np.linspace(1.0, 0.0, n) ** 1.5
    idx = np.cumsum(rate)
    idx = idx[idx < len(x) - 1]
    return np.interp(idx, np.arange(len(x)), x) * np.linspace(1, 0, len(idx))


# ---------- finale / act 2 sounds ----------

def tick_tock(tock=False, seed=15):
    """Mechanical clock tick; tock is lower and woodier."""
    p = 0.8 if tock else 1.0
    click = bandpass(noise(0.03, seed), 1800 * p, 7000) * env_exp(0.03, 0.003, 0.0002)
    t = t_axis(0.12)
    body = (np.sin(2 * np.pi * 1150 * p * t) * 0.6 + np.sin(2 * np.pi * 2730 * p * t) * 0.3) * env_exp(0.12, 0.018, 0.0005)
    return norm(mix(click, body * 0.5))


def alarm_clock(dur=1.6, rate=19.0, seed=16):
    """Twin-bell mechanical alarm: a hammer alternating between two small bells."""
    partials, decays = [1.0, 2.32, 4.25, 6.63], [0.22, 0.10, 0.05, 0.03]
    ts_ax = t_axis(0.35)
    bells = [sum(np.sin(2 * np.pi * fb * p * ts_ax + i * 0.7) * np.exp(-ts_ax / d) / (i + 1)
                 for i, (p, d) in enumerate(zip(partials, decays))) for fb in (2150.0, 2580.0)]
    out = np.zeros(int(dur * SR))
    k, at = 0, 0.0
    while at < dur:
        clank = bandpass(noise(0.012, seed + k), 3000, 9000) * env_exp(0.012, 0.002, 0.0001) * 0.4
        out += place(mix(bells[k % 2] * 0.6, clank), at, dur)
        at += 1.0 / rate
        k += 1
    fade = np.ones(len(out))
    m = int(0.06 * SR)
    fade[-m:] = np.linspace(1, 0, m)
    return norm(out * fade)


def air_raid_siren(dur=7.0, f_lo=70.0, f_hi=430.0, wind_up=4.5, wind_down_at=None, seed=17):
    """Mechanical two-rotor siren: harmonic-rich tone that winds up, wobbles, winds down."""
    t = t_axis(dur)
    f = f_lo + (f_hi - f_lo) * (1 - np.exp(-t / (wind_up / 3.0)))
    if wind_down_at is not None:
        f_wd = f_lo + (f_hi - f_lo) * (1 - np.exp(-wind_down_at / (wind_up / 3.0)))
        td = np.clip(t - wind_down_at, 0, None)
        f = np.where(t > wind_down_at, f_lo * 0.6 + (f_wd - f_lo * 0.6) * np.exp(-td / 1.4), f)
    f = f * (1 + 0.012 * np.sin(2 * np.pi * 0.7 * t) + 0.004 * np.sin(2 * np.pi * 5.3 * t))

    def voice(freq, n_harm):
        ph = 2 * np.pi * np.cumsum(freq) / SR
        return sum((1 / k**1.15) * (freq * k < 12000) * np.sin(k * ph) for k in range(1, n_harm))

    x = voice(f, 12) + 0.7 * voice(f * 1.189, 10)  # minor-third chord between the rotors
    level = np.clip((f - f_lo * 0.6) / (f_hi - f_lo * 0.6), 0, 1)
    env = np.clip(t / 0.4, 0, 1) * (0.3 + 0.7 * level)
    air = bandpass(noise(dur, seed), 300, 4000) * 0.15
    y = lowpass((x + air) * env, 7000)
    return norm(reverb(drive(y * 0.8, 1.5), 2.8, 0.35))


def crowd_roar(dur=6.0, voices=48, swell=True, seed=18):
    """Many voiced 'yells' (jittered sawtooth through vowel formants) plus rumble and claps."""
    rng = np.random.default_rng(seed)
    t = t_axis(dur)
    n = len(t)
    vowels = [(730, 1090, 2440), (570, 840, 2410), (660, 1720, 2410), (490, 1350, 1690)]
    out = np.zeros(n)
    for v in range(voices):
        f0 = rng.uniform(105, 270) * (1 + 0.03 * np.sin(2 * np.pi * rng.uniform(3, 6) * t + rng.uniform(0, 6)))
        saw = 2 * ((np.cumsum(f0) / SR) % 1.0) - 1
        src = saw + 0.35 * noise(dur, seed + 100 + v)
        F, s = vowels[v % len(vowels)], rng.uniform(0.9, 1.2)
        y = sum(bandpass(src, f * s * 0.88, f * s * 1.12, order=2) * g for f, g in zip(F, (1.0, 0.55, 0.2)))
        rate, ph = rng.uniform(0.3, 1.8), rng.uniform(0, 2 * np.pi)
        am = 0.25 + 0.75 * np.clip(np.sin(2 * np.pi * rate * t + ph), 0, None) ** 1.3
        out += y * am
    rumble = lowpass(noise(dur, seed + 7), 250) * 0.8
    claps = np.zeros(n)
    for _ in range(int(dur * 25)):
        at = rng.uniform(0, dur)
        claps += place(bandpass(noise(0.015, int(at * 1000)), 1000, 5000) * env_exp(0.015, 0.004, 0.0002), at, dur)
    shape = (np.clip(t / dur, 0, 1) ** 0.7) if swell else np.ones(n)
    y = norm(out) * 0.8 + norm(rumble) * 0.35 + norm(claps) * 0.25
    return norm(reverb(y * shape, 1.8, 0.3))


def crowd_stomp(people=24, seed=19):
    """A crowd stomping in (almost) unison."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(0.7 * SR))
    for i in range(people):
        f = rng.uniform(70, 110)
        thud = sweep(f * 1.6, f * 0.6, 0.3) * env_exp(0.3, 0.06, 0.002)
        scuff = bandpass(noise(0.08, seed + i), 300, 2500) * env_exp(0.08, 0.02, 0.001) * 0.3
        out += place(mix(thud, scuff) * rng.uniform(0.6, 1.0), 0.02 + abs(rng.normal(0, 0.01)), 0.7)
    return norm(reverb(out, 1.2, 0.25))


def crowd_clap(people=30, seed=20):
    rng = np.random.default_rng(seed)
    out = np.zeros(int(0.5 * SR))
    for i in range(people):
        c = bandpass(noise(0.02, seed + 50 + i), rng.uniform(900, 1500), 6000) * env_exp(0.02, 0.005, 0.0002)
        out += place(c * rng.uniform(0.5, 1.0), 0.015 + abs(rng.normal(0, 0.009)), 0.5)
    return norm(reverb(out, 1.0, 0.3))


def card_flip(seed=21):
    """Paper card flipping over: a short rising swish and a snap."""
    d = 0.16
    w = moving_band(noise(d, seed), np.geomspace(800, 5000, 16), 0.5) * np.sin(np.pi * np.clip(t_axis(d) / d, 0, 1)) ** 0.7
    snap = bandpass(noise(0.02, seed + 1), 1500, 6000) * env_exp(0.02, 0.004, 0.0003)
    return norm(mix(w * 0.7, place(snap, 0.14, 0.2)))


def shepard(dur=6.0, period=3.0, f_center=440.0):
    """Endlessly rising Shepard tone for tension."""
    t = t_axis(dur)
    out = np.zeros_like(t)
    for k in range(8):
        pos = (k + t / period) % 8
        f = 27.5 * 2**pos
        amp = np.exp(-0.5 * ((np.log2(f) - np.log2(f_center)) / 1.4) ** 2)
        out += amp * np.sin(2 * np.pi * np.cumsum(f) / SR)
    return norm(out * np.clip(t / 0.5, 0, 1))


def cell_slam(seed=23):
    """Steel door slam for BLOCKED/DENIED: comb-filtered hit, clank partials, low thud."""
    L = 1.4
    hit = place(noise(0.05, seed) * env_exp(0.05, 0.01, 0.0003), 0, L)
    d = int(0.0047 * SR)
    a = np.zeros(d + 1)
    a[0], a[d] = 1.0, -0.86
    comb = signal.lfilter([1.0], a, hit) * 0.25
    tt = t_axis(L)
    clank = sum(np.sin(2 * np.pi * 180 * p * tt) * np.exp(-tt / (0.55 / p)) / (i + 1)
                for i, p in enumerate([1.0, 1.47, 2.09, 2.56, 3.3]))
    thud = place(sweep(120, 50, 0.4) * env_exp(0.4, 0.08, 0.001), 0, L)
    return norm(reverb(mix(comb, clank * 0.5, drive(thud * 1.4, 2)), 1.4, 0.25))


def alarm_morph():
    """Alarm clock rings, then pitch-dives (the siren takes over underneath)."""
    a = alarm_clock(1.5)
    head, tail = a[: int(1.0 * SR)], tapestop(a[int(1.0 * SR):], 0.6)
    return norm(np.concatenate([head, tail]))


def win_ding(seed=24):
    """Bright, short 'correct answer' bell for scoreboard wins."""
    t = t_axis(0.9)
    mod = np.sin(2 * np.pi * 1760 * 2.0 * t) * 2.5 * env_exp(0.9, 0.08)
    x = np.sin(2 * np.pi * 1760 * t + mod) * env_exp(0.9, 0.22, 0.001)
    x += np.sin(2 * np.pi * 2637 * t) * env_exp(0.9, 0.15, 0.001) * 0.4
    return norm(reverb(x, 0.8, 0.2))


# ---------- library export ----------

LIBRARY = {
    "impact": lambda: impact(0.0),
    "impact_mid": lambda: impact(0.5, seed=21),
    "impact_hot": lambda: impact(1.0, seed=31),
    "subdrop": subdrop,
    "whoosh_up": lambda: whoosh(0.7, True),
    "whoosh_down": lambda: whoosh(0.5, False, seed=22),
    "whoosh_fast": lambda: whoosh(0.3, True, seed=23),
    "stamp": stamp,
    "card_slap_a": lambda: card_slap(4, 1.0),
    "card_slap_b": lambda: card_slap(41, 1.15),
    "card_slap_c": lambda: card_slap(42, 0.9),
    "tick": tick,
    "spin": spin,
    "spin_long": lambda: spin(3.0, 8, 60, seed=24),
    "kachunk": kachunk,
    "register": register,
    "glitch": glitch,
    "glitch_b": lambda: glitch(seed=25, dur=0.35),
    "riser": riser,
    "heartbeat": heartbeat,
    "boom_tail": boom_tail,
    "static_wall": static_wall,
    "clock_tick": lambda: tick_tock(False),
    "clock_tock": lambda: tick_tock(True, seed=24),
    "alarm_clock": alarm_clock,
    "siren": lambda: air_raid_siren(7.0, wind_down_at=5.5),
    "crowd_roar": crowd_roar,
    "crowd_stomp": crowd_stomp,
    "crowd_clap": crowd_clap,
    "card_flip": card_flip,
    "shepard": shepard,
    "cell_slam": cell_slam,
    "alarm_morph": alarm_morph,
    "siren_long": lambda: air_raid_siren(9.0, wind_down_at=6.6),
    "crowd_swell": lambda: crowd_roar(7.5, swell=True),
    "crowd_tail": lambda: (lambda x: x * np.linspace(1, 0, len(x)))(crowd_roar(4.0, swell=False, seed=90)),
    "win_ding": win_ding,
}


def write(name, x, folder=SFX_DIR):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.wav"
    sf.write(path, stereo(x, 0.5).astype(np.float32), SR, subtype="PCM_24")
    return path


if __name__ == "__main__":
    for name, fn in LIBRARY.items():
        p = write(name, fn())
        print(f"{p.relative_to(ROOT)}  {sf.info(p).duration:.2f}s")
