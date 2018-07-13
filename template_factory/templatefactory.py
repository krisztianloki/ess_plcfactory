#!/usr/bin/python

from __future__ import print_function
from __future__ import absolute_import

__author__    = "Krisztian Loki"
__copyright__ = "Copyright 2017, European Spallation Source, Lund"
__license__   = "GPLv3"


import argparse
import hashlib
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

    print("Processing {definition}...".format(definition = definition))

    if printers == []:
        hashobj = hashlib.sha256()
    else:
        hashobj = None

    with open(definition) as m:
        if_def = tf.processLines(m, FILENAME = definition)


    if if_def is None:
        exit(1)

    if hashobj is not None:
        if_def.calculate_hash(hashobj)
        print("HASH: ", hashobj.hexdigest())

    for printer in printers:
        createTemplate(definition, if_def, printer)

    print()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Parses interface definitons and creates PLCFactory templates", add_help = False)

    available_printers = tf.available_printers()

    parser.add_argument('--printers',
                        '-p',
                        help     = 'template printers',
                        nargs    = '+',
                        choices  = available_printers + [ 'all' ],
                        type     = str
                       )

    parser.add_argument('--show-printers',
                        help     = 'show the available printers',
                        default  = False,
                        action   = 'store_true',
                        dest     = 'show_printers'
                       )

    parser.add_argument('--optimize',
                        help     = "(default) optimize the created interface (won't be compatible with the new PLC mapper)",
                        default  = True,
                        action   = 'store_true',
                        dest     = "optimize",
                       )

    parser.add_argument('--no-optimize',
                        help     = "do NOT optimize the created interface (for legacy PLC mapper)",
                        action   = 'store_false',
                        dest     = "optimize",
                       )

    args = parser.parse_known_args()[0]

    if args.show_printers:
        print(available_printers)
        exit(0)

    parser = argparse.ArgumentParser(parents = [ parser ])
    parser.add_argument('definitions',
                        help     = 'interface definitions',
                        nargs    = '+',
                        type     = str
                       )

    args = parser.parse_args()

    if args.optimize:
        print("""
******************************
*Using datablock optimization*
******************************
""")

    if args.printers is None:
        # Do a syntax check only
        args.printers = []

    if 'all' in args.printers:
        args.printers = available_printers

    tf.optimize_s7db(args.optimize)

    map(lambda t: processDefinitionFile(t, args.printers), args.definitions)
