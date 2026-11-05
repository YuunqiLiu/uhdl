"""Structured values and valid/ready streams.

Struct: named fields packed into one vector (first field = most significant bits).

    Flit = Struct(last=1, dst=4, data=32)          # Flit.width == 37
    w = s.wire('w', Flit.pack(last=l, dst=d, data=x))
    Flit(w).dst                                     # w[35:32]
    Flit(r).dst += d                                # drive one field of a signal (see partial assignment)

Stream: a valid/ready interface with a payload (an int width or a Struct).

    s.ep = s.stream_in('ep0_in', Flit, domain=clk)  # ports ep0_in_vld, ep0_in_rdy, ep0_in_last/dst/data
    fifo.w += s.ep                                  # vld and payload forward, rdy back
    core_lane = Stream.of(s.core, 'l_in', Flit, lane=e)
    core_lane += fifo.r
    hs = s.ep.fire                                  # vld & rdy
"""
from collections import OrderedDict
from .UHDLException import ErrUHDLStr


class Struct:
    def __init__(self, **fields):
        if not fields:
            raise ErrUHDLStr('Struct() needs at least one field.')
        self._fields = OrderedDict()
        for n, w in fields.items():
            if isinstance(w, Struct):
                pass
            elif not isinstance(w, int) or isinstance(w, bool) or w < 1:
                raise ErrUHDLStr('Struct field %s: width must be a positive int or a Struct, got %r' % (n, w))
            self._fields[n] = w
        # bit offsets: the last field is at the bottom
        self._lsb, pos = {}, 0
        for n in reversed(list(self._fields)):
            self._lsb[n] = pos
            pos += self.field_width(n)
        self._width = pos

    @property
    def width(self):
        return self._width

    @property
    def fields(self):
        return list(self._fields)

    def field_width(self, n):
        w = self._fields[n]
        return w.width if isinstance(w, Struct) else w

    def field_type(self, n):
        return self._fields[n]

    def bounds(self, n):
        if n not in self._fields:
            raise ErrUHDLStr('Struct has no field "%s"; fields are %s.' % (n, ', '.join(self._fields)))
        lo = self._lsb[n]
        return lo + self.field_width(n) - 1, lo

    def pack(self, **values):
        """Concatenate field values (signals or ints) into one vector, first field on top."""
        from .Variable import UInt, _lit
        from .Operator import Combine
        missing = [n for n in self._fields if n not in values]
        extra = [n for n in values if n not in self._fields]
        if missing or extra:
            raise ErrUHDLStr('Struct.pack: %s%s' % ('missing ' + ', '.join(missing) if missing else '',
                                                    ('; unknown ' + ', '.join(extra)) if extra else ''))
        parts = []
        for n in self._fields:
            v = values[n]
            if isinstance(v, StructView):
                v = v.bits
            v = _lit(v, UInt(self.field_width(n)), 'Struct field %s' % n)
            if v.attribute.width != self.field_width(n):
                raise ErrUHDLStr('Struct.pack: field %s is %d bits, got a %d-bit value.'
                                 % (n, self.field_width(n), v.attribute.width))
            parts.append(v)
        return Combine(*parts)

    def __call__(self, x):
        """View a signal or expression as this struct: Flit(x).dst."""
        if isinstance(x, StructView):
            x = x.bits
        if x.attribute.width != self._width:
            raise ErrUHDLStr('Cannot view a %d-bit value as a %d-bit Struct.' % (x.attribute.width, self._width))
        return StructView(self, x)

    def __repr__(self):
        return 'Struct(%s)' % ', '.join('%s=%r' % kv for kv in self._fields.items())


class StructView:
    """A struct-typed view of a vector. Fields are slices; assigning a field with += drives that slice."""

    def __init__(self, struct, bits):
        object.__setattr__(self, '_struct', struct)
        object.__setattr__(self, '_bits', bits)

    @property
    def bits(self):
        return self._bits

    @property
    def struct(self):
        return self._struct

    def __getattr__(self, n):
        st = object.__getattribute__(self, '_struct')
        if n.startswith('_') or n not in st._fields:
            raise AttributeError(n)
        h, l = st.bounds(n)
        x = object.__getattribute__(self, '_bits')[h:l]
        t = st.field_type(n)
        return StructView(t, x) if isinstance(t, Struct) else x

    def __setattr__(self, n, v):
        # `view.f += x` ends in setattr(view, 'f', <the slice>); the slice already recorded the driver.
        if getattr(v, '_uhdl_part_assigned', False) or isinstance(v, StructView):
            return
        raise ErrUHDLStr('Assign a struct field with +=, e.g. Flit(sig).%s += value.' % n)


# ---------------------------------------------------------------------------- streams

class Stream:
    """vld / rdy plus a payload. The payload is either one signal (`data`) or one signal per
    struct field (`fields`). Build one with Stream.of(), s.stream_in(), s.stream_out(),
    s.stream_wire(), or the .w / .r of an AsyncFifo."""

    def __init__(self, vld, rdy, data=None, fields=None, struct=None):
        if (data is None) == (fields is None):
            raise ErrUHDLStr('Stream needs either data or fields.')
        self.vld, self.rdy, self.struct = vld, rdy, struct
        self._data, self.fields = data, fields

    # ---- payload access
    @property
    def data(self):
        """The payload as one vector (struct fields packed, first field on top)."""
        if self._data is not None:
            return self._data
        return self.struct.pack(**self.fields)

    @property
    def payload(self):
        """The payload as a StructView when the stream has a Struct, else the vector."""
        if self.struct is None:
            return self.data
        if self.fields is not None:
            return _FieldsView(self.struct, self.fields)
        return self.struct(self._data)

    def field(self, n):
        if self.fields is not None:
            if n not in self.fields:
                raise ErrUHDLStr('Stream has no field "%s".' % n)
            return self.fields[n]
        if self.struct is None:
            raise ErrUHDLStr('Stream has no struct payload, so it has no field "%s".' % n)
        return getattr(self.struct(self._data), n)

    @property
    def fire(self):
        """vld & rdy: a transfer happens this cycle."""
        return self.vld & self.rdy

    # ---- connection: dst += src
    def __iadd__(self, src):
        if not isinstance(src, Stream):
            raise ErrUHDLStr('A Stream can only be connected to a Stream (dst += src).')
        self.vld += src.vld
        if self.fields is not None:
            for n, sig in self.fields.items():
                sig += src.field(n)
        else:
            want = self._data.attribute.width
            v = src.data
            if v.attribute.width != want:
                raise ErrUHDLStr('Stream payloads differ in width: %d vs %d.' % (want, v.attribute.width))
            self._data += v
        src.rdy += self.rdy
        return self

    # ---- construction
    @staticmethod
    def of(comp, prefix, payload=None, lane=None):
        """The stream formed by comp's ports <prefix>_vld, <prefix>_rdy and either
        <prefix>_data or one <prefix>_<field> per field of the Struct `payload`.
        lane=i takes lane i of flat vectors (vld is N bits, each field N times its width)."""
        def get(n):
            if not hasattr(comp, n):
                raise ErrUHDLStr('%s has no port "%s".' % (type(comp).__name__, n))
            return getattr(comp, n)
        vld, rdy = get(prefix + '_vld'), get(prefix + '_rdy')
        struct = payload if isinstance(payload, Struct) else None
        if struct is not None and all(hasattr(comp, '%s_%s' % (prefix, f)) for f in struct.fields):
            fields = OrderedDict((f, get('%s_%s' % (prefix, f))) for f in struct.fields)
            data = None
        else:
            fields, data = None, get(prefix + '_data')
        if lane is not None:
            n = vld.attribute.width
            if not 0 <= lane < n:
                raise ErrUHDLStr('lane %d out of range: %s_vld has %d lanes.' % (lane, prefix, n))
            vld, rdy = vld[lane], rdy[lane]
            if fields is not None:
                fields = OrderedDict((f, s.split(n)[lane]) for f, s in fields.items())
            else:
                data = data.split(n)[lane]
        return Stream(vld, rdy, data=data, fields=fields, struct=struct)


class _FieldsView:
    def __init__(self, struct, fields):
        self._struct, self._f = struct, fields

    def __getattr__(self, n):
        if n.startswith('_'):
            raise AttributeError(n)
        return self._f[n]

    @property
    def bits(self):
        return self._struct.pack(**self._f)
