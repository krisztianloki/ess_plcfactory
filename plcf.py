"""
plcflang.py

This module processes expressions in 'PLCFLang', the embedded domain-specific
language of PLC Factory. Please see the documentation for further details.

Note that erroneous input in syntactically valid expressions, for instance
using a variable name that is not defined as a device property in CCDB,
will not lead to an error. Instead, such input is simply returned unchanged.

"""

# Python libraries
import datetime


# PLC Factory modules
import ccdb
import glob
import plcf_ext        as ext
import processTemplate as pt


# global vars
current_device = None


def keywordsHeader(filename, device, id):
    assert isinstance(filename, str)
    assert isinstance(device,   str)
    assert isinstance(id,       str)

    timestamp  = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
    deviceType = ccdb.getDeviceType(device)

    # dictionary of the form key: tag, value: replacement
    substDict = {'INSTALLATION_SLOT': device
                ,'TEMPLATE'         : 'template-' + id
                ,'TIMESTAMP'        : timestamp
                ,'DEVICE_TYPE'      : deviceType
                }

    return processLine(filename, device, substDict)


def evalCounter(line, counters):
    assert isinstance(line,     str )
    assert isinstance(counters, dict)

    # substitutions
    for key in counters.keys():
        line = substitute(line, key, str(counters[key]))

    # evaluation
    (_, line) = processLineCounter(line)

    return line


def evalCounterIncrease(line, counters):
    assert isinstance(line,     str )
    assert isinstance(counters, dict)

    # identify start of expression and substitute
    pos = line.find("[PLCF#")

    if pos != -1:

        pre  = line[:pos]
        post = line[pos:]
        
        for key in counters.keys():
            post = substitute(post, key, str(counters[key]))
            
        line = pre + post

    # identify counter
    counterVar = line.split()[2]
    assert 'Counter' in counterVar

    # evaluate
    (counter, line) = processLineCounter(line)
    assert isinstance(counter, int)
    assert isinstance(line,    str)
        
    for key in counters.keys():
        if counterVar == key:
            counters[key] = counter
        
    return (counters, line)


def processLineCounter(line):
    assert isinstance(line,      str )

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

    result = ""

    # evaluation happens after all substitutions have been performed
    try:
        result = eval(expression)

    # catch references to slot names (and erroneous input)
    except (SyntaxError, NameError) as e:
        result = expression

    return (result, line[:start] + str(result) + line[end + 1:])


# extracts a PLFCLang expression from a line in a template,
# evaluates the expression, and returns a new line with
# the result of the evaluation
def processLine(line, device, substDict):
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

    # maintain PLCF tag if a counter variable is part of the expression
    if 'Counter1' in reduced or 'Counter2' in reduced:
        return line[:start] + "[PLCF#" + reduced + line[end:]

    result     = line[:start] + reduced + line[end + 1:]

    # recurse until all PLCF_Lang expressions have been processed
    return processLine(result, device, substDict)


def evalUp(line):
    assert isinstance(line, str)

    while line.find("^(") != -1:

        # extract property
        start = line.find("^(")
        end   = line.find(")", start)
        prop  = line[start + 2:end]

        # backtrack
        val  = ccdb.backtrack(prop, current_device)
        line = line[:start] + val + line[end+1:]

    return line


# replaces all variables in a PLCFLang expression with values
# from CCDB and returns the evaluated expression
def evaluateExpression(line, device, propDict):
    assert isinstance(line,     str )
    assert isinstance(device,   str )
    assert isinstance(propDict, dict)

    global current_device

    # resolve all references to properties in devices on an upper level in the hierarchy
    line = evalUp(line)

    for elem in propDict.keys():
        if elem in line:
            value = propDict.get(elem)
            tmp   = substitute(line, elem, value)
            # recursion to take care of multiple occurrences of variables
            return evaluateExpression(tmp, device, propDict)

    # note that an expression like "INSTALLATION_SLOT + 1" is of course not syntactically correct
    tag = 'INSTALLATION_SLOT'
    if tag in line:
        line = substitute(line, tag, device)

    current_device = device

    # evaluation happens after all substitutions have been performed
    try:
        result = eval(line)

   # catch references to slot names (and erroneous input)
    except (SyntaxError, NameError) as e:
        result = line

    return str(result)


# substitutes a variable in an expression with the proviced value
def substitute(expr, variable, value):
    assert isinstance(expr,     str)
    assert isinstance(variable, str)
    assert isinstance(value,    str)

    if variable not in expr:
        return expr

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

