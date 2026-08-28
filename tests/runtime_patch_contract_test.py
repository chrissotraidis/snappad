#!/usr/bin/env python3
"""Check critical runtime source contracts at the exact patched dependency pin."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "ref/paper-mario-recut/lib/N64ModernRuntime/librecomp/src"
RT64_HLE = ROOT / "ref/paper-mario-recut/lib/rt64/src/hle"


class FlashContractTests(unittest.TestCase):
    def test_full_chip_clear_accepts_end_exclusive_boundary(self) -> None:
        pi_source = (RUNTIME / "pi.cpp").read_text(encoding="utf-8")
        flash_source = (RUNTIME / "flash.cpp").read_text(encoding="utf-8")
        self.assertIn(
            "assert(start + size <= save_context.save_buffer.size());", pi_source
        )
        self.assertIn(
            "save_clear(0, ultramodern::save_size, 0xFF);", flash_source
        )

    def test_paper_mario_page_wrap_policy_is_not_carried(self) -> None:
        flash_source = (RUNTIME / "flash.cpp").read_text(encoding="utf-8")
        self.assertNotIn("flash_page_offset", flash_source)

    def test_verified_recompiled_audio_precedes_paper_mario_fallbacks(self) -> None:
        rsp_source = (RUNTIME / "rsp.cpp").read_text(encoding="utf-8")
        callback = "RspUcodeFunc* ucode_func = rsp_callbacks.get_rsp_microcode(task);"
        preferred = "if (ucode_func != nullptr) goto run_recompiled_ucode;"
        fallback = "return run_hle_audio_task(rdram, task);"
        self.assertIn(callback, rsp_source)
        self.assertIn(preferred, rsp_source)
        self.assertLess(rsp_source.index(preferred), rsp_source.index(fallback))


class PresentationTelemetryContractTests(unittest.TestCase):
    def test_successful_present_path_records_worst_interval_without_logging(self) -> None:
        present_source = (RT64_HLE / "rt64_present_queue.cpp").read_text(
            encoding="utf-8"
        )
        shared_source = (RT64_HLE / "rt64_shared_queue_resources.h").read_text(
            encoding="utf-8"
        )
        successful_present = (
            "swapChainValid = ext.swapChain->present(swapChainIndex, "
            "&waitSemaphore, 1);"
        )
        interval_update = "presentIntervalCount.fetch_add("
        self.assertIn(successful_present, present_source)
        self.assertIn(interval_update, present_source)
        self.assertLess(
            present_source.index(successful_present),
            present_source.index(interval_update),
        )
        self.assertIn("presentIntervalMaxUs.compare_exchange_weak", present_source)
        self.assertNotIn("fprintf", present_source[present_source.index(interval_update):])
        for counter in (
            "presentIntervalCount",
            "presentIntervalTotalUs",
            "presentIntervalMaxUs",
            "presentIntervalsOver50Ms",
            "presentIntervalsOver100Ms",
        ):
            self.assertIn(f"std::atomic<uint64_t> {counter}", shared_source)


if __name__ == "__main__":
    unittest.main()
