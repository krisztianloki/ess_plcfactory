# BEAST Definition syntax

## General rules

Because in the current implementation every alarm definition is a special subset of python the same set of rules apply as to a python script. Basically every "instruction" is a function call; thus parenthesis are mandatory. Optional arguments are represented as keyword arguments and take the form of **`KEYWORD="value"`**. An exception to python syntax is that leading spaces and tabs are allowed (and ignored).

## Defining config

Can only be used in `.alarm-tree`
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

## Defining default attributes

Can be used in `.alarm-tree`, `.alarms`, `.alarms-template` definitions.
Every alarm will have these attribute values unless they are explicitly overriden.

### Latching

**`default_latching({True|False})`**

### Annunciating

**`default_annunciating({True|False})`**

## Defining Titles for Guidance, Display, Command, and Automated action attributes

Can be used in `.alarm-tree`, `.alarms`, `.alarms-template` definitions.
To ease maintenance the possible titles of aforementioned attributes have to be defined beforehand. Every title is assigned a _type_ (a string identifier) and this type shall be used when defining the actual attributes.

### Title

**`define_title("<type>", "<title>")`**

## Adding alarms to a component

Can only be used in `.alarms` and `.alarms-template` definitions.
After a component is defined it can be populated with alarms. An alarm definition starts with defining the associated PV. Attributes of an alarm can be defined *after* defining the PV. The scope of an alarm / PV ends with the definition of another alarm / PV.

### PV

**`pv("<name>")`**

### Description

**`description("<desc>")`**

### Latching

**`latching({True|False})`**

### Annunciating

**`annunciating({True|False})`**

### Guidance

**`guidance("<type>", "<guidance>")`**

### Display

**`display("<type>", "<display>")`**

### Command

**`command("<type>", "<command>")`**

### Automated action

**`automated_action("<type>", "<action>", <delay>)`**

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

*   `pv("CrS-TICP:Cryo-Virt-MJFLT1:Major_Fault_051")`
    `description("Instrument Air Failure On Cold Box")`
    `guidance("op_action", "utilities fault 55- cold box emergency stop")`
    `guidance("causes", "No pneumatic air available / Filter clogged")`

    `pv("CrS-TICP:Cryo-Virt-MJFLT1:Major_Fault_055"`
    `description("Utilities Fault On Cold Box")`
    `guidance("op_action", "close PV-31301 and PV-33399- reset purifier and mobile dewar filling")`
    `guidance("causes", "")`

    *   Defines two alarms

### Components

*   `component("TICP ColdBox")`
    `    component("UTILITIES")`
    `    end_component()`
    `    component("ColdBox Vacuum")`

    *    Defines the following component tree
         *   TICP ColdBox
             *   UTILITIES
             *   ColdBox Vacuum

