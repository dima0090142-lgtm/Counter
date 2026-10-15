"""Log file for errors, crashes and hangs: logs/ptw.log next to the program.

- every unhandled error (main thread, worker threads, Tk callbacks) is written with
  its traceback;
- a hard crash of Python itself is written by faulthandler;
- if the window does not respond for HANG_SECONDS, the stacks of all threads are
  written (once per hang), so a freeze can be found later.
"""
import faulthandler
import logging
import logging.handlers
import os
import sys
import threading
import time
import traceback

from . import storage

HANG_SECONDS = 30
log = logging.getLogger("ptw")
LOG_DIR = ""
_crash_file = None
_beat = [time.monotonic()]


def _writable(folder):
    try:
        os.makedirs(folder, exist_ok=True)
        test = os.path.join(folder, ".write_test")
        with open(test, "w") as f:
            f.write("x")
        os.remove(test)
        return True
    except OSError:
        return False


def log_dir():
    """logs/ next to the program; if that folder is read-only, the user's local folder."""
    main = os.path.join(storage.APP_DIR, "logs")
    if _writable(main):
        return main
    alt = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                       "PTW_Generator", "logs")
    os.makedirs(alt, exist_ok=True)
    return alt


def setup():
    """Start logging; safe to call more than once."""
    global LOG_DIR, _crash_file
    if log.handlers:
        return LOG_DIR
    LOG_DIR = log_dir()
    handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, "ptw.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(threadName)s: %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    # Python itself crashing (access violation ...): faulthandler writes the stacks
    _crash_file = open(os.path.join(LOG_DIR, "crash.log"), "a", encoding="utf-8")  # noqa: SIM115
    faulthandler.enable(file=_crash_file, all_threads=True)
    sys.excepthook = lambda t, v, tb: error("Unhandled error", (t, v, tb))
    threading.excepthook = lambda a: error(f"Unhandled error in thread {a.thread.name if a.thread else ''}",
                                           (a.exc_type, a.exc_value, a.exc_traceback))
    from . import __version__
    log.info("---- start, version %s, Python %s, %s", __version__, sys.version.split()[0],
             sys.platform)
    return LOG_DIR


def error(message, exc_info=None):
    """Write an error with traceback (exc_info: True for the current exception)."""
    if exc_info is True:
        exc_info = sys.exc_info()
    text = "".join(traceback.format_exception(*exc_info)) if exc_info else ""
    log.error("%s\n%s", message, text)
    for h in log.handlers:
        h.flush()


def heartbeat():
    """Called by the GUI every second while it is responsive."""
    _beat[0] = time.monotonic()


def start_watchdog():
    """Thread that writes the stacks of all threads when the window hangs."""
    def watch():
        reported = False
        while True:
            time.sleep(5)
            stale = time.monotonic() - _beat[0]
            if stale > HANG_SECONDS and not reported:
                log.warning("Window not responding for %.0f s - stacks of all threads:", stale)
                if _crash_file:
                    _crash_file.write(f"\n==== {time.ctime()} window not responding "
                                      f"for {stale:.0f} s\n")
                    faulthandler.dump_traceback(file=_crash_file, all_threads=True)
                    _crash_file.flush()
                reported = True
            elif stale < HANG_SECONDS:
                if reported:
                    log.info("Window responds again")
                reported = False
    t = threading.Thread(target=watch, name="watchdog", daemon=True)
    t.start()
    return t
