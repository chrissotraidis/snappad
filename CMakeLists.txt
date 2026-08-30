cmake_minimum_required(VERSION 3.20)

project(SnapPad LANGUAGES C CXX)

include(CTest)

set(CMAKE_C_STANDARD 17)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
    set(CMAKE_OSX_DEPLOYMENT_TARGET "15.0" CACHE STRING "Minimum iOS version" FORCE)
endif()

set(SNAPPAD_VERSION "0.2.0")
set(SNAPPAD_BUILD_NUMBER "2")
set(SNAPPAD_BUILD_PROFILE "community-preview")
set(DEVELOPMENT_TEAM "" CACHE STRING
    "Apple development team used for signed iPhoneOS builds")
set(SNAPPAD_GENERATED_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/generated" CACHE PATH
    "Root containing evidence-verified ROM-derived build products")

get_filename_component(SNAPPAD_ROOT "${CMAKE_CURRENT_SOURCE_DIR}" ABSOLUTE)
add_compile_options(
    "-ffile-prefix-map=${SNAPPAD_ROOT}=."
    "-fmacro-prefix-map=${SNAPPAD_ROOT}=."
    "-fdebug-prefix-map=${SNAPPAD_ROOT}=.")

if(APPLE)
    enable_language(OBJCXX)
endif()

add_library(snappad_input STATIC
    port/runtime/accessory_policy.cpp
    port/runtime/controller_slots.cpp
    port/runtime/gyro_input_policy.cpp)
target_include_directories(snappad_input PUBLIC
    "${CMAKE_CURRENT_SOURCE_DIR}/port/runtime"
    "${CMAKE_CURRENT_SOURCE_DIR}/port/apple")

if(BUILD_TESTING)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)

    set(SNAPPAD_RUNTIME_ROOT
        "${CMAKE_CURRENT_SOURCE_DIR}/ref/paper-mario-recut/lib/N64ModernRuntime")
    add_library(snappad_overlay_registration_syntax OBJECT
        port/runtime/register_overlays.cpp)
    target_include_directories(snappad_overlay_registration_syntax PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures"
        "${CMAKE_CURRENT_SOURCE_DIR}/port/runtime"
        "${SNAPPAD_RUNTIME_ROOT}/N64Recomp/include"
        "${SNAPPAD_RUNTIME_ROOT}/librecomp/include")

    add_executable(snappad_controller_slots_test
        tests/controller_slots_test.cpp)
    target_link_libraries(snappad_controller_slots_test PRIVATE snappad_input)
    add_test(NAME snappad_controller_slots COMMAND snappad_controller_slots_test)

    add_executable(snappad_touch_tap_latch_test
        tests/touch_tap_latch_test.cpp)
    target_link_libraries(snappad_touch_tap_latch_test PRIVATE snappad_input)
    add_test(NAME snappad_touch_tap_latch COMMAND snappad_touch_tap_latch_test)

    add_executable(snappad_gyro_input_policy_test
        tests/gyro_input_policy_test.cpp)
    target_link_libraries(snappad_gyro_input_policy_test PRIVATE snappad_input)
    add_test(NAME snappad_gyro_input_policy COMMAND snappad_gyro_input_policy_test)

    add_executable(snappad_accessory_policy_test
        tests/accessory_policy_test.cpp)
    target_link_libraries(snappad_accessory_policy_test PRIVATE snappad_input)
    add_test(NAME snappad_accessory_policy COMMAND snappad_accessory_policy_test)

    add_executable(snappad_test_input_replay_test
        tests/test_input_replay_test.cpp
        port/runtime/test_input_replay.cpp)
    target_include_directories(snappad_test_input_replay_test PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/port/runtime")
    add_test(NAME snappad_test_input_replay COMMAND snappad_test_input_replay_test)

    add_executable(snappad_runtime_game_policy_test
        tests/runtime_game_policy_test.cpp
        port/runtime/game_registration.cpp
        port/runtime/n64_input_policy.cpp)
    target_link_libraries(snappad_runtime_game_policy_test PRIVATE snappad_input)
    target_include_directories(snappad_runtime_game_policy_test PRIVATE
        "${SNAPPAD_RUNTIME_ROOT}/ultramodern/include"
        "${SNAPPAD_RUNTIME_ROOT}/librecomp/include"
        "${SNAPPAD_RUNTIME_ROOT}/N64Recomp/include"
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty"
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty/concurrentqueue"
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty/sse2neon")
    add_test(NAME snappad_runtime_game_policy COMMAND snappad_runtime_game_policy_test)

    add_executable(snappad_sp_integrity_hook_test
        tests/sp_integrity_hook_test.cpp
        port/runtime/snappad_game_hooks.cpp)
    target_include_directories(snappad_sp_integrity_hook_test PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures"
        "${CMAKE_CURRENT_SOURCE_DIR}/port/runtime"
        "${SNAPPAD_RUNTIME_ROOT}/N64Recomp/include")
    add_test(NAME snappad_sp_integrity_hook COMMAND snappad_sp_integrity_hook_test)

    add_executable(snappad_address_translation_test
        tests/address_translation_test.cpp
        port/runtime/address_translation.cpp)
    target_include_directories(snappad_address_translation_test PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/port/runtime"
        "${SNAPPAD_RUNTIME_ROOT}/N64Recomp/include")
    add_test(NAME snappad_address_translation COMMAND snappad_address_translation_test)

    add_executable(snappad_n64_os_stubs_test
        tests/n64_os_stubs_test.cpp
        port/runtime/n64_os_stubs.cpp)
    target_include_directories(snappad_n64_os_stubs_test PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/port/runtime"
        "${SNAPPAD_RUNTIME_ROOT}/N64Recomp/include")
    add_test(NAME snappad_n64_os_stubs COMMAND snappad_n64_os_stubs_test)

    add_test(NAME snappad_generate_n64recomp_config
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/generate_n64recomp_config_test.py")
    add_test(NAME snappad_generate_rsp_config
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/generate_rsp_config_test.py")
    add_test(NAME snappad_audit_generation_logs
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/audit_generation_logs_test.py")
    add_test(NAME snappad_audit_dynamic_code
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/audit_dynamic_code_test.py")
    add_test(NAME snappad_runtime_patch_contract
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/runtime_patch_contract_test.py")

    set(SNAPPAD_XXHASH_ROOT
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty/xxHash")
    add_executable(snappad_rom_xxh3
        tools/rom_xxh3.c
        "${SNAPPAD_XXHASH_ROOT}/xxhash.c")
    target_include_directories(snappad_rom_xxh3 PRIVATE "${SNAPPAD_XXHASH_ROOT}")
    add_test(NAME snappad_rom_xxh3
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/rom_xxh3_test.py"
            "$<TARGET_FILE:snappad_rom_xxh3>")
    add_test(NAME snappad_generated_core_gate
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/generated_core_gate_test.py")
    add_test(NAME snappad_paperpad_shell_parity
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/scripts/audit-paperpad-shell-parity.py")
    add_test(NAME snappad_paperpad_runner_derivation
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/scripts/audit-paperpad-runner-derivation.py")
    add_test(NAME snappad_renderer_policy
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/renderer_policy_test.py")
    add_test(NAME snappad_link_probe_scope
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/link_probe_scope_test.py")
    add_test(NAME snappad_packaging_contract
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/packaging_contract_test.py")
    add_test(NAME snappad_crash_capture_derivation
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/crash_capture_derivation_test.py")
    add_test(NAME snappad_runtime_breadcrumb_contract
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/runtime_breadcrumb_contract_test.py")
    add_test(NAME snappad_readme_paperpad_coverage
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/readme_paperpad_coverage_test.py")
    add_test(NAME snappad_device_deployment_contract
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/device_deployment_contract_test.py")
    add_test(NAME snappad_perf_trace_summary
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/perf_trace_summary_test.py")
    add_test(NAME snappad_soak_trace_summary
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/soak_trace_summary_test.py")
    add_test(NAME snappad_inspect_snap_save
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/inspect_snap_save_test.py")
    add_test(NAME snappad_decomp_cpp_selection
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/decomp_cpp_selection_test.py")
    add_test(NAME snappad_recover_decomp_address_symbols
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/recover_decomp_address_symbols_test.py")
    add_test(NAME snappad_filter_decomp_defined_symbols
        COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/filter_decomp_defined_symbols_test.py")
endif()

option(SNAPPAD_BUILD_SHELL_PREVIEW "Build the ROM-free iOS shell preview" OFF)
option(SNAPPAD_BUILD_GENERATED_CORE "Compile verified generated game/RSP sources and native glue" OFF)
option(SNAPPAD_BUILD_RUNTIME_STACK "Compile the ROM-free native runtime and RT64 stack" OFF)
option(SNAPPAD_BUILD_NATIVE_APP "Link the verified generated core into the macOS app" OFF)

if(SNAPPAD_BUILD_NATIVE_APP)
    set(SNAPPAD_BUILD_GENERATED_CORE ON CACHE BOOL "Compile generated core" FORCE)
    set(SNAPPAD_BUILD_RUNTIME_STACK ON CACHE BOOL "Compile native runtime stack" FORCE)
endif()

if(SNAPPAD_BUILD_RUNTIME_STACK)
    if(NOT APPLE)
        message(FATAL_ERROR "The current SnapPad runtime-stack rung supports Apple targets only")
    endif()

    set(SNAPPAD_RECUT_ROOT
        "${CMAKE_CURRENT_SOURCE_DIR}/ref/paper-mario-recut")
    set(SNAPPAD_RUNTIME_ROOT
        "${SNAPPAD_RECUT_ROOT}/lib/N64ModernRuntime")
    set(SNAPPAD_RENDERER_ROOT
        "${SNAPPAD_RECUT_ROOT}/lib/rt64")
    set(PAPERPAD_ZSTD_SOURCE_DIR
        "${CMAKE_CURRENT_SOURCE_DIR}/ref/zstd"
        CACHE PATH "Complete pinned zstd source" FORCE)
    # Match the reviewed PaperPad/ReCut Apple runtime profile without bringing
    # any generated Pokemon Snap bytes into this ROM-free compile rung.
    set(RT64_STATIC TRUE CACHE BOOL "Build RT64 as a static library" FORCE)
    set(RT64_SDL_WINDOW_VULKAN FALSE CACHE BOOL "Use SDL Vulkan windows" FORCE)
    set(RT64_BUILD_EXAMPLES OFF CACHE BOOL "Build RT64 examples" FORCE)
    if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
        set(RT64_BUILD_TOOLS OFF CACHE BOOL "RT64 target-side host tools" FORCE)
        set(DXC_PATH
            "${SNAPPAD_RENDERER_ROOT}/src/contrib/dxc/bin/arm64/dxc-macos"
            CACHE FILEPATH "Pinned host DXC" FORCE)
        set(SNAPPAD_RT64_HOST_TOOLS
            "${CMAKE_CURRENT_SOURCE_DIR}/build-rt64-host-tools"
            CACHE PATH "Native RT64 host tools")
        set(SPIRV_CROSS_MSL_PATH
            "${SNAPPAD_RT64_HOST_TOOLS}/spirv_cross_msl"
            CACHE FILEPATH "Host spirv_cross_msl" FORCE)
        set(FILE_TO_C_PATH
            "${SNAPPAD_RT64_HOST_TOOLS}/file_to_c"
            CACHE FILEPATH "Host file_to_c" FORCE)
        set(SDL_SHARED OFF CACHE BOOL "Build SDL shared library" FORCE)
        set(SDL_STATIC ON CACHE BOOL "Build SDL static library" FORCE)
        set(SDL_TEST OFF CACHE BOOL "Build SDL tests" FORCE)
        add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/ref/SDL2" "${CMAKE_BINARY_DIR}/sdl2")
        set(SDL2_INCLUDE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/ref/SDL2/include")
        set(SDL2_LIBRARIES SDL2::SDL2-static)
    else()
        set(SNAPPAD_SDL2_STATIC_DIR
            "${CMAKE_CURRENT_SOURCE_DIR}/build-macos-sdl2"
            CACHE PATH "Pinned native SDL2 static build")
        if(NOT EXISTS "${SNAPPAD_SDL2_STATIC_DIR}/libSDL2.a")
            message(FATAL_ERROR
                "Missing pinned native SDL2 archive. Run scripts/build-sdl2.sh first.")
        endif()
        set(SDL2_INCLUDE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/ref/SDL2/include")
        set(SDL2_LIBRARIES "${SNAPPAD_SDL2_STATIC_DIR}/libSDL2.a")
    endif()
    add_compile_definitions(HLSL_CPU)
    add_subdirectory("${SNAPPAD_RENDERER_ROOT}" "${CMAKE_BINARY_DIR}/rt64")
    if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
        target_compile_options(rt64 PRIVATE
            -Wno-shorten-64-to-32
            -Wno-nontrivial-memcall
            -Wno-deprecated-literal-operator)
    endif()

    set(N64MODERN_NO_DYNAMIC_CODE ON CACHE BOOL "Disable runtime code generation" FORCE)
    set(WITH_ARES_BRIDGE OFF CACHE BOOL "Disable ares bridge" FORCE)
    add_subdirectory("${SNAPPAD_RUNTIME_ROOT}" "${CMAKE_BINARY_DIR}/runtime")
    if(TARGET fmt)
        target_compile_definitions(fmt PUBLIC FMT_USE_CONSTEVAL=0)
    endif()

    add_library(snappad_runtime_stack INTERFACE)
    target_link_libraries(snappad_runtime_stack INTERFACE
        librecomp ultramodern rt64)

    # Compile the ROM-independent runner against fixture identity/entrypoint
    # metadata. This proves the callback surface while the real generated
    # metadata and recomp_entrypoint remain gated on G1.
    if(NOT CMAKE_SYSTEM_NAME STREQUAL "iOS")
      add_library(snappad_runner_syntax OBJECT
        port/runtime/snappad_runner.cpp
        port/runtime/snappad_rt64_context.cpp
        port/runtime/test_input_replay.cpp)
    target_include_directories(snappad_runner_syntax PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures"
        "${CMAKE_CURRENT_SOURCE_DIR}/port/runtime"
        "${CMAKE_CURRENT_SOURCE_DIR}/port/apple"
        "${CMAKE_CURRENT_SOURCE_DIR}/ref/SDL2/include"
        "${SNAPPAD_RUNTIME_ROOT}/ultramodern/include"
        "${SNAPPAD_RUNTIME_ROOT}/librecomp/include"
        "${SNAPPAD_RUNTIME_ROOT}/N64Recomp/include"
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty"
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty/concurrentqueue"
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty/sse2neon"
        "${SNAPPAD_RENDERER_ROOT}/src/contrib"
        "${SNAPPAD_RENDERER_ROOT}/src/contrib/hlslpp/include"
        "${SNAPPAD_RENDERER_ROOT}/src"
        "${SNAPPAD_RENDERER_ROOT}/src/rhi"
        "${SNAPPAD_RENDERER_ROOT}/src/render"
        "${CMAKE_BINARY_DIR}/rt64/src")

    add_executable(snappad_native_link_probe EXCLUDE_FROM_ALL
        $<TARGET_OBJECTS:snappad_runner_syntax>
        tests/fixtures/native_link_probe_stubs.cpp
        port/runtime/game_registration.cpp
        port/runtime/n64_input_policy.cpp
        port/runtime/register_overlays.cpp
        port/runtime/address_translation.cpp
        port/apple/snappad_paths.mm)
    target_include_directories(snappad_native_link_probe PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures"
        "${CMAKE_CURRENT_SOURCE_DIR}/port/runtime"
        "${CMAKE_CURRENT_SOURCE_DIR}/port/apple"
        "${CMAKE_CURRENT_SOURCE_DIR}/ref/SDL2/include"
        "${SNAPPAD_RUNTIME_ROOT}/ultramodern/include"
        "${SNAPPAD_RUNTIME_ROOT}/librecomp/include"
        "${SNAPPAD_RUNTIME_ROOT}/N64Recomp/include"
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty"
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty/concurrentqueue"
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty/sse2neon")
    target_link_libraries(snappad_native_link_probe PRIVATE
        snappad_input snappad_runtime_stack
        "-framework AppKit -framework Metal -framework QuartzCore -framework CoreGraphics -framework Foundation -framework CoreVideo -framework IOKit -framework ForceFeedback -framework Carbon -framework AudioToolbox -framework CoreAudio -framework GameController -framework CoreHaptics")
    endif()
endif()

if(SNAPPAD_BUILD_GENERATED_CORE)
    set(SNAPPAD_RUNTIME_ROOT
        "${CMAKE_CURRENT_SOURCE_DIR}/ref/paper-mario-recut/lib/N64ModernRuntime")
    set(SNAPPAD_RECOMP_OUT
        "${SNAPPAD_GENERATED_ROOT}/aot/snappad_recomp_out")
    set(SNAPPAD_AUDIO_RSP_SOURCE
        "${SNAPPAD_GENERATED_ROOT}/aot/rsp/aspMain.cpp")
    set(SNAPPAD_GAME_METADATA
        "${SNAPPAD_GENERATED_ROOT}/aot/snappad_game_metadata.h")

    foreach(required_path
        "${SNAPPAD_RECOMP_OUT}/lookup.cpp"
        "${SNAPPAD_RECOMP_OUT}/recomp_overlays.inl"
        "${SNAPPAD_AUDIO_RSP_SOURCE}"
        "${SNAPPAD_GAME_METADATA}")
        if(NOT EXISTS "${required_path}")
            message(FATAL_ERROR
                "Missing verified generated core input: ${required_path}. "
                "Run scripts/build-decomp.sh with the supported ROM, then scripts/generate-game.sh.")
        endif()
    endforeach()

    file(GLOB SNAPPAD_RECOMP_SOURCES CONFIGURE_DEPENDS
        "${SNAPPAD_RECOMP_OUT}/*.c"
        "${SNAPPAD_RECOMP_OUT}/*.cpp")
    if(NOT SNAPPAD_RECOMP_SOURCES)
        message(FATAL_ERROR "No generated N64Recomp sources found in ${SNAPPAD_RECOMP_OUT}")
    endif()

    set(SNAPPAD_RUNTIME_INCLUDE_DIRS
        "${SNAPPAD_RUNTIME_ROOT}/ultramodern/include"
        "${SNAPPAD_RUNTIME_ROOT}/librecomp/include"
        "${SNAPPAD_RUNTIME_ROOT}/N64Recomp/include"
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty"
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty/concurrentqueue"
        "${SNAPPAD_RUNTIME_ROOT}/thirdparty/sse2neon")

    add_library(snappad_recompiled_funcs STATIC ${SNAPPAD_RECOMP_SOURCES})
    target_compile_options(snappad_recompiled_funcs PRIVATE
        -fno-strict-aliasing
        -Wno-unused-variable
        -Wno-implicit-function-declaration
        -Wno-shorten-64-to-32
        -Wno-pointer-sign)
    target_include_directories(snappad_recompiled_funcs PRIVATE
        "${SNAPPAD_RECOMP_OUT}"
        "${CMAKE_CURRENT_SOURCE_DIR}/port/runtime"
        ${SNAPPAD_RUNTIME_INCLUDE_DIRS})

    add_library(snappad_generated_core STATIC
        port/runtime/game_registration.cpp
        port/runtime/n64_input_policy.cpp
        port/runtime/n64_os_stubs.cpp
        port/runtime/register_overlays.cpp
        port/runtime/snappad_game_hooks.cpp
        "${SNAPPAD_AUDIO_RSP_SOURCE}")
    target_include_directories(snappad_generated_core PRIVATE
        "${SNAPPAD_GENERATED_ROOT}/aot"
        "${SNAPPAD_RECOMP_OUT}"
        "${CMAKE_CURRENT_SOURCE_DIR}/port/runtime"
        ${SNAPPAD_RUNTIME_INCLUDE_DIRS})
    target_link_libraries(snappad_generated_core PRIVATE
        snappad_input snappad_recompiled_funcs)
endif()

if(SNAPPAD_BUILD_NATIVE_APP)
    add_executable(SnapPad
        port/runtime/snappad_runner.cpp
        port/runtime/snappad_rt64_context.cpp
        port/runtime/test_input_replay.cpp
        port/runtime/address_translation.cpp
        port/apple/snappad_paths.mm)
    target_include_directories(SnapPad PRIVATE
        "${SNAPPAD_GENERATED_ROOT}/aot"
        "${SNAPPAD_RECOMP_OUT}"
        "${CMAKE_CURRENT_SOURCE_DIR}/port/runtime"
        "${CMAKE_CURRENT_SOURCE_DIR}/port/apple"
        "${CMAKE_CURRENT_SOURCE_DIR}/ref/SDL2/include"
        ${SNAPPAD_RUNTIME_INCLUDE_DIRS}
        "${SNAPPAD_RENDERER_ROOT}/src/contrib"
        "${SNAPPAD_RENDERER_ROOT}/src/contrib/hlslpp/include"
        "${SNAPPAD_RENDERER_ROOT}/src"
        "${SNAPPAD_RENDERER_ROOT}/src/rhi"
        "${SNAPPAD_RENDERER_ROOT}/src/render"
        "${CMAKE_BINARY_DIR}/rt64/src")
    target_link_libraries(SnapPad PRIVATE
        snappad_generated_core snappad_input snappad_runtime_stack)
    if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
        target_sources(SnapPad PRIVATE
            port/apple/ios_main.mm
            port/apple/rom_setup.mm
            port/apple/diagnostics.mm
            port/apple/PrivacyInfo.xcprivacy
            port/apple/Assets.xcassets)
        set_source_files_properties(
            port/apple/PrivacyInfo.xcprivacy
            port/apple/Assets.xcassets
            PROPERTIES MACOSX_PACKAGE_LOCATION Resources)
        target_link_libraries(SnapPad PRIVATE
            SDL2::SDL2main SDL2::SDL2-static
            "-framework UIKit -framework Metal -framework QuartzCore -framework CoreGraphics -framework CoreMotion -framework Foundation -framework UniformTypeIdentifiers")
        set_target_properties(SnapPad PROPERTIES
            MACOSX_BUNDLE TRUE
            MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/port/apple/Info.plist.in"
            MACOSX_BUNDLE_BUNDLE_NAME "SnapPad"
            MACOSX_BUNDLE_GUI_IDENTIFIER "com.chrissotraidis.snappad"
            MACOSX_BUNDLE_SHORT_VERSION_STRING "${SNAPPAD_VERSION}"
            MACOSX_BUNDLE_BUNDLE_VERSION "${SNAPPAD_BUILD_NUMBER}"
            OUTPUT_NAME "SnapPad"
            XCODE_ATTRIBUTE_IPHONEOS_DEPLOYMENT_TARGET "15.0"
            XCODE_ATTRIBUTE_CODE_SIGN_STYLE Automatic
            XCODE_ATTRIBUTE_DEVELOPMENT_TEAM "${DEVELOPMENT_TEAM}"
            XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "com.chrissotraidis.snappad"
            XCODE_ATTRIBUTE_ASSETCATALOG_COMPILER_APPICON_NAME "AppIcon"
            # Native iPhone + iPad support, matching PaperPad rather than
            # forcing an iPhone compatibility window on iPadOS.
            XCODE_ATTRIBUTE_TARGETED_DEVICE_FAMILY "1,2")
    else()
        target_link_libraries(SnapPad PRIVATE
            "-framework AppKit -framework Metal -framework QuartzCore -framework CoreGraphics -framework Foundation -framework CoreVideo -framework IOKit -framework ForceFeedback -framework Carbon -framework AudioToolbox -framework CoreAudio -framework GameController -framework CoreHaptics")
        set_target_properties(SnapPad PROPERTIES
            MACOSX_BUNDLE TRUE
            MACOSX_BUNDLE_BUNDLE_NAME "SnapPad"
            MACOSX_BUNDLE_GUI_IDENTIFIER "com.chrissotraidis.snappad"
            MACOSX_BUNDLE_SHORT_VERSION_STRING "${SNAPPAD_VERSION}"
            MACOSX_BUNDLE_BUNDLE_VERSION "${SNAPPAD_BUILD_NUMBER}")
    endif()
endif()

if(CMAKE_SYSTEM_NAME STREQUAL "iOS" AND SNAPPAD_BUILD_SHELL_PREVIEW)
    set(CMAKE_OSX_DEPLOYMENT_TARGET "15.0" CACHE STRING "Minimum iOS version" FORCE)
    set(SDL_SHARED OFF CACHE BOOL "Build SDL shared library" FORCE)
    set(SDL_STATIC ON CACHE BOOL "Build SDL static library" FORCE)
    set(SDL_TEST OFF CACHE BOOL "Build SDL tests" FORCE)
    add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/ref/SDL2" "${CMAKE_BINARY_DIR}/sdl2")

    add_executable(SnapPadShell
        port/apple/ios_main.mm
        port/apple/rom_setup.mm
        port/apple/diagnostics.mm
        port/apple/snappad_paths.mm
        port/apple/PrivacyInfo.xcprivacy
        port/apple/Assets.xcassets
        port/runtime/shell_preview_stubs.cpp)
    set_source_files_properties(
        port/apple/PrivacyInfo.xcprivacy
        port/apple/Assets.xcassets
        PROPERTIES MACOSX_PACKAGE_LOCATION Resources)
    target_include_directories(SnapPadShell PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/port/apple"
        "${CMAKE_CURRENT_SOURCE_DIR}/port/runtime"
        "${CMAKE_CURRENT_SOURCE_DIR}/ref/SDL2/include")
    target_link_libraries(SnapPadShell PRIVATE
        SDL2::SDL2main SDL2::SDL2-static
        "-framework UIKit -framework Metal -framework QuartzCore -framework CoreGraphics -framework Foundation -framework UniformTypeIdentifiers")
    set_target_properties(SnapPadShell PROPERTIES
        MACOSX_BUNDLE TRUE
        MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/port/apple/Info.plist.in"
        MACOSX_BUNDLE_BUNDLE_NAME "SnapPad"
        MACOSX_BUNDLE_GUI_IDENTIFIER "com.chrissotraidis.snappad"
        MACOSX_BUNDLE_SHORT_VERSION_STRING "${SNAPPAD_VERSION}"
        MACOSX_BUNDLE_BUNDLE_VERSION "${SNAPPAD_BUILD_NUMBER}"
        OUTPUT_NAME "SnapPad"
        XCODE_ATTRIBUTE_IPHONEOS_DEPLOYMENT_TARGET "15.0"
        XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED "NO"
        XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "com.chrissotraidis.snappad"
        XCODE_ATTRIBUTE_ASSETCATALOG_COMPILER_APPICON_NAME "AppIcon"
        XCODE_ATTRIBUTE_TARGETED_DEVICE_FAMILY "1,2")
endif()
