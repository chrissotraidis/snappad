cmake_minimum_required(VERSION 3.28)
project(SnapPadHostTools LANGUAGES C CXX)
get_filename_component(SNAPPAD_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
set(SNAPPAD_RECUT_ROOT "" CACHE PATH "Exact ReCut source with reviewed patches")
find_package(Python3 REQUIRED COMPONENTS Interpreter)
execute_process(COMMAND "${Python3_EXECUTABLE}" "${SNAPPAD_ROOT}/scripts/module_generation.py"
    verify-source "${SNAPPAD_RECUT_ROOT}" COMMAND_ERROR_IS_FATAL ANY)
set(source "${SNAPPAD_RECUT_ROOT}/lib/N64ModernRuntime/N64Recomp")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
add_compile_definitions(FMT_USE_CONSTEVAL=0)
add_subdirectory("${source}" upstream)

# Iterate output-only sets in a stable order on MSVC and libc++. Compile a
# guarded build copy, preserving the verified public source checkout.
set(rsp_source "${source}/RSPRecomp/src/rsp_recomp.cpp")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${rsp_source}")
file(READ "${rsp_source}" rsp)
foreach(targets branch_targets.indirect_targets resume_targets.delay_targets resume_targets.non_delay_targets)
    set(needle "${targets}) {")
    string(FIND "${rsp}" "${needle}" position)
    if(position EQUAL -1)
        message(FATAL_ERROR "Pinned RSP output loop changed; review deterministic generation")
    endif()
    string(REPLACE "${needle}" "std::set<uint32_t>(${targets}.begin(), ${targets}.end())) {" rsp "${rsp}")
endforeach()
string(REPLACE "#include <unordered_set>" "#include <unordered_set>\n#include <set>" rsp "${rsp}")
file(CONFIGURE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/rsp_recomp.cpp" CONTENT "${rsp}" @ONLY)
set_property(TARGET RSPRecomp PROPERTY SOURCES "${CMAKE_CURRENT_BINARY_DIR}/rsp_recomp.cpp")

set(xxhash "${SNAPPAD_RECUT_ROOT}/lib/N64ModernRuntime/thirdparty/xxHash")
add_executable(snappad_rom_xxh3 "${SNAPPAD_ROOT}/tools/rom_xxh3.c" "${xxhash}/xxhash.c")
target_include_directories(snappad_rom_xxh3 PRIVATE "${xxhash}")

# These pinned tools use narrow filesystem paths. Select UTF-8 per process;
# CMake merges this with its ordinary execution-level manifest at link time.
if(MSVC)
    foreach(target N64RecompCLI RSPRecomp snappad_rom_xxh3)
        target_sources(${target} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/windows-utf8.manifest")
    endforeach()
endif()
