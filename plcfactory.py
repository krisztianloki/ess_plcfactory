#!/usr/bin/python
"""
PLC Factory
(c) European Spallation Source, Lund

Authors:
- Gregor Ulm: 2016-07-04 to 2016-09-02
- ...

See plcfactory.txt for further documentation.
"""

# python plcfactory.py --device LNS-LEBT-010:Vac-VPGCF-001 --template 2
# python plcfactory.py --device LNS-LEBT-010:Vac-PLC-11111 --template 2


# Python libraries
import argparse
import datetime
import os
import sys


# PLC Factory modules
import restful         as rs
import processTemplate as pt


# #FILENAME INSTALLATION_SLOT-TEMPLATE-TIMESTAMP.scl


# no: $[PLCF#$(INSTALLATION_SLOT)]" ; $(INSTALLATION_SLOT)
# [PLCF#INSTALLATION_SLOT]

# #FILENAME [PLCF#INSTALLATION_SLOT]-[PLCF#TEMPLATE]-[PLCF#TIMESTAMP].scl

# global variables
TEMPLATE_DIR = "templates"
OUTPUT_DIR   = "output"


def getArtefact(deviceType, filenames, tag, n):
    assert isinstance(deviceType, str )
    assert isinstance(filenames,  list)
    assert isinstance(tag,        str )
    assert isinstance(n,          int )

    lines = []

    for filename in filenames:

        if matchingArtefact(filename, tag, n):

            rs.getArtefact(deviceType, filename)

            with open(filename) as f:
                lines = f.readlines()

            break

    return lines


def getTemplateName(deviceType, filenames, n):
    assert isinstance(deviceType, str )
    assert isinstance(filenames,  list)
    assert isinstance(n,          int )

    result = ""

    for filename in filenames:

        if matchingArtefact(filename, "TEMPLATE", n):
            result = filename
            # download header and save in template directory
            rs.getArtefact(deviceType, filename)
            break

    return result


def matchingArtefact(filename, tag, n):
    assert isinstance(filename, str)
    assert isinstance(tag,      str)
    assert isinstance(n,        int)

    # attached artefacts may be of different file types, e.g. PDF
    if not filename.endswith('.txt'):
        return False

    # sample filename: VALVE_TEMPLATE_1.txt

    # TODO: assert: exactly one '.' in filename

    filename    = filename.split('.')[0] # removing '.txt.
    tmp         = filename.split("_")    # separating fields in filename


    if tmp[-1].startswith("TEMPLATE"):
        template_nr = int(tmp[-1][len("TEMPLATE"):])
    else:
        template_nr = int(tmp[-1])

    return template_nr == n and tag in filename


def createFilename(header, device, n, deviceType):
    assert isinstance(header,     list)
    assert isinstance(device,     str )
    assert isinstance(n,          int )
    assert isinstance(deviceType, str )

    tag        = "#FILENAME"
    timestamp  = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())

    # #FILENAME INSTALLATION_SLOT-TEMPLATE-TIMESTAMP.scl

    # python plcfactory.py --device LNS-LEBT-010:Vac-PLC-11111 --template 1


    if len(header) == 0 or not header[0].startswith(tag):

        outputFile = plc + "_" + "template_" + str(n) + "_" + timestamp + ".scl"
        return (outputFile, header)

    else:

        assert header[0].startswith(tag)

        filename  = header[0]

        # remove tag and strip surrounding whitespace
        filename = filename[len(tag):].strip()

        if 'INSTALLATION_SLOT' in filename:
            filename = replaceTag(
                filename, 'INSTALLATION_SLOT', device)

        if 'TEMPLATE' in filename:
            filename = replaceTag(
                filename, 'TEMPLATE', 'template' + str(n))

        if 'TIMESTAMP' in filename:
            filename = replaceTag(
                filename, 'TIMESTAMP', timestamp)

        # FIXME: this is untested; no input provided yet
        if 'DEVICE_TYPE' in filename:            
            filename = replaceTag(
                filename, 'DEVICE_TYPE', deviceType)

        # ensure that there are no duplicate tags
        assert 'INSTALLATION_SLOT' not in filename
        assert 'TEMPLATE'          not in filename
        assert 'TIMESTAMP'         not in filename

        # remove second line in header template if it is empty
        if header[1].strip() == "":
            return (filename, header[2:])

        else:
            return (filename, header[1:])


def replaceTag(line, tag, insert):
    assert isinstance(line,   str)
    assert isinstance(tag,    str)
    assert isinstance(insert, str)

    start = line.find(tag)
    assert start != -1

    end   = start + len(tag)

    return line[:start] + insert + line[end:]


# ensures that filenames are legal in Windows
# (OSX automatically replaces illegal characters)
def sanitizeFilename(filename):
    assert isinstance(filename, str)

    result = map(lambda x: '_' if x in '<>:"/\|?*' else x, filename)
    return "".join(result)


if __name__ == "__main__":

    os.system('clear')

    # invocation:
    # python plcfactory.py --device LNS-LEBT-010:Vac-VPGCF-001 --template 2
    # i.e. device / installations slot, and template number

    parser = argparse.ArgumentParser()

    parser.add_argument(
                        '-d',
                        '--device',
                        help='device / installation slot',
                        required=True
                        )

    parser.add_argument(
                        '-t',
                        '--template',
                        help='template number',
                        type=int,
                        required=True)

    # retrieve parameters
    args = parser.parse_args()

    # PLC name and template number given as arguments
    plc  = args.device
    n    = args.template

    # collect lines to be written at the end
    output  = []

    # get artifact names of files attached to plc
    (deviceType, plcArtefacts) = rs.getArtefactNames(plc)

    # find devices this PLC controls
    controls = rs.controlCCDB(plc)

    print "PLC: " + plc + "\n"
    print "This device controls: "

    for elem in controls:
        print "\t- " + elem

    print "\n"

    # change working directory to template directory
    os.chdir(TEMPLATE_DIR)

    header = getArtefact(deviceType, plcArtefacts, "HEADER", n)
    print "Header read.\n"

    footer = getArtefact(deviceType, plcArtefacts, "FOOTER", n)
    print "Footer read.\n"

    print "Processed templates:"
    # for each device, find corresponding template and process it

    output = []

    for elem in controls:

        # get template
        (deviceType, artefacts) = rs.getArtefactNames(elem)

        # only need to download the file
        filename = getTemplateName(deviceType, artefacts, n)

        if filename != "":
            # process template and add result to output
            output += pt.process(elem, filename)
            print "\t- " + elem

        else:
            print "\t- " + elem + ": no template found"

    print "\n"

    os.chdir("..")

    (outputFile, header) = createFilename(header, plc, n, deviceType)
    output               = header + output + footer
    outputFile           = sanitizeFilename(outputFile)

    if len(output) > 0:

        os.chdir(OUTPUT_DIR)

        # write entire output
        with open(outputFile,'w') as f:
            map(lambda x: f.write(x), output)

        os.chdir("..")

        print "Output file written: " + outputFile + "\n"

    else:

        #os.system('clear')
        print "There were no available templates for N = " + str(n) + ".\n"