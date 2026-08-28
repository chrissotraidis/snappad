#!/usr/bin/env python3
"""Verify SnapPad's runner is the audited game-neutral PaperPad derivation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "ref/paperpad/src/paperpad_main.cpp"
ACTUAL = ROOT / "port/runtime/snappad_runner.cpp"
LOCKED_COMMIT = "74b6e45830a06c7f274c5ac1ddd7c625bc13a557"


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def replace_required(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        fail(f"PaperPad runner drifted at {label}: expected one match, found {count}")
    return source.replace(old, new)


def render_expected(source: str) -> str:
    source = replace_required(
        source,
        "#include <cstdlib>\n",
        "#include <cstdlib>\n#include <cstring>\n",
        "acceptance auto-shutter string include",
    )
    source = replace_required(
        source,
        "#include <filesystem>\n",
        "#include <filesystem>\n#include <fstream>\n#include <iterator>\n",
        "reloadable deterministic route includes",
    )
    source = replace_required(
        source, '#include "builtin_texture_pack.h"\n', "", "texture-pack include")
    source = replace_required(
        source,
        '#include "paper_rt64_context.h"',
        '#include "snappad_rt64_context.h"\n'
        '#include "game_registration.h"\n'
        '#include "n64_input_policy.h"\n'
        '#include "register_overlays.h"\n'
        '#include "snappad_game_hooks.h"\n'
        '#include "snappad_game_metadata.h"',
        "SnapPad runtime includes",
    )
    source = replace_required(
        source,
        '#include "controller_slots.h"',
        '#include "controller_slots.h"\n#include "test_input_replay.h"',
        "deterministic input replay include",
    )
    source = replace_required(
        source,
        "namespace paper_mario {\n    void register_overlays();\n}\n\n",
        "",
        "overlay forward declaration",
    )
    source = replace_required(source, "extern RspUcodeFunc n_aspMain;", "extern RspUcodeFunc aspMain;", "audio RSP symbol")
    source = replace_required(source, "gpr get_entrypoint_address();\n", "", "literal entrypoint declaration")

    for line in (
        "    constexpr uint64_t paper_mario_us_xxh3 = 0x1A478F060D5194CFULL;\n",
        "    constexpr gpr paper_mario_game_status_vram = 0x80074024;\n",
        "    constexpr gpr paper_mario_player_status_vram = 0x8010EFC8;\n",
        "    constexpr gpr paper_mario_current_npc_list_vram = 0x800A0B90;\n",
        "    constexpr gpr paper_mario_current_save_file_vram = 0x800DACC0;\n",
        "    constexpr gpr paper_mario_partner_npc_vram = 0x8010C930;\n",
        "    constexpr gpr paper_mario_world_script_list_vram = 0x802DA490;\n",
        "    std::atomic<uint64_t> game_loop_count{0};\n",
        "    std::atomic<uint64_t> last_game_loop_ms{0};\n",
        "    std::atomic<bool> play_session_active{true};\n",
        "    std::atomic<bool> play_session_watchdog_started{false};\n",
    ):
        source = replace_required(source, line, "", line.strip())

    trace_start = source.find("    struct PlayTraceState {")
    trace_end = source.find("    void report_controller_changes(", trace_start)
    if trace_start < 0 or trace_end < 0:
        fail("Paper Mario scene/watchdog trace block could not be isolated")
    source = source[:trace_start] + source[trace_end:]
    exported_trace_start = source.find('extern "C" void paperpad_trace_game_loop(')
    exported_trace_end = source.find("// Touch bridge (Apple shell).", exported_trace_start)
    if exported_trace_start < 0 or exported_trace_end < 0:
        fail("Paper Mario exported trace hook could not be isolated")
    source = source[:exported_trace_start] + source[exported_trace_end:]

    source = source.replace("paperpad::input", "snappad::input")
    source = source.replace("paperpad_", "snappad_")
    source = source.replace("PaperPad_", "SnapPad_")
    source = source.replace("PaperPad", "SnapPad")
    source = source.replace("paper_rt64_context", "snappad_rt64_context")
    source = source.replace("paper_mario::renderer", "pokemon_snap::renderer")
    source = source.replace("paper_mario::register_overlays()", "pokemon_snap::register_overlays()")
    source = source.replace("return n_aspMain;", "return aspMain;")
    source = source.replace('return "PM " +', 'return "SNAP " +')
    source = source.replace("pm.n64.us.z64", "pokemonsnap.n64.us.z64")
    source = source.replace('u8"pm.n64.us"', 'u8"pokemonsnap.n64.us"')
    source = source.replace("Paper Mario (U)", "Pokémon Snap (USA)")
    source = source.replace("Paper Mario (US) 1.0", "Pokémon Snap (USA)")
    source = source.replace("US Paper Mario ROM", "US Pokémon Snap ROM")
    source = source.replace("That Paper Mario ROM", "That Pokémon Snap ROM")
    source = source.replace(
        "supported US version. Please choose Paper Mario (U).",
        "supported US version. Please choose Pokémon Snap (USA).",
    )
    source = source.replace("legally dumped Paper Mario", "legally dumped Pokémon Snap")

    source = replace_required(
        source,
        '''        // One-shot delayed diagnostics (post-swapchain-resize state).
        void* diag_window = wm_info.info.uikit.window;
        void* diag_layer = ios_layer;
        std::thread([diag_window, diag_layer]() {
            for (int i = 0; i < 5; ++i) {
                std::this_thread::sleep_for(std::chrono::seconds(5));
                snappad_log_window_diagnostics(diag_window, diag_layer);
            }
        }).detach();''',
        '''        // Repeated UIKit/CAMetal state probes can synchronize with the UI and
        // present threads in Simulator. Keep the useful startup snapshot, but
        // make delayed diagnostic polling opt-in instead of ordinary gameplay
        // work.
        const char* window_trace = std::getenv("SNAPPAD_WINDOW_TRACE");
        if (window_trace != nullptr && window_trace[0] != '0') {
            void* diag_window = wm_info.info.uikit.window;
            void* diag_layer = ios_layer;
            std::thread([diag_window, diag_layer]() {
                for (int i = 0; i < 5; ++i) {
                    std::this_thread::sleep_for(std::chrono::seconds(5));
                    snappad_log_window_diagnostics(diag_window, diag_layer);
                }
            }).detach();
        }''',
        "opt-in delayed window diagnostics",
    )

    source = replace_required(
        source,
        "    SDL_AudioDeviceID audio_device = 0;\n"
        "    SDL_AudioStream* audio_stream = nullptr;",
        "    SDL_AudioDeviceID audio_device = 0;\n"
        "    SDL_AudioStream* audio_stream = nullptr;\n"
        "    std::atomic<bool> app_backgrounded{false};",
        "iOS lifecycle audio state",
    )
    source = replace_required(
        source,
        '    ultramodern::gfx_callbacks_t::gfx_data_t create_gfx() {\n'
        '        SDL_SetHint(SDL_HINT_GAMECONTROLLER_USE_BUTTON_LABELS, "0");\n',
        '    ultramodern::gfx_callbacks_t::gfx_data_t create_gfx() {\n'
        '        SDL_SetHint(SDL_HINT_GAMECONTROLLER_USE_BUTTON_LABELS, "0");\n'
        '#if defined(__APPLE__) && TARGET_OS_IPHONE\n'
        '        // SnapPad is an interactive game, not a background-audio player.\n'
        '        // Ambient makes iOS silence/deactivate the session when the app loses\n'
        "        // the foreground instead of SDL's default Playback category keeping\n"
        '        // the process and audio callbacks alive behind the Home screen.\n'
        '        SDL_SetHint(SDL_HINT_AUDIO_CATEGORY, "ambient");\n'
        '#endif\n',
        "iOS ambient audio category",
    )
    source = replace_required(
        source,
        '''            else if (event.type == SDL_APP_DIDENTERFOREGROUND) {
                std::fprintf(stderr,
                    "[input t=%.3fs] foreground resume: reconciling controllers\\n",
                    play_session_ms() / 1000.0);
                reconcile_controllers("foreground-resume");
            }
''',
        '''            else if (event.type == SDL_APP_WILLENTERBACKGROUND
                || event.type == SDL_APP_DIDENTERBACKGROUND) {
                if (!app_backgrounded.exchange(true, std::memory_order_acq_rel)) {
                    if (audio_device != 0) {
                        SDL_PauseAudioDevice(audio_device, 1);
                        SDL_ClearQueuedAudio(audio_device);
                    }
                    std::fprintf(stderr,
                        "[lifecycle t=%.3fs] background: audio paused and queue cleared\\n",
                        play_session_ms() / 1000.0);
                }
            }
            else if (event.type == SDL_APP_DIDENTERFOREGROUND) {
                const bool was_backgrounded =
                    app_backgrounded.exchange(false, std::memory_order_acq_rel);
                if (audio_device != 0) {
                    SDL_ClearQueuedAudio(audio_device);
                    SDL_PauseAudioDevice(audio_device, 0);
                }
                std::fprintf(stderr,
                    "[lifecycle t=%.3fs] foreground: audio resumed, controllers reconciling (was_backgrounded=%d)\\n",
                    play_session_ms() / 1000.0,
                    was_backgrounded ? 1 : 0);
                reconcile_controllers("foreground-resume");
            }
''',
        "iOS background audio lifecycle",
    )
    source = replace_required(
        source,
        "        SDL_PauseAudioDevice(audio_device, 0);\n"
        "        output_sample_rate = output_freq;",
        "        SDL_PauseAudioDevice(\n"
        "            audio_device,\n"
        "            app_backgrounded.load(std::memory_order_acquire) ? 1 : 0);\n"
        "        output_sample_rate = output_freq;",
        "background-aware audio reset",
    )
    source = replace_required(
        source,
        "        if (audio_device == 0 || sample_count == 0) {",
        "        if (audio_device == 0 || sample_count == 0\n"
        "            || app_backgrounded.load(std::memory_order_acquire)) {",
        "background audio discard",
    )
    source = replace_required(
        source,
        "    size_t get_frames_remaining() {\n"
        "        if (audio_device == 0) {",
        "    size_t get_frames_remaining() {\n"
        "        if (audio_device == 0\n"
        "            || app_backgrounded.load(std::memory_order_acquire)) {",
        "background audio feedback",
    )

    source = replace_required(
        source,
        "    bool has_previous_output_frame = false;\n",
        '''    bool has_previous_output_frame = false;

    bool audio_telemetry_enabled() {
        static const bool enabled = []() {
            const char* audio_trace = std::getenv("SNAPPAD_AUDIO_TRACE");
            return audio_trace != nullptr && audio_trace[0] != '\\0'
                && std::strcmp(audio_trace, "0") != 0;
        }();
        return enabled;
    }
''',
        "opt-in audio telemetry gate",
    )
    source = replace_required(
        source,
        '''        static std::vector<float> source_buffer;
        static std::vector<float> converted_buffer;

        const auto callback_now = std::chrono::steady_clock::now();
        if (previous_audio_callback.time_since_epoch().count() != 0) {
            const uint64_t callback_gap_us = static_cast<uint64_t>(
                std::chrono::duration_cast<std::chrono::microseconds>(
                    callback_now - previous_audio_callback).count());
            audio_telemetry.max_callback_gap_us = std::max(
                audio_telemetry.max_callback_gap_us, callback_gap_us);
        }
        previous_audio_callback = callback_now;
''',
        '''        static std::vector<float> source_buffer;
        static std::vector<float> converted_buffer;
        const bool collect_audio_telemetry = audio_telemetry_enabled();

        if (collect_audio_telemetry) {
            const auto callback_now = std::chrono::steady_clock::now();
            if (previous_audio_callback.time_since_epoch().count() != 0) {
                const uint64_t callback_gap_us = static_cast<uint64_t>(
                    std::chrono::duration_cast<std::chrono::microseconds>(
                        callback_now - previous_audio_callback).count());
                audio_telemetry.max_callback_gap_us = std::max(
                    audio_telemetry.max_callback_gap_us, callback_gap_us);
            }
            previous_audio_callback = callback_now;
        }
''',
        "audio callback timing gate",
    )
    source = replace_required(
        source,
        '''            audio_telemetry.peak_input = std::max(
                audio_telemetry.peak_input,
                static_cast<uint32_t>(std::max(
                    std::abs(static_cast<int32_t>(audio_data[i + 0])),
                    std::abs(static_cast<int32_t>(audio_data[i + 1])))));
''',
        '''            if (collect_audio_telemetry) {
                audio_telemetry.peak_input = std::max(
                    audio_telemetry.peak_input,
                    static_cast<uint32_t>(std::max(
                        std::abs(static_cast<int32_t>(audio_data[i + 0])),
                        std::abs(static_cast<int32_t>(audio_data[i + 1])))));
            }
''',
        "audio peak scan gate",
    )
    if source.count("            audio_telemetry.conversion_errors++;\n") != 3:
        fail("PaperPad runner drifted at audio conversion telemetry counters")
    source = source.replace(
        "            audio_telemetry.conversion_errors++;\n",
        "            if (collect_audio_telemetry) audio_telemetry.conversion_errors++;\n",
    )
    source = replace_required(
        source,
        '''        audio_telemetry.callbacks++;
        audio_telemetry.input_frames += sample_count / input_channels;
        audio_telemetry.output_frames +=
            queue_bytes / (output_channels * sizeof(float));
        audio_telemetry.min_prequeue_us = std::min(
            audio_telemetry.min_prequeue_us, queued_input_us);
        if (queued_input_us == 0) {
            audio_telemetry.zero_prequeue_callbacks++;
        }
        if (queued_input_us < 5000) {
            audio_telemetry.under_5ms_prequeue_callbacks++;
        }
        audio_telemetry.peak_queue_us = std::max(audio_telemetry.peak_queue_us, queued_input_us);
        if (queued_input_us >= 100000) audio_telemetry.over_100ms_callbacks++;
''',
        '''        if (collect_audio_telemetry) {
            audio_telemetry.callbacks++;
            audio_telemetry.input_frames += sample_count / input_channels;
            audio_telemetry.output_frames +=
                queue_bytes / (output_channels * sizeof(float));
            audio_telemetry.min_prequeue_us = std::min(
                audio_telemetry.min_prequeue_us, queued_input_us);
            if (queued_input_us == 0) {
                audio_telemetry.zero_prequeue_callbacks++;
            }
            if (queued_input_us < 5000) {
                audio_telemetry.under_5ms_prequeue_callbacks++;
            }
            audio_telemetry.peak_queue_us = std::max(
                audio_telemetry.peak_queue_us, queued_input_us);
            if (queued_input_us >= 100000) audio_telemetry.over_100ms_callbacks++;
        }
''',
        "audio queue statistics gate",
    )
    source = replace_required(
        source,
        "            if (output_frame_count != 0) {\n",
        "            if (collect_audio_telemetry && output_frame_count != 0) {\n",
        "audio discontinuity scan gate",
    )
    source = replace_required(
        source,
        "                audio_telemetry.queue_errors++;\n",
        "                if (collect_audio_telemetry) audio_telemetry.queue_errors++;\n",
        "audio queue error counter gate",
    )
    source = replace_required(
        source,
        '''        const uint64_t queued_output_us =
            uint64_t(SDL_GetQueuedAudioSize(audio_device)) /
            (output_channels * sizeof(float)) * 1000000 / output_sample_rate;
        audio_telemetry.peak_queue_us = std::max(audio_telemetry.peak_queue_us, queued_output_us);
        report_audio_telemetry(queued_output_us);
''',
        '''        if (collect_audio_telemetry) {
            const uint64_t queued_output_us =
                uint64_t(SDL_GetQueuedAudioSize(audio_device)) /
                (output_channels * sizeof(float)) * 1000000 / output_sample_rate;
            audio_telemetry.peak_queue_us = std::max(
                audio_telemetry.peak_queue_us, queued_output_us);
            report_audio_telemetry(queued_output_us);
        }
''',
        "audio reporting gate",
    )

    source = replace_required(
        source,
        """    ultramodern::input::connected_device_info_t get_connected_device_info(int controller_num) {
        if (controller_num != 0) {
            return { ultramodern::input::Device::None, ultramodern::input::Pak::None };
        }
        return { ultramodern::input::Device::Controller, ultramodern::input::Pak::RumblePak };
    }
""",
        """    ultramodern::input::connected_device_info_t get_connected_device_info(int controller_num) {
        return snappad::input::runtime_connected_device_info(controller_num);
    }
""",
        "accessory callback",
    )

    registration_start = source.find('    std::u8string game_id = u8"pokemonsnap.n64.us";')
    registration_end = source.find("\n\n    recomp::register_config_path", registration_start)
    if registration_start < 0 or registration_end < 0:
        fail("Paper Mario game registration block could not be isolated")
    registration = """    std::u8string game_id = pokemon_snap::generated::game_id;
    recomp::GameEntry pokemon_snap_us = pokemon_snap::make_game_entry(
        pokemon_snap::generated::rom_xxh3,
        pokemon_snap::generated::internal_name,
        game_id,
        pokemon_snap::generated::entrypoint,
        recomp_entrypoint);"""
    source = source[:registration_start] + registration + source[registration_end:]
    source = replace_required(source, "recomp::register_game(paper_mario_us);", "recomp::register_game(pokemon_snap_us);", "game registration call")
    source = replace_required(
        source,
        """    recomp::register_game(pokemon_snap_us);
    pokemon_snap::register_overlays();""",
        """    recomp::register_game(pokemon_snap_us);
    std::fprintf(stderr,
        "[core] registered Pokémon Snap US: xxh3=%016llX entrypoint=0x%08X save=flashram\\n",
        static_cast<unsigned long long>(pokemon_snap::generated::rom_xxh3),
        pokemon_snap::generated::entrypoint);
    pokemon_snap::register_overlays();""",
        "core registration breadcrumb",
    )
    source = replace_required(
        source,
        """        if (task->t.type == M_AUDTASK) {
            return aspMain;
        }""",
        """        if (task->t.type == M_AUDTASK) {
            static std::atomic<bool> announced_audio_rsp{false};
            if (!announced_audio_rsp.exchange(true, std::memory_order_relaxed)) {
                std::fprintf(stderr, "[rsp] first audio task routed to verified aspMain\\n");
            }
            return aspMain;
        }""",
        "audio RSP breadcrumb",
    )
    source = replace_required(source, "    paper_mario::ensure_builtin_texture_pack(app_config_path() / \"builtin_textures\");\n\n", "", "texture-pack call")
    source = replace_required(source, "    play_session_active.store(false, std::memory_order_relaxed);\n\n", "", "watchdog shutdown")
    source = source.replace(
        "//   image_filter:    reserved; SnapPad uses the stable smooth path",
        "//   image_filter:    reserved until Pokemon Snap renderer testing",
    )
    source = replace_required(
        source,
        "// SnapPad native runner.",
        "// SnapPad native runner.\n//\n"
        "// Derived from the pinned PaperPad runner, with Paper Mario-specific scene\n"
        "// tracing, frame hooks, accessory policy, game identity, and texture hooks\n"
        "// removed. Renderer policy is supplied by SnapPad separately and must be\n"
        "// validated against Pokemon Snap before gameplay acceptance.",
        "provenance header",
    )
    source = replace_required(
        source,
        """                        keyboard_tap_latches[i].store(4, std::memory_order_release);
                    }
                }
""",
        """                        auto& latch = keyboard_tap_latches[i];
                        uint8_t remaining = latch.load(std::memory_order_acquire);
                        while (remaining < 4
                            && !latch.compare_exchange_weak(
                                remaining, 4,
                                std::memory_order_acq_rel,
                                std::memory_order_acquire)) {
                        }
                    }
                }
                // Computer-driven acceptance runs cannot keep a modifier key
                // physically held. When explicitly enabled, the otherwise
                // unmapped F6 key latches only the N64 Z trigger for a bounded
                // number of input polls so a subsequent A press can exercise
                // the real shutter path. F8 releases that test-only latch so
                // computer-driven acceptance can inspect the held viewfinder,
                // aim, fire, and return to ordinary controls deterministically.
                // Ordinary builds and launches retain PaperPad's exact
                // keyboard behavior.
                const char* test_z_hold = std::getenv(\"SNAPPAD_TEST_Z_HOLD_POLLS\");
                if (test_z_hold != nullptr
                    && event.key.keysym.scancode == SDL_SCANCODE_F6) {
                    char* end = nullptr;
                    const long requested = std::strtol(test_z_hold, &end, 10);
                    if (end != test_z_hold && *end == '\\0'
                        && requested >= 4 && requested <= 1'000'000) {
                        test_z_hold_polls.store(
                            static_cast<uint32_t>(requested), std::memory_order_release);
                        std::fprintf(stderr,
                            \"[test-input] latched Z trigger for %ld polls\\n\", requested);
                    }
                }
                else if (event.key.keysym.scancode == SDL_SCANCODE_F8) {
                    test_z_hold_polls.store(0, std::memory_order_release);
                    test_auto_shutter_armed.store(false, std::memory_order_release);
                    test_auto_shutter_sweep_polls.store(0, std::memory_order_release);
                    std::fprintf(stderr,
                        \"[test-input] released latched Z trigger and disarmed auto-shutter\\n\");
                }
                const char* test_auto_shutter = std::getenv(\"SNAPPAD_TEST_AUTO_SHUTTER\");
                if (test_auto_shutter != nullptr
                    && *test_auto_shutter != '\\0'
                    && std::strcmp(test_auto_shutter, \"0\") != 0
                    && event.key.keysym.scancode == SDL_SCANCODE_F9) {
                    test_auto_shutter_sweep_polls.store(0, std::memory_order_release);
                    test_auto_shutter_armed.store(true, std::memory_order_release);
                    std::fprintf(stderr,
                        \"[test-input] armed auto-shutter\\n\");
                }
                if (event.key.keysym.scancode == SDL_SCANCODE_F7) {
                    if (!test_input_replay_file_path.empty()) {
                        if (install_test_input_replay_file(false)) {
                            std::fprintf(stderr,
                                \"[test-input] deterministic route reloaded and started by F7\\n\");
                        }
                    }
                    else if (test_input_replay.has_value()
                        && test_input_replay_waiting_for_trigger) {
                        test_input_replay_waiting_for_trigger = false;
                        std::fprintf(stderr,
                            \"[test-input] deterministic route started by F7\\n\");
                    }
                }
""",
        "bounded computer-driven Z-trigger latch",
    )
    source = replace_required(
        source,
        "    std::atomic<bool> graphics_settings_applied{false};",
        """    std::atomic<bool> graphics_settings_applied{false};
    std::atomic<uint32_t> test_z_hold_polls{0};
    std::atomic<bool> test_auto_shutter_armed{false};
    std::atomic<uint32_t> test_auto_shutter_sweep_polls{0};
    std::optional<snappad::testing::TestInputReplay> test_input_replay;
    bool test_input_replay_waiting_for_trigger = false;
    std::string test_input_replay_file_path;

    bool install_test_input_replay(
        const std::string& specification, bool waiting_for_trigger,
        const char* source) {
        std::string error;
        auto replay = snappad::testing::TestInputReplay::parse(specification, error);
        if (!replay.has_value()) {
            std::fprintf(stderr,
                \"[test-input] invalid deterministic route from %s: %s\\n\",
                source, error.c_str());
            return false;
        }

        test_input_replay_waiting_for_trigger = waiting_for_trigger;
        std::fprintf(stderr,
            \"[test-input] armed deterministic route from %s: steps=%zu polls=%llu trigger=%s\\n\",
            source,
            replay->step_count(),
            static_cast<unsigned long long>(replay->total_polls()),
            test_input_replay_waiting_for_trigger ? \"F7\" : \"immediate\");
        test_input_replay = std::move(*replay);
        return true;
    }

    bool install_test_input_replay_file(bool waiting_for_trigger) {
        std::ifstream input(test_input_replay_file_path, std::ios::binary);
        if (!input) {
            std::fprintf(stderr,
                \"[test-input] could not open deterministic route file: %s\\n\",
                test_input_replay_file_path.c_str());
            return false;
        }
        const std::string specification{
            std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
        return install_test_input_replay(
            specification, waiting_for_trigger, test_input_replay_file_path.c_str());
    }

    bool initialize_test_input_replay() {
        const char* route_file = std::getenv(\"SNAPPAD_TEST_INPUT_ROUTE_FILE\");
        if (route_file != nullptr && route_file[0] != '\\0') {
            test_input_replay_file_path = route_file;
        }

        const char* specification = std::getenv(\"SNAPPAD_TEST_INPUT_ROUTE\");
        if (test_input_replay_file_path.empty()
            && (specification == nullptr || specification[0] == '\\0')) {
            return true;
        }

        const char* armed = std::getenv(\"SNAPPAD_TEST_INPUT_ROUTE_ARMED\");
        const bool waiting_for_trigger =
            armed != nullptr && armed[0] == '1' && armed[1] == '\\0';
        if (!test_input_replay_file_path.empty()) {
            return install_test_input_replay_file(waiting_for_trigger);
        }
        return install_test_input_replay(
            specification, waiting_for_trigger, \"SNAPPAD_TEST_INPUT_ROUTE\");
    }""",
        "deterministic input replay setup",
    )
    source = replace_required(
        source,
        """    std::atomic<uint32_t> test_z_hold_polls{0};
    std::atomic<bool> test_auto_shutter_armed{false};
    std::atomic<uint32_t> test_auto_shutter_sweep_polls{0};
    std::optional<snappad::testing::TestInputReplay> test_input_replay;
    bool test_input_replay_waiting_for_trigger = false;
    std::string test_input_replay_file_path;
""",
        """    std::atomic<uint32_t> test_z_hold_polls{0};
    std::atomic<bool> test_auto_shutter_armed{false};
    std::atomic<uint32_t> test_auto_shutter_sweep_polls{0};
    std::atomic<uint64_t> input_poll_count{0};
    std::optional<snappad::testing::TestInputReplay> test_input_replay;
    bool test_input_replay_waiting_for_trigger = false;
    std::string test_input_replay_file_path;

    struct PerformanceTelemetry {
        FILE* file = nullptr;
        std::chrono::steady_clock::time_point previous_report{};
        std::chrono::steady_clock::time_point next_report{};
        uint64_t previous_input_polls = 0;
        uint64_t previous_screen_updates = 0;
        uint64_t previous_presented_frames = 0;
        uint64_t previous_present_interval_count = 0;
        uint64_t previous_present_interval_total_us = 0;
        uint64_t previous_present_intervals_over_50_ms = 0;
        uint64_t previous_present_intervals_over_100_ms = 0;
    } performance_telemetry;

    void initialize_performance_telemetry() {
        const char* path = std::getenv(\"SNAPPAD_PERF_TRACE_PATH\");
        if (path == nullptr || path[0] == '\\0') return;

        performance_telemetry.file = std::fopen(path, \"w\");
        if (performance_telemetry.file == nullptr) {
            std::fprintf(stderr,
                \"[perf] could not open trace path: %s\\n\", path);
            return;
        }
        std::fprintf(performance_telemetry.file,
            \"session_ms,interval_ms,input_polls,input_hz,screen_updates,screen_hz,\"
            \"presented_frames,presented_hz,present_intervals,mean_present_interval_ms,\"
            \"max_present_interval_ms,present_intervals_over_50_ms,\"
            \"present_intervals_over_100_ms,display_hz,focused,minimized\\n\");
        std::fflush(performance_telemetry.file);
        std::fprintf(stderr, \"[perf] tracing frame cadence to %s\\n\", path);
    }

    void report_performance_telemetry() {
        if (performance_telemetry.file == nullptr) return;

        const auto now = std::chrono::steady_clock::now();
        uint64_t screen_updates = 0;
        uint64_t presented_frames = 0;
        uint32_t display_hz = 0;
        SnapPad_GetFrameTelemetry(
            &screen_updates, &presented_frames, &display_hz);
        const uint64_t input_polls =
            input_poll_count.load(std::memory_order_relaxed);

        if (performance_telemetry.previous_report.time_since_epoch().count() == 0) {
            uint64_t interval_count = 0;
            uint64_t interval_total_us = 0;
            uint64_t interval_max_us = 0;
            uint64_t intervals_over_50_ms = 0;
            uint64_t intervals_over_100_ms = 0;
            SnapPad_TakePresentIntervalTelemetry(
                &interval_count, &interval_total_us, &interval_max_us,
                &intervals_over_50_ms, &intervals_over_100_ms);
            performance_telemetry.previous_report = now;
            performance_telemetry.next_report = now + std::chrono::seconds(1);
            performance_telemetry.previous_input_polls = input_polls;
            performance_telemetry.previous_screen_updates = screen_updates;
            performance_telemetry.previous_presented_frames = presented_frames;
            performance_telemetry.previous_present_interval_count = interval_count;
            performance_telemetry.previous_present_interval_total_us = interval_total_us;
            performance_telemetry.previous_present_intervals_over_50_ms = intervals_over_50_ms;
            performance_telemetry.previous_present_intervals_over_100_ms = intervals_over_100_ms;
            return;
        }
        if (now < performance_telemetry.next_report) return;

        uint64_t interval_count = 0;
        uint64_t interval_total_us = 0;
        uint64_t interval_max_us = 0;
        uint64_t intervals_over_50_ms = 0;
        uint64_t intervals_over_100_ms = 0;
        SnapPad_TakePresentIntervalTelemetry(
            &interval_count, &interval_total_us, &interval_max_us,
            &intervals_over_50_ms, &intervals_over_100_ms);

        const uint64_t interval_ms = static_cast<uint64_t>(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                now - performance_telemetry.previous_report).count());
        if (interval_ms == 0) return;
        const uint64_t input_delta =
            input_polls - performance_telemetry.previous_input_polls;
        const uint64_t screen_delta =
            screen_updates - performance_telemetry.previous_screen_updates;
        const uint64_t presented_delta =
            presented_frames - performance_telemetry.previous_presented_frames;
        const uint64_t present_interval_delta =
            interval_count - performance_telemetry.previous_present_interval_count;
        const uint64_t present_interval_total_delta_us =
            interval_total_us - performance_telemetry.previous_present_interval_total_us;
        const uint64_t present_intervals_over_50_ms_delta =
            intervals_over_50_ms
            - performance_telemetry.previous_present_intervals_over_50_ms;
        const uint64_t present_intervals_over_100_ms_delta =
            intervals_over_100_ms
            - performance_telemetry.previous_present_intervals_over_100_ms;
        const double mean_present_interval_ms = present_interval_delta == 0
            ? 0.0
            : static_cast<double>(present_interval_total_delta_us)
                / static_cast<double>(present_interval_delta) / 1000.0;
        const double seconds = static_cast<double>(interval_ms) / 1000.0;
        const Uint32 flags = window != nullptr ? SDL_GetWindowFlags(window) : 0;
        const int focused = (flags & SDL_WINDOW_INPUT_FOCUS) != 0 ? 1 : 0;
        const int minimized = (flags & SDL_WINDOW_MINIMIZED) != 0 ? 1 : 0;

        std::fprintf(performance_telemetry.file,
            \"%llu,%llu,%llu,%.3f,%llu,%.3f,%llu,%.3f,\"
            \"%llu,%.3f,%.3f,%llu,%llu,%u,%d,%d\\n\",
            static_cast<unsigned long long>(play_session_ms()),
            static_cast<unsigned long long>(interval_ms),
            static_cast<unsigned long long>(input_delta), input_delta / seconds,
            static_cast<unsigned long long>(screen_delta), screen_delta / seconds,
            static_cast<unsigned long long>(presented_delta), presented_delta / seconds,
            static_cast<unsigned long long>(present_interval_delta),
            mean_present_interval_ms,
            static_cast<double>(interval_max_us) / 1000.0,
            static_cast<unsigned long long>(present_intervals_over_50_ms_delta),
            static_cast<unsigned long long>(present_intervals_over_100_ms_delta),
            display_hz, focused, minimized);
        std::fflush(performance_telemetry.file);

        performance_telemetry.previous_report = now;
        performance_telemetry.next_report = now + std::chrono::seconds(1);
        performance_telemetry.previous_input_polls = input_polls;
        performance_telemetry.previous_screen_updates = screen_updates;
        performance_telemetry.previous_presented_frames = presented_frames;
        performance_telemetry.previous_present_interval_count = interval_count;
        performance_telemetry.previous_present_interval_total_us = interval_total_us;
        performance_telemetry.previous_present_intervals_over_50_ms = intervals_over_50_ms;
        performance_telemetry.previous_present_intervals_over_100_ms = intervals_over_100_ms;
    }
""",
        "opt-in frame cadence telemetry",
    )
    source = replace_required(
        source,
        """    bool test_input_replay_waiting_for_trigger = false;
    std::string test_input_replay_file_path;
""",
        """    bool test_input_replay_waiting_for_trigger = false;
    bool test_input_replay_waiting_for_tunnel_progress = false;
    bool test_input_replay_tunnel_target_assist = false;
    std::string test_input_replay_file_path;
""",
        "Tunnel progress route state",
    )
    source = replace_required(
        source,
        """            test_input_replay_waiting_for_trigger ? \"F7\" : \"immediate\");
""",
        """            test_input_replay_waiting_for_tunnel_progress
                ? \"tunnel-electrode-approach-window\"
                : (test_input_replay_waiting_for_trigger ? \"F7\" : \"immediate\"));
""",
        "Tunnel progress route description",
    )
    source = replace_required(
        source,
        """        const char* armed = std::getenv(\"SNAPPAD_TEST_INPUT_ROUTE_ARMED\");
        const bool waiting_for_trigger =
            armed != nullptr && armed[0] == '1' && armed[1] == '\\0';
""",
        """        const char* armed = std::getenv(\"SNAPPAD_TEST_INPUT_ROUTE_ARMED\");
        const bool f7_trigger =
            armed != nullptr && armed[0] == '1' && armed[1] == '\\0';
        const char* tunnel_progress =
            std::getenv(\"SNAPPAD_TEST_INPUT_ROUTE_TUNNEL_PROGRESS\");
        test_input_replay_waiting_for_tunnel_progress =
            tunnel_progress != nullptr
            && tunnel_progress[0] == '1'
            && tunnel_progress[1] == '\\0';
        test_input_replay_tunnel_target_assist =
            test_input_replay_waiting_for_tunnel_progress;
        const bool waiting_for_trigger =
            f7_trigger || test_input_replay_waiting_for_tunnel_progress;
""",
        "Tunnel progress route activation",
    )
    source = replace_required(
        source,
        """        bool controller_active = false;
""",
        """        uint32_t test_z_remaining = test_z_hold_polls.load(std::memory_order_acquire);
        while (test_z_remaining != 0) {
            if (test_z_hold_polls.compare_exchange_weak(
                    test_z_remaining, test_z_remaining - 1,
                    std::memory_order_acq_rel, std::memory_order_acquire)) {
                apply_input_action(
                    static_cast<int>(InputAction::Z), 1.0f,
                    out_buttons, out_x, out_y);
                break;
            }
        }

        // Computer-driven golden-path runs can hold the authentic viewfinder
        // and press A only when Pokémon Snap's own detector reports a subject.
        // This is input automation, not a score or progression shortcut: the
        // game still creates, selects, evaluates, and saves every photograph.
        const char* test_auto_shutter = std::getenv("SNAPPAD_TEST_AUTO_SHUTTER");
        static std::uint32_t auto_shutter_hold_polls = 0;
        static std::uint32_t auto_shutter_cooldown_polls = 0;
        static std::array<bool, 152> auto_shutter_captured_subjects{};
        static std::int32_t auto_shutter_locked_subject = -1;
        const char* test_auto_shutter_arm_on_item_subject =
            std::getenv("SNAPPAD_TEST_AUTO_SHUTTER_ARM_ON_ITEM_SUBJECT");
        const std::int32_t impacted_subject = SnapPad_ConsumeItemImpactSubject();
        if (impacted_subject > 0
            && test_auto_shutter_arm_on_item_subject != nullptr
            && *test_auto_shutter_arm_on_item_subject != '\\0') {
            char* end = nullptr;
            const long requested_subject = std::strtol(
                test_auto_shutter_arm_on_item_subject, &end, 10);
            if (end != test_auto_shutter_arm_on_item_subject
                && *end == '\\0'
                && requested_subject == impacted_subject) {
                test_auto_shutter_armed.store(true, std::memory_order_release);
                std::fprintf(stderr,
                    "[test-input] armed auto-shutter after item impact subject=%d\\n",
                    impacted_subject);
            }
        }
        if (!test_auto_shutter_armed.load(std::memory_order_acquire)) {
            auto_shutter_captured_subjects.fill(false);
            auto_shutter_locked_subject = -1;
        }
        if (test_auto_shutter_armed.load(std::memory_order_acquire)
            && test_auto_shutter != nullptr
            && *test_auto_shutter != '\\0'
            && std::strcmp(test_auto_shutter, "0") != 0) {
            const std::int32_t focused_subject = SnapPad_CurrentFocusedSubject();
            const bool photographable_subject =
                focused_subject > 0 && focused_subject <= 151;
            const bool uncaptured_photographable_subject =
                photographable_subject
                && !auto_shutter_captured_subjects[focused_subject];
            out_buttons |= Z_BUTTON;
            const char* test_auto_shutter_lock_subject =
                std::getenv("SNAPPAD_TEST_AUTO_SHUTTER_LOCK_SUBJECT");
            if (auto_shutter_locked_subject < 0
                && test_auto_shutter_lock_subject != nullptr
                && *test_auto_shutter_lock_subject != '\\0') {
                char* end = nullptr;
                const long requested_subject = std::strtol(
                    test_auto_shutter_lock_subject, &end, 10);
                if (end != test_auto_shutter_lock_subject
                    && *end == '\\0'
                    && requested_subject > 0
                    && requested_subject <= 151
                    && focused_subject == requested_subject) {
                    auto_shutter_locked_subject =
                        static_cast<std::int32_t>(requested_subject);
                    std::fprintf(stderr,
                        "[test-input] locked viewfinder on subject=%d\\n",
                        auto_shutter_locked_subject);
                }
            }
            if (auto_shutter_hold_polls != 0) {
                out_buttons |= A_BUTTON;
                --auto_shutter_hold_polls;
            } else if (auto_shutter_cooldown_polls != 0) {
                --auto_shutter_cooldown_polls;
            } else if (focused_subject > 0
                && focused_subject <= 151
                && !auto_shutter_captured_subjects[focused_subject]) {
                out_buttons |= A_BUTTON;
                auto_shutter_hold_polls = 2;
                auto_shutter_cooldown_polls = 45;
                auto_shutter_captured_subjects[focused_subject] = true;
                std::fprintf(stderr,
                    "[test-input] auto-shutter focused subject=%d\\n",
                    focused_subject);
            }

            // An opt-in acceptance sweep slowly scans the horizon whenever
            // the stock detector has no photographable subject. It pauses as
            // soon as a real Pokemon is focused, so the ordinary shutter path
            // still creates every submitted frame. Production launches never
            // set this environment variable and retain PaperPad input parity.
            const char* test_auto_shutter_sweep =
                std::getenv("SNAPPAD_TEST_AUTO_SHUTTER_SWEEP");
            const bool sweep_enabled = test_auto_shutter_sweep != nullptr
                && *test_auto_shutter_sweep != '\\0'
                && std::strcmp(test_auto_shutter_sweep, "0") != 0;
            if (sweep_enabled
                && auto_shutter_locked_subject < 0
                && !uncaptured_photographable_subject
                && auto_shutter_hold_polls == 0
                && std::abs(out_x) < 0.05f
                && std::abs(out_y) < 0.05f) {
                const std::uint32_t sweep_poll =
                    test_auto_shutter_sweep_polls.fetch_add(
                        1, std::memory_order_acq_rel);
                const std::uint32_t sweep_phase = sweep_poll % 360;
                if (sweep_phase < 120) {
                    out_x = 0.35f;
                } else if (sweep_phase >= 180 && sweep_phase < 300) {
                    out_x = -0.35f;
                }
            }
        }

        bool controller_active = false;
""",
        "long-lived computer-driven Z-trigger latch",
    )
    source = replace_required(
        source,
        """        if (controller_num != 0) {
            return false;
        }

        uint16_t out_buttons = 0;
""",
        """        if (controller_num != 0) {
            return false;
        }
        input_poll_count.fetch_add(1, std::memory_order_relaxed);

        uint16_t out_buttons = 0;
""",
        "input poll cadence counter",
    )
    source = replace_required(
        source,
        """            next_controller_check = now + std::chrono::seconds(1);
        }
    }
""",
        """            next_controller_check = now + std::chrono::seconds(1);
        }
        report_performance_telemetry();
    }
""",
        "frame cadence sampling",
    )
    source = replace_required(
        source,
        """#endif

        const float clamped_x = std::clamp(out_x, -1.0f, 1.0f);""",
        """#endif

        if (test_input_replay.has_value()
            && test_input_replay_waiting_for_trigger
            && test_input_replay_waiting_for_tunnel_progress
            && SnapPad_ConsumeTunnelHiddenPathReady()) {
            test_input_replay_waiting_for_trigger = false;
            test_input_replay_waiting_for_tunnel_progress = false;
            std::fprintf(stderr,
                \"[test-input] deterministic route started on the final Tunnel Electrode approach\\n\");
        }

        if (test_input_replay.has_value()
            && !test_input_replay_waiting_for_trigger) {
            const auto frame = test_input_replay->next();
            out_buttons = frame.buttons;
            out_x = frame.stick_x;
            out_y = frame.stick_y;
            static std::uint32_t tunnel_target_item_hold_polls = 0;
            static std::uint32_t tunnel_target_item_cooldown_polls = 0;
            static std::uint32_t tunnel_target_aim_up_polls = 0;
            static std::uint32_t tunnel_target_aim_left_polls = 0;
            static bool tunnel_target_assist_completed = false;
            if (test_input_replay_tunnel_target_assist) {
                if (tunnel_target_item_hold_polls != 0) {
                    out_buttons |= B_BUTTON;
                    out_x = 0.0f;
                    out_y = 0.0f;
                    --tunnel_target_item_hold_polls;
                } else if (tunnel_target_item_cooldown_polls != 0) {
                    out_x = 0.0f;
                    out_y = 0.0f;
                    --tunnel_target_item_cooldown_polls;
                } else if (tunnel_target_aim_up_polls != 0) {
                    out_x = 0.0f;
                    out_y = -1.0f;
                    --tunnel_target_aim_up_polls;
                    if (tunnel_target_aim_up_polls == 0) {
                        tunnel_target_aim_left_polls = 8;
                    }
                } else if (tunnel_target_aim_left_polls != 0) {
                    out_x = -1.0f;
                    out_y = 0.0f;
                    --tunnel_target_aim_left_polls;
                    if (tunnel_target_aim_left_polls == 0) {
                        tunnel_target_item_hold_polls = 2;
                        tunnel_target_item_cooldown_polls = 60;
                        tunnel_target_assist_completed = true;
                    }
                } else if (!tunnel_target_assist_completed
                    && SnapPad_IsFinalTunnelElectrodeFocused()) {
                    out_x = 0.0f;
                    out_y = -0.5f;
                    tunnel_target_aim_up_polls = 12;
                    std::fprintf(stderr,
                        \"[test-input] acquired exact hidden-path Electrode; throwing midpoint-arc pester\\n\");
                }
            }
            if (test_input_replay->consume_completed()) {
                std::fprintf(stderr, \"[test-input] deterministic route completed\\n\");
                // Return control to the live keyboard/controller after the
                // bounded route. A completed replay must not leave player one
                // permanently overridden with neutral input.
                test_input_replay.reset();
            }
        }

        const float clamped_x = std::clamp(out_x, -1.0f, 1.0f);""",
        "deterministic input replay polling",
    )
    source = replace_required(
        source,
        """        *buttons = out_buttons;
        *x = clamped_x;
        *y = clamped_y;

        // Keep input evidence compact:""",
        """        *buttons = out_buttons;
        *x = clamped_x;
        *y = clamped_y;
        SnapPad_ObserveControllerButtons(out_buttons);

        // Keep input evidence compact:""",
        "shutter edge observation",
    )
    source = replace_required(
        source,
        """int PAPERPAD_MAIN(int argc, char** argv) {
    setvbuf(stderr, nullptr, _IONBF, 0);""",
        """int PAPERPAD_MAIN(int argc, char** argv) {
    setvbuf(stderr, nullptr, _IONBF, 0);
    initialize_performance_telemetry();
    if (!initialize_test_input_replay()) {
        return EXIT_FAILURE;
    }""",
        "deterministic input replay and performance telemetry activation",
    )
    source = replace_required(
        source,
        """    if (audio_stream != nullptr) {
        SDL_FreeAudioStream(audio_stream);
        audio_stream = nullptr;
    }
    SDL_Quit();
""",
        """    if (audio_stream != nullptr) {
        SDL_FreeAudioStream(audio_stream);
        audio_stream = nullptr;
    }
    if (performance_telemetry.file != nullptr) {
        std::fclose(performance_telemetry.file);
        performance_telemetry.file = nullptr;
    }
    SDL_Quit();
""",
        "performance telemetry shutdown",
    )
    source = source.replace("[paperpad]", "[snappad]")
    source = source.replace(
        "That is a Paper Mario ROM, but not the supported US version. Please choose Pokémon Snap (USA).",
        "That is not the supported US Pokémon Snap revision. Please choose Pokémon Snap (USA).",
    )
    source = replace_required(
        source,
        "//   aspect_mode:     0 = Original (4:3), 1 = final-presentation fill/crop",
        "//   aspect_mode:     0 = Original (4:3), 1 = final-presentation fill/crop,\n"
        "//                    2 = RT64 expanded projection (experimental)",
        "experimental widescreen setting contract",
    )
    source = replace_required(
        source,
        "    config.ar_option = aspect_mode == 1\n"
        "        ? ultramodern::renderer::AspectRatio::Expand\n"
        "        : ultramodern::renderer::AspectRatio::Original;",
        "    config.ar_option = aspect_mode == 1\n"
        "        ? ultramodern::renderer::AspectRatio::Expand\n"
        "        : (aspect_mode == 2\n"
        "            ? ultramodern::renderer::AspectRatio::Manual\n"
        "            : ultramodern::renderer::AspectRatio::Original);",
        "experimental widescreen runtime signal",
    )
    source = source.replace("PAPERPAD_MAIN", "SNAPPAD_MAIN")
    return source


def main() -> None:
    revision = subprocess.run(
        ["git", "-C", str(ROOT / "ref/paperpad"), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != LOCKED_COMMIT:
        fail(f"PaperPad revision mismatch: {revision}")
    if not REFERENCE.is_file() or not ACTUAL.is_file():
        fail("runner reference or SnapPad derivation is missing")
    expected = render_expected(REFERENCE.read_text(encoding="utf-8"))
    actual = ACTUAL.read_text(encoding="utf-8")
    if actual != expected:
        fail("SnapPad runner drifted from the audited PaperPad derivation")
    print("PaperPad runner derivation passed: reusable plumbing is exact and game-specific removals are audited.")


if __name__ == "__main__":
    main()
