# Alarm Factory
(c) 2019-2021 European Spallation Source, Lund
Author: Krisztian Loki

Alarm Factory is intended to simplify alarm service xml file creation.
It takes an alarm tree and one or more alarm definitions and creates an alarm service xml file.

## Quickstart

Alarm Factory requires Python.
The output file name is taken from the config entry name of the alarm tree or the config specified with `--config` if present.

#### CCDB based workflow

Automatically generates an alarm service configuration xml from alarm definition files that are linked to CCDB devices or device types.
The resulting output file will be written to a dedicated directory \(the config entry name in lowercase\) in the `output` folder.

###### Generate alarm configuration xml file for IOC LEBT-010:Vac-IOC-DAQ001 that is in CCDB
`python beastfactory.py --ioc LEBT-010:Vac-IOC-DAQ001`

###### Generate alarm configuration xml file for IOC LEBT-010:Vac-IOC-DAQ001 (that is in CCDB) overriding the config entry name
`python beastfactory.py --ioc LEBT-010:Vac-IOC-DAQ001 --config=mytest`

###### Generate a single alarm configuration xml file from IOCs LEBT-010:Vac-IOC-DAQ001 and VacS-ACCV:Vac-IOC-11010 with 'Vacuum' as config entry name
`python beastfactory.py --ioc LEBT-010:Vac-IOC-DAQ001 --ioc VacS-ACCV:Vac-IOC-11010 --config Vacuum`

### 'Local' workflow

Generates alarm service configuration xml from alarm definition files that are available locally on your computer. The output file is written to the current directory.

###### Generate alarm configuration xml file using local .alarm-tree and .alarms files
`python beastfactory.py --alarm-tree tree.alarm-tree part1.alarms part2.alarms`

### Working with already existing alarm service configuration xmls

Merges already existing alarm service configuration xml files into one xml. The output file is written to the current directory.

###### Merge alarm configuration xml files
`python beastfactory.py --merge-xmls --config "Merged config" first.xml second.xml`


## Usage

#### Input related options

Exactly one of them is required and allowed

*   **--ioc <ioc_name_as_in_CCDB>**
    *   \[**REQUIRED**\]
    *   The IOC for which alarm configuration should be generated. If specified more than once (`--config` becomes mandatory) a single configuration will be generated merging the alarm trees (and alarms) of the IOCs
    *   `--ioc LEBT-010:Vac-IOC-DAQ001`
    *   `--ioc LEBT-010:Vac-IOC-DAQ001 --ioc VacS-ACCV:Vac-IOC-11010`
*   **--merge-xmls**
    *   \[**REQUIRED**\]
    *   Merges alarm configuration xml files to one. `--config` is mandatory.
*   **--alarm-tree <alarm_tree_file>**
    *   \[**REQUIRED**\]
    *   The filename of the .alarm-tree file
    *   `--alarm-tree tree.alarm-tree`

#### CCDB options

Consulted when `--ioc` is specified

*   **--ccdb <directory_of_ccdb_dump_OR_path_to_.ccdb.zip>**
    *   \[OPTIONAL\]
    *   Use the specified CCDB-dump of _device_ instead of connecting to the CCDB database
    *   `--ccdb VacS-ACCV_Vac-PLC-01001.ccdb.zip`
    *   `--ccdb modules/m-epics-vacs-accv_vac-plc-01001/misc/ccdb`
*   **--ccdb-test**
    *   \[OPTIONAL\]
    *   Use the test version of the CCDB database
*   **--ccdb-production**
    *   \[OPTIONAL\]
    *   Use the production version of the CCDB database. This is the default.
*   **--tag <tag_name>**
    *   \[OPTIONAL\]
    *   Used to select the correct link if more than one External Link was found
    *   `--tag mps` will match
        *    External Links with name `BEAST TREE__mps`, `BEAST TEMPLATE__mps`, and `BEAST__mps`

#### General purpose options

*   **--config <config_entry_name>**
    *   \[OPTIONAL\]
    *   Use this name instead of the one specified in the alarm tree. **REQUIRED** if `--ioc` is specified more than once
    *   `--config mytest`
*   **--verify**
    *   \[OPTIONAL\]
    *   Try to cross-check alarms with Interface Definition files. Only works with the `--ioc` option

## CCDB configuration

#### Git repository

Every configuration and definition file shall be uploaded to a Git repository (only Bitbucket has been tested so far). The URL of the repository (without the **.git** extension) shall be specified as an _External Link_.

#### External Links

The name of an External Link shall be one of the following:

*    **`BEAST TREE`**
    *   Filename extension: .`alarm-tree`
*    **`BEAST TEMPLATE`**
    *   Filename extension: .`alarms-template`
*    **`BEAST`**
    *   Filename extension: .`alarms`

The aforementioned names can be specialized further by specifying an additional "tag":

*    **`BEAST TREE__tag`**
*    **`BEAST TEMPLATE__tag`**
*    **`BEAST__tag`**

This enables devices to have more than one alarm definition and selects the correct one specified by the "tag" (see `--tag` option).

#### Git tags, branches, commits

It is possible to specify a Git tag / branch / commit to use other than _master_ with the following properties (either on _slot_ or _device type_ level):

*    **`BEAST TREE VERSION`** or **`BEAST TREE__tag VERSION`**
*    **`BEAST TEMPLATE VERSION`** or **`BEAST TEMPLATE__tag VERSION`**
*    **`BEAST VERSION`** or **`BEAST__tag VERSION`**

#### File names

By default AlarmFactory constructs the filename to download as follows:

*    takes the name of the _device type_
*    in all uppercase
*    changes reserved characters (**<**, **>**, **:**, **"**, **/**, **\\**, **|**, **?**, **\***) to **_**
*    appends the extension that belongs to the External Link name

It is possible to explicitly specify the filename in square brackets after `BEAST*`; **`BEAST[file-to-download]`**, **`BEAST TEMPLATE__tag[file-to-download]`**. The file must still have the correct extension (although it is automatically appended if not already specified). This technique can be used to share the same Alarm Definition across device types.

## Basic definitions

#### Creating the Alarm tree

The alarm tree definition uses a subset of the 'normal' alarm definition syntax and has to be assigned to the IOC (or specified with the `--alarm-tree` option). The assignment is done with the **`BEAST TREE`** External Link name. The extension of the file shall be **`.alarm-tree`**. A sample alarm tree looks like this (Tabs/Spaces are optional):
```
config("sample")
component("Level1.1")
	component("Level2.1")
		component("Level3.1")
		end_component()
	end_component()
	component("Level2.2")
	end_component()
end_component()
component("Level1.2")
end_component()
```

#### Creating alarm template definitions

Only works with the CCDB based workflow.

Alarm template definitions define `PV`s _without_ the device prefix and are usually assigned to a group of devices. The `PV`s will be prefixed with the actual device name in the generated configuration. Alarm template definitions shall have **`.alarms-template`** as extension and assigned to **`device types`** or **`devices`** with the **`BEAST TEMPLATE`** External Link name.

#### Creating alarm definitions

Alarm definitions that define "complete" `PV`s (fully prefixed with a device name) and can only be assigned to individual devices (usually to the IOC itself). Alarm definitions shall have **`.alarms`** as extension and assigned to **`devices`** with the **`BEAST`** External Link name.

## Alarm definition syntax

Please see [beastdef.md](beastdef.md)
