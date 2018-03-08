""" Template Factory: TIA_MAP printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


#FIXME:
# Use the counter_keyword() of the corresponding BLOCK instead of hardcoding Counter1 and Counter2


from . import PRINTER
from tf_ifdef import CMD_BLOCK



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
    def header(self, output):
        PRINTER.header(self, output)

        self._append("""#FILENAME {inst_slot}-TIA-MAP-{timestamp}.scl
#EOL "\\r\\n"
#COUNTER Counter1 = [PLCF# Counter1 + 10];
#COUNTER Counter2 = [PLCF# Counter2 + 10];
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

   // {inst_slot}: PLC <-> EPICS Communication Mapping
   //------------------------------------------------------------------------

   // Hashes Comparision
   IF (#PLC_Hash = #IOC_Hash) THEN
""".format(inst_slot = self.inst_slot(),
           timestamp = self.timestamp()).replace("\n", "\r\n"), output)



    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)

        self._append("""
      "_CommsEPICSDataMappingFBFactory"(EPICSToPLCLength           := {epicstoplclength},
                                        EPICSToPLCDataBlockOffset  := [PLCF# ^(EPICSToPLCDataBlockStartOffset) + Counter1],
                                        EPICSToPLCParametersStart  := {commandwordslength},
                                        PLCToEPICSLength           := {plctoepicslength},
                                        PLCToEPICSDataBlockOffset  := [PLCF# ^(PLCToEPICSDataBlockStartOffset) + Counter2],
                                        EPICSToPLCCommandRegisters := {reg}.CommandReg,
                                        PLCToEPICSStatusRegisters  := {reg}.StatusReg,
                                        EPICSToPLCDataBlock        := "EPICSToPLC"."Word",
                                        PLCToEPICSDataBlock        := "PLCToEPICS"."Word");
#COUNTER Counter1 = [PLCF# Counter1 + {epicstoplclength}];
#COUNTER Counter2 = [PLCF# Counter2 + {plctoepicslength}];
""".format(inst_slot          = self.inst_slot(),
           epicstoplclength   = if_def.to_plc_words_length(),
           plctoepicslength   = if_def.from_plc_words_length(),
           commandwordslength = str(if_def.properties()[CMD_BLOCK.length_keyword()]),
           reg                = self._xReg()
          ).replace("\n", "\r\n"), output)



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
      "Word" : Array[0..[PLCF# Counter1 - 1]] of Word;
   END_STRUCT;


BEGIN
END_DATA_BLOCK

//########## PLC->EPICS datablock ##########
DATA_BLOCK "PLCToEPICS"
{{ S7_Optimized_Access := 'FALSE' }}
VERSION : 0.1
NON_RETAIN
   STRUCT
      "Word" : Array[0..[PLCF# Counter2 - 1]] of Word;
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

""".format(bytestosend    = self.plcf("2 * Counter2"),
           interfaceid    = self.plcf("PLC-EPICS-COMMS: InterfaceID"),
           s7connectionid = self.plcf("PLC-EPICS-COMMS: S7ConnectionID"),
           mbconnectionid = self.plcf("PLC-EPICS-COMMS: MBConnectionID"),
           s7port         = self.plcf("PLC-EPICS-COMMS: S7Port"),
           mbport         = self.plcf("PLC-EPICS-COMMS: MBPort")).replace("\n", "\r\n"), output)




class TIA_MAP_INTERFACE(TIA_MAP_DIRECT):
    def __init__(self):
        TIA_MAP_DIRECT.__init__(self)


    def _xReg(self):
        return '"DEV_{inst_slot}_iDB"'.format(inst_slot = self.inst_slot())


    @staticmethod
    def name():
        return "TIA-MAP-INTERFACE"
