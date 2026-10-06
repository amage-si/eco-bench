# AMAGE Eco vs GPUI

A head-to-head benchmark of [AMAGE Eco](https://github.com/amage-si) (our UI
toolkit written in Bend 2: Ankra window, Kairo/Tessra/Mokko interaction and
layout, Runika/Syllo/Dithra text, Ocula PNG, Splina SVG, Chromi draw lists,
Voltra Vulkan) and [GPUI](https://github.com/zed-industries/zed/tree/main/crates/gpui)
(Zed's Rust UI framework, wgpu on Vulkan), on the same scenes, window sizes,
assets, display path and machine.

The goal is an honest picture of where Eco stands and where to work next,
not a win. The method below was written before the first measurement and
corrected where a run showed it was wrong; each correction is stated.

**Status (2026-10-06):** the X11/XWayland comparison of the demo and the
text grid, Eco before and after two Runika fixes found here, binary sizes
and build times are measured. The campaign was stopped before the GPUI
Wayland column, the XIM side note, profiles after the fixes and saved
captures; see [Not yet measured](#not-yet-measured).

## Summary

On X11, after the Runika fixes (medians):

- **Eco wins** at rest (0 main-thread wakeups and 22 ms of CPU in 10 s,
  against GPUI's 120 wakeups per second and 71 ms), memory (104 against
  144 MiB in the demo, 117 against 215 MiB with 5000 labels), binary size
  (3.2 against 40.2 MB) and the response to input that changes no text
  (1.9 against 5.0 ms from key-down to the presented frame: Eco draws as
  soon as the event arrives; GPUI's X11 client draws on its next 120 Hz
  refresh tick). It also starts and responds faster in the 200 and 1000
  label grids.
- **Eco loses** when text changes: 6.1 against 4.0 ms of CPU per update in
  the demo (4.6 against 2.6 ms on the main thread), activation 7.3 against
  5.3 ms; the demo starts in 537 against 481 ms; and every Eco change costs
  a full 85-93 s build at 3.8-5.1 GiB, against 2-4 s for cargo's
  incremental build.
- **Even:** resize (13.5 against 11.7 ms) and 5000 labels (about 33 ms per
  update for both).
- **Found and fixed in Eco:** an activation took 168 ms as found. Runika
  read every font byte through a tree whose every level computed
  `U32.pow(2, p)`, and scanned all 94 `cmap` segments for every character.
  Two commits ([0ab65e3](https://github.com/amage-si/runika/commit/0ab65e3),
  [c2b4af9](https://github.com/amage-si/runika/commit/c2b4af9)) brought the
  activation to 7.3 ms and the 5000-label startup from 12.9 to 0.48 s.

## What is compared

| | AMAGE Eco | GPUI |
| --- | --- | --- |
| Revision | Sibling repositories at the commits in [results/versions.txt](results/versions.txt) | `github.com/zeronsh/zui` rev `c2d273dc3dadcb260b0fa7c35fc2fe02a14f5add`, the revision Farol pins (its lockfile, pruned by cargo to this program) |
| Language and toolchain | Bend 2.0.35 (compiler in TypeScript on Bun, native build through C and clang) | Rust 1.99.0 (cargo, LLVM) |
| Build | `bend <file> -o <bin>` (the native build Bend ships, clang with `-O3`) | `cargo build --release` (opt-level 3, no LTO, like Farol's release profile) |
| Window | Ankra: Xlib window, XWayland | GPUI's X11 client (x11rb/xcb), XWayland; its native Wayland client is the planned side column |
| Presentation | Voltra: Vulkan, FIFO | wgpu's Vulkan backend: FIFO on X11 (GPUI's default there); Mailbox on Wayland (GPUI's choice there) |
| GPU | NVIDIA GeForce RTX 3050 Laptop (the only Vulkan device), driver 610.57.04 | same |

Machine: AMD Ryzen 7 5800H (16 threads), 31 GiB, Arch Linux (Omarchy),
kernel 7.2.5, Hyprland 0.56.2 with XWayland 24.1.13, two 1920x1080 displays
at 120 Hz.

## Scenes

All scenes open at 900x560 at scale 1, with the same font file (Liberation
Sans 2.1.5 Regular, `/usr/share/fonts/liberation/LiberationSans-Regular.ttf`,
loaded explicitly by both programs), the same colors and the same layout
rules. Line height is the font's `(ascender - descender + lineGap) /
unitsPerEm` from `hhea` = 1.1499 em, which is what Syllo uses; GPUI is given
the same line height explicitly.

### 1. Demo

The Eco integrated demo, unchanged (Chromi `examples/eco/main.bend`), against
a faithful GPUI reproduction (`gpui-bench demo`):

- Background `#0D141E`; a panel inset 24 px, radius 18, fill `#151A20`,
  1 px border `#313A40`; content inset 32 px inside the panel.
- Wide layout (width >= 760): a text column at the content's left, width
  `max(120, w - 112 - 256 - 40)`, and a 256 px media column at the content's
  right, children centered. Narrow layout: text above, media below (420 px).
  Children of both columns are stacked with a 14 px gap.
- Text column: a 64x4 accent bar `#40F3BE` 14 px above the title; "AMAGE
  Eco" 34 px `#EEF1F9`; the subtitle 19 px `#B0C0CA`; the accented body
  paragraph 16 px `#EEF1F9`, wrapped to the column; the button; the status
  line 16 px `#B0C0CA`.
- Button (Mokko's): label "Ativar" 18 px white, size `(label width + 32) x
  max(44, label height + 20)`, radius 10, fill `#245CCE` (hover `#3170E6`,
  pressed `#183F96`); when focused, a 2 px ring `#A4C8FF` inset 2 px with
  radius 9.
- Media column: `/usr/share/pixmaps/kitty.png` (256x256 RGBA, from kitty
  0.48.2) decoded at startup; its caption 13 px; the SVG heart
  (`Splina/fixtures/heart-fill.svg`) at 96x96 in `#F35157`; its caption 13 px.
- Interaction (Kairo's rules, reproduced in GPUI): Tab focuses the button;
  Space or Enter key-down shows the pressed color, key-up activates; an
  activation increments the counter and the status line becomes "Ativado N
  vez(es).". Both programs build the PNG and SVG before the first frame, so
  the first frame is complete in both.

The two windows were compared side by side during development (demo, and
the grid with 200 labels, after Tab and an activation): same layout, wrap
points, colors, focus ring, image and heart. Visible differences: GPUI's
baseline sits up to 1 px lower (it centers the line gap) and its text looks
slightly heavier (its glyph contrast and gamma). Those captures were not
kept; saved side-by-side captures are pending.

### 2. Text grid

`N` labels plus a counter, to see how the cost of a redraw grows with
content (Chromi `examples/eco/grid.bend`, `gpui-bench grid N`):

- The same button at (16, 8) and, 16 px to its right, the counter "Ativações:
  N" (16 px `#EEF1F9`), vertically centered on the button.
- `N` labels "0001".."N" (10 px `#B0C0CA`) in a grid of 31 columns, cells
  28x12 px, origin (16, 64), row by row.
- N = 200, 1000 and 5000. At 200 and 1000 every label is inside the window;
  at 5000 rows below the window's bottom edge are drawn outside it (about
  1,240 labels visible). Both programs submit every label each frame; what
  each toolkit does with off-window content is part of the result.
- An activation changes only the counter label. Eco keeps the labels'
  prepared text runs and re-prepares the counter (its API leaves caching to
  the app); GPUI re-renders its whole view and reuses shaped lines through
  its own frame-to-frame cache.

### 3. Resize

The demo scene resized by the window manager through a fixed sequence:
900x560 -> 1100x700 -> 640x760 -> 1280x480 -> 760x560 -> 900x560, one step
every 1.5 s (`hyprctl dispatch hl.dsp.window.resize`). The test windows are
opened with Hyprland's per-window `no_anim` rule so the window manager
applies each size at once (global settings untouched).

## Metrics

Every presented frame is timestamped by a small Vulkan layer
([tools/presentlog/](tools/presentlog/)) enabled only in the benchmark's
processes through `VK_LAYER_PATH`/`VK_INSTANCE_LAYERS`: it records
`CLOCK_MONOTONIC` on entry to and return from each `vkQueuePresentKHR`, the
swapchain it presents, and each swapchain's extent at creation. **Presented**
means `vkQueuePresentKHR` returned: the frame was handed to the presentation
engine (not when it reached the display). Both toolkits go through the same
layer, driver and compositor.

- **Startup:** from a `CLOCK_MONOTONIC` timestamp taken by the launcher right
  before `exec` ([tools/monoexec.c](tools/monoexec.c)) to the return of the
  first present. Includes process start, font, PNG and SVG loading, text and
  layout, window and Vulkan setup, and the first frame.
- **Update:** synthetic key events sent only to the test window (XSendEvent,
  [tools/xinput.py](tools/xinput.py)): a FocusIn, Tab, then 30 activations,
  each a Space key-down and, 300 ms later, a Space key-up, 300 ms apart,
  each wait lengthened by a pseudo-random 0–8.4 ms (fixed seed: the same
  schedule for every session and program). Every key-down (pressed color)
  and every key-up (activation: counter and status text change) is one
  update. **Latency** runs from the timestamp taken right before
  `XSendEvent` to the return of the present of that update's frame. When
  every event produced exactly one frame (every reported session), frames
  are paired with events in order. **CPU per update** is the CPU time of
  all the process's threads (`/proc/<pid>/task/*/schedstat`, nanoseconds)
  from just before the first key-down to 1 s after the last key-up, divided
  by the 60 updates; reported raw, minus the program's own idle rate (from
  the idle phase of the same session), and for the main thread alone.
- **Idle:** after 2 s of settling, 10 s with no input: frames presented, CPU
  time, and voluntary plus involuntary context switches of the main thread
  and of all threads (a sleeping thread that wakes counts one).
- **Memory:** `VmRSS` at the end of the idle phase and `VmHWM` just before
  the window closes.
- **Resize:** for each step, from the moment `hyprctl` returned to the
  return of the first present on a swapchain of the new size.
- **Binary size:** the executable unstripped and after `strip --strip-all`
  (shared libraries not counted; both load Vulkan and X11 dynamically).
- **Build time:** wall and CPU time (user + system) and peak memory of the
  build's process tree ([tools/buildtime.py](tools/buildtime.py)).

One session runs the phases in order: launch and first frame, settle,
idle, update, resize (demo only), close.

Corrections made while measuring, before any reported number:

- The first trial spaced events 150 ms apart. Eco's activation, as found,
  took longer than that, so its frames queued behind the next event; the
  spacing became 300 ms and frames are paired with events in order (kept
  in `results/eco-demo-x11-asfound/spacing150-*`).
- 300 ms is exactly 36 periods of a 120 Hz frame clock: without jitter every
  event of a session lands at the same phase of GPUI's refresh timer. Three
  GPUI demo sessions measured that way had medians of 7.7, 1.5 and 6.8 ms,
  each with a spread under 0.4 ms (kept in
  `results/gpui-demo-x11/lockstep-*`). The 0–8.4 ms jitter was added. Eco
  draws as soon as an event arrives; its sessions with and without jitter
  agree (demo activation 7.4 and 7.1 ms, key-down 1.9 ms in both).
- A GPUI session started at a 1-minute load average of 14.6 (another
  program on the machine doing heavy I/O): it started 3x slower and lost 4
  activations. Its main thread stalled for more than the event spacing, so
  a key release and the next press reached GPUI's X11 client in one batch
  with the same timestamp (synthetic events carry time 0) and the client
  dropped the release as autorepeat. The session is excluded. From then on
  each phase records the CPU used by the rest of the machine and the I/O
  stall time, and the runs write their logs to tmpfs.

## Fairness rules

- **Display path:** both toolkits on XWayland for every reported number
  (GPUI with `WAYLAND_DISPLAY` unset).
- **Scale:** GPUI's X11 client derives a scale of 1.5 from this laptop
  panel's physical DPI (RandR); Ankra draws physical pixels. GPUI runs with
  `GPUI_X11_SCALE_FACTOR=1`, so both render the same 900x560 pixels.
- **Input method:** this desktop runs fcitx5 (`XMODIFIERS=@im=fcitx`). GPUI's
  X11 client routes key events through the XIM server when one is present;
  Ankra has no input method. GPUI runs with `XMODIFIERS` unset, so both
  receive key events straight from the X server.
- **Present mode:** FIFO for both (Voltra's default; wgpu's FIFO is GPUI's
  default on X11).
- **Builds:** optimized builds on both sides (see [What is compared](#what-is-compared)).
- **Threads:** Eco runs with `--threads 2 --gpu off`, as its own benchmarks
  do (`--gpu off` is Bend's compute offload, not graphics). GPUI uses its
  default executors.
- **Placement:** each window opens on workspace 1 (the laptop display),
  floating, without taking keyboard focus, through `hyprctl`; after its
  first frame the window manager moves it to (630, 310), away from the
  border with the external display above it (both programs ask for the
  display's top-left corner, where the user's pointer crosses between
  displays). Captures, when made, are of the test window only (`grim -T`).
- **Machine state:** the machine was in use. Before each session the load
  average and the CPU share of every process above 2% of a core are logged
  (process names and ids are removed from the published logs); a session
  starts only when other processes use less than 1.5 cores, when tasks
  stalled on I/O less than 5% of the last 10 s, and once the pointer has
  been on the external display for 3 s. A session whose log shows input the
  benchmark did not send (pointer motion, clicks, real focus changes) is
  discarded and run again; so is one where other processes used more than
  4 cores or tasks stalled on I/O more than 10% of its idle or update
  phase. The Farol session that drove the benchmark used about half a core.
- **Same work:** both programs log one line per input batch and per redraw.
- **Interleaving:** the last batches ran Eco and GPUI sessions interleaved
  (session 1 of each configuration, then session 2, ...).

## Results

All on X11/XWayland, FIFO, 900x560; medians, with the range across
sessions in parentheses; latencies pool every update of every session
(median / 90th percentile). Eco is at Runika `c2b4af9` (both fixes). The
tables come from `tools/report.py`, which also writes
[results/report.json](results/report.json) with the session list behind
every number.

### Demo scene

| Metric | AMAGE Eco | GPUI |
| --- | --- | --- |
| Sessions | 6 | 3 |
| Startup to first presented frame, ms | 537 (524–616) | 481 (429–488) |
| Key-down → presented, ms (median / p90) | 1.9 / 2.2 | 5.0 / 8.4 |
| Key-up, activation → presented, ms (median / p90) | 7.3 / 9.2 | 5.3 / 8.5 |
| CPU per update, all threads, ms | 6.07 (5.85–6.42) | 3.99 (3.93–4.01) |
| CPU per update minus idle rate, ms | 5.41 (5.09–5.56) | 1.75 (1.68–1.91) |
| CPU per update, main thread, ms | 4.62 (4.43–4.85) | 2.58 (2.56–2.63) |
| Idle 10 s: frames presented | 0 | 0 |
| Idle 10 s: CPU, ms | 22.1 (19.9–27.5) | 70.8 (63.9–73.8) |
| Idle 10 s: main-thread wakeups | 0 | 1208 (1204–1209) |
| Idle 10 s: wakeups, all threads | 1145 (1142–1146) | 2350 (2347–2353) |
| RSS after idle / peak, MiB | 104 / 104 | 144 / 145 |
| Resize → presented at the new size, ms (median step) | 13.5 (11.9–18.4) | 11.7 (11.7–19.0) |

Both presented exactly one frame per update in every reported session, and
nothing while idle. The wakeups of Eco's other threads (about 115 per
second) are the NVIDIA driver's own threads inside the process; GPUI's
include the same driver threads plus its 120 Hz refresh timer on the main
thread.

### Text grid

| N | Toolkit | Sessions | Startup, ms | Key-down / activation → presented, ms (median) | CPU per update, ms | Idle CPU 10 s, ms | RSS, MiB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 200 | Eco | 6 | 320 (299–360) | 1.9 / 2.2 | 3.4 (3.3–3.6) | 22 (20–25) | 99 |
| 200 | GPUI | 3 | 444 (409–500) | 6.1 / 6.2 | 4.9 (4.8–5.0) | 66 (64–75) | 146 |
| 1000 | Eco | 6 | 332 (297–378) | 6.9 / 7.2 | 8.2 (7.8–10.9) | 21 (18–28) | 101 |
| 1000 | GPUI | 2 | 490 (442–538) | 11.0 / 11.5 | 10.3 (10.0–10.5) | 72 (67–78) | 160 |
| 5000 | Eco | 5 | 483 (470–541) | 32.7 / 32.9 | 32.5 (32.2–33.9) | 21 (20–23) | 117 |
| 5000 | GPUI | 2 | 521 (479–562) | 34.9 / 33.2 | 34.0 (33.8–34.1) | 79 (75–83) | 215 |

Both redraw everything on every update. Eco also draws the ~3,760 labels
that fall outside the window at N = 5000 (Chromi keeps every operation of
the draw list); GPUI culls primitives outside the window but still builds,
lays out and paints its whole element tree.

### Eco before and after the Runika fixes

The as-found Eco (Runika `97bd37d`) was measured first. A `perf` profile of
the demo's activation (178 ms of CPU each) put 28% of the samples in
`U32.pow`, 23% in Runika's byte lookup, 23% in the runtime's closure
application and 21% in its memory release (`span_fade`, `term_drop`):
every font byte read walked Runika's byte tree computing `U32.pow(2, p)`
(p multiplications) at each of its 19 levels, and `glyph_id` read all 94
`cmap` segments for every character. The fixes keep results identical
(all checks pass; every code point 0..65535 maps to the same glyph, checked
with [tools/cmap_equiv.bend](tools/cmap_equiv.bend)). The first two
columns are medians of 3 sessions each with exactly 300 ms between events
(Eco does not depend on the phase); the last column is the final Eco of
the tables above:

| Scene | Metric | As found (Runika 97bd37d) | Byte reads O(depth) (0ab65e3) | + cmap stops at the segment (c2b4af9) |
| --- | --- | --- | --- | --- |
| Demo | Startup, ms | 731 | 653 | 537 |
| Demo | Activation → presented, ms | 168.2 | 104.5 | 7.3 |
| Demo | CPU per update, ms | 86.9 | 54.7 | 6.1 |
| Demo | Resize → presented, ms | 173.8 | 108.7 | 13.5 |
| Grid 200 | Startup, ms | 811 | 602 | 320 |
| Grid 200 | Activation → presented, ms | 9.9 | 6.4 | 2.2 |
| Grid 1000 | Startup, ms | 2784 | 1708 | 332 |
| Grid 1000 | Activation → presented, ms | 14.9 | 11.3 | 7.2 |
| Grid 5000 | Startup, ms | 12941 | 7376 | 483 |
| Grid 5000 | Activation → presented, ms | 41.4 | 38.5 | 32.9 |

### Binary size and build time

| | Unstripped | `strip --strip-all` |
| --- | --- | --- |
| GPUI `gpui-bench` (both scenes) | 40.2 MB | 29.2 MB |
| Eco demo (`examples/eco/main.bend`) | 3.16 MB | 2.98 MB |
| Eco grid (`examples/eco/grid.bend`) | 2.04 MB | 1.93 MB |

| Build | Wall | CPU (user + system) | Peak memory of the build |
| --- | --- | --- | --- |
| Eco demo, any change (3 builds) | 85–93 s | 96–105 s | 3.8–5.1 GiB |
| Eco grid, any change (3 builds) | 36–41 s | 43–48 s | 2.4 GiB |
| GPUI, first build of the program and all its crates (`-j6`, crates already downloaded; 1 build) | 158 s | 927 s | not measured |
| GPUI, `src/main.rs` changed | 1.6–4.3 s | – | not measured |

Bend has no incremental compilation: every change rebuilds Eco's libraries
from source in one compilation unit. The toolchains differ; the numbers say
what a developer waits. Raw records: [results/build/](results/build/).

### Sessions used

Each reported session is a directory under [results/](results/). The main
comparison uses `<n>` and `prelim-<n>` (both with jitter), and for Eco also
`nojitter-<n>` (the same final binaries, exactly 300 ms between events).
Not used: `lockstep-*`, `spacing150-*`, `discarded-*` (11 sessions with
input from the machine's user), `interrupted-*` (4, stopped mid-session) and
one GPUI session excluded for load (`gpui-grid1000-x11/prelim-2`). Sessions
recorded before the load measurement existed (`nojitter-*`, `prelim-*`,
the before/after runs) are kept only if the 1-minute load average was
below 6 when they started. GPUI has 2 or 3 sessions per configuration and
Eco 5 or 6, because the campaign was stopped partway.

## Where Eco stands, and what to do next

What the numbers show:

- At rest and in memory Eco is ahead: its loop sleeps on the X connection
  with no timer, and its process holds 40 to 100 MiB less.
- Eco responds faster to input that does not change text, because it draws
  at once; GPUI waits for its refresh tick (about half a 120 Hz period on
  average).
- When text changes, Eco spends more CPU than GPUI (main thread 4.6 against
  2.6 ms in the demo). After the fixes this was not profiled again; the
  work is re-preparing all seven demo texts (Syllo layout, glyph cache
  lookups in linked lists, Runika reads through the byte tree), the Tessra
  layout and rebuilding the whole draw list.
- Building Eco is slow: one compilation unit, 85–93 s and up to 5 GiB per
  change.

Highest-leverage improvements, ranked by expected gain (estimates, not
measured):

1. **Text caching:** memoize glyph id and advance per character in
   Syllo/Runika and keep the glyph cache in an array instead of a list
   searched linearly. Expected to bring the demo's activation from about 7
   toward 2 ms and to shorten every startup.
2. **Redraw less:** retain the unchanged part of the frame (damage regions)
   and drop draw-list operations outside the window. With 5000 labels the
   ~33 ms per update is the full rebuild.
3. **Flat font bytes:** an array instead of Runika's byte tree, O(1) per
   byte read.
4. **Incremental Bend builds** (toolchain): the largest cost in a day of
   work, 85–93 s per change against 2–4 s.
5. **Profile startup:** Eco's demo starts 56 ms after GPUI's; PNG decoding
   (Ocula) and SVG rasterization in Bend are the suspects.

## Caveats

- The key events are synthetic (XSendEvent to the window, time 0) and GPUI
  runs without the desktop's input method and at a forced scale of 1.
- "Presented" is the return of `vkQueuePresentKHR`, not light on the panel.
- One machine, one GPU and driver, one compositor, FIFO.
- GPUI has 2–3 sessions per configuration; the GPUI grids at 1000 and 5000
  only 2.
- The machine was in use during the campaign; discarded sessions are kept.

## Not yet measured

- GPUI on native Wayland (the side column): the tooling is in place
  (`gpui-*-wayland-auto` and `gpui-*-x11-auto` configurations: the program
  triggers its own updates from `auto 30 300 8.4 2026` on its standard
  input, since a Wayland client only receives input from the compositor's
  seat); one trial run was disturbed by pointer input and is not reported.
- GPUI on X11 with the XIM input method (`gpui-demo-x11-xim`).
- Profiles after the Runika fixes, for Eco and GPUI, and of Eco's startup.
- Saved side-by-side captures of both programs.
- Repeated clean GPUI builds and the peak memory of cargo builds.

## Reproducing

Clone the Eco repositories beside this one (capitalized names: Ankra,
Chromi, Kairo, Mokko, Ocula, Runika, Splina, Syllo, Tessra, Voltra, Dithra).
Needs Hyprland with XWayland, a Vulkan driver, Bend 2.0.35 with clang, Rust,
Python 3 and `grim`.

```sh
tools/presentlog/build.sh                          # the present-log layer
cc -O2 -o tools/monoexec tools/monoexec.c          # launch timestamps
(cd gpui && cargo build --release -j6)
cd ../Chromi && mkdir -p build/bench && export BEND_NO_TELEMETRY=1
bend examples/eco/main.bend -o build/bench/eco
bend examples/eco/grid.bend -o build/bench/grid
cd ../eco-bench
python3 tools/batch.py eco-demo-x11 gpui-demo-x11 eco-grid1000-x11 gpui-grid1000-x11 --runs 3 --interleave
python3 tools/report.py > results/report.md
```

`tools/batch.py` lists every configuration. Test windows open on workspace
1, floating and unfocused, and close themselves.

## Repository map

| Path | Purpose |
| --- | --- |
| [gpui/](gpui/) | The GPUI program (`demo`, `grid N`), pinned to Farol's GPUI revision. |
| [tools/presentlog/](tools/presentlog/) | The Vulkan layer that timestamps presents, swapchains and acquires. |
| [tools/launch.sh](tools/launch.sh), [tools/monoexec.c](tools/monoexec.c) | Launch through Hyprland with the layer and a launch timestamp. |
| [tools/session.py](tools/session.py) | One session: startup, idle, update, resize, close; raw samples. |
| [tools/batch.py](tools/batch.py) | Configurations, repeated and interleaved sessions, discards. |
| [tools/analyze.py](tools/analyze.py), [tools/report.py](tools/report.py) | Metrics per session and the published tables. |
| [tools/xinput.py](tools/xinput.py) | Synthetic X11 input to one window. |
| [tools/buildtime.py](tools/buildtime.py), [tools/versions.sh](tools/versions.sh) | Build timing and the environment record. |
| [tools/profile.py](tools/profile.py) | `perf` over a configuration's updates or startup. |
| [tools/cmap_equiv.bend](tools/cmap_equiv.bend) | The exhaustive check behind Runika `c2b4af9`. |
| [results/](results/) | Raw logs of every session (paths replaced by `<eco>`), batch logs, builds, `report.json`. |

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))
- MIT license ([LICENSE-MIT](LICENSE-MIT))

at your option. Unless you explicitly state otherwise, any contribution
intentionally submitted for inclusion in this work, as defined in the
Apache-2.0 license, shall be dual licensed as above, without any additional
terms or conditions.
