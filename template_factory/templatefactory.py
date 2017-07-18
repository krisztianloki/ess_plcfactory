#!/usr/bin/python

__author__    = "Krisztian Loki"
__copyright__ = "Copyright 2017, European Spallation Source, Lund"
__license__   = "GPLv3"


import argparse
import tf as tf


def createTemplate(definition, if_def, printername):
    printer = tf.get_printer(printername)
    header = []
    printer.header(header)
    printer.write("PLC_HEADER", header)

    body = []
    printer.body(if_def, body)
    printer.write(definition, body)

    footer = []
    printer.footer(footer)
    printer.write("PLC_FOOTER", footer)



def processDefinitionFile(definition, printers):
    assert isinstance(definition, str)
    assert isinstance(printers,   list)

    print "Processing " + definition + "..."

    with open(definition) as m:
        if_def = tf.processLines(None, m)


    if if_def is None:
        exit(1)

    for printer in printers:
        createTemplate(definition, if_def, printer)

    print



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Parses interface definitons and creates PLCFactory templates")

    available_printers = tf.available_printers()

    parser.add_argument('--printers',
                        '-p',
                        help     = 'template printers',
                        nargs    = '+',
                        choices  = available_printers,
                        type     = str)

    parser.add_argument('definitions',
                        help     = 'interface definitions',
                        nargs    = '+',
                        type     = str)

    args = parser.parse_args()

    if args.printers is None:
        args.printers = available_printers

    map(lambda t: processDefinitionFile(t, args.printers), args.definitions)
