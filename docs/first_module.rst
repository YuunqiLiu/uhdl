First Module
============



Create a new python file, enter the following code and execute it.

.. literalinclude :: example/FirstComp.py
    :language: python


After executing the above file, the following directory will be generated in the current working directory.

    docs/generated_verilog

Under the generated_verilog folder, the following files are generated.

    FirstComp/FirstComp.v

You can see the following generated verilog code in FirstComp.v:

.. literalinclude :: generated_verilog/FirstComp/FirstComp.v
    :language: verilog
    :linenos:
    :lines: 33-48


This is the verilog code that was generated through UHDL. It is a 1bit adder.
