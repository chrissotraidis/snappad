#include "snappad_input.h"

#include <atomic>
#include <cstdint>
#include <cstdio>

#include <SDL.h>
#include <SDL_syswm.h>

extern "C" void snappad_touch_attach(void* ui_window);

namespace {

std::atomic<float> g_volume{1.0F};
std::atomic<int> g_resolution{0};
std::atomic<int> g_aspect{0};

} // namespace

extern "C" void SnapPad_SetTouchButtons(uint16_t) {}
extern "C" void SnapPad_SetTouchStick(float, float) {}
extern "C" void SnapPad_ResetTouchInput(void) {}

extern "C" void SnapPad_SetAudioVolume(float volume) {
    g_volume.store(volume, std::memory_order_relaxed);
}

extern "C" void SnapPad_SetGraphicsConfig(
    int resolution_mode, int aspect_mode, int) {
    g_resolution.store(resolution_mode, std::memory_order_relaxed);
    g_aspect.store(aspect_mode, std::memory_order_relaxed);
}

extern "C" int SnapPad_GetEffectiveRenderState(
    uint32_t*, uint32_t*, uint32_t*) {
    return 0;
}

extern "C" int snappad_recomp_main(int, char**) {
    // This target intentionally contains no game or ROM-derived code. It lets
    // the exact native import/menu/touch shell compile and run while G1 is
    // waiting for the user's supported input.
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMECONTROLLER) != 0) {
        std::fprintf(stderr, "[SnapPad shell] SDL init failed: %s\n", SDL_GetError());
        return 1;
    }

    SDL_Window* window = SDL_CreateWindow(
        "SnapPad", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        960, 720, SDL_WINDOW_METAL | SDL_WINDOW_BORDERLESS | SDL_WINDOW_RESIZABLE);
    if (window == nullptr) {
        std::fprintf(stderr, "[SnapPad shell] window failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }

    SDL_SysWMinfo info;
    SDL_VERSION(&info.version);
    if (SDL_GetWindowWMInfo(window, &info) == SDL_TRUE) {
        snappad_touch_attach(info.info.uikit.window);
    }

    bool running = true;
    while (running) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) running = false;
        }
        SDL_Delay(16);
    }

    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
