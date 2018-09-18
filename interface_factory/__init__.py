from __future__ import print_function

class IFA(object):
    valid_variable_entries = [ 'VARIABLE', 'EPICS', 'TYPE', 'ARRAY_INDEX', 'BIT_NUMBER', 'BEAST', 'ARCHIVE' ]

    valid_device_entries   = [ 'DEVICE', 'DEVICE_TYPE', 'EPICSTOPLCPARAMETERSSTART', 'EPICSTOPLCLENGTH', 'EPICSTOPLCDATABLOCKOFFSET', 'PLCTOEPICSDATABLOCKOFFSET',
                               'BLOCK', 'DEFINE_ARRAY', 'END_ARRAY' ]
    valid_device_entries.extend(valid_variable_entries)

    valid_line_types       = [ 'HASH', 'MAX_IO_DEVICES', 'MAX_LOCAL_MODULES', 'MAX_MODULES_IN_IO_DEVICE', 'PLC_TYPE',
                               'TOTALEPICSTOPLCLENGTH', 'TOTALPLCTOEPICSLENGTH' ]
    valid_line_types.extend(valid_device_entries)


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
            self.parameters = { "DEVICE": name }

            self.status_items    = []
            self.command_items   = []
            self.parameter_items = []


        def __iter__(self):
            return IFA.Device.DeviceItemIterator([ iter(self.status_items), iter(self.command_items), iter(self.parameter_items) ])


        def append(self, line):
            self.comments.append(line)


        def extend(self, area):
            self.comments.extend(area)



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



    class Variable(DeviceItem):
        def __init__(self, name):
            super(IFA.Variable, self).__init__()
            self.parameters = { "VARIABLE": name }


        def __repr__(self):
            return repr(self.parameters)


        def is_variable(self):
            return True



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

            Area     = None

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
                        item = None
                        continue

                    elif linetype == "DEFINE_ARRAY":
                        Area.append(IFA.WrapperArrayStart(line))
                        continue

                    elif linetype == "END_ARRAY":
                        Area.append(IFA.WrapperArrayEnd(line))
                        continue

                    elif linetype == "VARIABLE":
                        item = IFA.Variable(line)
                        Area.append(item)
                        continue

                    if item and linetype not in IFA.valid_variable_entries:
                        raise IFA.FatalException("Unknown VARIABLE keyword", linetype)

                    if item is not None:
                        item.parameters[linetype] = line
                    elif device is not None:
                        device.parameters[linetype] = line
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
