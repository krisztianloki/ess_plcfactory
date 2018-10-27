from __future__ import absolute_import

""" Template Factory: Startup Snippet printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER
from tf_ifdef import STATUS_BLOCK



def printer():
    return [ (ST_CMD.name(), ST_CMD), (AUTOSAVE_ST_CMD.name(), AUTOSAVE_ST_CMD), (ST_TEST_CMD.name(), ST_TEST_CMD), (AUTOSAVE_ST_TEST_CMD.name(), AUTOSAVE_ST_TEST_CMD) ]




class ST_CMD(PRINTER):
    def __init__(self):
        super(ST_CMD, self).__init__()


    @staticmethod
    def name():
        return "ST-CMD"


    @staticmethod
    def flavor():
        return ""


    #
    # HEADER
    #
    def header(self, output, **keyword_parameters):
        super(ST_CMD, self).header(output, **keyword_parameters).add_filename_header(output, inst_slot = self.modulename(), template = False, extension = "cmd")

        st_cmd_header = """
# @field IPADDR
# @type STRING
# PLC IP address

# @field RECVTIMEOUT
# @type INTEGER
# PLC->EPICS receive timeout (ms), should be longer than frequency of PLC SND block trigger (REQ input)

# @field REQUIRE_{modulename}_VERSION
# @runtime YES
#COUNTER {status_cnt} = [PLCF#{status_cnt} + 10 * 2]

""".format(modulename = self.modulename(),
           status_cnt = STATUS_BLOCK.counter_keyword())

        self._append(st_cmd_header, output)


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output):
        status = if_def._status_block()
        if status is not None:
            self._append("#COUNTER {status_cnt} = [PLCF# {status_cnt} + {db_length}]".format(status_cnt = STATUS_BLOCK.counter_keyword(),
                                                                                             db_length  = status.length()), output)


    #
    # FOOTER
    #
    def footer(self, output):
        super(ST_CMD, self).footer(output)

        st_cmd_footer = """
# S7 port           : {s7drvport}
# Input block size  : {insize} bytes
# Output block size : 0 bytes
# Endianness        : {endianness}
s7plcConfigure("{modulename}", $(IPADDR), {s7drvport}, {insize}, 0, {bigendian}, $(RECVTIMEOUT), 0)

# Modbus port       : {modbusdrvport}
drvAsynIPPortConfigure("{modulename}", $(IPADDR):{modbusdrvport}, 0, 0, 1)

# Link type         : TCP/IP (0)
modbusInterposeConfig("{modulename}", 0, $(RECVTIMEOUT), 0)

# Slave address     : 0
# Function code     : 16 - Write Multiple Registers
# Addressing        : Absolute (-1)
# Data segment      : 2 words
drvModbusAsynConfigure("{modulename}write", "{modulename}", 0, 16, -1, 2, 0, 0, "S7-1500")

# Load plc interface database
dbLoadRecords("{modulename}.db", "PLCNAME={modulename}, MODVERSION=$(REQUIRE_{modulename}_VERSION)")
""".format(s7drvport     = self.plcf("PLC-EPICS-COMMS: S7Port"),
           modbusdrvport = self.plcf("PLC-EPICS-COMMS: MBPort"),
           insize        = self.plcf(STATUS_BLOCK.counter_keyword()),
           endianness    = self.plcf("PLC-EPICS-COMMS:Endianness"),
           bigendian     = self.plcf("1 if 'PLC-EPICS-COMMS:Endianness' == 'BigEndian' else 0"),
           modulename    = self.modulename()
          )

        self._append(st_cmd_footer, output)




class ST_TEST_CMD(PRINTER):
    def __init__(self):
        super(ST_TEST_CMD, self).__init__()


    @staticmethod
    def name():
        return "ST-TEST-CMD"


    @staticmethod
    def flavor():
        return "-test"


    #
    # HEADER
    #
    def header(self, output, **keyword_parameters):
        super(ST_TEST_CMD, self).header(output, **keyword_parameters).add_filename_header(output, inst_slot = self.modulename(), template = "test", extension = "cmd")

        st_cmd_header = """
# @field REQUIRE_{modulename}_VERSION
# @runtime YES

""".format(modulename = self.modulename())

        self._append(st_cmd_header, output)


    #
    # FOOTER
    #
    def footer(self, output):
        super(ST_TEST_CMD, self).footer(output)

        st_cmd_footer = """
# Load plc interface database
dbLoadRecords("{modulename}-test.db", "MODVERSION=$(REQUIRE_{modulename}_VERSION)")
""".format(modulename    = self.modulename())

        self._append(st_cmd_footer, output)




def autosave_header(printer):
    return """# @field SAVEFILE_DIR
# @type  STRING
# The directory where autosave should save files

# @field REQUIRE_{modulename}_PATH
# @runtime YES
""".format(modulename = printer.modulename())


def autosave_footer(printer):
    return """
# Configure autosave
# Number of sequenced backup files to write
save_restoreSet_NumSeqFiles(1)

# Specify directories in which to search for request files
set_requestfile_path("$(REQUIRE_{modulename}_PATH)", "misc")

# Specify where the save files should be
set_savefile_path("$(SAVEFILE_DIR)", "")

# Specify what save files should be restored
set_pass0_restoreFile("{modulename}{flavor}.sav")

# Create monitor set
doAfterIocInit("create_monitor_set('{modulename}{flavor}.req', 1, '')")
""".format(modulename = printer.modulename(),
           flavor     = printer.flavor())




class AUTOSAVE_ST_CMD(ST_CMD):
    def __init__(self, **keyword_parameters):
        super(AUTOSAVE_ST_CMD, self).__init__(**keyword_parameters)


    @staticmethod
    def name():
        return "AUTOSAVE-ST-CMD"


    #
    # HEADER
    #
    def header(self, output, **keyword_parameters):
        super(AUTOSAVE_ST_CMD, self).header(output, **keyword_parameters)

        self._append(autosave_header(self), output)


    #
    # FOOTER
    #
    def footer(self, output):
        super(AUTOSAVE_ST_CMD, self).footer(output)

        self._append(autosave_footer(self), output)




class AUTOSAVE_ST_TEST_CMD(ST_TEST_CMD):
    def __init__(self):
        super(AUTOSAVE_ST_TEST_CMD, self).__init__()


    @staticmethod
    def name():
        return "AUTOSAVE-ST-TEST-CMD"


    #
    # HEADER
    #
    def header(self, output, **keyword_parameters):
        super(AUTOSAVE_ST_TEST_CMD, self).header(output, **keyword_parameters)

        self._append(autosave_header(self), output)


    #
    # FOOTER
    #
    def footer(self, output):
        super(AUTOSAVE_ST_TEST_CMD, self).footer(output)

        self._append(autosave_footer(self), output)
