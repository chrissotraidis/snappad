#include "snappad_game_hooks.h"
#include "snappad_game_metadata.h"

#include <cstdio>
#include <cstdlib>
#include <utility>
#include <vector>

namespace {

int set_flag_calls = 0;
gpr set_flag_id = 0;
gpr set_flag_value = 0;
gpr focused_photo_id = 0;

[[noreturn]] void fail(const char* message) {
    std::fprintf(stderr, "sp_integrity_hook_test: %s\n", message);
    std::exit(EXIT_FAILURE);
}

void require(bool condition, const char* message) {
    if (!condition) fail(message);
}

void store_n64_byte(std::vector<std::uint8_t>& rdram, gpr address, std::uint8_t value) {
    *recomp_translate_address(rdram.data(), address ^ 3U) = value;
}

void reset_capture() {
    set_flag_calls = 0;
    set_flag_id = 0;
    set_flag_value = 0;
}

} // namespace

extern "C" std::uint8_t* recomp_translate_address(std::uint8_t* rdram, gpr address) {
    return rdram + (address & 0x7FFFFFU);
}

extern "C" void setPlayerFlag(std::uint8_t*, recomp_context* context) {
    ++set_flag_calls;
    set_flag_id = context->r4;
    set_flag_value = context->r5;
}

extern "C" void func_8009BCC4(std::uint8_t*, recomp_context* context) {
    context->r2 = focused_photo_id;
}

int main() {
    std::vector<std::uint8_t> rdram_storage(8 * 1024 * 1024);
    std::uint8_t* rdram = rdram_storage.data();
    recomp_context context{};

    SnapPad_ResetPhotoCaptureSession(rdram, &context);
    require(SnapPad_IsFinalTunnelElectrodeFocused() == 0,
        "Tunnel Electrode focus leaked across a capture session reset");
    require(SnapPad_WasHiddenPathImpactCommandObserved() == 0,
        "Tunnel impact command leaked across a capture session reset");
    constexpr gpr item_target = 0x80110000;
    constexpr gpr item_target_pokemon = 0x80110100;
    MEM_W(0x58, item_target) = item_target_pokemon;
    MEM_W(0x00, item_target_pokemon) = 113;
    context.r4 = item_target;
    context.r5 = 13;
    SnapPad_ObserveCommand(rdram, &context);
    require(SnapPad_ConsumeItemImpactSubject() == 113,
        "apple impact did not publish the stock target subject");
    require(SnapPad_ConsumeItemImpactSubject() == -1,
        "item impact subject was not single-consumer");
    context.r5 = 10;
    SnapPad_ObserveCommand(rdram, &context);
    require(SnapPad_ConsumeItemImpactSubject() == -1,
        "proximity command was misreported as an item impact");
    context.r5 = 13;
    SnapPad_ObserveCommand(rdram, &context);
    SnapPad_ResetPhotoCaptureSession(rdram, &context);
    require(SnapPad_ConsumeItemImpactSubject() == -1,
        "item impact subject leaked across a capture session reset");
    context.r4 = 0x80123450;
    SnapPad_ObserveHiddenPathGuard(rdram, &context);
    context.r4 = 0x80543210;
    context.r5 = 13;
    SnapPad_ObserveCommand(rdram, &context);
    require(SnapPad_WasHiddenPathImpactCommandObserved() == 0,
        "impact command for another Pokemon matched the hidden-path guard");
    context.r4 = 0x80123450;
    SnapPad_ObserveCommand(rdram, &context);
    require(SnapPad_WasHiddenPathImpactCommandObserved() == 1,
        "apple impact command did not match the hidden-path guard object");
    SnapPad_ResetPhotoCaptureSession(rdram, &context);
    require(SnapPad_WasHiddenPathImpactCommandObserved() == 0,
        "Tunnel impact command did not reset between capture sessions");
    context.r4 = 0x80123450;
    SnapPad_ObserveHiddenPathGuard(rdram, &context);
    MEM_W(0, pokemon_snap::generated::player_focus_flag_vram) = 1;
    MEM_W(0, pokemon_snap::generated::player_focus_object_vram) = 0x80123450;
    MEM_W(0, pokemon_snap::generated::player_focus_subject_vram) = 101;
    SnapPad_ObservePlayerFocus(rdram, &context);
    require(SnapPad_IsFinalTunnelElectrodeFocused() == 1,
        "player-facing focus did not identify the hidden-path guard object");
    SnapPad_ResetPhotoCaptureSession(rdram, &context);
    context.r2 = 3;
    context.f4.fl = 0.99f;
    SnapPad_ObserveTunnelProgress(rdram, &context);
    require(SnapPad_ConsumeTunnelHiddenPathReady() == 0,
        "Tunnel route armed before the final course block");
    context.r2 = 4;
    context.f4.fl = 0.0f;
    SnapPad_ObserveTunnelProgress(rdram, &context);
    require(SnapPad_ConsumeTunnelHiddenPathReady() == 1,
        "Tunnel route did not arm at the final course block entry");
    require(SnapPad_ConsumeTunnelHiddenPathReady() == 0,
        "Tunnel window trigger was not single-consumer");
    context.f4.fl = 0.25f;
    SnapPad_ObserveTunnelProgress(rdram, &context);
    require(SnapPad_ConsumeTunnelHiddenPathReady() == 0,
        "Tunnel window trigger re-armed after being consumed");

    SnapPad_ResetPhotoCaptureSession(rdram, &context);
    context.r2 = 5;
    context.f4.fl = 0.35f;
    SnapPad_ObserveTunnelProgress(rdram, &context);
    require(SnapPad_ConsumeTunnelHiddenPathReady() == 0,
        "Tunnel route armed after the hidden-path interaction window closed");
    SnapPad_ObserveHiddenPathReveal(rdram, &context);

    store_n64_byte(rdram_storage, pokemon_snap::generated::sp_imem_ok_vram, 1);
    store_n64_byte(rdram_storage, pokemon_snap::generated::sp_dmem_ok_vram, 1);
    SnapPad_RunSPIntegrityCheck(rdram, &context);
    require(set_flag_calls == 0, "healthy SP state was marked as an illegal copy");

    for (const auto [imem, dmem] : {
             std::pair{std::uint8_t{0}, std::uint8_t{1}},
             std::pair{std::uint8_t{1}, std::uint8_t{0}},
             std::pair{std::uint8_t{0}, std::uint8_t{0}},
         }) {
        reset_capture();
        store_n64_byte(rdram_storage, pokemon_snap::generated::sp_imem_ok_vram, imem);
        store_n64_byte(rdram_storage, pokemon_snap::generated::sp_dmem_ok_vram, dmem);
        SnapPad_RunSPIntegrityCheck(rdram, &context);
        require(set_flag_calls == 1, "failed SP state did not set the player flag");
        require(
            set_flag_id == pokemon_snap::generated::illegal_copy_player_flag,
            "hook set the wrong player flag");
        require(set_flag_value == 1, "hook did not enable the illegal-copy flag");
    }

    constexpr gpr stack_address = 0x80100000;
    constexpr gpr photo_address = 0x80200000;
    constexpr gpr score_address = 0x80300000;
    constexpr gpr score_offset = 0x3A0;
    context = {};
    context.r29 = stack_address;
    context.r2 = score_address;
    MEM_W(0x28, stack_address) = photo_address;

    focused_photo_id = 16;
    SnapPad_ApplyPhotoScoreFallback(rdram, &context, photo_address);
    require(MEM_HU(score_offset + 0x0A, score_address) == 0,
        "photo fallback rescored an uncorrelated report photo");
    require(MEM_W(score_offset + 0x00, score_address) == 0,
        "photo fallback supplied points without a makePhoto correlation");
    require(context.r2 == score_address,
        "photo fallback did not restore the recompiled register context");

    constexpr gpr captured_photo_address = photo_address + 0x3A0;
    constexpr gpr captured_score_address = score_address + 0x1000;
    SnapPad_ResetPhotoCaptureSession(rdram, &context);
    // Toggle-camera mode reaches makePhoto after an A edge without Z remaining
    // held. The makePhoto hook itself must therefore establish correlation.
    MEM_W(0, pokemon_snap::generated::player_focus_flag_vram) = 1;
    MEM_W(0, pokemon_snap::generated::player_focus_subject_vram) = 0x3EC;
    SnapPad_CaptureFocusedSubject(rdram, &context);
    context.r2 = captured_score_address;
    MEM_W(0x28, stack_address) = captured_photo_address;
    focused_photo_id = -1;
    SnapPad_ApplyPhotoScoreFallback(rdram, &context, captured_photo_address);
    require(MEM_HU(score_offset + 0x0A, captured_score_address) == 0x3EC,
        "photo fallback did not retain the detector subject at makePhoto");
    require(MEM_W(score_offset + 0x00, captured_score_address) == 3000,
        "photo fallback did not supply the centered-shot baseline score");
    require(MEM_HU(score_offset + 0x0C, captured_score_address) == 1000,
        "photo fallback did not supply the baseline size score");
    require(MEM_HU(score_offset + 0x10, captured_score_address) == 500,
        "photo fallback did not supply the baseline pose score");

    constexpr gpr fresh_photo_address = photo_address + 0x740;
    constexpr gpr fresh_score_address = score_address + 0x2000;
    SnapPad_ResetPhotoCaptureSession(rdram, &context);
    MEM_W(0, pokemon_snap::generated::player_focus_flag_vram) = 1;
    MEM_W(0, pokemon_snap::generated::player_focus_subject_vram) = 16;
    SnapPad_CaptureFocusedSubject(rdram, &context);
    context.r2 = fresh_score_address;
    MEM_W(0x28, stack_address) = fresh_photo_address;
    SnapPad_ApplyPhotoScoreFallback(rdram, &context, fresh_photo_address);
    require(MEM_HU(score_offset + 0x0A, fresh_score_address) == 16,
        "new detector session retained a subject from an abandoned course");

    constexpr gpr unrecognized_photo_address = photo_address + 0xAE0;
    constexpr gpr unrecognized_score_address = score_address + 0x3000;
    SnapPad_ResetPhotoCaptureSession(rdram, &context);
    MEM_W(0, pokemon_snap::generated::player_focus_flag_vram) = 1;
    MEM_W(0, pokemon_snap::generated::player_focus_subject_vram) = 143;
    SnapPad_CaptureFocusedSubject(rdram, &context);
    context.r2 = unrecognized_score_address;
    MEM_H(score_offset + 0x0A, unrecognized_score_address) = 500;
    MEM_W(score_offset + 0x00, unrecognized_score_address) = 0;
    focused_photo_id = 500;
    SnapPad_ApplyPhotoScoreFallback(rdram, &context, unrecognized_photo_address);
    require(MEM_HU(score_offset + 0x0A, unrecognized_score_address) == 143,
        "photo fallback did not replace the game's unrecognized-ID sentinel");
    require(MEM_W(score_offset + 0x00, unrecognized_score_address) == 3000,
        "unrecognized-ID recovery did not supply the centered-shot baseline score");

    context.r2 = score_address;
    MEM_W(0x28, stack_address) = photo_address;

    MEM_H(score_offset + 0x0A, score_address) = 25;
    MEM_W(score_offset + 0x00, score_address) = 4321;
    focused_photo_id = 16;
    SnapPad_ApplyPhotoScoreFallback(rdram, &context, photo_address);
    require(MEM_W(score_offset + 0x00, score_address) == 4321,
        "photo fallback replaced an authentic nonzero score");

    MEM_H(score_offset + 0x0A, score_address) = 0;
    MEM_W(score_offset + 0x00, score_address) = 0;
    focused_photo_id = 9999;
    SnapPad_ApplyPhotoScoreFallback(rdram, &context, photo_address);
    require(MEM_HU(score_offset + 0x0A, score_address) == 0,
        "photo fallback accepted an unscorable photo tag");

    std::puts("sp_integrity_hook_test: all scenarios passed");
    return EXIT_SUCCESS;
}
