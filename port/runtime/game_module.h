#pragma once
#include <cstdint>
#include "recomp.h"

enum class RspExitReason;

// The app owns the runtime, renderer and overlay map. Generated game code and
// metadata stay in the private module. No C++ containers cross this table.
struct SnapPadGameModule {
    uint32_t version;
    uint32_t size;
    const char* identity;
    uint64_t rom_xxh3;
    uint32_t entrypoint_address;
    const char* internal_name;
    const char8_t* game_id;
    void (*entrypoint)(uint8_t*, recomp_context*);
    RspExitReason (*audio)(uint8_t*, uint32_t);
    void (*register_overlays)();
    int (*consume_tunnel_hidden_path_ready)();
    int (*is_final_tunnel_electrode_focused)();
    int (*current_focused_subject)();
    int (*consume_item_impact_subject)();
};

constexpr uint32_t snappad_game_module_version = 1;
using SnapPadGetGameModule = const SnapPadGameModule*();
extern "C" const char* snappad_load_game_module(const char* path);
extern "C" const SnapPadGameModule* snappad_game_module();
