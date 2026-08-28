#pragma once

#include <stdint.h>

#include "recomp.h"

#ifdef __cplusplus
extern "C" {
#endif

// Declared by N64ModernRuntime but absent from the generated game function
// header because the original game reaches AI_LEN through direct MMIO reads.
void osAiGetLength_recomp(uint8_t* rdram, recomp_context* ctx);
void SnapPad_RunSPIntegrityCheck(uint8_t* rdram, recomp_context* context);
void SnapPad_ObserveControllerButtons(uint16_t buttons);
void SnapPad_ResetPhotoCaptureSession(uint8_t* rdram, recomp_context* context);
void SnapPad_ObservePlayerFocus(uint8_t* rdram, recomp_context* context);
void SnapPad_EnableAcceptancePesterBall(uint8_t* rdram, recomp_context* context);
void SnapPad_CaptureFocusedSubject(uint8_t* rdram, recomp_context* context);
void SnapPad_ObserveTunnelProgress(uint8_t* rdram, recomp_context* context);
void SnapPad_ObserveHiddenPathGuard(uint8_t* rdram, recomp_context* context);
void SnapPad_ObservePesterTrajectory(uint8_t* rdram, recomp_context* context);
void SnapPad_ObserveCommand(uint8_t* rdram, recomp_context* context);
void SnapPad_ObserveHiddenPathReveal(uint8_t* rdram, recomp_context* context);
int SnapPad_ConsumeTunnelHiddenPathReady(void);
int SnapPad_IsFinalTunnelElectrodeFocused(void);
int SnapPad_CurrentFocusedSubject(void);
int SnapPad_ConsumeItemImpactSubject(void);
int SnapPad_WasHiddenPathImpactCommandObserved(void);
void SnapPad_ApplyPhotoScoreFallback(
    uint8_t* rdram, recomp_context* context, uint32_t photo_address);

#ifdef __cplusplus
}
#endif
