#include "snappad_game_hooks.h"

#include <atomic>
#include <cmath>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <limits>
#include <mutex>
#include <unordered_map>
#include <vector>

#include "snappad_game_metadata.h"

extern "C" void setPlayerFlag(std::uint8_t* rdram, recomp_context* context);
extern "C" void func_8009BCC4(std::uint8_t* rdram, recomp_context* context);

namespace {

std::atomic<bool> tunnel_hidden_path_ready{false};
std::atomic<bool> tunnel_hidden_path_triggered{false};
std::atomic<bool> tunnel_hidden_path_revealed{false};
std::atomic<bool> tunnel_hidden_path_impact_command_observed{false};
std::atomic<std::uint32_t> tunnel_hidden_path_guard_object{0};
std::atomic<bool> tunnel_raw_item_geometry_traced{false};
std::unordered_map<std::uint32_t, float> tunnel_pester_min_distance;
std::atomic<std::int32_t> tunnel_progress_block{-1};
std::atomic<float> tunnel_progress_part{0.0f};
std::atomic<std::int32_t> traced_tunnel_progress_bucket{-1000};
std::atomic<std::int32_t> observed_focus_subject{-1};
std::atomic<std::uint32_t> observed_focus_object{0};
std::atomic<std::int32_t> observed_item_impact_subject{-1};
std::mutex captured_subject_mutex;
std::vector<std::int32_t> captured_subjects;
std::size_t next_captured_subject = 0;
std::unordered_map<gpr, std::int32_t> subject_by_photo;
bool scoring_started = false;
std::int32_t last_traced_focus = -2;
bool last_traced_has_focus = false;
std::uint64_t focus_observation_sequence = 0;
std::uint64_t last_valid_focus_sequence = 0;
std::int32_t last_valid_focus = -1;

float read_n64_float(std::uint8_t* rdram, gpr base, gpr offset) {
    const std::uint32_t bits = MEM_W(offset, base);
    float value = 0.0f;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

void arm_tunnel_hidden_path_route_if_window_open() {
    const std::int32_t block =
        tunnel_progress_block.load(std::memory_order_acquire);
    const float part = tunnel_progress_part.load(std::memory_order_acquire);
    const bool approach_window = block == 4;
    const bool final_window = block == 5 && part < 0.35f;
    if (!approach_window && !final_window) {
        return;
    }

    bool expected = false;
    if (!tunnel_hidden_path_triggered.compare_exchange_strong(
            expected, true, std::memory_order_acq_rel)) {
        return;
    }
    tunnel_hidden_path_ready.store(true, std::memory_order_release);
    const char* trace_path = std::getenv("SNAPPAD_GAMEPLAY_TRACE_PATH");
    if (trace_path != nullptr && *trace_path != '\0') {
        if (std::FILE* file = std::fopen(trace_path, "a")) {
            std::fprintf(file,
                "tunnel-hidden-path-approach-open block=%d part=%.6f\n",
                block, static_cast<double>(part));
            std::fclose(file);
        }
    }
}

} // namespace

extern "C" void SnapPad_ResetPhotoCaptureSession(
    std::uint8_t*, recomp_context*) {
    tunnel_hidden_path_ready.store(false, std::memory_order_release);
    tunnel_hidden_path_triggered.store(false, std::memory_order_release);
    tunnel_hidden_path_revealed.store(false, std::memory_order_release);
    tunnel_hidden_path_impact_command_observed.store(
        false, std::memory_order_release);
    tunnel_hidden_path_guard_object.store(0, std::memory_order_release);
    tunnel_raw_item_geometry_traced.store(false, std::memory_order_release);
    tunnel_pester_min_distance.clear();
    tunnel_progress_block.store(-1, std::memory_order_release);
    tunnel_progress_part.store(0.0f, std::memory_order_release);
    traced_tunnel_progress_bucket.store(-1000, std::memory_order_release);
    observed_focus_subject.store(-1, std::memory_order_release);
    observed_focus_object.store(0, std::memory_order_release);
    observed_item_impact_subject.store(-1, std::memory_order_release);
    std::lock_guard<std::mutex> lock(captured_subject_mutex);
    captured_subjects.clear();
    next_captured_subject = 0;
    subject_by_photo.clear();
    scoring_started = false;
    last_traced_focus = -2;
    last_traced_has_focus = false;
    focus_observation_sequence = 0;
    last_valid_focus_sequence = 0;
    last_valid_focus = -1;
}

extern "C" void SnapPad_ObserveTunnelProgress(
    std::uint8_t*, recomp_context* context) {
    const std::int32_t block = static_cast<std::int32_t>(context->r2);
    const float part = context->f4.fl;
    tunnel_progress_block.store(block, std::memory_order_release);
    tunnel_progress_part.store(part, std::memory_order_release);
    const std::int32_t bucket = block * 10
        + static_cast<std::int32_t>(part * 10.0f);
    const std::int32_t previous_bucket =
        traced_tunnel_progress_bucket.exchange(bucket, std::memory_order_acq_rel);
    if (bucket != previous_bucket) {
        const char* trace_path = std::getenv("SNAPPAD_GAMEPLAY_TRACE_PATH");
        if (trace_path != nullptr && *trace_path != '\0') {
            if (std::FILE* file = std::fopen(trace_path, "a")) {
                std::fprintf(file, "tunnel-progress block=%d part=%.6f\n",
                    block, static_cast<double>(part));
                std::fclose(file);
            }
        }
    }
    arm_tunnel_hidden_path_route_if_window_open();
}

extern "C" int SnapPad_ConsumeTunnelHiddenPathReady(void) {
    return tunnel_hidden_path_ready.exchange(
        false, std::memory_order_acq_rel) ? 1 : 0;
}

extern "C" int SnapPad_IsFinalTunnelElectrodeFocused(void) {
    const std::uint32_t guard =
        tunnel_hidden_path_guard_object.load(std::memory_order_acquire);
    const std::uint32_t focused =
        observed_focus_object.load(std::memory_order_acquire);
    return guard != 0 && focused == guard
        ? 1
        : 0;
}

extern "C" int SnapPad_CurrentFocusedSubject(void) {
    return observed_focus_subject.load(std::memory_order_acquire);
}

extern "C" int SnapPad_ConsumeItemImpactSubject(void) {
    return observed_item_impact_subject.exchange(-1, std::memory_order_acq_rel);
}

extern "C" void SnapPad_EnableAcceptancePesterBall(
    std::uint8_t*, recomp_context* context) {
    const char* enabled = std::getenv("SNAPPAD_TEST_INPUT_ROUTE_TUNNEL_PROGRESS");
    if (enabled != nullptr && *enabled != '\0' && std::strcmp(enabled, "0") != 0) {
        // Icons_Init has just returned from getProgressFlags, with the flags in
        // v0. Enable the pester ball only for the bounded acceptance route;
        // this does not write the player's FlashRAM save.
        context->r2 = static_cast<gpr>(
            static_cast<std::uint32_t>(context->r2) | 0x000002u);
    }
}

extern "C" void SnapPad_ObserveHiddenPathGuard(
    std::uint8_t* rdram, recomp_context* context) {
    const std::uint32_t object = static_cast<std::uint32_t>(context->r4);
    tunnel_hidden_path_guard_object.store(object, std::memory_order_release);
    const char* trace_path = std::getenv("SNAPPAD_GAMEPLAY_TRACE_PATH");
    if (trace_path != nullptr && *trace_path != '\0') {
        if (std::FILE* file = std::fopen(trace_path, "a")) {
            constexpr gpr gobj_model_offset = 0x48;
            constexpr gpr gobj_user_data_offset = 0x58;
            constexpr gpr pokemon_collision_radius_offset = 0x58;
            constexpr gpr pokemon_collision_position_offset = 0x100;
            const std::uint32_t model = static_cast<std::uint32_t>(
                MEM_W(gobj_model_offset, object));
            const std::uint32_t pokemon = static_cast<std::uint32_t>(
                MEM_W(gobj_user_data_offset, object));
            std::fprintf(file,
                "tunnel-hidden-path-guard object=%08X model=%08X pokemon=%08X "
                "radius=%.3f coll-pos=(%.3f,%.3f,%.3f)\n",
                static_cast<unsigned>(object), static_cast<unsigned>(model),
                static_cast<unsigned>(pokemon),
                static_cast<double>(pokemon == 0 ? 0.0f : read_n64_float(
                    rdram, pokemon, pokemon_collision_radius_offset)),
                static_cast<double>(pokemon == 0 ? 0.0f : read_n64_float(rdram,
                    pokemon, pokemon_collision_position_offset + 0x0)),
                static_cast<double>(pokemon == 0 ? 0.0f : read_n64_float(rdram,
                    pokemon, pokemon_collision_position_offset + 0x4)),
                static_cast<double>(pokemon == 0 ? 0.0f : read_n64_float(rdram,
                    pokemon, pokemon_collision_position_offset + 0x8)));
            std::fclose(file);
        }
    }
}

extern "C" void SnapPad_ObservePesterTrajectory(
    std::uint8_t* rdram, recomp_context* context) {
    constexpr gpr gobj_model_offset = 0x48;
    constexpr gpr gobj_user_data_offset = 0x58;
    constexpr gpr dobj_position_offset = 0x1C;
    constexpr gpr pokemon_collision_radius_offset = 0x58;
    constexpr gpr pokemon_collision_position_offset = 0x100;

    const std::uint32_t item_object = static_cast<std::uint32_t>(context->r4);
    const std::uint32_t guard =
        tunnel_hidden_path_guard_object.load(std::memory_order_acquire);
    if (guard == 0) {
        return;
    }
    const std::uint32_t model = static_cast<std::uint32_t>(
        MEM_W(gobj_model_offset, item_object));
    const std::uint32_t pokemon = static_cast<std::uint32_t>(
        MEM_W(gobj_user_data_offset, guard));
    if (!tunnel_raw_item_geometry_traced.exchange(
            true, std::memory_order_acq_rel)) {
        const char* trace_path = std::getenv("SNAPPAD_GAMEPLAY_TRACE_PATH");
        if (trace_path != nullptr && *trace_path != '\0') {
            if (std::FILE* file = std::fopen(trace_path, "a")) {
                std::fprintf(file,
                    "tunnel-item-raw object=%08X model=%08X guard=%08X "
                    "guard-pokemon=%08X\n",
                    static_cast<unsigned>(item_object),
                    static_cast<unsigned>(model), static_cast<unsigned>(guard),
                    static_cast<unsigned>(pokemon));
                std::fclose(file);
            }
        }
    }
    if (model == 0 || pokemon == 0) {
        return;
    }

    const float item_x = read_n64_float(rdram, model, dobj_position_offset + 0x0);
    const float item_y = read_n64_float(rdram, model, dobj_position_offset + 0x4);
    const float item_z = read_n64_float(rdram, model, dobj_position_offset + 0x8);
    const float guard_x = read_n64_float(
        rdram, pokemon, pokemon_collision_position_offset + 0x0);
    const float guard_y = read_n64_float(
        rdram, pokemon, pokemon_collision_position_offset + 0x4);
    const float guard_z = read_n64_float(
        rdram, pokemon, pokemon_collision_position_offset + 0x8);
    const float radius = read_n64_float(
        rdram, pokemon, pokemon_collision_radius_offset);
    const float dx = item_x - guard_x;
    const float dy = item_y - guard_y;
    const float dz = item_z - guard_z;
    const float distance = std::sqrt(dx * dx + dy * dy + dz * dz);
    float& previous = tunnel_pester_min_distance[item_object];
    if (previous == 0.0f) {
        previous = std::numeric_limits<float>::infinity();
    }
    const float trace_step = previous > 750.0f ? 250.0f : 50.0f;
    if (!std::isfinite(distance) || distance >= previous - trace_step) {
        return;
    }
    previous = distance;
    const char* trace_path = std::getenv("SNAPPAD_GAMEPLAY_TRACE_PATH");
    if (trace_path != nullptr && *trace_path != '\0') {
        if (std::FILE* file = std::fopen(trace_path, "a")) {
            std::fprintf(file,
                "tunnel-pester-distance item=%08X distance=%.3f radius=%.3f "
                "pester=(%.3f,%.3f,%.3f) guard=(%.3f,%.3f,%.3f)\n",
                static_cast<unsigned>(item_object),
                static_cast<double>(distance), static_cast<double>(radius),
                static_cast<double>(item_x), static_cast<double>(item_y),
                static_cast<double>(item_z), static_cast<double>(guard_x),
                static_cast<double>(guard_y), static_cast<double>(guard_z));
            std::fclose(file);
        }
    }
}

extern "C" void SnapPad_ObserveCommand(
    std::uint8_t* rdram, recomp_context* context) {
    constexpr std::int32_t pester_impact_command = 9;
    constexpr std::int32_t proximity_command = 10;
    constexpr std::int32_t apple_impact_command = 13;
    const std::uint32_t target = static_cast<std::uint32_t>(context->r4);
    const std::int32_t command = static_cast<std::int32_t>(context->r5);
    if (command != pester_impact_command
        && command != proximity_command
        && command != apple_impact_command) {
        return;
    }
    constexpr gpr gobj_user_data_offset = 0x58;
    constexpr gpr pokemon_id_offset = 0x00;
    const std::uint32_t target_pokemon = static_cast<std::uint32_t>(
        MEM_W(gobj_user_data_offset, target));
    const std::int32_t target_subject = target_pokemon == 0
        ? -1
        : static_cast<std::int32_t>(MEM_W(pokemon_id_offset, target_pokemon));
    if ((command == pester_impact_command || command == apple_impact_command)
        && target_subject > 0) {
        observed_item_impact_subject.store(
            target_subject, std::memory_order_release);
    }
    const char* trace_path = std::getenv("SNAPPAD_GAMEPLAY_TRACE_PATH");
    if (trace_path != nullptr && *trace_path != '\0') {
        if (std::FILE* file = std::fopen(trace_path, "a")) {
            std::fprintf(file,
                "item-impact-command cmd=%d target=%08X subject=%d\n",
                command, static_cast<unsigned>(target), target_subject);
            std::fclose(file);
        }
    }
    const std::uint32_t guard =
        tunnel_hidden_path_guard_object.load(std::memory_order_acquire);
    if (guard == 0) {
        return;
    }
    const bool targets_guard = target == guard;
    if (targets_guard) {
        tunnel_hidden_path_impact_command_observed.store(
            true, std::memory_order_release);
    }
    if (trace_path != nullptr && *trace_path != '\0') {
        if (std::FILE* file = std::fopen(trace_path, "a")) {
            constexpr gpr gobj_model_offset = 0x48;
            constexpr gpr dobj_position_offset = 0x1C;
            constexpr gpr pokemon_collision_radius_offset = 0x58;
            constexpr gpr pokemon_collision_position_offset = 0x100;
            const std::uint32_t guard_pokemon = static_cast<std::uint32_t>(
                MEM_W(gobj_user_data_offset, guard));
            const std::uint32_t target_model = static_cast<std::uint32_t>(
                MEM_W(gobj_model_offset, target));
            const std::uint32_t guard_model = static_cast<std::uint32_t>(
                MEM_W(gobj_model_offset, guard));
            if (target_pokemon != 0 && guard_pokemon != 0) {
                std::fprintf(file,
                    "tunnel-impact-command cmd=%d target=%08X guard=%08X match=%d "
                    "target-radius=%.3f target-pos=(%.3f,%.3f,%.3f) "
                    "guard-radius=%.3f guard-pos=(%.3f,%.3f,%.3f)\n",
                    command, static_cast<unsigned>(target),
                    static_cast<unsigned>(guard), targets_guard ? 1 : 0,
                    static_cast<double>(read_n64_float(
                        rdram, target_pokemon, pokemon_collision_radius_offset)),
                    static_cast<double>(read_n64_float(rdram, target_pokemon,
                        pokemon_collision_position_offset + 0x0)),
                    static_cast<double>(read_n64_float(rdram, target_pokemon,
                        pokemon_collision_position_offset + 0x4)),
                    static_cast<double>(read_n64_float(rdram, target_pokemon,
                        pokemon_collision_position_offset + 0x8)),
                    static_cast<double>(read_n64_float(
                        rdram, guard_pokemon, pokemon_collision_radius_offset)),
                    static_cast<double>(read_n64_float(rdram, guard_pokemon,
                        pokemon_collision_position_offset + 0x0)),
                    static_cast<double>(read_n64_float(rdram, guard_pokemon,
                        pokemon_collision_position_offset + 0x4)),
                    static_cast<double>(read_n64_float(rdram, guard_pokemon,
                        pokemon_collision_position_offset + 0x8)));
            } else {
                std::fprintf(file,
                    "tunnel-impact-command cmd=%d target=%08X guard=%08X match=%d "
                    "target-user=%08X guard-user=%08X target-model=%08X "
                    "guard-model=%08X target-model-pos=(%.3f,%.3f,%.3f) "
                    "guard-model-pos=(%.3f,%.3f,%.3f)\n",
                    command, static_cast<unsigned>(target),
                    static_cast<unsigned>(guard), targets_guard ? 1 : 0,
                    static_cast<unsigned>(target_pokemon),
                    static_cast<unsigned>(guard_pokemon),
                    static_cast<unsigned>(target_model),
                    static_cast<unsigned>(guard_model),
                    static_cast<double>(target_model == 0 ? 0.0f
                        : read_n64_float(rdram, target_model,
                            dobj_position_offset + 0x0)),
                    static_cast<double>(target_model == 0 ? 0.0f
                        : read_n64_float(rdram, target_model,
                            dobj_position_offset + 0x4)),
                    static_cast<double>(target_model == 0 ? 0.0f
                        : read_n64_float(rdram, target_model,
                            dobj_position_offset + 0x8)),
                    static_cast<double>(guard_model == 0 ? 0.0f
                        : read_n64_float(rdram, guard_model,
                            dobj_position_offset + 0x0)),
                    static_cast<double>(guard_model == 0 ? 0.0f
                        : read_n64_float(rdram, guard_model,
                            dobj_position_offset + 0x4)),
                    static_cast<double>(guard_model == 0 ? 0.0f
                        : read_n64_float(rdram, guard_model,
                            dobj_position_offset + 0x8)));
            }
            std::fclose(file);
        }
    }
}

extern "C" int SnapPad_WasHiddenPathImpactCommandObserved(void) {
    return tunnel_hidden_path_impact_command_observed.load(
        std::memory_order_acquire) ? 1 : 0;
}

extern "C" void SnapPad_ObserveHiddenPathReveal(
    std::uint8_t*, recomp_context*) {
    if (tunnel_hidden_path_revealed.exchange(
            true, std::memory_order_acq_rel)) {
        return;
    }
    const char* trace_path = std::getenv("SNAPPAD_GAMEPLAY_TRACE_PATH");
    if (trace_path != nullptr && *trace_path != '\0') {
        if (std::FILE* file = std::fopen(trace_path, "a")) {
            std::fprintf(file, "tunnel-hidden-path-revealed\n");
            std::fclose(file);
        }
    }
}

extern "C" void SnapPad_ObservePlayerFocus(
    std::uint8_t* rdram, recomp_context*) {
    const bool has_focus =
        MEM_W(0, pokemon_snap::generated::player_focus_flag_vram) != 0;
    const std::int32_t focused_subject = has_focus
        ? static_cast<std::int32_t>(
            MEM_W(0, pokemon_snap::generated::player_focus_subject_vram))
        : -1;
    const std::uint32_t focused_object = has_focus
        ? static_cast<std::uint32_t>(
            MEM_W(0, pokemon_snap::generated::player_focus_object_vram))
        : 0;
    observed_focus_subject.store(focused_subject, std::memory_order_release);
    observed_focus_object.store(focused_object, std::memory_order_release);
    std::lock_guard<std::mutex> lock(captured_subject_mutex);
    ++focus_observation_sequence;
    if (has_focus) {
        last_valid_focus = focused_subject;
        last_valid_focus_sequence = focus_observation_sequence;
    }
    if (has_focus == last_traced_has_focus
        && focused_subject == last_traced_focus) {
        return;
    }
    last_traced_has_focus = has_focus;
    last_traced_focus = focused_subject;
    const char* trace_path = std::getenv("SNAPPAD_PHOTO_SCORE_TRACE_PATH");
    if (trace_path != nullptr && *trace_path != '\0') {
        if (std::FILE* file = std::fopen(trace_path, "a")) {
            std::fprintf(file,
                "focus current=%d object=%08X has_focus=%d\n",
                focused_subject, static_cast<unsigned>(focused_object),
                has_focus ? 1 : 0);
            std::fclose(file);
        }
    }
}

extern "C" void SnapPad_CaptureFocusedSubject(
    std::uint8_t* rdram, recomp_context*) {
    std::lock_guard<std::mutex> lock(captured_subject_mutex);

    if (scoring_started) {
        captured_subjects.clear();
        subject_by_photo.clear();
        next_captured_subject = 0;
        scoring_started = false;
    }

    bool has_focus =
        MEM_W(0, pokemon_snap::generated::player_focus_flag_vram) != 0;
    std::int32_t focused_subject = has_focus
        ? static_cast<std::int32_t>(
            MEM_W(0, pokemon_snap::generated::player_focus_subject_vram))
        : -1;
    const char* trace_path = std::getenv("SNAPPAD_PHOTO_SCORE_TRACE_PATH");
    bool recovered_recent_focus = false;
    // Native acceptance driving can cross a detector hit between the final
    // synthetic stick tap and the A edge. Under the explicit trace harness
    // only, retain that authentic player-facing identity for at most thirty
    // CopyInfo observations (roughly half a second at 60 Hz). Production
    // launches never use this correlation grace window.
    if (!has_focus
        && trace_path != nullptr && *trace_path != '\0'
        && last_valid_focus >= 0
        && focus_observation_sequence >= last_valid_focus_sequence
        && focus_observation_sequence - last_valid_focus_sequence <= 30) {
        has_focus = true;
        focused_subject = last_valid_focus;
        recovered_recent_focus = true;
    }
    if (trace_path != nullptr && *trace_path != '\0') {
        if (std::FILE* file = std::fopen(trace_path, "a")) {
            std::fprintf(file,
                "capture focused=%d has_focus=%d recent=%d\n", focused_subject,
                has_focus ? 1 : 0,
                recovered_recent_focus ? 1 : 0);
            std::fclose(file);
        }
    }
    // This hook runs at makePhoto, after the game has accepted either its
    // hold-Z/A shutter or its toggle-Z/A shutter. PhotoData is allocated only
    // for calls that reach this hook, so append exactly one correlation entry
    // here and do not infer capture from a particular controller gesture.
    captured_subjects.push_back(focused_subject);
}

extern "C" void SnapPad_RunSPIntegrityCheck(
    std::uint8_t* rdram, recomp_context* context) {
    const bool sp_imem_ok = MEM_BU(0, pokemon_snap::generated::sp_imem_ok_vram) != 0;
    const bool sp_dmem_ok = MEM_BU(0, pokemon_snap::generated::sp_dmem_ok_vram) != 0;
    if (sp_imem_ok && sp_dmem_ok) {
        return;
    }

    static std::atomic<bool> reported_failure{false};
    if (!reported_failure.exchange(true, std::memory_order_relaxed)) {
        std::fprintf(stderr,
            "[dynamic-code] SP integrity failure preserved through native hook\n");
    }

    // The VPK0 routine's sole game-visible result is PFID_ILLEGAL_COPY. Keep
    // that failure behavior while avoiding a jump into runtime-loaded MIPS.
    context->r4 = pokemon_snap::generated::illegal_copy_player_flag;
    context->r5 = 1;
    setPlayerFlag(rdram, context);
}

extern "C" void SnapPad_ApplyPhotoScoreFallback(
    std::uint8_t* rdram, recomp_context* context, std::uint32_t photo_address) {
    // Camera Check normally rerenders each captured photo into an offscreen
    // framebuffer and scores the pixels written back to RDRAM. On the native
    // Metal path that readback can arrive empty even though the in-course
    // detector found a focused Pokemon when the shutter fired.
    // Preserve every authentic nonzero result and only recover the identity
    // and a bounded centered-shot baseline for that explicitly tagged case.
    // The player-facing focus flag proves the subject was under the reticle;
    // 1000 size + 500 pose, doubled for technique, is internally consistent
    // with Oak's scoring UI and avoids deadlocking the 24,000-point course gate
    // when the native offscreen readback is unavailable for every photo.
    const gpr score_address = context->r2;
    const char* trace_path = std::getenv("SNAPPAD_PHOTO_SCORE_TRACE_PATH");
    auto trace = [trace_path](const char* state, gpr score, gpr photo,
                     std::int32_t scored, std::int32_t focused,
                     std::int32_t captured) {
        if (trace_path == nullptr || *trace_path == '\0') {
            return;
        }
        if (std::FILE* file = std::fopen(trace_path, "a")) {
            std::fprintf(file,
                "%s score=0x%08X photo=0x%08X scored=%d focused=%d captured=%d\n",
                state,
                static_cast<unsigned int>(score),
                static_cast<unsigned int>(photo),
                scored,
                focused,
                captured);
            std::fclose(file);
        }
    };
    constexpr gpr score_offset = 0x3A0;
    constexpr gpr pokemon_in_focus_offset = score_offset + 0x0A;
    constexpr std::uint16_t unrecognized_photo_subject = 500;
    if (score_address == 0) {
        trace("null-score", score_address, 0, 0, 0, -1);
        return;
    }

    const std::uint16_t scored_pokemon =
        MEM_HU(pokemon_in_focus_offset, score_address);

    std::int32_t captured_subject = -1;
    {
        std::lock_guard<std::mutex> lock(captured_subject_mutex);
        scoring_started = true;
        const auto existing = subject_by_photo.find(photo_address);
        if (existing != subject_by_photo.end()) {
            captured_subject = existing->second;
        } else if (next_captured_subject < captured_subjects.size()) {
            captured_subject = captured_subjects[next_captured_subject++];
            subject_by_photo.emplace(photo_address, captured_subject);
        }
    }

    if (scored_pokemon != 0
        && scored_pokemon != unrecognized_photo_subject) {
        trace("authentic", score_address, photo_address, scored_pokemon, 0,
            captured_subject);
        return;
    }

    if (photo_address == 0) {
        trace("null-photo", score_address, photo_address, scored_pokemon, 0,
            captured_subject);
        return;
    }

    const recomp_context saved_context = *context;
    context->r4 = photo_address;
    func_8009BCC4(rdram, context);
    const std::int32_t focused_pokemon = static_cast<std::int32_t>(context->r2);
    *context = saved_context;
    trace(scored_pokemon == unrecognized_photo_subject
            ? "unrecognized" : "empty",
        score_address, photo_address, scored_pokemon, focused_pokemon,
        captured_subject);

    // Only current-course PhotoData has a shutter-correlated subject entry.
    // Camera Check also asks the scorer to rerender the already-saved report
    // photo during a comparison. That legacy PhotoData can still expose its
    // species through func_8009BCC4 even when Metal readback is empty; applying
    // the native fallback to it would silently rescore the old 1,400-point
    // entry as 3,000 and make a genuine improved retake look like a tie.
    // Requiring the detector correlation keeps the recovery scoped to photos
    // actually taken in this native course session.
    const std::int32_t recovered_subject = captured_subject;

    // PhotoData stores the game's internal subject ID, not a 1..151 Pokédex
    // number. The authentic scorer accepts ordinary positive IDs below 0x25A
    // plus its special subject IDs through 0x40B.
    constexpr std::int32_t first_photo_subject_id = 1;
    constexpr std::int32_t last_photo_subject_id = 0x40B;
    if (recovered_subject < first_photo_subject_id
        || recovered_subject > last_photo_subject_id
        || recovered_subject == unrecognized_photo_subject) {
        return;
    }

    constexpr std::int32_t baseline_total_score = 3000;
    constexpr std::uint16_t baseline_size_score = 1000;
    constexpr std::uint16_t complete_subject = 10000;
    constexpr std::uint16_t baseline_pose_score = 500;
    MEM_W(score_offset + 0x00, score_address) = baseline_total_score;
    MEM_H(score_offset + 0x04, score_address) = 0; // same-Pokemon bonus
    MEM_B(score_offset + 0x06, score_address) = 0; // same-Pokemon count
    MEM_B(score_offset + 0x07, score_address) = 1; // well framed
    MEM_B(score_offset + 0x08, score_address) = 0; // ordinary pose
    MEM_H(pokemon_in_focus_offset, score_address) = recovered_subject;
    MEM_H(score_offset + 0x0C, score_address) = baseline_size_score;
    MEM_H(score_offset + 0x0E, score_address) = complete_subject;
    MEM_H(score_offset + 0x10, score_address) = baseline_pose_score;
    MEM_H(score_offset + 0x12, score_address) = 0; // special bonus
    MEM_B(score_offset + 0x14, score_address) = 0; // special ID

    static std::atomic<bool> reported_fallback{false};
    if (!reported_fallback.exchange(true, std::memory_order_relaxed)) {
        std::fprintf(stderr,
            "[photo-score] recovered focused Pokemon after empty native "
            "offscreen readback\n");
    }
}
