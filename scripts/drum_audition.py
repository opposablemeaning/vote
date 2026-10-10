"""Drum-kit auditions: the same groove + 808 bass with each kit in kits.py.

  python scripts/drum_audition.py  ->  assets/audio/auditions/drums-<K>-<name>.wav
                                       assets/audio/auditions/drums-all.wav (A..F, 1.5 s gaps)

Each clip is 2 bars of `groove` then 4 bars of `drive`, with one headline hit (impact_mid)
on bar 5 so the kit can be judged under the hits. Clips are loudness-matched (K-weighted,
like YouTube's normalization), since louder always sounds better in an A/B.
"""

import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent))
from sfx import LIBRARY, ROOT, SR, place  # noqa: E402
import music  # noqa: E402
from kits import KITS  # noqa: E402

NAMES = {"A": "current", "B": "punchy", "C": "industrial", "D": "taiko", "E": "acoustic", "F": "tr808"}
OUT = ROOT / "assets" / "audio" / "auditions"
ARR = [{"section": "groove", "bars": 2}, {"section": "drive", "bars": 4}]


def clip(kit):
    n_bars = sum(a["bars"] for a in ARR)
    dur = n_bars * music.BAR + 0.6
    bed = music.render(ARR, kit=kit)[: int(dur * SR)]
    hit = place(LIBRARY["impact_mid"]() * 0.85, 4 * music.BAR, dur)
    x = bed * 0.55 + hit * 0.6
    f = int(0.4 * SR)
    x[-f:] *= np.linspace(1, 0, f)
    x *= 10 ** ((-16 - lufs(x)) / 20)  # same loudness for every kit (what YouTube normalizes to)
    return np.tanh(x * 1.1) * 0.95


def lufs(x):
    """Ungated BS.1770 loudness (K-weighting at 48 kHz): good enough for an A/B."""
    y = signal.lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585], x)
    y = signal.lfilter([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621], y)
    return -0.691 + 10 * np.log10(np.mean(y**2) + 1e-12)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    gap = np.zeros(int(1.5 * SR))
    allx, t = [], 0.0
    for k in KITS:
        x = clip(k)
        sf.write(OUT / f"drums-{k}-{NAMES[k]}.wav", np.stack([x, x], 1).astype(np.float32), SR, subtype="PCM_24")
        print(f"  {k} {NAMES[k]:11s} starts at {int(t // 60)}:{t % 60:04.1f} in drums-all.wav")
        allx += [x, gap]
        t += (len(x) + len(gap)) / SR
    y = np.concatenate(allx)
    sf.write(OUT / "drums-all.wav", np.stack([y, y], 1).astype(np.float32), SR, subtype="PCM_24")
    print(f"drums-all.wav: {len(y) / SR:.1f}s -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
