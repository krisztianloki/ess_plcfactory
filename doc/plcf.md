# PLCF Language

The PLCF Language (PLCF#) is a simple embedded domain-specific language for use in template files. It has successfully been used with template files that generate TIA Portal files as well as EPICS database records. The main purpose of PLCF# is to name properties, which will be substituted with corresponding values from CCDB, and perform simple operations on those properties.


## Format

The general format of an expression in PLCF# is `[PLCF# <expression> ]`.

A simple example is `[PLCF# PropertyInteger02 + 1 ]`. In this case, CCDB is used to resolve the reference to `PropertyInteger02` of the given device, and add `1` to it.

In general, PLCF# expressions are valid Python expressions, with the addition of a limited number of keywords, which are specified further below, calls to user-defined functions, and properties, which need to refer to entries in CCDB.

Basic sanity checks are included:

 - an opening square bracket has to be followed by a closing square bracket
 - parentheses need to match

In general, though, it is the responsibility of the user who creates template files to ensure that PLCF# expressions are syntactically and semantically valid.


## Keywords

Keywords are reserved terms. Currently, PLCF# has the following keywords:

- `INSTALLATION_SLOT`
- `TEMPLATE`
- `TIMESTAMP`
- `DEVICE_TYPE`
- `Counter`
- `Counter<N>`

Currently, PLCF# recognises `Counter1` up to and including `Counter9`. In case you need to use more counters, modify the line `numOfCounters = 9` in `plcfactory.py`.

## Inbuilt and user-defined functions

PLCF# is embedded in Python and thus standard Python functions can be called. To give a simple examples, which may not be realistic:

`[PLCF# abs(PropertyInteger02) + 1 ]`

The Python function `abs()` computes the absolute value of its argument. Assuming `PropertyInteger02` evaluates to `-2`, the result of evaluating the entire PLCF# expression is `3`.

In addition, users can define their own functions in the file `plcf_ext.py`. For instance, if that file contains a definition of the function `foo()`, it can be called in PLCF# as follows:

`[PLCF# ext.foo(PropertyInteger02) + 1 ]`



## References to higher levels in a device hierarchy

In a given hierarchy of devices it may be the case that a particular property of a device `X` needs to be re-used in a device `Y` that is at a lower level in the hierarchy. Instead of defining this property in CCDB for device `Y`, it is possible to reference to a top-level device in a template.

In order to indicate that a property value is to be taken from a device at a higher level in the hierarchy, put the property reference into parentheses, and suffix the resulting sub-expression with a `^`, which is to be read as 'up' and represents a stylised arrow that points upwards.

The general pattern is `[PLCF# ^(<property>) ]`, where `^(<property>)` evaluates to the value of a property. Note that technically a property itself is an expression, but it is not generally true that an expression can take the place of a property in the definition above. Thus, a definition like `^(Property01 + 2)` is invalid. Instead, the correct definition is `^(Property01) + 2`.


## Evaluation Order

An expression in PLCF# is evaluated in four distincts steps. We will follow a more complex and not necessarily realistic example for the purpose of illustration:

`[PLCF# ^(PropertyInteger02) + abs(PropertyInteger02 + 2 * 4) + Counter1 ]`


### Resolve references to properties in higher levels of the hierarchy

First, `^(PropertyInteger02)` expresses that the desired property does not refer to the current device `X`, but to a device higher up the hierarchy. Thus, an exhaustive search is initiated, which will continue until a device `Y` is found that is higher in the hierarchy and for which an entry `PropertyInteger02` exists in CCDB. Note that it is the responsibility of the user to ensure that a corresponding entry exists.

Assume said entry is `4`:

`[PLCF# 4 + abs(PropertyInteger02 + 2 * 4) + Counter1 ]`



### Replace all remaining properties with their corresponding values

Device `X` is assumed to have CCDB entries corresponding to all references. Those are resolved in the second step of the evaluation. Assume that `X` has a `PropertyInteger02` value of `1`:

`[PLCF# 4 + abs(1 + 2 * 4) + Counter1 ]`



### Evaluate counter variables

If the remaining PLCF# expression contains a counter variable, for instance `Counter1` or `Counter2`, then those variables are resolved. Afterwards, the entire expression is evaluated. If there are no counter variables, then the expression is evaluated as it is.

Assume the value for `Counter1` in our example is `10`, thus:
`[PLCF# 4 + abs(1 + 2 * 4) + 10 ]`


### Final evaluation

Lastly, the resulting expression is evaluated:

  `[PLCF# 4 + abs(1 + 2 * 4) + 10 ]`

= `[PLCF# 4 + abs(9)         + 10 ]`

= `[PLCF# 4 + 9              + 10 ]`

= `[PLCF# 23                      ]`

= `23`
