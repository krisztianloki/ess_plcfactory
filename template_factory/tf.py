from __future__ import print_function
from __future__ import absolute_import

""" Template Factory:  """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


from tf_ifdef import IF_DEF
from printers import get_printer, available_printers, is_combinable

OPTIMIZE_S7DB = False

def optimize_s7db(optimize):
    global OPTIMIZE_S7DB

    OPTIMIZE_S7DB = optimize


def new(hashobj = None):
    return IF_DEF(hashobj)


def parseDef(def_file, **kwargs):
    assert isinstance(def_file, str)

    if "OPTIMIZE" not in kwargs:
        kwargs["OPTIMIZE"] = OPTIMIZE_S7DB

    if_def = IF_DEF(**kwargs)

    if_def.parse(def_file)

    if_def.end()

    return if_def


def assert_IF_DEF(obj):
    assert isinstance(obj, IF_DEF)




if __name__ == "__main__":
    pass
