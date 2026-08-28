# SnapPad rights and licenses

SnapPad is an independent, unofficial project. It is not affiliated with,
endorsed by, or sponsored by Nintendo, The Pokémon Company, or their partners.
Pokémon Snap and related names, characters, copyrights, and trademarks belong
to their respective owners.

## v0.1.0 release boundary

The maintainer authorized publication of the SnapPad v0.1.0 integration-source
snapshot and its free, unsigned, ROM-free IPA on 28 August 2026.

The repository and IPA do not include a Pokémon Snap ROM, extracted game
assets, saves, photographs, signing credentials, or a maintainer provisioning
profile. Users must provide their own legally obtained, unmodified Pokémon Snap
(USA) ROM after installation.

This authorization applies only to the SnapPad release decision. It does not
grant rights in Nintendo material, the Pokémon Snap decompilation, translated
game logic, or third-party dependencies.

## Source and translated-code caution

The pinned `ethteck/pokemonsnap` revision has no general license at its
repository root. SnapPad keeps that checkout outside the published integration
tree, but the native IPA contains ahead-of-time translated game logic. A
ROM-free package does not by itself resolve the legal or licensing status of
that translated code.

SnapPad should therefore be described as source-available community software,
not as broadly relicensed open-source game code. The v0.1.0 authorization does
not extend to paid access, commercial licensing, TestFlight, App Store, or
other official-store distribution. Obtain independent legal advice before
expanding distribution.

## Third-party software

SnapPad builds on N64Recomp, N64ModernRuntime, RSPRecomp, RT64, SDL2, zstd,
and their bundled dependencies. Each project retains its own copyright and
license terms. The IPA includes the license and notice files discovered from
the exact pinned dependency checkouts under `ThirdPartyLicenses/`.

Nothing in this document relicenses upstream projects or Nintendo material.
This document records the engineering and release boundary; it is not legal
advice.
