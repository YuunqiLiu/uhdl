Import Verilog
=================

Environment settings
--------------------

Before importing verilog, we need to install an open source project slang, which is a system verilog compiler that UHDL uses to parse the verilog and generate the syntax tree. The project path for slang is here.

If you are currently using an environment where module environments are configured and slang environments are set up. You can directly run

.. code-block:: shell

    module load slang

or use

.. code-block:: shell

    module av

to see if there are similar modules.


Another way is to compile and install from the source code.

1. Get the source code from github.

.. code-block:: shell

    git clone https://github.com/MikePopoloski/slang.git

2. Switch the current directory and go to the slang directory.

.. code-block:: shell

    cd ./slang

3. Compile slang.

.. code-block:: shell

    cmake -B build
    cmake --build build

If there is an error in the above three steps, you can view a more detailed installation tutorial on the slang website.


4. Test if slang compiles successfully.

.. code-block:: shell

    ./build/bin/slang --version


If the above command runs successfully, the output will be:

.. code-block:: shell

    slang version 2.0.97+5ee5382c

5. add . /build/bin to the environment variable PATH



Import a simple verilog module
------------------------------


In this example, we first define a very simple verilog module "adder" as follows.

.. literalinclude :: example/case_import_v/adder.v
    :language: verilog


In UHDL, there exists a VComponent type, which is a black box used to represent a module written in verilog.

When instantiating a VComponent, you need to specify the path to the verilog file it will import, as well as the module name of the verilog.

After importing, the VComponent will be used exactly like a normal Component, except that UHDL will treat it as a black box that only recognizes and processes IO information and does not pay attention to any internal content.

An example of importing a Verilog file using VCompnent is as follows.

.. literalinclude :: example/case_import_v/adder_top.py
    :language: python


The execution of the above file results in the following. There is no difference between referencing a Verilog file and using a normal Component for the upper-level UHDL Component.


.. literalinclude :: generated_verilog/AdderTop/AdderTop.v
    :language: verilog
    :linenos:
    :lines: 33-51

Import a parameterized verlog module
------------------------------------

Further, this time we define a verilog module with parameters as follows.

.. literalinclude :: example/case_import_v/adder_param.v
    :language: verilog


For VComponent imported with a verilog parameter, you can modify the default value by passing in an input with the same name as the verilog parameter before instantiating.


.. literalinclude :: example/case_import_v/adder_param_top.py
    :language: python


The results are as follows.



.. literalinclude :: generated_verilog/AdderParamTop_WIDTH_64/AdderParamTop_WIDTH_64.v
    :language: verilog
    :linenos:
    :lines: 33-51


VComponent does not check any of the input parameters, it just converts all of them to strings and uses them for.

1. configure the verilog compiler slang and generate the AST.
2. Passing incoming parameter values to the verilog module at instantiation time.


Import a module with struct ports
---------------------------------

UHDL supports importing SystemVerilog modules that use ``typedef struct packed`` ports.
When a module port's type is a packed struct defined via ``typedef`` in a package,
VComponent will automatically recognize the struct fields and create ``InputStructIO``
or ``OutputStructIO`` ports instead of flat bit vectors.

Consider the following SystemVerilog:

.. code-block:: systemverilog

    package mypkg;
        typedef struct packed {
            logic [3:0] a;
            logic signed [7:0] b;
            logic c;
        } my_struct_t;
    endpackage

    module struct_user (
        input  mypkg::my_struct_t  s_in,
        output mypkg::my_struct_t  s_out
    );
    assign s_out = s_in;
    endmodule

Importing in UHDL:

.. code-block:: python

    vc = VComponent(file='struct_ports.v', top='struct_user')
    # vc.s_in  is InputStructIO  with fields a(4), b(8, signed), c(1)
    # vc.s_out is OutputStructIO with the same struct type

    # Access fields via dot notation:
    ref_a = vc.s_in.a    # StructFieldRef, width 4
    ref_b = vc.s_in.b    # StructFieldRef, width 8, signed

**Struct mode control:**

- ``struct_mode='auto'`` (default): Struct typedef ports become ``InputStructIO``/``OutputStructIO``.
- ``struct_mode='packed'``: All ports become flat ``Input``/``Output`` with the packed bit width (backward compatible).

.. code-block:: python

    # Packed mode: flatten to bit vectors
    vc = VComponent(file='struct_ports.v', top='struct_user', struct_mode='packed')
    # vc.s_in is Input(UInt(13)), vc.s_out is Output(UInt(13))

**Type safety:**

Struct connections enforce strict typedef identity. Two struct ports can only be connected
if they share the same typedef name (e.g., ``mypkg::my_struct_t``). Ports with the same
bit layout but different typedef names will be rejected.

**Current limitations:**

- Struct InOut ports are not yet supported (planned for a future release).
- Nested structs and enum/union fields are imported as flat packed vectors.
- Array-of-struct ports are not yet supported.