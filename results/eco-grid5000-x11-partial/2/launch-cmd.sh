#!/bin/bash
cd <eco>/Chromi
env -u WAYLAND_DISPLAY -u XMODIFIERS GPUI_X11_SCALE_FACTOR=1 VK_LAYER_PATH=<eco>/bench/tools/presentlog VK_INSTANCE_LAYERS=VK_LAYER_AMAGE_present_log AMAGE_PRESENT_LOG=/tmp/eco-bench-runs/eco-grid5000-x11-partial-2-3709760/present.log <eco>/bench/tools/monoexec /tmp/eco-bench-runs/eco-grid5000-x11-partial-2-3709760/app.log ./build/bench/grid-partial 5000 --threads 2 --gpu off < /dev/null >> /tmp/eco-bench-runs/eco-grid5000-x11-partial-2-3709760/app.log 2>&1
echo exit=$? >> /tmp/eco-bench-runs/eco-grid5000-x11-partial-2-3709760/app.log
