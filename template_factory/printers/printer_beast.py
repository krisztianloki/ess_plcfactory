from __future__ import absolute_import

""" Template Factory: BeastFactory printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2019, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER
from tf_ifdef import ALARM



def printer():
    return [ (BEAST.name(), BEAST),
             (BEAST_TEMPLATE.name(), BEAST_TEMPLATE) ]




class BEAST_BASE(PRINTER):
    def __init__(self):
        super(BEAST_BASE, self).__init__(comments = False, preserve_empty_lines = False, show_origin = False)


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        super(BEAST_BASE, self).header(output, **keyword_params)
        self.add_filename_header(output, extension = self._extension())



class BEAST(BEAST_BASE):
    def __init__(self):
        super(BEAST, self).__init__()


    @staticmethod
    def name():
        return "BEAST"


    def _extension(self):
        return "alarms"


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        printed = False
        device = keyword_params["DEVICE"].name()

        for var in if_def.alarms():
            if not printed:
                printed = True
                self._append("""
{separator}
# {device} #
{separator}
""".format(separator = "#" * (4 + len(device)),
           device    = device), output)

            self._append("""pv("{inst_slot}:{pv_name}")
\tdescription("{desc}")""".format(inst_slot = self.inst_slot(),
                                  pv_name   = var.pv_name(),
                                  desc      = var.get_parameter("PV_DESC", "")), output)



class BEAST_TEMPLATE(BEAST_BASE):
    def __init__(self):
        super(BEAST_TEMPLATE,  self).__init__()
        self._devtypes = []


    @staticmethod
    def name():
        return "BEAST-TEMPLATE"


    def _extension(self):
        return "alarms-template"


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        device = keyword_params["DEVICE"]

        device_type = device.deviceType()
        if device_type in self._devtypes:
            return

        self._devtypes.append(device_type)
        printed = False

        for var in if_def.alarms():
            if not printed:
                printed = True
                self._append("""
{separator}
# {devtype} #
{separator}
""".format(separator = "#" * (4 + len(device_type)),
           devtype   = device_type), output)

            self._append("""pv("{pv_name}")
\tdescription("{desc}")""".format(pv_name   = var.pv_name(),
                                  desc      = var.get_parameter("PV_DESC", "")), output)
