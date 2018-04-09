
""" InterfaceFactory : Entry point """

__author__     = "Miklos Boros"
__copyright__  = "Copyright 2017-2018, European Spallation Source, Lund"
__credits__    = [ "Krisztian Loki"
				, "Miklos Boros"
				, "Francois Bellorini"
				]
__license__    = "GPLv3"
__maintainer__ = "Miklos Boros"
__email__      = "miklos.boros@esss.se; borosmiklos@gmail.com"
__status__     = "Production"
__env__        = "Python version 2.7"

# Python libraries
import argparse
import datetime
import os
import errno
import sys
import time
import hashlib
import zipfile

#Global variables
timestamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())

OrderedLines = []
ExternalSourceFile = []

DeviceNum = 0
HASH = ""
ActualDeviceName = ""
ActualDeviceNameWhite = ""
ActualDeviceType = ""
EPICSTOPLCLENGTH = ""
EPICSTOPLCDATABLOCKOFFSET = ""
EPICSTOPLCPARAMETERSSTART = ""
PLCTOEPICSDATABLOCKOFFSET = ""
DeviceTypeList = []

DevTypeHeader = []
DevTypeVAR_INPUT = []
DevTypeVAR_INOUT = []
DevTypeVAR_OUTPUT = []
DevTypeDB_SPEC = []
DevTypeVAR_TEMP = []
DevTypeBODY_HEADER = []
DevTypeBODY_CODE = []
DevTypeBODY_CODE_ARRAY = []
DevTypeBODY_END = []

EPICS_PLC_TesterDB = []

EPICS_device_calls_body = []
EPICS_device_calls_test_body = []
EPICS_device_calls_header = []
EPICS_device_calls_test_header = []

DeviceInstance = []

EndString = ""
EndString2 = ""
IsDouble = False

MaxStatusReg = 0
MaxCommandReg = 0

MAX_IO_DEVICES = 0
MAX_LOCAL_MODULES = 0
MAX_MODULES_IN_IO_DEVICE = 0

Direct = False

class InterfaceFactoryArgumentError(Exception):
	def __init__(self, status):
		print "\nERROR:"
		print "InterfaceFactory needs more parameter to run. Use -h parameter for more help!\n"
		self.status = status

class InterfaceFactoryArgumentParser(argparse.ArgumentParser):
	def __init__(self):
		argparse.ArgumentParser.__init__(self)


	def exit(self, status = 0, message = None):
		if message:
			self._print_message(message, sys.stderr)
		raise InterfaceFactoryArgumentError(status)

def makedirs(path):
	try:
		os.makedirs(path)
	except OSError as ose:
		if not os.path.isdir(path):
			raise

def Pre_ProcessIFA(IfaPath):
	print "PLCFactory file location: "+IfaPath
    
	#Pre process IFA to have Status, Command, Parameter order	
	print "Pre-processing .ifa file..."
	
	global DeviceNum 
	DeviceNum = 0
	global OrderedLines
	OrderedLines = []
	global HASH 
	HASH = ""
	global MAX_IO_DEVICES
	MAX_IO_DEVICES = 0
	global MAX_LOCAL_MODULES
	MAX_LOCAL_MODULES = 0
	global MAX_MODULES_IN_IO_DEVICE
	MAX_MODULES_IN_IO_DEVICE = 0

	
	StatusArea = []
	CommandArea = []
	ParameterArea = []
	Comments = []
	
	InStatus = False
	InCommand = False
	InParameter = False

	FirstDevice = True
		
	with open(IfaPath) as f:
		lines = f.readlines()
		pos = 0
		while pos < len(lines):
			if lines[pos].rstrip() == "HASH":
				HASH = lines[pos+1].rstrip()
			if lines[pos].rstrip() == "MAX_IO_DEVICES":
				MAX_IO_DEVICES = int(lines[pos+1].strip())
				if MAX_IO_DEVICES <= 0:
					MAX_IO_DEVICES = 1
			if lines[pos].rstrip() == "MAX_LOCAL_MODULES":
				MAX_LOCAL_MODULES = int(lines[pos+1].strip())
				if MAX_LOCAL_MODULES <= 0:
					MAX_LOCAL_MODULES = 1
			if lines[pos].rstrip() == "MAX_MODULES_IN_IO_DEVICE":
				MAX_MODULES_IN_IO_DEVICE = int(lines[pos+1].strip())
				if MAX_MODULES_IN_IO_DEVICE <= 0:
					MAX_MODULES_IN_IO_DEVICE = 1
			if lines[pos].rstrip() == "DEVICE":
				DeviceNum = DeviceNum + 1
				InStatus = False
				InCommand = False
				InParameter = False
				if FirstDevice == False:
					for line in StatusArea:
						OrderedLines.append(line)
					for line in CommandArea:
						OrderedLines.append(line)
					for line in ParameterArea:
						OrderedLines.append(line)
				StatusArea = []
				CommandArea = []
				ParameterArea = []
				FirstDevice = False
			if pos+1 <> len(lines):		
				if lines[pos].rstrip() == "STATUS":
					InStatus = True
					InCommand = False
					InParameter = False
				if lines[pos].rstrip() == "COMMAND":
					InStatus = False
					InCommand = True
					InParameter = False
				if lines[pos].rstrip() == "PARAMETER":
					InStatus = False
					InCommand = False
					InParameter = True
			if InStatus:
				StatusArea.append(lines[pos])
			if InCommand:
				CommandArea.append(lines[pos])
			if InParameter:
				ParameterArea.append(lines[pos])
				
			if not InStatus and not InCommand and not InParameter:
				OrderedLines.append(lines[pos])
			pos = pos + 1				

	for line in StatusArea:
		OrderedLines.append(line)
	for line in CommandArea:
		OrderedLines.append(line)
	for line in ParameterArea:
		OrderedLines.append(line)
	
	
	print "Total ("+ str(DeviceNum) + ") device(s) pre-processed.\n"

def CloseLastVariable():
	global DevTypeBODY_CODE
	global EndString 
	global EndString2 
	global IsDouble
	
	if IsDouble:
		if EndString <> "":
			DevTypeBODY_CODE.append("       " + EndString)
			EndString = ""
		if EndString2 <> "":
			DevTypeBODY_CODE.append("       " + EndString2)
			EndString2 = ""
	else:	
		if EndString <> "":
			DevTypeBODY_CODE.append("       " + EndString)
			EndString = ""
	
def WriteDevType():
	
	global DevTypeHeader 
	global DevTypeVAR_INPUT 
	global DevTypeVAR_OUTPUT 
	global DevTypeVAR_INOUT 
	global DevTypeDB_SPEC 
	global DevTypeVAR_TEMP 
	global DevTypeBODY_HEADER
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global DevTypeBODY_END
	global ExternalSourceFile
	
	global MaxStatusReg
	global MaxCommandReg
	
	for line in DevTypeHeader:
		ExternalSourceFile.append(line)
		
	ExternalSourceFile.append("   VAR_INPUT")	
	for line in DevTypeVAR_INPUT:
		ExternalSourceFile.append(line)
	ExternalSourceFile.append("   END_VAR")	

	ExternalSourceFile.append("   VAR_OUTPUT")	
	for line in DevTypeVAR_OUTPUT:
		ExternalSourceFile.append(line)
	ExternalSourceFile.append("      DEVICE_PARAM_OK { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Bool;")
	ExternalSourceFile.append("   END_VAR")	

	ExternalSourceFile.append("   VAR_IN_OUT")	
	for line in DevTypeVAR_INOUT:
		ExternalSourceFile.append(line)
	ExternalSourceFile.append("   END_VAR")	

		
	ExternalSourceFile.append("   VAR")	
	ExternalSourceFile.append("      StatusReg { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[0.."+ str(MaxStatusReg) +"] of Word;")
	ExternalSourceFile.append("      CommandReg { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[0.."+ str(MaxCommandReg) +"] of Word;")
	ExternalSourceFile.append("   END_VAR")	
		
	for line in DevTypeDB_SPEC:
		ExternalSourceFile.append(line)
		
	for line in DevTypeVAR_TEMP:
		ExternalSourceFile.append(line)
		
	for line in DevTypeBODY_HEADER:
		ExternalSourceFile.append(line)
		
	if DevTypeBODY_CODE_ARRAY != []:
		ExternalSourceFile.append("        IF \"Utilities\".TestInProgress = FALSE THEN");
	for line in DevTypeBODY_CODE_ARRAY:
		ExternalSourceFile.append(line)
	if DevTypeBODY_CODE_ARRAY != []:
		ExternalSourceFile.append("        END_IF;");

	for line in DevTypeBODY_CODE:
		ExternalSourceFile.append(line)
		
	for line in DevTypeBODY_END:
		ExternalSourceFile.append(line)

	DevTypeHeader = []
	DevTypeVAR_INPUT = [] 
	DevTypeVAR_INOUT = [] 
	DevTypeVAR_OUTPUT = [] 
	DevTypeDB_SPEC = [] 
	DevTypeVAR_TEMP = [] 
	DevTypeBODY_HEADER = []
	DevTypeBODY_CODE = []
	DevTypeBODY_CODE_ARRAY = []
	DevTypeBODY_END = []

def WriteEPICS_PLC_TesterDB():
	
	global EPICS_PLC_TesterDB 
	global ExternalSourceFile

	ExternalSourceFile.append("DATA_BLOCK \"EPICS_PLC_Tester\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'FALSE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("   STRUCT")
	ExternalSourceFile.append("      HeartBeat { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Bool;")
	
	for line in EPICS_PLC_TesterDB:
		ExternalSourceFile.append(line)
		
	ExternalSourceFile.append("   END_STRUCT;")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("END_DATA_BLOCK")
	
	EPICS_PLC_TesterDB = []
	
def WriteDeviceInstances():
	
	global DeviceInstance 
	global ExternalSourceFile
	global Direct
	
	for line in DeviceInstance:
		ExternalSourceFile.append(line)
			
	DeviceInstance = []

def WriteEPICS_device_calls():
	
	global ExternalSourceFile
	global EPICS_device_calls_body 
	global EPICS_device_calls_header 
	global HASH 

	ExternalSourceFile.append("FUNCTION \"EPICS_device_calls\" : Void");
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
	ExternalSourceFile.append("VERSION : 1.0");
	ExternalSourceFile.append("");
	ExternalSourceFile.append("   VAR_TEMP");	
	
	for line in EPICS_device_calls_header:
		ExternalSourceFile.append(line)

	ExternalSourceFile.append("   END_VAR");
	ExternalSourceFile.append("");
	ExternalSourceFile.append("BEGIN");
	ExternalSourceFile.append("      //Author: Miklos Boros (miklos.boros@esss.se), Copyrigth 2017-2018 by European Spallation Source, Lund");
	ExternalSourceFile.append("      //This block was generated by InterfaceFactory");
	ExternalSourceFile.append("      //According to HASH:"+HASH);
	ExternalSourceFile.append("      //Description: Description: This function calls the devices according to the corresponding device type");
	ExternalSourceFile.append("");
	ExternalSourceFile.append("        //DO NOT Modify the following line!!!");
	ExternalSourceFile.append("        \"Utilities\".TestInProgress := FALSE;");
	ExternalSourceFile.append("");

	for line in EPICS_device_calls_body:
		ExternalSourceFile.append(line)
		
	ExternalSourceFile.append("END_FUNCTION");
	
	EPICS_device_calls_body = []
	EPICS_device_calls_header = []

def WriteEPICS_device_calls_test():
	
	global ExternalSourceFile
	global EPICS_device_calls_test_body 
	global EPICS_device_calls_test_header 
	global HASH 

	ExternalSourceFile.append("FUNCTION \"EPICS_device_calls_test\" : Void");
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
	ExternalSourceFile.append("VERSION : 1.0");
	ExternalSourceFile.append("");
	ExternalSourceFile.append("   VAR_TEMP");	
	
	for line in EPICS_device_calls_test_header:
		ExternalSourceFile.append(line)

	ExternalSourceFile.append("   END_VAR");
	ExternalSourceFile.append("");
	ExternalSourceFile.append("BEGIN");
	ExternalSourceFile.append("      //Author: Miklos Boros (miklos.boros@esss.se), Copyrigth 2017-2018 by European Spallation Source, Lund");
	ExternalSourceFile.append("      //This block was generated by InterfaceFactory");
	ExternalSourceFile.append("      //According to HASH:"+HASH);
	ExternalSourceFile.append("      //Description: Description: This function calls the devices according to the corresponding device type");
	ExternalSourceFile.append("");
	ExternalSourceFile.append("      //DO NOT Modify the following line!!!");
	ExternalSourceFile.append("      \"Utilities\".TestInProgress := TRUE;");
	ExternalSourceFile.append("");

	for line in EPICS_device_calls_test_body:
		ExternalSourceFile.append(line)
		
	ExternalSourceFile.append("END_FUNCTION");
	
	EPICS_device_calls_test_body = []
	EPICS_device_calls_test_header = []

def WriteDiagnostics(TIAVersion):
	
	global ExternalSourceFile
	global MAX_IO_DEVICES
	global MAX_LOCAL_MODULES
	global MAX_MODULES_IN_IO_DEVICE

	ExternalSourceFile.append("DATA_BLOCK \"DiagnosticsData\"")
	ExternalSourceFile.append("TITLE = Diagosis data DB")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'FALSE' }")
	ExternalSourceFile.append("AUTHOR : SIEMENS")
	ExternalSourceFile.append("FAMILY : Diagnose")
	ExternalSourceFile.append("NAME : '10'")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("//The global data block contains the data structure of the IO system, the control, the devices with the modules and an error buffer.")
	ExternalSourceFile.append("   STRUCT")
	ExternalSourceFile.append("      MainPLC { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Struct")
	ExternalSourceFile.append("         errorState { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Bool;   // if this is TRUE one of the modules has a problem")
	ExternalSourceFile.append("         ActuallyConfiguredCentralModules { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Int;   // Number of configured local modules. (CPU included)")
	ExternalSourceFile.append("         StateOfModules { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[1.."+str(MAX_LOCAL_MODULES)+"] of Bool;   // Status of the Modules FALSE=OK, TRUE=faulty,")
	ExternalSourceFile.append("         AddressOfModules { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[1.."+str(MAX_LOCAL_MODULES)+"] of HW_IO;   // Detected HW address if zero = module doesn't exists")
	ExternalSourceFile.append("      END_STRUCT;")
	for i in range(int(MAX_IO_DEVICES)):
		ExternalSourceFile.append("      IOSystem"+str(i+1)+" { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Struct")
		ExternalSourceFile.append("         errorState { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Bool;   // if this is TRUE one of the modules in the IO system has a problem")
		ExternalSourceFile.append("         errorType { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Byte;   // Status of  the IO system 1=OK, 2=faulty, 3=lost connection, 4=disabled")
		ExternalSourceFile.append("         ioSystemAddress { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : HW_DEVICE;   // Logical address of a device or slave (system constant in HW configuration)")
		ExternalSourceFile.append("         ioSystemId { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : UInt;   // ID of  IO System")
		ExternalSourceFile.append("         ioSystemname { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : String[50];   // Device name")
		ExternalSourceFile.append("         ActuallyConfiguredModules { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Int;   // Number of configured local IO cards (PN or DP head modul included)")
		ExternalSourceFile.append("         StateOfModules { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[1.."+str(MAX_MODULES_IN_IO_DEVICE)+"] of Bool;   // Status of the Modules FALSE=OK, TRUE=faulty,")
		ExternalSourceFile.append("         AddressOfModules { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[1.."+str(MAX_MODULES_IN_IO_DEVICE)+"] of HW_IO;   // Detected HW address if zero = module doesn't exists")
		ExternalSourceFile.append("      END_STRUCT;")
	ExternalSourceFile.append("   END_STRUCT;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("END_DATA_BLOCK")


	ExternalSourceFile.append("FUNCTION_BLOCK \"DiagStartupIoSystem\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_INPUT DB_SPECIFIC")
	ExternalSourceFile.append("      ioSystemHwId : HW_IOSYSTEM;   // This ID is representing the IO System (PN or DP), find the ID in the system constants")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_OUTPUT ")
	ExternalSourceFile.append("      status : Int;   // The return value of system function, where the last error occured")
	ExternalSourceFile.append("      instructionError : Int;   // Indicates in which system function the error occured: 1= DeviceStates PN , 2=GetName PN, 3=ModuleStates PN,  4=DeviceStates DP, 5= GetName DP. 6= ModuleStates DP")
	ExternalSourceFile.append("      errorIndex : Int;   // The last index of the respective loop, if an error occures")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_IN_OUT DB_SPECIFIC")
	ExternalSourceFile.append("      errorState { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Bool;   // if this is TRUE one of the modules in the IO system has a problem")
	ExternalSourceFile.append("      errorType { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Byte;   // Status of  the IO system 1=OK, 2=faulty, 3=lost connection, 4=disabled")
	ExternalSourceFile.append("      ioSystemAddress { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : HW_DEVICE;   // Logical address of a device or slave (system constant in HW configuration)")
	ExternalSourceFile.append("      ioSystemId { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : UInt;   // ID of  IO System")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("   VAR_IN_OUT ")
	ExternalSourceFile.append("      ioSystemname : String;   // Device name")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("   VAR_IN_OUT DB_SPECIFIC")
	ExternalSourceFile.append("      ActuallyConfiguredModules { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Int;   // Number of configured local IO cards (PN or DP head modul included)")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("   VAR_IN_OUT ")
	ExternalSourceFile.append("      StateOfModules : Array[1.."+str(MAX_MODULES_IN_IO_DEVICE)+"] of Bool;   // Status of the Modules FALSE=OK, TRUE=faulty,")
	ExternalSourceFile.append("      AddressOfModules : Array[1.."+str(MAX_MODULES_IN_IO_DEVICE)+"] of HW_IO;   // Detected HW address if zero = module doesn't exists")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR ")
	ExternalSourceFile.append("      statGeoAddr {OriginalPartName := 'GEOADDR'; LibVersion := '1.0'; S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : GEOADDR;   // Slot information")
	ExternalSourceFile.append("      statGeoLaddr { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : HW_ANY;   // GEO2LOG hardware identifier")
	ExternalSourceFile.append("      statConfiguredDevices { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[0..1023] of Bool;   // Temporary storage of the return of \"DeviceStates\", to combine the states of the devices with numbers and names")
	ExternalSourceFile.append("      statExistingDevices : Array[0..1023] of Bool;   // Temporary storage of the return of \"DeviceStates\", to combine the states of the devices with numbers and names")
	ExternalSourceFile.append("      statFaultyDevices : Array[0..1023] of Bool;   // Temporary storage of the return of \"DeviceStates\", to combine the states of the divices with numbers and names")
	ExternalSourceFile.append("      statDisabledDevices { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[0..1023] of Bool;   // Storage of the status of all devices in the PN IO System --> State: Disabled")
	ExternalSourceFile.append("      statProblemDevices { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[0..1023] of Bool;   // Storage of the status of all devices in the PN IO System --> State: Problem")
	ExternalSourceFile.append("      statDeviceModuleStates : Array[0..127] of Bool;   // Storage of the status of all modules in the PN Devices --> State: Problem")
	ExternalSourceFile.append("      instGetNameDevices {OriginalPartName := 'FB_806_S71500'; LibVersion := '1.3'} : Get_Name;   // Instance of system function \"GetName\"")
	ExternalSourceFile.append("      statInitString : String;   // Used to initialize the temporary string to convert into STRING[50]")
	ExternalSourceFile.append("      statResetStatesOld : Bool;   // Detect a rising edge at ResetStates")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_TEMP ")
	ExternalSourceFile.append("      tempSlotIndex : Int;   // Loop index")
	ExternalSourceFile.append("      tempModuleNum : Int;   // index module number")
	ExternalSourceFile.append("      tempRetValGeo : Int;   // GEO2LOG error information")
	ExternalSourceFile.append("      tempRetValDeviceStates : Int;   // DeviceStates error information")
	ExternalSourceFile.append("      tempRetValModuleStates : Int;   // Return value system function ModuleStates")
	ExternalSourceFile.append("      tempStringConvert : String;   // Store the device names temporary here, to convert them into STRING[50]")
	ExternalSourceFile.append("      tempIoSystemError : Bool;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR CONSTANT ")
	ExternalSourceFile.append("      STATE_CONFIGURED : USInt := 1;   // Used for instruction DeviceStates, read out all configured devices")
	ExternalSourceFile.append("      STATE_FAULTY : USInt := 2;   // Used for instruction DeviceStates, read out all faulty devices")
	ExternalSourceFile.append("      STATE_DISABLED : USInt := 3;   // Used for instruction DeviceStates, read out all disabled devices")
	ExternalSourceFile.append("      STATE_EXIST : USInt := 4;   // Used for instruction DeviceStates, read out all devices not reachable")
	ExternalSourceFile.append("      STATE_PROBLEM : USInt := 5;   // Used for instruction DeviceStates, read out all devices with several problems")
	ExternalSourceFile.append("      DEVICE_SLAVE : USInt := 2;   // GEO2LOG structure: HW type = 2")
	ExternalSourceFile.append("      MODULE_OF_DEVICE : USInt := 4;   // GEO2LOG structure: HW type = 4")
	ExternalSourceFile.append("      IO_SYSTEM_AREA : USInt := 1;   // GEO2LOG structure: Area = 1")
	ExternalSourceFile.append("      DP_SYSTEM_AREA : USInt := 2;   // GEO2LOG structure: Area = 2")
	ExternalSourceFile.append("      ERR_DEV_STATE_DEVICES : USInt := 1;   // Identifies the instruction behind the error code of output \"Status\" --> DeviceStates PN (Configured, faulty, existing)")
	ExternalSourceFile.append("      ERR_GET_NAME_DEVICES : USInt := 2;   // Identifies the instruction behind the error code of output \"Status\" -->  GetName of devices PN")
	ExternalSourceFile.append("      ERR_MOD_STAT_DEVICES : USInt := 3;   // Identifies the instruction behind the error code of output \"Status\" --> ModuleStates PN")
	ExternalSourceFile.append("      ERR_DEV_STAT_PN : USInt := 1;   // Value for output instruction error, DeviceStates PN devices")
	ExternalSourceFile.append("      ERR_MOD_STAT_PN : USInt := 4;   // Value for output instruction error, ModuleStates PN devices")
	ExternalSourceFile.append("      MAX_SLAVES_DP : Int := 127;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros")
	ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Functionality: Determine hardware identifier and module states from ")
	ExternalSourceFile.append("	//               PN or DP IO system")
	ExternalSourceFile.append("	// ")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Please Note:")
	ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code")
	ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Change log table:")
	ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied")
	ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for InterfaceFactory ")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// CONFIGURED DEVICES")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// Find out how much devices are configured in the IO System --> PROFINET IO")
	ExternalSourceFile.append("	// This number is the maximum number of devices, which will be checked in the")
	ExternalSourceFile.append("	// following programm")
	ExternalSourceFile.append("	#tempRetValDeviceStates := DeviceStates(LADDR := #ioSystemHwId,")
	ExternalSourceFile.append("	                                        MODE := #STATE_CONFIGURED,")
	ExternalSourceFile.append("	                                        STATE := #statConfiguredDevices);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// Check if the block call was successful")
	ExternalSourceFile.append("	IF (#tempRetValDeviceStates <> 0)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	  // Error handling")
	ExternalSourceFile.append("	  #status := #tempRetValDeviceStates;")
	ExternalSourceFile.append("	  #instructionError := #ERR_DEV_STATE_DEVICES;")
	ExternalSourceFile.append("	  // Call ok --> store the actual number of configured devices    ")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	  ;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// EXISTING DEVICES")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	#tempRetValDeviceStates := DeviceStates(LADDR := #ioSystemHwId,")
	ExternalSourceFile.append("	                                        MODE := #STATE_EXIST,")
	ExternalSourceFile.append("	                                        STATE := #statExistingDevices);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// Check if the block call was successful")
	ExternalSourceFile.append("	IF (#tempRetValDeviceStates <> 0)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	  // Error handling")
	ExternalSourceFile.append("	  #status := #tempRetValDeviceStates;")
	ExternalSourceFile.append("	  #instructionError := #ERR_DEV_STATE_DEVICES;")
	ExternalSourceFile.append("	  // Call ok --> store the actual number of configured devices    ")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	  ;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// FAULTY DEVICES")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	#tempRetValDeviceStates := DeviceStates(LADDR := #ioSystemHwId,")
	ExternalSourceFile.append("	                                        MODE := #STATE_FAULTY,")
	ExternalSourceFile.append("	                                        STATE := #statFaultyDevices);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// Check if the block call was successful")
	ExternalSourceFile.append("	IF (#tempRetValDeviceStates <> 0)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	  // Error handling")
	ExternalSourceFile.append("	  #status := #tempRetValDeviceStates;")
	ExternalSourceFile.append("	  #instructionError := #ERR_DEV_STATE_DEVICES;")
	ExternalSourceFile.append("	  // Call ok --> store the actual number of configured devices    ")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	  ;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// Find out the number of the assigned IO system, to define if it is")
	ExternalSourceFile.append("	// a PN or DP Network")
	ExternalSourceFile.append("	#tempRetValGeo := LOG2GEO(LADDR := #ioSystemHwId,")
	ExternalSourceFile.append("	                          GEOADDR := #statGeoAddr);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// set IO system ID")
	ExternalSourceFile.append("	#ioSystemId := #statGeoAddr.IOSYSTEM;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// Inilize the structure for system function GEO2LOG")
	ExternalSourceFile.append("	#statGeoAddr.HWTYPE := #DEVICE_SLAVE;   // Hardware type 2: IO device")
	ExternalSourceFile.append("	// Predefine the type OF IO system. Either Profinet IO or Profibus DP")
	ExternalSourceFile.append("	IF ((#statGeoAddr.IOSYSTEM >= 100) ")
	ExternalSourceFile.append("	  AND (#statGeoAddr.IOSYSTEM <= 115))")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	  #statGeoAddr.AREA := #IO_SYSTEM_AREA;   // Area ID 1: PROFINET IO")
	ExternalSourceFile.append("	ELSIF ((#statGeoAddr.IOSYSTEM >= 1)")
	ExternalSourceFile.append("	  AND (#statGeoAddr.IOSYSTEM <= 32))")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	  #statGeoAddr.AREA := #DP_SYSTEM_AREA;   // Area ID 2: Profibus DP")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	  ;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// The devices are configured --> Read out the logical address and the")
	ExternalSourceFile.append("	// device name")
	ExternalSourceFile.append("	IF (#statConfiguredDevices[1] = TRUE)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	    	    ")
	ExternalSourceFile.append("	    // Station number ")
	ExternalSourceFile.append("	    #statGeoAddr.STATION := 1;")
	ExternalSourceFile.append("	    // read LADDR from devices")
	ExternalSourceFile.append("	    #tempRetValGeo := GEO2LOG(GEOADDR := #statGeoAddr,")
	ExternalSourceFile.append("	                              LADDR => #statGeoLaddr);")
	ExternalSourceFile.append("	    // Everything is ok!")
	ExternalSourceFile.append("	    IF (#tempRetValGeo = 0)")
	ExternalSourceFile.append("	    THEN")
	ExternalSourceFile.append("	        // store LADDR from devices in diagnostic data block")
	ExternalSourceFile.append("	        #ioSystemAddress := #statGeoLaddr;")
	ExternalSourceFile.append("	        ")
	ExternalSourceFile.append("	        // Store the device name, if the device is existing")
	ExternalSourceFile.append("	        // Get name is an acyclic instruction. In the startup OB, the")
	ExternalSourceFile.append("	        // instruction has to be repeated until it is done or error")
	ExternalSourceFile.append("	        REPEAT")
	ExternalSourceFile.append("	            // Get device name of each decive in PN System")
	ExternalSourceFile.append("	            #instGetNameDevices(LADDR := #ioSystemHwId,")
	ExternalSourceFile.append("	                                STATION_NR := #statGeoAddr.STATION,")
	ExternalSourceFile.append("	                                DATA := #tempStringConvert);")
	ExternalSourceFile.append("	            ")
	ExternalSourceFile.append("	        UNTIL (#instGetNameDevices.DONE = TRUE)")
	ExternalSourceFile.append("	            OR (#instGetNameDevices.ERROR = TRUE)")
	ExternalSourceFile.append("	        END_REPEAT;")
	ExternalSourceFile.append("	        ")
	ExternalSourceFile.append("	        IF (#instGetNameDevices.ERROR = TRUE)")
	ExternalSourceFile.append("	        THEN")
	ExternalSourceFile.append("	            // Error handling")
	ExternalSourceFile.append("	            #status := WORD_TO_INT(#instGetNameDevices.STATUS);")
	ExternalSourceFile.append("	            #instructionError := #ERR_GET_NAME_DEVICES;")
	ExternalSourceFile.append("	            #errorIndex := 1;")
	ExternalSourceFile.append("	            ")
	ExternalSourceFile.append("	            // Everything is ok --> Convert the String[254] into String[50]    ")
	ExternalSourceFile.append("	        ELSIF (#instGetNameDevices.DONE = TRUE)")
	ExternalSourceFile.append("	        THEN")
	ExternalSourceFile.append("	            // Cut all characters more than 50 to reduce the string length")
	ExternalSourceFile.append("	            #ioSystemname := DELETE(IN := #tempStringConvert,")
	ExternalSourceFile.append("	                                    L := 204,")
	ExternalSourceFile.append("	                                    P := 50);")
	ExternalSourceFile.append("	            ")
	ExternalSourceFile.append("	            // Initialize the temporary string before next loop")
	ExternalSourceFile.append("	            #tempStringConvert := #statInitString;")
	ExternalSourceFile.append("	        ELSE")
	ExternalSourceFile.append("	            ;")
	ExternalSourceFile.append("	        END_IF;")
	ExternalSourceFile.append("	    ELSE")
	ExternalSourceFile.append("	        // If the return value ist not = 0 --> the device/system/module is")
	ExternalSourceFile.append("	        // not configured --> No error handling")
	ExternalSourceFile.append("	        // set LADDR from devices to 0 in diagnostic data block")
	ExternalSourceFile.append("	        #ioSystemAddress := 0;")
	ExternalSourceFile.append("	        #ioSystemname := '';")
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	    // Check if the configured devices are faulty or lost once through")
	ExternalSourceFile.append("	    // the startup!")
	ExternalSourceFile.append("	    IF (#statExistingDevices[1] = TRUE)")
	ExternalSourceFile.append("	    THEN")
	ExternalSourceFile.append("	        IF (#statFaultyDevices[1] = TRUE)")
	ExternalSourceFile.append("	        THEN")
	ExternalSourceFile.append("	            ")
	ExternalSourceFile.append("	            #errorType := 2;")
	ExternalSourceFile.append("	            #errorState := TRUE;")
	ExternalSourceFile.append("	            ")
	ExternalSourceFile.append("	            // The device is not faulty and does exist --> set state ok!    ")
	ExternalSourceFile.append("	        ELSE")
	ExternalSourceFile.append("	            #errorType := 1;")
	ExternalSourceFile.append("	            #errorState := FALSE;")
	ExternalSourceFile.append("	        END_IF;")
	ExternalSourceFile.append("	        // The connection to the device is lost at the moment    ")
	ExternalSourceFile.append("	    ELSE")
	ExternalSourceFile.append("	        #errorType := 3;")
	ExternalSourceFile.append("	        #errorState := TRUE;")
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	    // No device is configured   ")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	    ;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// Get the logical address of all modules and store the actual number of")
	ExternalSourceFile.append("	// modules from each device")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// Inilize the structure for system function GEO2LOG")
	ExternalSourceFile.append("	#statGeoAddr.HWTYPE := #MODULE_OF_DEVICE;   // Hardware type 4: Module")
	ExternalSourceFile.append("	FOR #tempModuleNum := 1 TO "+str(MAX_MODULES_IN_IO_DEVICE)+" DO")
	ExternalSourceFile.append("	    // Slot number")
	ExternalSourceFile.append("	    #statGeoAddr.SLOT := INT_TO_UINT(#tempModuleNum);")
	ExternalSourceFile.append("	    // read LADDR from modules")
	ExternalSourceFile.append("	    #tempRetValGeo := GEO2LOG(GEOADDR := #statGeoAddr,")
	ExternalSourceFile.append("	                              LADDR => #statGeoLaddr);")
	ExternalSourceFile.append("	    // check Retval")
	ExternalSourceFile.append("	    IF (#tempRetValGeo = 0)")
	ExternalSourceFile.append("	    THEN")
	ExternalSourceFile.append("	        // store LADDR from modules in diagnostic data block")
	ExternalSourceFile.append("	        #AddressOfModules[#tempModuleNum] := #statGeoLaddr;")
	ExternalSourceFile.append("	        #ActuallyConfiguredModules := #ActuallyConfiguredModules + 1;")
	ExternalSourceFile.append("	    ELSE")
	ExternalSourceFile.append("	        // If the return value ist not = 0 --> the device/system/module is")
	ExternalSourceFile.append("	        // not configured --> No error handling")
	ExternalSourceFile.append("	        // set LADDR from modules to 0 in diagnostic data block")
	ExternalSourceFile.append("	        #AddressOfModules[#tempModuleNum] := 0;")
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	END_FOR;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// Check modules of faulty Devices")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// Check the state of the configured devices")
	ExternalSourceFile.append("	IF (#errorType = 2)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	    // The device is reachable, but faulty because of an error in a")
	ExternalSourceFile.append("	    // subordinated system --> check the modules")
	ExternalSourceFile.append("	    #tempRetValModuleStates := ModuleStates(LADDR := #ioSystemAddress,")
	ExternalSourceFile.append("	                                            MODE := #STATE_PROBLEM,")
	ExternalSourceFile.append("	                                            STATE := #statDeviceModuleStates);")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	    IF (#tempRetValModuleStates <> 0)")
	ExternalSourceFile.append("	    THEN")
	ExternalSourceFile.append("	        // Error hanlding")
	ExternalSourceFile.append("	        #status := #tempRetValModuleStates;")
	ExternalSourceFile.append("	        #instructionError := #ERR_MOD_STAT_DEVICES;")
	ExternalSourceFile.append("	    ELSE")
	ExternalSourceFile.append("	        // Store the state of the different module in the diag DB")
	ExternalSourceFile.append("	        FOR #tempSlotIndex := 1 TO #ActuallyConfiguredModules DO")
	ExternalSourceFile.append("	            IF (#statDeviceModuleStates[#tempSlotIndex] = TRUE)")
	ExternalSourceFile.append("	            THEN")
	ExternalSourceFile.append("	                #StateOfModules[#tempSlotIndex] := TRUE;")
	ExternalSourceFile.append("	            ELSE")
	ExternalSourceFile.append("	                #StateOfModules[#tempSlotIndex] := FALSE;")
	ExternalSourceFile.append("	            END_IF;")
	ExternalSourceFile.append("	        END_FOR;")
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	ELSIF (#errorType = 3)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	    FOR #tempSlotIndex := 1 TO #ActuallyConfiguredModules DO")
	ExternalSourceFile.append("	        IF (#AddressOfModules[#tempSlotIndex] <> 0)")
	ExternalSourceFile.append("	        THEN")
	ExternalSourceFile.append("	            #StateOfModules[#tempSlotIndex] := TRUE;")
	ExternalSourceFile.append("	        END_IF;")
	ExternalSourceFile.append("	    END_FOR;")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	    ; // no faulty device --> nothing to do!")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_FUNCTION_BLOCK")
	
	
	ExternalSourceFile.append("DATA_BLOCK \"DiagStartupIoSystem_iDB\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("\"DiagStartupIoSystem\"")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")
	

	ExternalSourceFile.append("FUNCTION_BLOCK \"DiagStartupPlc\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_OUTPUT ")
	ExternalSourceFile.append("      status : Int;   // The return value of system function, where the last error occured")
	ExternalSourceFile.append("      instructionError : Int;   // Indicates in which system function the error occured: 1= DeviceStates PN , 2=GetName PN, 3=ModuleStates PN,  4=DeviceStates DP, 5= GetName DP. 6= ModuleStates DP")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR ")
	ExternalSourceFile.append("      statGeoAddr {OriginalPartName := 'GEOADDR'; LibVersion := '1.0'; S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : GEOADDR;   // Slot information")
	ExternalSourceFile.append("      statGeoLaddr { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : HW_ANY;   // GEO2LOG hardware identifier")
	ExternalSourceFile.append("      statActualCentralModules : USInt := 0;   // Actual number of modules in the central station (PLC)")
	ExternalSourceFile.append("      statPlcModuleStates : Array[0..127] of Bool;   // Storage of the status of all modules in the PLC central station --> State: Problem")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_TEMP ")
	ExternalSourceFile.append("      tempModuleNum : Int;   // index module number")
	ExternalSourceFile.append("      tempRetValGeo : Int;   // GEO2LOG error information")
	ExternalSourceFile.append("      tempRetValModuleStates : Int;   // Return value system function ModuleStates")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR CONSTANT ")
	ExternalSourceFile.append("      MODULE_OF_PLC : USInt := 4;   // GEO2LOG structure: HW type = 4")
	ExternalSourceFile.append("      CPU : USInt := 0;   // GEO2LOG structure: Area = 0")
	ExternalSourceFile.append("      CENTRAL_SYSTEM : USInt := 0;   // GEO2LOG structure: IO System = 0")
	ExternalSourceFile.append("      CENTRAL_STATION : USInt;   // GEO2LOG structure: Station = 0")
	ExternalSourceFile.append("      HW_ID_PLC_MODULES : HW_DEVICE := 32;   // HW ID of the PLC, which is needed for getting the module states --> fix value")
	ExternalSourceFile.append("      STATE_PROBLEM : USInt := 5;   // Used for instruction DeviceStates, read out all devices with several problems")
	ExternalSourceFile.append("      ERR_MOD_STAT_CENTRAL : USInt := 3;   // Value for output instruction error, ModuleStates local modules")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros")
	ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Functionality: Determine hardware identifier and module states from local")
	ExternalSourceFile.append("	//               modules")
	ExternalSourceFile.append("	// ")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Please Note:")
	ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code")
	ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Change log table:")
	ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied")
	ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for InterfaceFactory ")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// Determine hardware identifier from LOCAL MODULES")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	#statGeoAddr.HWTYPE := #MODULE_OF_PLC;      // Hardware type 4: module")
	ExternalSourceFile.append("	#statGeoAddr.AREA := #CPU;                  // Area ID 0: CPU")
	ExternalSourceFile.append("	#statGeoAddr.IOSYSTEM := #CENTRAL_SYSTEM;   // PROFINET IO system")
	ExternalSourceFile.append("	                                            // (0 = central unit in the rack)")
	ExternalSourceFile.append("	#statGeoAddr.STATION := #CENTRAL_STATION;   // Number of the rack")
	ExternalSourceFile.append("	                                            // if area identifier")
	ExternalSourceFile.append("	                                            //  AREA = 0 (central module).")
	ExternalSourceFile.append("	                                            //  ")
	ExternalSourceFile.append("	\"DiagnosticsData\".MainPLC.errorState := FALSE;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	FOR #tempModuleNum := 1 TO "+str(MAX_LOCAL_MODULES)+" DO")
	ExternalSourceFile.append("	  // Slot number")
	ExternalSourceFile.append("	  #statGeoAddr.SLOT := INT_TO_UINT(#tempModuleNum);")
	ExternalSourceFile.append("	  // read LADDR from local modules")
	ExternalSourceFile.append("	  #tempRetValGeo := GEO2LOG(GEOADDR := #statGeoAddr,")
	ExternalSourceFile.append("	                            LADDR => #statGeoLaddr);")
	ExternalSourceFile.append("	  // check Retval")
	ExternalSourceFile.append("	  IF (#tempRetValGeo = 0)")
	ExternalSourceFile.append("	  THEN")
	ExternalSourceFile.append("	    // store LADDR from local modules in diagnostic data block")
	ExternalSourceFile.append("	      \"DiagnosticsData\".MainPLC.AddressOfModules[#tempModuleNum] := #statGeoLaddr;")
	ExternalSourceFile.append("	      #statActualCentralModules := #statActualCentralModules + 1;")
	ExternalSourceFile.append("	  ELSE")
	ExternalSourceFile.append("	    // If the return value ist not = 0 --> the device/system/module is not")
	ExternalSourceFile.append("	    // configured --> No error handling")
	ExternalSourceFile.append("	    // set LADDR from local modules to 0 in diagnostic data block")
	ExternalSourceFile.append("	      \"DiagnosticsData\".MainPLC.AddressOfModules[#tempModuleNum] := 0;")
	ExternalSourceFile.append("	      \"DiagnosticsData\".MainPLC.StateOfModules[#tempModuleNum] := FALSE;")
	ExternalSourceFile.append("	  END_IF;")
	ExternalSourceFile.append("	  // Store the actual configured devices in the diagnostics DB")
	ExternalSourceFile.append("	  \"DiagnosticsData\".MainPLC.ActuallyConfiguredCentralModules := #statActualCentralModules;")
	ExternalSourceFile.append("	END_FOR;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// Check module states from LOCAL MODULES")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// Check if central module are available - at least one module is always")
	ExternalSourceFile.append("	// configured, the PLC itself")
	ExternalSourceFile.append("	IF (\"DiagnosticsData\".MainPLC.ActuallyConfiguredCentralModules > 1)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	  // Check the status of the local modules")
	ExternalSourceFile.append("	  #tempRetValModuleStates := ModuleStates(LADDR := #HW_ID_PLC_MODULES,")
	ExternalSourceFile.append("	                                          MODE := #STATE_PROBLEM,")
	ExternalSourceFile.append("	                                          STATE := #statPlcModuleStates);")
	ExternalSourceFile.append("	  ")
	ExternalSourceFile.append("	  // Check if the block call was successful")
	ExternalSourceFile.append("	  IF (#tempRetValModuleStates <> 0)")
	ExternalSourceFile.append("	  THEN")
	ExternalSourceFile.append("	    // Error handling")
	ExternalSourceFile.append("	    #status := #tempRetValModuleStates;")
	ExternalSourceFile.append("	    #instructionError := #ERR_MOD_STAT_CENTRAL;")
	ExternalSourceFile.append("	  ELSE")
	ExternalSourceFile.append("	    ; // Everything is ok!")
	ExternalSourceFile.append("	  END_IF;")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	  ; // There are no central module configured")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("		")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// set module states from LOCAL MODULES")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// If the first bit in the array is true, at least one module is faulty")
	ExternalSourceFile.append("	IF (#statPlcModuleStates[0] = TRUE)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	  // Check which of the modules are faulty")
	ExternalSourceFile.append("	  // PLC modules array starts at index 2 for the first local module")
	ExternalSourceFile.append("	    FOR #tempModuleNum := 2 TO (\"DiagnosticsData\".MainPLC.ActuallyConfiguredCentralModules + 1) DO")
	ExternalSourceFile.append("	    IF (#statPlcModuleStates[#tempModuleNum] = TRUE)")
	ExternalSourceFile.append("	    THEN")
	ExternalSourceFile.append("	        \"DiagnosticsData\".MainPLC.StateOfModules[#tempModuleNum - 1] := TRUE;")
	ExternalSourceFile.append("	        \"DiagnosticsData\".MainPLC.errorState := TRUE;")
	ExternalSourceFile.append("	    ELSE")
	ExternalSourceFile.append("	        \"DiagnosticsData\".MainPLC.StateOfModules[#tempModuleNum - 1] := false;")
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	  END_FOR;")
	ExternalSourceFile.append("	  ")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	  // Everything is ok!")
	ExternalSourceFile.append("	    FOR #tempModuleNum := 1 TO \"DiagnosticsData\".MainPLC.ActuallyConfiguredCentralModules DO")
	ExternalSourceFile.append("	        \"DiagnosticsData\".MainPLC.StateOfModules[#tempModuleNum] := FALSE;")
	ExternalSourceFile.append("	  END_FOR;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_FUNCTION_BLOCK")

	ExternalSourceFile.append("DATA_BLOCK \"DiagStartupPlc_IDB\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("\"DiagStartupPlc\"")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")
	
	
	ExternalSourceFile.append("FUNCTION \"DiagnosticError\" : Void")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_INPUT ")
	ExternalSourceFile.append("      ioState : Word;   // IO state of the HW object")
	ExternalSourceFile.append("      laddr : HW_ANY;   // Hardware identifier")
	ExternalSourceFile.append("      channel : UInt;   // Channel number")
	ExternalSourceFile.append("      multiError : Bool;   // =true if more than one error is present")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_TEMP ")
	ExternalSourceFile.append("      tempGeoAddr {OriginalPartName := 'GEOADDR'; LibVersion := '1.0'} : GEOADDR;   // Geographical address of the disturbed Module / Device")
	ExternalSourceFile.append("      tempRetVal : Int;   // Return value of LOG2GEO")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR CONSTANT ")
	ExternalSourceFile.append("      GOOD : Word := 16#01;   // Status of the hardware object: Bit 0: Good")
	ExternalSourceFile.append("      AREA_CENTRAL : UInt := 0;   // Area ID for PLC")
	ExternalSourceFile.append("      AREA_PROFINET : UInt := 1;   // Area ID for PROFINET IO")
	ExternalSourceFile.append("      AREA_PROFIBUS : UInt := 2;   // Area ID for PROFIBUS DP")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros")
	ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Functionality: Evaluate Diagnostic interrupt OB information for PLC and")
	ExternalSourceFile.append("	//               devices")
	ExternalSourceFile.append("	// ")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Please Note:")
	ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code")
	ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Change log table:")
	ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied")
	ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for InterfaceFactory ")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// evaluate IO state from Diagnostic interrupt OB")
	ExternalSourceFile.append("	// and set information to DiagnosticsData DB")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// determine geographic address of faulty device")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	#tempRetVal := LOG2GEO(LADDR := #laddr,")
	ExternalSourceFile.append("	                       GEOADDR := #tempGeoAddr);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// evaluate diagnosis information for devices in an IO system")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	IF (#tempGeoAddr.AREA = #AREA_PROFINET)")
	ExternalSourceFile.append("	    OR (#tempGeoAddr.AREA = #AREA_PROFIBUS)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	    	    ")
	for i in range(int(MAX_IO_DEVICES)):
		ExternalSourceFile.append("	    //=============================================================================")
		ExternalSourceFile.append("	    // Check IO system "+str(i+1)+" ")
		ExternalSourceFile.append("	    //=============================================================================")
		ExternalSourceFile.append("	    IF \"DiagnosticsData\".IOSystem"+str(i+1)+".ioSystemId = #tempGeoAddr.IOSYSTEM")
		ExternalSourceFile.append("	    THEN")
		ExternalSourceFile.append("	        IF (#tempGeoAddr.STATION <= "+str(MAX_IO_DEVICES)+")")
		ExternalSourceFile.append("	            AND (#tempGeoAddr.SLOT+1 <= "+str(MAX_MODULES_IN_IO_DEVICE)+")")
		ExternalSourceFile.append("	        THEN")
		ExternalSourceFile.append("	          // evaluate diagnosis information IO system")
		ExternalSourceFile.append("	          IF (#ioState = #GOOD)")
		ExternalSourceFile.append("	          THEN")
		ExternalSourceFile.append("	              \"DiagnosticsData\".IOSystem"+str(i+1)+".errorState := False;")
		ExternalSourceFile.append("	              \"DiagnosticsData\".IOSystem"+str(i+1)+".StateOfModules[#tempGeoAddr.SLOT+1] := false;")
		ExternalSourceFile.append("	              ")
		ExternalSourceFile.append("	          ELSE")
		ExternalSourceFile.append("	              \"DiagnosticsData\".IOSystem"+str(i+1)+".errorState := TRUE;")
		ExternalSourceFile.append("	              \"DiagnosticsData\".IOSystem"+str(i+1)+".errorType := 2;")
		ExternalSourceFile.append("	              \"DiagnosticsData\".IOSystem"+str(i+1)+".StateOfModules[#tempGeoAddr.SLOT+1] := true;")
		ExternalSourceFile.append("	          END_IF;")
		ExternalSourceFile.append("	        END_IF; ")
		ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	    //=============================================================================")
	ExternalSourceFile.append("	    // evaluate diagnosis information for PLC")
	ExternalSourceFile.append("	    //=============================================================================")
	ExternalSourceFile.append("	ELSIF (#tempGeoAddr.AREA = #AREA_CENTRAL)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	    IF (#tempGeoAddr.SLOT+1 <= "+str(MAX_LOCAL_MODULES)+")")
	ExternalSourceFile.append("	    THEN")
	ExternalSourceFile.append("	        // evaluate diagnosis information PLC")
	ExternalSourceFile.append("	        IF (#ioState = #GOOD)")
	ExternalSourceFile.append("	        THEN")
	ExternalSourceFile.append("	            \"DiagnosticsData\".MainPLC.StateOfModules[#tempGeoAddr.SLOT+1]:= false;")
	ExternalSourceFile.append("	        ELSE")
	ExternalSourceFile.append("	            \"DiagnosticsData\".MainPLC.StateOfModules[#tempGeoAddr.SLOT+1] := true;")
	ExternalSourceFile.append("	        END_IF;")
	ExternalSourceFile.append("	    END_IF; ")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	    ;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_FUNCTION")
	
	ExternalSourceFile.append("FUNCTION \"PullOrPlugModules\" : Void")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_INPUT ")
	ExternalSourceFile.append("      laddr : HW_IO;   // Hardware identifier")
	ExternalSourceFile.append("      eventClass : Byte;   // 16#38/39: module inserted, removed")
	ExternalSourceFile.append("      faultId : Byte;   // Fault identifier")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_TEMP ")
	ExternalSourceFile.append("      tempGeoAddr {OriginalPartName := 'GEOADDR'; LibVersion := '1.0'} : GEOADDR;   // Geographical address of the disturbed Module / Device")
	ExternalSourceFile.append("      tempRetVal : Int;   // Return value of LOG2GEO")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR CONSTANT ")
	ExternalSourceFile.append("      AREA_CENTRAL : UInt := 0;   // Area ID for PLC")
	ExternalSourceFile.append("      AREA_PROFINET : UInt := 1;   // Area ID for PROFINET IO")
	ExternalSourceFile.append("      AREA_PROFIBUS : UInt := 2;   // Area ID for PROFIBUS DP")
	ExternalSourceFile.append("      MODULE_PLUGGED : Byte := 16#38;   // (Sub)module plugged")
	ExternalSourceFile.append("      MODULE_PULLED : Byte := 16#39;   // (Sub)module pulled or not responding")
	ExternalSourceFile.append("      MODULE_MATCHES : Byte := 16#54;   // IO submodule inserted and matches configured submodule")
	ExternalSourceFile.append("      MODULE_OK : Byte := 16#61;   // Module inserted, module type OK")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros")
	ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Functionality: Evaluate Pull/plug interrupt OB information for PLC and")
	ExternalSourceFile.append("	//               devices")
	ExternalSourceFile.append("	// ")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Please Note:")
	ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code")
	ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Change log table:")
	ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied")
	ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for InterfaceFactory ")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	#tempRetVal := LOG2GEO(LADDR := #laddr,")
	ExternalSourceFile.append("	                       GEOADDR := #tempGeoAddr);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// evaluate diagnosis information for devices in an IO system")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	IF (#tempGeoAddr.AREA = #AREA_PROFINET)")
	ExternalSourceFile.append("	    OR (#tempGeoAddr.AREA = #AREA_PROFIBUS)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	")
	for i in range(int(MAX_IO_DEVICES)):
		ExternalSourceFile.append("	    //=============================================================================")
		ExternalSourceFile.append("	    // Check IO system "+str(i+1)+" ")
		ExternalSourceFile.append("	    //=============================================================================")
		ExternalSourceFile.append("	    IF \"DiagnosticsData\".IOSystem"+str(i+1)+".ioSystemId = #tempGeoAddr.IOSYSTEM")
		ExternalSourceFile.append("	    THEN")
		ExternalSourceFile.append("	        IF (#tempGeoAddr.STATION <= "+str(MAX_IO_DEVICES)+")")
		ExternalSourceFile.append("	            AND (#tempGeoAddr.SLOT+1 <= "+str(MAX_MODULES_IN_IO_DEVICE)+")")
		ExternalSourceFile.append("	        THEN")
		ExternalSourceFile.append("	            // check modules plugged")
		ExternalSourceFile.append("	            IF (#eventClass = #MODULE_PLUGGED)")
		ExternalSourceFile.append("	            THEN")
		ExternalSourceFile.append("	                // reset error state only if the correct module is inserted")
		ExternalSourceFile.append("	                IF (#faultId = #MODULE_MATCHES)")
		ExternalSourceFile.append("	                    OR (#faultId = #MODULE_OK)")
		ExternalSourceFile.append("	                THEN")
		ExternalSourceFile.append("	                    \"DiagnosticsData\".IOSystem"+str(i+1)+".errorState := False;")
		ExternalSourceFile.append("	                    \"DiagnosticsData\".IOSystem"+str(i+1)+".StateOfModules[#tempGeoAddr.SLOT+1] := false;")
		ExternalSourceFile.append("	                END_IF;")
		ExternalSourceFile.append("	                ")
		ExternalSourceFile.append("	                // check modules pulled  ")
		ExternalSourceFile.append("	            ELSIF (#eventClass = #MODULE_PULLED)")
		ExternalSourceFile.append("	            THEN")
		ExternalSourceFile.append("	                \"DiagnosticsData\".IOSystem"+str(i+1)+".errorState := TRUE;")
		ExternalSourceFile.append("	                \"DiagnosticsData\".IOSystem"+str(i+1)+".errorType := 2;")
		ExternalSourceFile.append("	                \"DiagnosticsData\".IOSystem"+str(i+1)+".StateOfModules[#tempGeoAddr.SLOT+1] := true;")
		ExternalSourceFile.append("	                ")
		ExternalSourceFile.append("	            ELSE")
		ExternalSourceFile.append("	                ;")
		ExternalSourceFile.append("	            END_IF;")
		ExternalSourceFile.append("	        END_IF;")
		ExternalSourceFile.append("	        ")
		ExternalSourceFile.append("	    END_IF;")
		ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	    //=============================================================================")
	ExternalSourceFile.append("	    // evaluate diagnosis information for PLC")
	ExternalSourceFile.append("	    //=============================================================================")
	ExternalSourceFile.append("	ELSIF (#tempGeoAddr.AREA = #AREA_CENTRAL)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	    IF (#tempGeoAddr.SLOT+1 <= "+str(MAX_LOCAL_MODULES)+")")
	ExternalSourceFile.append("	    THEN")
	ExternalSourceFile.append("	        IF (#eventClass = #MODULE_PLUGGED)")
	ExternalSourceFile.append("	        THEN")
	ExternalSourceFile.append("	            IF (#faultId = #MODULE_MATCHES)")
	ExternalSourceFile.append("	                OR (#faultId = #MODULE_OK)")
	ExternalSourceFile.append("	            THEN")
	ExternalSourceFile.append("	                \"DiagnosticsData\".MainPLC.StateOfModules[#tempGeoAddr.SLOT+1] := false;")
	ExternalSourceFile.append("	            END_IF;")
	ExternalSourceFile.append("	            ")
	ExternalSourceFile.append("	        ELSIF (#eventClass = #MODULE_PULLED)")
	ExternalSourceFile.append("	        THEN")
	ExternalSourceFile.append("	            \"DiagnosticsData\".MainPLC.StateOfModules[#tempGeoAddr.SLOT+1] := true;")
	ExternalSourceFile.append("	        ELSE")
	ExternalSourceFile.append("	            ;")
	ExternalSourceFile.append("	        END_IF;")
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	    ;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("END_FUNCTION")
	
	ExternalSourceFile.append("FUNCTION \"RackOrStationFaliure\" : Void")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_INPUT ")
	if (TIAVersion == "13"):
		ExternalSourceFile.append("      laddr : HW_IO;   // Hardware identifier")
	if (TIAVersion == "14"):
		ExternalSourceFile.append("      laddr : HW_DEVICE;   // Hardware identifier")
	ExternalSourceFile.append("      eventClass : Byte;   // Event class")
	ExternalSourceFile.append("      faultId : Byte;   // Fault identifier")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_TEMP ")
	ExternalSourceFile.append("      index : Int;   // index system")
	ExternalSourceFile.append("      tempSlotIndex : Int;   // Loop index")
	ExternalSourceFile.append("      tempIoSystemIndex : Int;   // Index for IO System")
	ExternalSourceFile.append("      tempGeoAddr {OriginalPartName := 'GEOADDR'; LibVersion := '1.0'} : GEOADDR;   // Geographical address of the disturbed Module / Device")
	ExternalSourceFile.append("      tempRetVal : Int;   // Return value of LOG2GEO")
	ExternalSourceFile.append("      tempRetValModuleStates : Int;   // Return value system function ModuleStates")
	ExternalSourceFile.append("      tempDeviceModuleStates : Array[0..127] of Bool;   // Storage of the status of all modules in the PN Devices --> State: Problem")
	ExternalSourceFile.append("      tempLaddr : HW_DEVICE;   // logical address of the disturbed Module / Device")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR CONSTANT ")
	ExternalSourceFile.append("      AREA_CENTRAL : UInt := 0;   // Area ID for PLC")
	ExternalSourceFile.append("      AREA_PROFINET : UInt := 1;   // Area ID for PROFINET IO")
	ExternalSourceFile.append("      AREA_PROFIBUS : UInt := 2;   // Area ID for PROFIBUS DP")
	ExternalSourceFile.append("      SLAVE_DEVICE_RET : Byte := 16#38;   // return of a DP slave / IO device")
	ExternalSourceFile.append("      SLAVE_DEVICE_FAIL : Byte := 16#39;   // Failure of a DP slave / IO device")
	ExternalSourceFile.append("      DP_SLAVE_FAIL_RET : Byte := 16#C4;   // Failure/return of a DP slave")
	ExternalSourceFile.append("      IO_DEVICE_FAIL_RET : Byte := 16#CB;   // Failure/return of a PROFINET IO device")
	ExternalSourceFile.append("      STATE_PROBLEM : USInt := 5;   // Used for instruction DeviceStates, read out all devices with several problems")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros")
	ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Functionality: Evaluate Rack/Station interrupt OB information for PLC and")
	ExternalSourceFile.append("	//               devices")
	ExternalSourceFile.append("	// ")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Please Note:")
	ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code")
	ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Change log table:")
	ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied")
	ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for InterfaceFactory ")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// evaluate event class from Rack error OB")
	ExternalSourceFile.append("	// and set information to DiagnosticsData DB")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// determine geographic address of faulty device")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	#tempRetVal := LOG2GEO(LADDR := #laddr,")
	ExternalSourceFile.append("	                       GEOADDR := #tempGeoAddr);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// evaluate diagnosis information for devices in an IO system")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	IF (#tempGeoAddr.AREA = #AREA_PROFINET)")
	ExternalSourceFile.append("	    OR (#tempGeoAddr.AREA = #AREA_PROFIBUS)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	    ")
	for i in range(int(MAX_IO_DEVICES)):
		ExternalSourceFile.append("	    //=============================================================================")
		ExternalSourceFile.append("	    // Check IO system "+str(i+1)+" ")
		ExternalSourceFile.append("	    //=============================================================================")
		ExternalSourceFile.append("	    IF \"DiagnosticsData\".IOSystem"+str(i+1)+".ioSystemId = #tempGeoAddr.IOSYSTEM")
		ExternalSourceFile.append("	    THEN")
		ExternalSourceFile.append("	        // check DP slave or IO device return ")
		ExternalSourceFile.append("	        IF (#eventClass = #SLAVE_DEVICE_RET)")
		ExternalSourceFile.append("	        THEN")
		ExternalSourceFile.append("	            // reset error state only if the slave or device state is OK")
		ExternalSourceFile.append("	            IF (#faultId = #DP_SLAVE_FAIL_RET)")
		ExternalSourceFile.append("	                OR (#faultId = #IO_DEVICE_FAIL_RET)")
		ExternalSourceFile.append("	            THEN")
		ExternalSourceFile.append("	                \"DiagnosticsData\".IOSystem"+str(i+1)+".errorState := FALSE;")
		ExternalSourceFile.append("	                ")
		ExternalSourceFile.append("	                FOR #tempSlotIndex := 1 TO \"DiagnosticsData\".IOSystem"+str(i+1)+".ActuallyConfiguredModules DO")
		ExternalSourceFile.append("	                    \"DiagnosticsData\".IOSystem"+str(i+1)+".StateOfModules[#tempSlotIndex] := FALSE;")
		ExternalSourceFile.append("	                END_FOR;")
		ExternalSourceFile.append("	                ")
		ExternalSourceFile.append("	            ELSE")
		ExternalSourceFile.append("	                ")
		ExternalSourceFile.append("	                // The device is reachable, but faulty because of an error in a")
		ExternalSourceFile.append("	                // subordinated system --> check the modules")
		ExternalSourceFile.append("	                #tempRetVal := GEO2LOG(LADDR => #tempLaddr,")
		ExternalSourceFile.append("	                                       GEOADDR := #tempGeoAddr);")
		ExternalSourceFile.append("	                ")
		ExternalSourceFile.append("	                #tempRetValModuleStates := ModuleStates(LADDR := #tempLaddr,")
		ExternalSourceFile.append("	                                                        MODE := #STATE_PROBLEM,")
		ExternalSourceFile.append("	                                                        STATE := #tempDeviceModuleStates);")
		ExternalSourceFile.append("	                ")
		ExternalSourceFile.append("	                IF (#tempRetValModuleStates = 0)")
		ExternalSourceFile.append("	                THEN")
		ExternalSourceFile.append("	                    // Store the state of the different module in the diag DB")
		ExternalSourceFile.append("	                    FOR #tempSlotIndex := 1 TO  \"DiagnosticsData\".IOSystem"+str(i+1)+".ActuallyConfiguredModules DO")
		ExternalSourceFile.append("	                        IF (#tempDeviceModuleStates[#tempSlotIndex ] = TRUE)")
		ExternalSourceFile.append("	                        THEN")
		ExternalSourceFile.append("	                            \"DiagnosticsData\".IOSystem"+str(i+1)+".StateOfModules[#tempSlotIndex] := TRUE;")
		ExternalSourceFile.append("	                        ELSE")
		ExternalSourceFile.append("	                            \"DiagnosticsData\".IOSystem"+str(i+1)+".StateOfModules[#tempSlotIndex] := FALSE;")
		ExternalSourceFile.append("	                        END_IF;")
		ExternalSourceFile.append("	                    END_FOR;")
		ExternalSourceFile.append("	                END_IF;")
		ExternalSourceFile.append("	                ")
		ExternalSourceFile.append("	                \"DiagnosticsData\".IOSystem"+str(i+1)+".errorType := 2;")
		ExternalSourceFile.append("	                ")
		ExternalSourceFile.append("	            END_IF;")
		ExternalSourceFile.append("	            ")
		ExternalSourceFile.append("	            // check DP slave or IO device failure ")
		ExternalSourceFile.append("	        ELSIF (#eventClass = #SLAVE_DEVICE_FAIL)")
		ExternalSourceFile.append("	        THEN")
		ExternalSourceFile.append("	            \"DiagnosticsData\".IOSystem"+str(i+1)+".errorState := TRUE;")
		ExternalSourceFile.append("	            \"DiagnosticsData\".IOSystem"+str(i+1)+".errorType := 3;")
		ExternalSourceFile.append("	            ")
		ExternalSourceFile.append("	            FOR #tempSlotIndex := 1 TO \"DiagnosticsData\".IOSystem"+str(i+1)+".ActuallyConfiguredModules DO")
		ExternalSourceFile.append("	                IF \"DiagnosticsData\".IOSystem"+str(i+1)+".AddressOfModules[#tempSlotIndex] <> 0")
		ExternalSourceFile.append("	                THEN")
		ExternalSourceFile.append("	                    \"DiagnosticsData\".IOSystem"+str(i+1)+".StateOfModules[#tempSlotIndex] := TRUE;")
		ExternalSourceFile.append("	                END_IF;")
		ExternalSourceFile.append("	            END_FOR;")
		ExternalSourceFile.append("	            ")
		ExternalSourceFile.append("	        ELSE")
		ExternalSourceFile.append("	            ;")
		ExternalSourceFile.append("	        END_IF;")
		ExternalSourceFile.append("	    ")
		ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	    //=============================================================================")
	ExternalSourceFile.append("	    //evaluate diagnosis information for PLC")
	ExternalSourceFile.append("	    //=============================================================================")
	ExternalSourceFile.append("	ELSIF (#tempGeoAddr.AREA = #AREA_CENTRAL)")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	    IF (#tempGeoAddr.SLOT+1 <= "+str(MAX_LOCAL_MODULES)+")")
	ExternalSourceFile.append("	    THEN")
	ExternalSourceFile.append("	        // check DP slave or IO device return ")
	ExternalSourceFile.append("	        IF (#eventClass = #SLAVE_DEVICE_RET)")
	ExternalSourceFile.append("	        THEN")
	ExternalSourceFile.append("	            IF (#faultId = #DP_SLAVE_FAIL_RET)")
	ExternalSourceFile.append("	                OR (#faultId = #IO_DEVICE_FAIL_RET)")
	ExternalSourceFile.append("	            THEN")
	ExternalSourceFile.append("	                \"DiagnosticsData\".MainPLC.StateOfModules[#tempGeoAddr.SLOT+1] := false;")
	ExternalSourceFile.append("	            END_IF;")
	ExternalSourceFile.append("	            ")
	ExternalSourceFile.append("	            // check DP slave or IO device failure ")
	ExternalSourceFile.append("	        ELSIF (#eventClass = #SLAVE_DEVICE_FAIL)")
	ExternalSourceFile.append("	        THEN")
	ExternalSourceFile.append("	            \"DiagnosticsData\".MainPLC.StateOfModules[#tempGeoAddr.SLOT+1] := true;")
	ExternalSourceFile.append("	        ELSE")
	ExternalSourceFile.append("	            ;")
	ExternalSourceFile.append("	        END_IF;")
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	    ;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("END_FUNCTION")

	ExternalSourceFile.append("FUNCTION_BLOCK \"Diagnostics\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_TEMP ")
	ExternalSourceFile.append("      retValLed : Int;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR CONSTANT ")
	ExternalSourceFile.append("      ERROR_LED : UInt := 2;   // Identification number of the ERROR LED")
	ExternalSourceFile.append("      ERROR_LED_ON : UInt := 4;   // LED status Color 1 flashing")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros")
	ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Functionality: Basic diagnostic function that has to be called in every cycle")
	ExternalSourceFile.append("	// ")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Please Note:")
	ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code")
	ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Change log table:")
	ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied")
	ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for InterfaceFactory ")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	// check error active")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	#retValLed := LED(LADDR := \"Local~Common\", LED := #ERROR_LED);")
	ExternalSourceFile.append("	IF #retValLed = #ERROR_LED_ON")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	    \"DiagnosticsData\".MainPLC.errorState := TRUE;")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	    \"DiagnosticsData\".MainPLC.errorState := FALSE;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_FUNCTION_BLOCK")

	ExternalSourceFile.append("DATA_BLOCK \"Diagnostics_iDB\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("\"Diagnostics\"")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")

	ExternalSourceFile.append("ORGANIZATION_BLOCK \"CyclicDiagnostics\"")
	ExternalSourceFile.append("TITLE = \"Main Program Sweep (Cycle)\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	\"Diagnostics_iDB\"();")
	ExternalSourceFile.append("END_ORGANIZATION_BLOCK")

	ExternalSourceFile.append("ORGANIZATION_BLOCK \"Diagnostic error interrupt\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros")
	ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Functionality: Diagnostic error interrupt OB ")
	ExternalSourceFile.append("	// ")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Please Note:")
	ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code")
	ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Change log table:")
	ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied")
	ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for InterfaceFactory ")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	\"DiagnosticError\"(ioState:=#IO_State,")
	ExternalSourceFile.append("	                  laddr:=#LADDR,")
	ExternalSourceFile.append("	                  channel:=#Channel,")
	ExternalSourceFile.append("	                  multiError:=#MultiError);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_ORGANIZATION_BLOCK")

	ExternalSourceFile.append("ORGANIZATION_BLOCK \"Pull or plug of modules\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros")
	ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Functionality: Pull or plug of modules interrupt OB ")
	ExternalSourceFile.append("	// ")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Please Note:")
	ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code")
	ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Change log table:")
	ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied")
	ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for InterfaceFactory ")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	\"PullOrPlugModules\"(laddr:=#LADDR,")
	ExternalSourceFile.append("	                    eventClass:=#Event_Class,")
	ExternalSourceFile.append("	                    faultId:=#Fault_ID);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_ORGANIZATION_BLOCK")

	ExternalSourceFile.append("ORGANIZATION_BLOCK \"Rack or station failure\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros")
	ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Functionality: Rack/Station interrupt OB ")
	ExternalSourceFile.append("	// ")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Please Note:")
	ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code")
	ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Change log table:")
	ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied")
	ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for InterfaceFactory ")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	\"RackOrStationFaliure\"(laddr:=#LADDR,")
	ExternalSourceFile.append("	                       eventClass:=#Event_Class,")
	ExternalSourceFile.append("	                       faultId:=#Fault_ID);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_ORGANIZATION_BLOCK")

	ExternalSourceFile.append("ORGANIZATION_BLOCK \"Startup\"")
	ExternalSourceFile.append("TITLE = \"Complete Restart\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros")
	ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Functionality:")
	ExternalSourceFile.append("	//        This OB is a Startup OB, it will be called after OB100 and before the main cycle.")
	ExternalSourceFile.append("	// ")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Please Note:")
	ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code")
	ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//Change log table:")
	ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied")
	ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for InterfaceFactory ")
	ExternalSourceFile.append("	//=============================================================================")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Initialize the Main PLC Diagnostic")
	ExternalSourceFile.append("	\"DiagStartupPlc_IDB\"();")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	")
	for i in range(int(MAX_IO_DEVICES)):
		ExternalSourceFile.append("	//Initialize IOSystem"+str(i+1))
		ExternalSourceFile.append("	\"DiagStartupIoSystem_iDB\"(ioSystemHwId := 261,")
		ExternalSourceFile.append("	                          errorState := \"DiagnosticsData\".IOSystem"+str(i+1)+".errorState,")
		ExternalSourceFile.append("	                          errorType := \"DiagnosticsData\".IOSystem"+str(i+1)+".errorType,")
		ExternalSourceFile.append("	                          ioSystemAddress := \"DiagnosticsData\".IOSystem"+str(i+1)+".ioSystemAddress,")
		ExternalSourceFile.append("	                          ioSystemId := \"DiagnosticsData\".IOSystem"+str(i+1)+".ioSystemId,")
		ExternalSourceFile.append("	                          ioSystemname := \"DiagnosticsData\".IOSystem"+str(i+1)+".ioSystemname,")
		ExternalSourceFile.append("	                          ActuallyConfiguredModules := \"DiagnosticsData\".IOSystem"+str(i+1)+".ActuallyConfiguredModules,")
		ExternalSourceFile.append("	                          StateOfModules := \"DiagnosticsData\".IOSystem"+str(i+1)+".StateOfModules,")
		ExternalSourceFile.append("	                          AddressOfModules := \"DiagnosticsData\".IOSystem"+str(i+1)+".AddressOfModules);")
		ExternalSourceFile.append("	")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_ORGANIZATION_BLOCK")

def WriteStandardPLCCode(TIAVersion):
	
	global ExternalSourceFile


	ExternalSourceFile.append("FUNCTION \"UTIL_P_TRIG\" : Void")
	ExternalSourceFile.append("TITLE = Positive Edge Detection Pulse")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_INPUT ")
	ExternalSourceFile.append("      \"i_Input Bit\" : Bool;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_IN_OUT ")
	ExternalSourceFile.append("      \"iq_Trigger Bit\" : Bool;")
	ExternalSourceFile.append("      \"iq_Pulse Bit\" : Bool;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//Prositive edge generator for SCL")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	IF #\"i_Input Bit\" AND #\"iq_Trigger Bit\"")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	    #\"iq_Pulse Bit\" := FALSE;")
	ExternalSourceFile.append("	ELSIF #\"i_Input Bit\"")
	ExternalSourceFile.append("	    THEN")
	ExternalSourceFile.append("	        #\"iq_Pulse Bit\" := TRUE;")
	ExternalSourceFile.append("	        #\"iq_Trigger Bit\" := TRUE;")
	ExternalSourceFile.append("	    ELSE")
	ExternalSourceFile.append("	        #\"iq_Pulse Bit\" := FALSE;")
	ExternalSourceFile.append("	        #\"iq_Trigger Bit\" := FALSE;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("END_FUNCTION")

	ExternalSourceFile.append("FUNCTION_BLOCK \"_UtilitiesFB\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_INPUT ")
	ExternalSourceFile.append("      CPUSytemMemoryBits : Byte;   // Address of system memory byte")
	ExternalSourceFile.append("      CPUClockMemoryBits : Byte;   // Address of clock memory byte")
	ExternalSourceFile.append("      StartupDelaySP : Time;   // Delay before startup delay bit turned on")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR ")
	ExternalSourceFile.append("      AlwaysOn : Bool;   // Bit always TRUE")
	ExternalSourceFile.append("      AlwaysTrue : Bool;   // Bit always TRUE")
	ExternalSourceFile.append("      AlwaysOff : Bool;   // Bit always FALSE")
	ExternalSourceFile.append("      AlwaysFalse : Bool;   // Bit always FALSE")
	ExternalSourceFile.append("      FirstScan : Bool;   // Bit TRUE for only the first scan of the PLC")
	ExternalSourceFile.append("      StartupDelayDn : Bool;   // Bit initially FALSE, turning TRUE after preset delay")
	if (TIAVersion == "13"):
		ExternalSourceFile.append("      StartupDelayTmr {OriginalPartName := 'IEC_TIMER'; LibVersion := '1.0'} : TON_TIME;")
	if (TIAVersion == "14"):
		ExternalSourceFile.append("      StartupDelayTmr {OriginalPartName := 'IEC_TIMER'; LibVersion := '1.0'} : IEC_TIMER;")
	ExternalSourceFile.append("      Square_100ms : Bool;   // Bit FALSE/TRUE based on square wave (100 ms frequency)")
	ExternalSourceFile.append("      Square_100msONS : Bool;")
	ExternalSourceFile.append("      Pulse_100ms : Bool;   // Bit TRUE every 100 ms for one PLC scan")
	ExternalSourceFile.append("      Square_200ms : Bool;   // Bit FALSE/TRUE based on square wave (200 ms frequency)")
	ExternalSourceFile.append("      Square_200msONS : Bool;")
	ExternalSourceFile.append("      Pulse_200ms : Bool;   // Bit TRUE every 200 ms for one PLC scan")
	ExternalSourceFile.append("      Square_400ms : Bool;   // Bit FALSE/TRUE based on square wave (400 ms frequency)")
	ExternalSourceFile.append("      Square_400msONS : Bool;")
	ExternalSourceFile.append("      Pulse_400ms : Bool;   // Bit TRUE every 400 ms for one PLC scan")
	ExternalSourceFile.append("      Square_500ms : Bool;   // Bit FALSE/TRUE based on square wave (500 ms frequency)")
	ExternalSourceFile.append("      Square_500msONS : Bool;")
	ExternalSourceFile.append("      Pulse_500ms : Bool;   // Bit TRUE every 500 ms for one PLC scan")
	ExternalSourceFile.append("      Square_800ms : Bool;   // Bit FALSE/TRUE based on square wave (800 ms frequency)")
	ExternalSourceFile.append("      Square_800msONS : Bool;")
	ExternalSourceFile.append("      Pulse_800ms : Bool;   // Bit TRUE every 800 ms for one PLC scan")
	ExternalSourceFile.append("      Square_1s : Bool;   // Bit FALSE/TRUE based on square wave (1 s frequency)")
	ExternalSourceFile.append("      Square_1sONS : Bool;")
	ExternalSourceFile.append("      Pulse_1s : Bool;   // Bit TRUE every 1 s for one PLC scan")
	ExternalSourceFile.append("      Square_1600ms : Bool;   // Bit FALSE/TRUE based on square wave (1600 ms frequency)")
	ExternalSourceFile.append("      Square_1600msONS : Bool;")
	ExternalSourceFile.append("      Pulse_1600ms : Bool;   // Bit TRUE every 1600 ms for one PLC scan")
	ExternalSourceFile.append("      Square_2s : Bool;   // Bit FALSE/TRUE based on square wave (2 s frequency)")
	ExternalSourceFile.append("      Square_2sONS : Bool;")
	ExternalSourceFile.append("      Pulse_2s : Bool;   // Bit TRUE every 2 s for one PLC scan")
	ExternalSourceFile.append("      TestInProgress : Bool;   // Indicates which caller FC is used")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//This block provides standard \"Utilities\" tags that can be used in the rest OF the PLC code such")
	ExternalSourceFile.append("	//as:")
	ExternalSourceFile.append("	//* Always On")
	ExternalSourceFile.append("	//* Always Off")
	ExternalSourceFile.append("	//* Startup Delay")
	ExternalSourceFile.append("	//* Pulses (different frequences)")
	ExternalSourceFile.append("	//* etc.")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//When using This block in your program, name the instance DB \"Utilities\" AND THEN you will be able TO use tags like \"Utilities.AlwaysOn\" in the rest OF your program.")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//This block relies On information provided BY the CPU. This needs TO be enabled in the CPU hardware configuration under System AND Clock Memory.")
	ExternalSourceFile.append("	//Enable both functions AND pick memory bytes you'd like TO use (defauls are %MB1 AND %MB0 respectively).")
	ExternalSourceFile.append("	//THEN connect the selected Byte TO the inputs OF This block.")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Bit TRUE for only the first scan of the PLC")
	ExternalSourceFile.append("	#FirstScan := #CPUSytemMemoryBits.%X0;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Bit always TRUE")
	ExternalSourceFile.append("	#AlwaysOn := #CPUSytemMemoryBits.%X2;")
	ExternalSourceFile.append("	#AlwaysTrue := #CPUSytemMemoryBits.%X2;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Bit always FALSE")
	ExternalSourceFile.append("	#AlwaysOff := #CPUSytemMemoryBits.%X3;")
	ExternalSourceFile.append("	#AlwaysFalse := #CPUSytemMemoryBits.%X3;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Bit initially FALSE, turning TRUE after preset delay")
	if (TIAVersion == "13"):
		ExternalSourceFile.append("	#StartupDelayTmr(IN := #AlwaysTrue,")
		ExternalSourceFile.append("	                 PT := #StartupDelaySP,")
		ExternalSourceFile.append("	                 Q => #StartupDelayDn);")
	if (TIAVersion == "14"):
		ExternalSourceFile.append("	#StartupDelayTmr.TON(IN := #AlwaysTrue,")
		ExternalSourceFile.append("	                     PT := #StartupDelaySP,")
		ExternalSourceFile.append("	                     Q => #StartupDelayDn);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Bit TRUE every 100 ms FOR one PLC scan")
	ExternalSourceFile.append("	#Square_100ms := #CPUClockMemoryBits.%X0;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_100ms,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_100msONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_100ms);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Bit TRUE every 200 ms FOR one PLC scan")
	ExternalSourceFile.append("	#Square_200ms := #CPUClockMemoryBits.%X1;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_200ms,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_200msONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_200ms);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Bit TRUE every 400 ms FOR one PLC scan")
	ExternalSourceFile.append("	#Square_400ms := #CPUClockMemoryBits.%X2;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_400ms,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_400msONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_400ms);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Bit TRUE every 500 ms FOR one PLC scan")
	ExternalSourceFile.append("	#Square_500ms := #CPUClockMemoryBits.%X3;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_500ms,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_500msONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_500ms);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Bit TRUE every 800 ms FOR one PLC scan")
	ExternalSourceFile.append("	#Square_800ms := #CPUClockMemoryBits.%X4;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_800ms,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_800msONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_800ms);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Bit TRUE every 1 s FOR one PLC scan")
	ExternalSourceFile.append("	#Square_1s := #CPUClockMemoryBits.%X5;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_1s,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_1sONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_1s);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Bit TRUE every 1600 ms FOR one PLC scan")
	ExternalSourceFile.append("	#Square_1600ms := #CPUClockMemoryBits.%X6;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_1600ms,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_1600msONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_1600ms);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Bit TRUE every 2s FOR one PLC scan")
	ExternalSourceFile.append("	#Square_2s := #CPUClockMemoryBits.%X7;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_2s,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_2sONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_2s);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_FUNCTION_BLOCK")

	ExternalSourceFile.append("DATA_BLOCK \"Utilities\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("\"_UtilitiesFB\"")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")

	ExternalSourceFile.append("DATA_BLOCK \"EPICSToPLC\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'FALSE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("//########## EPICS->PLC datablock ##########")
	ExternalSourceFile.append("   STRUCT ")
	ExternalSourceFile.append("      \"Word\" : Array[0..10] of Word;")
	ExternalSourceFile.append("   END_STRUCT;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK	")

	ExternalSourceFile.append("DATA_BLOCK \"PLCToEPICS\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'FALSE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("//########## PLC->EPICS datablock ##########")
	ExternalSourceFile.append("   STRUCT ")
	ExternalSourceFile.append("      \"Word\" : Array[0..10] of Word;")
	ExternalSourceFile.append("   END_STRUCT;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")

	ExternalSourceFile.append("FUNCTION \"_CommsEPICSDataMappingFBFactory\" : Void")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("//This blocks maps data to/from PLC/EPICS data exchange block")
	ExternalSourceFile.append("   VAR_INPUT ")
	ExternalSourceFile.append("      EPICSToPLCLength : Int;   // Length of device command register array (in words)")
	ExternalSourceFile.append("      EPICSToPLCDataBlockOffset : Int;   // Offset in EPICS->PLC comms block where this device data resides (in words)")
	ExternalSourceFile.append("      EPICSToPLCParametersStart : Int;   // The border offset between the Command and the Parameter area")
	ExternalSourceFile.append("      PLCToEPICSLength : Int;   // Length of device status register array (in words)")
	ExternalSourceFile.append("      PLCToEPICSDataBlockOffset : Int;   // Offset in PLC->EPICS comms block where this device data resides (in words)")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_IN_OUT ")
	ExternalSourceFile.append("      EPICSToPLCCommandRegisters : Variant;   // Pointer to device command registers (header of the array of words)")
	ExternalSourceFile.append("      PLCToEPICSStatusRegisters : Variant;   // Pointer to device status registers (header of the array of words)")
	ExternalSourceFile.append("      EPICSToPLCDataBlock : Variant;   // Pointer to EPICS->PLC data exchange block (header of the array of words)")
	ExternalSourceFile.append("      PLCToEPICSDataBlock : Variant;   // Pointer to PLC->EPICS data exchange block (header of the array of words)")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_TEMP ")
	ExternalSourceFile.append("      temp : Int;")
	ExternalSourceFile.append("      ZeroWord : Word;")
	ExternalSourceFile.append("      LoopCounter : Int;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	(*")
	ExternalSourceFile.append("	  Author:       Nick Levchenko")
	ExternalSourceFile.append("	  Modified:     Miklos Boros")
	ExternalSourceFile.append("	  ")
	ExternalSourceFile.append("	  Description:  This function maps the the data between any device and PLC/EPICS communication blocks.")
	ExternalSourceFile.append("	                Every device data that needs to be communicated to EPICS needs to have so called \"communication registers\".")
	ExternalSourceFile.append("	                They should be implemented inside the device FB as:")
	ExternalSourceFile.append("	                CommandReg  Array [0..x] of Word")
	ExternalSourceFile.append("	                StatusReg   Array [0..x] of Word")
	ExternalSourceFile.append("	                Parameters  Array [0..x] of Word")
	ExternalSourceFile.append("	                To map device data to PLC/EPICS data exchange blocks call this function and provide pointers to device communication registers,")
	ExternalSourceFile.append("	                their lengths, pointers to PLC/EPICS data exchange blocks and offsets in those block where this device data should go.")
	ExternalSourceFile.append("	                ")
	ExternalSourceFile.append("	                Status registers are simply copied from device to data exchange block.")
	ExternalSourceFile.append("	                Command registers are copied from data exchange blocks to device and CLEARED. This is to accept commands only once. ")
	ExternalSourceFile.append("	                Parameter registers are copied from data exchange blocks to device WITHOUT clearing. This means this are can be used for SetPoints and other parameters.")
	ExternalSourceFile.append("	*)")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// Map command/parameter registers")
	ExternalSourceFile.append("	IF #EPICSToPLCLength > 0 THEN")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	    #temp := MOVE_BLK_VARIANT(")
	ExternalSourceFile.append("	                              SRC := #EPICSToPLCDataBlock,")
	ExternalSourceFile.append("	                              COUNT := INT_TO_UDINT(#EPICSToPLCLength),")
	ExternalSourceFile.append("	                              SRC_INDEX := #EPICSToPLCDataBlockOffset,")
	ExternalSourceFile.append("	                              DEST_INDEX := 0,")
	ExternalSourceFile.append("	                              DEST => #EPICSToPLCCommandRegisters);")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	    IF (NOT \"Utilities\".TestInProgress) THEN")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	        //Clear commands, but leave parameters unchanged (loop through all command registers AND write 0 TO them)    ")
	ExternalSourceFile.append("	        #ZeroWord := 0;")
	ExternalSourceFile.append("	        IF (#EPICSToPLCParametersStart = #EPICSToPLCLength) THEN")
	ExternalSourceFile.append("	            FOR #LoopCounter := 0 TO (#EPICSToPLCLength - 1) DO")
	ExternalSourceFile.append("	                ")
	ExternalSourceFile.append("	                #temp := MOVE_BLK_VARIANT(SRC := #ZeroWord,")
	ExternalSourceFile.append("	                                          COUNT := 1,")
	ExternalSourceFile.append("	                                          SRC_INDEX := 0,")
	ExternalSourceFile.append("	                                          DEST_INDEX := #EPICSToPLCDataBlockOffset + #LoopCounter,")
	ExternalSourceFile.append("	                                          DEST => #EPICSToPLCDataBlock);")
	ExternalSourceFile.append("	            END_FOR;")
	ExternalSourceFile.append("	        ELSE")
	ExternalSourceFile.append("	            IF (#EPICSToPLCParametersStart > 0) THEN")
	ExternalSourceFile.append("	                FOR #LoopCounter := 0 TO (#EPICSToPLCParametersStart - 1) DO")
	ExternalSourceFile.append("	                    ")
	ExternalSourceFile.append("	                    #temp := MOVE_BLK_VARIANT(SRC := #ZeroWord,")
	ExternalSourceFile.append("	                                              COUNT := 1,")
	ExternalSourceFile.append("	                                              SRC_INDEX := 0,")
	ExternalSourceFile.append("	                                              DEST_INDEX := #EPICSToPLCDataBlockOffset + #LoopCounter,")
	ExternalSourceFile.append("	                                              DEST => #EPICSToPLCDataBlock);")
	ExternalSourceFile.append("	                END_FOR;")
	ExternalSourceFile.append("	            END_IF;")
	ExternalSourceFile.append("	        END_IF;")
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// Map status registers")
	ExternalSourceFile.append("	IF #PLCToEPICSLength > 0 THEN")
	ExternalSourceFile.append("	    #temp := MOVE_BLK_VARIANT(")
	ExternalSourceFile.append("	                              SRC := #PLCToEPICSStatusRegisters,")
	ExternalSourceFile.append("	                              COUNT := INT_TO_UDINT(#PLCToEPICSLength),")
	ExternalSourceFile.append("	                              SRC_INDEX := 0,")
	ExternalSourceFile.append("	                              DEST_INDEX := #PLCToEPICSDataBlockOffset,")
	ExternalSourceFile.append("	                              DEST => #PLCToEPICSDataBlock);")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_FUNCTION")

	ExternalSourceFile.append("	FUNCTION \"_CommsEPICSDataMap\" : Void")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_TEMP ")
	ExternalSourceFile.append("      Hash : DInt;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	        //Comms data generation hash")
	ExternalSourceFile.append("	        #Hash := DInt#104734097;")
	ExternalSourceFile.append("	        \"PLCToEPICS\".\"Word\"[1] := DINT_TO_WORD(#Hash);")
	ExternalSourceFile.append("	        \"PLCToEPICS\".\"Word\"[0] := DINT_TO_WORD(SHR(IN := #Hash, N := 16));")
	ExternalSourceFile.append("	        ")
	ExternalSourceFile.append("END_FUNCTION")

	ExternalSourceFile.append("FUNCTION_BLOCK \"_CommsPLC_EPICS\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_INPUT ")
	ExternalSourceFile.append("      Enable : Bool;   // Enable all comms")
	ExternalSourceFile.append("      SendTrigger : Bool;   // Trigger for PLC->EPICS data send (should be quick and cyclic)")
	ExternalSourceFile.append("      BytesToSend : Int;   // Number of bytes for PLC->EPICS data send")
	ExternalSourceFile.append("      InterfaceID : HW_ANY;   // Hardware identifier of Ethernet port to be used (see under device configuration)")
	ExternalSourceFile.append("      S7ConnectionID : Int := 256;   // Connection ID for EPICS s7plc driver connection")
	ExternalSourceFile.append("      MBConnectionID : Int := 255;   // Connection ID for EPICS modbus driver connection")
	ExternalSourceFile.append("      S7Port : Int := 2000;   // PLC port for EPICS s7plc driver connection")
	ExternalSourceFile.append("      MBPort : Int := 502;   // PLC port for EPICS modbus driver connection")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_OUTPUT ")
	ExternalSourceFile.append("      SendDone : Bool;")
	ExternalSourceFile.append("      SendBusy : Bool;")
	ExternalSourceFile.append("      SendError : Bool;")
	ExternalSourceFile.append("      SendStatus : Word;")
	ExternalSourceFile.append("      RcvNewDataReady : Bool;")
	ExternalSourceFile.append("      RcvDataRead : Bool;")
	ExternalSourceFile.append("      RcvError : Bool;")
	ExternalSourceFile.append("      RcvStatus : Word;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_IN_OUT ")
	ExternalSourceFile.append("      PLCToEPICSData : Variant;   // Pointer to PLC->EPICS data exchange block (header of the array of words)")
	ExternalSourceFile.append("      EPICSToPLCData : Variant;   // Pointer to EPICS->PLC data exchange block (header of the array of words)")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR ")
	ExternalSourceFile.append("      SendConnData {OriginalPartName := 'TCON_IP_v4'; LibVersion := '1.0'} : TCON_IP_v4;   // Connection parameters")
	ExternalSourceFile.append("      RcvConnData {OriginalPartName := 'TCON_IP_v4'; LibVersion := '1.0'} : TCON_IP_v4;   // Connection parameters")
	ExternalSourceFile.append("      TSEND_C_DB {OriginalPartName := 'TSENDC'; LibVersion := '3.2'} : TSEND_C;")
	ExternalSourceFile.append("      MB_SERVER_DB {OriginalPartName := 'MBSERVER'; LibVersion := '4.2'} : MB_SERVER;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//This function block performs send/recieve communication between the PLC AND EPICS using:")
	ExternalSourceFile.append("	//1. Open user communication (s7plc driver in EPICS)")
	ExternalSourceFile.append("	//2. Modbus TCP (Modbus driver in EPICS)")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//The block is fully self-contained, i.e. you should be able TO simple insert it in your program (AND call it OF course) AND provide some inputs TO it")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Set up connections (Ethernet port ID)")
	ExternalSourceFile.append("	#SendConnData.InterfaceId := #InterfaceID;")
	ExternalSourceFile.append("	#RcvConnData.InterfaceId := #InterfaceID;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Set up connections (Connection ID) (separate connections for s7 and Modbus)")
	ExternalSourceFile.append("	#SendConnData.ID := INT_TO_WORD(IN:= #S7ConnectionID);")
	ExternalSourceFile.append("	#RcvConnData.ID := INT_TO_WORD(IN := #MBConnectionID);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Set up connections (Connection type)")
	ExternalSourceFile.append("	#SendConnData.ConnectionType := 11;")
	ExternalSourceFile.append("	#RcvConnData.ConnectionType := 11;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Set up connections (Active connection establishment)")
	ExternalSourceFile.append("	IF NOT #SendConnData.ActiveEstablished THEN")
	ExternalSourceFile.append("	    #RcvConnData.ActiveEstablished := false;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Set up connections (Local port)")
	ExternalSourceFile.append("	#SendConnData.LocalPort := INT_TO_UINT(IN:= #S7Port);")
	ExternalSourceFile.append("	#RcvConnData.LocalPort := INT_TO_UINT(IN := #MBPort);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//PLC -> EPICS communication. Data is sent using open user communication (s7plc driver in EPICS)")
	ExternalSourceFile.append("	#TSEND_C_DB(REQ:=#SendTrigger,")
	ExternalSourceFile.append("	            CONT:=TRUE,")
	ExternalSourceFile.append("	            LEN:=INT_TO_UINT(IN:=#BytesToSend),")
	ExternalSourceFile.append("	            DONE=>#SendDone,")
	ExternalSourceFile.append("	            BUSY=>#SendBusy,")
	ExternalSourceFile.append("	            ERROR=>#SendError,")
	ExternalSourceFile.append("	            STATUS=>#SendStatus,")
	ExternalSourceFile.append("	            CONNECT:=#SendConnData,")
	ExternalSourceFile.append("	            DATA:=#PLCToEPICSData);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//EPICS <- EPICS communication. Data is received using modbus server on the PLC (modbus driver in EPICS)")
	ExternalSourceFile.append("	#MB_SERVER_DB(DISCONNECT:=NOT #Enable,")
	ExternalSourceFile.append("	              NDR=>#RcvNewDataReady,")
	ExternalSourceFile.append("	              DR=>#RcvDataRead,")
	ExternalSourceFile.append("	              ERROR=>#RcvError,")
	ExternalSourceFile.append("	              STATUS=>#RcvStatus,")
	ExternalSourceFile.append("	              MB_HOLD_REG:=#EPICSToPLCData,")
	ExternalSourceFile.append("	              CONNECT:=#RcvConnData);")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_FUNCTION_BLOCK")

	ExternalSourceFile.append("DATA_BLOCK \"_CommsPLC_EPICS_DB\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("\"_CommsPLC_EPICS\"")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")

	ExternalSourceFile.append("FUNCTION \"_CommsEPICS\" : Void")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//Heartbeat PLC->EPICS")
	ExternalSourceFile.append("	IF \"Utilities\".Pulse_1s THEN")
	ExternalSourceFile.append("	    \"PLCToEPICS\".\"Word\"[2] := \"PLCToEPICS\".\"Word\"[2] + 1;")
	ExternalSourceFile.append("	    IF \"PLCToEPICS\".\"Word\"[2] >= 32000 THEN")
	ExternalSourceFile.append("	        \"PLCToEPICS\".\"Word\"[2] := 0;")
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	// Call the comms block to provide PLC<->EPICS comms")
	ExternalSourceFile.append("	\"_CommsPLC_EPICS_DB\"(Enable := \"Utilities\".AlwaysOn,")
	ExternalSourceFile.append("	                     SendTrigger := \"Utilities\".Pulse_200ms,")
	ExternalSourceFile.append("	                     BytesToSend := 10,")
	ExternalSourceFile.append("	                     InterfaceID := 64,")
	ExternalSourceFile.append("	                     S7ConnectionID := 256,")
	ExternalSourceFile.append("	                     MBConnectionID := 255,")
	ExternalSourceFile.append("	                     S7Port := 2000,")
	ExternalSourceFile.append("	                     MBPort := 502,")
	ExternalSourceFile.append("	                     PLCToEPICSData := \"PLCToEPICS\".\"Word\",")
	ExternalSourceFile.append("	                     EPICSToPLCData := \"EPICSToPLC\".\"Word\");")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	//Map all devices command and status registers to EPICS->PLC and PLC->EPICS data exchange blocks")
	ExternalSourceFile.append("	\"_CommsEPICSDataMap\"();")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_FUNCTION")

	ExternalSourceFile.append("FUNCTION \"_Comms\" : Void")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//This is an aggregator function, it will call all the other comms functions required:")
	ExternalSourceFile.append("	//1. PLC/EPICS")
	ExternalSourceFile.append("	//2. Any other comms")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("	\"_CommsEPICS\"();")
	ExternalSourceFile.append("	")
	ExternalSourceFile.append("END_FUNCTION")
	
	
def ProcessIFADevTypes(OutputDir, IfaPath, TIAVersion):

	#Process IFA devices	
	print "Processing .ifa file..."
	
	ProcessedDeviceNum = 0
	
	global OrderedLines
	global ExternalSourceFile
	global HASH 
	global ActualDeviceName 
	global ActualDeviceNameWhite 
	global ActualDeviceType 
	global EPICSTOPLCLENGTH 
	global EPICSTOPLCDATABLOCKOFFSET 
	global EPICSTOPLCPARAMETERSSTART 
	global PLCTOEPICSDATABLOCKOFFSET 
	global DeviceTypeList
	DeviceTypeList = []
	
	global DevTypeHeader 
	global DevTypeVAR_INPUT 
	global DevTypeVAR_INOUT 
	global DevTypeVAR_OUTPUT 
	global DevTypeDB_SPEC 
	global DevTypeVAR_TEMP 
	global DevTypeBODY_HEADER
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global DevTypeBODY_END

	global EPICS_PLC_TesterDB
	global DeviceInstance
	global EPICS_device_calls_body 
	global EPICS_device_calls_header 

	
	global EndString
	global EndString2
	global IsDouble
	
	global MAX_IO_DEVICES
	global MAX_LOCAL_MODULES
	global MAX_MODULES_IN_IO_DEVICE
	global Direct

	InStatus = False
	InCommand = False
	InParameter = False
	FirstDevice = True
	StartingRegister = -1
	
	
	ActVariablePLCName = ""
	ActVariableEPICSName = ""
	ActVariableType = ""
	LastVariableType = ""
	ActVariableArrayIndex = 0
	ActVariableBitNumber = 0
	EndString = ""
	EndString2 = ""
	EndDeviceString = ""
	IsDouble = False
	NewDeviceType = False
	
	global MaxStatusReg;
	global MaxCommandReg;
	MaxStatusReg = 0;
	MaxCommandReg = 0;
	
	InArray = False 
	InArrayName = "" 
	InArrayNum = 0 

	if Direct:
		print ""
		print "***Note***: PLCFactory runs in direct mode. PLC type blocks will not be generated!"
		print ""


	pos = 0
	while pos < len(OrderedLines)-1:
		if OrderedLines[pos].rstrip() == "DEVICE":
			ProcessedDeviceNum = ProcessedDeviceNum + 1
			InStatus = False
			InCommand = False
			InParameter = False
			if FirstDevice == False:
				CloseLastVariable()
				if EndDeviceString <> "":
					EPICS_device_calls_test_body.append("                                 DEVICE_PARAM_OK=>#\""+EndDeviceString+"\");")					
					EndDeviceString = ""
				if NewDeviceType == True:
					if not Direct:
						WriteDevType()

				else:	
					DevTypeHeader = []
					DevTypeVAR_INPUT = [] 
					DevTypeVAR_OUTPUT = [] 
					DevTypeDB_SPEC = [] 
					DevTypeVAR_TEMP = [] 
					DevTypeBODY_HEADER = []
					DevTypeBODY_CODE = []
					DevTypeBODY_END = []
				if Direct:
					DeviceInstance.append("   VAR")
					DeviceInstance.append("      StatusReg { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[0.."+ str(MaxStatusReg) +"] of Word;")
					DeviceInstance.append("      CommandReg { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[0.."+ str(MaxCommandReg) +"] of Word;")
					DeviceInstance.append("   END_VAR")
					DeviceInstance.append("BEGIN")
					DeviceInstance.append("END_DATA_BLOCK")

			FirstDevice = False
			if (OrderedLines[pos + 2].rstrip() <> "DEVICE_TYPE") or (OrderedLines[pos + 4].rstrip() <> "EPICSTOPLCLENGTH") or	(OrderedLines[pos + 6].rstrip() <> "EPICSTOPLCDATABLOCKOFFSET") or (OrderedLines[pos + 8].rstrip() <> "EPICSTOPLCPARAMETERSSTART") or (OrderedLines[pos + 10].rstrip() <> "PLCTOEPICSDATABLOCKOFFSET"):	
				print "ERROR:"
				print "The .ifa file has a bad DEVICE format! Exiting InterfaceFactory...\n"
				print("--- %.1f seconds ---\n" % (time.time() - start_time))
				sys.exit()		
			ActualDeviceName = OrderedLines[pos+1].rstrip()
			ActualDeviceType = OrderedLines[pos+3].rstrip()  
			EPICSTOPLCLENGTH = OrderedLines[pos+5].rstrip()
			EPICSTOPLCDATABLOCKOFFSET = OrderedLines[pos+7].rstrip()
			EPICSTOPLCPARAMETERSSTART = OrderedLines[pos+9].rstrip()
			PLCTOEPICSDATABLOCKOFFSET = OrderedLines[pos+11].rstrip()
			ActualDeviceNameWhite = ActualDeviceName
			Text = "Device: "+ ActualDeviceName + " Type: "+ ActualDeviceType
			print "    " + "-" * len(Text)
			print "    " + Text
			print "    " + "-" * len(Text)
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace(":","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("/","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("\\","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("?","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("*","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("[","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("]","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace(".","")
			
			#Device Instance
			if not Direct:
				DeviceInstance.append("")
				DeviceInstance.append("DATA_BLOCK \"DEV_" +ActualDeviceName+ "_iDB\"")
				DeviceInstance.append("{ S7_Optimized_Access := 'TRUE' }")
				DeviceInstance.append("VERSION : 1.0")
				DeviceInstance.append("NON_RETAIN")
				DeviceInstance.append("\"DEVTYPE_"+ActualDeviceType+"\"")
				DeviceInstance.append("BEGIN")
				DeviceInstance.append("END_DATA_BLOCK")
				DeviceInstance.append("")
			else:
				DeviceInstance.append("")
				DeviceInstance.append("DATA_BLOCK \"DEV_" +ActualDeviceName+ "_iDB\"")
				DeviceInstance.append("{ S7_Optimized_Access := 'TRUE' }")
				DeviceInstance.append("VERSION : 1.0")
				DeviceInstance.append("NON_RETAIN")

			EPICS_device_calls_header.append("      \""+ActualDeviceName+"\" : Bool;   // HASH codes are OK")
			EPICS_device_calls_test_header.append("      \""+ActualDeviceName+"\" : Bool;   // HASH codes are OK")
			
			EPICS_device_calls_body.append("");    
			EPICS_device_calls_body.append("        //********************************************");
			EPICS_device_calls_body.append("        // Device name: "+ActualDeviceName);
			EPICS_device_calls_body.append("        // Device type: "+ActualDeviceType);
			EPICS_device_calls_body.append("        //********************************************");
			EPICS_device_calls_body.append("");
			EPICS_device_calls_body.append("      \"DEV_"+ActualDeviceName+"_iDB\" ();")
			
			EndDeviceString = ActualDeviceName
			EPICS_device_calls_test_body.append("");    
			EPICS_device_calls_test_body.append("      //********************************************");
			EPICS_device_calls_test_body.append("      // Device name: "+ActualDeviceName);
			EPICS_device_calls_test_body.append("      // Device type: "+ActualDeviceType);
			EPICS_device_calls_test_body.append("      //********************************************");
			EPICS_device_calls_test_body.append("");
			EPICS_device_calls_test_body.append("      \"DEV_"+ActualDeviceName+"_iDB\" (")
			
			
			#Check if DeviceType is already generated
			if ActualDeviceType not in DeviceTypeList:
				if not Direct:
					MaxStatusReg = 0;
					MaxCommandReg = 0;

					NewDeviceType = True
					DeviceTypeList.append(ActualDeviceType)
					print "    ->  New device type found. ["+ ActualDeviceType+"] Creating source code..."
					DevTypeHeader.append("FUNCTION_BLOCK \"" + "DEVTYPE_" + ActualDeviceType+ "\"")
					DevTypeHeader.append("{ S7_Optimized_Access := 'TRUE' }")
					DevTypeHeader.append("VERSION : 1.0")

					DevTypeDB_SPEC.append("   Var DB_SPECIFIC")
					DevTypeDB_SPEC.append("      MyWord { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Word;")
					DevTypeDB_SPEC.append("      MyBytesinWord { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} AT MyWord : Array[0..1] of Byte;")
					DevTypeDB_SPEC.append("      MyBoolsinWord { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} AT MyWord : Array[0..15] of Bool;")
					DevTypeDB_SPEC.append("      MyDInt { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : DInt;")
					DevTypeDB_SPEC.append("      MyWordsinDint { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} AT MyDInt : Array[0..1] of Word;")
					DevTypeDB_SPEC.append("      MyReal { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Real;")
					DevTypeDB_SPEC.append("      MyWordsinReal { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} AT MyReal : Array[0..1] of Word;")
					DevTypeDB_SPEC.append("      MyInt { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Int;")
					DevTypeDB_SPEC.append("      MyWordinInt { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} AT MyInt : Word;")
					DevTypeDB_SPEC.append("      MyDWord { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : DWord;")
					DevTypeDB_SPEC.append("      MyWordsinDWord { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} AT MyDWord : Array[0..1] of Word;")
					DevTypeDB_SPEC.append("      MyTime { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Time;")
					DevTypeDB_SPEC.append("      MyWordsinTime { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} AT MyTime : Array[0..1] of Word;")
					DevTypeDB_SPEC.append("   END_VAR")

					DevTypeVAR_TEMP.append("   VAR_TEMP")
					DevTypeVAR_TEMP.append("      HashModbus : DInt;")
					DevTypeVAR_TEMP.append("      HashIFA : DInt;")
					DevTypeVAR_TEMP.append("      HashTIAMap : DInt;")
					DevTypeVAR_TEMP.append("   END_VAR")

					DevTypeBODY_HEADER.append("    //Author: Miklos Boros (miklos.boros@esss.se), Copyrigth 2017-2018 by European Spallation Source, Lund")
					DevTypeBODY_HEADER.append("    //This block was generated by InterfaceFactory, please don't change it MANUALLY!")
					DevTypeBODY_HEADER.append("    //Input File Name: " + os.path.basename(IfaPath))
					DevTypeBODY_HEADER.append("    //According to HASH: "+HASH)
					DevTypeBODY_HEADER.append("    //Device type: "+ActualDeviceType)
					DevTypeBODY_HEADER.append("    //Generated: "+timestamp)
					DevTypeBODY_HEADER.append("    //Description: This function does the variable mapping for a device. All device-variable will be linked to an interface variable defined in this block.")
					DevTypeBODY_HEADER.append("")
					DevTypeBODY_HEADER.append("    //********************************************")
					DevTypeBODY_HEADER.append("    //****************HASH check******************")
					DevTypeBODY_HEADER.append("    //********************************************")
					DevTypeBODY_HEADER.append("")
					DevTypeBODY_HEADER.append("")
					DevTypeBODY_HEADER.append("    #MyWordsinDint[0] := \"EPICSToPLC\".\"Word\"[0];")
					DevTypeBODY_HEADER.append("    #MyWordsinDint[1] := \"EPICSToPLC\".\"Word\"[1];")
					DevTypeBODY_HEADER.append("    #HashModbus := #MyDInt; //Hash from EPICS/ModbusTCP")
					DevTypeBODY_HEADER.append("")
					DevTypeBODY_HEADER.append("    #HashIFA := " + HASH + "; //Hash from Interface Factory as a constant")
					DevTypeBODY_HEADER.append("")
					DevTypeBODY_HEADER.append("    #MyWordsinDint[0] := \"PLCToEPICS\".\"Word\"[0];")
					DevTypeBODY_HEADER.append("    #MyWordsinDint[1] := \"PLCToEPICS\".\"Word\"[1];")
					DevTypeBODY_HEADER.append("    #HashTIAMap := #MyDInt; //Hash from PLCFactory TIA Map")
					DevTypeBODY_HEADER.append("")
					DevTypeBODY_HEADER.append("")
					DevTypeBODY_HEADER.append("    IF ((#HashIFA = #HashModbus) AND (#HashModbus = #HashTIAMap)) THEN //Check CRCs")
					DevTypeBODY_HEADER.append("        #DEVICE_PARAM_OK := TRUE;")

					DevTypeBODY_END.append("    Else")
					DevTypeBODY_END.append("       #DEVICE_PARAM_OK := FALSE; //Invalid Hash")
					DevTypeBODY_END.append("    END_IF;")
					DevTypeBODY_END.append("END_FUNCTION_BLOCK")

			else:
				NewDeviceType = False


		if OrderedLines[pos].rstrip() == "DEFINE_ARRAY":
			InArray = True
			InArrayName = OrderedLines[pos+1].rstrip()
			InArrayNum = 0
		if OrderedLines[pos].rstrip() == "END_ARRAY":
			InArray = False
			DevTypeVAR_INPUT.append("      \"" + InArrayName + "\" "+"{ S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[1.."+ str(InArrayNum) +"] of "+ ActVariableType+";   //EPICS Status variables defined in an array")
			InArrayName = ""
				
		if OrderedLines[pos].rstrip() == "STATUS":
			CloseLastVariable()
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("    //********************************************")
			DevTypeBODY_CODE.append("    //*************STATUS VARIABLES***************")
			DevTypeBODY_CODE.append("    //********************************************")	
			DevTypeBODY_CODE.append("")
			InStatus = True
			InCommand = False
			InParameter = False
			StartingRegister = -1
		if OrderedLines[pos].rstrip() == "COMMAND":
			CloseLastVariable()
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("    //********************************************")
			DevTypeBODY_CODE.append("    //*************COMMAND VARIABLES**************")
			DevTypeBODY_CODE.append("    //********************************************")	
			DevTypeBODY_CODE.append("")
			InStatus = False
			InCommand = True
			InParameter = False
			StartingRegister = -1
		if OrderedLines[pos].rstrip() == "PARAMETER":
			CloseLastVariable()
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("    //********************************************")
			DevTypeBODY_CODE.append("    //************PARAMETER VARIABLES*************")
			DevTypeBODY_CODE.append("    //********************************************")	
			DevTypeBODY_CODE.append("")
			InStatus = False
			InCommand = False
			InParameter = True
			StartingRegister = -1
		pos = pos + 1
		if OrderedLines[pos].rstrip().startswith("//"):
			DevTypeBODY_CODE.append("       "+OrderedLines[pos].rstrip())
		if OrderedLines[pos].rstrip() == "VARIABLE":
			if (OrderedLines[pos + 2].rstrip() <> "EPICS") or (OrderedLines[pos + 4].rstrip() <> "TYPE") or	(OrderedLines[pos + 6].rstrip() <> "ARRAY_INDEX") or (OrderedLines[pos + 8].rstrip() <> "BIT_NUMBER"):	
				print "ERROR:"
				print "The .ifa file has a bad VARIABLE format! Exiting InterfaceFactory...\n"
				print("--- %.1f seconds ---\n" % (time.time() - start_time))
				sys.exit()		
			
			ActVariablePLCName = OrderedLines[pos + 1].rstrip()
			ActVariableEPICSName = OrderedLines[pos + 3].rstrip()
			ActVariableType = OrderedLines[pos + 5].rstrip()
			ActVariableArrayIndex = int(OrderedLines[pos + 7].rstrip())
			ActVariableBitNumber = int(OrderedLines[pos + 9].rstrip())
			
			#Close the last variable if there is a new variable
			if 	LastVariableType <> ActVariableType:
				LastVariableType = ActVariableType
				CloseLastVariable()
			
			if InStatus:
				if InArray:
					DevTypeVAR_INOUT.append("      \"" + ActVariablePLCName + "\" "+"{ S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : "+ ActVariableType+";   //EPICS Status variable in an array: "+ActVariableEPICSName)
					EPICS_PLC_TesterDB.append("      \"" + ActualDeviceName+"_" + ActVariablePLCName + "\" "+"{ S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : "+ ActVariableType+";   //EPICS Status variable: "+ActVariableEPICSName)
					if (TIAVersion == "13"):
						EPICS_device_calls_test_body.append("                                 "+ActVariablePLCName+" := \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")
					if (TIAVersion == "14"):
						EPICS_device_calls_test_body.append("                                 "+"\""+ActVariablePLCName+"\""+" := \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")
				else:
					DevTypeVAR_INPUT.append("      \"" + ActVariablePLCName + "\" "+"{ S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : "+ ActVariableType+";   //EPICS Status variable: "+ActVariableEPICSName)
					EPICS_PLC_TesterDB.append("      \"" + ActualDeviceName+"_" + ActVariablePLCName + "\" "+"{ S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : "+ ActVariableType+";   //EPICS Status variable: "+ActVariableEPICSName)
					if (TIAVersion == "13"):
						EPICS_device_calls_test_body.append("                                 "+ActVariablePLCName+" := \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")
					if (TIAVersion == "14"):
						EPICS_device_calls_test_body.append("                                 "+"\""+ActVariablePLCName+"\""+" := \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")
				
				
			if InCommand:
				DevTypeVAR_OUTPUT.append("      \"" + ActVariablePLCName + "\" "+"{ S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : "+ ActVariableType+";   //EPICS Command variable: "+ActVariableEPICSName)
				EPICS_PLC_TesterDB.append("      \"" + ActualDeviceName+"_" + ActVariablePLCName + "\" "+"{ S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : "+ ActVariableType+";   //EPICS Command variable: "+ActVariableEPICSName)
				if (TIAVersion == "13"):
					EPICS_device_calls_test_body.append("                                 "+ActVariablePLCName+" => \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")
				if (TIAVersion == "14"):
					EPICS_device_calls_test_body.append("                                 "+"\""+ActVariablePLCName+"\""+" => \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")
			if InParameter:
				DevTypeVAR_OUTPUT.append("      \"" + ActVariablePLCName + "\" "+"{ S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : "+ ActVariableType+";   //EPICS Parameter variable: "+ActVariableEPICSName)
				EPICS_PLC_TesterDB.append("      \"" + ActualDeviceName+"_" + ActVariablePLCName + "\" "+"{ S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : "+ ActVariableType+";   //EPICS Parameter variable: "+ActVariableEPICSName)
				if (TIAVersion == "13"):
					EPICS_device_calls_test_body.append("                                 "+ActVariablePLCName+" => \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")
				if (TIAVersion == "14"):
					EPICS_device_calls_test_body.append("                                 "+"\""+ActVariablePLCName+"\""+" => \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")

			#SUPPORTED TYPES
			#PLC_types = {'BOOL', 'BYTE', 'WORD', 'DWORD', 'INT', 'DINT', 'REAL', 'TIME' }
			
			#====== BOOL TYPE ========	
			if ActVariableType == "BOOL":
				if InStatus:
					if InArray:
						InArrayNum = InArrayNum + 1 
						DevTypeBODY_CODE_ARRAY.append("              #\""+ ActVariablePLCName +"\" := "+InArrayName+"["+str(InArrayNum)+"];")
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyWord := W#0;")
					if ActVariableBitNumber < 8:
						DevTypeBODY_CODE.append("       #MyBoolsinWord[" + str((int(ActVariableBitNumber)+8)) + "] := #\""+ ActVariablePLCName +"\";    //EPICSName: "+ActVariableEPICSName)
						IsDouble = False
						EndString = "#StatusReg["+str(ActVariableArrayIndex) +"] := #MyWord;"
					else:	
						DevTypeBODY_CODE.append("       #MyBoolsinWord[" + str((int(ActVariableBitNumber)-8)) + "] := #\""+ ActVariablePLCName +"\";    //EPICSName: "+ActVariableEPICSName)
						IsDouble = False
						EndString = "#StatusReg["+str(ActVariableArrayIndex) +"] := #MyWord;"
				if InParameter or InCommand:
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyWord := #CommandReg["+str(ActVariableArrayIndex) +"];")
					if ActVariableBitNumber < 8:
						DevTypeBODY_CODE.append("       #\""+ ActVariablePLCName +"\" := #MyBoolsinWord[" + str((int(ActVariableBitNumber)+8)) + "];    //EPICSName: "+ActVariableEPICSName)
						IsDouble = False
						EndString = ""
					else:	
						DevTypeBODY_CODE.append("       #\""+ ActVariablePLCName +"\" := #MyBoolsinWord[" + str((int(ActVariableBitNumber)-8)) + "];    //EPICSName: "+ActVariableEPICSName)
						IsDouble = False
						EndString = ""
			#==========================		
			#====== BYTE TYPE ========	
			if ActVariableType == "BYTE":
				if InStatus:
					if InArray:
						InArrayNum = InArrayNum + 1 
						DevTypeBODY_CODE_ARRAY.append("              #\""+ ActVariablePLCName +"\" := "+InArrayName+"["+str(InArrayNum)+"];")
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyWord := W#0;")
					if ActVariableBitNumber == 0:
						DevTypeBODY_CODE.append("       #MyBytesinWord[0] := #\""+ ActVariablePLCName +"\";    //EPICSName: "+ActVariableEPICSName)
						IsDouble = False
						EndString = "#StatusReg["+str(ActVariableArrayIndex) +"] := #MyWord;"
					else:	
						DevTypeBODY_CODE.append("       #MyBytesinWord[1] := #\""+ ActVariablePLCName +"\";    //EPICSName: "+ActVariableEPICSName)
						IsDouble = False
						EndString = "#StatusReg["+str(ActVariableArrayIndex) +"] := #MyWord;"
				if InParameter or InCommand:
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyWord := #CommandReg["+str(ActVariableArrayIndex) +"];")
					if ActVariableBitNumber == 0:
						DevTypeBODY_CODE.append("       #\""+ ActVariablePLCName +"\" := #MyBytesinWord[1];    //EPICSName: "+ActVariableEPICSName)
						IsDouble = False
						EndString = ""
					else:	
						DevTypeBODY_CODE.append("       #\""+ ActVariablePLCName +"\" := #MyBytesinWord[0];    //EPICSName: "+ActVariableEPICSName)
						IsDouble = False
						EndString = ""
			#==========================		
			#====== INT TYPE ========	
			if ActVariableType == "INT":
				if InStatus:
					if InArray:
						InArrayNum = InArrayNum + 1 
						DevTypeBODY_CODE_ARRAY.append("              #\""+ ActVariablePLCName +"\" := "+InArrayName+"["+str(InArrayNum)+"];")
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyInt := #\""+ ActVariablePLCName +"\";")
					if ActVariableBitNumber == 0:
						IsDouble = False
						EndString = "#StatusReg["+str(ActVariableArrayIndex) +"] := #MyWordinInt;"
				if InParameter or InCommand:
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyWordinInt := #CommandReg["+str(ActVariableArrayIndex) +"];")
						DevTypeBODY_CODE.append("       #\""+ ActVariablePLCName +"\" := #MyInt;    //EPICSName: "+ActVariableEPICSName)
						IsDouble = False
						EndString = ""
			#==========================		
			#====== WORD TYPE ========	
			if ActVariableType == "WORD":
				if InStatus:
					if InArray:
						InArrayNum = InArrayNum + 1 
						DevTypeBODY_CODE_ARRAY.append("              #\""+ ActVariablePLCName +"\" := "+InArrayName+"["+str(InArrayNum)+"];")
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyWord := #\""+ ActVariablePLCName +"\";")
					if ActVariableBitNumber == 0:
						IsDouble = False
						EndString = "#StatusReg["+str(ActVariableArrayIndex) +"] := #MyWord;"
				if InParameter or InCommand:
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #\""+ ActVariablePLCName +"\" := #CommandReg["+str(ActVariableArrayIndex) +"];    //EPICSName: "+ActVariableEPICSName)
						IsDouble = False
						EndString = ""
			#==========================		
			#====== DINT TYPE ========	
			if ActVariableType == "DINT":
				if InStatus:
					if InArray:
						InArrayNum = InArrayNum + 1 
						DevTypeBODY_CODE_ARRAY.append("              #\""+ ActVariablePLCName +"\" := "+InArrayName+"["+str(InArrayNum)+"];")
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyDInt := #\""+ ActVariablePLCName +"\";")
					if ActVariableBitNumber == 0:
						IsDouble = True
						EndString  = "#StatusReg["+str(ActVariableArrayIndex) +"] := #MyWordsinDint[0];"
						EndString2 = "#StatusReg["+str(ActVariableArrayIndex+1) +"] := #MyWordsinDint[1];"
				if InParameter or InCommand:
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyDInt	:= 0;")
						DevTypeBODY_CODE.append("       #MyWordsinDint[0]	:= #CommandReg["+str(ActVariableArrayIndex) +"];")
						DevTypeBODY_CODE.append("       #MyWordsinDint[1]	:= #CommandReg["+str(ActVariableArrayIndex+1) +"];")
						DevTypeBODY_CODE.append("       #\""+ ActVariablePLCName +"\" := #MyDInt;    //EPICSName: "+ActVariableEPICSName)
						IsDouble = True
						EndString = ""
			#==========================		
			#====== DWORD TYPE ========	
			if ActVariableType == "DWORD":
				if InStatus:
					if InArray:
						InArrayNum = InArrayNum + 1 
						DevTypeBODY_CODE_ARRAY.append("              #\""+ ActVariablePLCName +"\" := "+InArrayName+"["+str(InArrayNum)+"];")
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyDWord := #\""+ ActVariablePLCName +"\";")
					if ActVariableBitNumber == 0:
						IsDouble = True
						EndString  = "#StatusReg["+str(ActVariableArrayIndex) +"] := #MyWordsinDWord[0];"
						EndString2 = "#StatusReg["+str(ActVariableArrayIndex+1) +"] := #MyWordsinDWord[1];"
				if InParameter or InCommand:
					print "DWORD is not supported for ModbusTCP" 
			#==========================		
			#====== REAL TYPE ========	
			if ActVariableType == "REAL":
				if InStatus:
					if InArray:
						InArrayNum = InArrayNum + 1 
						DevTypeBODY_CODE_ARRAY.append("              #\""+ ActVariablePLCName +"\" := "+InArrayName+"["+str(InArrayNum)+"];")
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyReal := #\""+ ActVariablePLCName +"\";")
					if ActVariableBitNumber == 0:
						IsDouble = True
						EndString  = "#StatusReg["+str(ActVariableArrayIndex) +"] := #MyWordsinReal[0];"
						EndString2 = "#StatusReg["+str(ActVariableArrayIndex+1) +"] := #MyWordsinReal[1];"
				if InParameter or InCommand:
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyReal	:= 0.0;")
						DevTypeBODY_CODE.append("       #MyWordsinReal[0]	:= #CommandReg["+str(ActVariableArrayIndex) +"];")
						DevTypeBODY_CODE.append("       #MyWordsinReal[1]	:= #CommandReg["+str(ActVariableArrayIndex+1) +"];")
						DevTypeBODY_CODE.append("       #\""+ ActVariablePLCName +"\" := #MyReal;    //EPICSName: "+ActVariableEPICSName)
						IsDouble = True
						EndString = ""
			#==========================		
			#====== TIME TYPE ========	
			if ActVariableType == "TIME":
				if InStatus:
					if InArray:
						InArrayNum = InArrayNum + 1 
						DevTypeBODY_CODE_ARRAY.append("              #\""+ ActVariablePLCName +"\" := "+InArrayName+"["+str(InArrayNum)+"];")
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyTime := #\""+ ActVariablePLCName +"\";")
					if ActVariableBitNumber == 0:
						IsDouble = True
						EndString  = "#StatusReg["+str(ActVariableArrayIndex) +"] := #MyWordsinTime[0];"
						EndString2 = "#StatusReg["+str(ActVariableArrayIndex+1) +"] := #MyWordsinTime[1];"
				if InParameter or InCommand:
					if StartingRegister <> ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       #MyDInt	:= 0;")
						DevTypeBODY_CODE.append("       #MyWordsinDint[0]	:= #CommandReg["+str(ActVariableArrayIndex) +"];")
						DevTypeBODY_CODE.append("       #MyWordsinDint[1]	:= #CommandReg["+str(ActVariableArrayIndex+1) +"];")
						DevTypeBODY_CODE.append("       #\""+ ActVariablePLCName +"\" := #MyDInt;    //EPICSName: "+ActVariableEPICSName)
						IsDouble = True
						EndString = ""
			#==========================		
			if InStatus:
				if ActVariableArrayIndex >= MaxStatusReg:
					if IsDouble:
						MaxStatusReg = ActVariableArrayIndex + 1
					else:
						MaxStatusReg = ActVariableArrayIndex
					
			if InParameter or InCommand:
				if ActVariableArrayIndex >= MaxCommandReg:
					if IsDouble:
						MaxCommandReg = ActVariableArrayIndex + 1
					else:
						MaxCommandReg = ActVariableArrayIndex

	CloseLastVariable()
	#Constuct the output source file 					
	if EndDeviceString <> "":
		EPICS_device_calls_test_body.append("                                 DEVICE_PARAM_OK=>#\""+EndDeviceString+"\");")					
		EndDeviceString = ""
	if NewDeviceType == True:
		if not Direct:
			WriteDevType()
	else:	
		DevTypeHeader = []
		DevTypeVAR_INPUT = [] 
		DevTypeVAR_OUTPUT = [] 
		DevTypeDB_SPEC = [] 
		DevTypeVAR_TEMP = [] 
		DevTypeBODY_HEADER = []
		DevTypeBODY_CODE = []
		DevTypeBODY_END = []
	if Direct:
		DeviceInstance.append("   VAR")
		DeviceInstance.append("      StatusReg { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[0.."+ str(MaxStatusReg) +"] of Word;")
		DeviceInstance.append("      CommandReg { S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False'} : Array[0.."+ str(MaxCommandReg) +"] of Word;")
		DeviceInstance.append("   END_VAR")
		DeviceInstance.append("BEGIN")
		DeviceInstance.append("END_DATA_BLOCK")
	else:
		WriteDeviceInstances()
		WriteEPICS_PLC_TesterDB()
		WriteEPICS_device_calls()
		WriteEPICS_device_calls_test()

	print "\nTotal ("+ str(ProcessedDeviceNum) + ") device(s) processed."
	if not Direct:
		print "Total ("+ str(len(DeviceTypeList)) + ") device type(s) generated.\n"
	else:
		print "Device types are not being generated. (Direct mode)\n"


def produce(OutputDir, IfaPath, SclPath, TIAVersion, **kwargs):
	global Direct
	Pre_ProcessIFA(IfaPath)
	if HASH <> "" and DeviceNum <> 0:
		generated_files = dict()

		#=============Call main functions=============
		global ExternalSourceFile
		ExternalSourceFile = []

		TIAVersion = str(TIAVersion)
		try:
			onlydiag = kwargs['onlydiag']
		except KeyError:
			onlydiag = False
		try:
			nodiag = kwargs['nodiag']
		except KeyError:
			nodiag = False

		try:
			Direct = kwargs['direct']
		except KeyError:
			Direct = False

		if not onlydiag:
			#WriteStandardPLCCode
			WriteStandardPLCCode(TIAVersion)

			standardPath = os.path.join(OutputDir, "InterfaceFactory_external_source_standard_TIAv{tiaversion}.scl".format(tiaversion = TIAVersion))
			with open(standardPath, 'wb') as standardScl:
				for line in ExternalSourceFile:
					standardScl.write(line + '\r\n')

			generated_files["STANDARD_SCL"] = standardPath

			ExternalSourceFile = []

			#Process devices/device types
			ProcessIFADevTypes(OutputDir, IfaPath, TIAVersion)

		if not nodiag:
			#WriteDiagnostics
			WriteDiagnostics(TIAVersion)
		else:
			print "NOTE:\nSkipping diagnostics"

		#Write the output fo file
		externalPath = os.path.join(OutputDir, "InterfaceFactory_external_source_TIAv{tiaversion}.scl".format(tiaversion = TIAVersion))
		with open(externalPath, 'wb') as externalScl:
			for line in ExternalSourceFile:
				externalScl.write(line + '\r\n')

			if not onlydiag:
				#Copy the .SCL from the ZIP file to the end of the code
				with open(SclPath, 'r') as tiamap:
					for line in tiamap:
						externalScl.write(line)
			else:
				print "NOTE:\nOnly diagnostics code is generated"

		generated_files["EXTERNAL_SCL"] = externalPath

		return generated_files

	else:
		if HASH <> "":
			print "ERROR:"
			print "After pre-processing the .IFA file there was no HASH code inside!\n"
			return
		if DeviceNum <> 0:
			print "ERROR:"
			print "After pre-processing the .IFA file there were no DEVICES inside!\n"
			return


def main(argv):
	os.system('clear')

	print "  _____       _             __                 ______         _                   "
	print " |_   _|     | |           / _|               |  ____|       | |                  "
	print "   | |  _ __ | |_ ___ _ __| |_ __ _  ___ ___  | |__ __ _  ___| |_ ___  _ __ _   _ "
	print "   | | | '_ \| __/ _ \ '__|  _/ _` |/ __/ _ \ |  __/ _` |/ __| __/ _ \| '__| | | |"
	print "  _| |_| | | | ||  __/ |  | || (_| | (_|  __/ | | | (_| | (__| || (_) | |  | |_| |"
	print " |_____|_| |_|\__\___|_|  |_| \__,_|\___\___| |_|  \__,_|\___|\__\___/|_|   \__, |"
	print "                                                                             __/ |"
	print " Copyright 2017-2018, European Spallation Source, Lund                      |___/ \n"

	parser         = InterfaceFactoryArgumentParser()


	parser.add_argument(
						'-z',
						'--zip',
						dest     = "inputzipfile",
						help     = 'Data input: .zip file from PLC factory',
						required = True
						)

	parser.add_argument(
						'-TIA',
						'--TIA',
						dest     = "TIAVersion",
						help     = 'TIA Portal version V13 or V14',
						required = True
						)

	parser.add_argument(
						'-nodiag',
						'--nodiag',
						dest    = "nodiag",
						help    = "create the PLC code without the diagnostic blocks",
						action  = "store_true"
						)

	parser.add_argument(
						'-onlydiag',
						'--onlydiag',
						dest    = "onlydiag",
						help    = "create the PLC code only with diagnostic blocks",
						action  = "store_true"
						)
						

	# Retrieve parameters
	args       = parser.parse_args(argv)

	inputzipfile = args.inputzipfile
	nodiag       = args.nodiag
	onlydiag     = args.onlydiag
	TIAVersion   = args.TIAVersion
	

	start_time     = time.time()

	if (nodiag) and (onlydiag):
		print "ERROR:"
		print "You have selected NoDiagnostics and OnlyDiagnostics in the same time!"
		print "Remove unconsistant parameter!\n\n"
		print("--- %.1f seconds ---\n" % (time.time() - start_time))
		sys.exit()		
	
	
	#Check TIA Portal version
	if (TIAVersion <> "13") and (TIAVersion <> "14"):
	
		print "ERROR:"
		print "InterfaceFactory supports only TIA Portal v13 or v14"
		print "The selected version was: TIA v"+TIAVersion+"\n\n" 
		print("--- %.1f seconds ---\n" % (time.time() - start_time))
		sys.exit()		
	print "The selected version was: TIA v"+TIAVersion+"\n\n"
	
	# Make output directory
	OutputDir, file_extension = os.path.splitext(inputzipfile)
	OutputDir = OutputDir + "_TIAv"+TIAVersion
	makedirs(OutputDir)

	#Unzip content
	with zipfile.ZipFile(inputzipfile, "r") as z:
		z.extractall(OutputDir)

	#Find IFA file
	IfaPath = ""
	SclPath = ""
	for file in os.listdir(OutputDir):
		if file.endswith(".ifa"):
			IfaPath = os.path.join(OutputDir, file)
	if IfaPath <> "":
		for file in os.listdir(OutputDir):
			if file.endswith(".scl") and ("TIA-MAP-NG" in file):
				SclPath = os.path.join(OutputDir, file)
		if SclPath <> "":
			print "ZIP content OK..."
			produce(OutputDir, IfaPath, SclPath, TIAVersion, nodiag = nodiag, onlydiag = onlydiag)
		else:
			print "ERROR:"
			print "The input zip file content is unknown! .scl file can't be located inside the archive! Exiting InterfaceFactory...\n"
			print("--- %.1f seconds ---\n" % (time.time() - start_time))
			sys.exit()		
	else:
		print "ERROR:"
		print "The input zip file content is unknown! .ifa file can't be located inside the archive! Exiting InterfaceFactory...\n"
		print("--- %.1f seconds ---\n" % (time.time() - start_time))
		sys.exit()		

	print "\n"	
	print "InterfaceFactory run complete."     
	print("--- %.1f seconds ---\n" % (time.time() - start_time))


if __name__ == "__main__":
	try:
		main(sys.argv[1:])
	except InterfaceFactoryArgumentError, e:
		exit(e.status)
