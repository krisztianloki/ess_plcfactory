"""
plcflang.py

This module processes expressions in 'PLCFLang', the embedded domain-specific
language of PLC Factory. Please see the documentation for further details.

Note that erroneous input in syntactically valid expressions, for instance
using a variable name that is not defined as a device property in CCDB,
will not lead to an error. Instead, such input is simply returned unchanged.

"""

# PLC Factory modules
import restful             as rs
import processTemplate     as pt
import plcflang_extensions as ext


# replaces all variables in a PLCFLang expression with values
# from CCDB and returns the evaluated expression
def evaluateExpression(line, device, propDict):
    assert isinstance(line,     str )
    assert isinstance(device,   str )
    assert isinstance(propDict, dict)
    
    # substitute
    for elem in propDict.keys():
        if elem in line:
            value = propDict.get(elem)
            tmp   = substitute(line, elem, value)
            # recursion to take care of multiple occurrences of variables
            return evaluateExpression(tmp, device, propDict)
        
    # evaluation happens after all substitutions have been performed
    try:
        result = eval(line)

   # catch references to slot names (and erroneous input)
    except SyntaxError as e:
        result = line

    except NameError as e:
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
    
    # check for matching parentheses
    assert matchingParentheses(expression)
    
    reduced    = evaluateExpression(expression, device, propDict)

    result     = line[:start] + reduced + line[end + 1:]

    return result