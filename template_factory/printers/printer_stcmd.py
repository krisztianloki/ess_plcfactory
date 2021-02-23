from __future__ import absolute_import

""" Template Factory: Startup Snippet printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017,2018, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER, TemplatePrinterException
from tf_ifdef import STATUS_BLOCK, BASE_TYPE



def printer():
    return [ (ST_CMD.name(), ST_CMD),
             (IOCSH.name(), IOCSH),
             (AUTOSAVE_ST_CMD.name(), AUTOSAVE_ST_CMD),
             (AUTOSAVE_IOCSH.name(), AUTOSAVE_IOCSH),
             (ST_TEST_CMD.name(), ST_TEST_CMD),
             (TEST_IOCSH.name(), TEST_IOCSH),
             (AUTOSAVE_ST_TEST_CMD.name(), AUTOSAVE_ST_TEST_CMD),
             (AUTOSAVE_TEST_IOCSH.name(), AUTOSAVE_TEST_IOCSH) ]




class eee(object):
    @staticmethod
    def _extension():
        return "cmd"


    def modulename(self):
        return self.plcf("ext.eee_modulename()")


    def snippet(self):
        return self.plcf("ext.eee_snippet()")


    def _modversion(self):
        return "REQUIRE_{modulename}_VERSION".format(modulename = self.modulename())




class e3(object):
    @staticmethod
    def _extension():
        return "iocsh"


    def modulename(self):
        return self.plcf("ext.e3_modulename()")


    def snippet(self):
        return self.plcf("ext.e3_snippet()")


    def _modversion(self):
        return "{modulename}_VERSION".format(modulename = self.modulename())




class MACROS(object):
    def __init__(self):
        super(MACROS, self).__init__()
        self._root_macro = False
        self._macros     = []


    @staticmethod
    def macro_name(macro):
        return macro[2:-1]


    def macros(self):
        return self._macros


    def _declare_macros(self, if_def, output):
        if not self._root_macro:
            self._root_macro = True
            if self.raw_root_inst_slot()[0] == '$':
                self._macros.append(self.raw_root_inst_slot())
                self._append("""
# @field {}
# @type STRING
# PLC device name
""".format(self.macro_name(self.raw_root_inst_slot())), output)

        for macro in if_def.macros():
            self._macros.append(macro)
            self._append("""
# @field {macro}
# @type STRING
# {macro}
""".format(macro = self.macro_name(macro)), output)


    def _define_macros(self):
        if not self._macros:
            return ""

        return ", " + ", ".join(["{m}={v}".format(m = self.macro_name(m), v = m) for m in self._macros])




class ST_CMD(eee, MACROS, PRINTER):
    SIEMENS_PLC_PULSE = dict({"Pulse_100ms" : 100,
                              "Pulse_200ms" : 200,
                              "Pulse_400ms" : 400,
                              "Pulse_500ms" : 500,
                              "Pulse_800ms" : 800,
                              "Pulse_1s" : 1000,
                              "Pulse_1600ms" : 1600,
                              "Pulse_2s" : 200})

    def __init__(self):
        super(ST_CMD, self).__init__()
        self._opc = False


    @staticmethod
    def name():
        return "ST-CMD"


    @staticmethod
    def flavor():
        return ""


    def hostname(self):
        return self._ipaddr


    #
    # HEADER
    #
    def header(self, output, **keyword_parameters):
        super(ST_CMD, self).header(output, **keyword_parameters).add_filename_header(output, inst_slot = self.snippet(), template = False, extension = self._extension())
        self._opc = True if 'OPC' in keyword_parameters.get('PLC_TYPE', '') else False

        self._ipaddr = self.get_property("Hostname", None)
        if self._ipaddr == "":
            self._ipaddr = None

        self._recvtimeout = 3000
        plc_pulse = self.get_property("PLC-EPICS-COMMS: PLCPulse", "Pulse_200ms")
        try:
            plc_pulse = self.SIEMENS_PLC_PULSE[plc_pulse]
            self._recvtimeout = plc_pulse * 1.5
        except KeyError:
            raise TemplatePrinterException("Cannot interpret PLCPulse property: '{}'".format(plc_pulse))

        st_cmd_header = """
# @field IPADDR
# @{ipaddr}
# PLC IP address
{s7_vs_opc}
# @field {modversion}
# @runtime YES

# @field S7_PORT
# @runtime YES
# Can override S7 port with this

# @field MB_PORT
# @runtime YES
# Can override Modbus port with this
#COUNTER {status_cnt} = [PLCF#{status_cnt} + 10 * 2]

""".format(ipaddr     = "type STRING" if self._ipaddr is None else "runtime YES",
           modversion = self._modversion(),
           status_cnt = STATUS_BLOCK.counter_keyword(),
           s7_vs_opc  = """
# @field RECVTIMEOUT
# @type INTEGER
# PLC->EPICS receive timeout (ms), should be longer than frequency of PLC SND block trigger (REQ input)
""" if not self._opc else """
# @field PORT
# @type INTEGER
# PLC OPC-UA port

# @field PUBLISHING_INTERVAL
# @type INTEGER
# The OPC-UA publishing interval
""")

        self._append(st_cmd_header, output)


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_parameters):
        # Append macro 'declarations' to header part...
        self._declare_macros(if_def, output);

        status = if_def._status_block()
        if status is not None:
            self._append("#COUNTER {status_cnt} = [PLCF# {status_cnt} + {db_length}]".format(status_cnt = STATUS_BLOCK.counter_keyword(),
                                                                                             db_length  = status.length()), output)


    def _dbLoadRecords(self, plc_macro):
        return """#- Load plc interface database
dbLoadRecords("{modulename}.db", "{PLC_MACRO}={plcname}, MODVERSION=$({modversion}), S7_PORT=$(S7_PORT={s7_port}), MODBUS_PORT=$(MB_PORT={modbus_port}){macros}")""".format(
            PLC_MACRO   = plc_macro,
            plcname     = self.raw_root_inst_slot(),
            modulename  = self.modulename(),
            modversion  = self._modversion(),
            s7_port     = self.plcf("PLC-EPICS-COMMS: S7Port"),
            modbus_port = self.plcf("PLC-EPICS-COMMS: MBPort"),
            macros      = self._define_macros())


    #
    # FOOTER
    #
    def footer(self, output, **keyword_parameters):
        if self._opc:
            self._opc_footer(output, **keyword_parameters)
        else:
            self._s7_footer(output, **keyword_parameters)

    #
    # S7 + MODBUS FOOTER
    #
    def _s7_footer(self, output, **keyword_parameters):
        super(ST_CMD, self).footer(output, **keyword_parameters)

        st_cmd_footer = """
#- S7 port           : {s7drvport}
#- Input block size  : {insize} bytes
#- Output block size : 0 bytes
#- Endianness        : {endianness}
s7plcConfigure("{plcname}", {ipaddr}, $(S7_PORT={s7drvport}), {insize}, 0, {bigendian}, $(RECVTIMEOUT={recvtimeout}), 0)

#- Modbus port       : {modbusdrvport}
drvAsynIPPortConfigure("{plcname}", {ipaddr}:$(MB_PORT={modbusdrvport}), 0, 0, 1)

#- Link type         : TCP/IP (0)
#- The timeout is initialized to the (modbus) default if not specified
modbusInterposeConfig("{plcname}", 0, $(RECVTIMEOUT=0), 0)

#- Slave address     : 0
#- Function code     : 16 - Write Multiple Registers
#- Addressing        : Absolute (-1)
#- Data segment      : 20 words
drvModbusAsynConfigure("{plcname}write", "{plcname}", 0, 16, -1, 20, 0, 0, "S7-1500")

#- Slave address     : 0
#- Function code     : 3 - Read Multiple Registers
#- Addressing        : Relative ({start_offset})
#- Data segment      : 10 words
#- Polling           : 1000 msec
drvModbusAsynConfigure("{plcname}read", "{plcname}", 0, 3, {start_offset}, 10, 0, 1000, "S7-1500")

{dbloadrecords}
""".format(ipaddr        = "$(IPADDR)" if self._ipaddr is None else "$(IPADDR={})".format(self._ipaddr),
           recvtimeout   = self._recvtimeout,
           s7drvport     = self.plcf("PLC-EPICS-COMMS: S7Port"),
           modbusdrvport = self.plcf("PLC-EPICS-COMMS: MBPort"),
           insize        = self.plcf(STATUS_BLOCK.counter_keyword()),
           endianness    = self.plcf("PLC-EPICS-COMMS:Endianness"),
           bigendian     = self.plcf("1 if 'PLC-EPICS-COMMS:Endianness' == 'BigEndian' else 0"),
           modulename    = self.modulename(),
           modversion    = self._modversion(),
           plcname       = self.raw_root_inst_slot(),
           dbloadrecords = self._dbLoadRecords("PLCNAME"),
           start_offset  = self.plcf("EPICSToPLCDataBlockStartOffset")
          )

        self._append(st_cmd_footer, output)


    #
    # OPC-UA FOOTER
    #
    def _opc_footer(self, output, **keyword_parameters):
        super(ST_CMD, self).footer(output, **keyword_parameters)

        st_cmd_footer = """
#- Session name : {plcname}-session
opcuaCreateSession("{plcname}-session", "opc.tcp://$(IPADDR):$(PORT)")

#- Subscription       : {plcname}
#- Publising interval : $(PUBLISHING_INTERVAL)
opcuaCreateSubscription("{plcname}", "{plcname}-session", $(PUBLISHING_INTERVAL))

{dbloadrecords}
""".format(modulename    = self.modulename(),
           modversion    = self._modversion(),
           plcname       = self.raw_root_inst_slot(),
           dbloadrecords = self._dbLoadRecords("SUBSCRIPTION")
          )

        self._append(st_cmd_footer, output)




class IOCSH(e3, ST_CMD):
    def __init__(self):
        super(IOCSH, self).__init__()


    @staticmethod
    def name():
        return "IOCSH"




class ST_TEST_CMD(eee, MACROS, PRINTER):
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
        super(ST_TEST_CMD, self).header(output, **keyword_parameters).add_filename_header(output, inst_slot = self.snippet(), template = "test", extension = self._extension())

        st_cmd_header = """
# @field {modversion}
# @runtime YES

""".format(modversion = self._modversion())

        self._append(st_cmd_header, output)


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_parameters):
        # Append macro 'declarations' to header part...
        self._declare_macros(if_def, output);


    #
    # FOOTER
    #
    def footer(self, output, **keyword_parameters):
        super(ST_TEST_CMD, self).footer(output, **keyword_parameters)

        st_cmd_footer = """
#- Load plc interface database
dbLoadRecords("{modulename}-test.db", "MODVERSION=$({modversion}){macros}")
""".format(modulename = self.modulename(),
           modversion = self._modversion(),
           macros     = self._define_macros())

        self._append(st_cmd_footer, output)




class TEST_IOCSH(e3, ST_TEST_CMD):
    def __init__(self):
        super(TEST_IOCSH, self).__init__()


    @staticmethod
    def name():
        return "TEST-IOCSH"




def autosave_header(printer):
    return """# @field SAVEFILE_DIR
# @type  STRING
# The directory where autosave should save files

# @field REQUIRE_{modulename}_PATH
# @runtime YES
""".format(modulename = printer.modulename())



def e3_autosave_header(printer):
    return """# @field SAVEFILE_DIR
# @type STRING
# The directory where autosave should save files

# @field REQUIRE_IOC
# @runtime YES

# @field IOCNAME
# @runtime YES
"""



def autosave_footer(printer):
    return """
#- Configure autosave
#- Number of sequenced backup files to write
save_restoreSet_NumSeqFiles(1)

#- Specify directories in which to search for request files
set_requestfile_path("$(REQUIRE_{modulename}_PATH)", "misc")

#- Specify where the save files should be
set_savefile_path("$(SAVEFILE_DIR)", "")

#- Specify what save files should be restored
set_pass0_restoreFile("{modulename}{flavor}.sav")

#- Create monitor set
doAfterIocInit("create_monitor_set('{modulename}{flavor}.req', 1, '')")
""".format(modulename = printer.modulename(),
           flavor     = printer.flavor())




class AUTOSAVE_ST_CMD(ST_CMD):
    def __init__(self, **keyword_parameters):
        super(AUTOSAVE_ST_CMD, self).__init__(**keyword_parameters)
        self._has_params = False


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
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_parameters):
        super(AUTOSAVE_ST_CMD, self)._ifdef_body(if_def, output, **keyword_parameters)

        if not self._has_params:
            for src in if_def.interfaces():
                if isinstance(src, BASE_TYPE) and src.is_parameter():
                    self._has_params = True
                    break


    #
    # FOOTER
    #
    def footer(self, output, **keyword_parameters):
        super(AUTOSAVE_ST_CMD, self).footer(output, **keyword_parameters)

        if self._has_params:
            self._append(autosave_footer(self), output)




class AUTOSAVE_IOCSH(IOCSH):
    def __init__(self, **keyword_parameters):
        super(AUTOSAVE_IOCSH, self).__init__(**keyword_parameters)
        self._has_params = False


    @staticmethod
    def name():
        return "AUTOSAVE-IOCSH"


    #
    # HEADER
    #
    def header(self, output, **keyword_parameters):
        super(AUTOSAVE_IOCSH, self).header(output, **keyword_parameters)

        self._append(e3_autosave_header(self), output)


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_parameters):
        super(AUTOSAVE_IOCSH, self)._ifdef_body(if_def, output, **keyword_parameters)

        if not self._has_params:
            for src in if_def.interfaces():
                if isinstance(src, BASE_TYPE) and src.is_parameter():
                    self._has_params = True
                    break


    #
    # FOOTER
    #
    def footer(self, output, **keyword_parameters):
        super(AUTOSAVE_IOCSH, self).footer(output, **keyword_parameters)

        if self._has_params:
            self._append("""
#- Load autosave config
iocshLoad("${autosave_DIR}/autosave.iocsh", "AS_TOP = ${SAVEFILE_DIR=.}, IOCNAME = ${IOCNAME=${REQUIRE_IOC}}, NUM_SEQ = 1")
""", output)




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
    def footer(self, output, **keyword_parameters):
        super(AUTOSAVE_ST_TEST_CMD, self).footer(output, **keyword_parameters)

        self._append(autosave_footer(self), output)




class AUTOSAVE_TEST_IOCSH(TEST_IOCSH):
    def __init__(self):
        super(AUTOSAVE_TEST_IOCSH, self).__init__()


    @staticmethod
    def name():
        return "AUTOSAVE-TEST-IOCSH"


    #
    # HEADER
    #
    def header(self, output, **keyword_parameters):
        super(AUTOSAVE_TEST_IOCSH, self).header(output, **keyword_parameters)

        self._append(e3_autosave_header(self), output)


    #
    # FOOTER
    #
    def footer(self, output, **keyword_parameters):
        super(AUTOSAVE_TEST_IOCSH, self).footer(output, **keyword_parameters)

        self._append("""
#- Load autosave config
iocshLoad("${autosave_DIR}/autosave.iocsh", "AS_TOP = ${SAVEFILE_DIR=.}, IOCNAME = ${IOCNAME=${REQUIRE_IOC}-test}, NUM_SEQ = 1")
""", output)
