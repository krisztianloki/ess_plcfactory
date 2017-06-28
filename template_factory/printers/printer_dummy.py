""" Template Factory: dummy printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from printers import PRINTER



def printer():
    return (DUMMY.name(), DUMMY)




class DUMMY(PRINTER):
    def __init__(self, comments = False):
        PRINTER.__init__(self, comments)


    @staticmethod
    def name():
#TODO: Return the name of your printer
        raise NotImplementedError


    #
    # HEADER
    #
    def header(self, output):
        PRINTER.header(self, output)


    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)


    #
    # FOOTER
    #
    def footer(self, output):
        PRINTER.footer(self, output)
