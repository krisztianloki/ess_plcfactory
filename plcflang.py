"""


"""



# PLC Factory modules
import restful             as rs
import processTemplate     as pt
import plcflang_extensions as ext




# processOne
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
        
    try:
            result = eval(line)
    except SyntaxError as e:     # catches references to slot names (and erroneous input)
            result = line
    except NameError as e:
            result = line
            
    return str(result)
    
    
def substitute(expr, variable, value):
    assert isinstance(expr,     str)
    assert isinstance(variable, str)
    assert isinstance(value,    str)
    
    start = expr.find(variable)
    end   = start + len(variable)
    
    return expr[:start] + value + expr[end:]
        

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
    assert end != -1
    
    expression = line[start + offset : end]
    
    # check for matching parentheses
    assert matchingParentheses(expression)
    
    reduced    = evaluateExpression(expression, device, propDict)

    result     = line[:start] + reduced + line[end + 1:]

    return result