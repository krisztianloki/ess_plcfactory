""" Template Factory: Device list printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2018, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER



def printer():
    return (DEVLIST.name(), DEVLIST)




class DEVLIST(PRINTER):
    def __init__(self):
        PRINTER.__init__(self, comments = False, preserve_empty_lines = False, show_origin = False)


    @staticmethod
    def name():
        return "DEVICE-LIST"


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        PRINTER.header(self, output, **keyword_params)
        self.add_filename_header(output, "list")
        self._append(self.root_inst_slot(), output)


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output):
        self._any_body(output)


    def _any_body(self, output):
        self._append(self.inst_slot(), output)


    #
    # FOOTER
    #
    def footer(self, output):
        PRINTER.footer(self, output)
