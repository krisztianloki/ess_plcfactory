""" Template Factory: EPICS printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


#TODO:
# convert EPICS to proper header/body/footer style


from . import PRINTER
from tf_ifdef import IfDefInternalError, SOURCE, VERBATIM, BLOCK, CMD_BLOCK, STATUS_BLOCK, BASE_TYPE



def printer():
    return [(EPICS.name(), EPICS), (EPICS_TEST.name(), EPICS_TEST), (UPLOAD_PARAMS.name(), UPLOAD_PARAMS)]




#
# EPICS output
#
class EPICS(PRINTER):
    def __init__(self, test = False):
        PRINTER.__init__(self, comments = True, show_origin = True, preserve_empty_lines = True)
        self._test   = test
        self._if_def = None


    def comment(self):
        return "#"


    @staticmethod
    def name():
        return "EPICS-DB"


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        PRINTER.header(self, output, **keyword_params).add_filename_header(output, "db")
        epics_db_header = """
record(stringin, "{root_inst_slot}:ModVersionR") {{
	field(DISP, "1")
	field(VAL,  "$(MODVERSION=N/A)")
	field(PINI, "YES")
}}

#########################################################
########## EPICS <-> PLC connection management ##########
#########################################################
record(asyn, "{root_inst_slot}:iAsyn") {{
	field(DTYP,	"asynRecordDevice")
	field(PORT,	"$(PLCNAME)")
}}
record(bi, "{root_inst_slot}:ModbusConnectedR") {{
	field(DESC,	"Shows if the MODBUS channel connected")
	field(INP,	"{root_inst_slot}:iAsyn.CNCT CP")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(ZSV,      "MAJOR")
	field(FLNK,	"{root_inst_slot}:CommsHashToPLCS")
}}
record(bi, "{root_inst_slot}:S7ConnectedR") {{
	field(DESC,	"Shows if the S7 channel is connected")
	field(SCAN,	"I/O Intr")
	field(DTYP,	"S7plc stat")
	field(INP,	"@$(PLCNAME)")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(ZSV,      "MAJOR")
}}
record(calcout, "{root_inst_slot}:iCalcConn") {{
	field(INPA,	"{root_inst_slot}:S7ConnectedR CP")
	field(INPB,	"{root_inst_slot}:ModbusConnectedR CP")
	field(CALC,	"A && B")
	field(OUT,	"{root_inst_slot}:ConnectedR PP")
}}
record(bi, "{root_inst_slot}:ConnectedR") {{
	field(DESC,	"Shows if the PLC is connected")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(ZSV,      "MAJOR")
}}
record(bi, "{root_inst_slot}:PLCHashCorrectR") {{
	field(DESC,	"Shows if the comms hash is correct")
	field(ONAM,	"Correct")
	field(ZNAM,	"Incorrect")
	field(ZSV,      "MAJOR")
}}
record(bi, "{root_inst_slot}:AliveR") {{
	alias("{root_inst_slot}:CommsOK")
	field(DESC,	"Shows if the PLC is sending heartbeats")
	field(ONAM,	"Alive")
	field(ZNAM,	"Not responding")
	field(ZSV,      "MAJOR")
}}
record(calcout, "{root_inst_slot}:iCheckHash") {{
	field(INPA,	"{root_inst_slot}:iCommsHashToPLC")
	field(INPB,	"{root_inst_slot}:CommsHashFromPLCR")
	field(CALC,	"A = B")
	field(OOPT,	"On Change")
	field(OUT,	"{root_inst_slot}:PLCHashCorrectR PP")
}}
record(bi, "{root_inst_slot}:iOne") {{
	field(DISP,	"1")
	field(PINI,	"YES")
	field(VAL,	"1")
}}
record(bo, "{root_inst_slot}:iGotHeartbeat") {{
	field(DOL,	"{root_inst_slot}:iOne")
	field(OMSL,	"closed_loop")
	field(OUT,	"{root_inst_slot}:iKickAlive PP")
}}
record(bo, "{root_inst_slot}:iKickAlive") {{
	field(HIGH,	"5")
	field(OUT,	"{root_inst_slot}:AliveR PP")
}}

########################################################
########## EPICS -> PLC comms management data ##########
########################################################
record(ao, "{root_inst_slot}:iCommsHashToPLC") {{
	field(DISP,	"1")
	field(PINI,	"YES")
	field(VAL,	"#HASH")
}}
record(ao, "{root_inst_slot}:CommsHashToPLCS") {{
	field(DESC,	"Sends comms hash to PLC")
	field(SCAN,	"1 second")
	field(DTYP,	"asynInt32")
	field(OUT,	"@asyn($(PLCNAME)write, [PLCF#EPICSToPLCDataBlockStartOffset], 100)INT32_[PLCF#'BE' if 'PLC-EPICS-COMMS:Endianness' == 'BigEndian' else 'LE']")
	field(OMSL,	"closed_loop")
	field(DOL,	"{root_inst_slot}:iCommsHashToPLC")
	field(DISV,	"0")
	field(SDIS,	"{root_inst_slot}:ModbusConnectedR")
}}
record(calc, "{root_inst_slot}:iHeartbeatToPLC") {{
	field(SCAN,	"1 second")
	field(INPA,	"{root_inst_slot}:iHeartbeatToPLC.VAL")
	field(CALC,	"(A >= 32000)? 0 : A + 1")
	field(FLNK,	"{root_inst_slot}:HeartbeatToPLCS")
	field(DISV,	"0")
	field(SDIS,	"{root_inst_slot}:ModbusConnectedR")
}}
record(ao, "{root_inst_slot}:HeartbeatToPLCS") {{
	field(DESC,	"Sends heartbeat to PLC")
	field(DTYP,	"asynInt32")
	field(OUT,	"@asyn($(PLCNAME)write, [PLCF#EPICSToPLCDataBlockStartOffset + 2], 100)")
	field(OMSL,	"closed_loop")
	field(DOL,	"{root_inst_slot}:iHeartbeatToPLC.VAL")
	field(OIF,	"Full")
	field(DRVL,	"0")
	field(DRVH,	"32000")
	field(DISV,	"0")
	field(SDIS,	"{root_inst_slot}:ModbusConnectedR")
}}

########################################################
########## PLC -> EPICS comms management data ##########
########################################################
record(ai, "{root_inst_slot}:CommsHashFromPLCR") {{
	field(DESC,	"Comms hash from PLC")
	field(SCAN,	"I/O Intr")
	field(DTYP,	"S7plc")
	field(INP,	"@$(PLCNAME)/[PLCF#PLCToEPICSDataBlockStartOffset] T=INT32")
	field(FLNK,	"{root_inst_slot}:iCheckHash")
}}
record(ai, "{root_inst_slot}:HeartbeatFromPLCR") {{
	field(DESC,	"Heartbeat from PLC")
	field(SCAN,	"I/O Intr")
	field(DTYP,	"S7plc")
	field(INP,	"@$(PLCNAME)/[PLCF#(PLCToEPICSDataBlockStartOffset + 4)] T=INT16")
	field(FLNK,	"{root_inst_slot}:iGotHeartbeat")
	field(DISS,	"INVALID")
	field(DISV,	"0")
	field(SDIS,	"{root_inst_slot}:PLCHashCorrectR")
}}

#COUNTER {cmd_cnt} = [PLCF#{cmd_cnt} + 10];
#COUNTER {status_cnt} = [PLCF#{status_cnt} + 10];
""".format(inst_slot       = self.inst_slot(),
           root_inst_slot  = self.root_inst_slot(),
           cmd_cnt         = CMD_BLOCK.counter_keyword(),
           status_cnt      = STATUS_BLOCK.counter_keyword())

        self._append(epics_db_header, output)
        return self


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output):
        self._if_def = if_def
        self._output = output

        self._append("""
##########
########## {inst_slot} ##########
##########
""".format(inst_slot = self.inst_slot()))
        self._body_verboseheader(if_def._cmd_block(), output)
        self._body_verboseheader(if_def._param_block(), output)
        self._body_verboseheader(if_def._status_block(), output)

        self._append("""##########

""")

        self._params = []
        for src in if_def.interfaces():
            if isinstance(src, BLOCK):
                self._body_block(src, output)
            elif isinstance(src, BASE_TYPE):
                self._body_var(src, output)
            elif isinstance(src, VERBATIM):
                self._append((src.source(), str(src)))
            elif isinstance(src, SOURCE):
                self._body_source(src, output)
            else:
                self._append(src.toEPICS(inst_slot = if_def.inst_slot(), test = self._test))

        self._body_end_param(if_def, output)
        self._append("\n\n")
        self._body_end_cmd(if_def, output)
        self._body_end_status(if_def, output)


    def _body_block(self, block, output):
        if block.is_status_block():
            comment = "PLC   -> EPICS status  "
        elif block.is_cmd_block():
            comment = "EPICS -> PLC commands  "
        elif block.is_param_block():
            comment = "EPICS -> PLC parameters"
        else:
            raise IfDefInternalError("Unsupported block type: " + block.type())

        self._append((block.source(), """
##########
########## {inst_slot} {dir} ##########
##########
""".format(inst_slot = self.inst_slot(),
           dir = comment)))


    def _body_var(self, var, output):
        self._append(var.toEPICS(inst_slot = self._if_def.inst_slot(), test = self._test))
        if not var.is_parameter():
            return

        self._params.extend([ var ])


    def _body_source(self, var, output):
        self._append(var)


    def _body_end_param(self, if_def, output):
        if len(self._params) == 0:
            return

        fo_name = '_UploadParamS{foc}-FO'
        foc = 0
        lnk = 1
        for param in self._params:
            if lnk == 6:
                foc += 1
                self._append("""	field(LNK{lnk}, "{inst_slot}:{upload}")
}}
""".format(lnk       = str(lnk),
           inst_slot = self.inst_slot(),
           upload    = fo_name.format(foc = str(foc))), output)
                lnk = 1

            if lnk == 1:
                self._append("""record(fanout, "{inst_slot}:{upload}") {{
""".format(inst_slot = self.inst_slot(),
           upload    = 'UploadParametersS' if foc == 0 else fo_name.format(foc = str(foc))), output)

            self._append("""	field(LNK{lnk}, "{inst_slot}:{param}")
""".format(lnk       = str(lnk),
           inst_slot = self.inst_slot(),
           param     = param.pv_name()), output)

            lnk += 1

        self._append("}", output)


    def _body_end_cmd(self, if_def, output):
        self._body_end(CMD_BLOCK.counter_keyword(), if_def.to_plc_words_length(), output)


    def _body_end_status(self, if_def, output):
        self._body_end(STATUS_BLOCK.counter_keyword(), if_def.from_plc_words_length(), output)


    def _body_end(self, counter_keyword, plc_db_length, output):
        if self._test:
            return

        counter_template = "#COUNTER {counter} = [PLCF# {counter} + {plc_db_length}]\n"

        self._append(counter_template.format(counter = counter_keyword, plc_db_length = plc_db_length))


    def _body_verboseheader(self, block, output):
        if block is None or self._test:
            return

        self._append("########## {keyword}: {length}\n".format(keyword = block.length_keyword(), length = block.length() // 2))




class EPICS_TEST(EPICS):
    def __init__(self):
        EPICS.__init__(self, test = True)


    @staticmethod
    def name():
        return "EPICS-TEST-DB"


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        PRINTER.header(self, output, **keyword_params).add_filename_header(output, "db")
        epics_db_header = """
#########################################################
########## EPICS <-> PLC connection management ##########
#########################################################
record(bi, "{root_inst_slot}:ModbusConnectedR") {{
	field(DESC,	"Shows if the MODBUS channel connected")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(ZSV,      "MAJOR")
	field(VAL,	"1")
	field(PINI,	"YES")
	field(FLNK,	"{root_inst_slot}:CommsHashToPLCS")
}}
record(bi, "{root_inst_slot}:S7ConnectedR") {{
	field(DESC,	"Shows if the S7 channel is connected")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(ZSV,      "MAJOR")
	field(VAL,	"1")
	field(PINI,	"YES")
}}
record(calcout, "{root_inst_slot}:iCalcConn") {{
	field(INPA,	"{root_inst_slot}:S7ConnectedR CP")
	field(INPB,	"{root_inst_slot}:ModbusConnectedR CP")
	field(CALC,	"A && B")
	field(OUT,	"{root_inst_slot}:ConnectedR PP")
}}
record(bi, "{root_inst_slot}:ConnectedR") {{
	field(DESC,	"Shows if the PLC is connected")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(ZSV,      "MAJOR")
}}
record(bi, "{root_inst_slot}:PLCHashCorrectR") {{
	field(DESC,	"Shows if the comms hash is correct")
	field(ONAM,	"Correct")
	field(ZNAM,	"Incorrect")
	field(ZSV,      "MAJOR")
}}
record(bi, "{root_inst_slot}:AliveR") {{
	field(DESC,	"Shows if the PLC is sending heartbeats")
	field(ONAM,	"Alive")
	field(ZNAM,	"Not responding")
	field(ZSV,      "MAJOR")
}}
record(calcout, "{root_inst_slot}:iCheckHash") {{
	field(INPA,	"{root_inst_slot}:iCommsHashToPLC")
	field(INPB,	"{root_inst_slot}:CommsHashFromPLCR")
	field(CALC,	"A = B")
	field(OOPT,	"On Change")
	field(OUT,	"{root_inst_slot}:PLCHashCorrectR PP")
}}
record(bi, "{root_inst_slot}:iOne") {{
	field(DISP,	"1")
	field(PINI,	"YES")
	field(VAL,	"1")
}}
record(bo, "{root_inst_slot}:iGotHeartbeat") {{
	field(DOL,	"{root_inst_slot}:iOne")
	field(OMSL,	"closed_loop")
	field(OUT,	"{root_inst_slot}:iKickAlive PP")
}}
record(bo, "{root_inst_slot}:iKickAlive") {{
	field(HIGH,	"5")
	field(OUT,	"{root_inst_slot}:AliveR PP")
}}

########################################################
########## EPICS -> PLC comms management data ##########
########################################################
record(ao, "{root_inst_slot}:iCommsHashToPLC") {{
	field(DISP,	"1")
	field(PINI,	"YES")
	field(VAL,	"#HASH")
}}
record(ao, "{root_inst_slot}:CommsHashToPLCS") {{
	field(DESC,	"Sends comms hash to PLC")
	field(OMSL,	"closed_loop")
	field(DOL,	"{root_inst_slot}:iCommsHashToPLC")
	field(DISV,	"0")
	field(SDIS,	"{root_inst_slot}:ConnectedR")
}}
record(calc, "{root_inst_slot}:iHeartbeatToPLC") {{
	field(SCAN,	"1 second")
	field(INPA,	"{root_inst_slot}:iHeartbeatToPLC.VAL")
	field(CALC,	"(A >= 32000)? 0 : A + 1")
	field(FLNK,	"{root_inst_slot}:HeartbeatToPLCS")
	field(DISV,	"0")
	field(SDIS,	"{root_inst_slot}:ConnectedR")
}}
record(ao, "{root_inst_slot}:HeartbeatToPLCS") {{
	field(DESC,	"Sends heartbeat to PLC")
	field(OMSL,	"closed_loop")
	field(DOL,	"{root_inst_slot}:iHeartbeatToPLC.VAL")
	field(OIF,	"Full")
	field(DRVL,	"0")
	field(DRVH,	"32000")
}}

########################################################
########## PLC -> EPICS comms management data ##########
########################################################
record(ai, "{root_inst_slot}:CommsHashFromPLCR") {{
	field(DESC,	"Comms hash from PLC")
	field(SCAN,	"1 second")
	field(INP,	"{root_inst_slot}:iCommsHashToPLC")
	field(FLNK,	"{root_inst_slot}:iCheckHash")
}}
record(ai, "{root_inst_slot}:HeartbeatFromPLCR") {{
	field(DESC,	"Heartbeat from PLC")
	field(INP,	"{root_inst_slot}:iHeartbeatToPLC.VAL CP")
	field(FLNK,	"{root_inst_slot}:iGotHeartbeat")
}}

""".format(inst_slot      = self.inst_slot(),
           root_inst_slot = self.root_inst_slot())

        self._append(epics_db_header, output)
        return self


class UPLOAD_PARAMS(PRINTER):
    def __init__(self):
        PRINTER.__init__(self)

        self._fo_name = '_UploadParamS{foc}-FO'
        self._foc = 0
        self._lnk = 1


    @staticmethod
    def name():
        return "UPLOAD-PARAMS"


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        PRINTER.header(self, output, **keyword_params).add_filename_header(output, "db")
        epics_db_header = """
record(fanout, "{root_inst_slot}:UploadParametersS") {{
""".format(inst_slot      = self.inst_slot(),
           root_inst_slot = self.root_inst_slot())

        self._append(epics_db_header, output)
        return self


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output):
        self._output = output

        self._params = []
        for src in if_def.interfaces():
            if isinstance(src, BLOCK) and src.is_param_block():
                self._LNKx(output)


    def _LNKx(self, output):
        if self._lnk == 6:
            self._foc += 1
            self._append("""	field(LNK{lnk}, "{root_inst_slot}:{upload}")
}}
""".format(lnk       = str(self._lnk),
           root_inst_slot = self.root_inst_slot(),
           upload    = self._fo_name.format(foc = str(self._foc))), output)
            self._lnk = 1

        if self._lnk == 1 and self._foc:
            self._append("""record(fanout, "{root_inst_slot}:{upload}") {{
""".format(root_inst_slot = self.root_inst_slot(),
           upload    = 'UploadParametersS' if self._foc == 0 else self._fo_name.format(foc = str(self._foc))), output)

        self._append("""	field(LNK{lnk}, "{inst_slot}:UploadParametersS")
""".format(lnk       = str(self._lnk),
           inst_slot = self.inst_slot()), output)

        self._lnk += 1


    #
    # FOOTER
    #
    def footer(self, output):
        PRINTER.footer(self, output)
        self._append("}", output)
