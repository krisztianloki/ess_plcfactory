#!/usr/bin/python

__author__    = "Krisztian Loki"
__copyright__ = "Copyright 2017, European Spallation Source, Lund"
__license__   = "GPLv3"


import argparse
import tf as tf


def processLine(if_def, line, num):
    tf.assert_IF_DEF(if_def)
    assert isinstance(line, str)
    assert isinstance(num,  int)

    errormsg = "{error} at line {num}: {line}"

    try:
        if_def.add(line)
    except SyntaxError:
        print errormsg.format(error = "Syntax error", num = num, line = line.strip())
        exit(1)
    except AssertionError,e :
        print errormsg.format(error = "Internal error", num = num, line = line.strip())
        if e.args:
            print e.args[0]
        exit(1)
    except Exception, e:
        print errormsg.format(error = "Exception", num = num, line = line)
        if e.args:
            print e.args[0]
        exit(1)


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



def processDefinition(definition, printers):
    assert isinstance(definition, str)
    assert isinstance(printers,   list)

    print "Processing " + definition + "..."

    if_def = tf.new()

    multiline  = None
    multilinei = 1
    with open(definition) as m:
        i = 1
        for line in m:
            #
            # Check for multiline strings making sure that it actually spans multiple lines
            #
            if line.count('"""') % 2:
                if multiline is None:
                    multiline  = line
                    multilinei = i
                else:
                    multiline += line
                    processLine(if_def, multiline, multilinei)
                    multiline = None
            elif multiline:
                multiline += line
            else:
                processLine(if_def, line, i)
            i += 1


    if multiline:
        multiline_error = "Unclosed multiline string at {num}: {line}"
        print multiline_error.format(num = multilinei, line = multiline)
        exit(1)

    if_def.end()

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

    map(lambda t: processDefinition(t, args.printers), args.definitions)
