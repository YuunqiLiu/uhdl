#!/usr/bin/env bash
# Prepare a Python with UHDL from the wheels bundled with this skill, offline.
# Prints the python path on stdout; all messages go to stderr.
#
#   PY=$(bash uhdl_env.sh)
#
# UHDL_PYTHON=<python>      base interpreter (default: the first Python >= 3.8 on PATH)
# UHDL_VENV=<dir>           where to create the environment
#                           (default: ~/.cache/uhdl-skill/<version>-py<X.Y>-<machine>)
# UHDL_ALLOW_NETWORK=1      let pip fetch pyslang from PyPI when the bundle has no wheel for this system
set -u

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SKILL=$(dirname "$HERE")
WHEELS="$SKILL/wheels"
VERSION=$(cat "$SKILL/VERSION" 2>/dev/null || echo dev)

say() { echo "[uhdl_env] $*" >&2; }
die() { say "ERROR: $*"; exit 1; }

[ -d "$WHEELS" ] || die "no wheels/ in $SKILL (this is the skill source, not a built bundle: run skill/build.py)"
UHDL_WHL=$(ls "$WHEELS"/uhdl-*.whl 2>/dev/null | head -1)
[ -n "$UHDL_WHL" ] || die "no uhdl wheel in $WHEELS"
UHDL_VER=$(basename "$UHDL_WHL" | cut -d- -f2)

# ---- 1. a base Python >= 3.8
ok_python() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; }
BASE=""
if [ -n "${UHDL_PYTHON:-}" ]; then
    ok_python "$UHDL_PYTHON" || die "UHDL_PYTHON=$UHDL_PYTHON is not a Python 3.8 or newer"
    BASE=$UHDL_PYTHON
else
    for c in python3 python3.14 python3.13 python3.12 python3.11 python3.10 python3.9 python3.8 python; do
        p=$(command -v "$c" 2>/dev/null) || continue
        if ok_python "$p"; then BASE=$p; break; fi
    done
    [ -n "$BASE" ] || die "no Python 3.8 or newer on PATH (found: $(for c in python3 python; do command -v $c; done | tr '\n' ' ')). Set UHDL_PYTHON."
fi
case "$BASE" in */*) BASE="$(cd "$(dirname "$BASE")" && pwd)/$(basename "$BASE")" ;; *) BASE=$(command -v "$BASE") ;; esac
PYVER=$("$BASE" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
VENV=${UHDL_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/uhdl-skill/$VERSION-py$PYVER-$(uname -m)}
STAMP="$VENV/.uhdl_skill"

# ---- 2. already prepared?
find_vpy() { for p in "$VENV/bin/python" "$VENV/Scripts/python.exe" "$VENV/python"; do [ -x "$p" ] && { echo "$p"; return; }; done; }
VPY=$(find_vpy)
if [ -n "$VPY" ] && [ "$(cat "$STAMP" 2>/dev/null)" = "$VERSION $BASE" ] && "$VPY" -c 'import uhdl' >/dev/null 2>&1; then
    echo "$VPY"; exit 0
fi

# ---- 3. create the environment
say "preparing UHDL $UHDL_VER for Python $PYVER ($BASE) in $VENV"
rm -rf "$VENV"; mkdir -p "$(dirname "$VENV")"
PIP_WHL=$(ls "$WHEELS"/pip-*.whl 2>/dev/null | head -1)
PIPOPT=(--disable-pip-version-check --no-input -q)
if "$BASE" -m venv "$VENV" >/dev/null 2>&1; then
    VPY=$(find_vpy)
elif "$BASE" -m venv --without-pip "$VENV" >/dev/null 2>&1 && [ -n "$PIP_WHL" ]; then
    VPY=$(find_vpy)                                # no ensurepip (e.g. Debian without python3-venv)
    "$VPY" "$PIP_WHL/pip" install "${PIPOPT[@]}" --no-index "$PIP_WHL" >&2 || die "could not install pip into $VENV"
else
    # no venv module at all: install into a directory and wrap the base Python
    [ -n "$PIP_WHL" ] || die "$BASE has neither venv nor pip, and the bundle has no pip wheel"
    mkdir -p "$VENV/site"
    printf '#!/bin/sh\nPYTHONPATH="%s/site${PYTHONPATH:+:$PYTHONPATH}" exec "%s" "$@"\n' "$VENV" "$BASE" > "$VENV/python"
    chmod +x "$VENV/python"; VPY="$VENV/python"
    PIPCMD=("$BASE" "$PIP_WHL/pip" install "${PIPOPT[@]}" --target "$VENV/site")
fi
[ -n "$VPY" ] || die "could not create an environment in $VENV"
if [ -z "${PIPCMD+x}" ]; then
    # a recent pip first: old ones (e.g. 20.x) do not know the manylinux_2_27 wheels of pyslang
    [ -n "$PIP_WHL" ] && "$VPY" -m pip install "${PIPOPT[@]}" --no-index --upgrade "$PIP_WHL" >&2
    PIPCMD=("$VPY" -m pip install "${PIPOPT[@]}")
fi

# ---- 4. UHDL with pyslang from the bundle; UHDL alone if no pyslang wheel fits
SV=yes
if ! "${PIPCMD[@]}" --no-index --find-links "$WHEELS" --only-binary :all: "uhdl[sv]==$UHDL_VER" >&2 2>/dev/null; then
    if [ "${UHDL_ALLOW_NETWORK:-}" = 1 ] && "${PIPCMD[@]}" --find-links "$WHEELS" --only-binary :all: "uhdl[sv]==$UHDL_VER" >&2; then
        say "pyslang came from PyPI"
    else
        SV=no
        "${PIPCMD[@]}" --no-index --find-links "$WHEELS" "uhdl==$UHDL_VER" >&2 || die "could not install UHDL from $WHEELS"
    fi
fi
"$VPY" -c 'import uhdl' >&2 || die "UHDL does not import in $VPY"
if [ $SV = yes ]; then
    say "ready: UHDL $UHDL_VER, pyslang $("$VPY" -c 'import importlib.metadata as m; print(m.version("pyslang"))' 2>/dev/null || echo '?')"
else
    say "ready: UHDL $UHDL_VER WITHOUT SV import: the bundle has no pyslang wheel for Python $PYVER on $(uname -sm)."
    say "       VComponent / import_sv_package will fail. UHDL_ALLOW_NETWORK=1 lets pip fetch pyslang from PyPI."
fi
echo "$VERSION $BASE" > "$STAMP"
echo "$VPY"
