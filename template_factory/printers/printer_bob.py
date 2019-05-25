from __future__ import absolute_import

""" Template Factory: CS-Studio Display Builder printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER
from tf_ifdef import BASE_TYPE



def printer():
    return (BOB.name(), BOB)




class BOB(PRINTER):
    def __init__(self):
        PRINTER.__init__(self, comments = False, preserve_empty_lines = False, show_origin = False)
        self._x      = 0
        self._y      = 0


    @staticmethod
    def name():
        return "BOB"


    #
    # HEADER
    #
    def header(self, output, **keyword_params):
        PRINTER.header(self, output, **keyword_params)
        self.add_filename_header(output, extension = "bob")
        self._append("""<?xml version="1.0" encoding="UTF-8"?>
<display version="2.0.0">
  <name>Display</name>""", output)


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output):
        x                = 0
        y                = 0
        group_width      = 42;
        group_height     = 42;
        label_width      = 200
        textupdate_width = 150

        self._append("""  <widget type="group" version="2.0.0">
    <name>{group}</name>
    <x>{x}</x>
    <y>{y}</y>
    <transparent>true</transparent>""".format(group = self.inst_slot(),
                                              x     = self._x,
                                              y     = self._y), output)

        for stat_var in if_def.interfaces():
            if isinstance(stat_var, BASE_TYPE) and stat_var.is_status():
                self._append("""    <widget type="label" version="2.0.0">
      <name>Label {label_name}</name>
      <text>{text}</text>
      <x>{label_x}</x>
      <y>{label_y}</y>
      <width>{label_width}</width>
      <horizontal_alignment>2</horizontal_alignment>
      <vertical_alignment>1</vertical_alignment>
      <tooltip>{text}</tooltip>
    </widget>
    <widget type="textupdate" version="2.0.0">
      <name>{textupdate_name}</name>
      <pv_name>{pv_name}</pv_name>
      <x>{textupdate_x}</x>
      <y>{textupdate_y}</y>
      <width>{textupdate_width}</width>
    </widget>""".format(label_name       = stat_var.name(),
                        text             = "{}:".format(stat_var.get_parameter("PV_DESC", stat_var.name())).replace("<", "&lt;").replace(">", "&gt;"),
                        label_x          = x,
                        label_y          = y,
                        label_width      = label_width,
                        textupdate_name  = stat_var.name(),
                        pv_name          = "{}:{}".format(self.inst_slot(), stat_var.pv_name()),
                        textupdate_x     = x + label_width + 10,
                        textupdate_y     = y,
                        textupdate_width = textupdate_width), output)
                y = y + 25

        group_width  = group_width + label_width + 10 + textupdate_width
        group_height = group_height + y
        self._y      = self._y + group_height + 20

        self._append("""    <width>{group_width}</width>
    <height>{group_height}</height>
</widget>""".format(group_width  = group_width,
                    group_height = group_height), output)


    #
    # FOOTER
    #
    def footer(self, output):
        PRINTER.footer(self, output)
        self._append("""<height>{height}</height>
</display>
""".format(height = self._y), output)
