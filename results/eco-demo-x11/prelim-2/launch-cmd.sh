#!/bin/bash
cd <eco>/Chromi
env -u WAYLAND_DISPLAY -u XMODIFIERS GPUI_X11_SCALE_FACTOR=1 VK_LAYER_PATH=<eco>/bench/tools/presentlog VK_INSTANCE_LAYERS=VK_LAYER_AMAGE_present_log AMAGE_PRESENT_LOG=<eco>/bench/results/eco-demo-x11/2/present.log <eco>/bench/tools/monoexec <eco>/bench/results/eco-demo-x11/2/app.log ./build/bench/eco --threads 2 --gpu off < /dev/null >> <eco>/bench/results/eco-demo-x11/2/app.log 2>&1
echo exit=$? >> <eco>/bench/results/eco-demo-x11/2/app.log
