"""
Type descriptors for UHDL composite types (struct, enum, union).

This module defines the type kernel hierarchy and their associated
Constant-like wrappers used as port attributes:

    TypeKernel (base)
    ├── StructType   →  StructConstant
    ├── EnumType     →  EnumConstant
    └── UnionType    →  UnionConstant
"""

from collections import OrderedDict


################################################################################################################
#
#   TypeKernel – base class for all composite type descriptors
#
################################################################################################################

class TypeKernel:
    """Base class for unified type descriptors (StructType, EnumType, UnionType)."""

    def _derive_package(self, name, package):
        if package is None and name and '::' in name:
            return name.split('::')[0]
        return package

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, type(self)):
            return False
        if self.name and other.name:
            return self.name == other.name
        if self.name is None and other.name is None:
            return self._schema_eq(other)
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.__class__.__name__, self.name, self._width))

    @classmethod
    def get_or_create(cls, name, *args, **kwargs):
        if name and name in cls._registry:
            return cls._registry[name]
        obj = cls(name, *args, **kwargs)
        if name:
            cls._registry[name] = obj
        return obj

    @classmethod
    def clear_registry(cls):
        cls._registry.clear()


class TypedConstant:
    """Base class for Constant-like wrappers used as attributes of IO ports."""

    @property
    def width(self):
        return self._type_obj.width

    @property
    def attribute(self):
        return self

    @property
    def template(self):
        return self

    def rstring(self, lvalue):
        return "%s'b%s" % (self.width, '0' * self.width)

    @property
    def lstring(self):
        raise NotImplementedError

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self._type_obj == other._type_obj
        if hasattr(other, 'width') and not isinstance(other, type(self)):
            return False
        return NotImplemented

    def __ne__(self, other):
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return eq
        return not eq

    def __hash__(self):
        return hash((self.__class__.__name__, self._type_obj))

    def __str__(self):
        name = self._type_obj.name or 'anon'
        return f"{self.__class__.__name__}({name}, {self.width})"


################################################################################################################
#
#   StructType – unified type kernel for struct support
#
################################################################################################################

class StructType(TypeKernel):
    """Unified type descriptor for packed structs.

    Every struct value (port, wire, expression) that carries struct semantics
    shares a *single* ``StructType`` instance so that identity comparison
    (``is``) can be used to enforce strict‑same‑typedef checking.

    Attributes:
        name:       Canonical typedef name, e.g. ``'mypkg::my_struct_t'``.
                    ``None`` for anonymous inline structs.
        fields:     ``OrderedDict[str, dict]`` preserving declaration order.
                    Each value is ``{'width': int, 'signed': bool, 'offset': int,
                    'struct_type': StructType | None}``.
        width:      Total packed width (sum of all field widths).
        package:    Package scope name, or ``None``.
    """

    # Global registry: canonical name -> StructType singleton
    _registry: dict = {}

    def __init__(self, name, fields, package=None):
        """
        Args:
            name:    Typedef name (may include ``pkg::`` prefix) or ``None``.
            fields:  OrderedDict or list of ``(field_name, info_dict)`` pairs.
                     Each *info_dict* must have ``'width'`` and ``'signed'`` keys,
                     and optionally ``'struct_type'`` for nested structs.
            package: Explicit package name (derived from *name* if omitted).
        """
        self.name = name
        if isinstance(fields, OrderedDict):
            self.fields = fields
        elif isinstance(fields, list):
            self.fields = OrderedDict(fields)
        else:
            self.fields = OrderedDict(fields)
        self.package = self._derive_package(name, package)
        # Compute per‑field bit offset (MSB‑first / packed order) and total width
        offset = 0
        for fname, finfo in reversed(list(self.fields.items())):
            finfo.setdefault('offset', offset)
            offset += finfo['width']
        self._width = sum(f['width'] for f in self.fields.values())
    @property
    def width(self):
        return self._width

    def _schema_eq(self, other):
        """Deep schema comparison for anonymous structs."""
        if list(self.fields.keys()) != list(other.fields.keys()):
            return False
        for k in self.fields:
            a, b = self.fields[k], other.fields[k]
            if a['width'] != b['width'] or a['signed'] != b['signed']:
                return False
            ast = a.get('struct_type')
            bst = b.get('struct_type')
            if ast != bst:
                return False
        return True

    def __repr__(self):
        return f"StructType({self.name!r}, width={self._width}, fields={list(self.fields.keys())})"


class StructConstant(TypedConstant):
    """A Constant-like wrapper used as the ``attribute`` of StructIO ports.

    It carries both the packed bit-width *and* the StructType so that
    ``attribute == attribute`` still works for non-struct comparisons while
    struct-aware code can inspect ``.struct_type``.
    """

    def __init__(self, struct_type: StructType, base_type_cls=None):
        # base_type_cls: UInt or SInt – determines the Verilog signedness
        self._type_obj = struct_type
        self._base_cls = base_type_cls  # lazily resolved after Bits/UInt/SInt defined

    @property
    def struct_type(self):
        return self._type_obj

################################################################################################################
#
#   EnumType – unified type kernel for enum support
#
################################################################################################################

class EnumType(TypeKernel):
    """Unified type descriptor for SystemVerilog enums.

    Every enum value (port, wire, expression) that carries enum semantics
    shares a *single* ``EnumType`` instance so that identity comparison
    (``is``) can be used to enforce strict-same-typedef checking.

    Attributes:
        name:       Canonical typedef name, e.g. ``'pkg::state_t'``.
                    ``None`` for anonymous inline enums.
        members:    ``OrderedDict[str, int]`` preserving declaration order.
                    Maps member name to integer value.
        width:      Bit width of the enum's base type.
        signed:     Whether the enum's base type is signed.
        package:    Package scope name, or ``None``.
    """

    # Global registry: canonical name -> EnumType singleton
    _registry: dict = {}

    def __init__(self, name, members, width, signed=False, package=None):
        """
        Args:
            name:    Typedef name (may include ``pkg::`` prefix) or ``None``.
            members: OrderedDict or list of ``(member_name, int_value)`` pairs.
            width:   Bit width of the underlying type.
            signed:  Whether the base type is signed.
            package: Explicit package name (derived from *name* if omitted).
        """
        self.name = name
        if isinstance(members, OrderedDict):
            self.members = members
        elif isinstance(members, list):
            self.members = OrderedDict(members)
        else:
            self.members = OrderedDict(members)
        self._width = width
        self.signed = signed
        self.package = self._derive_package(name, package)
    @property
    def width(self):
        return self._width

    # ---------- member access ----------
    def __getattr__(self, name):
        """Allow ``enum_type.MEMBER_NAME`` to get the integer value."""
        if name.startswith('_'):
            raise AttributeError(name)
        members = object.__getattribute__(self, 'members')
        if name in members:
            return members[name]
        raise AttributeError(f"EnumType {self.name!r} has no member {name!r}. "
                             f"Available: {list(members.keys())}")

    def __contains__(self, name):
        """Check if a member name exists: ``'IDLE' in enum_type``."""
        return name in self.members

    def __iter__(self):
        """Iterate over (member_name, value) pairs."""
        return iter(self.members.items())

    def __len__(self):
        return len(self.members)

    def _schema_eq(self, other):
        """Deep schema comparison for anonymous enums."""
        if self._width != other._width or self.signed != other.signed:
            return False
        return list(self.members.items()) == list(other.members.items())

    def __repr__(self):
        return f"EnumType({self.name!r}, width={self._width}, members={list(self.members.keys())})"

class EnumConstant(TypedConstant):
    """A Constant-like wrapper used as the ``attribute`` of EnumIO ports.

    It carries both the packed bit-width *and* the EnumType so that
    ``attribute == attribute`` still works for non-enum comparisons while
    enum-aware code can inspect ``.enum_type``.
    """

    def __init__(self, enum_type: 'EnumType'):
        self._type_obj = enum_type

    @property
    def enum_type(self):
        return self._type_obj


################################################################################################################
#
#   UnionType – unified type kernel for packed union support
#
################################################################################################################

class UnionType(TypeKernel):
    """Unified type descriptor for SystemVerilog packed unions.

    Every union value (port, wire, expression) that carries union semantics
    shares a *single* ``UnionType`` instance so that identity comparison
    (``is``) can be used to enforce strict-same-typedef checking.

    Attributes:
        name:       Canonical typedef name, e.g. ``'pkg::my_union_t'``.
                    ``None`` for anonymous inline unions.
        fields:     ``OrderedDict[str, dict]`` preserving declaration order.
                    Each value is ``{'width': int, 'signed': bool,
                    'struct_type': StructType | None, 'enum_type': EnumType | None}``.
        width:      Total packed width (= max of all field widths for packed union).
        package:    Package scope name, or ``None``.
    """

    # Global registry: canonical name -> UnionType singleton
    _registry: dict = {}

    def __init__(self, name, fields, package=None):
        """
        Args:
            name:    Typedef name (may include ``pkg::`` prefix) or ``None``.
            fields:  OrderedDict or list of ``(field_name, info_dict)`` pairs.
                     Each *info_dict* must have ``'width'`` and ``'signed'`` keys.
            package: Explicit package name (derived from *name* if omitted).
        """
        self.name = name
        if isinstance(fields, OrderedDict):
            self.fields = fields
        elif isinstance(fields, list):
            self.fields = OrderedDict(fields)
        else:
            self.fields = OrderedDict(fields)
        self.package = self._derive_package(name, package)
        # Width is the max of all field widths for a packed union
        self._width = max(f['width'] for f in self.fields.values()) if self.fields else 0
    @property
    def width(self):
        return self._width

    def _schema_eq(self, other):
        """Deep schema comparison for anonymous unions."""
        if list(self.fields.keys()) != list(other.fields.keys()):
            return False
        for k in self.fields:
            a, b = self.fields[k], other.fields[k]
            if a['width'] != b['width'] or a['signed'] != b['signed']:
                return False
            ast = a.get('struct_type')
            bst = b.get('struct_type')
            if ast != bst:
                return False
        return True

    def __repr__(self):
        return f"UnionType({self.name!r}, width={self._width}, fields={list(self.fields.keys())})"

class UnionConstant(TypedConstant):
    """A Constant-like wrapper used as the ``attribute`` of UnionIO ports.

    It carries both the packed bit-width *and* the UnionType so that
    ``attribute == attribute`` still works for non-union comparisons while
    union-aware code can inspect ``.union_type``.
    """

    def __init__(self, union_type: 'UnionType'):
        self._type_obj = union_type

    @property
    def union_type(self):
        return self._type_obj
