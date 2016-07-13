#!/usr/bin/python
"""
PLC Factory
(c) European Spallation Source, Lund

Authors:
- Gregor Ulm: 2016-07-04 to 2016-09-02
- ...

See plcfactory.txt for further documentation.
"""

# Python libraries
import datetime
import os
import sys

# PLC Factory modules
import restful         as rs
import processTemplate as pt

"""
TODO
- second argument to script: location of template files (still needed?)
- layout standards for output files

"""

# global variables
TEMPLATE_DIR = "templates"



#FIXME: this is all hardcoded for now
def getHeader(plc):
    assert isinstance(plc, str)

    filename = "PLC_DEVICE_TEMPLATE1_HEADER.txt"
    lines = []
    
    with open(filename) as f:
        lines = f.readlines()
        
    return lines
    
#FIXME 
def getFooter(plc):
    assert isinstance(plc, str)
    
    filename = "PLC_DEVICE_TEMPLATE1_FOOTER.txt"
    lines = []
    
    with open(filename) as f:
        lines = f.readlines()
        
    return lines
    

# ensures that filenames are legal in Windows
# (OSX automatically replaces illegal characters)
def sanitizeFilename(filename):
    result = ""
    
    for char in filename:
        if char in '<>:"/\|?*':
            result += '_'
        else:
            result += char
            
    return result
     

if __name__ == "__main__":

    os.system('clear')

    output = []

    # global variables
    numArgs = 2    # note: file name counts as 1 argument

    # argument is a PLC at the root

    # reading arguments
    # typical invocation: 'python plcfactory foo'
    
    args = sys.argv
    assert len(args) == numArgs, "Illegal number of arguments."

    # get device, e.g. LNS-ISrc-01:Vac-TMPC-1
    # https://ics-services.esss.lu.se/ccdb-test/rest/slot/LNS-ISrc-01:Vac-TMPC-1
    # python plcfactory.py LNS-ISrc-01:Vac-IPC-1
    
    # PLC name given as arguments
    plc      = args[1]
    
    # find devices this PLC controls
    controls = rs.controlCCDB(plc)

    print "PLC: " + plc + "\n"
    print "This device controls: "
    for elem in controls:
        print "\t- " + elem
    print "\n"
    
    # change working directory to template directory
    os.chdir(TEMPLATE_DIR)
    
    output += getHeader(plc)
    print "Header processed.\n"
        
    # TODO: get name from RESTful interface, download file, maybe send list of lines to pt
    # Ricardo will work on that
    # thus: code below hard-coded and tailored to given example because the required REST interface has not yet
    # been implemented
    
    # for each device, find corresponding template and process it
    
    print "Processed templates:"
    
    for elem in controls:
        # get template
        
        # process template
        
        # hardcoded placeholders
        if elem == 'LNS-ISrc-01:Vac-TMPC-1':
            filename = "LEYBOLD_TURBOPUMP_CONTROLLER_TEMPLATE1.txt"
            
        if elem == 'LNS-ISrc-01:Vac-PGV-1':
            #filename = "VALVE_TEMPLATE1.txt"
            #filename = "VALVE_TEMPLATE2.txt"
            #filename = "VALVE_TEMPLATE3.txt"
            
            filename = "VACUUM_VALVE_TEMPLATE02a.txt"
            
        # add result to output
        output += pt.process(elem, filename)
        
        print "\t- " + elem
      
    print "\n"
    
    output += getFooter(plc)
    print "Footer processed.\n"    
    os.chdir("..")
    
    timestamp  = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
    outputFile = plc + "_" + timestamp + ".scl"
    outputFile = sanitizeFilename(outputFile)

    os.chdir("output")
    # write entire output
    f = open(outputFile,'w')
    for elem in output:
        f.write(elem)
    f.close()
    os.chdir("..")

    print "Output file written: " + outputFile + "\n"