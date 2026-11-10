# Patch the bundled TinyXML2 sources so they configure with CMake 4.
# Run by ExternalProject as: cmake -DSRC=<SOURCE_DIR> -P tinyxml2.cmake
#
# CMake 4 no longer allows setting CMP0063 to OLD. NEW only means the
# visibility presets are also honored for static libraries, which is harmless
# here.

SET(_file "${SRC}/CMakeLists.txt")
FILE(READ "${_file}" _content)
STRING(REPLACE "cmake_policy(SET CMP0063 OLD)" "cmake_policy(SET CMP0063 NEW)"
    _patched "${_content}")

IF(NOT _patched STREQUAL _content)
    FILE(WRITE "${_file}" "${_patched}")
    MESSAGE(STATUS "Patched ${_file} (CMP0063 OLD -> NEW)")
ENDIF()
