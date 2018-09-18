from __future__ import print_function

class IFA(object):
    valid_device_entries = [ 'DEVICE', 'DEVICE_TYPE', 'EPICSTOPLCPARAMETERSSTART', 'EPICSTOPLCLENGTH', 'EPICSTOPLCDATABLOCKOFFSET', 'PLCTOEPICSDATABLOCKOFFSET',
                             'BLOCK', 'DEFINE_ARRAY', 'END_ARRAY',
                             'VARIABLE', 'EPICS', 'TYPE', 'ARRAY_INDEX', 'BIT_NUMBER', 'BEAST', 'ARCHIVE' ]

    valid_line_types     = [ 'HASH', 'MAX_IO_DEVICES', 'MAX_LOCAL_MODULES', 'MAX_MODULES_IN_IO_DEVICE', 'PLC_TYPE',
                             'TOTALEPICSTOPLCLENGTH', 'TOTALPLCTOEPICSLENGTH' ]
    valid_line_types.extend(valid_device_entries)


    class Exception(Exception):
        pass



    class Warning(Exception):
        pass



    class FatalException(Exception):
        pass



    class Device(object):
        def __init__(self):
            self.lines      = []
            self.parameters = dict()


        def append(self, line):
            self.lines.append(line)


        def extend(self, area):
            self.lines.extend(area)



    def __init__(self, IfaPath):
        self.IfaPath                  = IfaPath
        self.HASH                     = None
        self.MAX_IO_DEVICES           = 0
        self.MAX_LOCAL_MODULES        = 0
        self.MAX_MODULES_IN_IO_DEVICE = 0
        self.PLC_type                 = ""
        self.TOTALEPICSTOPLCLENGTH    = 0
        self.TOTALPLCTOEPICSLENGTH    = 0
        self.Devices                  = []

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

            device = None

            for line in f:
                line = line.strip()

                if linetype is None:
                    if line.startswith("//"):
                        if Area is not None:
                            Area.append(line)
                        elif device is not None:
                            device.append(line)
                    else:
                        if line not in IFA.valid_line_types:
                            raise IFA.FatalException("Unknown IFA keyword", line)

                        linetype = line
                    continue

                try:
                    if linetype == "HASH":
                        self.HASH = line
                        continue

                    elif linetype == "MAX_IO_DEVICES":
                        self.MAX_IO_DEVICES = int(line)
                        if self.MAX_IO_DEVICES <= 0:
                            self.MAX_IO_DEVICES = 1
                        continue

                    elif linetype == "MAX_LOCAL_MODULES":
                        self.MAX_LOCAL_MODULES = int(line)
                        if self.MAX_LOCAL_MODULES <= 0:
                            self.MAX_LOCAL_MODULES = 1
                        continue

                    elif linetype == "MAX_MODULES_IN_IO_DEVICE":
                        self.MAX_MODULES_IN_IO_DEVICE = int(line)
                        if self.MAX_MODULES_IN_IO_DEVICE <= 0:
                            self.MAX_MODULES_IN_IO_DEVICE = 1
                        continue

                    elif linetype == "PLC_TYPE":
                        self.PLC_type = line
                        continue

                    elif linetype == "TOTALEPICSTOPLCLENGTH":
                        self.TOTALEPICSTOPLCLENGTH = int(line)
                        continue

                    elif linetype == "TOTALPLCTOEPICSLENGTH":
                        self.TOTALPLCTOEPICSLENGTH = int(line)
                        continue

                    elif linetype == "DEVICE":
                        if device is not None:
                            device.extend(StatusArea)
                            device.extend(CommandArea)
                            device.extend(ParameterArea)

                        StatusArea    = []
                        CommandArea   = []
                        ParameterArea = []
                        Area          = None
                        device        = IFA.Device()
                        self.Devices.append(device)

                    if device and linetype not in IFA.valid_device_entries:
                        raise IFA.FatalException("Unknown device keyword", linetype)

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
                    elif device is not None:
                        device.parameters[linetype] = line

                finally:
                    linetype = None

            if linetype is not None:
                raise IFA.FatalException("""IFA is not well formed. Last lines:
{type}
{line}
""".format(type = linetype,
           line = line))

            if device is not None:
                device.extend(StatusArea)
                device.extend(CommandArea)
                device.extend(ParameterArea)

        if self.HASH is None:
            raise IFA.Warning("""
ERROR:
After pre-processing the .IFA file there was no HASH code inside!
""")

        if not self.Devices:
            raise IFA.Warning("""
ERROR:
After pre-processing the .IFA file there were no DEVICES inside!
""")

        print("Total", str(len(self.Devices)), "device(s) pre-processed.\n")

