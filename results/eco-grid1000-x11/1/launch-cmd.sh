#!/bin/bash
cd <eco>/Chromi
env -u WAYLAND_DISPLAY -u XMODIFIERS GPUI_X11_SCALE_FACTOR=1 VK_LAYER_PATH=<eco>/bench/tools/presentlog VK_INSTANCE_LAYERS=VK_LAYER_AMAGE_present_log AMAGE_PRESENT_LOG=/tmp/eco-bench-runs/eco-grid1000-x11-1-1837480/present.log <eco>/bench/tools/monoexec /tmp/eco-bench-runs/eco-grid1000-x11-1-1837480/app.log ./build/bench/grid 1000 --threads 2 --gpu off < /dev/null >> /tmp/eco-bench-runs/eco-grid1000-x11-1-1837480/app.log 2>&1
echo exit=$? >> /tmp/eco-bench-runs/eco-grid1000-x11-1-1837480/app.log
