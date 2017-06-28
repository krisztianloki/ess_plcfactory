""" Template Factory:  """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


from tf_ifdef import IF_DEF
from printers import get_printer, available_printers


def new():
    return IF_DEF()


def assert_IF_DEF(obj):
    assert isinstance(obj, IF_DEF)




if __name__ == "__main__":
    pass
