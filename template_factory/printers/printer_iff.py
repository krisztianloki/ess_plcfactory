""" Template Factory: IFF printer class """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


#TODO:
# DOCUMENT, DOCUMENT, DOCUMENT


from . import PRINTER
from tf_ifdef import SOURCE, BLOCK, CMD_BLOCK, STATUS_BLOCK, BASE_TYPE, BIT


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




#
# InterFaceFactory output
#
class IFF(PRINTER):
    def __init__(self):
        PRINTER.__init__(self, comments = True, preserve_empty_lines = False, show_origin = False)


    def comment(self):
        return "//"


    @staticmethod
    def name():
        return "IFA"


    def plcdiag_orzero(self, plc_diag):
        return self.plcf("'PLC-DIAG:{plc_diag}' if not 'PLC-DIAG:{plc_diag}'.startswith('PLC-DIAG') else 0".format(plc_diag = plc_diag))


    #
    # HEADER
    #
    def header(self, output):
        #
        # No need to initialize counters to 10, IFA does not need it
        #
        PRINTER.header(self, output)._append("""#FILENAME {inst_slot}-[PLCF#TEMPLATE]-[PLCF#TIMESTAMP].ifa
HASH
#HASH
MAX_IO_DEVICES
{max_io_devices}
MAX_LOCAL_MODULES
{max_local_modules}
MAX_MODULES_IN_IO_DEVICE
{max_modules_in_io_device}
""".format(inst_slot                = self.inst_slot(),
           max_io_devices           = self.plcdiag_orzero("Max-IO-Devices"),
           max_local_modules        = self.plcdiag_orzero("Max-Local-Modules"),
           max_modules_in_io_device = self.plcdiag_orzero("Max-Modules-In-IO-Device")), output)


    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)

        self._append("""DEVICE
{inst_slot}
DEVICE_TYPE
{type}
EPICSTOPLCLENGTH
{epicstoplclength}
EPICSTOPLCDATABLOCKOFFSET
{epicstoplcdatablockoffset}
EPICSTOPLCPARAMETERSSTART
{epicstoplcparametersstart}
PLCTOEPICSDATABLOCKOFFSET
{plctoepicsdatablockoffset}
#COUNTER {cmd_cnt} = [PLCF# {cmd_cnt} + {epicstoplclength}];
#COUNTER {status_cnt} = [PLCF# {status_cnt} + {plctoepicslength}];
""".format(inst_slot                 = self.inst_slot(),
           type                      = self.plcf("DEVICE_TYPE"),
           epicstoplcdatablockoffset = self.plcf("^(EPICSToPLCDataBlockStartOffset) + {cmd_cnt}".format(cmd_cnt = CMD_BLOCK.counter_keyword())),
           plctoepicsdatablockoffset = self.plcf("^(PLCToEPICSDataBlockStartOffset) + {status_cnt}".format(status_cnt = STATUS_BLOCK.counter_keyword())),
           epicstoplcparametersstart = self.plcf(str(if_def.properties()[CMD_BLOCK.length_keyword()])),
           epicstoplclength          = if_def.to_plc_words_length(),
           plctoepicslength          = if_def.from_plc_words_length(),
           cmd_cnt                   = CMD_BLOCK.counter_keyword(),
           status_cnt                = STATUS_BLOCK.counter_keyword()), output)

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
        self._append(var, output)


    def _body_format_var(self, var):
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
                                    epics       = var.pv_name(),
                                    type        = var.plc_type(),
                                    array_index = str(var.offset() // 2),
                                    bit_number  = bit_number)


    #
    # FOOTER
    #
    def footer(self, output):
        PRINTER.footer(self, output)

        self._append("""TOTALEPICSTOPLCLENGTH
{totalepicstoplclength}
TOTALPLCTOEPICSLENGTH
{totalplctoepicslength}
""".format(totalepicstoplclength = self.plcf(CMD_BLOCK.counter_keyword() + " + 10"),
           totalplctoepicslength = self.plcf(STATUS_BLOCK.counter_keyword() + " + 10")), output)
