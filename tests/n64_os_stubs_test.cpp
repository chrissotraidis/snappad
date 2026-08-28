#include "n64_os_stubs.h"

#include <cstdio>
#include <cstdlib>

namespace {

[[noreturn]] void fail(const char* message) {
    std::fprintf(stderr, "n64_os_stubs_test: %s\n", message);
    std::exit(EXIT_FAILURE);
}

void require(bool condition, const char* message) {
    if (!condition) fail(message);
}

} // namespace

int main() {
    recomp_context context{};

    context.r2 = 0;
    __osContRamRead_recomp(nullptr, &context);
    require(context.r2 == 1, "controller RAM read did not report PFS_ERR_NOPACK");

    context.r2 = 0;
    __osContRamWrite_recomp(nullptr, &context);
    require(context.r2 == 1, "controller RAM write did not report PFS_ERR_NOPACK");

    context.r2 = 0x1234;
    __osSetWatchLo_recomp(nullptr, &context);
    require(context.r2 == 0x1234, "WatchLo no-op modified game-visible state");

    std::puts("n64_os_stubs_test: all scenarios passed");
    return EXIT_SUCCESS;
}
