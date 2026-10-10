"""Synthesized music bed. Aggressive ~135 BPM industrial/phonk loop, built per bar
so the video's beat grid and the music share one clock.

Usage: python scripts/music.py [arrangement.json] -> assets/audio/music/bed.wav
An arrangement is a list of {"section": name, "bars": n}. Sections: drone,
groove, drive, frenzy, silence, anthem.

Drums come from scripts/kits.py (KIT below; the user picks from the auditions made by
scripts/drum_audition.py). The 808 bass and drone are the same for every kit.
"""

import json
import sys

from sfx import *  # noqa: F401,F403  (shared primitives)
from kits import KITS, glue

KIT = "A"  # drum kit for the hero mix (see kits.py)

BPM = 135
BEAT = 60 / BPM
BAR = BEAT * 4
MUSIC_DIR = ROOT / "assets" / "audio" / "music"

# D minor riff for the 808, one note per eighth (None = rest)
D1, F1, G1, A1, Bb1, C2, D2 = 36.71, 43.65, 49.0, 55.0, 58.27, 65.41, 73.42
RIFF = [D1, None, D1, None, None, F1, None, D1, D1, None, None, Bb1, None, A1, None, None]
RIFF_B = [D1, None, D1, D2, None, C2, None, Bb1, D1, None, D1, None, A1, None, G1, F1]


def bass808(freq, dur, slide_from=None):
    t = t_axis(dur)
    f = np.full_like(t, freq)
    if slide_from:
        f = freq + (slide_from - freq) * np.exp(-t / 0.05)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(dur, dur * 0.8, 0.003)
    return drive(x, 3.0)


def drone(dur, seed=0):
    t = t_axis(dur)
    x = (np.sin(2 * np.pi * D1 * t) + 0.5 * np.sin(2 * np.pi * D1 * 1.498 * t)
         + 0.3 * lowpass(noise(dur, seed), 200))
    return drive(x * 0.6, 1.5)


def bar(section, idx, seed=0, kit=None):
    k_ = KITS[kit or KIT]
    kick, clap, hat, cowbell = k_["kick"], k_["snare"], k_["hat"], k_["perc"]
    hg = k_.get("hat_gain", 1.0)
    L = BAR + 2.0  # extra tail (reverbs); overlap-added
    drums = np.zeros(int(L * SR))
    bass = np.zeros(int(L * SR))
    e = BEAT / 2   # eighth
    s = BEAT / 4   # sixteenth
    riff = RIFF_B if idx % 2 else RIFF

    def add(x, at, g=1.0, bus=None):
        b = drums if bus is None else bus
        b += place(x * g, at, L)

    def out():
        d = glue(drums, **k_["glue"]) if k_.get("glue") else drums
        return d * 10 ** (k_.get("level", 0.0) / 20) + bass

    if section == "silence":
        return out()
    if section == "drone":
        add(drone(BAR, seed + idx) * 0.5, 0, bus=bass)
        add(kick(seed, 0.6) * 0.8, 0)
        return out()
    if section in ("groove", "drive", "frenzy"):
        kicks = [0, 3 * e, 4 * e + s * 2] if section == "groove" else [0, 3 * e, 5 * e, 6 * e + s * 2]
        if section == "frenzy":
            kicks = [i * e for i in range(8)]
        for k in kicks:
            add(kick(seed + idx, 1.0 if section != "groove" else 0.8), k)
        for b in (1, 3):
            add(clap(seed + idx * 7 + b), b * BEAT, 0.8)
        step = s if section != "groove" and not k_.get("hats_8ths") else e
        n = int(BAR / step)
        for i in range(n):
            add(hat(seed + i, open_=(section != "groove" and i % 8 == 6)), i * step, hg * (0.25 if i % 2 else 0.35))
        if section in ("drive", "frenzy"):
            for i in (2, 7, 10, 13):
                add(cowbell(seed + i), i * s, 0.5)
        for i, f in enumerate(riff):
            if f:
                nxt = next((j for j in range(i + 1, len(riff)) if riff[j]), len(riff))
                add(bass808(f, (nxt - i) * e * 0.95, slide_from=f * 1.5 if i == 0 else None), i * e, 0.7, bus=bass)
        return out()
    if section == "anthem":
        for b in range(4):
            add(kick(seed + b, 1.3), b * BEAT, 1.1)
            add(bass808(D1, BEAT * 0.9), b * BEAT, 0.8, bus=bass)
        for b in (1, 3):
            add(clap(seed + b), b * BEAT, 0.9)
        add(drone(BAR, seed + idx) * 0.35, 0, bus=bass)
        return out()
    raise ValueError(section)


def render(arrangement, seed=0, kit=None):
    total_bars = sum(a["bars"] for a in arrangement)
    out = np.zeros(int((total_bars * BAR + 3) * SR))
    i_bar = 0
    for a in arrangement:
        for k in range(a["bars"]):
            b = bar(a["section"], k, seed, kit)
            start = int(i_bar * BAR * SR)
            n = min(len(b), len(out) - start)
            out[start : start + n] += b[:n]
            i_bar += 1
    return norm(drive(out * 0.9, 1.2), 0.9)


DEMO = [
    {"section": "drone", "bars": 2},
    {"section": "groove", "bars": 4},
    {"section": "drive", "bars": 4},
    {"section": "frenzy", "bars": 2},
    {"section": "silence", "bars": 1},
    {"section": "anthem", "bars": 4},
]

if __name__ == "__main__":
    arr = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else DEMO
    y = render(arr)
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    name = "bed.wav" if len(sys.argv) > 1 else "demo.wav"
    sf.write(MUSIC_DIR / name, stereo(y, 0.3).astype(np.float32), SR, subtype="PCM_24")
    print(f"{name}: {len(y) / SR:.1f}s at {BPM} BPM, bar={BAR:.4f}s")
