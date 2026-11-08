#!/usr/bin/env python3
"""Build libuhdl_slang.so into uhdl/_native/ (where uhdl.core._slang loads it from).

    python native/build.py [--cxx /path/x86_64-conda-linux-gnu-g++] [--build-dir DIR] [--jobs N]

Needs CMake 3.20+, a C++20 compiler and the third_party/slang and third_party/fmt submodules
(`git submodule update --init third_party/slang third_party/fmt`); no network. The compiler's
sysroot sets the oldest glibc the library runs on: conda-forge gxx_linux-64 13 with
sysroot_linux-64=2.17 gives glibc 2.17. The result is checked for its glibc requirement.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'uhdl', '_native')


def glibc_needed(path):
    """Highest GLIBC_x.y symbol version the shared library needs."""
    tool = shutil.which('objdump') or shutil.which('readelf')
    if not tool:
        return None
    args = [tool, '-T', path] if tool.endswith('objdump') else [tool, '-V', path]
    text = subprocess.run(args, capture_output=True, text=True).stdout
    vers = {tuple(int(x) for x in m) for m in re.findall(r'GLIBC_(\d+)\.(\d+)', text)}
    return max(vers) if vers else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cxx', default=os.environ.get('CXX'), help='C++ compiler (default: $CXX or c++)')
    ap.add_argument('--build-dir', default=os.path.join(HERE, 'build'))   # native/build (not build/: setuptools owns that)
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 4)
    ap.add_argument('--max-glibc', default='2.17', help='fail if the library needs a newer glibc ("" to skip)')
    a = ap.parse_args()

    for sub in ('slang', 'fmt'):
        if not os.path.isfile(os.path.join(ROOT, 'third_party', sub, 'CMakeLists.txt')):
            raise SystemExit('third_party/%s is missing: git submodule update --init third_party/slang third_party/fmt' % sub)
    cmake = shutil.which('cmake') or raise_(SystemExit('cmake not found'))
    cfg = [cmake, '-S', HERE, '-B', a.build_dir, '-DCMAKE_BUILD_TYPE=Release']
    if shutil.which('ninja'):
        cfg += ['-G', 'Ninja']
    if a.cxx:
        cfg += ['-DCMAKE_CXX_COMPILER=' + a.cxx]
    print('+', ' '.join(cfg), flush=True)
    subprocess.run(cfg, check=True)
    subprocess.run([cmake, '--build', a.build_dir, '--target', 'uhdl_slang', '-j', str(a.jobs)], check=True)

    lib = os.path.join(a.build_dir, 'libuhdl_slang.so')
    need = glibc_needed(lib)
    if a.max_glibc and need is not None:
        limit = tuple(int(x) for x in a.max_glibc.split('.'))
        if need > limit:
            raise SystemExit('%s needs GLIBC_%d.%d, newer than %s: use a compiler whose sysroot is glibc %s'
                             % (lib, need[0], need[1], a.max_glibc, a.max_glibc))
    os.makedirs(OUT, exist_ok=True)
    shutil.copy2(lib, os.path.join(OUT, 'libuhdl_slang.so'))
    print('built %s (needs GLIBC_%s, %.1f MB)' % (os.path.join(OUT, 'libuhdl_slang.so'),
          '%d.%d' % need if need else '?', os.path.getsize(lib) / 1e6))


def raise_(e):
    raise e


if __name__ == '__main__':
    main()
