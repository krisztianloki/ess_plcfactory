"""
plcflang.py

This module processes expressions in 'PLCFLang', the embedded domain-specific
language of PLC Factory. Please see the documentation for further details.

Note that erroneous input in syntactically valid expressions, for instance
using a variable name that is not defined as a device property in CCDB,
will not lead to an error. Instead, such input is simply returned unchanged.

"""

import datetime


# PLC Factory modules
import restful             as rs
import processTemplate     as pt
import plcflang_extensions as ext

## FIXME add keywords



def go(device, n, deviceType):
    
    
    # read each line, process them, add one by one to accumulator
    propList = rs.propertiesCCDB(device)

    # create dictionary of properties
    propDict = createPropertyDict(propList)
    
    

# has: device, n, deviceType



def keywordsHeader(filename, device, n):
    assert isinstance(filename, str)
    assert isinstance(device,   str)
    assert isinstance(n,        int)

    timestamp  = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
    deviceType = rs.getDeviceType(device)
    
    # dictionary of the form key: tag, value: replacement
    substDict = {'INSTALLATION_SLOT': device
                ,'TEMPLATE'         : 'template-' + str(n)
                ,'TIMESTAMP'        : timestamp
                ,'DEVICE_TYPE'      : deviceType
                }
    
    # FIXME naming
    return xxProcessLine(filename, device, substDict)
    

def xxProcessLine(line, device, substDict):
    assert isinstance(line,      str )
    assert isinstance(device,    str )
    assert isinstance(substDict, dict)
    
    tag    = "[PLCF#"
    start  = line.find(tag)
    offset = len(tag)
      
    if start == -1:
        return line # nothing to replace

    end        = line.find("]", start)
    # assert matching square brackets
    assert end != -1
    
    
    expression = line[start + offset : end]
    
    assert matchingParentheses(expression)
    
    # TODO not needed for header; later on add for generalization
    reduced    = evaluateExpression(expression, device, substDict)
    
    result     = line[:start] + reduced + line[end + 1:]

    # recurse until all occurrences of PLCF_Lang expressions have been replaced
    return xxProcessLine(result, device, substDict)
    
    





########
"""
def processOne(line, plc):
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
"""



# global var
current_device = None


def evalUp(line):
    
    while line.find("^(") != -1:
                
        # extract property
        start = line.find("^(")
        end   = line.find(")", start)
        prop  = line[start + 2:end]
            
        # backtrack        
        val  = rs.backtrack(prop, current_device)
        line = line[:start] + val + line[end+1:]

    return line


# replaces all variables in a PLCFLang expression with values
# from CCDB and returns the evaluated expression
def evaluateExpression(line, device, propDict):
    assert isinstance(line,     str )
    assert isinstance(device,   str )
    assert isinstance(propDict, dict)
        
    global current_device
        
    # substitute
    # TODO
    
    # evalUp()
    
    # resolve all references to properties in devices on an upper level in the hierarchy
    line = evalUp(line)
    
    for elem in propDict.keys():
        if elem in line:
            value = propDict.get(elem)
            tmp   = substitute(line, elem, value)
            # recursion to take care of multiple occurrences of variables
            return evaluateExpression(tmp, device, propDict)
    
    # TODO
    # get keyword dict, perform replacements
    # at the end, replace keywords with values
    
    # note that an expression like "INSTALLATION_SLOT + 1" is of course not syntactically correct
    x = 'INSTALLATION_SLOT' 
    if x in line:
        line = substitute(line, x, device)
    
    
    current_device = device
    
    # evaluation happens after all substitutions have been performed
    try:
        result = eval(line)

   # catch references to slot names (and erroneous input)  # FIXME
    except (SyntaxError, NameError) as e:
        result = line
            
    return str(result)
    

# substitutes a variable in an expression with the proviced value
def substitute(expr, variable, value):
    assert isinstance(expr,     str)
    assert isinstance(variable, str)
    assert isinstance(value,    str)
    
    start = expr.find(variable)
    end   = start + len(variable)
    
    return expr[:start] + value + expr[end:]
        

# checks for basic validity of expression by determining whether
# open and closed parentheses match
def matchingParentheses(line):
    assert isinstance(line, str)
    
    def helper(line, acc):
        
        if acc < 0:
            return False
        
        if line == "":
            return acc == 0
            
        else:
            
            if line[0] == '(':
                return helper(line[1:], acc + 1)
                
            elif line[0] == ')':
                return helper(line[1:], acc - 1)
                
            else:
                return helper(line[1:], acc)
    
    return helper(line, 0)


# extracts a PLFCLang expression from a line in a template,
# evaluates the expression, and returns a new line with
# the result of the evaluation
def processLine(line, device, propDict):
    return xxProcessLine(line, device, propDict)
    """
    assert isinstance(line,     str )
    assert isinstance(device,   str )
    assert isinstance(propDict, dict)
    
    tag    = "$[PLCF#"
    start  = line.find(tag)
    offset = len(tag)
    
    if start == -1:
        return line # nothing to replace

    end        = line.find("]", start)
    # assert matching square brackets
    assert end != -1
    
    expression = line[start + offset : end]
    assert matchingParentheses(expression)
    
    reduced    = evaluateExpression(expression, device, propDict)
    result     = line[:start] + reduced + line[end + 1:]

    return result
    """