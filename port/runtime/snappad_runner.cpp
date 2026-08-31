// SnapPad native runner.
//
// Derived from the pinned PaperPad runner, with Paper Mario-specific scene
// tracing, frame hooks, accessory policy, game identity, and texture hooks
// removed. Renderer policy is supplied by SnapPad separately and must be
// validated against Pokemon Snap before gameplay acceptance.
//
// Adapted from Paper Mario ReCut's main.cpp (MIT) cross-platform core:
// N64Recomp game entry, SDL window/input/audio, RT64 rendering via
// snappad_rt64_context. The Windows launcher UI, texture-replacement tooling,
// and built-in texture pack are intentionally not ported; the Apple shell
// (UIKit) drives the same entry points on iOS.

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#define SDL_MAIN_HANDLED
#include "SDL.h"
#include "SDL_syswm.h"

#include "librecomp/game.hpp"
#include "librecomp/overlays.hpp"
#include "librecomp/rsp.hpp"
#include "recomp.h"
#include "snappad_rt64_context.h"
#include "game_registration.h"
#include "n64_input_policy.h"
#include "register_overlays.h"
#include "snappad_game_hooks.h"
#include "snappad_game_metadata.h"
#include "ultramodern/ultra64.h"
#include "ultramodern/ultramodern.hpp"

#include "snappad_input.h"
#include "controller_slots.h"
#include "test_input_replay.h"

#if defined(__APPLE__) && TARGET_OS_IPHONE
extern "C" void snappad_touch_snapshot(uint16_t* buttons, float* x, float* y);
extern "C" void snappad_touch_attach(void* ui_window);
extern "C" void snappad_fix_metal_layer_scale(void* ui_window, void* metal_layer);
#endif
#include "snappad_paths.h"

extern "C" void recomp_entrypoint(uint8_t* rdram, recomp_context* ctx);
extern "C" recomp_func_t* get_function(int32_t addr);
extern RspUcodeFunc aspMain;

namespace {

    const auto play_session_started_at = std::chrono::steady_clock::now();

    uint64_t play_session_ms() {
        return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - play_session_started_at).count());
    }

    constexpr uint16_t A_BUTTON = 0x8000;
    constexpr uint16_t B_BUTTON = 0x4000;
    constexpr uint16_t Z_BUTTON = 0x2000;
    constexpr uint16_t START_BUTTON = 0x1000;
    constexpr uint16_t U_JPAD = 0x0800;
    constexpr uint16_t D_JPAD = 0x0400;
    constexpr uint16_t L_JPAD = 0x0200;
    constexpr uint16_t R_JPAD = 0x0100;
    constexpr uint16_t L_TRIG = 0x0020;
    constexpr uint16_t R_TRIG = 0x0010;
    constexpr uint16_t U_CBUTTONS = 0x0008;
    constexpr uint16_t D_CBUTTONS = 0x0004;
    constexpr uint16_t L_CBUTTONS = 0x0002;
    constexpr uint16_t R_CBUTTONS = 0x0001;

    SDL_Window* window = nullptr;
#if defined(__APPLE__) && TARGET_OS_IPHONE
    // iOS: native handles retained for periodic window/layer diagnostics.
    void* ios_ui_window = nullptr;
    void* ios_metal_layer = nullptr;
#endif
    SDL_AudioDeviceID audio_device = 0;
    SDL_AudioStream* audio_stream = nullptr;
    std::atomic<bool> app_backgrounded{false};
    uint32_t sample_rate = 48000;
    uint32_t output_sample_rate = 48000;
    constexpr uint32_t input_channels = 2;
    constexpr uint32_t output_channels = 2;
    constexpr uint32_t bytes_per_input_frame = input_channels * sizeof(float);

    struct AudioTelemetry {
        std::chrono::steady_clock::time_point next_report{};
        uint64_t callbacks = 0;
        uint64_t max_callback_gap_us = 0;
        uint64_t input_frames = 0;
        uint64_t output_frames = 0;
        uint64_t min_prequeue_us = UINT64_MAX;
        uint64_t zero_prequeue_callbacks = 0;
        uint64_t under_5ms_prequeue_callbacks = 0;
        uint64_t peak_queue_us = 0;
        uint64_t over_100ms_callbacks = 0;
        uint32_t peak_input = 0;
        uint64_t boundary_delta_sum_ppm = 0;
        uint64_t boundary_count = 0;
        uint32_t peak_boundary_delta_ppm = 0;
        uint32_t peak_within_delta_ppm = 0;
        uint64_t conversion_errors = 0;
        uint64_t queue_errors = 0;
    } audio_telemetry;
    std::chrono::steady_clock::time_point previous_audio_callback{};
    std::array<float, output_channels> previous_output_frame{};
    bool has_previous_output_frame = false;

    bool audio_telemetry_enabled() {
        static const bool enabled = []() {
            const char* audio_trace = std::getenv("SNAPPAD_AUDIO_TRACE");
            return audio_trace != nullptr && audio_trace[0] != '\0'
                && std::strcmp(audio_trace, "0") != 0;
        }();
        return enabled;
    }

    void report_audio_telemetry(uint64_t current_queue_us) {
        const auto now = std::chrono::steady_clock::now();
        if (audio_telemetry.next_report.time_since_epoch().count() == 0) {
            audio_telemetry.next_report = now + std::chrono::seconds(2);
            return;
        }
        if (now < audio_telemetry.next_report) return;

        std::fprintf(stderr,
            "[audio t=%.3fs] input_hz=%u output_hz=%u callbacks=%llu max_gap_us=%llu input_frames=%llu "
            "output_frames=%llu prequeue_min_us=%llu prequeue_zero=%llu prequeue_under_5ms=%llu "
            "queue_us=%llu peak_queue_us=%llu over_100ms=%llu "
            "peak_input=%u boundary_avg_ppm=%llu boundary_peak_ppm=%u "
            "within_peak_ppm=%u conversion_errors=%llu queue_errors=%llu\n",
            play_session_ms() / 1000.0,
            sample_rate,
            output_sample_rate,
            static_cast<unsigned long long>(audio_telemetry.callbacks),
            static_cast<unsigned long long>(audio_telemetry.max_callback_gap_us),
            static_cast<unsigned long long>(audio_telemetry.input_frames),
            static_cast<unsigned long long>(audio_telemetry.output_frames),
            static_cast<unsigned long long>(audio_telemetry.min_prequeue_us == UINT64_MAX
                ? 0 : audio_telemetry.min_prequeue_us),
            static_cast<unsigned long long>(audio_telemetry.zero_prequeue_callbacks),
            static_cast<unsigned long long>(audio_telemetry.under_5ms_prequeue_callbacks),
            static_cast<unsigned long long>(current_queue_us),
            static_cast<unsigned long long>(audio_telemetry.peak_queue_us),
            static_cast<unsigned long long>(audio_telemetry.over_100ms_callbacks),
            audio_telemetry.peak_input,
            static_cast<unsigned long long>(audio_telemetry.boundary_count == 0
                ? 0
                : audio_telemetry.boundary_delta_sum_ppm / audio_telemetry.boundary_count),
            audio_telemetry.peak_boundary_delta_ppm,
            audio_telemetry.peak_within_delta_ppm,
            static_cast<unsigned long long>(audio_telemetry.conversion_errors),
            static_cast<unsigned long long>(audio_telemetry.queue_errors));

        audio_telemetry = {};
        audio_telemetry.next_report = now + std::chrono::seconds(2);
    }

    // Touch overlay state written by the Apple shell.
    std::atomic<uint16_t> touch_buttons{0};
    std::atomic<float> touch_stick_x{0.0f};
    std::atomic<float> touch_stick_y{0.0f};
    std::atomic<float> audio_volume{1.0f};
    std::atomic<bool> graphics_settings_applied{false};
    std::atomic<uint32_t> test_z_hold_polls{0};
    std::atomic<bool> test_auto_shutter_armed{false};
    std::atomic<uint32_t> test_auto_shutter_sweep_polls{0};
    std::atomic<uint64_t> input_poll_count{0};
    std::optional<snappad::testing::TestInputReplay> test_input_replay;
    bool test_input_replay_waiting_for_trigger = false;
    bool test_input_replay_waiting_for_tunnel_progress = false;
    bool test_input_replay_tunnel_target_assist = false;
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
        const char* path = std::getenv("SNAPPAD_PERF_TRACE_PATH");
        if (path == nullptr || path[0] == '\0') return;

        performance_telemetry.file = std::fopen(path, "w");
        if (performance_telemetry.file == nullptr) {
            std::fprintf(stderr,
                "[perf] could not open trace path: %s\n", path);
            return;
        }
        std::fprintf(performance_telemetry.file,
            "session_ms,interval_ms,input_polls,input_hz,screen_updates,screen_hz,"
            "presented_frames,presented_hz,present_intervals,mean_present_interval_ms,"
            "max_present_interval_ms,present_intervals_over_50_ms,"
            "present_intervals_over_100_ms,display_hz,focused,minimized\n");
        std::fflush(performance_telemetry.file);
        std::fprintf(stderr, "[perf] tracing frame cadence to %s\n", path);
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
            "%llu,%llu,%llu,%.3f,%llu,%.3f,%llu,%.3f,"
            "%llu,%.3f,%.3f,%llu,%llu,%u,%d,%d\n",
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

    bool install_test_input_replay(
        const std::string& specification, bool waiting_for_trigger,
        const char* source) {
        std::string error;
        auto replay = snappad::testing::TestInputReplay::parse(specification, error);
        if (!replay.has_value()) {
            std::fprintf(stderr,
                "[test-input] invalid deterministic route from %s: %s\n",
                source, error.c_str());
            return false;
        }

        test_input_replay_waiting_for_trigger = waiting_for_trigger;
        std::fprintf(stderr,
            "[test-input] armed deterministic route from %s: steps=%zu polls=%llu trigger=%s\n",
            source,
            replay->step_count(),
            static_cast<unsigned long long>(replay->total_polls()),
            test_input_replay_waiting_for_tunnel_progress
                ? "tunnel-electrode-approach-window"
                : (test_input_replay_waiting_for_trigger ? "F7" : "immediate"));
        test_input_replay = std::move(*replay);
        return true;
    }

    bool install_test_input_replay_file(bool waiting_for_trigger) {
        std::ifstream input(test_input_replay_file_path, std::ios::binary);
        if (!input) {
            std::fprintf(stderr,
                "[test-input] could not open deterministic route file: %s\n",
                test_input_replay_file_path.c_str());
            return false;
        }
        const std::string specification{
            std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
        return install_test_input_replay(
            specification, waiting_for_trigger, test_input_replay_file_path.c_str());
    }

    bool initialize_test_input_replay() {
        const char* route_file = std::getenv("SNAPPAD_TEST_INPUT_ROUTE_FILE");
        if (route_file != nullptr && route_file[0] != '\0') {
            test_input_replay_file_path = route_file;
        }

        const char* specification = std::getenv("SNAPPAD_TEST_INPUT_ROUTE");
        if (test_input_replay_file_path.empty()
            && (specification == nullptr || specification[0] == '\0')) {
            return true;
        }

        const char* armed = std::getenv("SNAPPAD_TEST_INPUT_ROUTE_ARMED");
        const bool f7_trigger =
            armed != nullptr && armed[0] == '1' && armed[1] == '\0';
        const char* tunnel_progress =
            std::getenv("SNAPPAD_TEST_INPUT_ROUTE_TUNNEL_PROGRESS");
        test_input_replay_waiting_for_tunnel_progress =
            tunnel_progress != nullptr
            && tunnel_progress[0] == '1'
            && tunnel_progress[1] == '\0';
        test_input_replay_tunnel_target_assist =
            test_input_replay_waiting_for_tunnel_progress;
        const bool waiting_for_trigger =
            f7_trigger || test_input_replay_waiting_for_tunnel_progress;
        if (!test_input_replay_file_path.empty()) {
            return install_test_input_replay_file(waiting_for_trigger);
        }
        return install_test_input_replay(
            specification, waiting_for_trigger, "SNAPPAD_TEST_INPUT_ROUTE");
    }

    enum class InputAction : int {
        N64A,
        N64B,
        Start,
        Z,
        L,
        R,
        CUp,
        CDown,
        CLeft,
        CRight,
        DPadUp,
        DPadDown,
        DPadLeft,
        DPadRight,
        StickUp,
        StickDown,
        StickLeft,
        StickRight,
        Count
    };

    constexpr int input_action_count = static_cast<int>(InputAction::Count);

    struct InputActionDescriptor {
        InputAction action;
        const char* label;
        uint16_t button;
        int axis_x;
        int axis_y;
    };

    constexpr std::array<InputActionDescriptor, input_action_count> input_actions{ {
        { InputAction::N64A, "A Button", A_BUTTON, 0, 0 },
        { InputAction::N64B, "B Button", B_BUTTON, 0, 0 },
        { InputAction::Start, "Start", START_BUTTON, 0, 0 },
        { InputAction::Z, "Z Trigger", Z_BUTTON, 0, 0 },
        { InputAction::L, "L Trigger", L_TRIG, 0, 0 },
        { InputAction::R, "R Trigger", R_TRIG, 0, 0 },
        { InputAction::CUp, "C Up", U_CBUTTONS, 0, 0 },
        { InputAction::CDown, "C Down", D_CBUTTONS, 0, 0 },
        { InputAction::CLeft, "C Left", L_CBUTTONS, 0, 0 },
        { InputAction::CRight, "C Right", R_CBUTTONS, 0, 0 },
        { InputAction::DPadUp, "D-Pad Up", U_JPAD, 0, 0 },
        { InputAction::DPadDown, "D-Pad Down", D_JPAD, 0, 0 },
        { InputAction::DPadLeft, "D-Pad Left", L_JPAD, 0, 0 },
        { InputAction::DPadRight, "D-Pad Right", R_JPAD, 0, 0 },
        { InputAction::StickUp, "Stick Up", 0, 0, 1 },
        { InputAction::StickDown, "Stick Down", 0, 0, -1 },
        { InputAction::StickLeft, "Stick Left", 0, -1, 0 },
        { InputAction::StickRight, "Stick Right", 0, 1, 0 }
    } };

    enum class GamepadBindingKind {
        Button,
        AxisPositive,
        AxisNegative
    };

    struct GamepadBinding {
        GamepadBindingKind kind = GamepadBindingKind::Button;
        int code = SDL_CONTROLLER_BUTTON_INVALID;
    };

    struct AppInputSettings {
        int preferred_controller_index = 0;
        std::array<SDL_Scancode, input_action_count> keyboard_bindings{};
        std::array<GamepadBinding, input_action_count> gamepad_bindings{};
    };

    AppInputSettings make_default_input_settings() {
        AppInputSettings settings{};
        settings.keyboard_bindings = {
            SDL_SCANCODE_Z,
            SDL_SCANCODE_X,
            SDL_SCANCODE_RETURN,
            SDL_SCANCODE_LSHIFT,
            SDL_SCANCODE_Q,
            SDL_SCANCODE_E,
            SDL_SCANCODE_I,
            SDL_SCANCODE_K,
            SDL_SCANCODE_J,
            SDL_SCANCODE_L,
            SDL_SCANCODE_W,
            SDL_SCANCODE_S,
            SDL_SCANCODE_A,
            SDL_SCANCODE_D,
            SDL_SCANCODE_UP,
            SDL_SCANCODE_DOWN,
            SDL_SCANCODE_LEFT,
            SDL_SCANCODE_RIGHT
        };
        settings.gamepad_bindings = {
            GamepadBinding{ GamepadBindingKind::Button, SDL_CONTROLLER_BUTTON_A },
            GamepadBinding{ GamepadBindingKind::Button, SDL_CONTROLLER_BUTTON_X },
            GamepadBinding{ GamepadBindingKind::Button, SDL_CONTROLLER_BUTTON_START },
            GamepadBinding{ GamepadBindingKind::AxisPositive, SDL_CONTROLLER_AXIS_TRIGGERLEFT },
            GamepadBinding{ GamepadBindingKind::Button, SDL_CONTROLLER_BUTTON_LEFTSHOULDER },
            GamepadBinding{ GamepadBindingKind::Button, SDL_CONTROLLER_BUTTON_RIGHTSHOULDER },
            GamepadBinding{ GamepadBindingKind::AxisNegative, SDL_CONTROLLER_AXIS_RIGHTY },
            GamepadBinding{ GamepadBindingKind::AxisPositive, SDL_CONTROLLER_AXIS_RIGHTY },
            GamepadBinding{ GamepadBindingKind::AxisNegative, SDL_CONTROLLER_AXIS_RIGHTX },
            GamepadBinding{ GamepadBindingKind::AxisPositive, SDL_CONTROLLER_AXIS_RIGHTX },
            GamepadBinding{ GamepadBindingKind::Button, SDL_CONTROLLER_BUTTON_DPAD_UP },
            GamepadBinding{ GamepadBindingKind::Button, SDL_CONTROLLER_BUTTON_DPAD_DOWN },
            GamepadBinding{ GamepadBindingKind::Button, SDL_CONTROLLER_BUTTON_DPAD_LEFT },
            GamepadBinding{ GamepadBindingKind::Button, SDL_CONTROLLER_BUTTON_DPAD_RIGHT },
            GamepadBinding{ GamepadBindingKind::AxisNegative, SDL_CONTROLLER_AXIS_LEFTY },
            GamepadBinding{ GamepadBindingKind::AxisPositive, SDL_CONTROLLER_AXIS_LEFTY },
            GamepadBinding{ GamepadBindingKind::AxisNegative, SDL_CONTROLLER_AXIS_LEFTX },
            GamepadBinding{ GamepadBindingKind::AxisPositive, SDL_CONTROLLER_AXIS_LEFTX }
        };
        return settings;
    }

    std::mutex settings_mutex;
    AppInputSettings input_settings = make_default_input_settings();
    // Preserve very short key taps until the next emulated input poll. SDL's
    // event pump and the game-input callback run on different host threads;
    // polling SDL_GetKeyboardState alone can miss a keydown+keyup pair that
    // occurs between two game frames.
    std::array<std::atomic<uint8_t>, input_action_count> keyboard_tap_latches{};
    class SDLControllerBackend final : public snappad::input::ControllerBackend {
    public:
        void set_preferred_device_index(int device_index) {
            preferred_device_index_ = device_index;
        }

        std::vector<snappad::input::EnumeratedController> enumerate() override {
            std::vector<snappad::input::EnumeratedController> result;
            const int count = SDL_NumJoysticks();
            result.reserve(static_cast<std::size_t>(std::max(count, 0)));
            for (int device_index = 0; device_index < count; ++device_index) {
                if (!SDL_IsGameController(device_index)) {
                    continue;
                }
                const SDL_JoystickID instance_id = SDL_JoystickGetDeviceInstanceID(device_index);
                if (instance_id >= 0) {
                    result.push_back({device_index, instance_id});
                }
            }
            std::stable_sort(result.begin(), result.end(), [this](const auto& left, const auto& right) {
                return left.device_index == preferred_device_index_
                    && right.device_index != preferred_device_index_;
            });
            return result;
        }

        snappad::input::ControllerHandle open(int device_index) override {
            return SDL_GameControllerOpen(device_index);
        }

        void close(snappad::input::ControllerHandle handle) override {
            SDL_GameControllerClose(static_cast<SDL_GameController*>(handle));
        }

        bool connected(snappad::input::ControllerHandle handle) const override {
            return SDL_GameControllerGetAttached(static_cast<SDL_GameController*>(handle)) == SDL_TRUE;
        }

        snappad::input::ControllerInstanceId instance_id(
            snappad::input::ControllerHandle handle) const override {
            SDL_Joystick* joystick = SDL_GameControllerGetJoystick(
                static_cast<SDL_GameController*>(handle));
            return joystick == nullptr ? -1 : SDL_JoystickInstanceID(joystick);
        }

    private:
        int preferred_device_index_ = 0;
    };

    std::mutex controller_mutex;
    SDLControllerBackend controller_backend;
    snappad::input::ControllerSlots controller_slots;
#if defined(__APPLE__) && TARGET_OS_IPHONE
    std::optional<bool> reported_physical_controller_state;
#endif

    std::filesystem::path app_base_path() {
        return std::filesystem::current_path();
    }

    std::filesystem::path app_config_path() {
#if defined(__APPLE__)
        // macOS/iOS: user data belongs in the Application Support directory.
        const char* support_dir = snappad_apple_application_support_dir();
        std::filesystem::path base = std::filesystem::path(support_dir ? support_dir : "user");
        free(const_cast<char*>(support_dir));
        std::filesystem::create_directories(base);
        return base;
#else
        std::filesystem::path base = app_base_path() / "user";
        std::filesystem::create_directories(base);
        return base;
#endif
    }

    void show_message(const char* msg) {
        std::fprintf(stderr, "%s\n", msg);
        SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "SnapPad", msg, window);
    }

    void report_controller_changes(
        const char* reason,
        const std::vector<snappad::input::ControllerSlotChange>& changes) {
        for (const auto& change : changes) {
            const int player = change.player_slot + 1;
            switch (change.kind) {
                case snappad::input::ControllerSlotChangeKind::Assigned: {
                    const auto handle = controller_slots.player_handle(change.player_slot);
                    const char* name = handle == nullptr
                        ? "unknown"
                        : SDL_GameControllerName(static_cast<SDL_GameController*>(handle));
                    std::fprintf(stderr,
                        "[input t=%.3fs] controller assigned: reason=%s instance_id=%d player=%d "
                        "device_index=%d name=%s\n",
                        play_session_ms() / 1000.0,
                        reason,
                        change.instance_id,
                        player,
                        change.device_index,
                        name ?: "unknown");
                    break;
                }
                case snappad::input::ControllerSlotChangeKind::Released:
                    std::fprintf(stderr,
                        "[input t=%.3fs] controller released: reason=%s instance_id=%d player=%d\n",
                        play_session_ms() / 1000.0,
                        reason,
                        change.instance_id,
                        player);
                    break;
                case snappad::input::ControllerSlotChangeKind::OpenFailed:
                    std::fprintf(stderr,
                        "[input t=%.3fs] controller open failed: reason=%s instance_id=%d player=%d "
                        "device_index=%d error=%s\n",
                        play_session_ms() / 1000.0,
                        reason,
                        change.instance_id,
                        player,
                        change.device_index,
                        SDL_GetError());
                    break;
            }
        }
    }

    void reconcile_controllers(const char* reason) {
        int preferred_controller_index = 0;
        {
            std::lock_guard<std::mutex> lock(settings_mutex);
            preferred_controller_index = input_settings.preferred_controller_index;
        }
        std::size_t connected_count = 0;
        {
            std::lock_guard<std::mutex> lock(controller_mutex);
            controller_backend.set_preferred_device_index(preferred_controller_index);
            const auto changes = controller_slots.reconcile(controller_backend);
            report_controller_changes(reason, changes);
            connected_count = controller_slots.connected_count();
        }
#if defined(__APPLE__) && TARGET_OS_IPHONE
        const bool physically_connected = connected_count != 0;
        if (!reported_physical_controller_state.has_value()
            || *reported_physical_controller_state != physically_connected) {
            reported_physical_controller_state = physically_connected;
            SnapPad_SetPhysicalControllerConnected(physically_connected);
        }
#endif
    }

    ultramodern::gfx_callbacks_t::gfx_data_t create_gfx() {
        SDL_SetHint(SDL_HINT_GAMECONTROLLER_USE_BUTTON_LABELS, "0");
#if defined(__APPLE__) && TARGET_OS_IPHONE
        // SnapPad is an interactive game, not a background-audio player.
        // Ambient makes iOS silence/deactivate the session when the app loses
        // the foreground instead of SDL's default Playback category keeping
        // the process and audio callbacks alive behind the Home screen.
        SDL_SetHint(SDL_HINT_AUDIO_CATEGORY, "ambient");
#endif

        if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMECONTROLLER | SDL_INIT_AUDIO) != 0) {
            show_message(SDL_GetError());
            std::exit(EXIT_FAILURE);
        }

        reconcile_controllers("startup");
        return nullptr;
    }

    ultramodern::renderer::WindowHandle create_window(ultramodern::gfx_callbacks_t::gfx_data_t) {
        uint32_t flags = SDL_WINDOW_RESIZABLE;
#if defined(__APPLE__)
        flags |= SDL_WINDOW_METAL;
#if TARGET_OS_IPHONE
        // iOS owns a full-screen UIWindow. Mark its SDL view borderless so the
        // SDL view controller hides the status bar and gives RT64 the complete
        // drawable before fitting Original (4:3) or Expand.
        flags |= SDL_WINDOW_BORDERLESS;
#endif
#endif

        window = SDL_CreateWindow("SnapPad", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, 960, 720, flags);
        if (window == nullptr) {
            show_message(SDL_GetError());
            std::exit(EXIT_FAILURE);
        }
        SDL_ShowWindow(window);

        SDL_SysWMinfo wm_info;
        SDL_VERSION(&wm_info.version);
        SDL_GetWindowWMInfo(window, &wm_info);

#if defined(_WIN32)
        return ultramodern::renderer::WindowHandle{ wm_info.info.win.window, GetCurrentThreadId() };
#elif defined(__linux__) || defined(__ANDROID__)
        return window;
#elif defined(__APPLE__)
#if TARGET_OS_IPHONE
        // iOS: SDL owns the UIWindow; RT64's CocoaWindow maps it.
        std::fprintf(stderr, "[snappad] window created: ui_window=%p\n",
            wm_info.info.uikit.window);
        void* ios_layer = SDL_Metal_GetLayer(SDL_Metal_CreateView(window));
        ios_ui_window = wm_info.info.uikit.window;
        ios_metal_layer = ios_layer;
        snappad_fix_metal_layer_scale(wm_info.info.uikit.window, ios_layer);
        snappad_touch_attach(wm_info.info.uikit.window);
        snappad_log_window_diagnostics(wm_info.info.uikit.window, ios_layer);
        // Repeated UIKit/CAMetal state probes can synchronize with the UI and
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
        }
        return ultramodern::renderer::WindowHandle{ wm_info.info.uikit.window, ios_layer };
#else
        SDL_MetalView view = SDL_Metal_CreateView(window);
        std::fprintf(stderr, "[snappad] window created: ns_window=%p layer=%p\n",
            wm_info.info.cocoa.window, SDL_Metal_GetLayer(view));
        return ultramodern::renderer::WindowHandle{ wm_info.info.cocoa.window, SDL_Metal_GetLayer(view) };
#endif
#else
        return window;
#endif
    }

    void update_gfx(void*) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) {
                std::fprintf(stderr, "[snappad] SDL_QUIT received\n");
                ultramodern::quit();
            }
            else if (event.type == SDL_CONTROLLERDEVICEADDED) {
                const SDL_JoystickID instance_id =
                    SDL_JoystickGetDeviceInstanceID(event.cdevice.which);
                std::fprintf(stderr,
                    "[input t=%.3fs] controller added event: device_index=%d instance_id=%d\n",
                    play_session_ms() / 1000.0,
                    event.cdevice.which,
                    instance_id);
                reconcile_controllers("device-added");
            }
            else if (event.type == SDL_CONTROLLERDEVICEREMOVED) {
                std::fprintf(stderr,
                    "[input t=%.3fs] controller removed event: instance_id=%d\n",
                    play_session_ms() / 1000.0,
                    event.cdevice.which);
                {
                    std::lock_guard<std::mutex> lock(controller_mutex);
                    const auto changes = controller_slots.release_instance(
                        controller_backend, event.cdevice.which);
                    report_controller_changes("device-removed", changes);
                }
                reconcile_controllers("device-removed");
            }
            else if (event.type == SDL_CONTROLLERDEVICEREMAPPED) {
                std::fprintf(stderr,
                    "[input t=%.3fs] controller remapped event: instance_id=%d\n",
                    play_session_ms() / 1000.0,
                    event.cdevice.which);
                reconcile_controllers("device-remapped");
            }
            else if (event.type == SDL_APP_WILLENTERBACKGROUND
                || event.type == SDL_APP_DIDENTERBACKGROUND) {
                if (!app_backgrounded.exchange(true, std::memory_order_acq_rel)) {
                    if (audio_device != 0) {
                        SDL_PauseAudioDevice(audio_device, 1);
                        SDL_ClearQueuedAudio(audio_device);
                    }
                    std::fprintf(stderr,
                        "[lifecycle t=%.3fs] background: audio paused and queue cleared\n",
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
                    "[lifecycle t=%.3fs] foreground: audio resumed, controllers reconciling (was_backgrounded=%d)\n",
                    play_session_ms() / 1000.0,
                    was_backgrounded ? 1 : 0);
                reconcile_controllers("foreground-resume");
            }
            else if (event.type == SDL_KEYDOWN && event.key.repeat == 0) {
                std::lock_guard<std::mutex> lock(settings_mutex);
                for (int i = 0; i < input_action_count; i++) {
                    if (input_settings.keyboard_bindings[i] == event.key.keysym.scancode) {
                        // A few runtime polls can occur inside one rendered
                        // frame. Retain the tap across four polls so the game
                        // sees it in its pressed-button edge calculation.
                        auto& latch = keyboard_tap_latches[i];
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
                const char* test_z_hold = std::getenv("SNAPPAD_TEST_Z_HOLD_POLLS");
                if (test_z_hold != nullptr
                    && event.key.keysym.scancode == SDL_SCANCODE_F6) {
                    char* end = nullptr;
                    const long requested = std::strtol(test_z_hold, &end, 10);
                    if (end != test_z_hold && *end == '\0'
                        && requested >= 4 && requested <= 1'000'000) {
                        test_z_hold_polls.store(
                            static_cast<uint32_t>(requested), std::memory_order_release);
                        std::fprintf(stderr,
                            "[test-input] latched Z trigger for %ld polls\n", requested);
                    }
                }
                else if (event.key.keysym.scancode == SDL_SCANCODE_F8) {
                    test_z_hold_polls.store(0, std::memory_order_release);
                    test_auto_shutter_armed.store(false, std::memory_order_release);
                    test_auto_shutter_sweep_polls.store(0, std::memory_order_release);
                    std::fprintf(stderr,
                        "[test-input] released latched Z trigger and disarmed auto-shutter\n");
                }
                const char* test_auto_shutter = std::getenv("SNAPPAD_TEST_AUTO_SHUTTER");
                if (test_auto_shutter != nullptr
                    && *test_auto_shutter != '\0'
                    && std::strcmp(test_auto_shutter, "0") != 0
                    && event.key.keysym.scancode == SDL_SCANCODE_F9) {
                    test_auto_shutter_sweep_polls.store(0, std::memory_order_release);
                    test_auto_shutter_armed.store(true, std::memory_order_release);
                    std::fprintf(stderr,
                        "[test-input] armed auto-shutter\n");
                }
                if (event.key.keysym.scancode == SDL_SCANCODE_F7) {
                    if (!test_input_replay_file_path.empty()) {
                        if (install_test_input_replay_file(false)) {
                            std::fprintf(stderr,
                                "[test-input] deterministic route reloaded and started by F7\n");
                        }
                    }
                    else if (test_input_replay.has_value()
                        && test_input_replay_waiting_for_trigger) {
                        test_input_replay_waiting_for_trigger = false;
                        std::fprintf(stderr,
                            "[test-input] deterministic route started by F7\n");
                    }
                }
            }
        }

        static auto next_controller_check = std::chrono::steady_clock::now();
        const auto now = std::chrono::steady_clock::now();
        if (now >= next_controller_check) {
            reconcile_controllers("active-check");
            next_controller_check = now + std::chrono::seconds(1);
        }
        report_performance_telemetry();
    }

    void update_audio_stream() {
        if (audio_stream != nullptr) {
            SDL_FreeAudioStream(audio_stream);
            audio_stream = nullptr;
        }

        audio_stream = SDL_NewAudioStream(
            AUDIO_F32,
            input_channels,
            static_cast<int>(sample_rate),
            AUDIO_F32,
            static_cast<Uint8>(output_channels),
            static_cast<int>(output_sample_rate));
        if (audio_stream == nullptr) {
            std::fprintf(stderr, "Error creating SDL audio stream: %s\n", SDL_GetError());
            std::exit(EXIT_FAILURE);
        }
    }

    void reset_audio(uint32_t output_freq) {
        if (audio_device != 0) {
            SDL_CloseAudioDevice(audio_device);
            audio_device = 0;
        }

        SDL_AudioSpec desired{};
        desired.freq = static_cast<int>(output_freq);
        desired.format = AUDIO_F32;
        desired.channels = static_cast<Uint8>(output_channels);
        desired.samples = 256;
        desired.callback = nullptr;

        audio_device = SDL_OpenAudioDevice(nullptr, 0, &desired, nullptr, 0);
        if (audio_device == 0) {
            std::fprintf(stderr, "SDL error opening audio device: %s\n", SDL_GetError());
            std::exit(EXIT_FAILURE);
        }

        SDL_PauseAudioDevice(
            audio_device,
            app_backgrounded.load(std::memory_order_acquire) ? 1 : 0);
        output_sample_rate = output_freq;
        update_audio_stream();
    }

    void set_frequency(uint32_t freq) {
        sample_rate = freq == 0 ? 48000 : freq;

        if (audio_device == 0) {
            reset_audio(48000);
            return;
        }

        update_audio_stream();
    }

    void queue_samples(int16_t* audio_data, size_t sample_count) {
        if (audio_device == 0 || sample_count == 0
            || app_backgrounded.load(std::memory_order_acquire)) {
            return;
        }

        static std::vector<float> source_buffer;
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

        source_buffer.resize(sample_count);

        const float output_gain = 0.5f / 32768.0f;
        for (size_t i = 0; i + 1 < sample_count; i += input_channels) {
            if (collect_audio_telemetry) {
                audio_telemetry.peak_input = std::max(
                    audio_telemetry.peak_input,
                    static_cast<uint32_t>(std::max(
                        std::abs(static_cast<int32_t>(audio_data[i + 0])),
                        std::abs(static_cast<int32_t>(audio_data[i + 1])))));
            }
            source_buffer[i + 0] = audio_data[i + 1] * output_gain;
            source_buffer[i + 1] = audio_data[i + 0] * output_gain;
        }

        if (SDL_AudioStreamPut(
                audio_stream,
                source_buffer.data(),
                static_cast<int>(sample_count * sizeof(float))) < 0) {
            if (collect_audio_telemetry) audio_telemetry.conversion_errors++;
            std::fprintf(stderr, "Error feeding SDL audio stream: %s\n", SDL_GetError());
            return;
        }

        constexpr uint32_t bytes_per_output_frame = input_channels * sizeof(float);
        uint64_t queued_input_us =
            uint64_t(SDL_GetQueuedAudioSize(audio_device)) /
            bytes_per_output_frame * 1000000 / output_sample_rate;

        int available_bytes = SDL_AudioStreamAvailable(audio_stream);
        if (available_bytes < 0) {
            if (collect_audio_telemetry) audio_telemetry.conversion_errors++;
            std::fprintf(stderr, "Error reading SDL audio stream availability: %s\n", SDL_GetError());
            return;
        }
        available_bytes -= available_bytes % static_cast<int>(output_channels * sizeof(float));
        converted_buffer.resize(static_cast<size_t>(available_bytes) / sizeof(float));
        int converted_bytes = 0;
        if (available_bytes != 0) {
            converted_bytes = SDL_AudioStreamGet(
                audio_stream, converted_buffer.data(), available_bytes);
            if (converted_bytes < 0) {
                if (collect_audio_telemetry) audio_telemetry.conversion_errors++;
                std::fprintf(stderr, "Error draining SDL audio stream: %s\n", SDL_GetError());
                return;
            }
        }
        uint32_t queue_bytes = static_cast<uint32_t>(converted_bytes);
        float* samples_to_queue = converted_buffer.data();

        // Let N64ModernRuntime's get_frames_remaining feedback regulate
        // production. Never shorten already-rendered PCM to catch up: that
        // creates discontinuities and pitch/time jumps.
        if (collect_audio_telemetry) {
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

        if (queue_bytes != 0) {
            const uint32_t output_frame_count =
                queue_bytes / (output_channels * sizeof(float));
            if (collect_audio_telemetry && output_frame_count != 0) {
                if (has_previous_output_frame) {
                    const float left_delta = std::abs(samples_to_queue[0] - previous_output_frame[0]);
                    const float right_delta = std::abs(samples_to_queue[1] - previous_output_frame[1]);
                    const uint32_t delta_ppm = static_cast<uint32_t>(
                        std::lround(std::max(left_delta, right_delta) * 1000000.0f));
                    audio_telemetry.boundary_delta_sum_ppm += delta_ppm;
                    audio_telemetry.boundary_count++;
                    audio_telemetry.peak_boundary_delta_ppm = std::max(
                        audio_telemetry.peak_boundary_delta_ppm, delta_ppm);
                }
                for (uint32_t frame = 1; frame < output_frame_count; ++frame) {
                    const size_t current = frame * output_channels;
                    const size_t previous = current - output_channels;
                    const float left_delta = std::abs(
                        samples_to_queue[current + 0] - samples_to_queue[previous + 0]);
                    const float right_delta = std::abs(
                        samples_to_queue[current + 1] - samples_to_queue[previous + 1]);
                    const uint32_t delta_ppm = static_cast<uint32_t>(
                        std::lround(std::max(left_delta, right_delta) * 1000000.0f));
                    audio_telemetry.peak_within_delta_ppm = std::max(
                        audio_telemetry.peak_within_delta_ppm, delta_ppm);
                }
                const size_t last = (output_frame_count - 1) * output_channels;
                previous_output_frame[0] = samples_to_queue[last + 0];
                previous_output_frame[1] = samples_to_queue[last + 1];
                has_previous_output_frame = true;
            }

            // Apply the master volume gain to the float PCM before queueing.
            const float gain = audio_volume.load(std::memory_order_relaxed);
            if (gain < 1.0f) {
                uint32_t sample_words = queue_bytes / sizeof(float);
                float* samples = static_cast<float*>(samples_to_queue);
                for (uint32_t i = 0; i < sample_words; i++) {
                    samples[i] *= gain;
                }
            }

            if (SDL_QueueAudio(audio_device, samples_to_queue, queue_bytes) < 0) {
                if (collect_audio_telemetry) audio_telemetry.queue_errors++;
                std::fprintf(stderr, "Error queueing audio: %s\n", SDL_GetError());
            }
        }

        if (collect_audio_telemetry) {
            const uint64_t queued_output_us =
                uint64_t(SDL_GetQueuedAudioSize(audio_device)) /
                (output_channels * sizeof(float)) * 1000000 / output_sample_rate;
            audio_telemetry.peak_queue_us = std::max(
                audio_telemetry.peak_queue_us, queued_output_us);
            report_audio_telemetry(queued_output_us);
        }
    }

    size_t get_frames_remaining() {
        if (audio_device == 0
            || app_backgrounded.load(std::memory_order_acquire)) {
            return 0;
        }

        uint64_t buffered_byte_count = SDL_GetQueuedAudioSize(audio_device);
        if (audio_stream != nullptr) {
            const int converted_bytes = SDL_AudioStreamAvailable(audio_stream);
            if (converted_bytes > 0) {
                buffered_byte_count += static_cast<uint64_t>(converted_bytes);
            }
        }
        buffered_byte_count = buffered_byte_count * input_channels * sample_rate / output_sample_rate / output_channels;
        return static_cast<size_t>(buffered_byte_count / bytes_per_input_frame);
    }

    void poll_input() {
        // SDL event pumping belongs to the host window thread; the game input
        // callback can run on a game/runtime thread.
    }

    float normalize_axis(Sint16 value) {
        if (std::abs(value) < 8000) {
            return 0.0f;
        }
        return std::clamp(static_cast<float>(value) / 32767.0f, -1.0f, 1.0f);
    }

    float gamepad_binding_strength(
        SDL_GameController* active_controller,
        const GamepadBinding& binding) {
        if (active_controller == nullptr
            || SDL_GameControllerGetAttached(active_controller) != SDL_TRUE) {
            return 0.0f;
        }

        if (binding.kind == GamepadBindingKind::Button) {
            if (binding.code < 0 || binding.code >= SDL_CONTROLLER_BUTTON_MAX) {
                return 0.0f;
            }
            return SDL_GameControllerGetButton(active_controller, static_cast<SDL_GameControllerButton>(binding.code)) ? 1.0f : 0.0f;
        }

        if (binding.code < 0 || binding.code >= SDL_CONTROLLER_AXIS_MAX) {
            return 0.0f;
        }

        const float axis_value = normalize_axis(SDL_GameControllerGetAxis(active_controller, static_cast<SDL_GameControllerAxis>(binding.code)));
        if (binding.kind == GamepadBindingKind::AxisPositive) {
            return std::max(axis_value, 0.0f);
        }
        return std::max(-axis_value, 0.0f);
    }

    void apply_input_action(int action_index, float strength, uint16_t& out_buttons, float& out_x, float& out_y) {
        if (action_index < 0 || action_index >= input_action_count || strength <= 0.0f) {
            return;
        }

        const InputActionDescriptor& action = input_actions[action_index];
        if (action.button != 0 && strength >= 0.5f) {
            out_buttons |= action.button;
        }
        out_x += action.axis_x * strength;
        out_y += action.axis_y * strength;
    }

    bool get_input(int controller_num, uint16_t* buttons, float* x, float* y) {
        if (controller_num != 0) {
            return false;
        }
        input_poll_count.fetch_add(1, std::memory_order_relaxed);

        uint16_t out_buttons = 0;
        float out_x = 0.0f;
        float out_y = 0.0f;

        AppInputSettings input_snapshot{};
        {
            std::lock_guard<std::mutex> lock(settings_mutex);
            input_snapshot = input_settings;
        }

        const Uint8* keys = SDL_GetKeyboardState(nullptr);
        for (int i = 0; i < input_action_count; i++) {
            const SDL_Scancode scancode = input_snapshot.keyboard_bindings[i];
            uint8_t remaining = keyboard_tap_latches[i].load(std::memory_order_acquire);
            bool tapped = false;
            while (remaining != 0) {
                if (keyboard_tap_latches[i].compare_exchange_weak(
                        remaining, static_cast<uint8_t>(remaining - 1),
                        std::memory_order_acq_rel, std::memory_order_acquire)) {
                    tapped = true;
                    break;
                }
            }
            if (tapped || (scancode > SDL_SCANCODE_UNKNOWN && scancode < SDL_NUM_SCANCODES && keys[scancode])) {
                apply_input_action(i, 1.0f, out_buttons, out_x, out_y);
            }
        }

        uint32_t test_z_remaining = test_z_hold_polls.load(std::memory_order_acquire);
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
            && *test_auto_shutter_arm_on_item_subject != '\0') {
            char* end = nullptr;
            const long requested_subject = std::strtol(
                test_auto_shutter_arm_on_item_subject, &end, 10);
            if (end != test_auto_shutter_arm_on_item_subject
                && *end == '\0'
                && requested_subject == impacted_subject) {
                test_auto_shutter_armed.store(true, std::memory_order_release);
                std::fprintf(stderr,
                    "[test-input] armed auto-shutter after item impact subject=%d\n",
                    impacted_subject);
            }
        }
        if (!test_auto_shutter_armed.load(std::memory_order_acquire)) {
            auto_shutter_captured_subjects.fill(false);
            auto_shutter_locked_subject = -1;
        }
        if (test_auto_shutter_armed.load(std::memory_order_acquire)
            && test_auto_shutter != nullptr
            && *test_auto_shutter != '\0'
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
                && *test_auto_shutter_lock_subject != '\0') {
                char* end = nullptr;
                const long requested_subject = std::strtol(
                    test_auto_shutter_lock_subject, &end, 10);
                if (end != test_auto_shutter_lock_subject
                    && *end == '\0'
                    && requested_subject > 0
                    && requested_subject <= 151
                    && focused_subject == requested_subject) {
                    auto_shutter_locked_subject =
                        static_cast<std::int32_t>(requested_subject);
                    std::fprintf(stderr,
                        "[test-input] locked viewfinder on subject=%d\n",
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
                    "[test-input] auto-shutter focused subject=%d\n",
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
                && *test_auto_shutter_sweep != '\0'
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
        {
            std::lock_guard<std::mutex> lock(controller_mutex);
            auto* player_one = static_cast<SDL_GameController*>(controller_slots.player_handle(0));
            controller_active = player_one != nullptr
                && SDL_GameControllerGetAttached(player_one) == SDL_TRUE;
            for (int i = 0; i < input_action_count; ++i) {
                apply_input_action(
                    i,
                    gamepad_binding_strength(player_one, input_snapshot.gamepad_bindings[i]),
                    out_buttons,
                    out_x,
                    out_y);
            }
        }

        // Touch overlay state from the Apple shell (iOS).
#if defined(__APPLE__) && TARGET_OS_IPHONE
        uint16_t touch_btns = 0;
        float touch_x = 0.0f;
        float touch_y = 0.0f;
        snappad_touch_snapshot(&touch_btns, &touch_x, &touch_y);
        const bool touch_active = touch_btns != 0 || std::abs(touch_x) >= 0.05f || std::abs(touch_y) >= 0.05f;
        out_buttons |= touch_btns;
        out_x += touch_x;
        out_y += touch_y;
#else
        const bool touch_active = touch_buttons.load(std::memory_order_relaxed) != 0
            || std::abs(touch_stick_x.load(std::memory_order_relaxed)) >= 0.05f
            || std::abs(touch_stick_y.load(std::memory_order_relaxed)) >= 0.05f;
        out_buttons |= touch_buttons.load(std::memory_order_relaxed);
        out_x += touch_stick_x.load(std::memory_order_relaxed);
        out_y += touch_stick_y.load(std::memory_order_relaxed);
#endif

        if (test_input_replay.has_value()
            && test_input_replay_waiting_for_trigger
            && test_input_replay_waiting_for_tunnel_progress
            && SnapPad_ConsumeTunnelHiddenPathReady()) {
            test_input_replay_waiting_for_trigger = false;
            test_input_replay_waiting_for_tunnel_progress = false;
            std::fprintf(stderr,
                "[test-input] deterministic route started on the final Tunnel Electrode approach\n");
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
                        "[test-input] acquired exact hidden-path Electrode; throwing midpoint-arc pester\n");
                }
            }
            if (test_input_replay->consume_completed()) {
                std::fprintf(stderr, "[test-input] deterministic route completed\n");
                // Return control to the live keyboard/controller after the
                // bounded route. A completed replay must not leave player one
                // permanently overridden with neutral input.
                test_input_replay.reset();
            }
        }

        const float clamped_x = std::clamp(out_x, -1.0f, 1.0f);
        const float clamped_y = std::clamp(out_y, -1.0f, 1.0f);
        *buttons = out_buttons;
        *x = clamped_x;
        *y = clamped_y;

        // Keep input evidence compact: button edges and coarse stick-direction
        // changes are enough to tell whether the app delivered a touch or
        // controller action without logging every poll.
        static uint16_t previous_buttons = 0;
        static int previous_direction = 0;
        static uint64_t last_direction_log_ms = 0;
        int direction = 0;
        if (std::abs(clamped_x) >= 0.20f || std::abs(clamped_y) >= 0.20f) {
            if (std::abs(clamped_x) > std::abs(clamped_y) * 1.25f) {
                direction = clamped_x > 0.0f ? 1 : 2;
            } else if (std::abs(clamped_y) > std::abs(clamped_x) * 1.25f) {
                direction = clamped_y > 0.0f ? 3 : 4;
            } else {
                direction = 5;
            }
        }
        const uint64_t now_ms = play_session_ms();
        const bool buttons_changed = out_buttons != previous_buttons;
        const bool direction_changed = direction != previous_direction
            && (direction == 0 || now_ms >= last_direction_log_ms + 100);
        if (buttons_changed || direction_changed) {
            std::fprintf(stderr,
                "[input t=%.3fs] buttons=0x%04x stick_dir=%d touch=%d controller=%d\n",
                now_ms / 1000.0,
                out_buttons,
                direction,
                touch_active ? 1 : 0,
                controller_active ? 1 : 0);
            if (direction_changed) {
                last_direction_log_ms = now_ms;
            }
        }
        previous_buttons = out_buttons;
        previous_direction = direction;
        return true;
    }

    void set_rumble(int, bool) {
    }

    ultramodern::input::connected_device_info_t get_connected_device_info(int controller_num) {
        return snappad::input::runtime_connected_device_info(controller_num);
    }

    RspUcodeFunc* get_rsp_microcode(const OSTask* task) {
        if (task->t.type == M_AUDTASK) {
            static std::atomic<bool> announced_audio_rsp{false};
            if (!announced_audio_rsp.exchange(true, std::memory_order_relaxed)) {
                std::fprintf(stderr, "[rsp] first audio task routed to verified aspMain\n");
            }
            return aspMain;
        }
        std::fprintf(stderr, "Unknown non-graphics RSP task type: %u\n", task->t.type);
        return nullptr;
    }

    std::string get_game_thread_name(const OSThread* thread) {
        return "SNAP " + std::to_string(thread ? thread->id : 0);
    }

    std::filesystem::path installed_rom_path() {
        return app_config_path() / "pokemonsnap.n64.us.z64";
    }

    const char* rom_validation_message(recomp::RomValidationError error) {
        switch (error) {
        case recomp::RomValidationError::FailedToOpen:
            return "Could not open the selected file. Please choose your legally dumped Pokémon Snap (USA) ROM.";
        case recomp::RomValidationError::NotARom:
            return "That file does not look like an N64 ROM. Please choose your legally dumped Pokémon Snap (USA) ROM.";
        case recomp::RomValidationError::IncorrectRom:
            return "That is not the supported Pokémon Snap (USA) ROM. Please choose your legally dumped US Pokémon Snap ROM.";
        case recomp::RomValidationError::NotYet:
            return "That Pokémon Snap ROM is not supported by this build yet. Please choose the supported US Pokémon Snap ROM.";
        case recomp::RomValidationError::IncorrectVersion:
            return "That is not the supported US Pokémon Snap revision. Please choose Pokémon Snap (USA).";
        case recomp::RomValidationError::OtherError:
        default:
            return "SnapPad could not validate that ROM. Please choose your legally dumped Pokémon Snap (USA) ROM.";
        }
    }

    bool install_rom_from_path(const std::filesystem::path& rom_path, std::u8string& game_id) {
        auto rom_result = recomp::select_rom(rom_path, game_id);
        if (rom_result == recomp::RomValidationError::Good) {
            if (recomp::load_stored_rom(game_id)) {
                return true;
            }

            show_message("The ROM validated, but SnapPad could not save it into its user folder.");
            return false;
        }

        std::fprintf(stderr, "ROM validation failed for %s with error %d\n", rom_path.c_str(), static_cast<int>(rom_result));
        show_message(rom_validation_message(rom_result));
        return false;
    }

    bool ensure_rom_installed(int argc, char** argv, std::u8string& game_id) {
        if (std::filesystem::exists(installed_rom_path()) && recomp::load_stored_rom(game_id)) {
            return true;
        }

        // iOS: the shell installs the validated ROM at <App Support>/baserom.z64
        // and chdirs into that directory before calling the game entry.
        const std::filesystem::path cwd_rom = std::filesystem::current_path() / "baserom.z64";
        if (std::filesystem::exists(cwd_rom)) {
            if (install_rom_from_path(cwd_rom, game_id)) {
                return true;
            }
        }

        if (argc > 1 && install_rom_from_path(std::filesystem::path(argv[1]), game_id)) {
            return true;
        }

#if defined(__APPLE__) && !TARGET_OS_IPHONE
        // A Finder-launched .app has no command-line ROM argument. Match the
        // mobile first-run experience with a native macOS picker, then let
        // N64ModernRuntime validate and store the selected ROM privately.
        const char* selected_rom = snappad_apple_choose_rom_path();
        if (selected_rom != nullptr) {
            const std::filesystem::path selected_path(selected_rom);
            free(const_cast<char*>(selected_rom));
            if (install_rom_from_path(selected_path, game_id)) {
                return true;
            }
        }
#endif

        show_message(
            "SnapPad cannot find an installed ROM. Choose your legally dumped Pokémon Snap (USA) ROM to continue, "
            "or pass its path as the first command-line argument.");
        return false;
    }
} // namespace

// Touch bridge (Apple shell).
extern "C" void SnapPad_SetTouchButtons(uint16_t buttons) {
    touch_buttons.store(buttons, std::memory_order_relaxed);
}


extern "C" void SnapPad_SetTouchStick(float x, float y) {
    touch_stick_x.store(x, std::memory_order_relaxed);
    touch_stick_y.store(y, std::memory_order_relaxed);
}

extern "C" void SnapPad_ResetTouchInput(void) {
    touch_buttons.store(0, std::memory_order_relaxed);
    touch_stick_x.store(0.0f, std::memory_order_relaxed);
    touch_stick_y.store(0.0f, std::memory_order_relaxed);
}

// Master audio volume, 0.0 .. 1.0. Applied as a gain on the float PCM in the
// audio thread before SDL_QueueAudio.
extern "C" void SnapPad_SetAudioVolume(float volume) {
    audio_volume.store(std::clamp(volume, 0.0f, 1.0f), std::memory_order_relaxed);
}

// Graphics settings from the iOS settings sheet.
//   resolution_mode: 0 = Auto (scale to window), 1..4 = fixed multiplier
//   aspect_mode:     0 = Original (4:3), 1 = final-presentation fill/crop,
//                    2 = RT64 expanded projection (experimental)
//   image_filter:    reserved until Pokemon Snap renderer testing
// Persisted by the shell; applied here via the runtime's graphics config.
extern "C" void SnapPad_SetGraphicsConfig(int resolution_mode,
                                             int aspect_mode,
                                             int image_filter_mode) {
    (void)image_filter_mode;
    graphics_settings_applied.store(true, std::memory_order_relaxed);
    auto config = ultramodern::renderer::get_graphics_config();
    const int fixed_scale = std::clamp(resolution_mode, 0, 4);
    config.resolution_multiplier = fixed_scale > 0 ? fixed_scale : 2.0;
    switch (fixed_scale) {
        case 1:
            config.res_option = ultramodern::renderer::Resolution::Original;
            break;
        case 2:
            config.res_option = ultramodern::renderer::Resolution::Original2x;
            break;
        case 3:
        case 4:
            config.res_option = ultramodern::renderer::Resolution::Manual;
            break;
        default:
            config.res_option = ultramodern::renderer::Resolution::Auto;
            break;
    }
    config.ar_option = aspect_mode == 1
        ? ultramodern::renderer::AspectRatio::Expand
        : (aspect_mode == 2
            ? ultramodern::renderer::AspectRatio::Manual
            : ultramodern::renderer::AspectRatio::Original);
    config.filtering_option = ultramodern::renderer::TextureFiltering::PixelScaling;
    config.upscale_2d = ultramodern::renderer::Upscale2D::ScaledOnly;
    config.three_point_filtering = true;
    ultramodern::renderer::set_graphics_config(config);
}

#if defined(__APPLE__) && TARGET_OS_IPHONE
// iOS: the UIKit shell (SDL_main) calls this after ROM setup + chdir.
extern "C" int snappad_recomp_main(int argc, char** argv);
#  define SNAPPAD_MAIN snappad_recomp_main
#else
#  define SNAPPAD_MAIN main
#endif

#if defined(__APPLE__) && TARGET_OS_IPHONE
extern "C"
#endif
int SNAPPAD_MAIN(int argc, char** argv) {
    setvbuf(stderr, nullptr, _IONBF, 0);
    initialize_performance_telemetry();
    if (!initialize_test_input_replay()) {
        return EXIT_FAILURE;
    }
#if defined(__APPLE__)
    // RT64's automatic API selection prefers D3D12; on Apple, Metal is the
    // supported RHI and must be selected explicitly.
    auto graphics_config = ultramodern::renderer::get_graphics_config();
    // Default to scale-to-window resolution (crisp upscale) unless the iOS
    // settings sheet already applied a saved preference.
    if (!graphics_settings_applied.load(std::memory_order_relaxed)) {
        graphics_config.res_option = ultramodern::renderer::Resolution::Auto;
        graphics_config.ar_option = ultramodern::renderer::AspectRatio::Original;
    }
    graphics_config.api_option = ultramodern::renderer::GraphicsApi::Metal;
    ultramodern::renderer::set_graphics_config(graphics_config);
#endif

    recomp::Version version{};
    if (!recomp::Version::from_string("0.1.0", version)) {
        return EXIT_FAILURE;
    }

    std::u8string game_id = pokemon_snap::generated::game_id;
    recomp::GameEntry pokemon_snap_us = pokemon_snap::make_game_entry(
        pokemon_snap::generated::rom_xxh3,
        pokemon_snap::generated::internal_name,
        game_id,
        pokemon_snap::generated::entrypoint,
        recomp_entrypoint);

    recomp::register_config_path(app_config_path());
    recomp::register_game(pokemon_snap_us);
    std::fprintf(stderr,
        "[core] registered Pokémon Snap US: xxh3=%016llX entrypoint=0x%08X save=flashram\n",
        static_cast<unsigned long long>(pokemon_snap::generated::rom_xxh3),
        pokemon_snap::generated::entrypoint);
    pokemon_snap::register_overlays();

    if (!ensure_rom_installed(argc, argv, game_id)) {
        return EXIT_FAILURE;
    }

    recomp::rsp::callbacks_t rsp_callbacks{
        .get_rsp_microcode = get_rsp_microcode,
    };

    ultramodern::renderer::callbacks_t renderer_callbacks{
        .create_render_context = pokemon_snap::renderer::create_render_context,
    };

    ultramodern::audio_callbacks_t audio_callbacks{
        .queue_samples = queue_samples,
        .get_frames_remaining = get_frames_remaining,
        .set_frequency = set_frequency,
    };

    ultramodern::input::callbacks_t input_callbacks{
        .poll_input = poll_input,
        .get_input = get_input,
        .set_rumble = set_rumble,
        .get_connected_device_info = get_connected_device_info,
    };

    ultramodern::gfx_callbacks_t gfx_callbacks{
        .create_gfx = create_gfx,
        .create_window = create_window,
        .update_gfx = update_gfx,
    };

    ultramodern::events::callbacks_t events_callbacks{
        .vi_callback = nullptr,
        .gfx_init_callback = nullptr,
    };
    ultramodern::error_handling::callbacks_t error_callbacks{
        .message_box = show_message,
    };
    ultramodern::threads::callbacks_t thread_callbacks{
        .get_game_thread_name = get_game_thread_name,
    };

    std::thread([game_id]() {
        std::this_thread::sleep_for(std::chrono::milliseconds(750));
        recomp::start_game(game_id);
    }).detach();

    recomp::start(
        version,
        {},
        rsp_callbacks,
        renderer_callbacks,
        audio_callbacks,
        input_callbacks,
        gfx_callbacks,
        events_callbacks,
        error_callbacks,
        thread_callbacks);

    {
        std::lock_guard<std::mutex> lock(controller_mutex);
        controller_slots.close_all(controller_backend);
    }
#if defined(__APPLE__) && TARGET_OS_IPHONE
    SnapPad_SetPhysicalControllerConnected(0);
#endif
    if (audio_device != 0) {
        SDL_CloseAudioDevice(audio_device);
        audio_device = 0;
    }
    if (audio_stream != nullptr) {
        SDL_FreeAudioStream(audio_stream);
        audio_stream = nullptr;
    }
    if (performance_telemetry.file != nullptr) {
        std::fclose(performance_telemetry.file);
        performance_telemetry.file = nullptr;
    }
    SDL_Quit();

    return EXIT_SUCCESS;
}
