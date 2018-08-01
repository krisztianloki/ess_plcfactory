""" Template Factory: Autosave req file printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER
from tf_ifdef import BASE_TYPE


def printer():
    return [ (AUTOSAVE.name(), AUTOSAVE), (AUTOSAVE_TEST.name(), AUTOSAVE_TEST) ]




class AUTOSAVE(PRINTER):
    def __init__(self):
        PRINTER.__init__(self, comments = False, preserve_empty_lines = False, show_origin = False)


    @staticmethod
    def name():
        return "AUTOSAVE"


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        PRINTER.header(self, output, **keyword_params).add_filename_header(output, "req")

        return self


    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)

        self._output = output

        for src in if_def.interfaces():
            if isinstance(src, BASE_TYPE) and src.is_parameter():
                self._append("{inst_slot}:{pv_name}.VAL".format(inst_slot = self.inst_slot(if_def),
                                                                pv_name   = src.pv_name()))



class AUTOSAVE_TEST(AUTOSAVE):
    def __init__(self):
        AUTOSAVE.__init__(self)


    @staticmethod
    def name():
        return "AUTOSAVE-TEST"


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        PRINTER.header(self, output, **keyword_params)
        self._append("""#FILENAME {inst_slot}-[PLCF#TEMPLATE]-[PLCF#TIMESTAMP]-test.req
""".format(inst_slot = self.inst_slot()), output)

        return self


    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)

        self._output = output

        for src in if_def.interfaces():
            if isinstance(src, BASE_TYPE) and src.is_status():
                self._append("{inst_slot}:{pv_name}.VAL".format(inst_slot = self.inst_slot(if_def),
                                                                pv_name   = src.pv_name()))
