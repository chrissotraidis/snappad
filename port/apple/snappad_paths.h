#pragma once

#ifdef __cplusplus
extern "C" {
#endif

// Returns a strdup'd private Application Support directory, or nullptr on
// failure. The caller owns the returned string and must free it.
const char* snappad_apple_application_support_dir(void);

// macOS only: presents the native supported-ROM picker and returns a strdup'd
// absolute path. Returns nullptr on cancellation and is a no-op on iOS.
const char* snappad_apple_choose_rom_path(void);

// iOS diagnostics and Metal drawable alignment. Both are no-ops on macOS.
void snappad_log_window_diagnostics(void* ui_window, void* metal_layer);
void snappad_fix_metal_layer_scale(void* ui_window, void* metal_layer);

#ifdef __cplusplus
}
#endif
