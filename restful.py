import json
import os
import sys


# add directory for third-party libraries to module search path
parent_dir = os.path.abspath(os.path.dirname(__file__))
lib_dir    = os.path.join(parent_dir, 'libs')
sys.path.append(lib_dir)

# third-party libraries, stored in folder 'libs' 
import requests

# disable printing of unsigned SSH connection warnings to console
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def controlCCDB(plc):
    assert isinstance(plc, str)
    return queryCCDB(plc, 'control')
    
    
def propertiesCCDB(plc):
    assert isinstance(plc, str)
    return queryCCDB(plc, 'properties')


def queryCCDB(plc, field):
    assert isinstance(plc,   str)
    assert isinstance(field, str)

    # create URL for GET request
    url     = "https://ics-services.esss.lu.se/ccdb-test/rest/slot/" + plc
    request = requests.get(url, verify=False)
                 # False because SSH connection is unsigned
    tmpDict = json.loads(request.text)
    
    result  = tmpDict.get(field)
    # convert from utf-8 to ascii for keys
    result  = map(lambda x: str(x), result)
    
    return result