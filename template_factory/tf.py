""" Template Factory:  """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


from tf_ifdef import IF_DEF
from printers import get_printer, available_printers


def new():
    return IF_DEF()


def _processLine(if_def, line, num):
    assert isinstance(if_def, IF_DEF)
    assert isinstance(line,   str)
    assert isinstance(num,    int)

    errormsg = "{error} at line {num}: {line}"

    try:
        if_def.add(line)
    except SyntaxError:
        print errormsg.format(error = "Syntax error", num = num, line = line.strip())
        exit(1)
    except AssertionError,e :
        print errormsg.format(error = "Internal error", num = num, line = line.strip())
        if e.args:
            print e.args[0]
        exit(1)
    except Exception, e:
        print errormsg.format(error = "Exception", num = num, line = line)
        if e.args:
            print e.args[0]
        exit(1)


def processLines(lines, processor = None):
    if isinstance(lines, list):
        assert isinstance(lines[0], str)
    else:
        assert isinstance(lines, file)

    if_def = IF_DEF()

    if processor is None:
        processor = _processLine

    multiline  = None
    multilinei = 1
    i = 1
    for line in lines:
        #
        # Check for multiline strings making sure that it actually spans multiple lines
        #
        if line.count('"""') % 2:
            if multiline is None:
                multiline  = line
                multilinei = i
            else:
                multiline += line
                processor(if_def, multiline, multilinei)
                multiline = None
        elif multiline:
            multiline += line
        else:
            processor(if_def, line, i)
        i += 1


    if multiline:
        multiline_error = "Unclosed multiline string at {num}: {line}"
        print multiline_error.format(num = multilinei, line = multiline)
        return None

    if_def.end()

    return if_def


def assert_IF_DEF(obj):
    assert isinstance(obj, IF_DEF)




if __name__ == "__main__":
    pass
