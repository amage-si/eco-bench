#!/bin/bash
# usage: tools/launch.sh <rundir> <mode> <workdir> <command...>
#
# Starts <command> through Hyprland on workspace 1 (the laptop display),
# floating, without taking keyboard focus and without window animations,
# with the present-log Vulkan layer enabled for that process only.
#
# mode: x11      XWayland, no input method (WAYLAND_DISPLAY, XMODIFIERS unset)
#       x11-xim  XWayland with the desktop's input method (XMODIFIERS kept)
#       wayland  native Wayland where the program supports it
#
# On X11, GPUI_X11_SCALE_FACTOR=1: GPUI's X11 client would otherwise derive
# 1.5 from this panel's physical DPI (RandR), while Ankra draws physical
# pixels; both must render the same 900x560 pixels. Wayland reports the
# compositor's scale (1 here).
#
# Standard input is <rundir>/control when that is a FIFO (opened read-write,
# so opening it never blocks; tools/session.py writes control lines there),
# /dev/null otherwise.
#
# Writes <rundir>/app.log (the CLOCK_MONOTONIC launch time taken right
# before exec, the program's output, its exit status) and
# <rundir>/present.log (the layer's lines).
set -e
here="$(cd "$(dirname "$0")" && pwd)"
run=$1; mode=$2; dir=$3; shift 3
mkdir -p "$run"
run="$(cd "$run" && pwd)"
case $mode in
  x11) envs="-u WAYLAND_DISPLAY -u XMODIFIERS GPUI_X11_SCALE_FACTOR=1" ;;
  x11-xim) envs="-u WAYLAND_DISPLAY GPUI_X11_SCALE_FACTOR=1" ;;
  wayland) envs="" ;;
  *) echo "unknown mode $mode" >&2; exit 2 ;;
esac
layer="VK_LAYER_PATH=$here/presentlog VK_INSTANCE_LAYERS=VK_LAYER_AMAGE_present_log AMAGE_PRESENT_LOG=$run/present.log"
input="< /dev/null"
[ -p "$run/control" ] && input="0<> $(printf %q "$run/control")"
script="$run/launch-cmd.sh"
{
  echo '#!/bin/bash'
  echo "cd $(printf %q "$dir")"
  echo "env $envs $layer $(printf %q "$here/monoexec") $(printf %q "$run/app.log") $(printf '%q ' "$@")$input >> $(printf %q "$run/app.log") 2>&1"
  echo "echo exit=\$? >> $(printf %q "$run/app.log")"
} > "$script"
chmod +x "$script"
: > "$run/app.log"
: > "$run/present.log"
hyprctl eval "hl.exec_cmd('$script', { workspace = '1 silent', float = true, no_initial_focus = true, no_anim = true })"
