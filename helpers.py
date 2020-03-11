from __future__ import absolute_import

""" PLC Factory: helper functions """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2018, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
import os
import unicodedata
try:
    from   urlparse import urlsplit
except ImportError:
    from urllib.parse import urlsplit

# Fake a WindowsError exception under non-Windows machines
try:
    we = WindowsError()
    del we
except NameError:
    WindowsError = OSError

# Fake a FileNotFoundError in Python2
try:
    fnf = FileNotFoundError()
    del fnf
except NameError:
    FileNotFoundError = OSError



def rmdirs(path):
    from shutil import rmtree
    def onrmtreeerror(func, e_path, exc_info):
        if e_path != path:
            raise

        if not (func is os.listdir or func is os.rmdir or func is os.lstat):
            raise

        if not (exc_info[0] is OSError or exc_info[0] is FileNotFoundError or exc_info[0] is WindowsError):
            raise

        if exc_info[1].errno != 2:
            raise

    rmtree(path, onerror = onrmtreeerror)


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


def sanitizeFilename(filename):
    # Only needed for Python2
    try:
        if isinstance(filename, str):
            filename = filename.decode("utf-8")
    except AttributeError:
        # Python3 string does not have decode()
        pass

    # replace accented characters with the unaccented equivalent
    filename = unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore")

    if isinstance(filename, bytes) and not isinstance(filename, str):
        # Only needef for Python3
        filename = filename.decode()

    def sanP(p):
        (head, tail) = os.path.split(p)
        if not head:
            return "".join(map(lambda x: '_' if x in '<>:"/\|?*' else x, p))
        head = "".join(map(lambda x: '_' if x in '<>:"/\|?*' else x, head))
        return os.path.join(head, sanP(tail))

    return sanP(filename)


def create_data_dir(product):
    dname = os.path.join(os.path.expanduser("~"), ".local", "share", product)
    makedirs(dname)

    return dname


def tounicode(string):
    try:
        # Python2 shortcut
        if isinstance(string, unicode):
            return string
    except NameError:
        # Python3, it is already unicode
        return string

    return string.decode("utf-8")
