""" Template Factory: PLC Diagnostics printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER



def printer():
    return (DIAG.name(), DIAG)




class DIAG(PRINTER):
    def __init__(self):
        PRINTER.__init__(self)


    @staticmethod
    def name():
        return "DIAG"


    #
    # HEADER
    #
    def header(self, output):
        PRINTER.header(self, output)

        self._append("""#FILENAME {inst_slot}-DiagConfig.txt
MAX_IO_DEVICES
{max_io_devices}
MAX_LOCAL_MODULES
{max_local_modules}
MAX_MODULES_IN_IO_DEVICE
{max_modules_in_io_device}
""".format(inst_slot                = self.inst_slot(),
           max_io_devices           = self.plcf("PLC-DIAG:Max-IO-Devices"),
           max_local_modules        = self.plcf("PLC-DIAG:Max-Local-Modules"),
           max_modules_in_io_device = self.plcf("PLC-DIAG:Max-Modules-In-IO-Device")), output)


    #
    # BODY
    #
    def body(self, if_def, output):
        PRINTER.body(self, if_def, output)


    #
    # FOOTER
    #
    def footer(self, output):
        PRINTER.footer(self, output)
