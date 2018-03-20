""" Template Factory: Startup Snippet printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER
from tf_ifdef import STATUS_BLOCK



def printer():
    return [ (ST_CMD.name(), ST_CMD), (AUTOSAVE_ST_CMD.name(), AUTOSAVE_ST_CMD), (ST_TEST_CMD.name(), ST_TEST_CMD), (AUTOSAVE_ST_TEST_CMD.name(), AUTOSAVE_ST_TEST_CMD) ]




class ST_CMD(PRINTER):
    def __init__(self, test = False):
        PRINTER.__init__(self)
        self._test = test


    @staticmethod
    def name():
        return "ST-CMD"


    def _modulename(self):
        return self.plcf("ext.eee_modulename()")

    #
    # HEADER
    #
    def header(self, output):
        PRINTER.header(self, output)

        st_cmd_header = """#FILENAME {startup}{test}-[PLCF#TIMESTAMP].cmd
# @field PLCNAME
# @type STRING
# asyn port name for the PLC

# @field IPADDR
# @type STRING
# PLC IP address

# @field RECVTIMEOUT
# @type INTEGER
# PLC->EPICS receive timeout (ms), should be longer than frequency of PLC SND block trigger (REQ input)

# @field REQUIRE_{modulename}_VERSION
# @runtime YES
#COUNTER {status_cnt} = [PLCF#{status_cnt} + 10 * 2]

""".format(startup    = self._modulename(),
           test       = "" if not self._test else "-test",
           modulename = self._modulename(),
           status_cnt = STATUS_BLOCK.counter_keyword())

        self._append(st_cmd_header, output)


    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)

        status = if_def._status_block()
        if status is not None:
            self._append("#COUNTER {status_cnt} = [PLCF# {status_cnt} + {db_length}]".format(status_cnt = STATUS_BLOCK.counter_keyword(),
                                                                                             db_length = status.length()), output)


    #
    # FOOTER
    #
    def footer(self, output):
        PRINTER.footer(self, output)

        if not self._test:
            st_cmd_footer = """
# Call the EEE module responsible for configuring IOC to PLC comms configuration
requireSnippet(s7plc-comms.cmd, "PLCNAME=$(PLCNAME), IPADDR=$(IPADDR), S7DRVPORT={s7drvport}, MODBUSDRVPORT={modbusdrvport}, INSIZE={insize}, OUTSIZE=0, BIGENDIAN={bigendian}, RECVTIMEOUT=$(RECVTIMEOUT)")

# Load plc interface database
dbLoadRecords("{modulename}.db", "PLCNAME=$(PLCNAME), MODVERSION=$(REQUIRE_{modulename}_VERSION)")
""".format(s7drvport     = self.plcf("PLC-EPICS-COMMS: S7Port"),
           modbusdrvport = self.plcf("PLC-EPICS-COMMS: MBPort"),
           insize        = self.plcf(STATUS_BLOCK.counter_keyword()),
           bigendian     = self.plcf("1 if 'PLC-EPICS-COMMS:Endianness' == 'BigEndian' else 0"),
           modulename    = self._modulename()
          )
        else:
            st_cmd_footer = """
# Load plc interface database
dbLoadRecords("{modulename}-test.db", "PLCNAME=$(PLCNAME)")
""".format(modulename    = self._modulename())

        self._append(st_cmd_footer, output)




class ST_TEST_CMD(ST_CMD):
    def __init__(self):
        ST_CMD.__init__(self, test = True)


    @staticmethod
    def name():
        return "ST-TEST-CMD"




class AUTOSAVE_ST_CMD(ST_CMD):
    def __init__(self, **keyword_parameters):
        ST_CMD.__init__(self, **keyword_parameters)


    @staticmethod
    def name():
        return "AUTOSAVE-ST-CMD"


    #
    # HEADER
    #
    def header(self, output):
        ST_CMD.header(self, output)

        st_cmd_header = """# @field SAVEFILE_PATH
# @type  STRING
# The path where autosave should save files

# @field REQUIRE_{modulename}_PATH
# @runtime YES
""".format(modulename    = self._modulename())

        self._append(st_cmd_header, output)


    #
    # FOOTER
    #
    def footer(self, output):
        ST_CMD.footer(self, output)

        st_cmd_footer = """
# Configure autosave
# Number of sequenced backup files to write
save_restoreSet_NumSeqFiles(1)

# Specify directories in which to search for request files
set_requestfile_path("$(REQUIRE_{modulename}_PATH)", "misc")

# Specify where the save files should be
set_savefile_path("$(SAVEFILE_PATH)", "")

# Specify what save files should be restored
set_pass0_restoreFile("{modulename}{test}.sav")

# Create monitor set
create_monitor_set("{modulename}{test}.req", 1, "")
""".format(modulename    = self._modulename(),
           test          = "" if not self._test else "-test")

        self._append(st_cmd_footer, output)




class AUTOSAVE_ST_TEST_CMD(AUTOSAVE_ST_CMD):
    def __init__(self):
        AUTOSAVE_ST_CMD.__init__(self, test = True)


    @staticmethod
    def name():
        return "AUTOSAVE-ST-TEST-CMD"
