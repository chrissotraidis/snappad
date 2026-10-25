function(snappad_module_identity root output)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    file(GLOB_RECURSE contract_sources CONFIGURE_DEPENDS
        "${root}/port/*.h" "${root}/port/*.cpp" "${root}/port/*.mm" "${root}/port/*.patch"
        "${root}/cmake/*.cmake" "${root}/cmake/*.manifest"
        "${root}/cmake/*/CMakeLists.txt" "${root}/config/*.json")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${contract_sources}
        "${root}/CMakeLists.txt" "${root}/dependencies.lock.json"
        "${root}/scripts/module_contract.py")
    execute_process(COMMAND "${Python3_EXECUTABLE}" "${root}/scripts/module_contract.py" identity
        OUTPUT_VARIABLE identity OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
    set(${output} "${identity}" PARENT_SCOPE)
endfunction()
