""" Template Factory: EPICS printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


#TODO:
# convert EPICS to proper header/body/footer style


from printers import PRINTER
from tf_ifdef import IfDefInternalError, SOURCE, VERBATIM, BLOCK, CMD_BLOCK, STATUS_BLOCK, BASE_TYPE



def printer():
    return (EPICS.name(), EPICS)




#
# EPICS output
#
class EPICS(PRINTER):
    def __init__(self):
        PRINTER.__init__(self, comments = True, show_origin = True, preserve_empty_lines = True)


    def comment(self):
        return "#"


    @staticmethod
    def name():
        return "EPICS-DB"


    #
    # HEADER
    #
    def header(self, output):
        PRINTER.header(self, output)
        epics_db_header = """#FILENAME {inst_slot}-[PLCF#TEMPLATE]-[PLCF#TIMESTAMP].db
#########################################################
########## EPICS <-> PLC connection management ##########
#########################################################
record(asyn, "{inst_slot}:iAsyn") {{
	field(DTYP,	"asynRecordDevice")
	field(PORT,	"$(PLCNAME)")
}}
record(bi, "{inst_slot}:Connected") {{
	field(INP,	"{inst_slot}:iAsyn.CNCT CP")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(FLNK,	"{inst_slot}:CommsGeneratedHashEPICSToPLC")
}}
record(bi, "{inst_slot}:PLCHashCorrect") {{
	field(ONAM,	"Correct")
	field(ZNAM,	"Incorrect")
}}
record(bi, "{inst_slot}:Alive") {{
	field(ONAM,	"Alive")
	field(ZNAM,	"Not responding")
}}
record(calcout, "{inst_slot}:iCheckHash") {{
	field(INPA,	"{inst_slot}:iCommsGeneratedHashEPICSToPLC")
	field(INPB,	"{inst_slot}:CommsGeneratedHashPLCToEPICS")
	field(CALC,	"A = B")
	field(OOPT,	"On Change")
	field(OUT,	"{inst_slot}:PLCHashCorrect PP")
}}
record(bi, "{inst_slot}:one") {{
	field(DISP,	"1")
	field(PINI,	"YES")
	field(VAL,	"1")
}}
record(bo, "{inst_slot}:iGotHeartbeat") {{
	field(DOL,	"{inst_slot}:one")
	field(OMSL,	"closed_loop")
	field(OUT,	"{inst_slot}:iKickAlive PP")
}}
record(bo, "{inst_slot}:iKickAlive") {{
	field(HIGH,	"5")
	field(OUT,	"{inst_slot}:Alive PP")
}}
########################################################
########## EPICS -> PLC comms management data ##########
########################################################
record(ao, "{inst_slot}:iCommsGeneratedHashEPICSToPLC") {{
	field(DISP,	"1")
	field(PINI,	"YES")
	field(VAL,	"#HASH")
}}
record(ao, "{inst_slot}:CommsGeneratedHashEPICSToPLC") {{
	field(SCAN,	"1 second")
	field(DTYP,	"asynInt32")
	field(OUT,	"@asyn($(PLCNAME)write, 0, 100)INT32_BE")
	field(OMSL,	"closed_loop")
	field(DOL,	"{inst_slot}:iCommsGeneratedHashEPICSToPLC")
}}
record(calc, "{inst_slot}:iHeartbeatEPICSToPLCCalc") {{
	field(SCAN,	"1 second")
	field(INPA,	"{inst_slot}:iHeartbeatEPICSToPLCCalc.VAL")
	field(CALC,	"(A >= 32000)? 0 : A + 1")
	field(FLNK,	"{inst_slot}:HeartbeatEPICSToPLC")
}}
record(ao, "{inst_slot}:HeartbeatEPICSToPLC") {{
	field(DTYP,	"asynInt32")
	field(OUT,	"@asyn($(PLCNAME)write, 2, 100)")
	field(OMSL,	"closed_loop")
	field(DOL,	"{inst_slot}:iHeartbeatEPICSToPLCCalc.VAL")
	field(OIF,	"Full")
	field(DRVL,	"0")
	field(DRVH,	"32000")
}}

########################################################
########## PLC -> EPICS comms management data ##########
########################################################
record(ai, "{inst_slot}:CommsGeneratedHashPLCToEPICS") {{
	field(SCAN,	"I/O Intr")
	field(DTYP,	"S7plc")
	field(INP,	"@$(PLCNAME)/[PLCF#PLCToEPICSDataBlockStartOffset] T=INT32")
	field(FLNK,	"{inst_slot}:iCheckHash")
}}
record(ai, "{inst_slot}:HeartbeatPLCToEPICS") {{
	field(SCAN,	"I/O Intr")
	field(DTYP,	"S7plc")
	field(INP,	"@$(PLCNAME)/[PLCF#(PLCToEPICSDataBlockStartOffset + 4)] T=INT16")
	field(FLNK,	"{inst_slot}:iGotHeartbeat")
}}

#COUNTER Counter1 = [PLCF#Counter1 + 10];
#COUNTER Counter2 = [PLCF#Counter2 + 10];
""".format(inst_slot = self.inst_slot())

        self._append(epics_db_header, output)
        return self


    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)
        self._output = output

        self._append("""
##########
########## [PLCF#INSTALLATION_SLOT] ##########
##########
""")
        self._body_verboseheader(if_def._cmd_block(), output)
        self._body_verboseheader(if_def._param_block(), output)
        self._body_verboseheader(if_def._status_block(), output)

        self._append("""##########

""")

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
                self._append(src.toEPICS())

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
########## [PLCF#INSTALLATION_SLOT] {dir} ##########
##########
""".format(dir = comment)))


    def _body_var(self, var, output):
        self._append(var.toEPICS())


    def _body_source(self, var, output):
        self._append(var)


    def _body_end_cmd(self, if_def, output):
        self._body_end(CMD_BLOCK.counter_keyword(), if_def.to_plc_words_length(), output)


    def _body_end_status(self, if_def, output):
        self._body_end(STATUS_BLOCK.counter_keyword(), if_def.from_plc_words_length(), output)


    def _body_end(self, counter_keyword, plc_db_length, output):
        counter_template = "#COUNTER {counter} = [PLCF# {counter} + {plc_db_length}]\n"

        self._append(counter_template.format(counter = counter_keyword, plc_db_length = plc_db_length))


    def _body_verboseheader(self, block, output):
        if block is None:
            return

        self._append("########## {keyword}: {length}\n".format(keyword = block.length_keyword(), length = block.length() // 2))
