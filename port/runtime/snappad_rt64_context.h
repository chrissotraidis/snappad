#pragma once

#include <cstdint>
#include <memory>

#include "ultramodern/renderer_context.hpp"

namespace pokemon_snap::renderer {

// Concrete RT64 policy remains separate from the game-neutral runner. It will
// be implemented from measured Pokemon Snap behavior; Paper Mario cadence,
// aspect, task-presentation, and enhancement assumptions are not inherited.
std::unique_ptr<ultramodern::renderer::RendererContext> create_render_context(
    std::uint8_t* rdram,
    ultramodern::renderer::WindowHandle window_handle,
    bool developer_mode);

} // namespace pokemon_snap::renderer
