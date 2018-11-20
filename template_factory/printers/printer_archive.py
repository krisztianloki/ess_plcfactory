""" Template Factory: ARCHIVE printer class """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2018, European Spallation Source, Lund"
__license__    = "GPLv3"


#TODO:
# DOCUMENT, DOCUMENT, DOCUMENT


from . import PRINTER
from tf_ifdef import IfDefSyntaxError, BASE_TYPE


def printer():
    return (ARCHIVE.name(), ARCHIVE)



#
# AA output
#
class ARCHIVE(PRINTER):
    methods = {"SCAN"    : "SCAN",
               "MONITOR" : "MONITOR"}

    def __init__(self):
        super(ARCHIVE, self).__init__()


    @staticmethod
    def name():
        return "ARCHIVE"


    @staticmethod
    def combinable():
        return True


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        #
        # No need to initialize anything
        #
        super(ARCHIVE, self).header(output, **keyword_params).add_filename_header(output, extension = "archive")


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output):
        inst_slot = self.inst_slot()
        for var in if_def.interfaces():
            if isinstance(var, BASE_TYPE) and var.get_parameter("ARCHIVE", False):
                self._append("{inst_slot}:{name}{spec}\n".format(inst_slot = inst_slot,
                                                                 name      = var.pv_name(),
                                                                 spec      = self._archive(var)), output)


    def _archive(self, var):
        arch = var.get_parameter("ARCHIVE")
        if isinstance(arch, bool):
            return ""
        if isinstance(arch, int) or isinstance(arch, float):
            return " {}".format(float(arch))
        elif not isinstance(arch, tuple):
            raise IfDefSyntaxError("Invalid ARCHIVE specification: {} {}".format(arch, type(arch)))

        if len(arch) != 2:
            raise IfDefSyntaxError("Wrong number of ARCHIVE elements: {}".format(arch))

        try:
            return " {} {}".format(float(arch[0]), self.methods[arch[1].upper()])
        except ValueError:
            raise IfDefSyntaxError("ARCHIVE parameters must start with a number: {}".format(arch))
        except KeyError:
            raise IfDefSyntaxError("ARCHIVE second parameter must be either one of {}".format(self.methods.values()))
