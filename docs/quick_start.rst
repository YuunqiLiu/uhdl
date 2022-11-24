Quick Start
============




First Module
--------------


Create a new python file, enter the following code and execute it.

.. literalinclude :: example/FirstComp.py
    :language: python


After executing the above file, a folder named "generated_verilog" will be created. In "generated_verilog/FirstComp_/FirstComp_.v", you can see the following generated verilog code:

.. literalinclude :: ../generated_verilog/FirstComp_/FirstComp_.v
    :language: verilog
    :linenos:
    :lines: 33-48


This is the verilog code that was generated through UHDL. It is a 1bit adder.
