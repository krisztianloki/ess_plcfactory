from __future__ import print_function

class IFA(object):
    mandatory_variable_properties = set([ 'VARIABLE', 'EPICS', 'TYPE', 'ARRAY_INDEX', 'BIT_NUMBER' ])

    valid_variable_entries = set([ 'BEAST', 'ARCHIVE' ])
    valid_variable_entries.update(mandatory_variable_properties)

    mandatory_device_properties = set([ 'DEVICE', 'DEVICE_TYPE', 'EPICSTOPLCPARAMETERSSTART', 'EPICSTOPLCLENGTH', 'EPICSTOPLCDATABLOCKOFFSET', 'PLCTOEPICSDATABLOCKOFFSET' ])

    valid_device_entries   = set([ 'BLOCK', 'DEFINE_ARRAY', 'END_ARRAY' ])
    valid_device_entries.update(mandatory_device_properties)
    valid_device_entries.update(valid_variable_entries)

    mandatory_ifa_properties = set([ 'HASH', 'MAX_IO_DEVICES', 'MAX_LOCAL_MODULES', 'MAX_MODULES_IN_IO_DEVICE', 'PLC_TYPE', 'TOTALEPICSTOPLCLENGTH', 'TOTALPLCTOEPICSLENGTH' ])

    valid_line_types = set(mandatory_ifa_properties)
    valid_line_types.update(valid_device_entries)


    class Exception(Exception):
        pass



    class Warning(Exception):
        pass



    class FatalException(Exception):
        pass



    class Device(object):
        class DeviceItemIterator(object):
            def __init__(self, iters):
                self.__iters = iters


            def next(self):
                return self.__next__()


            def __next__(self):
                try:
                    return next(self.__iters[0])
                except StopIteration:
                    self.__iters.pop(0)
                    return self.next()
                except IndexError:
                    raise StopIteration



        def __init__(self, name):
            self.comments   = []
            self.properties = { "DEVICE": name }

            self.status_items    = []
            self.command_items   = []
            self.parameter_items = []


        def __iter__(self):
            return IFA.Device.DeviceItemIterator([ iter(self.status_items), iter(self.command_items), iter(self.parameter_items) ])


        def append(self, line):
            self.comments.append(line)


        def extend(self, area):
            self.comments.extend(area)


        def check(self):
            if not IFA.mandatory_device_properties <= set(self.properties.keys()):
                raise IFA.FatalException("Missing DEVICE properties", IFA.mandatory_device_properties - set(self.properties.keys()))



    class DeviceItem(object):
        def __init__(self):
            self.comments = []


        def append(self, line):
            self.comments.append(line)


        def extend(self, area):
            self.comments.extend(area)


        def is_block(self):
            return False


        def is_variable(self):
            return False


        def is_wrapper_array(self):
            return False


        def check(self):
            pass



    class Block(DeviceItem):
        def __init__(self, block):
            super(IFA.Block, self).__init__()
            self.__block = block[0]


        def __repr__(self):
            return "BLOCK " + self.__block


        def is_block(self):
            return True


        def is_status(self):
            return self.__block == 'S'


        def is_command(self):
            return self.__block == 'C'


        def is_parameter(self):
            return self.__block == 'P'



    class Variable(Block):
        def __init__(self, name, block):
            super(IFA.Variable, self).__init__(block)
            self.properties = { "VARIABLE": name }


        def __repr__(self):
            return repr(self.properties)


        def is_block(self):
            return False


        def is_variable(self):
            return True


        def check(self):
            if not IFA.mandatory_variable_properties <= set(self.properties.keys()):
                raise IFA.FatalException("Missing VARIABLE properties", IFA.mandatory_variable_properties - set(self.properties.keys()))



    class WrapperArray(DeviceItem):
        def __init__(self, array_name, start):
            super(IFA.WrapperArray, self).__init__()
            self.__array_name = array_name
            self.__start      = start


        def __repr__(self):
            return ("BEGIN " if self.__start else "END ") + self.__array_name


        def is_wrapper_array(self):
            return True


        def is_start(self):
            return self.__start


        def name(self):
            return self.__array_name



    class WrapperArrayStart(WrapperArray):
        def __init__(self, array_name):
            super(IFA.WrapperArrayStart, self).__init__(array_name, True)



    class WrapperArrayEnd(WrapperArray):
        def __init__(self, array_name):
            super(IFA.WrapperArrayEnd, self).__init__(array_name, False)



    def __init__(self, IfaPath):
        self.properties               = dict()
        self.IfaPath                  = IfaPath
        self.HASH                     = None
        self.MAX_IO_DEVICES           = 0
        self.MAX_LOCAL_MODULES        = 0
        self.MAX_MODULES_IN_IO_DEVICE = 0
        self.PLC_type                 = ""
        self.TOTALEPICSTOPLCLENGTH    = 0
        self.TOTALPLCTOEPICSLENGTH    = 0
        self.Devices                  = []

        self.PreParse()
        self.Check()


    def PreParse(self):
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

            Area     = None
            Block    = None

            device   = None
            item     = None

            for line in f:
                line = line.strip()

                if linetype is None:
                    if line.startswith("//"):
                        if item   is not None:
                            item.append(line)
                        elif device is not None:
                            device.append(line)
                    else:
                        if line not in IFA.valid_line_types:
                            raise IFA.FatalException("Unknown IFA keyword", line)

                        linetype = line
                    continue

                try:
                    if linetype in IFA.mandatory_ifa_properties:
                        if linetype == "HASH":
                            self.HASH = line

                        elif linetype == "MAX_IO_DEVICES":
                            line = int(line)
                            if line <= 0:
                                line = 1
                            self.MAX_IO_DEVICES = line

                        elif linetype == "MAX_LOCAL_MODULES":
                            line = int(line)
                            if line <= 0:
                                line = 1
                            self.MAX_LOCAL_MODULES = line

                        elif linetype == "MAX_MODULES_IN_IO_DEVICE":
                            line = int(line)
                            if line <= 0:
                                line = 1
                            self.MAX_MODULES_IN_IO_DEVICE = line

                        elif linetype == "PLC_TYPE":
                            self.PLC_type = line

                        elif linetype == "TOTALEPICSTOPLCLENGTH":
                            line = int(line)
                            self.TOTALEPICSTOPLCLENGTH = line

                        elif linetype == "TOTALPLCTOEPICSLENGTH":
                            line = int(line)
                            self.TOTALPLCTOEPICSLENGTH = line

                        self.properties[linetype] = line
                        continue

                    elif linetype == "DEVICE":
                        Area   = None
                        item   = None
                        device = IFA.Device(line)
                        self.Devices.append(device)
                        continue

                    if device and linetype not in IFA.valid_device_entries:
                        raise IFA.FatalException("Unknown DEVICE keyword", linetype)

                    if linetype == "BLOCK":
                        if line == "STATUS":
                            Area = device.status_items
                        elif line == "COMMAND":
                            Area = device.command_items
                        elif line == "PARAMETER":
                            Area = device.parameter_items
                        else:
                            raise IFA.FatalException("Unknown BLOCK type", line)
                        Area.append(IFA.Block(line))
                        Block = line
                        item  = None
                        continue

                    elif linetype == "DEFINE_ARRAY":
                        Area.append(IFA.WrapperArrayStart(line))
                        continue

                    elif linetype == "END_ARRAY":
                        Area.append(IFA.WrapperArrayEnd(line))
                        continue

                    elif linetype == "VARIABLE":
                        item = IFA.Variable(line, Block)
                        Area.append(item)
                        continue

                    if item and linetype not in IFA.valid_variable_entries:
                        raise IFA.FatalException("Unknown VARIABLE keyword", linetype)

                    if item is not None:
                        item.properties[linetype] = line
                    elif device is not None:
                        device.properties[linetype] = line
                    else:
                        raise IFA.FatalException("Neither variable nor device")

                finally:
                    linetype = None

            if linetype is not None:
                raise IFA.FatalException("""IFA is not well formed. Last lines:
{type}
{line}
""".format(type = linetype,
           line = line))

        if not self.Devices:
            raise IFA.Warning("""
Warning:
After pre-processing the .IFA file there were no DEVICES inside!
""")

        print("Total", str(len(self.Devices)), "device(s) pre-processed.\n")


    def Check(self):
        if not IFA.mandatory_ifa_properties <= set(self.properties.keys()):
            raise IFA.FatalException("Missing IFA properties", IFA.mandatory_ifa_properties - set(self.properties.keys()))

        for device in self.Devices:
            device.check()

            for item in device:
                item.check()
