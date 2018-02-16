# PLC Factory
(c) 2016-2018 European Spallation Source, Lund
Author: Gregor Ulm, Krisztian Loki, Miklos Boros

PLC Factory is intended to simplify programming PLCs and creating the communication interface between EPICS and a PLC. It takes an arbitrary device and a list of template ids as input and processes the corresponding sub-tree of devices according to their entries in CCDB.

## Quickstart

PLC Factory requires Python 2.7.

Automaticly generate the PLC block and the corresponding IOC from CCDB using .def files. The .def files are linked to the CCDB device types.

Generate TIAv14 blocks with IOC:
`python plcfactory.py -d CrS-CMS:Cryo-PLC-01 --plc=14 --eee`

Using manually created plcFactory templates:

Invocation follows the pattern `python plcfactory.py --device <device> --template <ids>`, where `ids` is a list of template names of at least one element.

Sample invocation:
`python plcfactory.py --device LNS-LEBT-010:Vac-PLC-11111 --template EPICS-DB TIA-MAP`

With shorthands:
`python plcfactory.py -d LNS-LEBT-010:Vac-PLC-11111 -t EPICS-DB TIA-MAP`

The resulting output file will be written to `\output`.

For further information, see `\doc`.
