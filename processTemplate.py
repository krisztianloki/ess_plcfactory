import ast
import json
import restful as rs


# replace INSTALLATION_SLOT with provided name
def replaceSlotName(line, plc):
    assert isinstance(line,     str )
    assert isinstance(plc,      str )
    
    start = line.find("$(")
    end   = line.find(")", start)
    assert end != -1

    res   = line[:start] + plc + line[end + 1:]
    return fixLength(res)


def replaceSlotNameAndFixLength(line, plc):
    assert isinstance(line,     str )
    assert isinstance(plc,      str )
    
    
    res   = line[:start] + plc + line[end + 1:]

    return fixLength(res)
    



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
        
    if not start == 30:
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
        tmp = replaceSlotName(line, plc)
        # there is a PLCF tag left to process
        return processLine(tmp, plc, propDict)

    if line.find("$(PLCF#") != -1:
        return replaceTag(line, propDict)
    
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
        elem = ast.literal_eval(elem)

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
    
    res = []
    for elem in lines:        
        tmp = processLine(elem, plc, propDict)
        res.append(tmp)

    # second pass; removes references that were introduced
    # through property lookups
    final = []
    for elem in res:
        tmp = replaceReference(elem, plc)
        final.append(tmp)

    return final
    

# FIXME
def replaceReference(line, plc):
    assert isinstance(line,     str )
    assert isinstance(plc,      str )
    
    res = line
    
    if line.find("$(INSTALLATION_SLOT") != -1:
        tmp = replaceSlotName(line, plc)
        
        start = line.find("$(")
        end   = line.find(")", start)
        assert end != -1

        res   = line[:start] + plc + line[end + 1:]
        
    return res    
        
    

# read entire template file
# TODO: give filename as argument or call function with a list of lines,
#       i.e. process file in plfactory.py istead?
def getAllLines(filename):
    assert isinstance(filename, str)
    
    lines = []
    
    with open(filename) as f:
        lines = f.readlines()
        
    return lines


def process(plc, filename):
    assert isinstance(plc,      str)
    assert isinstance(filename, str)
    
    lines  = getAllLines(filename)
    result = processAll(lines, plc)    
        
    return result

"""
if __name__ == "__main__":
    
    plc      = "LNS-ISrc-01:Vac-TMPC-1" # would be given as an argument
    filename = "LEYBOLD_TURBOPUMP_CONTROLLER_TEMPLATE1.txt"
    lines    = allLines(filename)
    
    x = processAll(lines, plc)    
    
    for elem in x:
        print elem
    
    # write file
    f = open('output.txt','w')
    for elem in x:
        f.write(elem)
    f.close()
"""