#!/bin/bash
cd <eco>/bench
env -u WAYLAND_DISPLAY -u XMODIFIERS GPUI_X11_SCALE_FACTOR=1 VK_LAYER_PATH=<eco>/bench/tools/presentlog VK_INSTANCE_LAYERS=VK_LAYER_AMAGE_present_log AMAGE_PRESENT_LOG=<eco>/bench/results/gpui-grid5000-x11/1/present.log <eco>/bench/tools/monoexec <eco>/bench/results/gpui-grid5000-x11/1/app.log <eco>/bench/gpui/target/release/gpui-bench grid 5000 < /dev/null >> <eco>/bench/results/gpui-grid5000-x11/1/app.log 2>&1
echo exit=$? >> <eco>/bench/results/gpui-grid5000-x11/1/app.log
