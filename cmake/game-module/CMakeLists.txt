cmake_minimum_required(VERSION 3.28)
project(SnapPadGameModule LANGUAGES C CXX)
if(NOT CMAKE_SYSTEM_NAME STREQUAL "iOS" OR NOT CMAKE_OSX_ARCHITECTURES STREQUAL "arm64")
    message(FATAL_ERROR "Use PadMint's arm64 iOS module toolchain")
endif()
get_filename_component(SNAPPAD_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
set(SNAPPAD_GENERATED_ROOT "" CACHE PATH "Verified private G2 output")
set(SNAPPAD_RECUT_ROOT "${SNAPPAD_ROOT}/ref/paper-mario-recut" CACHE PATH "Verified public runtime source")
set(SNAPPAD_INPUTS_RECORD "" CACHE FILEPATH "Complete verified module input hashes")
find_package(Python3 REQUIRED COMPONENTS Interpreter)
file(GLOB_RECURSE private_inputs CONFIGURE_DEPENDS
    "${SNAPPAD_GENERATED_ROOT}/aot/*" "${SNAPPAD_GENERATED_ROOT}/evidence/*")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${private_inputs}
    "${SNAPPAD_INPUTS_RECORD}" "${SNAPPAD_ROOT}/scripts/module_contract.py")
execute_process(COMMAND "${Python3_EXECUTABLE}" "${SNAPPAD_ROOT}/scripts/module_contract.py" verify
    "${SNAPPAD_GENERATED_ROOT}" "${SNAPPAD_RECUT_ROOT}" "${SNAPPAD_INPUTS_RECORD}" COMMAND_ERROR_IS_FATAL ANY)
include("${SNAPPAD_ROOT}/cmake/ModuleIdentity.cmake")
snappad_module_identity("${SNAPPAD_ROOT}" identity)
set(runtime "${SNAPPAD_RECUT_ROOT}/lib/N64ModernRuntime")
set(aot "${SNAPPAD_GENERATED_ROOT}/aot")
file(GLOB generated CONFIGURE_DEPENDS "${aot}/snappad_recomp_out/*.c" "${aot}/snappad_recomp_out/*.cpp")
add_library(SnapPadGame SHARED ${generated}
    "${aot}/rsp/aspMain.cpp"
    "${SNAPPAD_ROOT}/port/runtime/register_overlays.cpp"
    "${SNAPPAD_ROOT}/port/runtime/snappad_game_hooks.cpp"
    "${SNAPPAD_ROOT}/port/runtime/game_module_entry.cpp")
set_target_properties(SnapPadGame PROPERTIES C_STANDARD 17 CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON
    CXX_SCAN_FOR_MODULES OFF C_VISIBILITY_PRESET hidden CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON PREFIX "" OUTPUT_NAME "SnapPadGame")
target_include_directories(SnapPadGame PRIVATE "${SNAPPAD_ROOT}/port/runtime"
    "${aot}" "${aot}/snappad_recomp_out"
    "${runtime}/N64Recomp/include" "${runtime}/librecomp/include" "${runtime}/ultramodern/include"
    "${runtime}/thirdparty" "${runtime}/thirdparty/sse2neon" "${runtime}/thirdparty/concurrentqueue")
target_compile_definitions(SnapPadGame PRIVATE "SNAPPAD_MODULE_ID=\"${identity}\"")
target_compile_options(SnapPadGame PRIVATE -fno-strict-aliasing -Wno-implicit-function-declaration
    -Wno-unused-variable -Wno-shorten-64-to-32 -Wno-pointer-sign
    "-ffile-prefix-map=${SNAPPAD_ROOT}=." "-fmacro-prefix-map=${SNAPPAD_ROOT}=.")
target_link_options(SnapPadGame PRIVATE "LINKER:-undefined,dynamic_lookup")
