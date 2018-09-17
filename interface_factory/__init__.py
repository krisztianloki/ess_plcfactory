from __future__ import print_function

class IFA(object):
    class Exception(Exception):
        pass



    class Warning(Exception):
        pass



    class FatalException(Exception):
        pass



    def __init__(self, IfaPath):
        self.IfaPath                  = IfaPath
        self.DeviceNum                = 0
        self.HASH                     = None
        self.MAX_IO_DEVICES           = 0
        self.MAX_LOCAL_MODULES        = 0
        self.MAX_MODULES_IN_IO_DEVICE = 0
        self.OrderedLines             = []

        self.PreProcess()


    def PreProcess(self):
        print("""

*******************************************
*                                         *
*   Generating Siemens PLC source code    *
*                                         *
*******************************************

PLCFactory file location: {}
Pre-processing .ifa file...""".format(self.IfaPath))
        #Pre process IFA to have Status, Command, Parameter order

        StatusArea = []
        CommandArea = []
        ParameterArea = []
        Comments = []

        InStatus = False
        InCommand = False
        InParameter = False

        FirstDevice = True

        with open(self.IfaPath) as f:
            lines = f.readlines()
            pos = 0
            while pos < len(lines):
                if lines[pos].rstrip() == "HASH":
                    self.HASH = lines[pos+1].rstrip()
                if lines[pos].rstrip() == "MAX_IO_DEVICES":
                    self.MAX_IO_DEVICES = int(lines[pos+1].strip())
                    if self.MAX_IO_DEVICES <= 0:
                        self.MAX_IO_DEVICES = 1
                if lines[pos].rstrip() == "MAX_LOCAL_MODULES":
                    self.MAX_LOCAL_MODULES = int(lines[pos+1].strip())
                    if self.MAX_LOCAL_MODULES <= 0:
                        self.MAX_LOCAL_MODULES = 1
                if lines[pos].rstrip() == "MAX_MODULES_IN_IO_DEVICE":
                    self.MAX_MODULES_IN_IO_DEVICE = int(lines[pos+1].strip())
                    if self.MAX_MODULES_IN_IO_DEVICE <= 0:
                        self.MAX_MODULES_IN_IO_DEVICE = 1
                if lines[pos].rstrip() == "DEVICE":
                    self.DeviceNum = self.DeviceNum + 1
                    InStatus = False
                    InCommand = False
                    InParameter = False
                    if FirstDevice == False:
                        for line in StatusArea:
                            self.OrderedLines.append(line)
                        for line in CommandArea:
                            self.OrderedLines.append(line)
                        for line in ParameterArea:
                            self.OrderedLines.append(line)
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
                    self.OrderedLines.append(lines[pos])
                pos = pos + 1

        for line in StatusArea:
            self.OrderedLines.append(line)
        for line in CommandArea:
            self.OrderedLines.append(line)
        for line in ParameterArea:
            self.OrderedLines.append(line)

        if self.HASH is None:
            raise IFA.Warning("""
ERROR:
After pre-processing the .IFA file there was no HASH code inside!
""")

        if self.DeviceNum == 0:
            raise IFA.Warning("""
ERROR:
After pre-processing the .IFA file there were no DEVICES inside!
""")

        print("Total", str(self.DeviceNum), "device(s) pre-processed.\n")

