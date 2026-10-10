"""Audio sketch of the finale so the sequence can be judged by ear before animating it.

  tick-tock (they're counting on you to sleep) -> 1.6s dead silence ("YOU THOUGHT WE WERE ASLEEP?")
  -> alarm clock -> pitches down into an air-raid siren -> crowd roar swells -> marching stomps
  -> VOTE. THEM. OUT. (three slams) -> boom + crowd.

Writes assets/audio/finale_sound_test.wav
"""

from sfx import *  # noqa: F401,F403
import music

BEAT = music.BEAT
TOTAL = 17.5
bus = np.zeros(int(TOTAL * SR))


def put(x, at, gain=1.0):
    global bus
    bus += place(x * gain, at, TOTAL)


# 1) the clock: 8 beats of tick/tock over a low drone and a slow heartbeat
for k in range(8):
    put(tick_tock(tock=bool(k % 2), seed=15 + k % 2), k * BEAT, 0.55 + 0.04 * k)
    if k % 2 == 0:
        put(heartbeat(), k * BEAT, 0.35)
put(music.drone(8 * BEAT) * np.linspace(0.2, 0.6, int(8 * BEAT * SR)), 0, 0.5)

# 2) dead silence: 3.556 -> 5.6 (text: YOU THOUGHT WE WERE ASLEEP?)
alarm_at = 5.6

# 3) alarm clock, then it pitches down into the siren
alarm = alarm_clock(1.5)
put(alarm[: int(1.0 * SR)], alarm_at, 0.9)
put(tapestop(alarm[int(1.0 * SR):], 0.6), alarm_at + 1.0, 0.9)
siren_at = alarm_at + 0.95
put(air_raid_siren(9.0, wind_down_at=6.6), siren_at, 0.75)

# 4) crowd swells under the siren; the march starts on a downbeat
put(crowd_roar(7.5, swell=True), siren_at + 0.6, 0.6)
g0 = siren_at + 1.6
stomp, clap = crowd_stomp(), crowd_clap()
for k in range(12):
    put(stomp, g0 + k * BEAT - 0.02, 0.8)
    if k % 2 == 1:
        put(clap, g0 + k * BEAT - 0.015, 0.55)
put(music.render([{"section": "anthem", "bars": 3}]), g0, 0.45)

# 5) VOTE. THEM. OUT.
slams = [g0 + 12 * BEAT, g0 + 13 * BEAT, g0 + 14 * BEAT]
for i, s in enumerate(slams):
    put(impact(0.6 + 0.2 * i, seed=40 + i), s, 1.0)
    put(kachunk(seed=60 + i), s, 0.35)
put(boom_tail(), slams[-1] + 0.02, 0.9)
tail = crowd_roar(4.0, swell=False, seed=90)
put(tail * np.linspace(1, 0, len(tail)), slams[-1] + 0.1, 0.7)

# silence must be truly silent
bus[int(8 * BEAT * SR) : int(alarm_at * SR)] = 0.0
y = np.tanh(bus * 0.9)
y = y / np.max(np.abs(y)) * 0.89
out = ROOT / "assets" / "audio" / "finale_sound_test.wav"
sf.write(out, np.stack([y, y], axis=1).astype(np.float32), SR, subtype="PCM_24")
print(f"wrote {out.relative_to(ROOT)} ({TOTAL}s); slams at {[round(s, 2) for s in slams]}")
