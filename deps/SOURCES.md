# Bundled dependency sources

The original `comphack` GitHub organization no longer exists, so every
dependency the build needs is now stored in this repository. Nothing is
downloaded at build time.

## Former submodules (now plain folders)

| Path | Recovered from | Commit |
|---|---|---|
| `libcomp/` | github.com/milkymilkyway/libcomp | d045b94ebe88346988229010926f91c2e85db8d5 |
| `libcomp/deps/sqrat/` | github.com/milkymilkyway/sqrat | f46b173cf7ff0d9317a12bfe05e2746795b17ab4 |
| `libcomp/coveralls-cmake/` | github.com/JoakimSoderberg/coveralls-cmake | 9f96714bdf0279ceab0a5dcd524be17e71df63be |
| `datastore/` | github.com/milkymilkyway/datastore | bb5f86eb700648abe6cfb4bdaa68ebb8fe6de525 |
| `deps/sqrat/` | github.com/milkymilkyway/sqrat | 0ce32046da39942a1eb38d5ccbec2df5ca239834 |
| `deps/cpp-optparse/` | github.com/weisslj/cpp-optparse | 2ec0b7aca9a692ff93017ed44ca9d13a8e7d4d00 |
| `coveralls-cmake/` | github.com/JoakimSoderberg/coveralls-cmake | 0feb9aafe02aafea347836835dcbadd91524c468 |

Each commit is the exact one the original submodule pointer referenced.

## External libraries (`deps/*.zip`)

Extracted from the official COMP_hack Ubuntu source package
`comphack_4.12.2.tar.xz` (Launchpad PPA `ppa:compomega/comphack`,
SHA-256 `643ea6376d33c9b3481e545071f96e8c8afcb4a6fc8c0e9e0d62ca9473d46119`,
matching its signed `.dsc`). Every zip's SHA-1 matches the `URL_HASH` in the
corresponding `cmake/deps/*.cmake`, so they are byte-identical to the
archives the build used to download.

GSL, JsonBox, asio, civetweb, googletest, mariadb, openssl, physfs,
squirrel3, tinyxml2, ttvfs, zlib.

**Not bundled:** `mbedtls.zip`. It is only used with the non-default
`-DUSE_MBED_TLS=ON` option, and no surviving copy was found.
