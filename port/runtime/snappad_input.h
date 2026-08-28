#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Shared normalized N64 input bridge between the Apple shell (touch overlay)
// and the recompiled game's poll path. The iOS/UIKit shell writes touch state
// here; SnapPad's SDL poll path ORs it into controller 0.
void SnapPad_SetTouchButtons(uint16_t buttons);
void SnapPad_SetTouchStick(float x, float y);
void SnapPad_ResetTouchInput(void);
// Hides gameplay touch targets while an SDL/iOS physical controller is
// connected, then restores them on disconnect according to the saved toggle.
void SnapPad_SetPhysicalControllerConnected(int connected);
void SnapPad_SetAudioVolume(float volume);
void SnapPad_SetGraphicsConfig(int resolution_mode, int aspect_mode, int image_filter_mode);
// Returns renderer-confirmed state once RT64 has presented a frame. Scale is
// expressed in thousandths to keep this C bridge ABI simple.
int SnapPad_GetEffectiveRenderState(uint32_t* scale_milli,
                                     uint32_t* internal_width,
                                     uint32_t* internal_height);
// Returns monotonic renderer counters used by opt-in performance tracing.
// Screen updates are emulator submissions; presented frames are confirmed by
// RT64's present queue and can therefore advance at a different rate.
int SnapPad_GetFrameTelemetry(uint64_t* screen_updates,
                              uint64_t* presented_frames,
                              uint32_t* display_hz);
// Returns aggregate timing measured on RT64's actual successful-present path.
// Counts and totals are monotonic. The maximum interval is atomically consumed
// by each caller so one-second trace buckets retain their own worst frame gap.
int SnapPad_TakePresentIntervalTelemetry(uint64_t* interval_count,
                                         uint64_t* interval_total_us,
                                         uint64_t* interval_max_us,
                                         uint64_t* intervals_over_50_ms,
                                         uint64_t* intervals_over_100_ms);

#ifdef __cplusplus
}
#endif
