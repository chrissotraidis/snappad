#include "game_module.h"
#include <cstdio>
#include <cstring>
#include <dlfcn.h>

namespace {
const SnapPadGameModule* module = nullptr;
void* library = nullptr;
}

extern "C" const char* snappad_load_game_module(const char* path) {
    if (module) return nullptr;
    if (!path || !*path) {
        return "This copy needs its game module. Build it with PadMint using your supported ROM.";
    }
    void* candidate = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!candidate) {
        std::fprintf(stderr, "[game module] %s\n", dlerror());
        return "The game module could not load. Build this copy with PadMint and install it again.";
    }
    auto getter = reinterpret_cast<SnapPadGetGameModule*>(dlsym(candidate, "snappad_get_game_module"));
    const auto* value = getter ? getter() : nullptr;
    if (!value || value->version != snappad_game_module_version || value->size != sizeof(SnapPadGameModule) ||
        !value->identity || std::strcmp(value->identity, SNAPPAD_MODULE_ID) != 0 ||
        !value->rom_xxh3 || !value->entrypoint_address || !value->internal_name || !*value->internal_name ||
        !value->game_id || !*value->game_id || !value->entrypoint || !value->audio ||
        !value->register_overlays || !value->consume_tunnel_hidden_path_ready ||
        !value->is_final_tunnel_electrode_focused || !value->current_focused_subject ||
        !value->consume_item_impact_subject) {
        dlclose(candidate);
        return "The game module belongs to a different app build. Build this copy with PadMint again.";
    }
    library = candidate; // Keep all code and overlay pointers alive for the game threads.
    module = value;
    return nullptr;
}

extern "C" const SnapPadGameModule* snappad_game_module() { return module; }
extern "C" void recomp_entrypoint(uint8_t* rdram, recomp_context* ctx) { module->entrypoint(rdram, ctx); }
RspExitReason aspMain(uint8_t* rdram, uint32_t address) { return module->audio(rdram, address); }
namespace pokemon_snap {
void register_overlays() { module->register_overlays(); }
}
extern "C" int SnapPad_ConsumeTunnelHiddenPathReady() { return module->consume_tunnel_hidden_path_ready(); }
extern "C" int SnapPad_IsFinalTunnelElectrodeFocused() { return module->is_final_tunnel_electrode_focused(); }
extern "C" int SnapPad_CurrentFocusedSubject() { return module->current_focused_subject(); }
extern "C" int SnapPad_ConsumeItemImpactSubject() { return module->consume_item_impact_subject(); }
