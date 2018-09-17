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
        self.PLC_type                 = ""
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

        # Pre process IFA to have Status, Command, Parameter order
        with open(self.IfaPath) as f:
            linetype = None

            StatusArea    = []
            CommandArea   = []
            ParameterArea = []
            Area          = None

            for line in f:
                line = line.strip()

                if linetype is None:
                    if line.startswith("//"):
                        if Area is not None:
                            Area.append(line)
                        else:
                            self.OrderedLines.append(line)
                    else:
                        linetype = line
                    continue


                if linetype == "HASH":
                    self.HASH = line

                elif linetype == "MAX_IO_DEVICES":
                    self.MAX_IO_DEVICES = int(line)
                    if self.MAX_IO_DEVICES <= 0:
                        self.MAX_IO_DEVICES = 1

                elif linetype == "MAX_LOCAL_MODULES":
                    self.MAX_LOCAL_MODULES = int(line)
                    if self.MAX_LOCAL_MODULES <= 0:
                        self.MAX_LOCAL_MODULES = 1

                elif linetype == "MAX_MODULES_IN_IO_DEVICE":
                    self.MAX_MODULES_IN_IO_DEVICE = int(line)
                    if self.MAX_MODULES_IN_IO_DEVICE <= 0:
                        self.MAX_MODULES_IN_IO_DEVICE = 1

                elif linetype == "PLC_TYPE":
                    self.PLC_type = line

                elif linetype == "DEVICE":
                    self.DeviceNum = self.DeviceNum + 1

                    self.OrderedLines.extend(StatusArea)
                    self.OrderedLines.extend(CommandArea)
                    self.OrderedLines.extend(ParameterArea)

                    StatusArea    = []
                    CommandArea   = []
                    ParameterArea = []
                    Area          = None

                if linetype == "BLOCK":
                    if line == "STATUS":
                        Area = StatusArea
                    elif line == "COMMAND":
                        Area = CommandArea
                    elif line == "PARAMETER":
                        Area = ParameterArea
                    else:
                        raise IFA.FatalException("Unknown block type", line)

                if Area is not None:
                    Area.append(linetype)
                    Area.append(line)
                else:
                    self.OrderedLines.append(linetype)
                    self.OrderedLines.append(line)

                linetype = None

            if linetype is not None:
                raise IFA.FatalException("""IFA is not well formed. Last lines:
{type}
{line}
""".format(type = linetype,
           line = line))

            self.OrderedLines.extend(StatusArea)
            self.OrderedLines.extend(CommandArea)
            self.OrderedLines.extend(ParameterArea)

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

