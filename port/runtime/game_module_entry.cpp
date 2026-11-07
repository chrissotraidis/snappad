#include "game_module.h"
#include "snappad_game_hooks.h"
#include "snappad_game_metadata.h"
#include "register_overlays.h"

extern "C" void recomp_entrypoint(uint8_t*, recomp_context*);
RspExitReason aspMain(uint8_t*, uint32_t);

extern "C" __attribute__((visibility("default")))
const SnapPadGameModule* snappad_get_game_module() {
    static const SnapPadGameModule module{
        snappad_game_module_version, sizeof(SnapPadGameModule), SNAPPAD_MODULE_ID,
        pokemon_snap::generated::rom_xxh3, pokemon_snap::generated::entrypoint,
        pokemon_snap::generated::internal_name, pokemon_snap::generated::game_id,
        recomp_entrypoint, aspMain, pokemon_snap::register_overlays,
        SnapPad_ConsumeTunnelHiddenPathReady, SnapPad_IsFinalTunnelElectrodeFocused,
        SnapPad_CurrentFocusedSubject, SnapPad_ConsumeItemImpactSubject
    };
    return &module;
}
