# PLC Factory
(c) European Spallation Source, Lund

Authors:

- Gregor Ulm: 2016-07-04 to 2016-09-02
- ...


## Overview

PLC Factory is a Python script that automates some of the tasks associated with programming PLCs. Concretely, it processes template files and creates TIA Portal files or EPICS database records that contain device information and other information, which may even be dynamically calculated. Thus, PLC Factory eliminates a large part of the potentially tedious and error-prone work associated with programming PLCs.


## Requirements

PLC Factory requires:

- Python 2.7
- Python library `requests` 2.10.0, provided in `/libs`

In addition, the user needs to have read-access to CCDB. Lastly, this application has been developed on Apple OSX. It should run without modifications on any POSIX-compliant operating system, but may not work as intended on non-POSIX-compliant operating systems. Non-POSIX-compliant operating systems included some versions of Microsoft Windows.


## Template file format

Template file names have to have the extension `.txt`. Note that the filename, without the extension, has to end with an integer, which can be separated from the required keyword `TEMPLATE` with an underscore (`_`), e.g. `VALVE_TEMPLATE_TIA-MAP.txt`.

Example template files are provided in the folder `/sample_templates`.


## Files

PLC Factory consists of the following files:


- `plcfactory.py`
- `glob.py`
- `ccdb.py`
- `processTemplate.py`
- `plcf.py`
- `plcf_ext.py`

- `README.md`
- `doc/plcfactory.md`
- `doc/plcf.md`



## Usage

The invocation of the script follows the pattern:

`python plcfactory.py --device <device-name> --template <template ids>`

It is possible to use shorthands for the parameters:

`python plcfactory.py -d <device-name> -t <template ids>`

For instance, `python plcfactory.py -d LNS-LEBT-010:Vac-PLC-11111 -t TIA-MAP TIA-DEVICES`.

Execution of the script ends with writing an output file to the directory `/output`.


## Outline

PLC Factory performs the following steps (pseudocode) for each of the provided template IDs, in order:

1. Look up `<device-name>` either in CCDB (first access) or in-memory

2. Determine which devices `X` are controlled by `<device-name>`

3. initialise a set `toProcess`, populated with all devices that are controlled by `<device-name>`

4. while `toProcess` is not empty:

  * remove one element `x`,

  * process template with id `i` associated with `x`, if available

  * add devices controlled by `x` to `toProcess`, but only if they have not yet been processed  

  * remove `x` from `toProcess`

5. Process header file associated with `<device-name>`

6. Process footer file associated with `<device-name>`

7. Write one output file according to specification in header file


For further details, please consult the provided source code.


## Some features

### Processing trees of arbitary depth

The dependencies that are defined between devices as `controls` and `controlBy` relationships in CCDB are interpreted as trees. PLC Factory can take any device `X` in this tree as an input parameter, and will exhaustively process the entire subtree of which `X` is the root element.


### Flexbile handling of properties

Instead of looking up property names that are provided in a PLCF expression in template files (see `doc/plcf.md` for further information), the lookup happens in reverse, i.e. first all properties that are associated with the current device are looked up in CCDB. Afterwards, each such property is evaluated to its corresponding value if it appears in the current PLCF# expression. The reasoning behind this approach is that it leads to great flexibility as it makes it possible to define any property in CCDB, whose value will be correctly used when processing template files as long as both the property name in CCDB and the property name in the associated template file match.


### References to property values in parent nodes

In order to minimize CCDB maintenance, it is possible to specify that a property value of a device `X` should refer to a property value of a device `Y` with which it is in a `controlBy` relationship, according to CCDB. The substitution is recursive, meaning that if the parent device does not have the desired property, the parent's partents will be evaluated, and so on, until a matching property name is encountered.

The benefit of this approach is that it greatly simplifies maintaining information of devices that use property values that are also present in a parent node. For instance, if device `X` controls `n` devices, which all share one particular property of `X`, then this property has to be defined only once in CCDB for device `X`, and not once for device `X` and `n` times for all devices this device controls.

In order to make use of this ability of PLC Factory, tag a property as follows: `^(<property>)`, e.g. `[PLCF# ^(PropertyString02)]`. This means that there will be no lookup for `PropertyString02` for the current device `X`, but for all devices `X` is controlled by, directly or indirectly, until one device is encountered for which a corresponding entry for `PropertyString02` exists in CCDB.


### Global handling of two counter variables

In order to remove the tedium of manually specifying values for memory locations, it is possible to make use of up to two counter variables in template files, `Counter1` and `Counter2`. After all template files have been processed, a final pass is performed that assigns correct values to all counter variables in the temporary data before creating the output file. The starting value for both counters is `0`.



### Custom file name

In order to create a custom filename for the output file, a header file needs to be provided. It has to contain, as the very first line, a definition of the desired name for the output file. The expected format is as follows:

`#FILENAME [PLCF#INSTALLATION_SLOT]-[PLCF#TEMPLATE]-[PLCF#TIMESTAMP].scl`

Note that certain characters in the resulting file name may get changed if they are not allwed in file names by the underlying operating system. For instance, on OSX, the colon (`:`) sign is turned into a slash (`/`).

The definition needs to start with `#FILENAME`. The following four keywords are implemented:

`INSTALLATION_SLOT`: installation slot taken from the invocation of `plcfactory.py`

`DEVICE_TYPE`:       device type retrieved from CCDB

`TEMPLATE`:          template number; taken from provided argument

`TIMESTAMP`:         date and time of programm invokation, using current system time

In order to add further fields, modify the function definition of `createFilename()` in the file `plcfactory.py`.

You can choose any file extension you want, and even omit an extension altogether.


## For advanced users

### Adding keywords

Look for the following lines of code is `plcf.py`:

	def keywordsHeader(filename, device, n):
	    assert isinstance(filename, str)
	    assert isinstance(device,   str)
	    assert isinstance(n,        int)

	    timestamp  = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
	    deviceType = ccdb.getDeviceType(device)

	    # dictionary of the form key: tag, value: replacement
	    substDict = {'INSTALLATION_SLOT': device
	                ,'TEMPLATE'         : 'template-' + str(n)
	                ,'TIMESTAMP'        : timestamp
	                ,'DEVICE_TYPE'      : deviceType
	                }

In order to add a new keyword, add a new entry to `substDict`. You may need to provice the corresponding value as a function argument.



### Scaling behavior

PLC Factory is rather efficient. The bottleneck of the execution is due to input/output operations like accessing CCDB via the network, downloading template files, opening those files, and writing the final output.

PLC Factory runs in `O(m + n) = O(n)`, where `m` is the number of device types, of which there is one template associated with each device type. Furthermore, `n` is the number of devices. CCDB needs to be accessed once for every device in a dependency tree. Internal operations are disregarded in this calculation; writing the final output is interpreted as a constant. As a consequence, PLC Factory is expected to scale linearly, depending on the number of both unique device types and the total number of devices.

Note that processing additional templates is a constant (!) because information regarding the same devices is needed. However, after the first template has been processed, informaiton regarding each affected device has been requested from CCDB once already and is therefore available in-memory.