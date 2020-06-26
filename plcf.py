from __future__ import print_function
from __future__ import absolute_import

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
import plcf_ext



class PLCFException(Exception):
    pass


class PLCFEvalException(PLCFException):
    def __init__(self, expression, exception, *args):
        super(PLCFEvalException, self).__init__(*args)
        self.expression = expression
        self.exception  = exception


    def __str__(self):
        return "The following exception occured during the evaluation of '{expr}': {exc}: {msg}".format(expr = self.expression,
                                                                                                        exc  = type(self.exception).__name__,
                                                                                                        msg  = str(self.exception))



class PLCF(object):
    plcf_tag     = "[PLCF#"
    plcf_tag_len = len(plcf_tag)
    plcf_up      = "^("
    plcf_up_len  = len(plcf_up)

    @staticmethod
    def __specialProperties(device):
        sp = { 'TIMESTAMP'              : glob.timestamp,
               'ROOT_INSTALLATION_SLOT' : glob.root_installation_slot
             }

        if device is not None:
            sp.update({ 'INSTALLATION_SLOT'      : device.name(),
                        'INSTALLATION_SLOT_DESC' : device.description(),
                        'DEVICE_TYPE'            : device.deviceType(),
                      })

        return sp


    def __init__(self, device):
        self._device  = device
        self._evalenv = { "ext": plcf_ext }

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

        if device is not None:
            # Need to use dict() to create a new instance
            #  as it will be modified locally
            self._properties = dict(device.propertiesDict())
        else:
            self._properties = dict()
        self._keys = self._properties.keys()

        sp   = self.__specialProperties(device)
        # Pre-register a TEMPLATE property without an actual value
        keys = sp.keys()
        keys.append('TEMPLATE')

        if set(keys) <= set(self._keys):
            raise PLCFException("Redefinition of the following reserved properties is not allowed: {}".format(set(self._keys).intersection(set(keys))))

        self._keys.extend(keys)
        self._keys.sort(key = lambda s: len(s), reverse = True)

        self._properties.update(sp)


    def register_template(self, templateId):
        self._properties['TEMPLATE'] = 'template-' + templateId


    def process(self, line_or_lines):
        if isinstance(line_or_lines, str):
            return self.processLine(line_or_lines)

        # read each line, process them, add one by one to accumulator
        return map(lambda x: self.processLine(x), line_or_lines)


    # extracts a PLFCLang expression from a line in a template,
    # evaluates the expression, and returns a new line with
    # the result of the evaluation
    def processLine(self, line):
        assert isinstance(line, str)

        result = ""
        while True:
            # recurse until all PLCF_Lang expressions have been processed
            (start, expression, end) = self.getPLCFExpression(line)

            if expression is None:
                return result + line

            reduced = self._evaluateExpression(expression)

            # maintain PLCF tag if a counter variable is part of the expression
            if 'Counter' in reduced:
                result += line[:start] + self.plcf_tag + reduced + "]"
            else:
                result += line[:start] + reduced

            line = line[end + 1:]


    def _evalUp(self, expression):
        assert isinstance(expression, str)

        while True:
            # extract property
            start = expression.find(self.plcf_up)
            if start == -1:
                break

            # FIXME: which one makes more sense?
            end   = expression.find(")", start)
#            end   = PLCF.findMatchingParenthesis(expression[start:], '()') + start
            prop  = expression[start + self.plcf_up_len:end]

            # backtrack
            val  = self._device.backtrack(prop)
            expression = expression[:start] + val + expression[end + 1:]

        return expression


    def _check_infinite_recursion(self, expression, barrier):
        expression = self._evalUp(expression)
        for elem in self._keys:
            # Found infinite recursion
            if elem == barrier:
                return True

            # Caught a longer match, no infinite recursion
            if elem in expression:
                break

        return False


    # replaces all variables in a PLCFLang expression with values
    # from CCDB and returns the evaluated expression
    def _evaluateExpression(self, expression):
        assert isinstance(expression, str)

        # resolve all references to properties in devices on a higher level
        # in the hierarchy
        expression = self._evalUp(expression)

        for elem in self._keys:
            if elem in expression:
                value                = self._properties.get(elem)
                (tmp, pos_after_val) = self.substitute(expression, elem, value)
                # If the substitution string ('value') contains the key ('elem') then check if the result contains other keys than 'elem'
                # In other words: try to avoid an infinite recursion
                if elem in value and self._check_infinite_recursion(tmp, elem):
                    tmp = tmp[:pos_after_val] + self._evaluateExpression(tmp[pos_after_val:])
                    expression = self._evalUp(tmp)
                    break
                # recursion to take care of multiple occurrences of variables
                return self._evaluateExpression(tmp)

        # evaluation happens after all substitutions have been performed
        wasquoted = False
        #Do not evaluate expressions which consist solely of a quoted string
        if (expression.startswith('"') and expression.endswith('"') and expression.count('"') == 2) or \
           (expression.startswith("'") and expression.endswith("'") and expression.count("'") == 2):
            wasquoted = expression[0]

        if "ext." in expression: #expression.startswith("ext."):
            try:
                #Evaluate ext module call
                result = eval(expression, self._evalenv)
            except plcf_ext.PLCFExtException as e:
                raise e #from None
            except Exception as e:
                raise PLCFEvalException(expression, e) #from None
        else:
            try:
                #Evaluate this expression
                result = eval(expression)
                if wasquoted:
                    result = wasquoted + result + wasquoted
            # catch references to slot names (and erroneous input)
            except (SyntaxError, NameError) as e:
                result = expression
            except Exception as e:
                raise PLCFEvalException(expression, e) #from None

        return str(result)


    @staticmethod
    def evalCounters(lines, counters):
        assert isinstance(lines, list)
        assert isinstance(counters, dict)

        output = []

        for line in lines:
            if PLCF.plcf_tag in line:
                if "#COUNTER" not in line:
                    line = PLCF._evalCounter(line, counters)
                else:
                    (counters, line) = PLCF._evalCounterIncrease(line, counters)

            assert isinstance(line, str)
            # PLCF should now all be processed
            assert PLCF.plcf_tag not in line, "Leftover PLCF# expression in line: {line}".format(line = line)
            output.append(line)

        return (output, counters)


    @staticmethod
    def _evalCounter(line, counters):
        assert isinstance(line,     str )
        assert isinstance(counters, dict)

        # substitutions
        for key in counters.keys():
            (line, _) = PLCF.substitute(line, key, str(counters[key]))

        # evaluation
        (_, line) = PLCF._processLineCounter(line)

        return line


    @staticmethod
    def _evalCounterIncrease(line, counters):
        assert isinstance(line, str)
        assert isinstance(counters, dict)

        # identify start of expression and substitute
        pos = line.find(PLCF.plcf_tag)

        if pos != -1:
            pre  = line[:pos]
            post = line[pos:]

            for key in counters.keys():
                (post, _) = PLCF.substitute(post, key, str(counters[key]))

            line = pre + post

        # identify counter
        counterVar = line.split()[1]
        assert counterVar in counters.keys()

        # evaluate
        (counter, line) = PLCF._processLineCounter(line)
        assert isinstance(counter, int), counter
        assert isinstance(line,    str)

        for key in counters.keys():
            if counterVar == key:
                counters[key] = counter

        return (counters, line)


    @staticmethod
    def _processLineCounter(line):
        assert isinstance(line, str)

        (start, expression, end) = PLCF.getPLCFExpression(line)

        if expression is None:
            return (None, line)

        result = ""

        # evaluation happens after all substitutions have been performed
        try:
            result = eval(expression)

        # catch references to slot names (and erroneous input)
        except (SyntaxError, NameError) as e:
            result = expression

        return (result, line[:start] + str(result) + line[end + 1:])


    @staticmethod
    def getPLCFExpression(line):
        assert isinstance(line, str)

        start = line.find(PLCF.plcf_tag)

        if start == -1:
            return (None, None, None) # nothing to replace

        try:
            end = PLCF.findMatchingParenthesis(line[start:], '[]') + start
        except PLCFException as e:
            raise PLCFException("Malformatted PLCF# expression ({error}) in line {line}".format(error = e.args[0], line = line))
        assert end != -1, "Unclosed PLCF# expression in line {line}".format(line = line)

        expression = line[start + PLCF.plcf_tag_len : end]
        assert PLCF.matchingParentheses(expression)

        return (start, expression, end)


    #Returns the index of the closing paren which matches the first opening paren
    @staticmethod
    def findMatchingParenthesis(line, paren):
        istart = []  # stack of indices of opening parentheses
        d      = []
        oparen = paren[0]
        cparen = paren[1]

        for i, c in enumerate(line):
            if c == oparen:
                istart.append(i)

            if c == cparen:
                try:
                    ci = istart.pop()
                    if not istart:   # check if this closed the first opening parenthesis
                        return i

                    d.append([ci, i])
                except IndexError:
                    raise PLCFException('Too many closing parentheses')

        if istart:  # check if stack is empty afterwards
            raise PLCFException('Too many opening parentheses')

        d.sort()

        return d[0][1]


    # substitutes a variable in an expression with the provided value
    @staticmethod
    def substitute(expr, variable, value):
        assert isinstance(expr,     str)
        assert isinstance(variable, str)
        assert isinstance(value,    str)

        if variable not in expr:
            return (expr, len(expr))

        start           = expr.find(variable)
        end             = start + len(variable)
        pos_after_value = start + len(value)

        return (expr[:start] + value + expr[end:], pos_after_value)

    # checks for basic validity of expression by determining whether
    # open and closed parentheses match
    @staticmethod
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




if __name__ == "__main__":
    class FakeDevice(object):
        def name(self):
            return "FakeDevice"
        def description(self):
            return "FakeDescription"
        def deviceType(self):
            return "FakeDeviceType"
        def propertiesDict(self):
            return { "infinity": "infinity",
                     "lonG"    : "lonG", "lonGer": "lonGer", "lengthy": "lonG",
                     "short"   : "shorter", "shorter" : "tiny",
                     "template": "beast-template",
                     "A"       : "AB", "AB": "AC"}
        def backtrack(self, prop):
            return prop


    cplcf = PLCF(FakeDevice())

    def noException(line):
        print("Checking {}... {}".format(line, cplcf.processLine(line)))


    def match(line, expected):
        print("Checking {}...".format(line), end = '')
        result = cplcf.processLine(line)
        if result == expected:
            print(result)
        else:
            print()
            raise RuntimeError("Test failed for {}:\nexpected {}\ngot      {}".format(line, expected, result))

    def expectException(line):
        try:
            print("Checking {}...".format(line))
            cplcf.processLine(line)
            raise RuntimeError("Test failed for {}".format(line))
        except (PLCFException, AssertionError):
            pass

    noException("[PLCF#]")

    expectException("[PLCF#")

    expectException("[PLCF#[]")

#    noException("[PLCF#(]")
    expectException("[PLCF#(]")

    noException("[PLCF#^(this is (a) weird property)]")

    expectException("[PLCF#(property]")

    expectException("[PLCF#ext.(]")

    expectException("[PLCF#ext.fn(()]")

    match("[PLCF#infinity]", "infinity")

    match("[PLCF#lengthyer]", "lonGer")

    match("[PLCF#lengthyer lengthy]", "lonGer lonG")

    match("[PLCF#short]", "tiny")

    match("[PLCF#template template short]", "beast-template beast-template tiny")

#    match("[PLCF#A]", "AC")
