from __future__ import print_function
from __future__ import absolute_import

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
import datetime
import os
import errno
import sys
import time
import shutil

# PLC Factory modules
import helpers

#Global variables
timestamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())

OrderedLines = []

FC_EPICS_DEVICE_CALLS_HEADER = []
FC_EPICS_DEVICE_CALLS_BODY = []
FC_EPICS_DEVICE_CALLS_FOOTER = []

DevTypeHeader = []
DevTypeVAR_INPUT = []
DevTypeVAR_OUTPUT = []
DevTypeVAR_TEMP = []
DevTypeBODY_HEADER = []
DevTypeBODY_CODE = []
DevTypeBODY_FOOTER = []

EPICS_GVL = []
EPICS_GVL_DEVICES = []
FB_EPICS_S7_Comm = []
FB_Pulse = []
ST_2_UINT = []
U_DINT_UINT = []
U_REAL_UINT = []
U_TIME_UINT = []
EPICS_PLC_TesterDB = []


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


DeviceInstance = []

EndString = ""
EndString2 = ""
IsDouble = False

MaxStatusReg = 0
MaxCommandReg = 0

TotalStatusReg = 0
TotalCommandReg = 0


Direct = False
OutputDirectory = ""

GlobalIDCounter = 0


def Pre_ProcessIFA(IfaPath):
	print("""

*******************************************
*                                         *
*   Generating Beckhoff PLC source code   *
*                                         *
*******************************************

PLCFactory file location: {}
Pre-processing .ifa file...""".format(IfaPath))
	#Pre process IFA to have Status, Command, Parameter order

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
			if pos+1 != len(lines):
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


	print("Total", str(DeviceNum), "device(s) pre-processed.\n")

def WriteEPICS_PLC_TesterDB():

	global EPICS_PLC_TesterDB
	global ExternalSourceFile


	for line in EPICS_PLC_TesterDB:
		ExternalSourceFile.append(line)


	EPICS_PLC_TesterDB = []

def Write_EPICS_device_calls():

	global OutputDirectory
	global FC_EPICS_DEVICE_CALLS_HEADER
	global FC_EPICS_DEVICE_CALLS_BODY
	global FC_EPICS_DEVICE_CALLS_FOOTER

	externalPath = os.path.join(OutputDirectory,"BECKHOFF","EPICS","EPICS calls", "FC_EPICS_DEVICE_CALLS.TcPOU")
	with open(externalPath, 'wb') as externalScl:
		for line in FC_EPICS_DEVICE_CALLS_HEADER:
			externalScl.write(line + '\r\n')

		for line in FC_EPICS_DEVICE_CALLS_BODY:
			externalScl.write(line + '\r\n')


		for line in FC_EPICS_DEVICE_CALLS_FOOTER:
			externalScl.write(line + '\r\n')

	FC_EPICS_DEVICE_CALLS_HEADER = []
	FC_EPICS_DEVICE_CALLS_BODY = []
	FC_EPICS_DEVICE_CALLS_FOOTER = []

def Write_EPICS_GVL():
	global EPICS_GVL
	global EPICS_GVL_DEVICES
	global TotalStatusReg
	global TotalCommandReg

	EPICS_GVL.append("	aDataS7				: ARRAY [0.."+str(TotalStatusReg-1)+"] OF UINT; 			//Array of data sent to EPICS");
	EPICS_GVL.append("	aDataModbus			AT %MW0 :ARRAY [0.."+str(TotalCommandReg-1)+"] OF UINT;		//Array of data from EPICS. Corresponds to Modbus address 12289 1-based addressing. (122988 0-based)");
	EPICS_GVL.append("	FB_EPICS_S7_Comm 	: FB_EPICS_S7_Comm;					//EPICS TCP/IP communication function block");
	EPICS_GVL.append("	EasyTester			: DINT;								//Test variable for EasyTester");
	EPICS_GVL.append("END_VAR");
	EPICS_GVL.append("]]>");
	EPICS_GVL.append("</Declaration>");
	EPICS_GVL.append("</GVL>");
	EPICS_GVL.append("</TcPlcObject>");
	EPICS_GVL.append("");

	externalPath = os.path.join(OutputDirectory,"BECKHOFF","EPICS","ESS standard PLC code", "EPICS_GVL.TcGVL")
	with open(externalPath, 'wb') as externalScl:
		for line in EPICS_GVL:
			externalScl.write(line + '\r\n')

	EPICS_GVL = []

def Write_Structs_and_Unions():

	global OutputDirectory
	global ST_2_UINT
	global U_DINT_UINT
	global U_REAL_UINT
	global U_TIME_UINT
	global GlobalIDCounter

	ST_2_UINT.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
	ST_2_UINT.append("<TcPlcObject ");
	ST_2_UINT.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">");
	ST_2_UINT.append("<DUT ");
	GlobalIDCounter = GlobalIDCounter + 1
	ST_2_UINT.append("Name=\"ST_2_UINT\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\">");
	ST_2_UINT.append("<Declaration>");
	ST_2_UINT.append("<![CDATA[");
	ST_2_UINT.append("TYPE ST_2_UINT :");
	ST_2_UINT.append("STRUCT");
	ST_2_UINT.append("	nLow	:UINT;");
	ST_2_UINT.append("	nHigh	:UINT;");
	ST_2_UINT.append("END_STRUCT");
	ST_2_UINT.append("END_TYPE");
	ST_2_UINT.append("]]>");
	ST_2_UINT.append("</Declaration>");
	ST_2_UINT.append("</DUT>");
	ST_2_UINT.append("</TcPlcObject>	");

	externalPath = os.path.join(OutputDirectory,"BECKHOFF","EPICS","ESS standard PLC code", "ST_2_UINT.TcDUT")
	with open(externalPath, 'wb') as externalScl:
		for line in ST_2_UINT:
			externalScl.write(line + '\r\n')

	U_DINT_UINT.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
	U_DINT_UINT.append("<TcPlcObject ");
	U_DINT_UINT.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">");
	U_DINT_UINT.append("<DUT ");
	GlobalIDCounter = GlobalIDCounter + 1
	U_DINT_UINT.append("Name=\"U_DINT_UINTs\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\">");
	U_DINT_UINT.append("<Declaration>");
	U_DINT_UINT.append("<![CDATA[");
	U_DINT_UINT.append("TYPE U_DINT_UINTs :");
	U_DINT_UINT.append("UNION");
	U_DINT_UINT.append("	stLowHigh	:ST_2_UINT;");
	U_DINT_UINT.append("	nValue		:DINT;");
	U_DINT_UINT.append("END_UNION");
	U_DINT_UINT.append("END_TYPE");
	U_DINT_UINT.append("]]>");
	U_DINT_UINT.append("</Declaration>");
	U_DINT_UINT.append("</DUT>");
	U_DINT_UINT.append("</TcPlcObject>		");

	externalPath = os.path.join(OutputDirectory,"BECKHOFF","EPICS","ESS standard PLC code", "U_DINT_UINTs.TcDUT")
	with open(externalPath, 'wb') as externalScl:
		for line in U_DINT_UINT:
			externalScl.write(line + '\r\n')

	U_REAL_UINT.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
	U_REAL_UINT.append("<TcPlcObject ");
	U_REAL_UINT.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">");
	U_REAL_UINT.append("<DUT ");
	GlobalIDCounter = GlobalIDCounter + 1
	U_REAL_UINT.append("Name=\"U_REAL_UINTs\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\">");
	U_REAL_UINT.append("<Declaration>");
	U_REAL_UINT.append("<![CDATA[");
	U_REAL_UINT.append("TYPE U_REAL_UINTs :");
	U_REAL_UINT.append("UNION");
	U_REAL_UINT.append("	stLowHigh	:ST_2_UINT;");
	U_REAL_UINT.append("	fValue		:REAL;");
	U_REAL_UINT.append("END_UNION");
	U_REAL_UINT.append("END_TYPE");
	U_REAL_UINT.append("]]>");
	U_REAL_UINT.append("</Declaration>");
	U_REAL_UINT.append("</DUT>");
	U_REAL_UINT.append("</TcPlcObject>");
	U_REAL_UINT.append("");

	externalPath = os.path.join(OutputDirectory,"BECKHOFF","EPICS","ESS standard PLC code", "U_REAL_UINTs.TcDUT")
	with open(externalPath, 'wb') as externalScl:
		for line in U_REAL_UINT:
			externalScl.write(line + '\r\n')

	U_TIME_UINT.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
	U_TIME_UINT.append("<TcPlcObject Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">");
	U_TIME_UINT.append("<DUT ");
	GlobalIDCounter = GlobalIDCounter + 1
	U_TIME_UINT.append("Name=\"U_TIME_UINTs\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\">");
	U_TIME_UINT.append("<Declaration>");
	U_TIME_UINT.append("<![CDATA[");
	U_TIME_UINT.append("TYPE U_TIME_UINTs :");
	U_TIME_UINT.append("UNION");
	U_TIME_UINT.append("	stLowHigh	:ST_2_UINT;");
	U_TIME_UINT.append("	tValue		:TIME;");
	U_TIME_UINT.append("END_UNION");
	U_TIME_UINT.append("END_TYPE");
	U_TIME_UINT.append("]]>");
	U_TIME_UINT.append("</Declaration>");
	U_TIME_UINT.append("</DUT>");
	U_TIME_UINT.append("</TcPlcObject>");


	externalPath = os.path.join(OutputDirectory,"BECKHOFF","EPICS","ESS standard PLC code", "U_TIME_UINTs.TcDUT")
	with open(externalPath, 'wb') as externalScl:
		for line in U_TIME_UINT:
			externalScl.write(line + '\r\n')

	ST_2_UINT = []
	U_DINT_UINT = []
	U_REAL_UINT = []
	U_TIME_UINT = []

def Write_FB_EPICS_S7_Comm():

	global FB_EPICS_S7_Comm
	global GlobalIDCounter

	FB_EPICS_S7_Comm.append

	FB_EPICS_S7_Comm.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
	FB_EPICS_S7_Comm.append("<TcPlcObject ");
	FB_EPICS_S7_Comm.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">");
	FB_EPICS_S7_Comm.append("<POU ");
	GlobalIDCounter = GlobalIDCounter + 1
	FB_EPICS_S7_Comm.append("Name=\"FB_EPICS_S7_Comm\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\" SpecialFunc=\"None\">");
	FB_EPICS_S7_Comm.append("<Declaration>");
	FB_EPICS_S7_Comm.append("<![CDATA[");
	FB_EPICS_S7_Comm.append("FUNCTION_BLOCK FB_EPICS_S7_Comm");
	FB_EPICS_S7_Comm.append("VAR_INPUT");
	FB_EPICS_S7_Comm.append("	bConnect	:BOOL;					//Open or closes TCP/IP connection");
	FB_EPICS_S7_Comm.append("	nS7Port		:UDINT :=2000;			//Server port. Leave empty for default 2000");
	FB_EPICS_S7_Comm.append("	nPLC_Hash	:DINT;					//Hash written during XML generation at PLC factory");
	FB_EPICS_S7_Comm.append("	tSendTrig	:TIME:= T#200MS;			//Frequency of pushed data");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("END_VAR");
	FB_EPICS_S7_Comm.append("VAR_OUTPUT");
	FB_EPICS_S7_Comm.append("	nCase		:INT:=0;				//Status. 0=Init, 1=Close conn., 2=Listen, 3=Accept, 4=Send data");
	FB_EPICS_S7_Comm.append("	bConnected	:BOOL;					//TCP/IP connection accepted");
	FB_EPICS_S7_Comm.append("	bError		:BOOL;					//Error in connection");
	FB_EPICS_S7_Comm.append("END_VAR");
	FB_EPICS_S7_Comm.append("VAR");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("	sSrvNetID		:T_AmsNetId :='';		// Local ID if empty");
	FB_EPICS_S7_Comm.append("	sLocalHost		:STRING(15) :='';	");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("	FB_SocketCloseAll:FB_SocketCloseAll;");
	FB_EPICS_S7_Comm.append("	bClose			:BOOL;");
	FB_EPICS_S7_Comm.append("	bCloseBusy		:BOOL;");
	FB_EPICS_S7_Comm.append("	bCloseError		:BOOL;");
	FB_EPICS_S7_Comm.append("	nCloseErrID		:UDINT;");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("	FB_SocketListen	:FB_SocketListen;");
	FB_EPICS_S7_Comm.append("	bListen			:BOOL;");
	FB_EPICS_S7_Comm.append("	bListenBusy		:BOOL;");
	FB_EPICS_S7_Comm.append("	bListenError	:BOOL;");
	FB_EPICS_S7_Comm.append("	nListenErrID	:UDINT;");
	FB_EPICS_S7_Comm.append("	hListener		:T_HSOCKET;");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("	FB_SocketAccept	:FB_SocketAccept;");
	FB_EPICS_S7_Comm.append("	bAccept			:BOOL;");
	FB_EPICS_S7_Comm.append("	bAccepted		:BOOL;");
	FB_EPICS_S7_Comm.append("	bAcceptBusy		:BOOL;");
	FB_EPICS_S7_Comm.append("	bAcceptError	:BOOL;");
	FB_EPICS_S7_Comm.append("	nAcceptErrID	:UDINT;");
	FB_EPICS_S7_Comm.append("	hSocket			:T_HSOCKET;");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("	FB_SocketSend	:FB_SocketSend;");
	FB_EPICS_S7_Comm.append("	bSend			:BOOL;");
	FB_EPICS_S7_Comm.append("	bSendBusy		:BOOL;");
	FB_EPICS_S7_Comm.append("	bSendError		:BOOL;");
	FB_EPICS_S7_Comm.append("	nSendErrID		:UDINT;");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("	F_bConnect		:F_TRIG;");
	FB_EPICS_S7_Comm.append("	T_Init			:TON;");
	FB_EPICS_S7_Comm.append("	tInit			:TIME:= T#1S;");
	FB_EPICS_S7_Comm.append("	T_Push			:TON;");
	FB_EPICS_S7_Comm.append("	nNumberOfErr	:INT:=0;");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("	//blink & counter functions");
	FB_EPICS_S7_Comm.append("	bBlink			:BOOL;			//enable blink function");
	FB_EPICS_S7_Comm.append("	fb_Pulse		:FB_Pulse;		//Pulse/counter function block");
	FB_EPICS_S7_Comm.append("	nCount			:UINT;");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("	i				:INT:=3;		//index for filling data array loop");
	FB_EPICS_S7_Comm.append("	nPLC_HashH		:UINT;			//Least significant part of the hash");
	FB_EPICS_S7_Comm.append("	nPLC_HashL		:UINT;			//Most significant part of the hash");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("END_VAR");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("]]>");
	FB_EPICS_S7_Comm.append("</Declaration>");
	FB_EPICS_S7_Comm.append("<Implementation>");
	FB_EPICS_S7_Comm.append("<ST>");
	FB_EPICS_S7_Comm.append("<![CDATA[");
	FB_EPICS_S7_Comm.append("(*");
	FB_EPICS_S7_Comm.append("**********************EPICS<-->Beckhoff integration at ESS in Lund, Sweden*******************************");
	FB_EPICS_S7_Comm.append("TCP/IP server on Bechoff for EPICS<--Beckhoff communication flow.");
	FB_EPICS_S7_Comm.append("Modbus Server on Beckhoff for EPICS-->Beckhoff communication flow.");
	FB_EPICS_S7_Comm.append("Created by: Andres Quintanilla (andres.quintanilla@esss.se)");
	FB_EPICS_S7_Comm.append("            Miklos Boros (miklos.boros@esss.se)");
	FB_EPICS_S7_Comm.append("Date: 06/04/2018");
	FB_EPICS_S7_Comm.append("Notes: TCP/IP server pushes data to the EPICS IOC connected. Modbus connection is open for R/W.");
	FB_EPICS_S7_Comm.append("Code must not be changed manually. Code is generated and handled by PLC factory at ESS.");
	FB_EPICS_S7_Comm.append("Functionality: ");
	FB_EPICS_S7_Comm.append("Step 0: Wait for initialization command. Is set true as default.");
	FB_EPICS_S7_Comm.append("Step 1: Close all open connections");
	FB_EPICS_S7_Comm.append("Step 2: Initialize TCP/Ip server Listener");
	FB_EPICS_S7_Comm.append("Step 3: Accept any incoming connection request. Matching connection is validated via the input nPLC Hash at EPICS level.");
	FB_EPICS_S7_Comm.append("Step 4: Sends data to epics constantly using input tSendTrig as frequency");
	FB_EPICS_S7_Comm.append("**********************************************************************************************************");
	FB_EPICS_S7_Comm.append("*)");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("CASE nCase OF ");
	FB_EPICS_S7_Comm.append("	0:// Wait for initialization command");
	FB_EPICS_S7_Comm.append("	IF bConnect THEN");
	FB_EPICS_S7_Comm.append("		bClose := FALSE;");
	FB_EPICS_S7_Comm.append("		nCase := nCase + 1;");
	FB_EPICS_S7_Comm.append("	END_IF");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("	1://Close all current connections");
	FB_EPICS_S7_Comm.append("	T_Init.IN	:= TRUE;");
	FB_EPICS_S7_Comm.append("	bClose 		:= TRUE;");
	FB_EPICS_S7_Comm.append("	bListen 	:= FALSE;");
	FB_EPICS_S7_Comm.append("	bAccept		:= FALSE;");
	FB_EPICS_S7_Comm.append("	bSend 		:= FALSE;");
	FB_EPICS_S7_Comm.append("	T_Push.IN	:= FALSE;");
	FB_EPICS_S7_Comm.append("	IF NOT bConnect AND T_Init.Q THEN");
	FB_EPICS_S7_Comm.append("		bClose := FALSE;");
	FB_EPICS_S7_Comm.append("		T_Init.IN:= FALSE;");
	FB_EPICS_S7_Comm.append("		nCase := nCase - 1;	");
	FB_EPICS_S7_Comm.append("	END_IF");
	FB_EPICS_S7_Comm.append("	IF bConnect AND NOT bCloseBusy AND T_Init.Q THEN");
	FB_EPICS_S7_Comm.append("		bClose := FALSE;");
	FB_EPICS_S7_Comm.append("		T_Init.IN:= FALSE;");
	FB_EPICS_S7_Comm.append("		nCase := nCase + 1;");
	FB_EPICS_S7_Comm.append("	END_IF");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("	2://Initialize Listener for new incoming connections ");
	FB_EPICS_S7_Comm.append("	T_Init.IN:=TRUE;");
	FB_EPICS_S7_Comm.append("	bListen	:= TRUE;");
	FB_EPICS_S7_Comm.append("	IF hListener.handle = 0 AND T_Init.Q THEN ");
	FB_EPICS_S7_Comm.append("		bListen	:= FALSE;");
	FB_EPICS_S7_Comm.append("		T_Init.IN:=FALSE;");
	FB_EPICS_S7_Comm.append("	END_IF");
	FB_EPICS_S7_Comm.append("	IF bListenError AND T_Init.Q THEN");
	FB_EPICS_S7_Comm.append("		bListen	:= FALSE;");
	FB_EPICS_S7_Comm.append("		T_Init.IN:=FALSE;");
	FB_EPICS_S7_Comm.append("		nCase := nCase - 1;");
	FB_EPICS_S7_Comm.append("	END_IF");
	FB_EPICS_S7_Comm.append("	IF hListener.handle <> 0 AND T_Init.Q THEN");
	FB_EPICS_S7_Comm.append("		bListen	:= FALSE;");
	FB_EPICS_S7_Comm.append("		T_Init.IN:=FALSE;");
	FB_EPICS_S7_Comm.append("		nCase := nCase + 1;");
	FB_EPICS_S7_Comm.append("	END_IF");
	FB_EPICS_S7_Comm.append("			");
	FB_EPICS_S7_Comm.append("	3://Accept connections");
	FB_EPICS_S7_Comm.append("	T_Init.IN	:= TRUE;");
	FB_EPICS_S7_Comm.append("	bAccept		:= TRUE;");
	FB_EPICS_S7_Comm.append("	IF NOT bAccepted AND T_Init.Q THEN");
	FB_EPICS_S7_Comm.append("		T_Init.IN	:= FALSE;");
	FB_EPICS_S7_Comm.append("		bAccept		:= FALSE;");
	FB_EPICS_S7_Comm.append("		nNumberOfErr	:= nNumberOfErr + 1;");
	FB_EPICS_S7_Comm.append("	END_IF");
	FB_EPICS_S7_Comm.append("	IF bAccepted AND T_Init.Q THEN");
	FB_EPICS_S7_Comm.append("		T_Init.IN	:= FALSE;");
	FB_EPICS_S7_Comm.append("		bAccept		:= FALSE;");
	FB_EPICS_S7_Comm.append("		nCase := nCase + 1;");
	FB_EPICS_S7_Comm.append("		nNumberOfErr	:=0;");
	FB_EPICS_S7_Comm.append("	END_IF");
	FB_EPICS_S7_Comm.append("	IF nNumberOfErr = 10 THEN");
	FB_EPICS_S7_Comm.append("		T_Push.IN	:= FALSE;");
	FB_EPICS_S7_Comm.append("		bSend 		:= FALSE;");
	FB_EPICS_S7_Comm.append("		nNumberOfErr	:=0;");
	FB_EPICS_S7_Comm.append("		nCase := 0;");
	FB_EPICS_S7_Comm.append("	END_IF");
	FB_EPICS_S7_Comm.append("		");
	FB_EPICS_S7_Comm.append("	4: //Push data to EPICS	");
	FB_EPICS_S7_Comm.append("	T_Push.IN	:= TRUE;");
	FB_EPICS_S7_Comm.append("	bSend 		:= TRUE;");
	FB_EPICS_S7_Comm.append("	IF T_Push.Q THEN");
	FB_EPICS_S7_Comm.append("		T_Push.IN	:= FALSE;");
	FB_EPICS_S7_Comm.append("		bSend 		:= FALSE;");
	FB_EPICS_S7_Comm.append("		IF bSendError THEN");
	FB_EPICS_S7_Comm.append("			nNumberOfErr	:= nNumberOfErr + 1;	");
	FB_EPICS_S7_Comm.append("		END_IF");
	FB_EPICS_S7_Comm.append("	END_IF");
	FB_EPICS_S7_Comm.append("	IF nNumberOfErr = 3 THEN");
	FB_EPICS_S7_Comm.append("		T_Push.IN	:= FALSE;");
	FB_EPICS_S7_Comm.append("		bSend 		:= FALSE;");
	FB_EPICS_S7_Comm.append("		nNumberOfErr	:=0;");
	FB_EPICS_S7_Comm.append("		nCase := 1;");
	FB_EPICS_S7_Comm.append("	END_IF");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("		");
	FB_EPICS_S7_Comm.append("END_CASE");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("//Prepares array to be sent");
	FB_EPICS_S7_Comm.append("nPLC_HashL := DINT_TO_UINT(SHR(nPLC_Hash,16));");
	FB_EPICS_S7_Comm.append("nPLC_HashH := DINT_TO_UINT(nPLC_Hash);");
	FB_EPICS_S7_Comm.append("EPICS_GVL.aDataS7[1]:=nPLC_HashL;");
	FB_EPICS_S7_Comm.append("EPICS_GVL.aDataS7[0]:=nPLC_HashH;");
	FB_EPICS_S7_Comm.append("EPICS_GVL.aDataS7[2]:=nCount;");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("//TCP IP communication function blocks");
	FB_EPICS_S7_Comm.append("FB_SocketCloseAll(");
	FB_EPICS_S7_Comm.append("	sSrvNetId:=sSrvNetID , ");
	FB_EPICS_S7_Comm.append("	bExecute:=bClose , ");
	FB_EPICS_S7_Comm.append("	tTimeout:=T#2S , ");
	FB_EPICS_S7_Comm.append("	bBusy=>bCloseBusy , ");
	FB_EPICS_S7_Comm.append("	bError=>bCloseError , ");
	FB_EPICS_S7_Comm.append("	nErrId=>nCloseErrID );");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("FB_SocketListen(");
	FB_EPICS_S7_Comm.append("	sSrvNetId:=sSrvNetID , ");
	FB_EPICS_S7_Comm.append("	sLocalHost:=sLocalHost , ");
	FB_EPICS_S7_Comm.append("	nLocalPort:=nS7Port , ");
	FB_EPICS_S7_Comm.append("	bExecute:=bListen , ");
	FB_EPICS_S7_Comm.append("	tTimeout:=T#2S , ");
	FB_EPICS_S7_Comm.append("	bBusy=>bListenBusy , ");
	FB_EPICS_S7_Comm.append("	bError=>bListenError , ");
	FB_EPICS_S7_Comm.append("	nErrId=>nListenErrID , ");
	FB_EPICS_S7_Comm.append("	hListener=>hListener );");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("FB_SocketAccept(");
	FB_EPICS_S7_Comm.append("	sSrvNetId:=sSrvNetID , ");
	FB_EPICS_S7_Comm.append("	hListener:=hListener , ");
	FB_EPICS_S7_Comm.append("	bExecute:=bAccept , ");
	FB_EPICS_S7_Comm.append("	tTimeout:=T#2S , ");
	FB_EPICS_S7_Comm.append("	bAccepted=>bAccepted , ");
	FB_EPICS_S7_Comm.append("	bBusy=>bAcceptBusy , ");
	FB_EPICS_S7_Comm.append("	bError=>bAcceptError , ");
	FB_EPICS_S7_Comm.append("	nErrId=>nAcceptErrID , ");
	FB_EPICS_S7_Comm.append("	hSocket=>hSocket );");
	FB_EPICS_S7_Comm.append("	");
	FB_EPICS_S7_Comm.append("FB_SocketSend(");
	FB_EPICS_S7_Comm.append("	sSrvNetId:=sSrvNetID , ");
	FB_EPICS_S7_Comm.append("	hSocket:=hSocket , ");
	FB_EPICS_S7_Comm.append("	cbLen:=SIZEOF(EPICS_GVL.aDataS7) , ");
	FB_EPICS_S7_Comm.append("	pSrc:=ADR(EPICS_GVL.aDataS7) , ");
	FB_EPICS_S7_Comm.append("	bExecute:=bSend , ");
	FB_EPICS_S7_Comm.append("	tTimeout:=T#5S , ");
	FB_EPICS_S7_Comm.append("	bBusy=>bSendBusy , ");
	FB_EPICS_S7_Comm.append("	bError=>bSendError , ");
	FB_EPICS_S7_Comm.append("	nErrId=>nSendErrID );");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("//Counter function");
	FB_EPICS_S7_Comm.append("IF nCase = 4 THEN ");
	FB_EPICS_S7_Comm.append("	bBlink	:= TRUE;");
	FB_EPICS_S7_Comm.append("	ELSE");
	FB_EPICS_S7_Comm.append("	bBlink	:= FALSE;	");
	FB_EPICS_S7_Comm.append("END_IF");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("fb_Pulse(bEn:=bBlink , tTimePulse:=T#1S , bPulse=> , nCount=>nCount );");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("//Triggers");
	FB_EPICS_S7_Comm.append("F_bConnect(CLK:=bConnect, Q=>);");
	FB_EPICS_S7_Comm.append("IF F_bConnect.Q  THEN //Close all connections");
	FB_EPICS_S7_Comm.append("	nCase:=1;");
	FB_EPICS_S7_Comm.append("	T_Init.IN:= FALSE;");
	FB_EPICS_S7_Comm.append("	nNumberOfErr:=0;");
	FB_EPICS_S7_Comm.append("END_IF");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("//Timers");
	FB_EPICS_S7_Comm.append("T_Init(IN:=, PT:=tInit);");
	FB_EPICS_S7_Comm.append("T_Push(IN:=, PT:=tSendTrig);");
	FB_EPICS_S7_Comm.append("");
	FB_EPICS_S7_Comm.append("//Outputs");
	FB_EPICS_S7_Comm.append("bConnected	:= bAccepted AND bConnect AND nCase>=3;");
	FB_EPICS_S7_Comm.append("bError		:= bConnect AND (bCloseError OR bListenError OR bAcceptError OR bSendError);");
	FB_EPICS_S7_Comm.append("]]>");
	FB_EPICS_S7_Comm.append("</ST>");
	FB_EPICS_S7_Comm.append("</Implementation>");
	FB_EPICS_S7_Comm.append("</POU>");
	FB_EPICS_S7_Comm.append("</TcPlcObject>");

	externalPath = os.path.join(OutputDirectory,"BECKHOFF","EPICS","ESS standard PLC code", "FB_EPICS_S7_Comm.TcPOU")
	with open(externalPath, 'wb') as externalScl:
		for line in FB_EPICS_S7_Comm:
			externalScl.write(line + '\r\n')

	FB_EPICS_S7_Comm = []

def Write_FB_Pulse():
	global FB_Pulse
	global GlobalIDCounter


	FB_Pulse.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
	FB_Pulse.append("<TcPlcObject ");
	FB_Pulse.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">");
	FB_Pulse.append("<POU ");
	GlobalIDCounter = GlobalIDCounter + 1
	FB_Pulse.append("Name=\"FB_Pulse\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\" SpecialFunc=\"None\">");
	FB_Pulse.append("<Declaration>");
	FB_Pulse.append("<![CDATA[");
	FB_Pulse.append("FUNCTION_BLOCK FB_Pulse			//Pulse and counter function block");
	FB_Pulse.append("VAR_INPUT");
	FB_Pulse.append("	bEn			:BOOL;");
	FB_Pulse.append("	tTimePulse	:TIME:=t#1s;");
	FB_Pulse.append("END_VAR");
	FB_Pulse.append("VAR_OUTPUT");
	FB_Pulse.append("	bPulse		:BOOL;			//Frequency of Pulse, 50/50 pulse width");
	FB_Pulse.append("	nCount		:UINT;			//Count of pulses generated. Resets at 65535");
	FB_Pulse.append("END_VAR");
	FB_Pulse.append("VAR");
	FB_Pulse.append("	T_BlinkON	:TON;			//Timer function");
	FB_Pulse.append("	T_BlinkOFF	:TOF;			//Timer function");
	FB_Pulse.append("	cCounter	:CTU;			//Counter up function");
	FB_Pulse.append("	");
	FB_Pulse.append("END_VAR");
	FB_Pulse.append("]]>");
	FB_Pulse.append("</Declaration>");
	FB_Pulse.append("<Implementation>");
	FB_Pulse.append("<ST>");
	FB_Pulse.append("<![CDATA[");
	FB_Pulse.append("(*");
	FB_Pulse.append("**********************EPICS<-->Beckhoff integration at ESS in Lund, Sweden*******************************");
	FB_Pulse.append("Poulse generator for sending data to the IOC");
	FB_Pulse.append("Created by: Andres Quintanilla (andres.quintanilla@esss.se)");
	FB_Pulse.append("            Miklos Boros (miklos.boros@esss.se)");
	FB_Pulse.append("Date: 04/04/2018");
	FB_Pulse.append("Code must not be changed manually. Code is generated and handled by PLC factory at ESS.");
	FB_Pulse.append("Versions:");
	FB_Pulse.append("Version 1: 06/04/2018. Communication stablished and stable");
	FB_Pulse.append("**********************************************************************************************************");
	FB_Pulse.append("*)");
	FB_Pulse.append("");
	FB_Pulse.append("T_BlinkON (IN:=bEn AND NOT T_BlinkOFF.Q, PT:=tTimePulse/2);");
	FB_Pulse.append("T_BlinkOFF(IN:=T_BlinkON.Q, PT:=tTimePulse/2, Q=>bPulse);");
	FB_Pulse.append("");
	FB_Pulse.append("cCounter(CU:=bPulse,");
	FB_Pulse.append("		Reset:=,");
	FB_Pulse.append("		PV:=,");
	FB_Pulse.append("		Q:=,");
	FB_Pulse.append("		CV=>nCount);");
	FB_Pulse.append("IF nCount = 65530 THEN");
	FB_Pulse.append("	cCounter.RESET := TRUE;");
	FB_Pulse.append("ELSE");
	FB_Pulse.append("	cCounter.RESET := FALSE;");
	FB_Pulse.append("END_IF");
	FB_Pulse.append("]]>");
	FB_Pulse.append("</ST>");
	FB_Pulse.append("</Implementation>");
	FB_Pulse.append("</POU>");
	FB_Pulse.append("</TcPlcObject>");

	externalPath = os.path.join(OutputDirectory,"BECKHOFF","EPICS","ESS standard PLC code", "FB_Pulse.TcPOU")
	with open(externalPath, 'wb') as externalScl:
		for line in FB_Pulse:
			externalScl.write(line + '\r\n')

	FB_Pulse = []

def Write_DevType():

	global ActualDeviceType

	global DevTypeHeader
	global DevTypeVAR_INPUT
	global DevTypeVAR_OUTPUT
	global DevTypeVAR_TEMP
	global DevTypeBODY_HEADER
	global DevTypeBODY_CODE
	global DevTypeBODY_FOOTER

	global MaxStatusReg
	global MaxCommandReg
	externalPath = os.path.join(OutputDirectory,"BECKHOFF","EPICS","EPICS types", "FB_DEVTYPE_"+ActualDeviceType+".TcPOU")
	with open(externalPath, 'wb') as externalScl:
		#DevTypeHeader
		for line in DevTypeHeader:
			externalScl.write(line + '\r\n')
		#DevTypeVAR_INPUT
		externalScl.write("VAR_INPUT" + '\r\n')
		externalScl.write("      nOffsetStatus	:INT;			//Offset for status variables"+ '\r\n');
		externalScl.write("	  nOffsetCmd   :INT;			//Offset for command variables"+ '\r\n');
		externalScl.write("      nOffsetPar   :INT;			//Offset for parameter variables"+ '\r\n');
		for line in DevTypeVAR_INPUT:
			externalScl.write(line + '\r\n')
		externalScl.write("END_VAR" + '\r\n')
		#DevTypeVAR_OUTPUT
		externalScl.write("VAR_OUTPUT" + '\r\n')
		for line in DevTypeVAR_OUTPUT:
			externalScl.write(line + '\r\n')
		externalScl.write("END_VAR" + '\r\n')
		#DevTypeVAR_TEMP
		for line in DevTypeVAR_TEMP:
			externalScl.write(line + '\r\n')
		#DevTypeBODY_HEADER
		for line in DevTypeBODY_HEADER:
			externalScl.write(line + '\r\n')
		#DevTypeBODY_CODE
		for line in DevTypeBODY_CODE:
			externalScl.write(line + '\r\n')
		#DevTypeBODY_FOOTER
		for line in DevTypeBODY_FOOTER:
			externalScl.write(line + '\r\n')

	DevTypeHeader = []
	DevTypeVAR_INPUT = []
	DevTypeVAR_OUTPUT = []
	DevTypeVAR_TEMP = []
	DevTypeBODY_HEADER = []
	DevTypeBODY_CODE = []
	DevTypeBODY_FOOTER = []

def CloseLastVariable():
	global DevTypeBODY_CODE
	global EndString
	global EndString2
	global IsDouble

	if IsDouble:
		if EndString != "":
			DevTypeBODY_CODE.append("       " + EndString)
			EndString = ""
		if EndString2 != "":
			DevTypeBODY_CODE.append("       " + EndString2)
			EndString2 = ""
	else:
		if EndString != "":
			DevTypeBODY_CODE.append("       " + EndString)
			EndString = ""

def ProcessIFADevTypes(OutputDir, IfaPath):

	#Process IFA devices
	print("Processing .ifa file...")

	ProcessedDeviceNum = 0

	global OrderedLines
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
	global DevTypeVAR_OUTPUT
	global DevTypeVAR_TEMP
	global DevTypeBODY_HEADER
	global DevTypeBODY_CODE
	global DevTypeBODY_FOOTER

	global EPICS_PLC_TesterDB

	global FC_EPICS_DEVICE_CALLS_HEADER
	global FC_EPICS_DEVICE_CALLS_BODY
	global FC_EPICS_DEVICE_CALLS_FOOTER

	global EndString
	global EndString2
	global IsDouble

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
	global TotalStatusReg
	global TotalCommandReg
	global GlobalIDCounter
	MaxStatusReg = 0;
	MaxCommandReg = 0;
	TotalStatusReg = 0;
	TotalCommandReg = 0;

	InArray = False
	InArrayName = ""
	InArrayNum = 0

	pos = 0


	EPICS_GVL.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
	EPICS_GVL.append("<TcPlcObject ");
	EPICS_GVL.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">");
	EPICS_GVL.append("<GVL ");
	GlobalIDCounter = GlobalIDCounter + 1
	EPICS_GVL.append("Name=\"EPICS_GVL\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\">");
	EPICS_GVL.append("<Declaration>");
	EPICS_GVL.append("<![CDATA[{attribute 'qualified_only'}");
	EPICS_GVL.append("VAR_GLOBAL");
	EPICS_GVL.append("(*");
	EPICS_GVL.append("**********************EPICS<-->Beckhoff integration at ESS in Lund, Sweden*******************************");
	EPICS_GVL.append("TCP/IP server on Bechoff for EPICS<--Beckhoff communication flow.");
	EPICS_GVL.append("Modbus Server on Beckhoff for EPICS-->Beckhoff communication flow.");
	EPICS_GVL.append("//Created by: Andres Quintanilla (andres.quintanilla@esss.se)");
	EPICS_GVL.append("              Miklos Boros (miklos.boros@esss.se)");
	EPICS_GVL.append("Date: 06/04/2018");
	EPICS_GVL.append("Notes: TCP/IP server pushes data to the EPICS IOC connected. Modbus connection is open for R/W.");
	EPICS_GVL.append("Code must not be changed manually. Code is generated and handled by PLC factory at ESS.");
	EPICS_GVL.append("Versions:");
	EPICS_GVL.append("Version 1: 06/04/2018. Communication stablished and stable");
	EPICS_GVL.append("**********************************************************************************************************");
	EPICS_GVL.append("*)");
	EPICS_GVL.append("");
	EPICS_GVL.append("//Global Variables used in EPICS<-->Beckhoff communication at ESS. ");



	while pos < len(OrderedLines)-1:
		if OrderedLines[pos].rstrip() == "TOTALEPICSTOPLCLENGTH":
			TotalCommandReg = int(OrderedLines[pos + 1].rstrip())
		if OrderedLines[pos].rstrip() == "TOTALPLCTOEPICSLENGTH":
			TotalStatusReg = int(OrderedLines[pos + 1].rstrip())
		if OrderedLines[pos].rstrip() == "DEVICE":
			ProcessedDeviceNum = ProcessedDeviceNum + 1
			InStatus = False
			InCommand = False
			InParameter = False
			if FirstDevice == False:
				CloseLastVariable()
				if NewDeviceType == True:
					Write_DevType()

				else:
					DevTypeHeader = []
					DevTypeVAR_INPUT = []
					DevTypeVAR_OUTPUT = []
					DevTypeVAR_TEMP = []
					DevTypeBODY_HEADER = []
					DevTypeBODY_CODE = []
					DevTypeBODY_FOOTER = []
			else:
				FC_EPICS_DEVICE_CALLS_HEADER.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>");
				FC_EPICS_DEVICE_CALLS_HEADER.append("<TcPlcObject ");
				FC_EPICS_DEVICE_CALLS_HEADER.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">");
				FC_EPICS_DEVICE_CALLS_HEADER.append("<POU ");
				GlobalIDCounter = GlobalIDCounter + 1
				FC_EPICS_DEVICE_CALLS_HEADER.append("Name=\"FC_EPICS_DEVICE_CALLS\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\" SpecialFunc=\"None\">");
				FC_EPICS_DEVICE_CALLS_HEADER.append("");
				FC_EPICS_DEVICE_CALLS_HEADER.append("<Declaration>");
				FC_EPICS_DEVICE_CALLS_HEADER.append("<![CDATA[");
				FC_EPICS_DEVICE_CALLS_HEADER.append("FUNCTION FC_EPICS_DEVICE_CALLS : BOOL");
				FC_EPICS_DEVICE_CALLS_HEADER.append("VAR_INPUT");
				FC_EPICS_DEVICE_CALLS_HEADER.append("END_VAR");
				FC_EPICS_DEVICE_CALLS_HEADER.append("VAR");
				FC_EPICS_DEVICE_CALLS_HEADER.append("END_VAR");
				FC_EPICS_DEVICE_CALLS_HEADER.append("]]>");
				FC_EPICS_DEVICE_CALLS_HEADER.append("</Declaration>");
				FC_EPICS_DEVICE_CALLS_HEADER.append("<Implementation>");
				FC_EPICS_DEVICE_CALLS_HEADER.append("<ST>");
				FC_EPICS_DEVICE_CALLS_HEADER.append("<![CDATA[");
				FC_EPICS_DEVICE_CALLS_HEADER.append("EPICS_GVL.FB_EPICS_S7_Comm(")
				FC_EPICS_DEVICE_CALLS_HEADER.append("    bConnect:=TRUE ,")
				FC_EPICS_DEVICE_CALLS_HEADER.append("    nS7Port:=2000 ,")
				FC_EPICS_DEVICE_CALLS_HEADER.append("    nPLC_Hash:="+HASH+" ,")
				FC_EPICS_DEVICE_CALLS_HEADER.append("    tSendTrig:=T#200MS ,")
				FC_EPICS_DEVICE_CALLS_HEADER.append("    nCase=> ,")
				FC_EPICS_DEVICE_CALLS_HEADER.append("    bConnected=> ,")
				FC_EPICS_DEVICE_CALLS_HEADER.append("    bError=> );")

				FC_EPICS_DEVICE_CALLS_FOOTER.append("]]>");
				FC_EPICS_DEVICE_CALLS_FOOTER.append("</ST>");
				FC_EPICS_DEVICE_CALLS_FOOTER.append("</Implementation>");
				FC_EPICS_DEVICE_CALLS_FOOTER.append("</POU>");
				FC_EPICS_DEVICE_CALLS_FOOTER.append("</TcPlcObject>");

			FirstDevice = False
			if (OrderedLines[pos + 2].rstrip() != "DEVICE_TYPE") or (OrderedLines[pos + 4].rstrip() != "EPICSTOPLCLENGTH") or (OrderedLines[pos + 6].rstrip() != "EPICSTOPLCDATABLOCKOFFSET") or (OrderedLines[pos + 8].rstrip() != "EPICSTOPLCPARAMETERSSTART") or (OrderedLines[pos + 10].rstrip() != "PLCTOEPICSDATABLOCKOFFSET"):
				print("ERROR:")
				print("The .ifa file has a bad DEVICE format! Exiting PLCFactory...\n")
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
			print("    ", "-" * len(Text), sep='')
			print("    ", Text, sep='')
			print("    ", "-" * len(Text), sep='')

			ActualDeviceNameWhite = ActualDeviceNameWhite.replace(":","_")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("/","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("\\","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("?","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("*","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("[","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("]","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace(".","")
			ActualDeviceNameWhite = ActualDeviceNameWhite.replace("-","_")
			ActualDeviceType = ActualDeviceType.replace("-","_")

			if (int(EPICSTOPLCDATABLOCKOFFSET)<12288):
				print("ERROR:")
				print("The PLCs modbus offset held by the property: PLCF#EPICSToPLCDataBlockStartOffset in CCDB is less then 12288! \n")
				print("Make sure your PLC in CCDB is PLC_BECKHOFF type instead of PLC! \n")
				print("--- %.1f seconds ---\n" % (time.time() - start_time))
				sys.exit()


			FC_EPICS_DEVICE_CALLS_BODY.append("")
			FC_EPICS_DEVICE_CALLS_BODY.append("//********************************************")
			FC_EPICS_DEVICE_CALLS_BODY.append("// Device name: "+ActualDeviceName)
			FC_EPICS_DEVICE_CALLS_BODY.append("// Device type: "+ActualDeviceType)
			FC_EPICS_DEVICE_CALLS_BODY.append("//********************************************")
			FC_EPICS_DEVICE_CALLS_BODY.append("");
			FC_EPICS_DEVICE_CALLS_BODY.append("EPICS_GVL.FB_DEV_"+ActualDeviceNameWhite+"(")
			FC_EPICS_DEVICE_CALLS_BODY.append("       nOffsetStatus:= "+str(int(PLCTOEPICSDATABLOCKOFFSET)+10)+",")
			FC_EPICS_DEVICE_CALLS_BODY.append("       nOffsetCmd:="+str(int(EPICSTOPLCDATABLOCKOFFSET)-12288+10)+",")
			FC_EPICS_DEVICE_CALLS_BODY.append("       nOffsetPar:="+str(int(EPICSTOPLCDATABLOCKOFFSET)-12288+10+int(EPICSTOPLCPARAMETERSSTART))+");")

			EPICS_GVL.append("	FB_DEV_"+ActualDeviceNameWhite+"	:FB_DEVTYPE_"+ActualDeviceType+";					//Device instance("+ActualDeviceName+")");

			#Check if DeviceType is already generated
			if ActualDeviceType not in DeviceTypeList:

				MaxStatusReg = 0;
				MaxCommandReg = 0;

				NewDeviceType = True
				DeviceTypeList.append(ActualDeviceType)
				print("    ->  New device type found. [", ActualDeviceType, "] Creating source code...", sep='')

				DevTypeHeader.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>")
				DevTypeHeader.append("<TcPlcObject ")
				DevTypeHeader.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">")
				DevTypeHeader.append("<POU ")
				GlobalIDCounter = GlobalIDCounter + 1
				DevTypeHeader.append("Name=\"FB_DEVTYPE_"+ActualDeviceType+"\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\" SpecialFunc=\"None\">")
				DevTypeHeader.append("<Declaration>")
				DevTypeHeader.append("<![CDATA[")
				DevTypeHeader.append("FUNCTION_BLOCK FB_DEVTYPE_"+ActualDeviceType+"")

				DevTypeVAR_TEMP.append("VAR")
				DevTypeVAR_TEMP.append("	nTempUINT		:UINT;")
				DevTypeVAR_TEMP.append("	sTempHStr		:T_MaxString;")
				DevTypeVAR_TEMP.append("")
				DevTypeVAR_TEMP.append("	uREAL2UINTs	:U_REAL_UINTs;")
				DevTypeVAR_TEMP.append("	uUINTs2REAL	:U_REAL_UINTs;")
				DevTypeVAR_TEMP.append("	uTIME2UINTs	:U_TIME_UINTs;")
				DevTypeVAR_TEMP.append("	uUINTs2TIME	:U_TIME_UINTs;")
				DevTypeVAR_TEMP.append("	uDINT2UINTs	:U_DINT_UINTs;")
				DevTypeVAR_TEMP.append("	uUINTs2DINT	:U_DINT_UINTs;")
				DevTypeVAR_TEMP.append("	fValue: INT;")
				DevTypeVAR_TEMP.append("END_VAR")

				DevTypeBODY_HEADER.append("")
				DevTypeBODY_HEADER.append("]]>")
				DevTypeBODY_HEADER.append("</Declaration>")
				DevTypeBODY_HEADER.append("<Implementation>")
				DevTypeBODY_HEADER.append("<ST>")
				DevTypeBODY_HEADER.append("<![CDATA[")
				DevTypeBODY_HEADER.append("(*")
				DevTypeBODY_HEADER.append("**********************EPICS<-->Beckhoff integration at ESS in Lund, Sweden*******************************")
				DevTypeBODY_HEADER.append("Data types handler for TCP/IP communication EPICS<--Beckhoff at ESS. Lund, Sweden.")
				DevTypeBODY_HEADER.append("Created by: Andres Quintanilla (andres.quintanilla@esss.se)")
				DevTypeBODY_HEADER.append("            Miklos Boros (miklos.boros@esss.se)")
				DevTypeBODY_HEADER.append("Notes: Converts different types of data into UINT. Adds the converted data into the array to be sent to EPICS.")
				DevTypeBODY_HEADER.append("The first 10 spaces of the array are reserved. nOffset input is used for that. ")
				DevTypeBODY_HEADER.append("Code must not be changed manually. Code is generated and handled by PLC factory at ESS.")
				DevTypeBODY_HEADER.append("Versions:")
				DevTypeBODY_HEADER.append("Version 1: 06/04/2018. Communication stablished and stable")
				DevTypeBODY_HEADER.append("**********************************************************************************************************")
				DevTypeBODY_HEADER.append("*)")


				DevTypeBODY_FOOTER.append("")
				DevTypeBODY_FOOTER.append("]]>")
				DevTypeBODY_FOOTER.append("</ST>")
				DevTypeBODY_FOOTER.append("</Implementation>")
				DevTypeBODY_FOOTER.append("</POU>")
				DevTypeBODY_FOOTER.append("</TcPlcObject>")
			else:
				NewDeviceType = False

		if OrderedLines[pos].rstrip() == "DEFINE_ARRAY":
			InArray = True
			InArrayName = OrderedLines[pos+1].rstrip()
			InArrayNum = 0
		if OrderedLines[pos].rstrip() == "END_ARRAY":
			InArray = False
			DevTypeVAR_INPUT.append("      " + InArrayName + " : Array[1.."+ str(InArrayNum) +"] OF "+ ActVariableType+";   //EPICS Status variables defined in an array")
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
		# if OrderedLines[pos].rstrip().startswith("//"):
			# DevTypeBODY_CODE.append("       "+OrderedLines[pos].rstrip())
		if OrderedLines[pos].rstrip() == "VARIABLE":
			if (OrderedLines[pos + 2].rstrip() != "EPICS") or (OrderedLines[pos + 4].rstrip() != "TYPE") or	(OrderedLines[pos + 6].rstrip() != "ARRAY_INDEX") or (OrderedLines[pos + 8].rstrip() != "BIT_NUMBER"):
				print("ERROR:")
				print("The .ifa file has a bad VARIABLE format! Exiting PLCFactory...\n")
				print("--- %.1f seconds ---\n" % (time.time() - start_time))
				sys.exit()

			ActVariablePLCName = OrderedLines[pos + 1].rstrip()
			ActVariableEPICSName = OrderedLines[pos + 3].rstrip()
			ActVariableType = OrderedLines[pos + 5].rstrip()
			ActVariableArrayIndex = int(OrderedLines[pos + 7].rstrip())
			ActVariableBitNumber = int(OrderedLines[pos + 9].rstrip())

			#Close the last variable if there is a new variable
			if 	LastVariableType != ActVariableType:
				LastVariableType = ActVariableType
				CloseLastVariable()

			if InStatus:
				if not InArray:
					DevTypeVAR_INPUT.append("      " + ActVariablePLCName +"  :"+ ActVariableType+";        //EPICS Status variable: "+ActVariableEPICSName)

			if InCommand:
				DevTypeVAR_OUTPUT.append("      " + ActVariablePLCName +"  :"+ ActVariableType+";        //EPICS Command variable: "+ActVariableEPICSName)

			if InParameter:
				DevTypeVAR_OUTPUT.append("      " + ActVariablePLCName +"  :"+ ActVariableType+";        //EPICS Parameter variable: "+ActVariableEPICSName)

			#SUPPORTED TYPES
			#PLC_types = {'BOOL', 'BYTE', 'WORD', 'DWORD', 'INT', 'DINT', 'REAL', 'TIME' }

			#====== BOOL TYPE ========
			if ActVariableType == "BOOL":
				if InStatus:
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
					if InArray:
						InArrayNum = InArrayNum + 1
						DevTypeBODY_CODE.append("       nTempUINT." + str(ActVariableBitNumber)+ "           := "+ InArrayName + "[" +str(InArrayNum)+"];       //EPICSName: "+ActVariableEPICSName)
					else:
						DevTypeBODY_CODE.append("       nTempUINT." + str(ActVariableBitNumber)+ "           := "+ ActVariablePLCName + ";       //EPICSName: "+ActVariableEPICSName)
					IsDouble = False
					EndString = "EPICS_GVL.aDataS7[nOffsetStatus + "+str(ActVariableArrayIndex) +"]    := nTempUINT;"
				if InParameter or InCommand:
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       nTempUINT			:= EPICS_GVL.aDataModbus[nOffsetCmd + "+str(ActVariableArrayIndex)+"];")
					DevTypeBODY_CODE.append("       "+ActVariablePLCName+"             :=     nTempUINT." + str(ActVariableBitNumber)+ ";       //EPICSName: "+ActVariableEPICSName)
					EndString = "if (EPICS_GVL.EasyTester <> 2) THEN EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]:=0; END_IF"
					IsDouble = False
			#==========================
			#====== BYTE TYPE ========
			if ActVariableType == "BYTE":
				if InStatus:
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
					if InArray:
						InArrayNum = InArrayNum + 1
						DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := BYTE_TO_UINT("+ InArrayName + "[" +str(InArrayNum)+"]);       //EPICSName: "+ActVariableEPICSName)
					else:
						DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := BYTE_TO_UINT("+ ActVariablePLCName + ");       //EPICSName: "+ActVariableEPICSName)
					IsDouble = False
					EndString = ""
				if InParameter or InCommand:
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
					DevTypeBODY_CODE.append("       "+ActVariablePLCName+"             := UINT_TO_BYTE(EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]);       //EPICSName: "+ActVariableEPICSName)
					EndString = ""
					IsDouble = False
			#==========================
			#====== INT TYPE ========
			if ActVariableType == "INT":
				if InStatus:
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
					if InArray:
						InArrayNum = InArrayNum + 1
						DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := INT_TO_UINT("+ InArrayName + "[" +str(InArrayNum)+"]);       //EPICSName: "+ActVariableEPICSName)
					else:
						DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := INT_TO_UINT("+ ActVariablePLCName + ");       //EPICSName: "+ActVariableEPICSName)
					IsDouble = False
					EndString = ""
				if InParameter or InCommand:
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
					DevTypeBODY_CODE.append("       "+ActVariablePLCName+"             := UINT_TO_INT(EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]);       //EPICSName: "+ActVariableEPICSName)
					EndString = ""
					IsDouble = False
			#==========================
			#====== WORD TYPE ========
			if ActVariableType == "WORD":
				if InStatus:
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
					if InArray:
						InArrayNum = InArrayNum + 1
						DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := WORD_TO_UINT("+ InArrayName + "[" +str(InArrayNum)+"]);       //EPICSName: "+ActVariableEPICSName)
					else:
						DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := WORD_TO_UINT("+ ActVariablePLCName + ");       //EPICSName: "+ActVariableEPICSName)
					IsDouble = False
					EndString = ""
				if InParameter or InCommand:
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
					DevTypeBODY_CODE.append("       "+ActVariablePLCName+"             := UINT_TO_WORD(EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]);       //EPICSName: "+ActVariableEPICSName)
					EndString = ""
					IsDouble = False
			#==========================
			#====== DWORD TYPE ========
			if ActVariableType == "DWORD":
				if InStatus:
					if InArray:
						InArrayNum = InArrayNum + 1
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
					DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := DWORD_TO_UINT("+ ActVariablePLCName + ");       //EPICSName: "+ActVariableEPICSName)
					DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(int(ActVariableArrayIndex)+1)+ "]           := DWORD_TO_UINT(SHR("+ ActVariablePLCName + ",16));       //EPICSName: "+ActVariableEPICSName)
					IsDouble = False
					EndString = ""
				if InParameter or InCommand:
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
					DevTypeBODY_CODE.append("       DWORD for Modbus is not supported")
					EndString = ""
					IsDouble = False
			#==========================
			#====== REAL TYPE ========
			if ActVariableType == "REAL":
				if InStatus:
					if InArray:
						InArrayNum = InArrayNum + 1
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       uREAL2UINTs.fValue :="+ ActVariablePLCName + ";")
					DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := uREAL2UINTs.stLowHigh.nLow;       //EPICSName: "+ActVariableEPICSName)
					DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(int(ActVariableArrayIndex)+1)+ "]           := uREAL2UINTs.stLowHigh.nHigh;       //EPICSName: "+ActVariableEPICSName)
					IsDouble = False
					EndString = ""
				if InParameter or InCommand:
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
					DevTypeBODY_CODE.append("       uUINTs2REAL.stLowHigh.nLow             := EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "];       //EPICSName: "+ActVariableEPICSName)
					DevTypeBODY_CODE.append("       uUINTs2REAL.stLowHigh.nHigh             := EPICS_GVL.aDataModbus[nOffsetCmd + " + str(int(ActVariableArrayIndex)+1)+ "];       //EPICSName: "+ActVariableEPICSName)
					EndString =  ActVariablePLCName + "				:= uUINTs2REAL.fValue;"
					IsDouble = False
			#==========================
			#====== DINT TYPE ========
			if ActVariableType == "DINT":
				if InStatus:
					if InArray:
						InArrayNum = InArrayNum + 1
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       uDINT2UINTs.nValue :="+ ActVariablePLCName + ";")
					DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := uDINT2UINTs.stLowHigh.nLow;       //EPICSName: "+ActVariableEPICSName)
					DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(int(ActVariableArrayIndex)+1)+ "]           := uDINT2UINTs.stLowHigh.nHigh;       //EPICSName: "+ActVariableEPICSName)
					IsDouble = False
					EndString = ""
				if InParameter or InCommand:
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
					DevTypeBODY_CODE.append("       uUINTs2DINT.stLowHigh.nLow             := EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "];       //EPICSName: "+ActVariableEPICSName)
					DevTypeBODY_CODE.append("       uUINTs2DINT.stLowHigh.nHigh             := EPICS_GVL.aDataModbus[nOffsetCmd + " + str(int(ActVariableArrayIndex)+1)+ "];       //EPICSName: "+ActVariableEPICSName)
					EndString =  ActVariablePLCName + "				:= uUINTs2DINT.nValue;"
					IsDouble = False
			#==========================
			#====== TIME TYPE ========
			if ActVariableType == "TIME":
				if InStatus:
					if InArray:
						InArrayNum = InArrayNum + 1
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
						DevTypeBODY_CODE.append("       uTIME2UINTs.tValue :="+ ActVariablePLCName + ";")
					DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := uTIME2UINTs.stLowHigh.nLow;       //EPICSName: "+ActVariableEPICSName)
					DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(int(ActVariableArrayIndex)+1)+ "]           := uTIME2UINTs.stLowHigh.nHigh;       //EPICSName: "+ActVariableEPICSName)
					IsDouble = False
					EndString = ""
				if InParameter or InCommand:
					if StartingRegister != ActVariableArrayIndex:
						CloseLastVariable()
						StartingRegister = ActVariableArrayIndex
						DevTypeBODY_CODE.append("")
					DevTypeBODY_CODE.append("       uUINTs2TIME.stLowHigh.nLow             := EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "];       //EPICSName: "+ActVariableEPICSName)
					DevTypeBODY_CODE.append("       uUINTs2TIME.stLowHigh.nHigh             := EPICS_GVL.aDataModbus[nOffsetCmd + " + str(int(ActVariableArrayIndex)+1)+ "];       //EPICSName: "+ActVariableEPICSName)
					EndString =  ActVariablePLCName + "				:= uUINTs2TIME.tValue;"
					IsDouble = False
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
	if NewDeviceType == True:
		Write_DevType()
	else:
		DevTypeHeader = []
		DevTypeVAR_INPUT = []
		DevTypeVAR_OUTPUT = []
		DevTypeVAR_TEMP = []
		DevTypeBODY_HEADER = []
		DevTypeBODY_CODE = []
		DevTypeBODY_FOOTER = []

	print("\nTotal", str(ProcessedDeviceNum), "device(s) processed.")
	if not Direct:
		print("Total", str(len(DeviceTypeList)), "device type(s) generated.\n")
	else:
		print("Device types are not being generated. (Direct mode)\n")


def produce(OutputDir, IfaPath, SclPath, TIAVersion, **kwargs):

	global MakeOutputFile
	global OutputDirectory
	global TotalStatusReg
	global TotalCommandReg
	global start_time

	start_time      = time.time()
	OutputDirectory = OutputDir

	generated_files = dict()

	#Pre-processing of the IFA file
	Pre_ProcessIFA(IfaPath)

	if HASH != "" and DeviceNum != 0:

		helpers.makedirs(os.path.join(OutputDirectory,"BECKHOFF","EPICS","EPICS types"))
		helpers.makedirs(os.path.join(OutputDirectory,"BECKHOFF","EPICS","EPICS calls"))
		helpers.makedirs(os.path.join(OutputDirectory,"BECKHOFF","EPICS","ESS standard PLC code"))

		#Process devices/device types
		ProcessIFADevTypes(OutputDir, IfaPath)

		#Generate FC_EPICS_DEVICE_CALLS.TcPOU
		Write_EPICS_device_calls();

		#Generate ST_2_UINT.TcDUT
		#Generate U_DINT_UINTs.TcDUT
		#Generate U_REAL_UINTs.TcDUT
		#Generate U_TIME_UINTs.TcDUT
		Write_Structs_and_Unions();

		#Generate FB_EPICS_S7_Comm.TcPOU
		Write_FB_EPICS_S7_Comm()

		#Generate FB_Pulse.TcPOU
		Write_FB_Pulse()

		#Generate EPICS_GVL.TcGVL
		Write_EPICS_GVL()

		generated_files['BECKHOFF'] = shutil.make_archive(os.path.join(OutputDirectory,"PLCFactory_external_source_Beckhoff"), 'zip', os.path.join(OutputDirectory,"BECKHOFF"))

		return generated_files


	else:
		if HASH == "":
			print("ERROR:")
			print("After pre-processing the .IFA file there was no HASH code inside!\n")
			return generated_files
		if DeviceNum == 0:
			print("ERROR:")
			print("After pre-processing the .IFA file there were no DEVICES inside!\n")
			return generated_files


def main(argv):
	os.system('clear')

	print("  _____       _             __                 ______         _                   ")
	print(" |_   _|     | |           / _|               |  ____|       | |                  ")
	print("   | |  _ __ | |_ ___ _ __| |_ __ _  ___ ___  | |__ __ _  ___| |_ ___  _ __ _   _ ")
	print("   | | | '_ \| __/ _ \ '__|  _/ _` |/ __/ _ \ |  __/ _` |/ __| __/ _ \| '__| | | |")
	print("  _| |_| | | | ||  __/ |  | || (_| | (_|  __/ | | | (_| | (__| || (_) | |  | |_| |")
	print(" |_____|_| |_|\__\___|_|  |_| \__,_|\___\___| |_|  \__,_|\___|\__\___/|_|   \__, |")
	print("                                                                             __/ |")
	print(" Copyright 2017-2018, European Spallation Source, Lund                      |___/ \n")



	start_time     = time.time()

	print("InterfaceFactory can't be run in standalone mode! Use PLCFactory instead.")
	print()
	print()

if __name__ == "__main__":
	main(sys.argv[1:])
