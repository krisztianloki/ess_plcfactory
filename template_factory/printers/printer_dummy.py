from __future__ import absolute_import

""" Template Factory: dummy printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER



def printer():
    return (DUMMY.name(), DUMMY)




class DUMMY(PRINTER):
    def __init__(self):
        PRINTER.__init__(self, comments = False, preserve_empty_lines = False, show_origin = False)


    @staticmethod
    def name():
#TODO: Return the name of your printer
        raise NotImplementedError


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        PRINTER.header(self, output, **keyword_params)


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output):
        pass


    def _any_body(self, output):
        pass


    #
    # FOOTER
    #
    def footer(self, output):
        PRINTER.footer(self, output)
