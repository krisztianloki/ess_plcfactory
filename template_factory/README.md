Integrating PLCs into an EPICS control system can be an error-prone task. Some of the error inducing difficulties can be mitigated by using CCDB and PLC Factory to create an EPICS database, an EEE module, and PLC code that handles the communication with an IOC. Of course this does not come for free; the interface between EPICS and the PLC has to be defined somehow. This somehow is the so-called **Interface Definition**. An interface definition is a text file (technically a python script with a very limited set of functionality) that defines what kind of information travels in which direction.

# The basics of an EPICS-PLC interface

The information flow has to directions:

*   from the PLC to EPICS; sent periodically (regardless of any value-change) as a block of data  

    *   **_status information_**

*   from EPICS to the PLC; sent only when requested and sent as individual data elements  

    *   **_commands_**
    *   **_parameters_**

## Status information

Typically these are sensor readings and various state information about the PLC program itself. A word array is constructed at the PLC side that is sent periodically and is disassembled by the IOC into individual PVs. Status information is enclosed in a **status block**.

## Commands

These are instructions to the PLC program. The PLC code resets every command to the default 0 value upon receiving. This prevents the repetition of the same command and ensures that only commands that are actually resent are interpreted as new instructions. Usually commands are one-bit values, but there is no restriction on their type. Commands are enclosed in a **command block**.

## Parameters

These are control values sent to the PLC program. Their values are preserved between PLC cycles. Typical parameters are setpoints and alarm limits Parameters are enclosed in a **parameter block**.

## Types

The following types can be used to add a variable to an interface definition:

*   **digital**; a simple 1-bit information. Maps to the **_binary input/output_** record in EPICS and to the **_BOOL_** type in the PLC
*   **analog**; an integer or floating point value. Maps to the **_analog input/output_** record in EPICS and the **_user specified_** PLC type in the PLC
*   **time**; an interval (NOT a timestamp) in milliseconds. Maps to the **_analog input/output_** record in EPICS and to the **_TIME_** type in the PLC
*   **alarm**; a simple 1-bit information that can generate an EPICS alarm. By default a value of 1 results in an alarm. Maps to the **_binary input_** record in EPICS and to the **_BOOL_** type in the PLC.
*   **enum**; an enumeration. Maps to the **_multi-bit binary input/output_** record in EPICS and the **_user specified_** PLC type in the PLC
*   **bitmask**; bits of a 16 bit integer. Maps to the **_multi-bit binary input/output direct_** record in EPICS and to the **_INT_** type in the PLC
*   **string**; a maximum 39 character long string. Maps to the **_stringin_** record in EPICS and to the **_STRING_** type in the PLC

## PLC Types

The following PLC types can be used to "back" the variables defined in the interface definition:

*   **BOOL**; it is implicitly specified with the **digital** type
*   **BYTE**; 8-bit integer
*   **USINT**; 8-bit unsigned integer
*   **SINT;** 8-bit signed integer
*   **WORD**; 16-bit unsigned integer
*   **INT**; 16-bit signed integer
*   **UINT**; 16-bit unsigned integer
*   **DWORD**; 32-bit unsigned integer
*   **DINT**; 32-bit signed integer
*   **UDINT**; 32-bit unsigned integer
*   **REAL**; 32-bit floating point number
*   **TIME**; it is implicitly specified with the **time** type
*   **STRING**; it is implicitly specified with the **string** type

## Data Layout

All the variables in each direction are assembled into a WORD (16-bit integer) array on the PLC side (the command and parameter blocks are concatenated to form one array). The array is filled from top to bottom, meaning that the earlier a variable shows up in the interface definition, the lower its array index will be.

Digital types are packed into WORDs so no space is wasted. The earlier the digital variable shows up, the lower its significance will be in the resulting WORD (ie. the first digital is mapped to 2⁰, the second to 2¹, and so on). If for whatever reason you need to have more control over the mapping to individual bits, spare digitals can be introduced.

**There is no mechanism to put a variable to a specific index (or bit) in the resulting array.**

# Interface Definition syntax

## General rules

Because in the current implementation every interface definition is a special subset of python the same set of rules apply as to a python script. Basically every "instruction" is a function call; thus parenthesis are mandatory. Optional arguments are represented as keyword arguments and take the form of **`KEYWORD="value"`**.

## Defining blocks

A block can only be defined once, empty blocks need not be defined. The scope of a block definition ends with the definition of another block.

### Status block

**`define_status_block()`**

### Command block

**`define_command_block()`**

### Parameter block

**`define_parameter_block()`**

## Adding variables to a block

After a block is defined it can be populated with variables. Adding a variable is done with the **`add__<type>_()`** construct. Every variable has a name; this name can be used to reference the variable in the PLC code and will be used (as the signal part) to construct the record name. Every variable has an associated PLC type, some variables (digital, time, alarm) have fixed types, for the others the type must be explicitly defined. EPICS fields can be specified with the **`PV__<field>_="value"`** keyword arguments. For example to have a different variable name in EPICS than in the PLC, the **`PV_NAME="different_name"`** argument can be used. A mockup variable declaration looks like this:

**`add_<type>("<name>", "<plc_type>" [,KEYWORD1="value"[, KEYWORD2="value"]...])`**

### Digital variable

**`add_digital("<name>")`**

Adding a spare bit:

**`add_digital()`**

**`skip_digital()`**

Adding more than one spare bit:

**`skip_digitals(<number>)`**

### Analog variable

**`add_analog("<name>", "<plc_type>")`**

### Time variable

**`add_time("<name>")`**

### Alarm variable

The _`short_alarm_message`_ will end up in the PV's ONAM (or ZNAM) field

A minor alarm if the value is 1:

**`add_minor_alarm("<name>", "<short_alarm_message>")`**

A major alarm if the value is 1:

**`add_major_alarm("<name>", "<short_alarm_message>")`**

A minor alarm if the value is 0:

**`add_minor_alarm("<name>", "<short_alarm_message>", INVERSE_LOGIC=True)`**

A major alarm if the value is 0:

**`add_major_alarm("<name>", "<short_alarm_message>", INVERSE_LOGIC=True)`**

### Enum variable

**`add_enum("<name>", "<plc_type">)`**

### Bitmask variable

**`add_bitmask("<name>", "<plc_type">)`**

### String variable

**`add_string("<name>" [, length])`**

The default length is the maximum allowed by EPICS; 39 characters

## Specifying archiving requirements

If a variable has to be archived the **`ARCHIVE=<spec>`** construction can be used. <spec> can be one of the following:

*   **`True`**; the variable will be archived with the default _policy_ of Archiver Appliance
*   **`"<policy>"`**; the variable will be archived with the specified policy of Archiver Appliance

The specifications will be collected in a file ending with _.archive_. This file has to be uploaded to the relevant archiver configuration repository.

## Examples

### Archiving examples

*   `add_digital("Error",`             **`ARCHIVE=True`**`)`
    *   Archive with the default policy
*   `add_analog("ErrorCodeR", "INT",`  **`ARCHIVE="1Hz"`**`)`
    *   Archive with the 1Hz policy
