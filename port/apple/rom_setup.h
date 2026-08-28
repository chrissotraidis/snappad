#pragma once

#ifdef __cplusplus
extern "C" {
#endif

// Blocks inside UIKit's run loop only when no valid private ROM is installed.
// Returns after the user imports the supported Pokémon Snap (US) revision.
bool snappad_prepare_rom_setup(void);

// Presents replace/remove controls above the running SDL view.
void snappad_present_rom_manager(void* presenter_pointer);

#ifdef __cplusplus
}
#endif
