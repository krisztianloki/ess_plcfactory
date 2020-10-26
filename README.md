# PLC Factory
(c) 2016-2018 European Spallation Source, Lund
Author: Gregor Ulm, Krisztian Loki, Miklos Boros

PLC Factory is intended to simplify programming PLCs and creating the communication interface between EPICS and PLCs.
It is also capable of processing text files and substituting specially formatted expressions that are defined as properties in CCDB.
It takes an arbitrary device and a list of template ids as input and processes the corresponding sub-tree of devices according to their entries in CCDB.

## Quickstart

PLC Factory requires Python 2.7.

Automaticly generate the PLC block and the corresponding IOC from CCDB using .def files. The .def files are linked to the CCDB device types.

#### Generate TIAv14 blocks with EEE module:
`python plcfactory.py -d CrS-CMS:Cryo-PLC-01 --plc-siemens=14 --eee`

#### Using manually created PLC Factory templates:

Invocation follows the pattern `python plcfactory.py --device <device> --template <ids>`, where `ids` is a list of template names of at least one element.

###### Sample invocation:
`python plcfactory.py --device LNS-LEBT-010:Vac-PLC-11111 --template EPICS-DB TIA-MAP`

###### With shorthands:
`python plcfactory.py -d LNS-LEBT-010:Vac-PLC-11111 -t EPICS-DB TIA-MAP`

The resulting output file(s) will be written to a dedicated directory \(derived from the device name\) in the `output` folder (can be customized with the `--output` option).

For further information, see the files in [doc](doc/).

## Usage

#### General purpose options

*   **--device=<device_name_as_in_CCDB>**
    *   \[**REQUIRED**\]
    *   The root device of the _controls_ hierarchy in CCDB
    *   `--device=VacS-ACCV:Vac-PLC-01001`
*   **--template list of templates**
    *   \[**REQUIRED** _if not using any plc options_\]
    *   The list of templates to process
    *   `--template EPICS-DB TIA-MAP MY-SPECIAL-TEMPLATE`
*   **--ccdb=<directory_of_ccdb_dump_OR_path_to_.ccdb.zip>**
    *   \[OPTIONAL\]
    *   Use the specified CCDB-dump of _device_ instead of connecting to the CCDB database
    *   `--ccdb=VacS-ACCV_Vac-PLC-01001.ccdb.zip`
    *   `--ccdb=modules/m-epics-vacs-accv_vac-plc-01001/misc/ccdb`
*   **--ccdb-test**
    *   \[OPTIONAL\]
    *   Use the test version of the CCDB database
*   **--ccdb-production**
    *   \[OPTIONAL\]
    *   Use the production version of the CCDB database. This is the default.
*   **--zip**=<created_zip_file>
    *   \[OPTIONAL\]
    *   Create a zip file containing the generated files. The default file name is derived from _device_
    *   `--zip`
    *   `--zip=foobar.zip`
*   **--tag=<tag_name>**
    *   \[OPTIONAL\]
    *   Used to select the correct template if more than one template was found
    *   `--tag=mps` will match
        *    template filenames like `*TEMPLATE__mps_<TEMPLATE-NAME>.txt`
        *    Interface Definition filenames like `*__mps.def`
        *    Interface Definition URLs with name `EPI__mps`
*   **--epi-version=<version>**
    *   \[OPTIONAL\]
    *   Used to select a version of EPI repositories other than `master`. Please note: it overrides any `EPI VERSION` property specified in CCDB
    *   `--epi-version=v4.0.1`
*   **--output=<directory>**
    *   \[OPTIONAL\]
    *   Used to control the location of the generated files. The default is `output/<devicename>` in the current directory
    *   `--output=my_output`   will save everything to `my_output`
    *   `--output=+my_device`  will save everything to `output/my_device`
    *   `--output=my_output+`  will save everything to `my_output/<devicename>`

## EPICS-PLC integration

PLC Factory is capable of integrating (and generating code for) the following PLC types:

*   **Siemens SIMATIC S7-1200 / S7-1500** (selected with the `--plc-siemens` option)

    *   _TIA Portal v13_
    *   _TIA Portal v14_
    *   _TIA Portal v15_
    *   _TIA Portal v15.1_

*   **Beckhoff** (selected with the `--plc-beckhoff` option)

    *   _TwinCAT 3_

#### Options related to EPICS-PLC integration

*   **--plc-siemens**=<tia_version>
    *   \[OPTIONAL\]
    *   Generate the EPICS db, the communication and the data (de)serialization PLC code for the specified TIA version. The default version is _TIA Portal v15.1_
    *   `--plc-siemens`
    *   `--plc-siemens=13`
*   **--plc-interface**=<tia_version>
    *   same as **--plc-siemens**
*   **--plc-beckhoff**
    *   \[OPTIONAL\]
    *   Generate the EPICS db, the communication and data (de)serialization PLC code for TwinCAT 3 (Diagnostics is not yet supported)
    *   `--plc-beckhoff`
*   **--plc-opc**
    *   \[OPTIONAL\]
    *   Generate the EPICS db for OPC UA using the opcua device support
    *   `--plc-opc`
*   **--plc-diag**
    *   \[OPTIONAL\]
    *   Generate diagnostics PLC code
    *   `--plc-diag`
*   **--plc-no-diag**
    *   \[OPTIONAL\]
    *   Do not generate diagnostics PLC code. This is the default
    *   `--plc-no-diag`
*   **--plc-only-diag**
    *   \[OPTIONAL\]
    *   Only diagnostics PLC code is generated
    *   `--plc-only-diag`
*   **--plc-test**
    *   \[OPTIONAL\]
    *   Generate PLC communication testing code
    *   `--plc-test`
*   **--plc-no-test**
    *   \[OPTIONAL\]
    *   Do not generate PLC communication testing code. This is the default
    *   `--plc-no-test`
*   **--plc-readonly**
    *   \[OPTIONAL\]
    *   Do not allow command or parameter blocks in the PLC. Modbus will still be enabled to exchange the hash and heartbeat.
    *   `--plc-readonly`
*   **--eee**=<module_name>
    *   \[OPTIONAL\]
    *   Generate a proper EEE module. If not specified, the module name is taken from the _EPICSModule_ property of _device_ with a fallback to being derived from _device_ and of course prefixed with m-epics. The name of the snippet follows a similar algorithm; taken from the _EPICSSnippet_ property and falls back to being derived from the module name. Implicitly adds _EPICS-DB_, _AUTOSAVE-ST-CMD_, and _AUTOSAVE_ to the list of templates (which means you don't have to add any templates explicitly)
    *   `--eee`
    *   `--eee=my-module`
    *   `--eee=m-epics-my-module`
*   **--e3**=<module_name>
    *   \[OPTIONAL\] \[EXPERIMENTAL\]
    *   Generate a proper E3 module. If not specified, the module name is taken from the _EPICSModule_ property of _device_ with a fallback to being derived from _device_ and of course prefixed with e3. The name of the snippet follows a similar algorithm; taken from the _EPICSSnippet_ property and falls back to being derived from the module name. Implicitly adds _EPICS-DB_, _AUTOSAVE-ST-CMD_, and _AUTOSAVE_ to the list of templates (which means you don't have to add any templates explicitly)
    *   `--e3`
    *   `--e3=my-module`
    *   `--e3=e3-my-module`
*   **--root=<prefix>**
    *   \[OPTIONAL\]
    *   Change the root prefix in the generated EPICS db from _device_ to the specified string.
    *   `--root=my-root`
    *   `--root='$(ROOT_PREFIX)'`

One of `--plc-siemens`, `--plc-beckhoff`, or `--plc-opc` is required for EPICS-PLC integration. These options implicitly adds _EPICS-DB_, _IFA_, and the proper _TIA-MAP_ to the list of templates (which means you don't have to add any templates explicitly).

The information on what is exchanged between EPICS and a PLC is defined in so-called **Interface Definition** files. For further information, please see [template_factory](template_factory/)

#### Assigning Interface Definition files to devices

Assigning Interface Definitions happens on the _device type_-level in CCDB. Every device that belongs to the same device type has the same Interface Definition. There are 2 distinct ways of assigning:

*   Upload the Interface Definition file as an _Artifact_ of the _device type_. The only restriction is that the file must have a **.def** extension.
*   Upload the Interface Definition file to a Git repository (only Bitbucket and GitLab has been tested so far) and add the URL to the repository as an _External Link_ to the _device type_ and use **EPI** as the link name. By default PLCFactory constructs the filename to download as follows:
    *    takes the name of the _device type_
    *    in all uppercase
    *    changes reserved characters (**<**, **>**, **:**, **"**, **/**, **\\**, **|**, **?**, **\***) to **_**
    *    appends **.def**

    It is possible to explicitly specify the filename (and path relative to the repository top) in square brackets after _EPI_; **EPI[file-to-download]**. The file must still have a **.def** extension (although it is automatically appended if not already specified). This technique can be used to share the same Interface Definition across device types.
    If the link specified with **EPI** has a _.git_ extension then the repository will be cloned. Otherwise the definition files will be individually downloaded (by appending /raw/<branch> to the URL).
    It is possible to specify a version of the .def file to use other than _master_ with the **EPI VERSION** property (either on _slot_ or _device type_ level).
    Authentication for GitLab is only supported if using the git clone method.

#### Built-in templates / output types

The following output types can be automatically generated from **Interface Definition** files (with the -t option):

*   DEVICE-LIST
    *    The list of devices that were processed. Always generated.
    *    `<device>-template-DEVICE-LIST-<timestamp>.txt`
*   README
    *    A README.md about the devices that were processed. Always generated.
    *    `<device>-template-README-<timestamp>.md`
*   ARCHIVE
    *    The list of PVs that has to be archived. Can be added to the archiver repository: `https://gitlab.esss.lu.se/ics-infrastructure/epicsarchiver-config.git`
    *    `<device>-template-ARCHIVE-<timestamp>.archive`
*   BOB
    *    A Display Builder OPI for the PLC. It is only really usable for small projects right now (few devices with few signals)
    *    `<device>-template-BOB-<timestamp>.bob`
*   BEAST
    *    A BeastFactory .alarms file. Automatically generated for PLCs and EPICS modules
    *    `<device>-template-BEAST-<timestamp>.alarms`
*   BEAST-TEMPLATE
    *    A BeastFactory .alarms-template file. Automatically generated for PLCs and EPICS modules
    *    `<device>-template-BEAST-TEMPLATE-<timestamp>.alarms-template`
*   OPC-MAP.XLS
    *    If the `openpyxl` package is installed (`sudo pip2 install openpyxl`) an Excel sheet is generated (by default with `--plc-opc`) with a mapping between EPICS PV names and PLC datablock-tag names
    *    `<device>-template-OPC-MAP.XLS-<timestamp>.xlsx`
