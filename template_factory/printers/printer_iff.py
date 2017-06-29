""" Template Factory: IFF printer class """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


#FIXME:
# ARRAY_INDEX in IFF should be in the format of [PLCF# Counter{3,4} + array_index]
#TODO:
# DOCUMENT, DOCUMENT, DOCUMENT


from printers import PRINTER
from tf_ifdef import SOURCE, BLOCK, BASE_TYPE, BIT


def printer():
    return (IFF.name(), IFF)



_iff_template = """VARIABLE
{name}
EPICS
{epics}
TYPE
{type}
ARRAY_INDEX
{array_index}
BIT_NUMBER
{bit_number}
"""




#STATUS       = "STATUS"
#CMD          = "COMMAND"
#counters          = { CMD : "Counter3",     STATUS : "Counter4" }



#
# InterFaceFactory output
#
class IFF(PRINTER):
    def __init__(self, comments = False):
        PRINTER.__init__(self, comments)


    def comment(self):
        return "#"


    @staticmethod
    def name():
        return "IFA"


    def header(self, output):
        PRINTER.header(self, output)._append("""#FILENAME [PLCF#INSTALLATION_SLOT]-[PLCF#TEMPLATE]-[PLCF#TIMESTAMP].ifa
HASH
#HASH
""", output)


    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)

        self._append("""DEVICE
{slot}
DEVICE_TYPE
{type}
""".format(slot = self.plcf("INSTALLATION_SLOT"), type = self.plcf("DEVICE_TYPE")), output)

        for src in if_def.interfaces():
            if isinstance(src, BLOCK):
                self._body_block(src, output)
            elif isinstance(src, BASE_TYPE):
                self._body_var(src, output)
            elif isinstance(src, SOURCE):
                self._body_source(src, output)


    def _body_block(self, block, output):
        self._append((block.source(), "BLOCK\n{block_type}\n".format(block_type = block.type())), output)


    def _body_var(self, var, output):
        self._append((var.source(), self._body_format_var(var)), output)


    def _body_source(self, var, output):
        if var.source().strip() == "":
            return
        #
        # Do not include comments
        #
#        self._append((var.source(), ""), output)


    def _body_format_var(self, var):
        if isinstance(var, BIT) and var._skip:
            return ""

        if var.is_overlapped():
            return ""

        if var.offset() % 2:
            if not isinstance(var, BIT):
                bit_number = 8
            else:
                bit_number = 8 + var.bit_number()
        else:
            bit_number = var.bit_number()

        return _iff_template.format(name        = var.name(),
                                    epics       = var.name(),
                                    type        = var.plc_type(),
                                    array_index = str(var.offset() // 2),
                                    bit_number  = bit_number)
