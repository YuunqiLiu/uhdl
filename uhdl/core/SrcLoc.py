"""Source locations: which line of the user's Python code made a signal, assignment or instance.

capture() walks up the call stack past UHDL's own frames (and the standard library's) and returns
(file, line) of the first user frame. Signals record where they were placed in a component
(`_src`), assignments record where they were written (`_rvalue_src`, a tuple of locations), and
UHDL errors use these to say where the problem is in the user's code. generate() also writes
them into the Verilog as comments, so a simulator or lint message can be traced back.

Errors found after circuit() (latches, slice coverage, CDC, ...) are "deferred": the stack then
no longer points at the cause, so capture() returns None inside deferred() and those errors name
the recorded locations explicitly.
"""
import contextlib
import linecache
import os
import sys
import sysconfig

_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
_STD = os.path.abspath(sysconfig.get_paths()['stdlib']) + os.sep
_SITE = tuple(os.path.abspath(p) + os.sep for p in {sysconfig.get_paths()['purelib'], sysconfig.get_paths()['platlib']})

_state = {'defer': 0, 'override': [], 'comments': 0}


def _internal(fn):
    if fn.startswith(_PKG) or fn.startswith('<frozen'):
        return True
    return fn.startswith(_STD) and not fn.startswith(_SITE)


def capture():
    '''(file, line) of the innermost user frame, or None (inside deferred() or with no user frame).'''
    if _state['override']:
        o = _state['override'][-1]
        return o[0] if o else None
    if _state['defer']:
        return None
    f = sys._getframe(1)
    while f is not None:
        fn = f.f_code.co_filename
        if not _internal(os.path.abspath(fn) if not os.path.isabs(fn) else fn):
            return (fn, f.f_lineno)
        f = f.f_back
    return None


def assign_locs():
    '''Locations to record for an assignment being made now (a tuple, possibly empty).'''
    if _state['override']:
        return _state['override'][-1]
    loc = capture()
    return (loc,) if loc else ()


@contextlib.contextmanager
def deferred():
    '''Checks run after the user's code: errors carry the recorded locations instead of the stack.'''
    _state['defer'] += 1
    try:
        yield
    finally:
        _state['defer'] -= 1


@contextlib.contextmanager
def assigned_at(locs):
    '''Assignments made inside record `locs` (a tuple of locations) as where they were written.'''
    _state['override'].append(tuple(l for l in locs if l))
    try:
        yield
    finally:
        _state['override'].pop()


@contextlib.contextmanager
def errors_at(locs):
    '''A UHDL error raised inside without a location of its own gets `locs`.'''
    try:
        yield
    except Exception as e:
        if hasattr(e, '_uhdl_locs') and not e._uhdl_locs:
            e._uhdl_locs = [l for l in locs if l]
        raise


def path(fn):
    '''A file name as shown to the user: relative to the working directory when inside it.'''
    try:
        rel = os.path.relpath(fn)
    except ValueError:
        return fn
    return fn if rel.startswith('..') else rel


def fmt(loc, code=True):
    '''"file:line: source text" (or just "file:line").'''
    if not loc:
        return '<unknown location>'
    fn, line = loc
    s = '%s:%d' % (path(fn), line)
    if code:
        text = linecache.getline(fn, line).strip()
        if text:
            s += ': ' + text
    return s


def short(locs, limit=6):
    '''Compact list for a Verilog comment: "a.py:3,7 b.py:12".'''
    by_file, order = {}, []
    for l in locs or ():
        if not l:
            continue
        if l[0] not in by_file:
            by_file[l[0]] = []
            order.append(l[0])
        if l[1] not in by_file[l[0]]:
            by_file[l[0]].append(l[1])
    parts, n = [], 0
    for fn in order:
        lines = by_file[fn][:max(limit - n, 0)]
        n += len(lines)
        if lines:
            parts.append('%s:%s' % (os.path.basename(fn), ','.join(str(x) for x in lines)))
    more = sum(len(v) for v in by_file.values()) - n
    return ' '.join(parts) + (' ...' if more > 0 else '')


def of(obj):
    '''Where `obj` was written: its assignments if it has any, else where it was declared.'''
    locs = tuple(getattr(obj, '__dict__', {}).get('_rvalue_src') or ())
    if not locs:
        d = getattr(obj, '__dict__', {}).get('_src')
        locs = (d,) if d else ()
    return locs


def decl(obj):
    return getattr(obj, '__dict__', {}).get('_src')


def named(obj, name=None):
    '''"top.u.x (file:line)" for messages.'''
    if name is None:
        try:
            name = obj.full_hier
        except Exception:
            name = str(obj)
    l = decl(obj) or (of(obj) or (None,))[0]
    return '%s (%s)' % (name, fmt(l, code=False)) if l else name


@contextlib.contextmanager
def verilog_comments():
    _state['comments'] += 1
    try:
        yield
    finally:
        _state['comments'] -= 1


def comments_on():
    return _state['comments'] > 0


def tag(lines, locs):
    '''Append "// file:line" to the first line of a Verilog statement when comments are on.'''
    if not lines or not _state['comments']:
        return lines
    s = short(locs)
    if not s:
        return lines
    return ['%s // %s' % (lines[0], s)] + list(lines[1:])
