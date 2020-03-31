from __future__ import division
from __future__ import absolute_import

""" Template Factory: EPICS printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


from . import PRINTER
from tf_ifdef import IfDefInternalError, SOURCE, VERBATIM, BLOCK, CMD_BLOCK, STATUS_BLOCK, BASE_TYPE



def printer():
    return [ (EPICS.name(), EPICS),
             (EPICS_TEST.name(), EPICS_TEST),
             (EPICS_OPC.name(), EPICS_OPC) ]




class EPICS_BASE(PRINTER):
    DISABLE_TEMPLATE = """
	field(DISS, "INVALID")
	field(DISV, "0")
	field(SDIS, "[PLCF#ROOT_INSTALLATION_SLOT]:PLCHashCorrectR{CP}")"""

    INPV_TEMPLATE  = """record({recordtype}, "{pv_name}")
{{{alias}
	field(SCAN, "I/O Intr")
	field(DTYP, "{dtyp}")
	field({inp_out}){pv_extra}
}}

"""

    OUTPV_TEMPLATE = """record({recordtype}, "{pv_name}")
{{{alias}
	field(DTYP, "{dtyp}")
	field({inp_out}){pv_extra}
}}

"""
    TEST_PV_TEMPLATE = """record({recordtype}, "{pv_name}")
{{{alias}{pv_extra}
}}

"""

    PLC_INFO_FIELDS = """
	info("plc_datablock", "{plc_datablock}")
	info("plc_variable", "{plc_variable}")"""


    UPLOAD_PARAMS = "UploadParametersS"

    LNKx    = [ '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F' ]
    MAX_LNK = len(LNKx)


    def __init__(self, test = False):
        super(EPICS_BASE, self).__init__(comments = True, show_origin = True, preserve_empty_lines = True)
        self._if_def = None
        self.DISABLE_TEMPLATE = self.DISABLE_TEMPLATE.format(CP = " CP" if test else "")

        self._fo_name = '_UploadParamS{foc}-FO'
        self._params  = []
        self._uploads = []


    def comment(self):
        return "#"


    def inpv_template(self, test = False):
        if test:
            return self.TEST_PV_TEMPLATE
        return self.INPV_TEMPLATE


    def outpv_template(self, test = False):
        if test:
            return self.TEST_PV_TEMPLATE
        return self.OUTPV_TEMPLATE


    def _body_register_block_printer(self, block):
        if block is None:
            return

        block.register_printer(self)


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
        self._append(self._toEPICS(var))
        if not var.is_parameter():
            return

        self._params.append(var)


    def _body_source(self, var, output):
        self._append(var)


    def _body_end_param(self, if_def, output):
        if len(self._params) == 0:
            return

        self._uploads.append("{}:{}".format(self.inst_slot(if_def), self.UPLOAD_PARAMS))

        self._gen_param_fanouts(self._params, self.inst_slot(if_def), output)


    def _gen_param_fanouts(self, param_list, inst_slot, output, footer = False):
        foc = 0
        lnk = 0

        for upload in param_list:
            if lnk == self.MAX_LNK:
                foc += 1
                self._append("""	field(FLNK, "{inst_slot}:{upload}")
}}
""".format(inst_slot = inst_slot,
           upload    = self._fo_name.format(foc = foc)), output)

                lnk = 0

            if lnk == 0:
                self._append("""record(fanout, "{inst_slot}:{upload}")
{{
""".format(inst_slot = inst_slot,
           upload    = self.UPLOAD_PARAMS if foc == 0 else self._fo_name.format(foc = foc)), output)

            self._append("""	field(LNK{lnk}, "{upload}")
""".format(lnk       = self.LNKx[lnk],
           upload    = upload if footer else "{}:{}".format(inst_slot, upload.pv_name())), output)

            lnk += 1

        if footer and foc == 0 and lnk == 0:
            # Create an empty UploadParamsS if there are no parameters
            epics_db_footer = """
record(fanout, "{inst_slot}:{upload}")
{{
""".format(inst_slot = inst_slot,
           upload    = self.UPLOAD_PARAMS)

            self._append(epics_db_footer, output)

        self._append("}", output)



    #
    # FOOTER
    #
    def footer(self, output, **keyword_params):
        super(EPICS_BASE, self).footer(output, **keyword_params)

        self._gen_param_fanouts(self._uploads, self.root_inst_slot(), output, True)




#
# EPICS output
#
class EPICS(EPICS_BASE):
    def __init__(self, test = False):
        super(EPICS, self).__init__(test)
        self._test   = test


    @staticmethod
    def name():
        return "EPICS-DB"


    def field_inp(self, inst_io, offset, dtyp_var_type, link_extra):
        return '@{inst_io}/{offset} T={dtyp_var_type}{link_extra}'.format(inst_io       = inst_io,
                                                                          offset        = offset,
                                                                          dtyp_var_type = dtyp_var_type,
                                                                          link_extra    = link_extra)


    def field_out(self, inst_io, offset, dtyp_var_type, link_extra):
        return '@{inst_io}($(PLCNAME)write, {offset}, {link_extra}){dtyp_var_type}'.format(inst_io       = inst_io,
                                                                                           offset        = offset,
                                                                                           dtyp_var_type = dtyp_var_type,
                                                                                           link_extra    = link_extra)


    def _toEPICS(self, var):
        pv_extra = self.DISABLE_TEMPLATE + var.build_pv_extra() + EPICS_BASE.PLC_INFO_FIELDS.format(plc_datablock = self._if_def.DEFAULT_DATABLOCK_NAME,
                                                                                                    plc_variable  = var.name())
        if var.is_parameter() or self._test:
            pv_extra = pv_extra + """
	info(autosaveFields_pass0, "VAL")"""

        return (var.source(),
                var.pv_template(test = self._test).format(recordtype = var.pv_type(),
                                                          pv_name    = var._build_pv_name(self._if_def.inst_slot()),
                                                          alias      = var._build_pv_alias(self._if_def.inst_slot()),
                                                          dtyp       = var.dtyp(),
                                                          inp_out    = var.inp_out(inst_io       = var.inst_io(),
                                                                                   offset        = var.link_offset(),
                                                                                   dtyp_var_type = var.endian_correct_dtyp_var_type(),
                                                                                   link_extra    = var.link_extra() + var._get_user_link_extra()),
                                                          pv_extra   = pv_extra))


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        super(EPICS, self).header(output, **keyword_params).add_filename_header(output, extension = "db")
        epics_db_header = """
record(stringin, "{root_inst_slot}:ModVersionR")
{{
	field(DISP,	"1")
	field(VAL,	"$(MODVERSION=N/A)")
	field(PINI,	"YES")
}}

record(stringin, "{root_inst_slot}:PLCFCommitR")
{{
	field(DISP,	"1")
#{plcf_commit}
	field(VAL,	"{plcf_commit_39}")
	field(PINI,	"YES")
	info("plcf_commit", "{plcf_commit}")
}}

#########################################################
########## EPICS <-> PLC connection management ##########
#########################################################
record(asyn, "{root_inst_slot}:iAsyn")
{{
	field(DTYP,	"asynRecordDevice")
	field(PORT,	"$(PLCNAME)")
}}
record(bi, "{root_inst_slot}:ModbusConnectedR")
{{
	field(DESC,	"Shows if the MODBUS channel connected")
	field(INP,	"{root_inst_slot}:iAsyn.CNCT CP")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(ZSV,      "MAJOR")
	field(FLNK,	"{root_inst_slot}:CommsHashToPLCS")
}}
record(bi, "{root_inst_slot}:S7ConnectedR")
{{
	field(DESC,	"Shows if the S7 channel is connected")
	field(SCAN,	"I/O Intr")
	field(DTYP,	"S7plc stat")
	field(INP,	"@$(PLCNAME)")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(ZSV,      "MAJOR")
}}
record(stringin, "{root_inst_slot}:PLCAddr-RB")
{{
# We assume S7 and Modbus address are the same (as they should be)
	field(DESC,	"Address of the PLC")
}}
record(scalcout, "{root_inst_slot}:iPLCAddr-RB")
{{
	field(DESC,	"Strip port number of host:port")
	field(INAA,	"{root_inst_slot}:S7Addr-RB CP")
	field(CALC,	"AA[0,':']")
	field(OUT,	"{root_inst_slot}:PLCAddr-RB PP")
}}
record(stringout, "{root_inst_slot}:PLCAddrS")
{{
	field(DESC,	"Address of the PLC")
	field(FLNK,	"{root_inst_slot}:iSetPLCAddrS")
}}
record(fanout, "{root_inst_slot}:iSetPLCAddrS")
{{
	field(LNK1,	"{root_inst_slot}:iCalcS7AddrS")
	field(LNK2,	"{root_inst_slot}:iCalcModbusAddrS")
}}
record(scalcout, "{root_inst_slot}:iCalcS7AddrS")
{{
	field(INAA,	"{root_inst_slot}:PLCAddrS")
	field(CALC,	"AA + ':' + '$(S7_PORT)'")
	field(OUT,	"{root_inst_slot}:iS7AddrS PP")
}}
record(scalcout, "{root_inst_slot}:iCalcModbusAddrS")
{{
	field(INAA,	"{root_inst_slot}:PLCAddrS")
	field(CALC,	"AA + ':' + '$(MODBUS_PORT)'")
	field(OUT,	"{root_inst_slot}:iAsyn.HOSTINFO PP")
}}
record(stringin, "{root_inst_slot}:ModbusAddr-RB")
{{
	field(DESC,	"Address of the PLC")
	field(INP,	"{root_inst_slot}:iAsyn.HOSTINFO CP")
}}
record(stringin, "{root_inst_slot}:S7Addr-RB")
{{
	field(DESC,	"Address of the PLC")
	field(INP,	"{root_inst_slot}:iS7AddrS CP")
}}
record(stringout, "{root_inst_slot}:iS7AddrS")
{{
	field(DESC,	"Set address of the PLC")
	field(DTYP,	"S7plc addr")
	field(OUT,	"@$(PLCNAME)")
	field(DISP,	"1")
}}
record(calcout, "{root_inst_slot}:iCalcConn")
{{
	field(INPA,	"{root_inst_slot}:S7ConnectedR CP")
	field(INPB,	"{root_inst_slot}:ModbusConnectedR CP")
	field(CALC,	"A && B")
	field(OUT,	"{root_inst_slot}:ConnectedR PP")
}}
record(bi, "{root_inst_slot}:ConnectedR")
{{
	field(DESC,	"Shows if the PLC is connected")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(ZSV,      "MAJOR")
}}
record(bi, "{root_inst_slot}:PLCHashCorrectR")
{{
	field(DESC,	"Shows if the comms hash is correct")
	field(ONAM,	"Correct")
	field(ZNAM,	"Incorrect")
	field(ZSV,      "MAJOR")
}}
record(bi, "{root_inst_slot}:AliveR")
{{
	alias("{root_inst_slot}:CommsOK")
	field(DESC,	"Shows if the PLC is sending heartbeats")
	field(ONAM,	"Alive")
	field(ZNAM,	"Not responding")
	field(ZSV,      "MAJOR")
}}
record(calcout, "{root_inst_slot}:iCheckHash")
{{
	field(INPA,	"{root_inst_slot}:iCommsHashToPLC")
	field(INPB,	"{root_inst_slot}:CommsHashFromPLCR")
	field(INPC,	"{root_inst_slot}:CommsHashFromPLCR.STAT")
	field(CALC,	"A == B && C == 0")
	field(OOPT,	"On Change")
	field(OUT,	"{root_inst_slot}:PLCHashCorrectR PP")
}}
record(bi, "{root_inst_slot}:iOne")
{{
	field(DISP,	"1")
	field(PINI,	"YES")
	field(VAL,	"1")
}}
record(bo, "{root_inst_slot}:iGotHeartbeat")
{{
	field(DOL,	"{root_inst_slot}:iOne")
	field(OMSL,	"closed_loop")
	field(OUT,	"{root_inst_slot}:iKickAlive PP")
}}
record(bo, "{root_inst_slot}:iKickAlive")
{{
	field(HIGH,	"5")
	field(OUT,	"{root_inst_slot}:AliveR PP")
}}

########################################################
########## EPICS -> PLC comms management data ##########
########################################################
record(ao, "{root_inst_slot}:iCommsHashToPLC")
{{
	field(DISP,	"1")
	field(PINI,	"YES")
	field(VAL,	"#HASH")
}}
record(ao, "{root_inst_slot}:CommsHashToPLCS")
{{
	field(DESC,	"Sends comms hash to PLC")
	field(SCAN,	"1 second")
	field(DTYP,	"asynInt32")
	field(OUT,	"@asyn($(PLCNAME)write, [PLCF#EPICSToPLCDataBlockStartOffset], 100)INT32_[PLCF#'BE' if 'PLC-EPICS-COMMS:Endianness' == 'BigEndian' else 'LE']")
	field(OMSL,	"closed_loop")
	field(DOL,	"{root_inst_slot}:iCommsHashToPLC")
	field(DISV,	"0")
	field(SDIS,	"{root_inst_slot}:ModbusConnectedR")
}}
record(calc, "{root_inst_slot}:iHeartbeatToPLC")
{{
	field(SCAN,	"1 second")
	field(INPA,	"{root_inst_slot}:iHeartbeatToPLC.VAL")
	field(CALC,	"(A >= 32000)? 0 : A + 1")
	field(FLNK,	"{root_inst_slot}:HeartbeatToPLCS")
	field(DISV,	"0")
	field(SDIS,	"{root_inst_slot}:ModbusConnectedR")
}}
record(ao, "{root_inst_slot}:HeartbeatToPLCS")
{{
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
record(ai, "{root_inst_slot}:CommsHashFromPLCR")
{{
	field(DESC,	"Comms hash from PLC")
	field(SCAN,	"I/O Intr")
	field(DTYP,	"S7plc")
	field(INP,	"@$(PLCNAME)/[PLCF#PLCToEPICSDataBlockStartOffset] T=INT32")
	field(FLNK,	"{root_inst_slot}:iCheckHash")
}}
record(ai, "{root_inst_slot}:HeartbeatFromPLCR")
{{
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
""".format(root_inst_slot  = self.root_inst_slot(),
           plcf_commit     = keyword_params.get("COMMIT_ID", "N/A"),
           plcf_commit_39  = keyword_params.get("COMMIT_ID", "N/A")[:39],
           cmd_cnt         = CMD_BLOCK.counter_keyword(),
           status_cnt      = STATUS_BLOCK.counter_keyword())

        self._append(epics_db_header, output)

        return self


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        self._if_def = if_def
        self._output = output

        self._body_register_block_printer(if_def._cmd_block())
        self._body_register_block_printer(if_def._param_block())
        self._body_register_block_printer(if_def._status_block())

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
                self._append(self._toEPICS(src))

        self._body_end_param(if_def, output)
        self._append("\n\n")
        self._body_end_cmd(if_def, output)
        self._body_end_status(if_def, output)


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
        super(EPICS_TEST, self).__init__(test = True)


    @staticmethod
    def name():
        return "EPICS-TEST-DB"


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        #Have to call PRINTER.header explicitly
        PRINTER.header(self, output, **keyword_params).add_filename_header(output, extension = "db")
        epics_db_header = """
record(stringin, "{root_inst_slot}:ModVersionR")
{{
	field(DISP,	"1")
	field(VAL,	"$(MODVERSION=N/A)")
	field(PINI,	"YES")
}}

record(stringin, "{root_inst_slot}:PLCFCommitR")
{{
	field(DISP,	"1")
#{plcf_commit}
	field(VAL,	"{plcf_commit_39}")
	field(PINI,	"YES")
	info("plcf_commit", "{plcf_commit}")
}}

#########################################################
########## EPICS <-> PLC connection management ##########
#########################################################
record(bi, "{root_inst_slot}:ModbusConnectedR")
{{
	field(DESC,	"Shows if the MODBUS channel connected")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(ZSV,      "MAJOR")
	field(VAL,	"1")
	field(PINI,	"YES")
	field(FLNK,	"{root_inst_slot}:CommsHashToPLCS")
}}
record(bi, "{root_inst_slot}:S7ConnectedR")
{{
	field(DESC,	"Shows if the S7 channel is connected")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(ZSV,      "MAJOR")
	field(VAL,	"1")
	field(PINI,	"YES")
}}
record(calcout, "{root_inst_slot}:iCalcConn")
{{
	field(INPA,	"{root_inst_slot}:S7ConnectedR CP")
	field(INPB,	"{root_inst_slot}:ModbusConnectedR CP")
	field(CALC,	"A && B")
	field(OUT,	"{root_inst_slot}:ConnectedR PP")
}}
record(bi, "{root_inst_slot}:ConnectedR")
{{
	field(DESC,	"Shows if the PLC is connected")
	field(ONAM,	"Connected")
	field(ZNAM,	"Disconnected")
	field(ZSV,      "MAJOR")
}}
record(bi, "{root_inst_slot}:PLCHashCorrectR")
{{
	field(DESC,	"Shows if the comms hash is correct")
	field(ONAM,	"Correct")
	field(ZNAM,	"Incorrect")
	field(ZSV,      "MAJOR")
}}
record(bi, "{root_inst_slot}:AliveR")
{{
	alias("{root_inst_slot}:CommsOK")
	field(DESC,	"Shows if the PLC is sending heartbeats")
	field(ONAM,	"Alive")
	field(ZNAM,	"Not responding")
	field(ZSV,      "MAJOR")
}}
record(calcout, "{root_inst_slot}:iCheckHash")
{{
	field(INPA,	"{root_inst_slot}:iCommsHashToPLC")
	field(INPB,	"{root_inst_slot}:CommsHashFromPLCR")
	field(INPC,	"{root_inst_slot}:CommsHashFromPLCR.STAT")
	field(CALC,	"A == B && C == 0")
	field(OOPT,	"On Change")
	field(OUT,	"{root_inst_slot}:PLCHashCorrectR PP")
}}
record(bi, "{root_inst_slot}:iOne")
{{
	field(DISP,	"1")
	field(PINI,	"YES")
	field(VAL,	"1")
}}
record(bo, "{root_inst_slot}:iGotHeartbeat")
{{
	field(DOL,	"{root_inst_slot}:iOne")
	field(OMSL,	"closed_loop")
	field(OUT,	"{root_inst_slot}:iKickAlive PP")
}}
record(bo, "{root_inst_slot}:iKickAlive")
{{
	field(HIGH,	"5")
	field(OUT,	"{root_inst_slot}:AliveR PP")
}}

########################################################
########## EPICS -> PLC comms management data ##########
########################################################
record(ao, "{root_inst_slot}:iCommsHashToPLC")
{{
	field(DISP,	"1")
	field(PINI,	"YES")
	field(VAL,	"#HASH")
}}
record(ao, "{root_inst_slot}:CommsHashToPLCS")
{{
	field(DESC,	"Sends comms hash to PLC")
	field(OMSL,	"closed_loop")
	field(DOL,	"{root_inst_slot}:iCommsHashToPLC")
	field(DISV,	"0")
	field(SDIS,	"{root_inst_slot}:ConnectedR")
}}
record(calc, "{root_inst_slot}:iHeartbeatToPLC")
{{
	field(SCAN,	"1 second")
	field(INPA,	"{root_inst_slot}:iHeartbeatToPLC.VAL")
	field(CALC,	"(A >= 32000)? 0 : A + 1")
	field(FLNK,	"{root_inst_slot}:HeartbeatToPLCS")
	field(DISV,	"0")
	field(SDIS,	"{root_inst_slot}:ConnectedR")
}}
record(ao, "{root_inst_slot}:HeartbeatToPLCS")
{{
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
record(ai, "{root_inst_slot}:CommsHashFromPLCR")
{{
	field(DESC,	"Comms hash from PLC")
	field(SCAN,	"1 second")
	field(PINI,	"YES")
	field(VAL,	"#HASH")
	field(FLNK,	"{root_inst_slot}:iCheckHash")
}}
record(ai, "{root_inst_slot}:HeartbeatFromPLCR")
{{
	field(DESC,	"Heartbeat from PLC")
	field(INP,	"{root_inst_slot}:iHeartbeatToPLC.VAL CP")
	field(FLNK,	"{root_inst_slot}:iGotHeartbeat")
}}

########################################################
################# Test management data #################
########################################################
record(ao, "{root_inst_slot}:FixHashS")
{{
	field(DESC,	"Make HASH correct")
	field(OMSL,	"closed_loop")
	field(DOL,	"{root_inst_slot}:iCommsHashToPLC")
	field(OUT,	"{root_inst_slot}:CommsHashFromPLCR PP")
}}

record(bo, "{root_inst_slot}:RuinHashS")
{{
	field(DESC,	"Make HASH incorrect")
	field(FLNK,	"{root_inst_slot}:iRuinHash")
}}
record(calcout, "{root_inst_slot}:iRuinHash")
{{
	field(DESC,	"Make HASH incorrect")
	field(INPA,	"{root_inst_slot}:iCommsHashToPLC")
	field(CALC,	"A * -1")
	field(OUT,	"{root_inst_slot}:CommsHashFromPLCR PP")
}}
""".format(root_inst_slot = self.root_inst_slot(),
           plcf_commit    = keyword_params.get("COMMIT_ID", "N/A"),
           plcf_commit_39 = keyword_params.get("COMMIT_ID", "N/A")[:39])

        self._append(epics_db_header, output)
        return self



#
# OPC-UA EPICS output
#
class EPICS_OPC(EPICS_BASE):
    def __init__(self):
        super(EPICS_OPC, self).__init__()


    @staticmethod
    def name():
        return "EPICS-OPC-DB"


    def field_inp(self, inst_io, datablock, var_name, **keyword_params):
        return '@{inst_io} ns=3;s=\\"{datablock}\\".\\"{var_name}\\"'.format(inst_io    = inst_io,
                                                                             datablock  = datablock,
                                                                             var_name   = var_name)


    def field_out(self, inst_io, datablock, var_name, monitor = " monitor=n"):
        return '@{inst_io} ns=3;s=\\"{datablock}\\".\\"{var_name}\\"{monitor}'.format(inst_io    = inst_io,
                                                                                      datablock  = datablock,
                                                                                      var_name   = var_name,
                                                                                      monitor    = monitor)


    def _toEPICS(self, var):
        pv_extra = self.DISABLE_TEMPLATE + var.build_pv_extra() + EPICS_BASE.PLC_INFO_FIELDS.format(plc_datablock = var.datablock_name(),
                                                                                                    plc_variable  = var.name())
        return (var.source(),
                var.pv_template().format(recordtype = var.pv_type(),
                                         pv_name    = var._build_pv_name(self._if_def.inst_slot()),
                                         alias      = var._build_pv_alias(self._if_def.inst_slot()),
                                         dtyp       = "OPCUA",
                                         inp_out    = var.inp_out(inst_io   = '$(SUBSCRIPTION)',
                                                                  datablock = var.datablock_name(),
                                                                  var_name  = var.name()),
                                         pv_extra   = pv_extra))


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        PRINTER.header(self, output, **keyword_params).add_filename_header(output, extension = "db")
        epics_db_header = """
record(stringin, "{root_inst_slot}:ModVersionR")
{{
	field(DISP,	"1")
	field(VAL,	"$(MODVERSION=N/A)")
	field(PINI,	"YES")
}}

record(stringin, "{root_inst_slot}:PLCFCommitR")
{{
	field(DISP,	"1")
#{plcf_commit}
	field(VAL,	"{plcf_commit_39}")
	field(PINI,	"YES")
	info("plcf_commit", "{plcf_commit}")
}}

record(mbbi, "{root_inst_slot}:OPCStateR")
{{
	field(DTYP, "OPCUA")
	field(INP, "@$(SUBSCRIPTION) i=2259")
	field(ZRST, "Running")
	field(ONST, "Failed")
	field(TWST, "NoConfiguration")
	field(THST, "Suspended")
	field(FRST, "Shutdown")
	field(FVST, "Test")
	field(SXST, "CommunicationFault")
	field(SVST, "Unknown")
}}

record(ao, "{root_inst_slot}:iCommsHashToPLC")
{{
	field(DISP,	"1")
	field(PINI,	"YES")
	field(VAL,	"#HASH")
}}
record(ao, "{root_inst_slot}:CommsHashToPLCS")
{{
	field(DESC,	"Sends comms hash to PLC")
#	field(SCAN,	"1 second")
	field(OMSL,	"closed_loop")
	field(DOL,	"{root_inst_slot}:iCommsHashToPLC")
}}
""".format(root_inst_slot  = self.root_inst_slot(),
           plcf_commit     = keyword_params.get("COMMIT_ID", "N/A"),
           plcf_commit_39  = keyword_params.get("COMMIT_ID", "N/A")[:39])

        self._append(epics_db_header, output)
        return self


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        self._if_def = if_def
        self._output = output

        self._body_register_block_printer(if_def._cmd_block())
        self._body_register_block_printer(if_def._param_block())
        self._body_register_block_printer(if_def._status_block())

        self._append("""
##########
########## {inst_slot} ##########
##########

""".format(inst_slot = self.inst_slot()))

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
                self._append(self._toEPICS(src))

        self._body_end_param(if_def, output)
        self._append("\n\n")
