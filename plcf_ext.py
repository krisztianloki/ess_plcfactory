from __future__ import absolute_import
""" PLC Factory: PLCF# Extensions """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"


# user-defined extensions for PLCF#
from ccdb import CCDB
import plcf_glob

# simple example:
def foo(x):
    assert isinstance(x, int)

    return x * x * x


# add whatever you need here:
def to_filename(x):
    assert isinstance(x, str)

    return CCDB.sanitizeFilename(x)

def eee_modulename():
    return plcf_glob.modulename
