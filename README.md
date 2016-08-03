# PLC Factory
(c) 2016 European Spallation Source, Lund


PLC Factory is intended to simplify programming PLCs by automatically generating template files. It takes an arbitrary device and template name as input and processes the corresponding sub-tree of devices according to their entries in CCDB.

## Quickstart

Sample invocation:
`python plcfactory.py --device LNS-LEBT-010:Vac-PLC-11111 --template EPICS-DB`

With shorthands:
`python plcfactory.py -d LNS-LEBT-010:Vac-PLC-11111 -t EPICS-DB`

The resulting output file will be written to `\output`.


For further information, see `\doc`.
