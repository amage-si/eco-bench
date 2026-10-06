#!/bin/bash
# usage: tools/shot.sh <rundir> <mode> <window title> <workdir> <command...>
#
# Opens a program (tools/launch.sh), waits for its window, and captures only
# that window (grim -T on its toplevel, never a screen region): once after
# it settles and, when $KEYS is set (e.g. "Tab space"), after each key sent
# to the window alone (tools/xinput.py). Closes it with the window manager's
# close request and prints its log.
here="$(cd "$(dirname "$0")" && pwd)"
run=$1; mode=$2; title=$3; dir=$4; shift 4
"$here/launch.sh" "$run" "$mode" "$dir" "$@" > /dev/null
info=""
for i in $(seq 1 300); do
  info=$(hyprctl clients -j | python3 -I -c "
import json,sys
for c in json.load(sys.stdin):
    if c['title'] == sys.argv[1]:
        print(c['address'], c['stableId']); break" "$title")
  [ -n "$info" ] && break; sleep 0.1
done
if [ -z "$info" ]; then echo "window '$title' not found"; cat "$run/app.log"; exit 1; fi
set -- $info; A=$1; T=$2
sleep "${SETTLE:-2}"
timeout 5 grim -T "$T" "$run/shot-0.png"
n=1
for k in $KEYS; do
  python3 -I "$here/xinput.py" "$title" "$k" > /dev/null
  sleep 0.6
  timeout 5 grim -T "$T" "$run/shot-$n-$k.png"; n=$((n+1))
done
hyprctl dispatch "hl.dsp.window.close({ window = \"address:$A\" })" > /dev/null
for i in $(seq 1 50); do grep -q '^exit=' "$run/app.log" && break; sleep 0.1; done
cat "$run/app.log"
for f in "$run"/shot-*.png; do magick identify -format '%f %wx%h\n' "$f"; done
