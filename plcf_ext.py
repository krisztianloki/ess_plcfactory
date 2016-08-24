""" PLC Factory: PLCF# Extensions """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"


# user-defined extensions for PLCF#

# simple example:
def foo(x):
    assert isinstance(x, int)
    
    return x * x * x


# add whatever you need here: