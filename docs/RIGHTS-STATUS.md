# SnapPad rights status

Status: **private-only**
Last reviewed: 2026-08-26

Chris has authorized private technical feasibility and development work on SnapPad. No public source release, binary, IPA, tag, package, generated output, screenshot set, or other publication is authorized by this status.

## Current findings

- The pinned `ethteck/pokemonsnap` repository revision `11ee0fec2143bdd636ee0e9c714a402fd8c7d9fe` has no general root license. A license nested under an imported tool does not license the repository as a whole.
- Repository visibility and user ROM ownership do not establish permission to redistribute decompiled or statically translated game logic.
- Every third-party dependency retains its own license and notice requirements.
- ROMs, rebuilt ROMs, extracted assets, generated AOT code, saves, photographs, crash memory, and private diagnostic logs are never publishable inputs.

## Intended topology

SnapPad is a separate integration repository. The pinned Pokémon Snap decomp is an ignored local build input under `ref/pokemonsnap`; no decomp source is copied into SnapPad. This topology is selected for private engineering and does not itself resolve public redistribution rights.

## Decisions still required for publication

1. Explicit maintainer/license clarity for the decomp source and translated-code boundary.
2. A complete dependency and binary-notice audit against the exact candidate.
3. Separate explicit authorization from Chris for any source release and any binary/IPA release.

This is an engineering gate, not legal advice.
