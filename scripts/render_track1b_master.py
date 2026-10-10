"""Master render and mix pipeline for Track 1B (Industrial Power-Chug) with Organic SFX.

Produces:
1. out/for-review/hero-track1b-new-sfx-full-mix.mp3 (Master mix)
2. out/for-review/hero-track1b-new-sfx-music-only.mp3 (Music bed alone)
3. out/for-review/hero-track1b-new-sfx-only.mp3 (SFX track alone across the 2:14 timeline)
4. out/for-review/hero-v3-track1b-new-sfx-720p.mp4 (Complete 720p video mux)
5. Updates hero/assets/audio/mix.wav and hero/assets/audio/stems/ for Hyperframes
"""

import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import scipy.signal as sps
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
import track_engines as te
from sfx_organic import ORGANIC_LIBRARY as LIBRARY, ROOT, SR
from mix import duck_env, load_clip, silence_env

DUCKERS = {"impact", "impact_mid", "impact_hot", "kachunk", "boom_tail", "subdrop", "cell_slam"}

REV_DIR = ROOT / "out" / "for-review"
REV_DIR.mkdir(parents=True, exist_ok=True)
HERO_AUDIO = ROOT / "hero" / "assets" / "audio"
HERO_AUDIO.mkdir(parents=True, exist_ok=True)
STEMS_DIR = HERO_AUDIO / "stems"
STEMS_DIR.mkdir(parents=True, exist_ok=True)

place = te.place
BAR = te.BAR
BEAT = te.BEAT
E = te.E
S = te.S
NOTES = te.NOTES


def powerchug_guitar(freq, dur=0.22):
    t = te.t_axis(dur)
    sig = (te.saw_osc(freq, dur) + te.saw_osc(freq * 1.498, dur) + te.saw_osc(freq * 2.0, dur)) / 3.0
    driven = te.soft_saturate(sig * 3.5, 4.0)
    cab = te.bandpass(driven, 120, 3400, order=3)
    env = te.env_exp(dur, 0.12, 0.002)
    return te.stereo_spread(cab * env * 1.05, width=0.35)


def render_industrial_1b_bar(section, idx, seed=0):
    dur = BAR + 0.6
    out = np.zeros((int(dur * SR), 2))
    riff_notes = [NOTES["D2"], NOTES["D2"], NOTES["D2"], NOTES["F2"],
                  NOTES["G2"], NOTES["D2"], NOTES["Bb2"], NOTES["A2"]]

    # 1. DRONE (Cold open, confessions hold, clock tension); OUTRO = the same bed under the end card
    if section in ("drone", "outro"):
        t = te.t_axis(BAR)
        sub = np.sin(2 * np.pi * NOTES["D1"] * t) * te.env_exp(BAR, BAR * 0.9, 0.005)
        # Fade out sub drone near end of bar 1 (1:52.5-1:53.3) for smooth silence entry
        if idx == 1 and section == "drone":
            fade_samples = int(0.6 * SR)
            fade_env = np.ones(len(sub))
            fade_env[-fade_samples:] = np.linspace(1.0, 0.0, fade_samples)
            sub = sub * fade_env
        out += place(te.stereo_spread(te.soft_saturate(sub * 1.5, 2.0) * 0.7, width=0.2), 0, dur)

        # Smooth 1:49.8 -> 1:50 transition: let anthem power chord ring out over beat 0
        if idx == 0:
            decay_tail = powerchug_guitar(NOTES["D2"], dur=1.5)
            env = te.env_exp(len(decay_tail) / SR, 0.6)[:, None]
            decay_tail = decay_tail * env
            out += place(decay_tail * 0.85, 0, dur)

        # Subtle 8th clockwork ticks (leave last tick in bar 1 alone in clear air)
        for i in range(8):
            vol = 0.25 if (idx == 0 or i < 6) else 0.15
            out += place(te.clock_tick_sound(seed=seed + i) * vol, i * E, dur)

    # 2. GROOVE (Act 1 entry, bridge transitions)
    elif section == "groove":
        for b in (0, 2):
            out += place(te.stereo_spread(te.kick_ind(hard=1.0, seed=seed + b)), b * BEAT, dur)
        for b in (1, 3):
            out += place(te.snare_ind(seed=seed + b) * 0.85, b * BEAT, dur)
        for i in range(8):
            out += place(te.stereo_spread(te.hat_ind(velocity=0.55 if i % 2 else 0.8, seed=seed + i)), i * E, dur)
        for i, n in enumerate(riff_notes):
            b = te.reese_ind(n, E * 0.92, cutoff=550)
            out += place(te.stereo_spread(b, width=0.25) * 0.8, i * E, dur)

    # 3. DRIVE (Act 1 receipts: hypnotic, steady, clean; never overstimulating)
    elif section == "drive":
        for k in (0, 1.5, 2.0, 3.5):
            out += place(te.stereo_spread(te.kick_ind(hard=1.1, seed=seed + int(k))), k * BEAT, dur)
        for b in (1, 3):
            out += place(te.snare_ind(seed=seed + b) * 0.9, b * BEAT, dur)
        for i in range(16):
            open_ = (i % 4 == 2)
            out += place(te.stereo_spread(te.hat_ind(open_=open_, velocity=0.45 if i % 2 else 0.8, seed=seed + i)), i * S, dur)
        cutoff = 600 + min(200, (idx % 8) * 25)
        for i, n in enumerate(riff_notes):
            b = te.reese_ind(n, E * 0.92, cutoff=cutoff)
            out += place(te.stereo_spread(b, width=0.3) * 0.82, i * E, dur)
        arp_scale = [NOTES["D3"], NOTES["F3"], NOTES["A3"], NOTES["C4"], NOTES["Bb3"], NOTES["A3"], NOTES["F3"], NOTES["D3"]]
        for i in range(16):
            out += place(te.stereo_spread(te.arp_ind(arp_scale[i % 8]), width=0.35) * 0.45, i * S, dur)
        if idx % 4 == 0:
            out += place(powerchug_guitar(NOTES["D2"], dur=E * 1.2) * 0.8, 0, dur)

    # 4. FRENZY (0:55-0:59 Overload, 29 cards flood screen)
    elif section == "frenzy":
        for i in range(8):
            out += place(te.stereo_spread(te.kick_ind(hard=1.25, seed=seed + i) * (0.8 + 0.4 * (i / 8.0))), i * E, dur)
        for i in range(16):
            out += place(te.snare_ind(seed=seed + i) * (0.6 + 0.35 * (i / 16.0)), i * S, dur)
        for i, n in enumerate(riff_notes):
            b = te.reese_ind(n, E * 0.92, cutoff=1400, drive_amt=3.8)
            out += place(te.stereo_spread(b, width=0.35) * 0.95, i * E, dur)
        out += place(te.braam_ind(NOTES["D1"], dur=BAR) * 0.85, 0, dur)

    # 5. ANTHEM (Scoreboard, Lift, 1:55 Finale "No kings!" map ignition)
    elif section == "anthem":
        for b in range(4):
            out += place(te.stereo_spread(te.kick_ind(hard=1.35, seed=seed + b) * 1.15), b * BEAT, dur)
        for b in (1, 3):
            out += place(te.snare_ind(seed=seed + b) * 1.1, b * BEAT, dur)
        for i in range(16):
            out += place(te.stereo_spread(te.hat_ind(open_=(i % 4 == 2), velocity=0.85, seed=seed + i)), i * S, dur)
        prog = [NOTES["Bb2"], NOTES["Bb2"], NOTES["C3"], NOTES["C3"], NOTES["D2"], NOTES["D2"], NOTES["D2"], NOTES["D2"]]
        for i, n in enumerate(prog):
            b = te.reese_ind(n, E * 0.92, cutoff=1400, drive_amt=3.8)
            out += place(te.stereo_spread(b, width=0.4) * 0.9, i * E, dur)
            chug = powerchug_guitar(n, dur=E * 0.85)
            out += place(chug * 0.85, i * E, dur)

    return out[:int(BAR * SR)]


def main():
    cues_path = ROOT / "data" / "hero.cues.json"
    c = json.loads(cues_path.read_text())
    dur = c["duration"]
    n = int(dur * SR)

    print("\n=======================================================")
    print(" RENDERING MASTER SOUNDTRACK: TRACK 1B + ORGANIC SFX")
    print("=======================================================")

    # 1. MUSIC BED
    bed = np.zeros((n, 2), dtype=np.float32)
    for seg_idx, seg in enumerate(c.get("music", [])):
        length = seg["until"] - seg["at"]
        bars = max(1, int(np.ceil(length / BAR)))
        section = seg["section"]
        gain = seg.get("gain", 1.0)
        seg_audio = np.zeros((int((bars * BAR + 1.0) * SR), 2))
        for b in range(bars):
            bar_audio = render_industrial_1b_bar(section, b, seed=seg_idx * 50 + b)
            seg_audio += place(bar_audio, b * BAR, bars * BAR + 1.0)

        seg_cut = seg_audio[: int((length + 0.04) * SR)].copy()
        fade_len = int(0.04 * SR)
        if len(seg_cut) > fade_len:
            seg_cut[-fade_len:] *= np.linspace(1, 0, fade_len)[:, None]
        bed += place(seg_cut * gain, seg["at"], dur)

    bed = np.tanh(bed * 1.1)
    bed = bed / max(1e-9, np.max(np.abs(bed))) * 0.89

    music_mp3 = REV_DIR / "hero-track1b-new-sfx-music-only.mp3"
    music_wav = REV_DIR / "hero-track1b-new-sfx-music-only.wav"
    sf.write(music_wav, bed, SR, subtype="PCM_24")
    subprocess.run(["ffmpeg", "-y", "-i", str(music_wav), "-codec:a", "libmp3lame", "-b:a", "256k", str(music_mp3)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"✓ Saved Music Bed: {music_mp3.name}")

    # 2. SFX BUS & VOICE BUS
    sfx_bus = np.zeros((n, 2), dtype=np.float32)
    voice_bus = np.zeros((n, 2), dtype=np.float32)
    cache, hits, voices, carves = {}, [], [], []

    for q in c["cues"]:
        if "clip" in q:
            clip_path = q["clip"]
            start_from = q.get("from", 0.0)
            clip_dur = q.get("dur")
            gain = q.get("gain", 1.0)
            fade_s = q.get("fade", 0.02)

            # Refinement: tune No Kings chant level and clean ending before slot reels
            if "no-kings" in str(clip_path):
                gain = 1.02
                clip_dur = 8.4  # Fades cleanly at 2:05.2, removing all car honks
                fade_s = 0.75

            x = load_clip(clip_path, start_from, clip_dur, fade_s, q.get("eq"), q.get("fade_out"))
            if x is not None:
                x_stereo = np.stack([x, x], axis=1) * gain
                voice_bus += place(x_stereo, q["t"], dur)
                dk = q.get("duck", True)
                if dk:
                    voices.append((q["t"], len(x) / SR, 1.0 if dk is True else float(dk)))
                if q.get("carve"):
                    carves.append((q["t"], len(x) / SR, float(q["carve"])))
            continue

        name = q["sfx"]
        if name not in cache:
            cache[name] = LIBRARY[name]()
        sfx_mono = cache[name] * q.get("gain", 1.0)
        sfx_bus += place(np.stack([sfx_mono, sfx_mono], axis=1), q["t"], dur)
        if name in DUCKERS:
            hits.append((q["t"], 0.0))

    # SFX isolated render
    sfx_isolated_wav = REV_DIR / "hero-track1b-new-sfx-only.wav"
    sfx_isolated_mp3 = REV_DIR / "hero-track1b-new-sfx-only.mp3"
    sfx_norm = sfx_bus / max(1e-9, np.max(np.abs(sfx_bus))) * 0.90
    sf.write(sfx_isolated_wav, sfx_norm, SR, subtype="PCM_24")
    subprocess.run(["ffmpeg", "-y", "-i", str(sfx_isolated_wav), "-codec:a", "libmp3lame", "-b:a", "256k", str(sfx_isolated_mp3)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"✓ Saved SFX-Only Track: {sfx_isolated_mp3.name}")

    # 3. SPEECH NOTCHING (CARVE) & DUCKING
    if carves:
        sos = sps.butter(2, [1000, 4000], btype="band", fs=SR, output="sos")
        cut = 1.0 - duck_env(n, carves, 1.0, 0.08, 0.0, 0.3)
        bed[:, 0] = bed[:, 0] - cut * sps.sosfiltfilt(sos, bed[:, 0])
        bed[:, 1] = bed[:, 1] - cut * sps.sosfiltfilt(sos, bed[:, 1])
        sfx_bus[:, 0] = sfx_bus[:, 0] - cut * sps.sosfiltfilt(sos, sfx_bus[:, 0])
        sfx_bus[:, 1] = sfx_bus[:, 1] - cut * sps.sosfiltfilt(sos, sfx_bus[:, 1])

    duck = duck_env(n, hits, 0.65, 0.005, 0.0, 0.25) * duck_env(n, voices, 0.75, 0.08, 0.05, 0.4)
    sfx_duck = duck_env(n, voices, 0.5, 0.08, 0.05, 0.4)

    # 4. MASTER SUMMATION & LIMITING (PUNCHY LANDING HITS: sfx_bus boosted to 1.05)
    m = bed * 0.46 * duck[:, None] + sfx_bus * 1.05 * sfx_duck[:, None] + voice_bus * 0.95
    m *= silence_env(n, c.get("silence", []))[:, None]
    m = np.tanh(m * 1.1)
    m = m / max(1e-9, np.max(np.abs(m))) * 0.891
    # the end card fades to silence with the video instead of stopping mid-sound
    tail = int(2.5 * SR)
    m[-tail:] *= (np.cos(np.linspace(0, np.pi / 2, tail)) ** 2)[:, None]

    # Master files for review
    mix_wav = REV_DIR / "hero-track1b-new-sfx-full-mix.wav"
    mix_mp3 = REV_DIR / "hero-track1b-new-sfx-full-mix.mp3"
    sf.write(mix_wav, m, SR, subtype="PCM_24")
    subprocess.run(["ffmpeg", "-y", "-i", str(mix_wav), "-codec:a", "libmp3lame", "-b:a", "256k", str(mix_mp3)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"✓ Saved Full Mix: {mix_mp3.name}")

    # 5. WRITE STEMS AND MASTER TO HERO/ASSETS/AUDIO/ (FOR HYPERFRAMES)
    hero_mix_wav = HERO_AUDIO / "mix.wav"
    sf.write(hero_mix_wav, m, SR, subtype="PCM_24")
    sf.write(STEMS_DIR / "music.wav", (bed * 0.46 * duck[:, None]).astype(np.float32), SR, subtype="PCM_24")
    sf.write(STEMS_DIR / "sfx.wav", (sfx_bus * 1.05 * sfx_duck[:, None]).astype(np.float32), SR, subtype="PCM_24")
    sf.write(STEMS_DIR / "voice.wav", (voice_bus * 0.95).astype(np.float32), SR, subtype="PCM_24")
    print(f"✓ Updated Hyperframes Assets: {hero_mix_wav.relative_to(ROOT)}")

    # 6. VIDEO MUX
    video_1080p = ROOT / "out" / "hero-v3-render-1080p.mp4"
    video_out = REV_DIR / "hero-v3-track1b-new-sfx-720p.mp4"
    if video_1080p.exists():
        subprocess.run(["ffmpeg", "-y", "-i", str(video_1080p), "-i", str(mix_wav),
                        "-vf", "scale=1280:720", "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                        "-c:a", "aac", "-b:a", "256k",
                        "-map", "0:v:0", "-map", "1:a:0", "-shortest", str(video_out)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"✓ Saved 720p Movie Mux: {video_out.name} ({video_out.stat().st_size / 1024 / 1024:.1f} MB)")

    # 7. LOUDNESS MEASUREMENT
    res = subprocess.run([
        "ffmpeg", "-i", str(mix_wav), "-af", "ebur128=framelog=verbose", "-f", "null", "-"
    ], capture_output=True, text=True)
    for line in res.stderr.splitlines():
        if "Integrated loudness:" in line or "Loudness range:" in line or "True peak:" in line:
            print(f"  {line.strip()}")


if __name__ == "__main__":
    main()
