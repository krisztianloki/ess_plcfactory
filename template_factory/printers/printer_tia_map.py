""" Template Factory: TIA_MAP printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"




from . import PRINTER
from tf_ifdef import CMD_BLOCK, STATUS_BLOCK



def printer():
    return [(TIA_MAP_DIRECT.name(), TIA_MAP_DIRECT), (TIA_MAP_INTERFACE.name(), TIA_MAP_INTERFACE)]




class TIA_MAP_DIRECT(PRINTER):
    def __init__(self):
        PRINTER.__init__(self, comments = False, preserve_empty_lines = False, show_origin = False)


    def comment(self):
        return "//"


    def _xReg(self):
        return '"{inst_slot}"'.format(inst_slot = self.inst_slot())


    @staticmethod
    def name():
        return "TIA-MAP-DIRECT"


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        PRINTER.header(self, output, **keyword_params)

        self._append("""#FILENAME {inst_slot}-TIA-MAP-{timestamp}.scl
#EOL "\\r\\n"
#COUNTER {cmd_cnt} = [PLCF# {cmd_cnt} + 10];
#COUNTER {status_cnt} = [PLCF# {status_cnt} + 10];
FUNCTION "_CommsEPICSDataMap" : Void
{{ S7_Optimized_Access := 'FALSE' }}
VERSION : 0.1
   VAR_TEMP
       tHashDint : DInt;
       wordTOdint AT tHashDint : Array[0..1] of Word;
       PLC_Hash : DInt;
       IOC_Hash : DInt;
   END_VAR

   BEGIN

   // PLC Hash (Generated from PLC Factory)
   #PLC_Hash := DINT##HASH;

   // Send the PLC Hash to the EPICS IOC
   "PLCToEPICS"."Word"[1] := DINT_TO_WORD(#PLC_Hash);
   "PLCToEPICS"."Word"[0] := DINT_TO_WORD(SHR(IN := #PLC_Hash, N := 16));

   // Get Hash from the EPICS IOC
   #wordTOdint[0] := "EPICSToPLC"."Word"[0];
   #wordTOdint[1] := "EPICSToPLC"."Word"[1];
   #IOC_Hash := #tHashDint;

   // Hashes Comparison
   IF (#PLC_Hash = #IOC_Hash) THEN

      // {inst_slot}: PLC <-> EPICS Communication Mapping
      //------------------------------------------------------------------------
""".format(inst_slot  = self.inst_slot(),
           timestamp  = self.timestamp(),
           cmd_cnt    = CMD_BLOCK.counter_keyword(),
           status_cnt = STATUS_BLOCK.counter_keyword()), output)



    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)

        self._append("""
      "_CommsEPICSDataMappingFBFactory"(EPICSToPLCLength           := {epicstoplclength},
                                        EPICSToPLCDataBlockOffset  := [PLCF# ^(EPICSToPLCDataBlockStartOffset) + {cmd_cnt}],
                                        EPICSToPLCParametersStart  := {commandwordslength},
                                        PLCToEPICSLength           := {plctoepicslength},
                                        PLCToEPICSDataBlockOffset  := [PLCF# ^(PLCToEPICSDataBlockStartOffset) + {status_cnt}],
                                        EPICSToPLCCommandRegisters := {reg}.CommandReg,
                                        PLCToEPICSStatusRegisters  := {reg}.StatusReg,
                                        EPICSToPLCDataBlock        := "EPICSToPLC"."Word",
                                        PLCToEPICSDataBlock        := "PLCToEPICS"."Word");
#COUNTER {cmd_cnt} = [PLCF# {cmd_cnt} + {epicstoplclength}];
#COUNTER {status_cnt} = [PLCF# {status_cnt} + {plctoepicslength}];
""".format(inst_slot          = self.inst_slot(),
           epicstoplclength   = if_def.to_plc_words_length(),
           cmd_cnt            = CMD_BLOCK.counter_keyword(),
           plctoepicslength   = if_def.from_plc_words_length(),
           status_cnt         = STATUS_BLOCK.counter_keyword(),
           commandwordslength = str(if_def.properties()[CMD_BLOCK.length_keyword()]),
           reg                = self._xReg()
          ), output)



    #
    # FOOTER
    #
    def footer(self, output):
        PRINTER.footer(self, output)

        self._append("""

   END_IF;

END_FUNCTION

//########## EPICS->PLC datablock ##########
DATA_BLOCK "EPICSToPLC"
{{ S7_Optimized_Access := 'FALSE' }}
VERSION : 0.1
NON_RETAIN
   STRUCT
      "Word" : Array[0..[PLCF# {cmd_cnt} - 1]] of Word;
   END_STRUCT;


BEGIN
END_DATA_BLOCK

//########## PLC->EPICS datablock ##########
DATA_BLOCK "PLCToEPICS"
{{ S7_Optimized_Access := 'FALSE' }}
VERSION : 0.1
NON_RETAIN
   STRUCT
      "Word" : Array[0..[PLCF# {status_cnt} - 1]] of Word;
   END_STRUCT;


BEGIN
END_DATA_BLOCK

FUNCTION "_CommsEPICS" : Void
{{ S7_Optimized_Access := 'TRUE' }}
VERSION : 0.1

BEGIN
	//Heartbeat PLC->EPICS
	IF "Utilities".Pulse_1s THEN
	    "PLCToEPICS"."Word"[2] := "PLCToEPICS"."Word"[2] + 1;
	    IF "PLCToEPICS"."Word"[2] >= 32000 THEN
	        "PLCToEPICS"."Word"[2] := 0;
	    END_IF;
	END_IF;

	// Call the comms block to provide PLC<->EPICS comms
	"_CommsPLC_EPICS_DB"(Enable         := "Utilities".AlwaysOn,
	                     SendTrigger    := "Utilities".Pulse_200ms,
	                     BytesToSend    := {bytestosend},
	                     InterfaceID    := {interfaceid},
	                     S7ConnectionID := {s7connectionid},
	                     MBConnectionID := {mbconnectionid},
	                     S7Port         := {s7port},
	                     MBPort         := {mbport},
	                     PLCToEPICSData := "PLCToEPICS"."Word",
	                     EPICSToPLCData := "EPICSToPLC"."Word");

	//Map all devices command and status registers to EPICS->PLC and PLC->EPICS data exchange blocks
	"_CommsEPICSDataMap"();

END_FUNCTION

""".format(bytestosend    = self.plcf("2 * {status_cnt}".format(status_cnt = STATUS_BLOCK.counter_keyword())),
           cmd_cnt        = CMD_BLOCK.counter_keyword(),
           status_cnt     = STATUS_BLOCK.counter_keyword(),
           interfaceid    = self.plcf("PLC-EPICS-COMMS: InterfaceID"),
           s7connectionid = self.plcf("PLC-EPICS-COMMS: S7ConnectionID"),
           mbconnectionid = self.plcf("PLC-EPICS-COMMS: MBConnectionID"),
           s7port         = self.plcf("PLC-EPICS-COMMS: S7Port"),
           mbport         = self.plcf("PLC-EPICS-COMMS: MBPort")), output)




class TIA_MAP_INTERFACE(TIA_MAP_DIRECT):
    def __init__(self):
        TIA_MAP_DIRECT.__init__(self)


    def _xReg(self):
        return '"DEV_{inst_slot}_iDB"'.format(inst_slot = self.inst_slot())


    @staticmethod
    def name():
        return "TIA-MAP-INTERFACE"
