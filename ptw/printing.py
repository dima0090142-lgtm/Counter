"""Sending finished permits to the printer (test feature)."""
import os
import shutil
import subprocess
import sys


def can_print():
    if sys.platform.startswith("win"):
        return True
    return bool(shutil.which("soffice") or shutil.which("libreoffice") or shutil.which("lp"))


def print_file(path):
    """Print a .docx on the default printer.

    Windows: the "print" action of the file type (Word prints and closes the
    document by itself). Other systems: LibreOffice in the background."""
    if sys.platform.startswith("win"):
        os.startfile(path, "print")  # noqa: S606
        return
    office = shutil.which("soffice") or shutil.which("libreoffice")
    if office:
        subprocess.Popen([office, "--headless", "-p", path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    subprocess.Popen(["lp", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
