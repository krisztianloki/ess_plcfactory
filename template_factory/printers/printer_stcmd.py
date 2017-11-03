""" Template Factory: Startup Snippet printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER



def printer():
    return (ST_CMD.name(), ST_CMD)




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

dbLoadRecords("{database}.db", "PLCNAME=$(PLCNAME)")
""".format(s7drvport     = self.plcf("PLC-EPICS-COMMS: S7Port"),
           modbusdrvport = self.plcf("PLC-EPICS-COMMS: MBPort"),
           insize        = self.plcf("Counter2"),
           bigendian     = self.plcf("1 if 'PLC-EPICS-COMMS:Endianness' == 'BigEndian' else 0"),
           database      = self.plcf("ext.to_filename('INSTALLATION_SLOT'.lower())")
          )

        self._append(st_cmd_footer, output)
