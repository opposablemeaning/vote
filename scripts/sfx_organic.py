"""Organic, physical sound design library for VOTE. THEM. OUT.

Replaces mathematical sine sweeps and uniform white-noise bursts with:
- Real acoustic CC0 material (TR-808 clave/rim, acoustic drums, cello body knocks)
- Multi-layer physical transient modeling
- Pink noise air-displacement for organic whooshes
- True stereo room reflections and tube saturation
"""

from functools import lru_cache
from pathlib import Path
import numpy as np
import scipy.signal as sps
import soundfile as sf

SR = 48_000
ROOT = Path(__file__).resolve().parent.parent
CC0_DIR = ROOT / "assets" / "audio" / "cc0"
TR808 = CC0_DIR / "tr808"
DRUMS = CC0_DIR / "drums"
CELLO_PLUCK = Path.home() / "tidal" / "samples" / "clean" / "samples-cello-plucked"

from sfx import (
    LIBRARY as ORIGINAL_LIBRARY,
    air_raid_siren,
    alarm_clock,
    alarm_morph,
    bandpass,
    cell_slam as orig_cell_slam,
    drive,
    env_exp,
    glitch,
    highpass,
    lowpass,
    mix,
    moving_band,
    norm,
    pad_to,
    place,
    reverb,
    riser as orig_riser,
    shepard,
    static_wall,
    stereo,
    sweep,
    t_axis,
    win_ding,
)


@lru_cache(maxsize=32)
def load_sample(path, dur=None):
    p = Path(path)
    if not p.exists():
        return np.zeros(100)
    x, sr = sf.read(p)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != SR:
        x = sps.resample_poly(x, SR, sr)
    idx = np.argmax(np.abs(x) > 0.05 * np.max(np.abs(x)))
    x = x[max(0, idx - 16):]
    if dur is not None:
        x = x[: int(dur * SR)]
    m = np.max(np.abs(x))
    return x / m if m > 0 else x


def pink_noise(dur, seed=0):
    rng = np.random.default_rng(seed)
    w = rng.uniform(-1, 1, int(dur * SR))
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1.0, -2.494956002, 2.017265875, -0.522189400]
    return sps.lfilter(b, a, w)


# ==============================================================================
# UPGRADED ORGANIC SOUND DESIGN
# ==============================================================================

def card_slap_organic(seed=4, pitch=1.0):
    """Option 1B: Muted mid-tom percussion tap (warm, round, low-mid thud)."""
    tom = load_sample(DRUMS / "Mid_Tom_1.wav", dur=0.15)
    if pitch != 1.0:
        tom = sps.resample(tom, int(len(tom) / pitch))
    filtered = bandpass(tom, 160, 950)
    t = np.linspace(0, len(filtered) / SR, len(filtered), endpoint=False)
    env = np.exp(-t / 0.08)
    x = reverb(filtered * env, size=0.4, wet=0.14)
    return norm(x, peak=0.92)


def stamp_organic(seed=3):
    """Stamp 3A: Tight acoustic kick + heavy cross-stick stomp (authoritative drum hit)."""
    k = load_sample(DRUMS / "Kick_4.wav", dur=0.25)
    rs = load_sample(TR808 / "RS.wav", dur=0.08) * 1.2
    w = load_sample(CELLO_PLUCK / "11_body_high.wav", dur=0.08) * 1.0
    x = mix(k * 1.1, rs, w)
    return norm(reverb(x, size=0.4, wet=0.16), peak=0.94)


def impact_organic(escalate=0.0, seed=1):
    """Hard-hitting cinematic impact: acoustic kick beater whack + heavy cello knock + sub-boom."""
    dur = 2.2
    # 1. Acoustic beater attack (Kick_4 full punch: 150 - 3400 Hz, crisp and hard-hitting)
    kick_raw = load_sample(DRUMS / "Kick_4.wav", dur=0.45)
    beater = bandpass(kick_raw, 120, 3400) * (1.3 + 0.3 * escalate)

    # 2. Heavy instrument / desk body knock
    knock_raw = load_sample(CELLO_PLUCK / "10_body_low.wav", dur=0.35)
    knock = bandpass(knock_raw, 90, 650) * 1.2

    # 3. Metallic anvil bite on hot impacts
    clank = np.zeros(int(0.35 * SR))
    if escalate > 0.2:
        bell_raw = load_sample(DRUMS / "Cymbal_Centre_Bell.wav", dur=0.35)
        clank = bandpass(bell_raw, 800, 4500) * env_exp(0.35, 0.08, 0.001) * (0.7 * escalate)

    # 4. Massive cinematic sub-boom (60 Hz -> 28 Hz)
    sub = sweep(60 + 18 * escalate, 28, dur) * env_exp(dur, 0.9, 0.002) * 1.35

    x = mix(beater, knock, clank, sub)
    driven = drive(x * 2.0, 2.7 + 0.6 * escalate)
    wet = reverb(driven, size=1.5 + 0.4 * escalate, wet=0.22 + 0.08 * escalate)
    return norm(wet, peak=0.99)


def whoosh_organic(dur=0.6, rising=True, seed=2):
    """Natural air displacement: pink-noise turbulence + sub-air pressure rush."""
    t = t_axis(dur)
    p = pink_noise(dur, seed)
    c = np.geomspace(250, 4500, 32) if rising else np.geomspace(4500, 250, 32)
    air = moving_band(p, c, 0.55)
    # Sub-bass air pressure rush
    sub_f = 65 if rising else 85
    sub_rush = np.sin(2 * np.pi * sub_f * t) * env_exp(dur, dur * 0.6, 0.01) * 0.35
    shape = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** (0.7 if rising else 1.2)
    return norm(mix(air * shape, sub_rush * shape), peak=0.9)


def kachunk_organic(seed=8):
    """Slot reel locks: physical relay clicks, acoustic body thump, and iron latch ping."""
    c1 = load_sample(TR808 / "CL.wav", dur=0.06) * 0.75
    c2 = load_sample(TR808 / "RS.wav", dur=0.08) * 0.85
    thump = load_sample(CELLO_PLUCK / "10_body_low.wav", dur=0.25) * 0.95
    # Metallic latch ping
    bell = load_sample(DRUMS / "Cymbal_Centre_Bell.wav", dur=0.5) * 0.4
    x = mix(place(c1, 0, 0.8), place(c2, 0.045, 0.8), place(thump, 0.05, 0.8), place(bell, 0.06, 0.8))
    return norm(reverb(drive(x, 1.5), size=0.6, wet=0.14), peak=0.94)


def heartbeat_organic(seed=12):
    """Organic human heartbeat with real chest acoustic resonance."""
    dur = 0.9
    t = t_axis(0.35)
    # Lub (mitral valve, 58 Hz)
    f_lub = 58 * np.exp(-t / 0.04)
    lub = np.sin(2 * np.pi * np.cumsum(f_lub) / SR) * env_exp(0.35, 0.09, 0.004)
    # Dub (aortic valve, 46 Hz)
    t2 = t_axis(0.3)
    f_dub = 46 * np.exp(-t2 / 0.035)
    dub = np.sin(2 * np.pi * np.cumsum(f_dub) / SR) * env_exp(0.3, 0.07, 0.003) * 0.75
    x = mix(place(lub, 0, dur), place(dub, 0.22, dur))
    return norm(lowpass(drive(x * 1.3, 1.8), 280), peak=0.92)


def subdrop_organic(dur=2.2):
    """Warm, cinematic sub-drop that glides through phone-audible 120-60 Hz range."""
    t = t_axis(dur)
    f_glide = 115 * np.exp(-t / 0.6) + 28
    sig = np.sin(2 * np.pi * np.cumsum(f_glide) / SR)
    env = env_exp(dur, dur / 2.2, 0.005)
    return norm(drive(sig * env * 1.5, 2.2), peak=0.95)


def cell_slam_organic(seed=17):
    """Prison cell door slam: heavy iron impact, acoustic latch rattle, hall resonance."""
    iron = load_sample(DRUMS / "Snare_1.wav", dur=0.3) * 0.8
    thud = load_sample(CELLO_PLUCK / "10_body_low.wav", dur=0.4) * 1.1
    sub = sweep(75, 32, 1.2) * env_exp(1.2, 0.5, 0.002) * 0.8
    x = mix(iron, thud, sub)
    return norm(reverb(drive(x, 2.2), size=1.8, wet=0.35), peak=0.96)


def card_flip_organic(seed=21):
    """Flip 2B: 1-Beat Tom Fill (tight 3-stroke tom roll leading into the reveal)."""
    dur = 0.444
    t1 = load_sample(DRUMS / "High_Tom_1.wav", dur=0.12) * 0.8
    t2 = load_sample(DRUMS / "Mid_Tom_1.wav", dur=0.12) * 0.9
    t3 = load_sample(DRUMS / "Low_Tom_1.wav", dur=0.18) * 1.0
    out = np.zeros(int(dur * SR))
    i1 = 0
    i2 = int(0.12 * SR)
    i3 = int(0.24 * SR)
    out[i1 : i1 + len(t1)] += t1
    out[i2 : i2 + len(t2)] += t2
    out[i3 : i3 + len(t3)] += t3
    return norm(reverb(out, size=0.4, wet=0.18), peak=0.92)


def clock_tick_tock_organic(tock=False, seed=15):
    """Mechanical clock escapement: real tactile click + wooden clock housing resonance."""
    p = 0.78 if tock else 1.0
    # Escapement click
    cl_raw = load_sample(TR808 / "CL.wav", dur=0.035)
    click = bandpass(cl_raw, int(1600 * p), 6500) * 0.8
    # Wooden case acoustic resonance
    body_raw = load_sample(CELLO_PLUCK / "10_body_low.wav", dur=0.1)
    body = bandpass(body_raw, int(180 * p), int(550 * p)) * env_exp(0.1, 0.02, 0.001) * 0.45
    x = mix(click, body)
    return norm(x, peak=0.88)


def spin_chunky(dur=0.44, start_rate=14, end_rate=42, seed=6):
    """Chunky mechanical ratchet gear clicks. Exact duration, cuts off dead at the landing hit!"""
    rs_raw = load_sample(DRUMS / "Snare_Rimshot_1.wav", dur=0.025)
    click_sample = bandpass(rs_raw, 400, 1900)
    body_raw = load_sample(CELLO_PLUCK / "10_body_low.wav", dur=0.03)
    cog = bandpass(body_raw, 250, 700) * 0.6
    tooth = mix(click_sample, cog)

    out = np.zeros(int(dur * SR))
    t, k = 0.0, 0
    rng = np.random.default_rng(seed)
    while t < dur - 0.015:  # stop 15ms before the end so it never bleeds into the landing hit
        rate = start_rate + (end_rate - start_rate) * (t / dur)
        pitch = 0.85 + 0.06 * (k % 4)
        c = sps.resample(tooth, int(len(tooth) / pitch)) if pitch != 1.0 else tooth
        c = c * (0.7 + 0.2 * rng.uniform())
        out += place(c, t, dur)
        t += 1.0 / rate
        k += 1

    fade_len = int(0.008 * SR)
    out[-fade_len:] *= np.linspace(1, 0, fade_len)
    return norm(out, peak=0.90)


def spin_organic(dur=0.44, seed=6):
    """1-beat ticker spin (0.44s): chunky mechanical teeth, cuts off dead on the slam."""
    return spin_chunky(dur=dur, start_rate=14, end_rate=42, seed=seed)


def spin_reels_organic(dur=0.88, seed=8):
    """2-beat finale slot reels (0.88s): stops dead right as 'VOTE.' lands."""
    return spin_chunky(dur=dur, start_rate=12, end_rate=36, seed=seed)


def spin_long_organic(dur=3.55, seed=24):
    """Overload frenzy spin (3.55s): stops dead right as 'ALL OF THE ABOVE.' lands."""
    return spin_chunky(dur=dur, start_rate=10, end_rate=50, seed=seed)


def crowd_stomp_organic(people=20, seed=19):
    """Acoustic boots on concrete: real drum body + cello knocks in stereo space."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(0.75 * SR))
    kick_raw = load_sample(DRUMS / "Kick_7.wav", dur=0.25)
    body_raw = load_sample(CELLO_PLUCK / "10_body_low.wav", dur=0.25)
    for i in range(people):
        thud = lowpass(kick_raw, rng.uniform(220, 380)) * rng.uniform(0.6, 1.0)
        knock = bandpass(body_raw, rng.uniform(110, 180), rng.uniform(350, 600)) * 0.7
        combined = mix(thud, knock)
        delay = 0.015 + abs(rng.normal(0, 0.012))
        out += place(combined, delay, 0.75)
    return norm(reverb(drive(out, 1.4), size=1.2, wet=0.28), peak=0.95)


def crowd_clap_organic(people=24, seed=20):
    """Stereo crowd claps: real 808 clap transients + acoustic rim reflections."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(0.6 * SR))
    cp_raw = load_sample(TR808 / "CP.wav", dur=0.15)
    rs_raw = load_sample(TR808 / "RS.wav", dur=0.08)
    for i in range(people):
        c = bandpass(cp_raw, rng.uniform(900, 1400), rng.uniform(5000, 7500)) * rng.uniform(0.5, 0.9)
        rim = bandpass(rs_raw, 1200, 6000) * rng.uniform(0.2, 0.5)
        delay = 0.01 + abs(rng.normal(0, 0.01))
        out += place(mix(c, rim), delay, 0.6)
    return norm(reverb(out, 0.9, 0.25), peak=0.92)


def win_ding_organic(seed=24):
    """Physical brass bell chime for scoreboard wins."""
    bell_raw = load_sample(DRUMS / "Cymbal_Centre_Bell.wav", dur=1.2)
    ding = highpass(bell_raw, 1750) * env_exp(1.2, 0.35, 0.001)
    # Add subtle octave overtone
    t = t_axis(0.8)
    shimmer = np.sin(2 * np.pi * 3520 * t) * env_exp(0.8, 0.18, 0.001) * 0.2
    x = mix(ding, shimmer)
    return norm(reverb(x, 0.8, 0.18), peak=0.92)


# ==============================================================================
# UPGRADED LIBRARY MAPPING
# ==============================================================================

ORGANIC_LIBRARY = dict(ORIGINAL_LIBRARY)
ORGANIC_LIBRARY.update({
    "impact": lambda: impact_organic(0.0),
    "impact_mid": lambda: impact_organic(0.5, seed=21),
    "impact_hot": lambda: impact_organic(1.0, seed=31),
    "subdrop": subdrop_organic,
    "whoosh_up": lambda: whoosh_organic(0.7, True),
    "whoosh_down": lambda: whoosh_organic(0.5, False, seed=22),
    "whoosh_fast": lambda: whoosh_organic(0.3, True, seed=23),
    "stamp": stamp_organic,
    "card_slap_a": lambda: card_slap_organic(4, 1.0),
    "card_slap_b": lambda: card_slap_organic(41, 1.12),
    "card_slap_c": lambda: card_slap_organic(42, 0.92),
    "tick": lambda: load_sample(TR808 / "CL.wav", dur=0.03) * 0.7,
    "kachunk": kachunk_organic,
    "heartbeat": heartbeat_organic,
    "cell_slam": cell_slam_organic,
    "card_flip": card_flip_organic,
    "clock_tick": lambda: clock_tick_tock_organic(False),
    "clock_tock": lambda: clock_tick_tock_organic(True, seed=24),
    "spin": lambda: spin_organic(0.44),
    "spin_long": lambda: spin_long_organic(3.55, seed=24),
    "spin_reels": lambda: spin_reels_organic(0.88, seed=8),
    "crowd_stomp": crowd_stomp_organic,
    "crowd_clap": crowd_clap_organic,
    "win_ding": win_ding_organic,
})

