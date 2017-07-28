""" Template Factory: TIA_MAP printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


#FIXME:
# Use the counter_keyword() of the corresponding BLOCK instead of hardcoding Counter1 and Counter2


from printers import PRINTER
from tf_ifdef import CMD_BLOCK



def printer():
    return [(TIA_MAP.name(), TIA_MAP), (TIA_MAPX.name(), TIA_MAPX)]




class TIA_MAP(PRINTER):
    def __init__(self, comments = False):
        PRINTER.__init__(self, comments)


    def comment(self):
        return "//"


    @staticmethod
    def name():
        return "TIA-MAP"


    #
    # HEADER
    #
    def header(self, output):
        PRINTER.header(self, output)

        self._append("""#FILENAME {inst_slot}-[PLCF#TEMPLATE]-[PLCF#TIMESTAMP].scl
#EOL "\\r\\n"
#COUNTER Counter1 = [PLCF# Counter1 + 10];
#COUNTER Counter2 = [PLCF# Counter2 + 10];
FUNCTION "_CommsEPICSDataMap" : Void
{{ S7_Optimized_Access := 'TRUE' }}
VERSION : 0.1
   VAR_TEMP
      Hash : DInt;
   END_VAR

BEGIN
        //Comms data generation hash
        #Hash := DInt##HASH;
        "[PLCF#PLCToEPICSDataBlockName]"."Word"[1] := DINT_TO_WORD(#Hash);
        "[PLCF#PLCToEPICSDataBlockName]"."Word"[0] := DINT_TO_WORD(SHR(IN := #Hash, N := 16));

  // {inst_slot}: PLC <-> EPICS Communication Mapping
  //------------------------------------------------------------------------
""".format(inst_slot = self.inst_slot()).replace("\n", "\r\n"), output)


    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)

        self._append("""
        "_CommsEPICSDataMappingFB"(EPICSToPLCLength := [PLCF# {epicstoplclength}],
                                   EPICSToPLCDataBlockOffset := [PLCF# ^(EPICSToPLCDataBlockStartOffset) + Counter1],
                                   PLCToEPICSLength := [PLCF# {plctoepicslength}],
                                   PLCToEPICSDataBlockOffset := [PLCF# ^(PLCToEPICSDataBlockStartOffset) + Counter2],
                                   EPICSToPLCCommandRegisters := "{inst_slot}".CommandReg,
                                   PLCToEPICSStatusRegisters := "{inst_slot}".StatusReg,
                                   EPICSToPLCDataBlock := "[PLCF# ^(EPICSToPLCDataBlockName)]"."Word",
                                   PLCToEPICSDataBlock := "[PLCF# ^(PLCToEPICSDataBlockName)]"."Word");
#COUNTER Counter1 = [PLCF# Counter1 + {epicstoplclength}];
#COUNTER Counter2 = [PLCF# Counter2 + {plctoepicslength}];
""".format(inst_slot        = self.inst_slot(),
           epicstoplclength = if_def.to_plc_words_length(),
           plctoepicslength = if_def.from_plc_words_length()
          ).replace("\n", "\r\n"), output)



    #
    # FOOTER
    #
    def footer(self, output):
        PRINTER.footer(self, output)

        self._append("""
END_FUNCTION

(*
At this stage we are not going to dynamically set the length of DB files, will just set them at 2000 bytes
########## EPICS->PLC datablock ##########
DATA_BLOCK "EPICSToPLC"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
   STRUCT
      "Word" : Array[0..[PLCF# Counter1 - 1]] of Word;
   END_STRUCT;


BEGIN
END_DATA_BLOCK

########## PLC->EPICS datablock ##########
DATA_BLOCK "PLCToEPICS"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
   STRUCT
      "Word" : Array[0..[PLCF# Counter2 - 1]] of Word;
   END_STRUCT;


BEGIN
        "Word"[0] := #HASH;
END_DATA_BLOCK
*)
""".replace("\n", "\r\n"), output)




class TIA_MAPX(TIA_MAP):
    def __init__(self, comments = False):
        TIA_MAP.__init__(self, comments)


    @staticmethod
    def name():
        return "TIA-MAPX"


    #
    # HEADER
    #
    def header(self, output):
        PRINTER.header(self, output)

        self._append("""#FILENAME {inst_slot}-[PLCF#TEMPLATE]-[PLCF#TIMESTAMP].scl
#EOL "\\r\\n"
#COUNTER Counter1 = [PLCF# Counter1 + 10];
#COUNTER Counter2 = [PLCF# Counter2 + 10];
FUNCTION "_CommsEPICSDataMap" : Void
{{ S7_Optimized_Access := 'TRUE' }}
VERSION : 0.1
   VAR_TEMP
      Hash : DInt;
   END_VAR

BEGIN
        //Comms data generation hash
        #Hash := DInt##HASH;
        "[PLCF#PLCToEPICSDataBlockName]"."Word"[1] := DINT_TO_WORD(#Hash);
        "[PLCF#PLCToEPICSDataBlockName]"."Word"[0] := DINT_TO_WORD(SHR(IN := #Hash, N := 16));

  // {inst_slot}: PLC <-> EPICS Communication Mapping
  //------------------------------------------------------------------------
""".format(inst_slot = self.inst_slot()).replace("\n", "\r\n"), output)


    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)

        self._append("""
        "_CommsEPICSDataMappingFBFactory"(EPICSToPLCLength := [PLCF# {epicstoplclength}],
                                          EPICSToPLCDataBlockOffset := [PLCF# ^(EPICSToPLCDataBlockStartOffset) + Counter1],
                                          EPICSToPLCParametersStart := [PLCF# {commandwordslength}],
                                          PLCToEPICSLength := [PLCF# {plctoepicslength}],
                                          PLCToEPICSDataBlockOffset := [PLCF# ^(PLCToEPICSDataBlockStartOffset) + Counter2],
                                          EPICSToPLCCommandRegisters := "DEV_{inst_slot}_iDB".CommandReg,
                                          PLCToEPICSStatusRegisters := "DEV_{inst_slot}_iDB".StatusReg,
                                          EPICSToPLCDataBlock := "[PLCF# ^(EPICSToPLCDataBlockName)]"."Word",
                                          PLCToEPICSDataBlock := "[PLCF# ^(PLCToEPICSDataBlockName)]"."Word");
#COUNTER Counter1 = [PLCF# Counter1 + {epicstoplclength}];
#COUNTER Counter2 = [PLCF# Counter2 + {plctoepicslength}];
""".format(inst_slot          = self.inst_slot(),
           epicstoplclength   = if_def.to_plc_words_length(),
           plctoepicslength   = if_def.from_plc_words_length(),
           commandwordslength = str(if_def.properties()[CMD_BLOCK.length_keyword()])
          ).replace("\n", "\r\n"), output)
