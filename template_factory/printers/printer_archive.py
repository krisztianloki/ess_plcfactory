""" Template Factory: ARCHIVE printer class """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2018, European Spallation Source, Lund"
__license__    = "GPLv3"


#TODO:
# DOCUMENT, DOCUMENT, DOCUMENT


from . import PRINTER
from tf_ifdef import BASE_TYPE


def printer():
    return (ARCHIVE.name(), ARCHIVE)



#
# AA output
#
class ARCHIVE(PRINTER):
    def __init__(self):
        PRINTER.__init__(self)


    @staticmethod
    def name():
        return "ARCHIVE"


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        #
        # No need to initialize anything
        #
        PRINTER.header(self, output, **keyword_params).add_filename_header(output)


    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)

        inst_slot = self.inst_slot()
        for var in if_def.interfaces():
            if isinstance(var, BASE_TYPE) and var.get_parameter("ARCHIVE", False):
                self._append("{inst_slot}:{name}\n".format(inst_slot = inst_slot,
                                                           name      = var.pv_name()), output)
