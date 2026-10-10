"""Mix the hero soundtrack from data/hero.cues.json -> hero/assets/audio/mix.wav.

cues.json:
  duration          total seconds
  music: [{at, section, until, gain}]   music.py sections placed on the shared beat grid
  cues:  [{t, sfx, gain}]               synthesized SFX from sfx.LIBRARY
         [{t, clip, gain}]              optional voice clips (skipped with a warning if missing)
            clip options: from, dur, fade (s); duck: true | false | 0..1 (scales how hard
            music/SFX duck under it); eq: "presence" (crowd chants: cut mud, lift 1.5-4 kHz);
            carve: 0..1 cuts the 1-4 kHz speech band out of music + SFX while the clip plays
  silence: [[t0, t1], ...]              windows of true digital silence; whatever is ringing at t0
         [[t0, t1, fade_out, fade_in]]  fades out over fade_out (default 0.12s) instead of
                                        being cut mid-tail, and t1 fades back in (default 0.01s)

Music ducks under big hits and under voice clips so both cut through on phone speakers.
"""

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal as sps

sys.path.insert(0, str(Path(__file__).parent))
from sfx import LIBRARY, ROOT, SR, bandpass, highpass, place  # noqa: E402
import music  # noqa: E402

STEMS = "--stems" in sys.argv
DUCKERS = {"impact", "impact_mid", "impact_hot", "kachunk", "boom_tail", "subdrop", "cell_slam"}


def presence(x):
    """Make a chant read through a dense mix: cut rumble, lift the consonant band, even it out."""
    x = highpass(x, 180)
    x = x + 0.9 * bandpass(x, 1500, 4000)
    return np.tanh(2.0 * x / max(1e-9, np.max(np.abs(x))))


def load_clip(path, start=0.0, dur=None, fade=0.25, eq=None, fade_out=None):
    cands = [Path(path)] if Path(path).is_absolute() else [ROOT / path, ROOT / "hero" / path]
    p = next((c for c in cands if c.exists()), None)
    if p is None:
        print(f"  ! clip missing, skipped: {path}")
        return None
    x, sr = sf.read(p, always_2d=True)
    x = x.mean(axis=1)
    if sr != SR:
        x = sps.resample_poly(x, SR, sr)
    x = x[int(start * SR):]
    if dur is not None:
        x = x[: int(dur * SR)]
    if eq == "presence":
        x = presence(x)
    f = min(int(fade * SR), len(x) // 2)
    fo = min(int((fade if fade_out is None else fade_out) * SR), len(x) // 2)
    if f > 0:
        x[:f] *= np.linspace(0, 1, f)
    if fo > 0:
        x[-fo:] *= np.linspace(1, 0, fo)
    return x / max(1e-9, np.max(np.abs(x)))


def duck_env(n, events, depth, attack_s, hold_s, release_s):
    env = np.ones(n)
    for ev in events:
        t0, length = ev[0], ev[1]
        d = depth * (ev[2] if len(ev) > 2 else 1.0)
        i0 = int(t0 * SR)
        a, h, r = int(attack_s * SR), int((hold_s + length) * SR), int(release_s * SR)
        shape = np.concatenate([np.linspace(1, 1 - d, a), np.full(h, 1 - d), np.linspace(1 - d, 1, r)])
        i0 = max(0, i0 - a)
        j = min(n, i0 + len(shape))
        env[i0:j] = np.minimum(env[i0:j], shape[: j - i0])
    return env


def silence_env(n, windows):
    """Gain envelope for silence windows: a short fade into each one, so a tail that is
    still ringing at t0 decays to zero instead of being chopped (an audible click/catch)."""
    env = np.ones(n)
    for w in windows:
        t0, t1 = w[0], w[1]
        fo = w[2] if len(w) > 2 else 0.12
        fi = w[3] if len(w) > 3 else 0.01
        i0, i1 = int(t0 * SR), int(t1 * SR)
        a = min(int(fo * SR), max(0, i1 - i0))
        env[i0 : i0 + a] = np.minimum(env[i0 : i0 + a], np.cos(np.linspace(0, np.pi / 2, a)) ** 2)
        env[i0 + a : i1] = 0.0
        b = min(int(fi * SR), n - i1)
        if b > 0:
            env[i1 : i1 + b] = np.minimum(env[i1 : i1 + b], np.sin(np.linspace(0, np.pi / 2, b)) ** 2)
    return env


def main(cue_path=ROOT / "data" / "hero.cues.json", out=ROOT / "hero" / "assets" / "audio" / "mix.wav"):
    c = json.loads(Path(cue_path).read_text())
    dur = c["duration"]
    n = int(dur * SR)

    bed = np.zeros(n)
    for seg in c.get("music", []):
        length = seg["until"] - seg["at"]
        bars = max(1, int(np.ceil(length / music.BAR)))
        x = music.render([{"section": seg["section"], "bars": bars}])[: int((length + 0.03) * SR)]
        fade = int(0.03 * SR)
        if len(x) > fade:
            x[-fade:] *= np.linspace(1, 0, fade)
        bed += place(x * seg.get("gain", 1.0), seg["at"], dur)

    sfx_bus = np.zeros(n)
    voice_bus = np.zeros(n)
    cache, hits, voices, carves = {}, [], [], []
    for q in c["cues"]:
        if "clip" in q:
            x = load_clip(q["clip"], q.get("from", 0.0), q.get("dur"), q.get("fade", 0.02), q.get("eq"), q.get("fade_out"))
            if x is not None:
                voice_bus += place(x * q.get("gain", 1.0), q["t"], dur)
                dk = q.get("duck", True)
                if dk:
                    voices.append((q["t"], len(x) / SR, 1.0 if dk is True else float(dk)))
                if q.get("carve"):
                    carves.append((q["t"], len(x) / SR, float(q["carve"])))
            continue
        name = q["sfx"]
        if name not in cache:
            cache[name] = LIBRARY[name]()
        sfx_bus += place(cache[name] * q.get("gain", 1.0), q["t"], dur)
        if name in DUCKERS:
            hits.append((q["t"], 0.0))

    if carves:
        # make room for the words: zero-phase band cut, so subtracting it is a clean notch
        sos = sps.butter(2, [1000, 4000], btype="band", fs=SR, output="sos")
        cut = 1.0 - duck_env(n, carves, 1.0, 0.08, 0.0, 0.3)
        bed = bed - cut * sps.sosfiltfilt(sos, bed)
        sfx_bus = sfx_bus - cut * sps.sosfiltfilt(sos, sfx_bus)
    duck = duck_env(n, hits, 0.6, 0.005, 0.0, 0.3) * duck_env(n, voices, 0.75, 0.08, 0.05, 0.4)
    sfx_duck = duck_env(n, voices, 0.5, 0.08, 0.05, 0.4)
    m = bed * 0.55 * duck + sfx_bus * 0.6 * sfx_duck + voice_bus * 0.95
    if STEMS:
        # separate music / sfx / voice tracks (same gain staging as the mix) for review or a producer
        stem_dir = out.parent / "stems"
        stem_dir.mkdir(parents=True, exist_ok=True)
        for name, x in (("music", bed * 0.55 * duck), ("sfx", sfx_bus * 0.6 * sfx_duck), ("voice", voice_bus * 0.95)):
            sf.write(stem_dir / f"{name}.wav", np.stack([x, x], axis=1).astype(np.float32), SR, subtype="PCM_24")

    m *= silence_env(n, c.get("silence", []))
    m = np.tanh(m * 1.1)
    m = m / max(1e-9, np.max(np.abs(m))) * 0.89
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out, np.stack([m, m], axis=1).astype(np.float32), SR, subtype="PCM_24")
    print(f"mix: {dur:.2f}s -> {out.relative_to(ROOT)} ({len(c['cues'])} cues, {len(c.get('music', []))} music segments)")


if __name__ == "__main__":
    main(*[Path(a).resolve() for a in sys.argv[1:3] if not a.startswith("--")])
