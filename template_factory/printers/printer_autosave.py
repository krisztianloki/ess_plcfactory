""" Template Factory: Autosave req file printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER
from tf_ifdef import BASE_TYPE


def printer():
    return (AUTOSAVE.name(), AUTOSAVE)




class AUTOSAVE(PRINTER):
    def __init__(self):
        PRINTER.__init__(self, comments = False, preserve_empty_lines = False, show_origin = False)


    @staticmethod
    def name():
        return "AUTOSAVE"


    #
    # HEADER
    #
    def header(self, output):
        PRINTER.header(self, output)
        self._append("""#FILENAME {inst_slot}-[PLCF#TEMPLATE]-[PLCF#TIMESTAMP].req
""".format(inst_slot = self.inst_slot()), output)

        return self


    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)

        self._output = output

        for src in if_def.interfaces():
            if isinstance(src, BASE_TYPE) and src.is_parameter():
                self._append("{inst_slot}:{pv_name}.VAL".format(inst_slot = self.inst_slot(),
                                                                pv_name   = src.pv_name()))
