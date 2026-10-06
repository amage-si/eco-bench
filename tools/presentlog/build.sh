#!/bin/sh
# Builds the layer next to its manifest. Needs a C compiler; no Vulkan headers.
set -e
cd "$(dirname "$0")"
${CC:-cc} -O2 -Wall -Wextra -fPIC -shared -fvisibility=hidden -o libVkLayer_amage_present_log.so present_log.c -lpthread
