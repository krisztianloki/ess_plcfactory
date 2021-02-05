# BEAST Definition syntax

## General rules

Because in the current implementation every alarm definition is a special subset of python the same set of rules apply as to a python script. Basically every "instruction" is a function call; thus parenthesis are mandatory. Optional arguments are represented as keyword arguments and take the form of **`KEYWORD="value"`**. An exception to python syntax is that leading spaces and tabs are allowed (and ignored).

## Defining config

Can only be used in `.alarm-tree`.
It is used to define the BEAST configuration name

**`config("<name>")`**

## Defining components

Can be used in `.alarm-tree`, `.alarms`, `.alarms-template` definitions.
Components defined in `.alarms` and `.alarms-template` files shall match (a subset of) the alarm tree structure.
A component can be embedded in another component. The scope of a component ends with the explicit closure of it.

### Starting a component

**`component("<name>")`**

### Closing a component

**`end_component()`**

## Including alarm templates

**Can only be used in `.alarm-tree`.**\
**Works only with --ioc**

If alarms from a device type have to be added to more than one component, this feature comes to the rescue. For example, the alarms for each ODH monitor belong to different components and it does not make sense to create a new `.alarms-template` with different `component()` definitions for **every** ODH monitor; create only one **without** component definitions and include that in the alarm tree at the correct components.

### Including by device name

**`include("<device-name-as-defined-in-CCDB>")`**

### Including by device type

**`include_type("<device-type-as-defined-in-CCDB>"[, filter="<regular-expression>"])`**

The _filter_ regular expression is matched against the name of the included device, if not specified then all devices in the device type are included.

## Defining default attributes

Can be used in `.alarm-tree`, `.alarms`, `.alarms-template` definitions.
Every alarm will have these attribute values unless they are explicitly overriden.

### Latching

**`default_latching({True|False})`**

**NOTE** despite the documentation states the the server default is **latching**, it does not seem to be the case. So it is best to always specify the default.

### Annunciating

**`default_annunciating({True|False})`**

### Filtering

**`default_filter("<filter_expression>")`**

## Defining Titles for Guidance, Display, Command, and Automated action attributes

Can be used in `.alarm-tree`, `.alarms`, `.alarms-template` definitions.

A title is:
*   a short text for the **guidance** that will appear in the context menu of the alarm, for example “Contacts” or “What to do”.
*   a short text for the **display** link that will appear in the context menu, for example “Vacuum Display”.
*   a short description of the **action**.

To ease maintenance the possible titles have to be defined beforehand. Every title is assigned a _type_ (a string identifier) and this type shall be used when defining the actual attributes.

### Title

**`define_title("<type>", "<title>")`**

## Adding alarms to a component

Can only be used in `.alarms` and `.alarms-template` definitions.
After a component is defined it can be populated with alarms. An alarm definition starts with defining the associated PV. Attributes of an alarm can be defined *after* defining the PV. The scope of an alarm / PV ends with the definition of another alarm / PV.

The Alarm Delay and Count work in combination. By default, with both the alarm delay and count at zero, a non-OK PV severity is right away recognized. When the alarm delay is larger than zero, it starts a timer to check the PV after the given delay. For example, assume an alarm delay of 10 seconds, and the PV enters a MINOR alarm. If the PV still carries a not-OK severity after 10 seconds, the alarm state becomes MINOR or whatever the highest alarm severity of the PV was in the 10 seconds since first entering a not-OK severty. On the other hand, if the PV recovers to OK, there will be no alarm after the 10 second delay.

As a second example, consider a PV that assumes MINOR severity, then recovers to OK and re-enters MINOR severity a couple of times. If the non-OK severity never persists longer then 10 seconds, it is ignored. The alarm count can be used to detect such cases. With an alarm count of 5, even if each non-OK severity lasts only say 1 second, when the PV becomes not-OK for 5 or more times within 10 seconds, the alarm will be indicated. For a delay of 10 seconds and a count of 5, there are thus two ways to enter an alarm state: Either the PV stays not-OK for at least 10 seconds, or it briefly becomes not-OK for at least 5 times within 10 seconds.

While the filter, alarm delay and count can be helpful to reduce the number of alarms from ‘noisy’ PVs, ideally all such logic is implemented at the source, i.e. in the IOC that provides the alarm trigger PV. This not only simplifies the task of the alarm system, but also makes the behavior more obvious, since a PV is used “as is”, the alarm server uses the same alarm state that is indicated in a display panel, without adding filtering that might not be obvious when later inspecting an alarm.

Note again that the alarm system only reacts to the severity of alarm trigger PVs. For EPICS records, this is for example configured via the HIGH, HSV and HYST fields of analog records, or the ZSV and OSV fields of binary records. Why, when and for how long an alarm trigger PV enters an alarm state is configured on the data source, and is not immediately obvious from the received alarm severity.

For example, an analog record might enter a MINOR alarm state when its value exceeds the ‘HIGH’ value. Why a certain HIGH threshold was chosen, what the user should do about it, and how the threshold could be changed, however, cannot be automatically determined. When adding an alarm trigger PV to the alarm system, it is thererfore important to also configure guidance and display links which allow the user to figure out:

*   What does this alarm mean? What should I do about it?
*   What displays allow me to see more, where can I do something about the alarm?


### PV

**`pv("<name>"[, delay=<delay>[, count=<count>]])`**

*   Delay: Only alarm if the trigger PV remains in alarm for at least this time.
*   Count: Used in combination with the alarm delay. If the trigger PVs exhibits a not-OK alarm severity more more than `count` times within the alarm delay, recognize the alarm.

For example, an alarm delay of 10 with an alarm count of 5 means: Recognise an alarm if the PV enters a not-OK severity for more than 10 seconds, **or** more often than 5 times within 10 seconds.

When the count is zero, only the alarm delay is used.

### Description

**`description("<desc>")`**

This text is displayed in the alarm table when the alarm triggers.

The description is also used by the alarm annunciator. By default, the annunciator will start the actual message with the alarm severity. For example, a description of “Vacuum Problem” will be annunciated as for example “Minor Alarm: Vacuum Problem”. The addition of the alarm severity can be disabled by starting the description with a `*` as in `"* Vacuum Problem”`.

When there is a flurry of alarms, the annunciator will summarize them to “There are 10 more alarms”. To assert that certain alarms are always annunciated, even if they occur within a burst of other alarms, start the message with `!` (or `*!`).

### Disabling

**`disable()`**

### Latching

**`latching({True|False})`**

By default, the Alarm Server latch alarms to the highest received severity until the alarm is acknowledged **and** clears. Use `latching(False)` (or set `default_latching(False)`) if the alarm should recover without requiring acknowledgement.

### Annunciating

**`annunciating({True|False})`**

Should the alarm be annunciated (if the annunciator is running), or should it only be displayed silently?

### Filtering

**`filter("<filter_expression>")`**

An optional expression that can enable the alarm based on other PVs.

Example: `"‘abc’ > 10"` will only enable this alarm if the PV `‘abc’` has a value above 10.

### Guidance

**`guidance("<type>", "<detail>")`**

Each alarm should have at least one guidance message to explain the meaning of an alarm to the user, to list for example contact information for subsystem experts. Guidance can be configured on each alarm PV, but it can also be configured on parent components of the alarm hierarchy.

*   `type`: the identifier of the title defined with `define_title()`
*   `detail`: A slightly longer text with the content of the guidance, for example a list of telephone numbers, or description of things to try for handling the alarm.

### Display

**`display("<type>", "<detail>")`**

As with Guidance, each alarm should have at least one link to a control system display that shows the actual alarm PV and the surrounding subsystem.

*   `type`: the identifier of the title defined with `define_title()`
*   `detail`: The display link. This is handled similar to `-resource..` arguments passed on the Phoebus command line. For plain display files, the complete path to the file will suffice, and the display tool is recognized by the file extension, i.e. \*.bob for the display runtime, or \*.html to open a web page. When passing macros, a complete URL is required.

### Command

**`command("<type>", "<command>")`**

### Automated action

**`automated_action("<type>", "<action>"[, <delay>])`**

**NOTE: delay must be an integer (in seconds) not a string.**

Automated actions are performed when the node in the alarm hierarchy enters and remains in an active alarm state for some time.

The intended use case for automated action is to for example send emails in case operators are currently unable to acknowledge and handle the alarm. If the alarm should always right away perform some action, then this is best handled in the IOC.

The automated action configuration has three parts:

*   `type`: the identifier of the title defined with `define_title()`
*   `delay`: (in seconds) determines how long the node needs to be in an active alarm state before the automated action is executed. A delay of 0 seconds will immediately execute the action, which in practice suggests that the action should be implemented on an IOC.
*   `action`: determines what the automated action will do.
    *   `mailto:user@site.org,another@else.com`: Sends email with alarm detail to list of recipients. The email server is configured in the alarm preferences.
    *   `cmd:some_command arg1 arg2`: Invokes command with list of space-separated arguments. The special argument `*` will be replaced with a list of alarm PVs and their alarm severity. The command is executed in the `command_directory` provided in the alarm preferences.
    *   `sevrpv:SomePV`: Names a PV that will be updated with the severity of the alarm, i.e. a value from 0 to 9 to represent the acknowledged or active alarm state. The delay is ignored for `sevrpv:` actions.



## Examples

### Titles

*   `define_title("op_action", "[Operator Action]")`
    *   Defines a title with type "op_action", and assigns the value of "[Operator Action]"
*   `define_title("causes", "[Possible Causes]")`
    *   Defines a title with type "causes", and assigns the value of "[Possible Causes]"

### Defaults

*   `default_latching(False)`
    *   Every alarm will be non-latching by default
*   `default_annunciating(True)`
    *   Every alarm will be announced by default

### Attributes

*   `guidance("op_action", "Cold box emergency stop")`
    *   Adds "[Operator Action]" guidance with "Cold box emergency stop" as details
*   `guidance("causes", "No Pneumatic air available / Filter clogged")`
    *   Adds "[Possible Causes]" guidance with "No Pneumatic air available / Filter clogged" as details

### Alarms

*   `pv("CrS-TICP:Cryo-Virt-MJFLT1:Major_Fault_051")`\
    `description("Instrument Air Failure On Cold Box")`\
    `guidance("op_action", "utilities fault 55- cold box emergency stop")`\
    `guidance("causes", "No pneumatic air available / Filter clogged")`

    `pv("CrS-TICP:Cryo-Virt-MJFLT1:Major_Fault_055"`\
    `description("Utilities Fault On Cold Box")`\
    `guidance("op_action", "close PV-31301 and PV-33399- reset purifier and mobile dewar filling")`\
    `guidance("causes", "")`

    *   Defines two alarms

### Components

*   `component("TICP ColdBox")`\
    `    component("UTILITIES")`\
    `    end_component()`\
    `    component("ColdBox Vacuum")`

    *    Defines the following alarm tree
         *   TICP ColdBox
             *   UTILITIES
             *   ColdBox Vacuum

### Including

**NOTE: only works with --ioc**

#### Devices

*   `component("ODH")`\
    `    component("Monitor 1")`\
    `        include("section-subsection:ODH-O2iM-1")`\
    `    end_component()`\
    `    component("Monitor 2")`\
    `        include("section-subsection:ODH-O2iM-2")`\
    `    end_component()`\
    `end_component()`

    *    Defines the following alarm tree and includes the `.alarms-template` (defined with the `BEAST TEMPLATE` External Link) from the two ODH monitors
         *   ODH
             *   Monitor 1
                 * alarms of `section-subsection:ODH-O2iM-1`
             *   Monitor 2
                 * alarms of `section-subsection:ODH-O2iM-2`

#### Device types

*   `component("ODH")`\
    `    component("Monitors")`\
    `        include-type("odh-monitor")`\
    `    end_component()`\
    `end_component()`

    *    Defines the following alarm tree and includes the `.alarms-template` (defined with the `BEAST TEMPLATE` External Link) from the controlled ODH monitors
         *   ODH
             *   Monitors
                 * alarms of `section-subsection:ODH-O2iM-1`
                 * alarms of `section-subsection:ODH-O2iM-2`

*   `component("ODH")`\
    `    component("Monitors")`\
    `        include-type("odh-monitor", filter="^FEB")`\
    `    end_component()`\
    `end_component()`

    *    Defines the following alarm tree and includes the `.alarms-template` (defined with the `BEAST TEMPLATE` External Link) from the controlled ODH monitors if the device name starts with 'FEB'
         *   ODH
             *   Monitors
                 * alarms of `FEB-subsection:ODH-O2iM-1`
                 * alarms of `FEB-subsection:ODH-O2iM-2`
