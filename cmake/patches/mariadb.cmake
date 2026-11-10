# Patch the bundled MariaDB Connector/C sources so they configure with CMake 4
# and install from multi-config (Visual Studio) builds.
# Run by ExternalProject as: cmake -DSRC=<SOURCE_DIR> -P mariadb.cmake

# cmake/ConnectorName.cmake closes an IF() block with END() instead of
# ENDIF(). Older CMake tolerated this; CMake 4 rejects the bad nesting.
SET(_file "${SRC}/cmake/ConnectorName.cmake")
FILE(READ "${_file}" _content)
STRING(REGEX REPLACE "\n([ \t]*)END\\(\\)" "\n\\1ENDIF()" _patched "${_content}")
IF(NOT _patched STREQUAL _content)
    FILE(WRITE "${_file}" "${_patched}")
    MESSAGE(STATUS "Patched ${_file} (END() -> ENDIF())")
ENDIF()

# libmariadb/CMakeLists.txt always installs a PDB from a hard-coded
# "RelWIthDebInfo" folder on Windows. In a Release (or Debug) build that file
# does not exist and the install step fails, so make it optional.
SET(_file "${SRC}/libmariadb/CMakeLists.txt")
FILE(READ "${_file}" _content)
STRING(REPLACE "INSTALL(FILES \${PDB_LOCATION} DESTINATION"
    "INSTALL(FILES \${PDB_LOCATION} OPTIONAL DESTINATION" _patched "${_content}")
IF(NOT _patched STREQUAL _content)
    FILE(WRITE "${_file}" "${_patched}")
    MESSAGE(STATUS "Patched ${_file} (optional PDB install)")
ENDIF()

# On Windows the top-level CMakeLists.txt resets SYSTEM_LIBS to the Win32
# system libraries and drops ${LIBZ}, so building with WITH_EXTERNAL_ZLIB=ON
# leaves compress()/uncompress() unresolved in libmariadb.dll and the tests.
SET(_file "${SRC}/CMakeLists.txt")
FILE(READ "${_file}" _content)
STRING(REPLACE "SET(SYSTEM_LIBS ws2_32 advapi32 kernel32 shlwapi crypt32)"
    "SET(SYSTEM_LIBS ws2_32 advapi32 kernel32 shlwapi crypt32 \${LIBZ})"
    _patched "${_content}")
IF(NOT _patched STREQUAL _content)
    FILE(WRITE "${_file}" "${_patched}")
    MESSAGE(STATUS "Patched ${_file} (link external zlib on Windows)")
ENDIF()
