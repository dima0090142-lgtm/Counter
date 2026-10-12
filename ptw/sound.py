"""Playing the program sounds (sounds/*.wav next to the program).

Any file in the sounds folder can be replaced with your own .wav of the same name.
Sounds never raise errors: no sound card or no player simply means silence.
"""
import os
import shutil
import subprocess
import sys

from . import storage

SOUND_DIR = os.path.join(storage.APP_DIR, "sounds")
EVENTS = ("startup", "shutdown", "tada", "ding", "chord", "exclamation", "click")

enabled = True
_players = []


def path(name):
    return os.path.join(SOUND_DIR, name + ".wav")


def play(name, wait=False):
    """Play sounds/<name>.wav. wait=True blocks until the sound ends (used on exit)."""
    if not enabled:
        return
    p = path(name)
    if not os.path.isfile(p):
        return
    try:
        if sys.platform.startswith("win"):
            import winsound
            flags = winsound.SND_FILENAME | winsound.SND_NODEFAULT
            if not wait:
                flags |= winsound.SND_ASYNC
            winsound.PlaySound(p, flags)
            return
        cmd = None
        for player, args in (("afplay", []), ("paplay", []), ("aplay", ["-q"])):
            exe = shutil.which(player)
            if exe:
                cmd = [exe, *args, p]
                break
        if not cmd:
            return
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _players.append(proc)
        if wait:
            proc.wait(timeout=5)
    except Exception:  # noqa: BLE001 - sound is decoration only
        pass
