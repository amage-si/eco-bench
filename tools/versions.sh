#!/bin/bash
# usage: tools/versions.sh > results/versions.txt
# The revisions and toolchains a benchmark run used.
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../.." && pwd)"
echo "date: $(date -Iseconds)"
echo "kernel: $(uname -r)"
echo "hyprland: $(hyprctl version 2>/dev/null | head -1)"
echo "xwayland: $(pacman -Q xorg-xwayland 2>/dev/null)"
echo "gpu: $(vulkaninfo --summary 2>/dev/null | grep -m1 deviceName | sed 's/.*= //'), driver $(vulkaninfo --summary 2>/dev/null | grep -m1 driverInfo | sed 's/.*= //'), vulkan loader $(pacman -Q vulkan-icd-loader 2>/dev/null | cut -d' ' -f2)"
echo "cpu: $(grep -m1 'model name' /proc/cpuinfo | sed 's/.*: //'), $(nproc) threads"
echo "memory: $(free -g | awk '/Mem:/{print $2}') GiB"
echo "bend: $(bend version 2>/dev/null)"
echo "clang: $(clang --version | head -1)"
echo "rustc: $(rustc --version)"
echo "cargo: $(cargo --version)"
echo "gpui: zeronsh/zui $(grep -m1 -A2 'name = "gpui"' "$here/../gpui/Cargo.lock" | grep source | sed 's/.*#//;s/"//')"
echo "wgpu: $(grep -A1 '^name = "wgpu"$' "$here/../gpui/Cargo.lock" | grep version | head -1 | sed 's/.*= //;s/"//g')"
for r in Ankra Chromi Dithra Kairo Mokko Ocula Runika Splina Syllo Tessra Voltra; do
  echo "eco $r: $(git -C "$root/$r" rev-parse --short HEAD)$(git -C "$root/$r" diff --quiet HEAD -- || echo ' (modified)')"
done
