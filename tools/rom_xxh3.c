#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "xxhash.h"

static int fail(const char* message, const char* path) {
    if (path != NULL) {
        fprintf(stderr, "rom_xxh3: %s: %s\n", message, path);
    } else {
        fprintf(stderr, "rom_xxh3: %s\n", message);
    }
    return EXIT_FAILURE;
}

int main(int argc, char** argv) {
    if (argc != 2) {
        return fail("usage: rom_xxh3 /absolute/path/to/normalized-rom", NULL);
    }

    const char* path = argv[1];
    FILE* stream = fopen(path, "rb");
    if (stream == NULL) {
        return fail("could not open input", path);
    }
    if (fseek(stream, 0, SEEK_END) != 0) {
        fclose(stream);
        return fail("could not seek input", path);
    }
    const long length = ftell(stream);
    if (length < 0 || fseek(stream, 0, SEEK_SET) != 0) {
        fclose(stream);
        return fail("could not determine input size", path);
    }

    const size_t size = (size_t)length;
    unsigned char* bytes = malloc(size == 0 ? 1 : size);
    if (bytes == NULL) {
        fclose(stream);
        return fail("could not allocate input buffer", path);
    }
    if (size != 0 && fread(bytes, 1, size, stream) != size) {
        free(bytes);
        fclose(stream);
        return fail("could not read complete input", path);
    }
    if (fclose(stream) != 0) {
        free(bytes);
        return fail("could not close input", path);
    }

    const uint64_t hash = XXH3_64bits(bytes, size);
    free(bytes);
    printf("0x%016" PRIX64 "\n", hash);
    return EXIT_SUCCESS;
}
