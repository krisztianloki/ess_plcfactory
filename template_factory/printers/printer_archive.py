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
    def _ifdef_body(self, if_def, output, **keyword_params):
        inst_slot = self.inst_slot()
        self._append("#" * 60, output)
        for var in if_def.interfaces():
            if isinstance(var, BASE_TYPE) and var.get_parameter("ARCHIVE", False):
                desc = self._get_desc(var)
                if desc:
                    self._append("# {}".format(desc), output)
                self._append("{inst_slot}:{name}{policy}".format(inst_slot = inst_slot,
                                                                 name      = var.pv_name(),
                                                                 policy    = self._archive(var)), output)


    def _archive(self, var):
        arch = var.get_parameter("ARCHIVE")
        if isinstance(arch, bool):
            return ""
        if not (isinstance(arch, str) or isinstance(arch, int) or isinstance(arch, float)):
            raise IfDefSyntaxError("Invalid ARCHIVE specification: {} {}".format(arch, type(arch)))

        return arch


    def _get_desc(self, var):
        desc = var.get_parameter("ARCH_DESC", None)
        if not desc:
            desc = var.get_parameter("ARCHIVE_DESC", None)
            if not desc:
                desc = var.get_parameter("PV_DESC", None)

        return desc
