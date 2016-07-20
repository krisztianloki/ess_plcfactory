"""
processTemplate.py


"""

# Python libraries
import ast
import json

# PLC Factory modules
import restful as rs
import plcflang as plang


def fixLength(line):
    assert isinstance(line, str)
    """
    The alignment of the variable assignmens in the generated output
    depends on the length of the device name that replaces the tag
    $(INSTALLATION_SLOT). If it is not exactly 22 characters long,
    then the first line will be misaligned

    TODO: right now, assume a max. length of 22 characters; shift assignment
          if needed; if device name > 22, then all assignents would need to be shifted.

    	"$(INSTALLATION_SLOT)"(    EPICStoPLC_DB:="$(PLCF#PropertyString01)",
    	                             EPICStoPLC_Offset:=$(PLCF#PropertyInteger01),


    In the example above, the first assignment statement needs to be shifted
    to the right so that it begins at position 30.
    """

    start = line.find("EPICStoPLC_DB")  # TODO: is this always the first assignment?
    assert start <= 30

    if not (start == 30 or start == -1):
        shift = " " * (30 - start) # creates white space
        return line[:start] + shift + line[start:]

    return line


def replaceTag(line, propDict):
        
    assert isinstance(line,     str )
    assert isinstance(propDict, dict)

    start = line.find("$(PLCF")
    tag   = line.find("#", start)
    end   = line.find(")", start)
    assert end != -1               # sanity check

    lookup = line[tag + 1:end]
    name   = propDict.get(lookup)

    return line[:start] + name + line[end + 1:]


def processLine(line, plc, propDict):
    assert isinstance(line,     str )
    assert isinstance(plc,      str )
    assert isinstance(propDict, dict)

    if line.find("$(INSTALLATION_SLOT") != -1:
        # replace INSTALLATION_SLOT with provided name
        tmp = replaceReference(line, plc)
        tmp = fixLength(tmp)
        # there is a PLCF tag left to process
        return processLine(tmp, plc, propDict)

    if line.find("$(PLCF#") != -1:
        tmp = replaceTag(line, propDict)
        print tmp
        return tmp
#        return replaceTag(line, propDict)

    # template may contain files that don't require any substitutions
    return line
    


# create a dictionary with all properties;
# input is a list of dictionaries, which is processed one by one
def createPropertyDict(propList):
    assert isinstance(propList, list)

    result = {}

    for elem in propList:
        assert isinstance(elem, str)

        # convert string to dictionary
        elem  = ast.literal_eval(elem)

        # input converted from utf-8 to ascii
        name  = str(elem.get("name"))
        value = str(elem.get("value"))

        # remove prefix if it exists
        tag   = name.find("#")
        if not tag == -1:
            name = name[tag + 1:]

        # sanity check against duplicate values, which would point to an
        # issue with the entered data
        assert name not in result.keys()

        result[name] = value

    return result


def processAll(lines, plc):
    assert isinstance(lines, list)
    assert isinstance(plc,   str )

    # read each line, process them, add one by one to accumulator
    propList = rs.propertiesCCDB(plc)

    # create dictionary of properties
    propDict = createPropertyDict(propList)

    # first pass
    result  = map(lambda x: plang.processLine(x, plc, propDict), lines)

    # second pass; removes references that were introduced
    # through property lookups
    result  = map(lambda x: fixLength(replaceReference(x, plc)), result)
    

    return result



# FIXME: INSTALLATION_SLOT

# "LNS-LEBT-010:Vac-VVA-00041"("Open Status DI Address (PLC Tag)":="$[PLCF#$(INSTALLATION_SLOT)]:Open.DI",



# replaces "$(INSTALLATION_SLOT" with device name
def replaceReference(line, plc):
    assert isinstance(line, str)
    assert isinstance(plc,  str)

    res = line

    if line.find("$(INSTALLATION_SLOT") != -1:

        start = line.find("$(")
        end   = line.find(")", start)
        assert end != -1

        res   = line[:start] + plc + line[end + 1:]

    return res


def getAllLines(filename):
    assert isinstance(filename, str)

    with open(filename) as f:
        lines = f.readlines()

    return lines


def process(device, filename):
    assert isinstance(device,      str)
    assert isinstance(filename, str)

    lines  = getAllLines(filename)
    result = processAll(lines, device)
    return result