#!/usr/bin/env python3
"""Regression tests for evidence-derived N64Recomp configuration."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate-n64recomp-config.py"
SPEC = importlib.util.spec_from_file_location("snappad_generate_config", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EntrypointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.splat = Path(self.tempdir.name) / "splat.yaml"
        self.splat.write_text(
            "segments:\n"
            "  - name: main\n"
            "    type: code\n"
            "    start: 0x1000\n"
            "    vram: 0x80000400\n"
            "    subsegments:\n"
            "    - [0x1000, hasm, entry]\n"
        )
        self.splat_patch = mock.patch.object(MODULE, "SPLAT", self.splat)
        self.splat_patch.start()

    def tearDown(self) -> None:
        self.splat_patch.stop()
        self.tempdir.cleanup()

    def test_zero_header_uses_unique_source_tied_entry_symbol(self) -> None:
        symbols = [(0x80000400, 0, "FUNC", "GLOBAL", "1", "func_80000400")]
        with mock.patch.object(
            MODULE, "run_readelf", return_value="Entry point address: 0x0\n"
        ):
            self.assertEqual(MODULE.derive_entrypoint(symbols), 0x80000400)

    def test_conflicting_header_is_rejected(self) -> None:
        symbols = [(0x80000400, 0, "FUNC", "GLOBAL", "1", "func_80000400")]
        with mock.patch.object(
            MODULE,
            "run_readelf",
            return_value="Entry point address: 0x80001000\n",
        ), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                MODULE.derive_entrypoint(symbols)

    def test_duplicate_entry_symbols_are_rejected(self) -> None:
        symbols = [
            (0x80000400, 0, "FUNC", "LOCAL", "1", "entry_alias"),
            (0x80000400, 0, "FUNC", "GLOBAL", "1", "func_80000400"),
        ]
        with mock.patch.object(
            MODULE, "run_readelf", return_value="Entry point address: 0x0\n"
        ), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                MODULE.derive_entrypoint(symbols)


class FunctionSizeTests(unittest.TestCase):
    def test_read_symbols_accepts_decimal_and_prefixed_hex_sizes(self) -> None:
        output = """\
Symbol table '.symtab' contains 2 entries:
 Num: Value Size Type Bind Vis Ndx Name
 1: 80000400 16 FUNC GLOBAL DEFAULT 3 entry
 2: 801dd260 0x32000 OBJECT GLOBAL DEFAULT ABS huge_object
"""
        with mock.patch.object(MODULE, "run_readelf", return_value=output):
            symbols = MODULE.read_symbols()
        self.assertEqual(symbols[0][1], 16)
        self.assertEqual(symbols[1][1], 0x32000)

    def test_alias_at_same_address_does_not_force_zero_size(self) -> None:
        sections = {1: (".text", 0x80000000, 0x40)}
        symbols = [
            (0x80000000, 0, "FUNC", "GLOBAL", "1", "first"),
            (0x80000000, 0, "NOTYPE", "GLOBAL", "1", "first_alias"),
            (0x80000010, 16, "FUNC", "GLOBAL", "1", "second"),
        ]
        self.assertEqual(
            MODULE.derive_function_sizes(symbols, sections), [("first", 0x10)]
        )

    def test_inferred_size_stops_at_input_object_boundary(self) -> None:
        sections = {3: (".main", 0x80000000, 0x100)}
        symbols = [
            (0x80000000, 0, "FUNC", "GLOBAL", "3", "function"),
            (0x80000080, 4, "OBJECT", "GLOBAL", "3", "later_data"),
        ]
        ranges = {".main": [(0x80000000, 0x80000020, "function.o")]}
        self.assertEqual(
            MODULE.derive_function_sizes(symbols, sections, ranges),
            [("function", 0x20)],
        )

    def test_local_and_rsp_end_labels_are_not_sized_as_cpu_functions(self) -> None:
        sections = {3: (".main", 0x80000000, 0x100)}
        symbols = [
            (0x80000000, 0, "FUNC", "LOCAL", "3", "nullsub"),
            (0x80000020, 0, "FUNC", "GLOBAL", "3", "aspMainTextEnd"),
        ]
        self.assertEqual(MODULE.derive_function_sizes(symbols, sections), [])

    def test_unique_defined_symbol(self) -> None:
        symbols = [(0x800484E0, 1, "OBJECT", "GLOBAL", "3", "gSPImemOkay")]
        self.assertEqual(
            MODULE.derive_unique_symbol(symbols, "gSPImemOkay"), 0x800484E0
        )

    def test_recovers_address_backed_ido_function_from_owning_object(self) -> None:
        sections = {3: (".main", 0x80000000, 0x1000)}
        symbols = [
            (0x80000180, 0, "NOTYPE", "GLOBAL", "ABS", "hidden_handler"),
        ]
        ranges = {".main": [(0x80000100, 0x80000300, "build/handler.o")]}
        object_symbols = [
            (0, 0x80, "NOTYPE", "GLOBAL", "UND", "hidden_handler"),
        ]
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE, "DECOMP", Path(directory)
        ), mock.patch.object(
            MODULE, "read_object_symbols", return_value=object_symbols
        ):
            object_path = Path(directory) / "build/handler.o"
            object_path.parent.mkdir(parents=True)
            object_path.touch()
            self.assertEqual(
                MODULE.derive_manual_functions(symbols, sections, ranges),
                [("hidden_handler", ".main", 0x80000180, 0x80)],
            )

    def test_address_backed_function_must_fit_owning_object(self) -> None:
        sections = {3: (".main", 0x80000000, 0x1000)}
        symbols = [(0x800002F0, 0, "NOTYPE", "GLOBAL", "ABS", "bad_handler")]
        ranges = {".main": [(0x80000100, 0x80000300, "handler.o")]}
        object_symbols = [(0, 0x40, "NOTYPE", "GLOBAL", "UND", "bad_handler")]
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE, "DECOMP", Path(directory)
        ), mock.patch.object(
            MODULE, "read_object_symbols", return_value=object_symbols
        ), contextlib.redirect_stderr(io.StringIO()):
            (Path(directory) / "handler.o").touch()
            with self.assertRaises(SystemExit):
                MODULE.derive_manual_functions(symbols, sections, ranges)

    def test_recovers_verified_anonymous_object_prefix(self) -> None:
        sections = {3: (".main", 0x80000000, 0x1000)}
        ranges = {
            ".main": [
                (0x80000100, 0x80000180, "build/ultralib/src/libc/sprintf.c.o")
            ]
        }
        object_symbols = [
            (0x24, 0x58, "FUNC", "GLOBAL", "4", "sprintf"),
        ]
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE, "DECOMP", Path(directory)
        ), mock.patch.object(
            MODULE, "read_object_symbols", return_value=object_symbols
        ), mock.patch.object(
            MODULE, "read_linked_jal_targets", return_value=set()
        ):
            object_path = Path(directory) / "build/ultralib/src/libc/sprintf.c.o"
            object_path.parent.mkdir(parents=True)
            object_path.touch()
            self.assertEqual(
                MODULE.derive_manual_functions([], sections, ranges),
                [("proutSprintf", ".main", 0x80000100, 0x24)],
            )

    def test_recovers_ordered_hidden_functions_from_tight_text_tail(self) -> None:
        object_symbols = [
            (0, 0x12C, "FUNC", "GLOBAL", "1", "alSndpNew"),
            (0, 0xA8, "NOTYPE", "GLOBAL", "UND", "_sndpVoiceHandler"),
            (0, 0x410, "NOTYPE", "GLOBAL", "UND", "_handleEvent"),
            (0, 0xA0, "NOTYPE", "GLOBAL", "UND", "_removeEvents"),
            (0, 0x4C, "NOTYPE", "GLOBAL", "UND", "_DivS32ByF32"),
        ]
        self.assertEqual(
            MODULE.infer_hidden_object_functions(
                object_symbols,
                {"alSndpNew"},
                [(0x1000, 0x112C)],
                0x1000,
                0x16D0,
            ),
            [
                ("_sndpVoiceHandler", 0x112C, 0xA8),
                ("_handleEvent", 0x11D4, 0x410),
                ("_removeEvents", 0x15E4, 0xA0),
                ("_DivS32ByF32", 0x1684, 0x4C),
            ],
        )

    def test_recovers_hidden_functions_across_two_close_fitting_gaps(self) -> None:
        object_symbols = [
            (0, 0x40, "NOTYPE", "GLOBAL", "UND", "first_hidden"),
            (0, 0x60, "NOTYPE", "GLOBAL", "UND", "second_hidden"),
        ]
        self.assertEqual(
            MODULE.infer_hidden_object_functions(
                object_symbols,
                set(),
                [(0x1040, 0x1080)],
                0x1000,
                0x10E0,
            ),
            [
                ("first_hidden", 0x1000, 0x40),
                ("second_hidden", 0x1080, 0x60),
            ],
        )

    def test_direct_call_entries_override_ido_symbol_order(self) -> None:
        object_symbols = [
            (0, 0x20, "NOTYPE", "GLOBAL", "UND", "second_in_table"),
            (0, 0x10, "NOTYPE", "GLOBAL", "UND", "first_in_code"),
        ]
        self.assertEqual(
            MODULE.infer_hidden_object_functions(
                object_symbols,
                set(),
                [],
                0x1000,
                0x1030,
                {0x1000, 0x1010},
            ),
            [
                ("first_in_code", 0x1000, 0x10),
                ("second_in_table", 0x1010, 0x20),
            ],
        )

    def test_derives_runtime_backed_ai_length_load_patches(self) -> None:
        symbols = [(0x80001000, 0x40, "FUNC", "GLOBAL", "3", "auThreadMain")]
        disassembly = """\
80001000: 3c18a450  lui t8,0xa450
80001004: 8f190004  lw t9,4(t8)
80001008: 3c18a450  lui t8,0xa450
8000100c: 00000000  nop
80001010: 8f0e0004  lw t6,4(t8)
"""
        with mock.patch.object(MODULE, "run_objdump_range", return_value=disassembly):
            self.assertEqual(
                MODULE.derive_ai_length_read_patches(symbols),
                [(0x80001004, 0x0040C825), (0x80001010, 0x00407025)],
            )

    def test_rejects_unverified_ai_length_read_count(self) -> None:
        symbols = [(0x80001000, 0x20, "FUNC", "GLOBAL", "3", "auThreadMain")]
        with mock.patch.object(
            MODULE,
            "run_objdump_range",
            return_value="80001000: 3c18a450  lui t8,0xa450\n",
        ), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                MODULE.derive_ai_length_read_patches(symbols)

    def test_derives_photo_score_wrapper_hook_and_saved_photo_slot(self) -> None:
        symbols = [
            (0x8037452C, 0x88, "FUNC", "GLOBAL", "4", "func_8037452C_847CDC"),
        ]
        disassembly = """\
8037456c: afa50020  sw a1,32(sp)
803745f4: ac6c0014  sw t4,20(v1)
803745f8: 8fbf001c  lw ra,28(sp)
803745fc: 27bd0020  addiu sp,sp,32
80374600: 03e00008  jr ra
"""
        with mock.patch.object(MODULE, "run_objdump_range", return_value=disassembly):
            self.assertEqual(
                MODULE.derive_photo_score_fallback_metadata(symbols),
                (0x803745F8, 0x20),
            )

    def test_rejects_missing_photo_score_wrapper_epilogue(self) -> None:
        symbols = [
            (0x8037452C, 0x88, "FUNC", "GLOBAL", "4", "func_8037452C_847CDC"),
        ]
        with mock.patch.object(
            MODULE,
            "run_objdump_range",
            return_value="8037456c: afa50020  sw a1,32(sp)\n",
        ), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                MODULE.derive_photo_score_fallback_metadata(symbols)

    def test_derives_photo_commit_focus_globals(self) -> None:
        symbols = [
            (0x8009C9E8, 0x3D8, "FUNC", "GLOBAL", "5", "makePhoto"),
            (0x80358E98, 0x7C, "FUNC", "GLOBAL", "48", "PokemonDetector_CopyInfo"),
            (0x803AE768, 0, "OBJECT", "GLOBAL", "48", "gHasPokemonInFocus"),
            (0x803AE76C, 0, "OBJECT", "GLOBAL", "48", "gPokemonInFocus"),
            (0x803AE770, 0, "OBJECT", "GLOBAL", "48", "gPokemonIdInFocus"),
        ]
        self.assertEqual(
            MODULE.derive_photo_capture_metadata(symbols),
            (0x803AE768, 0x803AE76C, 0x803AE770, 0x80358EE4),
        )

    def test_rejects_ordinary_references_that_do_not_fit_text_gaps(self) -> None:
        object_symbols = [
            (0, 0x80, "NOTYPE", "GLOBAL", "UND", "external_one"),
            (0, 0x80, "NOTYPE", "GLOBAL", "UND", "external_two"),
        ]
        self.assertEqual(
            MODULE.infer_hidden_object_functions(
                object_symbols, set(), [(0x1000, 0x10C0)], 0x1000, 0x1100
            ),
            [],
        )


class GameMetadataTests(unittest.TestCase):
    def test_native_runtime_owns_original_vi_manager_thread(self) -> None:
        self.assertEqual(MODULE.RUNTIME_OWNED_HIDDEN_FUNCTIONS, {"viMgrMain"})

    def test_all_rsp_text_boundaries_are_explicitly_classified(self) -> None:
        self.assertEqual(len(MODULE.RSP_TEXT_SYMBOLS), 8)
        self.assertIn("aspMainTextStart", MODULE.RSP_TEXT_SYMBOLS)
        self.assertIn("gspF3DEX2_NoN_fifoTextStart", MODULE.RSP_TEXT_SYMBOLS)
        self.assertEqual(
            MODULE.RSP_CONFIG_IGNORES,
            ("aspMainTextStart", "gspF3DEX2_NoN_fifoTextStart"),
        )

    def test_reads_trimmed_n64_internal_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rom = Path(directory) / "test.z64"
            rom.write_bytes(bytes(0x20) + b"POKEMON SNAP        " + bytes(32))
            self.assertEqual(MODULE.read_internal_name(rom), "POKEMON SNAP")

    def test_renders_flash_registration_constants(self) -> None:
        header = MODULE.render_game_metadata(
            "0x0123456789ABCDEF",
            "POKEMON SNAP",
            0x80000400,
            0x800484E0,
            0x800484E1,
            0x803AE768,
            0x803AE76C,
            0x803AE770,
        )
        self.assertIn("rom_xxh3 = 0x0123456789ABCDEFULL", header)
        self.assertIn("entrypoint = 0x80000400U", header)
        self.assertIn("sp_imem_ok_vram = 0x800484E0U", header)
        self.assertIn("sp_dmem_ok_vram = 0x800484E1U", header)
        self.assertIn("player_focus_flag_vram = 0x803AE768U", header)
        self.assertIn("player_focus_object_vram = 0x803AE76CU", header)
        self.assertIn("player_focus_subject_vram = 0x803AE770U", header)
        self.assertIn("illegal_copy_player_flag = 21U", header)
        self.assertIn('internal_name[] = "POKEMON SNAP"', header)
        self.assertIn('game_id[] = u8"pokemonsnap.n64.us"', header)

    def test_rejects_malformed_runtime_hash(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                MODULE.render_game_metadata(
                    "1234", "POKEMON SNAP", 0x80000400, 0x800484E0, 0x800484E1,
                    0x803AE768, 0x803AE76C, 0x803AE770
                )


if __name__ == "__main__":
    unittest.main()
