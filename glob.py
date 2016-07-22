

# memoizing data drawn from CCDB
cached = dict()



templateDict = dict()



# key: device, value: dict of all properties/values
deviceDict = dict()



"""
used in

def getField(device, field):
    # create URL for GET request
    # url     = "https://ics-services.esss.lu.se/ccdb-test/rest/slot/" + device

    url     = "https://ccdb.esss.lu.se/rest/slot/" + device

    request = requests.get(url, verify=False)
              # False because SSH connection is unsigned
    tmpDict = json.loads(request.text)

    result  = tmpDict.get(field)

    return result


"""