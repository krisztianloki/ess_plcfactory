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


def rmdirs(path):
    from shutil import rmtree
    def onrmtreeerror(func, e_path, exc_info):
        if e_path != path:
            raise

        if not (func is os.listdir or func is os.rmdir):
            raise

        if not (exc_info[0] is OSError or exc_info[0] is WindowsError):
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

    result = map(lambda x: '_' if x in '<>:"/\|?*' else x, filename)
    return "".join(result)


