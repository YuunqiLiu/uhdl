# libuhdl_slang: slang (third_party/slang, v10.0) behind a C interface for UHDL (see uhdl_slang.cpp).
# Build with native/build.py. Offline: fmt comes from the third_party/fmt submodule.
cmake_minimum_required(VERSION 3.20)
project(uhdl_slang CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

set(UHDL_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." CACHE PATH "uhdl repository root")
set(SLANG_INCLUDE_TESTS OFF CACHE BOOL "" FORCE)
set(SLANG_INCLUDE_TOOLS OFF CACHE BOOL "" FORCE)
set(SLANG_INCLUDE_PYLIB OFF CACHE BOOL "" FORCE)
set(SLANG_INCLUDE_DOCS OFF CACHE BOOL "" FORCE)
set(SLANG_INCLUDE_INSTALL OFF CACHE BOOL "" FORCE)
set(SLANG_USE_MIMALLOC OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(FETCHCONTENT_SOURCE_DIR_FMT "${UHDL_ROOT}/third_party/fmt" CACHE PATH "" FORCE)
set(FETCHCONTENT_FULLY_DISCONNECTED ON CACHE BOOL "" FORCE)
add_subdirectory("${UHDL_ROOT}/third_party/slang" slang EXCLUDE_FROM_ALL)

add_library(uhdl_slang SHARED uhdl_slang.cpp)
target_link_libraries(uhdl_slang PRIVATE slang::slang)
set_target_properties(uhdl_slang PROPERTIES CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN ON)
# Only the C functions are exported; libstdc++/libgcc are static, so the library needs only the
# glibc of the toolchain's sysroot (2.17 with conda-forge gxx_linux-64 + sysroot_linux-64=2.17).
# -s: no debug information or local symbols (19.6 MB -> about 8 MB); the exported C functions stay.
target_link_options(uhdl_slang PRIVATE -static-libstdc++ -static-libgcc -Wl,--exclude-libs,ALL -s)
