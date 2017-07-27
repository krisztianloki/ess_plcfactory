""" PLC Factory: Template Processing """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"

# Python libraries
import ast
import json

# PLC Factory modules
import ccdb
import plcf


def replaceTag(line, propDict):
    assert isinstance(line,     str )
    assert isinstance(propDict, dict)

    start = line.find("$(PLCF")
    tag   = line.find("#", start)
    end   = line.find(")", start)
    assert end != -1               # sanity check

    lookup = line[tag + 1:end]
    name   = propDict.get(lookup)
    
    print lookup, name

    return line[:start] + name + line[end + 1:]


# create a dictionary with all properties;
# input is a list of dictionaries, which are processed one by one
def createPropertyDict(propList):
    assert isinstance(propList, list)

    result = {}

    for elem in propList:
        assert isinstance(elem, str), type(elem)

        # convert string to dictionary
        elem  = ast.literal_eval(elem)

        name  = elem.get("name")
        value = elem.get("value")

        # remove prefix if it exists
        tag   = name.find("#")
        if not tag == -1:
            name = name[tag + 1:]

        # sanity check against duplicate values, which would point to an
        # issue with the entered data
        assert name not in result.keys()

        result[name] = value

    return result


def processAll(lines, device):
    assert isinstance(lines,  list)
    assert isinstance(device, str )

    propList = ccdb.properties(device)

    # create dictionary of properties
    propDict = createPropertyDict(propList)

    # read each line, process them, add one by one to accumulator
    return map(lambda x: plcf.processLine(x, device, propDict), lines)


def getAllLines(filename):
    assert isinstance(filename, str)

    with open(filename) as f:
        lines = f.readlines()

    return lines


def process(device, filename_or_template):
    assert isinstance(device,   str)

    if isinstance(filename_or_template, list):
        lines = filename_or_template
    else:
        lines = getAllLines(filename_or_template)

    return processAll(lines, device)
