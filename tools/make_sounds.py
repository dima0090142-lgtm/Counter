"""Synthesize the program's retro sounds (Windows 95 mood, own melodies) into sounds/*.wav.

    python tools/make_sounds.py

Pure Python (wave + math), 22 kHz 16-bit mono. Replace any file in sounds/ with your
own .wav of the same name to change a sound.
"""
import math
import os
import random
import struct
import wave

RATE = 22050
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sounds")


def note(name):
    """'C5' -> frequency."""
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    n = names[name[0]] + (1 if "#" in name else 0) + (int(name[-1]) - 4) * 12
    return 440.0 * 2 ** (n / 12)


def silence(sec):
    return [0.0] * int(RATE * sec)


def tone(freq, sec, partials=((1, 1.0), (2, 0.3), (3, 0.12)), attack=0.01, decay=3.0,
         vibrato=0.0):
    out = []
    n = int(RATE * sec)
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / attack) * math.exp(-decay * t)
        f = freq * (1 + vibrato * math.sin(2 * math.pi * 5.5 * t))
        s = sum(a * math.sin(2 * math.pi * f * k * t) for k, a in partials)
        out.append(env * s)
    return out


def bell(freq, sec, decay=4.0):
    # slightly inharmonic partials sound like a bell / chime
    return tone(freq, sec, partials=((1, 1.0), (2.01, 0.45), (3.02, 0.2), (4.2, 0.08)),
                attack=0.004, decay=decay)


def pad(freq, sec, attack=0.35, decay=1.1):
    return tone(freq, sec, partials=((1, 1.0), (2, 0.25), (0.5, 0.2), (3, 0.06)),
                attack=attack, decay=decay, vibrato=0.002)


def brass(freq, sec, decay=1.6):
    return tone(freq, sec, partials=((1, 1.0), (2, 0.6), (3, 0.42), (4, 0.25), (5, 0.12)),
                attack=0.03, decay=decay, vibrato=0.004)


def mix(length_sec, *parts):
    """parts: (start_sec, samples, gain)."""
    buf = [0.0] * int(RATE * length_sec)
    for start, samples, gain in parts:
        o = int(RATE * start)
        for i, v in enumerate(samples):
            if o + i < len(buf):
                buf[o + i] += v * gain
    return buf


def echo(buf, delay=0.11, feedback=0.35, times=4):
    d = int(RATE * delay)
    out = buf + [0.0] * d * times
    for k in range(1, times + 1):
        g = feedback ** k
        for i, v in enumerate(buf):
            out[i + d * k] += v * g
    return out


def fade_out(buf, sec=0.08):
    n = int(RATE * sec)
    for i in range(min(n, len(buf))):
        buf[-1 - i] *= i / n
    return buf


def save(name, buf, peak=0.85):
    m = max(abs(v) for v in buf) or 1.0
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(v / m * peak * 32767)) for v in buf))
    return path


def startup():
    """Warm rising chord with chimes on top, ~2.5 s."""
    chord = ["C4", "G4", "C5", "E5", "G5"]
    parts = [(0.0, pad(note("C3"), 2.6, attack=0.5, decay=0.9), 0.6)]
    for i, n in enumerate(chord):
        parts.append((0.08 + i * 0.13, pad(note(n), 2.4 - i * 0.13), 0.45))
    for i, n in enumerate(["G5", "C6", "E6", "G6"]):
        parts.append((0.7 + i * 0.18, bell(note(n), 1.4, decay=3.2), 0.22))
    parts.append((1.45, bell(note("C7"), 1.0, decay=3.5), 0.12))
    return fade_out(echo(mix(2.6, *parts), 0.16, 0.3, 3), 0.4)


def tada():
    """Short fanfare: two pick-up notes and a big chord."""
    parts = [(0.0, brass(note("G4"), 0.16, 6), 0.7), (0.15, brass(note("C5"), 0.16, 6), 0.7)]
    for n in ("C4", "G4", "C5", "E5", "G5"):
        parts.append((0.3, brass(note(n), 1.1, 2.4), 0.5))
    parts.append((0.3, bell(note("C6"), 0.9), 0.25))
    return fade_out(echo(mix(1.4, *parts), 0.09, 0.25, 2), 0.2)


def ding():
    return fade_out(mix(0.7, (0.0, bell(note("E6"), 0.7, 5.5), 1.0),
                        (0.0, bell(note("E5"), 0.7, 5), 0.35)))


def chord():
    """Error: three-note bell chord, slightly dark."""
    parts = [(0.0, bell(note(n), 0.8, 4.5), 0.6) for n in ("A4", "C5", "E5")]
    parts.append((0.0, bell(note("A3"), 0.8, 4), 0.4))
    return fade_out(mix(0.8, *parts))


def exclamation():
    return fade_out(mix(0.7, (0.0, bell(note("B5"), 0.35, 7), 0.8),
                        (0.14, bell(note("G5"), 0.55, 5), 0.8)))


def shutdown():
    """Falling chord for exit, ~1.3 s."""
    parts = []
    for i, n in enumerate(["G5", "E5", "C5", "G4", "C4"]):
        parts.append((i * 0.12, pad(note(n), 1.2 - i * 0.08, attack=0.05, decay=2.2), 0.5))
    return fade_out(echo(mix(1.3, *parts), 0.14, 0.25, 2), 0.25)


def click():
    random.seed(1)
    buf = [random.uniform(-1, 1) * math.exp(-i / 60) for i in range(int(RATE * 0.02))]
    return buf


SOUNDS = {"startup": startup, "tada": tada, "ding": ding, "chord": chord,
          "exclamation": exclamation, "shutdown": shutdown, "click": click}


def main():
    for name, fn in SOUNDS.items():
        print("written", save(name, fn()))


if __name__ == "__main__":
    main()
