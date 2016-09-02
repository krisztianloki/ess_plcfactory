#!/usr/bin/python

""" PLC Factory: Entry point """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__credits__    = [ "Gregor Ulm"
                 , "David Brodrick"
                 , "Nick Levchenko"
                 , "Francois Bellorini"
                 , "Ricardo Fernandes"
                 ]
__license__    = "GPLv3"
__maintainer__ = "Gregor Ulm"
__email__      = "gregor.ulm@esss.se"
__status__     = "Production"
__env__        = "Python version 2.7"

# Python libraries
import argparse
import datetime
import os
import sys
import time

# PLC Factory modules
import ccdb
import glob
import plcf
import processTemplate as pt


# global variables
TEMPLATE_DIR = "templates"
OUTPUT_DIR   = "output"


def getArtefact(deviceType, filenames, tag, templateID):
    assert isinstance(deviceType, str )
    assert isinstance(filenames,  list)
    assert isinstance(tag,        str )
    assert isinstance(templateID, str )

    lines = []

    for filename in filenames:
        
        if matchingArtefact(filename, tag, templateID):    
            ccdb.getArtefact(deviceType, filename)

            with open(filename) as f:
                lines = f.readlines()

            break

    return lines


def getTemplateName(deviceType, filenames, templateID):
    assert isinstance(deviceType, str )
    assert isinstance(filenames,  list)
    assert isinstance(templateID, str )

    result = ""

    for filename in filenames:

        if matchingArtefact(filename, "TEMPLATE", templateID):

            result = filename
            # download header and save in template directory
            ccdb.getArtefact(deviceType, filename)
            break

    return result


def matchingArtefact(filename, tag, templateID):
    assert isinstance(filename,   str)
    assert isinstance(tag,        str)
    assert isinstance(templateID, str)

    # attached artefacts may be of different file types, e.g. PDF
    if not filename.endswith('.txt'):
        return False

    # exactly one '.' in filename
    assert filename.count('.') == 1

    filename = filename.split('.')[0] # removing '.txt.
    tmp      = filename.split("_")    # separating fields in filename

    # extract template ID
    name     = tmp[-1]

    return name == templateID and tag in filename


def createFilename(header, device, templateID, deviceType):
    assert isinstance(header,     list)
    assert isinstance(device,     str )
    assert isinstance(templateID, str )
    assert isinstance(deviceType, str )

    tag    = "#FILENAME"
    tagPos = findTag(header, tag)

    # default filename is chosen when no custom filename is specified
    if len(header) == 0 or tagPos == -1:

        outputFile = device + "_" + deviceType + "_template-" + templateID \
                   + "_" + glob.timestamp + ".scl"

        return outputFile

    else:

        filename = header[tagPos]

        # remove tag and strip surrounding whitespace
        filename = filename[len(tag):].strip()
        filename = plcf.keywordsHeader(filename, device, templateID)

        return filename


def findTag(lines, tag):
    assert isinstance(lines, list)
    assert isinstance(tag,   str )

    tagPos = -1

    for i in range(len(lines)):
        if lines[i].startswith(tag):
            tagPos = i
            break

    return tagPos


def processHash(header):
    assert isinstance(header, list)

    tag     = "#HASH"
    hashSum = ccdb.getHash()
    pos     = -1

    for i in range(len(header)):
        if tag in header[i]:
            pos = i
            break

    if pos == -1:
        return header

    line        = header[pos]
    tagPos      = line.find(tag)
    line        = line[:tagPos] + hashSum + line[tagPos + len(tag):]
    header[pos] = line

    return header


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


def processRoot(templateID, device):
    assert isinstance(templateID, str)
    assert isinstance(device,     str)

    # get artifact names of files attached to root device
    (deviceType, rootArtefacts) = ccdb.getArtefactNames(device)

    # find devices this PLC controls
    controls = ccdb.control(device)

    print device + " controls: "

    for elem in controls:
        print "\t- " + elem

    print "\n"

    # change working directory to template directory
    os.chdir(TEMPLATE_DIR)

    header = getArtefact(deviceType, rootArtefacts, "HEADER", templateID)
    

    if len(header) == 0:
        print "No header found.\n"
    else:
        print "Header read.\n"

    footer = getArtefact(deviceType, rootArtefacts, "FOOTER", templateID)

    if len(footer) == 0:
        print "No footer found.\n"
    else:
        print "Footer read.\n"

    print "Processing entire tree of controls-relationships:\n"

    return (deviceType, rootArtefacts, controls, header, footer)


def processTemplateID(templateID, device):
    assert isinstance(templateID, str)
    assert isinstance(device,     str)

    print "#" * 60
    print "Template ID " + templateID
    print "Device at root: " + device + "\n"

    # collect lines to be written at the end
    output = []

    # process header/footer
    (deviceType, rootArtefacts, controls, header, footer) =       \
        processRoot(templateID, device)

    # for each device, find corresponding template and process it
    output     = []

    toProcess  = controls # starting with devices controlled by PLC
    processed  = set()
    outputFile =                                                  \
        createFilename(header, device, templateID, deviceType)    

    headerFileName = ""
    headerFiles = filter(lambda x: "HEADER" in x and templateID in x, rootArtefacts)

    if len(headerFiles) >= 1:
        headerFileName = headerFiles[0]
    
    if not headerFileName == "":
        header = pt.process(device, headerFileName)
    
    
    while toProcess != []:

        elem = toProcess.pop()

        if elem in processed:  # this should be redundant
            continue

        print elem

        # get template
        (deviceType, artefacts) = ccdb.getArtefactNames(elem)
        print "Device type: " + deviceType

        filename = getTemplateName(deviceType, artefacts, templateID)

        if filename != "":
            # process template and add result to output
            output += pt.process(elem, filename)
            output.append("\n\n")
            print "Template processed."

        else:
            print "No template found."

        controls = ccdb.control(elem)

        print "This device controls: "

        if len(controls) > 0:

            for c in controls:
                print "\t- " + c #, c in processed
                if c not in processed:
                    toProcess.append(c)

        else:
            print "N/A"

        print "=" * 40
        processed.add(elem)

    print "\n"

    os.chdir("..")

    # process #HASH keyword in header
    header      = processHash(header)

    output      = header + output + footer
    outputFile  = sanitizeFilename(outputFile)

    if len(output) == 0:
        print "There were no templates for ID = " + templateID + ".\n"
        return

    lines  = output
    output = []

    # Process counters; initialize
    numOfCounters = 9
    counters      = dict()

    for n in range(numOfCounters):
        counters["Counter" + str(n + 1)] = 0


    for line in lines:

        if "[PLCF#" in line and "#COUNTER" not in line:            
            line = plcf.evalCounter(line, counters)

        elif "[PLCF#" in line and '#COUNTER' in line:
            (counters, line) = plcf.evalCounterIncrease(line, counters)

        assert isinstance(line, str)
        assert "[PLCF#" not in line  # PLCF should now all be be processed
        output.append(line)


    #write file
    os.chdir(OUTPUT_DIR)

    with open(outputFile,'w') as f:
        for line in output:
            line = line.rstrip()
            if not line.startswith("#COUNTER") \
               and not line.startswith("#FILENAME"):
                f.write(line + "\n")

    os.chdir("..")

    print "Output file written: " + outputFile + "\n",
    print "Hash sum: " + glob.hashSum


if __name__ == "__main__":

    os.system('clear')

    start_time     = time.time()

    glob.timestamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())

    parser         = argparse.ArgumentParser()

    parser.add_argument(
                        '-d',
                        '--device',
                        help='device / installation slot',
                        required=True
                        )

    parser.add_argument(
                        '-t',
                        '--template',
                        help='template name',
                        nargs = '*',
                        type=str,
                        required=True)
    parser.add_argument(
                        '--test',
                        help='select test database',
                        action='store_true',
                        required=False)
    # this argument is just for show as the corresponding value is
    # set to True by default                        
    parser.add_argument(
                        '--production',
                        help='select production database',
                        action='store_true',
                        required=False)    

    # retrieve parameters
    args       = parser.parse_args()

    # PLC name and template number given as arguments
    device      = args.device
    templateIDs = args.template

    if args.test:
        glob.production = False

    assert len(templateIDs) >= 1, "at least one template ID must be given"


    # remove templates downloaded in a previous run
    os.chdir(TEMPLATE_DIR)

    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    for f in files:
        if "TEMPLATE" in f:
            os.remove(f)

    os.chdir("..")

    map(lambda x: processTemplateID(x, device), templateIDs)

    print("--- %.1f seconds ---\n" % (time.time() - start_time))
