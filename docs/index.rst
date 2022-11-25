.. ltool documentation master file, created by
   sphinx-quickstart on Thu Dec 12 16:07:48 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to UHDL's documentation!
=================================

Introduction
------------

UHDL is a hardware description language that is based on a python implementation and can be treated as a python package or a set of python APIs.

The product of UHDL is verilog.

It has following features:

1. Better flexibility than verilog, can support any form of input as parameters, even if it is a json or xlsx.

2. Interpretive language, immediately stop at the scene of an error.

3. Built-in lint, to ensure the quality of the output verilog.

4. Output highly readable verilog.
5. Unrestricted use of python's native control structures to manipulate circuit elements.



.. toctree::
   :maxdepth: 1
   :caption: Contents
   :titlesonly:
   :hidden:
   
   install_uhdl.rst
   first_module.rst
   basic_syntax.rst
   import_verilog.rst



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
