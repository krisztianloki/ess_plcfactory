from __future__ import absolute_import
""" PLC Factory: PLCF# Extensions """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"


# user-defined extensions for PLCF#
import helpers
import plcf_glob

class PLCFExtException(Exception):
    pass



# simple example:
def foo(x):
    assert isinstance(x, int)

    return x * x * x


# add whatever you need here:
def to_filename(x):
    assert isinstance(x, str)

    return helpers.sanitizeFilename(x)


def eee_modulename():
    return plcf_glob.modulename


def e3_modulename():
    return plcf_glob.modulename


def snippet():
    return plcf_glob.snippet



class PVLengthException(PLCFExtException):
    pass



def check_pv_length(pv_name):
    assert isinstance(pv_name, str)

    if (len(pv_name) <= 60):
        return pv_name

    raise PVLengthException("The PV name '{pv_name}' is longer than permitted ({act_len} / 60)".format(pv_name = pv_name, act_len = len(pv_name)))
