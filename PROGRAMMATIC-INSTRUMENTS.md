# Programmatic Instrument & Sound Design Catalog

This document is the definitive reference manual for all musical instruments, synthesizer engines, acoustic sample libraries, and sound design elements built for **VOTE. THEM. OUT.** 

It includes mathematical formulations, sample library paths, parameter settings, and ready-to-run Python recipes so you can easily reuse these instruments in future projects.

---

## 1. Directory Structure & Asset Locations

All source audio assets are stored locally and organized by category:

| Asset Library | Location | Description & Included Instruments |
| :--- | :--- | :--- |
| **CC0 Acoustic Drums** | `assets/audio/cc0/drums/` | Clean acoustic multi-sampled kit: 8 kicks (`Kick_1`–`Kick_8`), 2 snares, `Snare_Rimshot_1`, 4 high toms, 4 mid toms, 3 low toms, 3 closed/open hi-hats, ride cymbal, and bell (`Cymbal_Centre_Bell.wav`). |
| **Roland TR-808 Kit** | `assets/audio/cc0/tr808/` | Vintage analog drum machine: `BD` (Bass Drum variations), `SD` (Snares), `CH`/`OH` (Hi-Hats), `CL` (Clave), `RS` (Rimshot), `CP` (Handclap), `CB` (Cowbell), `MA` (Maraca). |
| **Acoustic Cello Plucked** | `~/tidal/samples/clean/samples-cello-plucked/` | Multi-sampled cello: `00`–`02` C2 plucks, `03`–`05` C3 plucks, `06_C3_pluck_harmonic.wav`, `07_C4`, `08_C5`, `10_body_low.wav` & `11_body_high.wav` (wood resonance), and arpeggios. |
| **Acoustic Cello Bowed** | `~/tidal/samples/clean/samples-cello-bowed/` | Sustained acoustic cello bows across registers for cinematic drone beds and transitions. |
| **Fretless Bass** | `~/tidal/samples/clean/samples-flbass/` | Clean electric fretless bass notes for organic basslines and slides. |
| **Spoken Word & Clips** | `assets/clips/` (not in the repo) | `trump-cold-open.wav` and `trump-11780.wav` (Georgia phone call) are fair-use commentary clips for VOTE. THEM. OUT. only: **not CC0, not reusable assets**. The No Kings chant and cheers are CC0 (Freesound, CHallSmith) in `assets/audio/cc0/`. |
| **Rendered Review Files** | `out/for-review/` | All audition reels, stems, master mixes, and MP4 video cuts. |

---

## 2. Core Python DSP Toolkit (`scripts/sfx.py` & `scripts/track_engines.py`)

These core utilities provide sample-rate independent synthesis, pitch-shifting, phone-speaker saturation, and room reflections:

```python
import numpy as np
import scipy.signal as sps
import soundfile as sf
from pathlib import Path
from functools import lru_cache

SR = 48_000

def t_axis(dur):
    """Generate time axis in seconds."""
    return np.arange(int(dur * SR)) / SR

def env_exp(dur, decay, attack=0.002):
    """Exponential decay envelope with fast attack smoothing."""
    t = t_axis(dur)
    a = np.clip(t / attack, 0, 1) if attack > 0 else 1.0
    return a * np.exp(-t / decay)

def env_ahdsr(dur, a=0.01, h=0.05, d=0.1, s=0.7, r=0.1):
    """Full Attack-Hold-Decay-Sustain-Release envelope."""
    t = t_axis(dur)
    env = np.zeros_like(t)
    ia, ih, id_ = int(a * SR), int(h * SR), int(d * SR)
    if ia > 0: env[:ia] = np.linspace(0, 1, ia)
    env[ia:ia+ih] = 1.0
    decay_len = min(id_, len(env) - (ia + ih))
    if decay_len > 0: env[ia+ih:ia+ih+decay_len] = np.linspace(1, s, decay_len)
    env[ia+ih+decay_len:] = s
    ir = int(r * SR)
    if ir > 0 and len(env) > ir: env[-ir:] *= np.linspace(1, 0, ir)
    return env

def bandpass(x, lo, hi, order=3):
    sos = sps.butter(order, [max(10, lo), min(SR/2 - 100, hi)], btype="band", fs=SR, output="sos")
    return sps.sosfilt(sos, x)

def lowpass(x, fc, order=3):
    sos = sps.butter(order, min(SR/2 - 100, fc), btype="low", fs=SR, output="sos")
    return sps.sosfilt(sos, x)

def highpass(x, fc, order=3):
    sos = sps.butter(order, max(10, fc), btype="high", fs=SR, output="sos")
    return sps.sosfilt(sos, x)

def soft_saturate(x, drive_amt=2.0):
    """Asymmetric tube saturation: produces phone-audible 2nd and 3rd harmonics."""
    y = x * drive_amt
    y_asym = y + 0.15 * (y ** 2)
    return np.tanh(y_asym) / np.tanh(drive_amt)

def stereo_spread(x_mono, width=0.4, delay_ms=12.0):
    """Mono-safe widening: a delayed, high-passed copy is added to L and subtracted from R,
    so L+R is exactly the dry sound (no comb filtering on mono phone/Bluetooth speakers),
    the image stays centered, and everything under ~250 Hz stays in the middle.
    Don't widen with a plain L/R delay: it cost the kick and bass ~6 dB at 60-150 Hz in mono
    and pulled the image left (measured on the VOTE. THEM. OUT. mix, 2026-10-10)."""
    if width <= 0: return np.stack([x_mono, x_mono], axis=1)
    d = int(delay_ms * 0.001 * SR)
    mid = np.pad(x_mono, (0, d))
    side = highpass(np.pad(x_mono, (d, 0)), 250.0) * width
    return np.stack([mid + side, mid - side], axis=1)

def reverb(x, size=0.5, wet=0.18, seed=11):
    """Fast convolution room reverb simulation."""
    is_stereo = x.ndim > 1
    t = t_axis(size)
    rng = np.random.default_rng(seed)
    ir = lowpass(rng.uniform(-1, 1, int(size * SR)) * np.exp(-t / (size / 4.0)), 5000)
    ir /= np.sqrt(np.sum(ir ** 2) + 1e-12)
    if is_stereo:
        ir_r = lowpass(rng.uniform(-1, 1, int(size * SR)) * np.exp(-t / (size / 4.0)), 5000)
        ir_r /= np.sqrt(np.sum(ir_r ** 2) + 1e-12)
        wl = sps.fftconvolve(x[:, 0], ir)[: len(x)]
        wr = sps.fftconvolve(x[:, 1], ir_r)[: len(x)]
        return np.stack([wl, wr], axis=1) * wet + x * (1.0 - wet)
    w = sps.fftconvolve(x, ir)[: len(x)]
    return w * wet + x * (1.0 - wet)

@lru_cache(maxsize=128)
def load_sample(path, dur=None, pitch_semitones=0):
    """Loads, resamples, trims, and pitch-shifts audio samples."""
    p = Path(path)
    if not p.exists(): return np.zeros(100)
    x, sr = sf.read(p)
    if x.ndim > 1: x = x.mean(axis=1)
    if sr != SR: x = sps.resample_poly(x, SR, sr)
    if pitch_semitones != 0:
        ratio = 2.0 ** (pitch_semitones / 12.0)
        x = sps.resample(x, int(len(x) / ratio))
    idx = np.argmax(np.abs(x) > 0.05 * np.max(np.abs(x)))
    x = x[max(0, idx - 16):]
    if dur is not None: x = x[: int(dur * SR)]
    m = np.max(np.abs(x))
    return x / m if m > 0 else x
```

---

## 3. The Soundtrack Engines (`scripts/track_engines.py`)

Four complete, production-ready musical engines were designed at 135 BPM in D minor:

### Engine 1: Industrial Power-Chug (Active Track 1B)
- **Aesthetic**: Gritty, relentless, driving industrial rock (Nine Inch Nails / Doom).
- **Core Instruments**:
  1. **Powerchug Guitar**: Triple detuned sawtooth oscillators run through aggressive cabinet filtering (120–3400 Hz) and tube saturation.
     ```python
     def powerchug_guitar(freq, dur=0.22):
         t = t_axis(dur)
         sig = (saw_osc(freq, dur) + saw_osc(freq * 1.498, dur) + saw_osc(freq * 2.0, dur)) / 3.0
         driven = soft_saturate(sig * 3.5, 4.0)
         cab = bandpass(driven, 120, 3400, order=3)
         return stereo_spread(cab * env_exp(dur, 0.12, 0.002) * 1.05, width=0.35)
     ```
  2. **Saturated Reese Mid-Bass**: Dual detuned sawtooths (+/- 9 cents) layered over a sub sine wave, filtered through a resonant lowpass at 600–850 Hz.
  3. **Industrial Rhythm Section**: Tight sub kick, gated acoustic snare, and 16th-note inharmonic metallic hi-hats.

### Engine 2: Cyberpunk / Darksynth Thriller (Track 2)
- **Aesthetic**: Dark, retro-futuristic synth thriller (Carpenter Brut / Kavinsky).
- **Core Instruments**:
  1. **Punchy Analog Sub Kick**: 55 Hz sub with a 160 Hz exponential plunge and 3.5 kHz transient click.
  2. **80s Gated Snare**: Resonant 220 Hz drum body layered with stereo white noise and a 240 ms brickwall gated reverb.
  3. **Sequenced Bass Saw**: Detuned saws lowpass-filtered at 800 Hz with fast 70 ms decay.

### Engine 3: Cinematic Hybrid (Track 3)
- **Aesthetic**: High-stakes theatrical trailer (Hans Zimmer / Junkie XL).
- **Core Instruments**:
  1. **Brass Braam Impact**: Pitch-dropping triple saw cluster opening to 1.8 kHz and plunging down into sub-bass saturation.
  2. **Orchestral Taiko Hit**: Resonant acoustic drum skin knock layered with an 808 sub sweep.
  3. **16th-Note Cello Ostinato**: Acoustic cello samples (`samples-cello-plucked`) arpeggiated across D minor.

### Engine 4: Heavy Electro-Rock (Track 4)
- **Aesthetic**: Live rock energy with electronic propulsion (Royal Blood / Muse / The Prodigy).
- **Core Instruments**:
  1. **Live Acoustic Kit**: Multi-sampled acoustic kicks (`Kick_4`), rimshots (`Snare_Rimshot_1`), and real hi-hats.
  2. **Dual-Amp Distorted Fuzz Bass**: Clean DI sub-bass lowpassed at 180 Hz, blended with a parallel guitar-amp fuzz pedal bandpassed at 250–2800 Hz.

---

## 4. Rhythmic UI Percussion Catalog (Philosophy 1)

These elements replace artificial collision Foley with **real drum kit percussion locked to the 135 BPM quarter-note grid**:

### A. Card Arrival: Option 1B — Muted Mid-Tom Tap *(Master Winner)*
- **Role**: Punctuation for evidence receipts and document arrivals.
- **Sound Source**: `assets/audio/cc0/drums/Mid_Tom_1.wav`.
- **Processing**: Bandpassed between 160 Hz and 950 Hz, smoothed with an 80 ms exponential decay and subtle 0.4s room reflections.
- **Why It Works**: Sits comfortably in the low-mids, supporting the kick drum. Completely eliminates high-frequency clicks and ear fatigue over 50+ cards.
```python
def card_slap_organic(seed=4, pitch=1.0):
    tom = load_sample(DRUMS / "Mid_Tom_1.wav", dur=0.15)
    if pitch != 1.0:
        tom = sps.resample(tom, int(len(tom) / pitch))
    filtered = bandpass(tom, 160, 950)
    t = np.linspace(0, len(filtered) / SR, len(filtered), endpoint=False)
    env = np.exp(-t / 0.08)
    x = reverb(filtered * env, size=0.4, wet=0.14)
    return norm(x, peak=0.92)
```

### B. Alternate Card Arrival: Option 1A — Acoustic Cross-Stick
- **Sound Source**: `assets/audio/cc0/tr808/RS.wav` + `~/tidal/samples/clean/samples-cello-plucked/11_body_high.wav`.
- **Processing**: Bandpassed between 900 Hz and 4800 Hz with a 45 ms decay.
- **Vibe**: Crisp, dry side-stick rim click across the snare; sits in the hi-hat pocket.

### C. Alternate Card Arrival: Option 1C — 808 Clave / Electro Rim
- **Sound Source**: `assets/audio/cc0/tr808/CL.wav`.
- **Processing**: 35 ms transient with 0.45s room reflections.
- **Vibe**: Classic vintage electro-industrial percussive strike.

### D. Card Flip at 1:04: Flip 2B — 1-Beat Tom Fill
- **Role**: 180° transition when "THEY SAID" flips to "THEY DID".
- **Sound Source**: `High_Tom_1` → `Mid_Tom_1` → `Low_Tom_1`.
- **Duration**: Exactly 1 musical beat (0.444s at 135 BPM).
- **Vibe**: A tight 3-stroke acoustic drum fill rolling right into the reveal downbeat.

### E. Official Document Stamp: Stamp 3A — Kick + Cross-Stick Stomp
- **Role**: Red stamp marks ("CONFESSION", "A VOTE FOR REPUBLICANS IS:", "WATCH US.").
- **Sound Source**: `Kick_4.wav` + TR-808 `RS.wav` + `11_body_high.wav`.
- **Vibe**: Authoritative physical foot stomp / heavy wood handle slam with sub-kick body.

---

## 5. Grid-Locking & Visual Synchronization Rules

To achieve frame-accurate synchronization between visual animations and music:

1. **The Quarter-Note Grid Formula**:
   - `BPM = 135` → `BEAT = 60 / 135 = 0.4444s`
   - Set card spacing to integer beats: `gap = 1.0` (444 ms).
   - Set initial card delay to integer beats: `first = 1.0` (444 ms).
2. **Page Hold & Duration Rounding**:
   - Total page duration must always round up to an even integer of beats:
     $$\text{dur} = \max\left(6, 2 \times \left\lceil \frac{\text{first} + (n - 1)\text{gap} + 2.5}{2} \right\rceil\right)$$
   - In 4-card sections, duration is 8 beats (2 complete bars): 4 beats of arrivals + 4 beats of hold.
   - In 6-card sections, duration is 10–12 beats (2.5–3 bars): 6 beats of arrivals + 4–6 beats of hold.
3. **Hyperframes Render Protocol**:
   - Never mux new audio onto an older pre-rendered MP4 if the timing changed.
   - Always run `npx hyperframes render -o <output.mp4>` directly in `hero/` so Chrome captures the updated GSAP timeline frame-for-frame.
