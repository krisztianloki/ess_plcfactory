""" Template Factory: Startup Snippet printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER



def printer():
    return [ (ST_CMD.name(), ST_CMD), (AUTOSAVE_ST_CMD.name(), AUTOSAVE_ST_CMD) ]




class ST_CMD(PRINTER):
    def __init__(self):
        PRINTER.__init__(self)


    @staticmethod
    def name():
        return "ST-CMD"


    #
    # HEADER
    #
    def header(self, output):
        PRINTER.header(self, output)

        st_cmd_header = """#FILENAME {startup}.cmd
# @field PLCNAME
# @type STRING
# asyn port name for the PLC

# @field IPADDR
# @type STRING
# PLC IP address

# @field RECVTIMEOUT
# @type INTEGER
# PLC->EPICS receive timeout (ms), should be longer than frequency of PLC SND block trigger (REQ input)
#COUNTER Counter2 = [PLCF#Counter2 + 10 * 2]

""".format(startup = self.plcf("ext.to_filename('INSTALLATION_SLOT'.lower())"))

        self._append(st_cmd_header, output)


    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)

        status = if_def._status_block()
        if status is not None:
            self._append("#COUNTER Counter2 = [PLCF# Counter2 + {db_length}]".format(db_length = status.length()), output)


    #
    # FOOTER
    #
    def footer(self, output):
        PRINTER.footer(self, output)

        st_cmd_footer = """
# Call the EEE module responsible for configuring IOC to PLC comms configuration
requireSnippet(s7plc-comms.cmd, "PLCNAME=$(PLCNAME), IPADDR=$(IPADDR), S7DRVPORT={s7drvport}, MODBUSDRVPORT={modbusdrvport}, INSIZE={insize}, OUTSIZE=0, BIGENDIAN={bigendian}, RECVTIMEOUT=$(RECVTIMEOUT)")

# Load plc interface database
dbLoadRecords("{modulename}.db", "PLCNAME=$(PLCNAME)")
""".format(s7drvport     = self.plcf("PLC-EPICS-COMMS: S7Port"),
           modbusdrvport = self.plcf("PLC-EPICS-COMMS: MBPort"),
           insize        = self.plcf("Counter2"),
           bigendian     = self.plcf("1 if 'PLC-EPICS-COMMS:Endianness' == 'BigEndian' else 0"),
           modulename    = self.plcf("ext.to_filename('INSTALLATION_SLOT'.lower())")
          )

        self._append(st_cmd_footer, output)




class AUTOSAVE_ST_CMD(ST_CMD):
    def __init__(self):
        PRINTER.__init__(self)


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
"""

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
set_pass0_restoreFile("{modulename}.sav")

# Create monitor set
create_monitor_set("{modulename}.req", 1, "")
""".format(modulename    = self.plcf("ext.to_filename('INSTALLATION_SLOT'.lower())")
          )

        self._append(st_cmd_footer, output)
