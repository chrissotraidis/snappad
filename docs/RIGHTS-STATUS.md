# SnapPad rights status

Status: **maintainer-authorized community release; upstream rights unresolved**
Last reviewed: 2026-08-31

On 28 August 2026, Chris accepted the current physical-iPad build as stable and
explicitly authorized the first public SnapPad integration-source snapshot,
tag, screenshot, and free unsigned ROM-free IPA. This records the maintainer's
release decision; it does not establish permission from upstream authors or
Nintendo and is not legal advice.

On 31 August 2026, Chris accepted the gyro-enabled physical-iPad build as
stable and explicitly authorized Preview 2 as another free integration-source
snapshot and unsigned ROM-free IPA under the same rights boundary.

## Current findings

- The pinned `ethteck/pokemonsnap` repository revision `11ee0fec2143bdd636ee0e9c714a402fd8c7d9fe` has no general root license. A license nested under an imported tool does not license the repository as a whole.
- Repository visibility and user ROM ownership do not establish permission to redistribute decompiled or statically translated game logic.
- Every third-party dependency retains its own license and notice requirements.
- ROMs, rebuilt ROMs, extracted assets, generated AOT code, saves, photographs, crash memory, and private diagnostic logs are never publishable inputs.

## Intended topology

SnapPad is a separate integration repository. The pinned Pokémon Snap decomp is an ignored local build input under `ref/pokemonsnap`; no decomp source is copied into SnapPad. This topology is selected for private engineering and does not itself resolve public redistribution rights.

## Current publication boundary

The v0.1.0 and Preview 2 releases may include the SnapPad integration source,
patches, scripts, documentation, screenshots, an unsigned ROM-free IPA, scoped
rights notice, and dependency notices. They must not include any ROM, rebuilt
ROM, extracted asset, generated AOT source input, save, photograph, private
log, signing material, or maintainer provisioning profile.

The release is source-available community software, not a broad license grant
for upstream or translated game code. Paid access, commercial licensing,
TestFlight, App Store, or other official-store distribution still requires a
new decision and independent rights review.

## Unresolved rights questions

1. Explicit maintainer/license clarity for the decomp source and translated-code boundary.
2. Independent legal review before broader or commercial distribution.
3. Continued dependency and binary-notice audits for every exact candidate.

This is an engineering gate, not legal advice.
