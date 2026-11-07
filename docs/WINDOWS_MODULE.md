# Private iOS module prototype

The published PadMint recipe still uses the existing full Mac build. This source
prototype separates the iOS runtime from privately generated game code; it does
not yet establish a complete Windows player build or physical-device acceptance.
SnapPad's release pause remains in effect.

## Boundary

The empty shell owns UIKit, SDL, RT64, N64ModernRuntime, input and save handling,
OS replacement functions, and the runtime's function lookup and overlay map.
`SnapPadGame.dylib` owns the generated CPU/lookup/overlay/RSP sources, generated
game metadata, and the game hooks that use that metadata. The hooks' four
integer queries used by the runner cross the same function table as the game
entrypoint, audio RSP and overlay registration. No C++ containers cross it.

Only `snappad_get_game_module` is public in the module. The loader checks its
version, size, source identity and required fields before retaining the library.
iOS loads it from `Frameworks/SnapPadGame.dylib` before ROM setup. Missing or
incompatible modules stop startup; the runner separately checks readiness before
registering the game. The runtime stays in the app, including `get_function`.

The identity covers the dependency lock, native source and patches, CMake files,
configuration and the verification helper. Both artifacts must come from the
same identity. Do not pair an older shell with a newly rebuilt module merely
because their version labels agree.

## Maintainer validation

Use exact public source pins with the reviewed patch stack. Explicit source
paths are checked without resetting or patching the supplied checkout. ReCut's
pinned build expects the locked `mupen64plus-rsp-hle` checkout beside it. Preserve
existing modified caches; prepare a separate source stage if needed.

On a Mac, the shell uses its own build folder and deliberately points the
generated-input setting at a nonexistent folder:

```sh
python3 scripts/build-module-shell.py \
  --recut /path/to/pinned/recut --sdl /path/to/pinned/SDL2 \
  --zstd /path/to/pinned/zstd --jobs 2 \
  --output /path/to/new/SnapPad-module-shell.ipa
```

The module-only entrypoint consumes existing, accepted G2 output. It does not
perform or substitute for the full ROM rebuild. Give it PadMint's iOS toolchain
prepared for the matching shell, with an iOS 15 deployment target:

```sh
python3 scripts/build-game-module.py \
  --generated-dir /path/to/private/generated \
  --source-dir /path/to/pinned/recut \
  --toolchain /path/to/iPhoneOS-open-source.sdk/toolchain.cmake \
  --build-dir /path/to/private/module-build --jobs 2
```

This verifies accepted G2 evidence and records every private AOT/evidence file,
including overlay headers. CMake and the post-build check reject changes to that
record. Original ROMs and generated inputs are not rewritten. Use PadMint's
shared import, physical-iOS compatibility and IPA insertion checks on the result.

`scripts/check-module-loader.py` tests the actual loader with synthetic native
Mac libraries, including rejection and forwarding behavior. These checks do not
prove iOS loading, gameplay, controller behavior, performance or save preservation.

Local validation has compiled matching empty shells and private modules for
iOS 15 on Mac and Windows. The modules export only their getter; shared PadMint
checks resolve their imports and insert them while preserving every original
shell archive member. The existing static generated-core target and all 20
synthetic native loader cases also pass.

## Complete Windows backend candidate

`scripts/build-windows-module.py` is the maintainer's complete private backend.
It requires PadMint's bundled x64 CPython 3.13, Git, CMake, Ninja and prepared iOS
toolchain, plus Visual Studio C++ Build Tools and a Windows SDK with libraries
for the selected native host compiler. ARM64 hosts prefer native ARM64 tools and
can fall back to x64 tools; x64 hosts select an installation with x64 tools.
The Windows SDK and selected compiler are checked before preparation starts.

The remaining decompilation tools currently come from a local, independently
verified candidate manifest. The manifest and its SHA-256 are explicit inputs;
this script does not download or implicitly trust replacement binaries. It
checks tool inventories and provenance receipts, the Python wheel ABI, and the
installed Rabbitizer wheel's complete payload and RECORD. Until approved tool
archives are available, this is not an advertised PadMint player route.

```powershell
& 'C:\PadMint\app\python\python.exe' -X utf8 -B scripts/build-windows-module.py `
  --rom 'C:\Games\original.z64' --work 'C:\Builds\SnapPad' `
  --toolchain 'C:\Builds\sdk\iPhoneOS-open-source.sdk\toolchain.cmake' `
  --tools 'C:\Builds\candidate-tools.json' --tools-sha256 REVIEWED_SHA256 `
  --result 'C:\Builds\SnapPad\module-result.json' --jobs 2
```

The backend normalizes a private copy of the original ROM, prepares exact public
source pins and reviewed patches, and creates a frozen Python environment. The
only runtime dependency override is the reviewed Rabbitizer 1.14.3 Windows
unsigned-address fix. It rebuilds the entire ROM with native Windows tools and
requires the original ROM checksum before generating CPU/RSP code and compiling
the iOS module. Unexpected linker failures stop the build; there is no Windows
symbol-recovery fallback.

A complete Windows ARM64 candidate run reproduced the original ROM, and all 89
generated code/header files matched the Mac output byte for byte. It used fresh
NTFS source checkouts from existing Git objects, a cold frozen Python environment
with the maintained Rabbitizer wheel, and a warm verified tool bundle. Shared
import, iOS 15 compatibility and IPA insertion checks passed. An unchanged-input
retry after SDK preparation reused the same module without recompilation.
This evidence is distinct from a clean installation of published player tools.
The complete run also passed with Unicode work and temporary directories and an
invalid inherited `USR_LIB`, confirming the backend's scoped runtime environment.

An optional `--decomp-cache` or `--recut-cache` supplies existing Git objects,
never a copied working tree or generated game output. Owned checkouts use LF
files regardless of inherited Git newline settings. Source pins and patch
changes select new cache folders while preserving older work. All failed build
attempts and their logs remain available for diagnosis.

Complete-build reuse verifies every recorded output and the installed wheel.
Its key includes the original ROM, exact tool manifest, source/script content
and the complete prepared SDK content, including headers and linker stubs.
Changing those inputs triggers a new attempt; unchanged inputs preserve the
module. The result is a descriptor for PadMint's shared import, compatibility
and IPA insertion checks, not a separately implemented packager.

Public CI prepares the locked source checkouts on Windows x64, Windows ARM64
and macOS, builds the host generators, and checks hand-authored CPU/RSP/hash
fixtures. It also exercises source preservation, tool inventory, cache
invalidation and path handling without private inputs or game artifact uploads.
These checks and private build evidence do not establish physical-device
loading or gameplay. The public recipe and release pause remain unchanged.

The Windows host generators request UTF-8 per process through an embedded
manifest; no system locale setting changes. Visual Studio environment capture
uses Unicode output, and GNU inspection tools receive ASCII artifact basenames
within their original working directories. Python subprocesses use UTF-8, and
paths exchanged between interpreters use JSON. Public fixtures cover Unicode paths
with native ARM64 and x64 generator binaries, including manifest readback and
CPU execution. Local x64 execution is under Windows ARM64 emulation; it is not
physical x64 hardware or a complete x64 player-build acceptance result.
