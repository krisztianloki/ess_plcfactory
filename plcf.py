""" PLC Factory: PLCF# Language """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"


"""
This module processes expressions in 'PLCFLang', the embedded domain-specific
language of PLC Factory. Please see the documentation for further details.

Note that erroneous input in syntactically valid expressions, for instance
using a variable name that is not defined as a device property in CCDB,
will not lead to an error. Instead, such input is simply returned unchanged.
"""


# Python libraries

# PLC Factory modules
import plcf_glob       as glob
import plcf_ext        as ext



def keywordsHeader(line, device, id):
    assert isinstance(line,     str)
    assert isinstance(device,   str)
    assert isinstance(id,       str)

    deviceType = glob.ccdb.getDeviceType(device)
    desc = glob.ccdb.getDescription(device)

    # dictionary of the form key: tag, value: replacement
    substDict = {'INSTALLATION_SLOT': device
                ,'INSTALLATION_SLOT_DESC': desc
                ,'TEMPLATE'         : 'template-' + id
                ,'TIMESTAMP'        : glob.timestamp
                ,'DEVICE_TYPE'      : deviceType
                }

    return processLine(line, device, substDict)


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
    counterVar = line.split()[1]
    assert counterVar in counters.keys()

    # evaluate
    (counter, line) = processLineCounter(line)
    assert isinstance(counter, int), counter
    assert isinstance(line,    str)

    for key in counters.keys():
        if counterVar == key:
            counters[key] = counter

    return (counters, line)


def getPLCFExpression(line):
    assert isinstance(line, str)

    tag    = "[PLCF#"
    start  = line.find(tag)
    offset = len(tag)

    if start == -1:
        return (None, None, None) # nothing to replace

    end        = findMatchingSquareParenthesis(line[start:]) + start
    # assert matching square brackets
    assert end != -1, "Unclosed PLCF# expression in line {line}".format(line = line)

    expression = line[start + offset : end]
    assert matchingParentheses(expression)

    return (start, expression, end)


def processLineCounter(line):
    assert isinstance(line, str)

    (start, expression, end) = getPLCFExpression(line)

    if expression is None:
        return line

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

    (start, expression, end) = getPLCFExpression(line)

    if expression is None:
        return line

    reduced = evaluateExpression(expression, device, substDict)

    # maintain PLCF tag if a counter variable is part of the expression
    if 'Counter' in reduced:
        return line[:start] + "[PLCF#" + reduced + line[end:]

    result = line[:start] + reduced + line[end + 1:]

    # recurse until all PLCF_Lang expressions have been processed
    return processLine(result, device, substDict)


def evalUp(line, device):
    assert isinstance(line, str)

    while line.find("^(") != -1:

        # extract property
        start = line.find("^(")
        end   = line.find(")", start)
        prop  = line[start + 2:end]

        # backtrack
        val  = glob.ccdb.backtrack(prop, device)
        line = line[:start] + val + line[end+1:]

    return line


# replaces all variables in a PLCFLang expression with values
# from CCDB and returns the evaluated expression
def evaluateExpression(line, device, propDict):
    assert isinstance(line,     str )
    assert isinstance(device,   str )
    assert isinstance(propDict, dict)

    # resolve all references to properties in devices on a higher level
    # in the hierarchy
    line = evalUp(line, device)

    keys = propDict.keys()
    keys.sort(key = lambda s: len(s), reverse=True)
    """
    Sorting property names from longest to shortest avoids
    the potential issue that a PLCF# expression can't be fully
    evaluated when a property name is part of another property name of
    the same device.

    In more technical terms: the list of propery names that are
    retrieved via the method keys() is neither sorted nor deterministic,
    i.e. multiple calls may result in different permutations of the
    same elements.

    In PLC Factory, property names are processed one by one, as they
    are encountered (see the for-loop below). Further, there is no
    semantic analysis of PLCF# expressions. Thus, without
    sorting, it may happen that a property name "foo" is processed before
    a property name "foobar", but processing the former would leave "bar"
    in the resulting expression. This would be bad enough, but imagine
    what would happen if there was a property name "bar" left to process!

    With sorting by property names by length in reverse, i.e. from longest
    to shortest, "foobar" is processed before "foo", so the issue described
    above is entirely avoided. For the curious, this approach is similar
    to the "maximal munch" concept in compiler theory.
    """

    for elem in keys:
        if elem in line:
            value = propDict.get(elem)
            tmp   = substitute(line, elem, value)
            # recursion to take care of multiple occurrences of variables
            return evaluateExpression(tmp, device, propDict)

    desc = glob.ccdb.getDescription(device)
    tag = 'INSTALLATION_SLOT_DESC'
    if tag in line:
        line = substitute(line, tag, desc)

    tag = 'INSTALLATION_SLOT'
    if tag in line:
        line = substitute(line, tag, device)

    deviceType = glob.ccdb.getDeviceType(device)
    tag = 'DEVICE_TYPE'
    if tag in line:
        line = substitute(line, tag, deviceType)

    # evaluation happens after all substitutions have been performed
    try:
        wasquoted=False
        #Do not evaluate expressions which consist soley of a quoted string
        if line.startswith('"') and line.endswith('"') and line.count('"')==2:
          wasquoted=True
        #Evaluate this expression
        result = eval(line)
        if wasquoted:
          result='"'+result+'"'
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


#Returns the index of the ] which matches the first [
def findMatchingSquareParenthesis(line):
  istart = []  # stack of indices of opening parentheses
  d = []
  for i, c in enumerate(line):
    if c == '[':
         istart.append(i)
    if c == ']':
        try:
            ci = istart.pop()
            if not istart:   # check if this closed the first opening parenthesis
                return i
            d.append([ci, i])
        except IndexError:
            print 'Too many closing parentheses'
            return -1
  if istart:  # check if stack is empty afterwards
    print 'Too many opening parentheses'
    return -1
  d.sort()
  return d[0][1]

