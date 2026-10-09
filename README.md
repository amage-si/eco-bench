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
captures; see [Not yet measured](#not-yet-measured). Later that night Eco
was measured again [after the text cache](#after-the-text-cache) (with
another session's partial redraw) and [after partial redraw](#after-partial-redraw)
was finished; the tables before those sections are kept as first measured.

## Summary

After the fast decoders ([details](#after-the-fast-decoders); 2026-10-09,
startup only, sessions under load): the demo starts in 285–300 ms. Under the
same load the previous build took 540–548 ms, and GPUI took 481 ms in earlier quiet
sessions. Assets now take 13–20 ms. The rest of startup is window and
Vulkan setup.

After the partial redraw was finished ([details](#after-partial-redraw);
medians, X11, the text cache included): with 5000 labels an activation is
presented 0.6 ms after the key (p90 0.8; GPUI 33.2 / 37.4) with 0.55 ms of
main-thread CPU per update (GPUI 32.5), and grids of 200, 1000 and 5000
labels now cost the same; the demo's activation takes 0.8 ms (p90 1.0;
GPUI 5.3 / 8.5); startup 282 ms with 5000 labels (GPUI 521) and 493 ms for
the demo (GPUI 481); resident memory 87–93 MiB (GPUI 144–215); idle stays at
0 frames and 0 main-thread wakeups. A partial frame's present names its
rectangles, so XWayland hands the compositor about a hundredth of the window
per update.

After the text cache and the partial redraw ([details](#after-the-text-cache);
medians, X11): Eco's activation that changes text takes 0.9 ms from key-up to
the presented frame (GPUI 5.3), with 2.36 ms of CPU per update on all threads
and 0.80 ms on the main thread (GPUI 3.99 and 2.58); the grids respond in
0.6 ms at 200, 1000 and 5000 labels (GPUI 6.2, 11.5, 33.2). The demo still
starts later (526 against 481 ms). The first measurement follows.

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

## After the text cache

**Status (2026-10-06, night):** a second round attacked the text path the
profile pointed at (the ranked items 1 and 3 below). It ran at the same
time as another session's partial redraw (retained frames, damage-only
redraws, culling of operations outside their clip: Chromi
[c59b59c](https://github.com/amage-si/chromi/commit/c59b59c), Voltra
[264d689](https://github.com/amage-si/voltra/commit/264d689)), so the Eco
measured here has both. The demo was also measured with the partial redraw
alone, to tell the two apart. The tables of the sections above are kept as
they were measured.

### What changed in the text path

| Repository | Commit | Change |
| --- | --- | --- |
| Runika | [47a95f0](https://github.com/amage-si/runika/commit/47a95f0) | Font bytes in a tree of 32-bit words: reads borrow the tree, with no `U32.pow`, no division and no closure per read. An aligned `u32` read: 1.7–1.9 µs → 0.20–0.26 µs. |
| Runika | [c651a8d](https://github.com/amage-si/runika/commit/c651a8d) | Every font carries a Latin-1 table (glyph and advance for U+0000..U+00FF, built when the font is parsed, same answers and errors as the `cmap`/`hmtx` path); fonts are boxed (see the finding below). |
| Syllo | [484d2b7](https://github.com/amage-si/syllo/commit/484d2b7) | Layout reads the table, carries its state in parameters instead of a closure per character, and measures a word once. |
| Voltra | [8b26312](https://github.com/amage-si/voltra/commit/8b26312), [52f51a6](https://github.com/amage-si/voltra/commit/52f51a6) | A persistent map by U32 key (Patricia trie, `keys.bend`); the atlas finds entries in it instead of walking a list with a closure per step (~10,000 closure calls per frame in the demo). |
| Chromi | [182f1ab](https://github.com/amage-si/chromi/commit/182f1ab), [b05b1f8](https://github.com/amage-si/chromi/commit/b05b1f8) | The demo's text keeps glyph masks by atlas key and prepared runs by (text, size, width) in key maps; an unchanged text costs a hash, a lookup and a comparison. Checked bit for bit against preparing from scratch. |

Why not a flat byte array: Bend 2.0.35 compiles `Array<U32>` to a native
block (~1 ns per read), but arrays are affine and a font is a shared `Data`
value kept in every model; Runika's [docs/api.md](https://github.com/amage-si/runika/blob/main/docs/api.md#byte-storage-and-performance)
has the measurements and the reasoning.

Windowless timing of the demo's update work (pure Bend, no window, same
font and assets, 100 iterations, `--threads 2`):

| Work | Before (Runika c2b4af9) | After |
| --- | --- | --- |
| Activation: rebuild the model (seven texts, layout), draw list, GPU plan | 5.1 ms | 0.11 ms |
| Hover change: draw list and GPU plan | 1.12 ms | 0.08 ms |
| The seven texts laid out by Syllo alone | 1.82 ms | 0.06 ms |
| Font load | 27 ms | 20 ms |

### A finding: the widest record sets the cost of every call

Bend's compiler passes a record that is not recursive flattened, one word
per field, through every call, and the generated C gives every segment the
same register frame, as wide as the widest record or continuation in the
program (`WL_RESW`). The demo's model holds the font (25 words), seven runs
and ten rectangles: its frame was 122 words. Adding the font's two new
fields and the text cache made it 128, and every call of the program got
about a third slower (decoding the demo's PNG and SVG went from ~147 to
~198 ms; padding the old model by the same six words did the same, while
two or four words changed nothing). Runika's `Font` is now recursive (an
`Alias` constructor nothing builds), so the compiler keeps it behind one
pointer: the demo's frame is 104 words, and a copy of a font counts one
reference instead of five. Any app can check its own with
`bend app.bend -o app.c` and `grep "#define WL_RESW" app.c`.

### Results after the text cache

Same scenes, method, fairness rules and machine as above, Eco only (GPUI's
columns are the earlier sessions). Eco binaries: `eco-text`/`grid-text` built
from the commits above on top of the partial redraw; `eco-redraw` with the
partial redraw alone (Runika c2b4af9, Syllo d360082). Medians, ranges across
sessions in parentheses; latencies pool every update (median / p90).

| Metric | Eco before (Runika c2b4af9) | Eco, partial redraw alone | Eco, text cache + partial redraw | GPUI |
| --- | --- | --- | --- | --- |
| Sessions | 6 | 3 | 3 | 3 |
| Startup to first presented frame, ms | 537 (524–616) | 610 (605–626) | 526 (478–552) | 481 (429–488) |
| Key-down → presented, ms (median / p90) | 1.9 / 2.2 | 0.7 / 0.8 | 0.7 / 0.8 | 5.0 / 8.4 |
| Key-up, activation → presented, ms (median / p90) | 7.3 / 9.2 | 7.0 / 9.2 | 0.9 / 2.9 | 5.3 / 8.5 |
| CPU per update, all threads, ms | 6.07 (5.85–6.42) | 5.43 (5.15–5.45) | 2.36 (2.24–2.37) | 3.99 (3.93–4.01) |
| CPU per update minus idle rate, ms | 5.41 (5.09–5.56) | 4.69 (4.37–4.71) | 1.60 (1.50–1.63) | 1.75 (1.68–1.91) |
| CPU per update, main thread, ms | 4.62 (4.43–4.85) | 3.91 (3.76–3.93) | 0.80 (0.77–0.85) | 2.58 (2.56–2.63) |
| Idle 10 s: frames presented | 0 | 0 | 0 | 0 |
| Idle 10 s: CPU, ms | 22.1 (19.9–27.5) | 23.9 (22.9–24.5) | 23.3 (23.0–24.3) | 70.8 (63.9–73.8) |
| Idle 10 s: main-thread wakeups | 0 | 0 | 0 | 1208 (1204–1209) |
| Idle 10 s: wakeups, all threads | 1145 (1142–1146) | 1142 (1141–1143) | 1143 (1140–1145) | 2350 (2347–2353) |
| RSS after idle / peak, MiB | 104 / 104 | 105 / 105 | 97 / 97 | 144 / 145 |
| Resize → presented at the new size, ms (median step) | 13.5 (11.9–18.4) | 15.1 (14.8–15.4) | 8.7 (8.0–11.5) | 11.7 (11.7–19.0) |

With Runika 131874b (the font's tree built in one pass), 2 sessions: startup 528 (509–548) ms, activation 0.8 / 1.9 ms, key-down 0.6 / 0.7 ms, CPU per update 2.21 (2.16–2.26) ms (main thread 0.76 (0.74–0.79)), RSS 93 MiB. The ~13 ms the font load saves (windowless) is within the spread of startup across sessions.

| N | Build | Sessions | Startup, ms | Key-down → presented, ms (median / p90) | Activation → presented, ms (median / p90) | CPU per update, all threads / main, ms | Idle CPU 10 s, ms | RSS, MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 200 | Eco before | 6 | 320 (299–360) | 1.9 / 2.1 | 2.2 / 3.8 | 3.4 (3.3–3.6) / 2.0 (2.0–2.1) | 22 (20–25) | 99 |
| 200 | Eco after | 3 | 310 (306–339) | 0.5 / 0.6 | 0.6 / 1.8 | 2.0 (1.7–2.0) / 0.6 (0.6–0.6) | 22 (22–22) | 93 |
| 200 | GPUI | 3 | 444 (409–500) | 6.1 / 9.7 | 6.2 / 9.1 | 4.9 (4.8–5.0) / 3.5 (3.5–3.6) | 66 (64–75) | 146 |
| 1000 | Eco before | 6 | 332 (297–378) | 6.9 / 8.6 | 7.2 / 9.8 | 8.2 (7.8–10.9) / 6.8 (6.5–9.1) | 21 (18–28) | 101 |
| 1000 | Eco after | 3 | 271 (261–313) | 0.5 / 0.6 | 0.6 / 2.7 | 2.0 (2.0–2.1) / 0.6 (0.6–0.6) | 23 (22–24) | 95 |
| 1000 | GPUI | 2 | 490 (442–538) | 11.0 / 14.7 | 11.5 / 14.5 | 10.3 (10.0–10.5) / 8.9 (8.5–9.2) | 72 (67–78) | 160 |
| 5000 | Eco before | 5 | 483 (470–541) | 32.7 / 35.0 | 32.9 / 35.4 | 32.5 (32.2–33.9) / 31.2 (30.6–32.5) | 21 (20–23) | 117 |
| 5000 | Eco after | 3 | 319 (313–327) | 0.5 / 0.6 | 0.6 / 1.7 | 1.9 (1.9–2.0) / 0.6 (0.6–0.6) | 21 (21–22) | 97 |
| 5000 | GPUI | 2 | 521 (479–562) | 34.9 / 37.0 | 33.2 / 37.4 | 34.0 (33.8–34.1) / 32.5 (32.5–32.5) | 79 (75–83) | 215 |

Reading the tables:

- The partial redraw alone makes input that changes no text cheap (key-down
  1.9 → 0.7 ms) but leaves the activation at 7.0 ms: rebuilding the text was
  the cost. The text cache brings the activation to 0.9 ms and the CPU per
  update to 2.36 ms (main thread 0.80 ms), below GPUI's 5.3 ms and 3.99 ms.
- The activation's p90 (2.9 ms) comes from the first ten activations
  (1.2–4.7 ms): each shows a digit for the first time, and the frames that
  upload a new glyph to the atlas spend 1–4 ms in `scene + GPU` against 0–1 ms
  for the others (the program's log). Voltra's `update` waits for the device
  to go idle (`vkDeviceWaitIdle`) and then for the copy, which is the likely
  cost (read in the code, not timed alone); parsing a new glyph's outline
  takes ~13 µs and rasterizing it at 16 px ~70 µs (measured). From the
  eleventh activation on every activation takes 0.7–1.1 ms.
- The grids include both changes and were not measured with the partial
  redraw alone. With 5000 labels the earlier cost was the full rebuild (see
  above), so most of that gain (32.9 → 0.6 ms) is presumably the partial
  redraw's (damage only, culling); re-preparing the counter is the text
  cache's part.
- Startup: 526 ms against 610 with the partial redraw alone and 537 before;
  text was ~30 ms of it (font ~20 ms, the model's 93 glyphs ~10 ms). Runika
  [131874b](https://github.com/amage-si/runika/commit/131874b), after these
  sessions, builds the font's tree in one pass: loading the font takes ~7 ms
  (windowless); in the window the startup stays the same within the
  sessions' spread (528 ms median of 2, line under the demo table). Window and Vulkan setup
  (~250 ms) and decoding the PNG and SVG (~135 ms) are most of the rest.
  GPUI starts in 481 ms.
- Resident memory went down (97 against 104–105 MiB), probably mostly the
  word tree (a quarter of the byte tree's nodes).

Correctness: every suite passes (Runika 58, Syllo 19, Dithra 15 and its
`all_tests` 92 with Runika's and Syllo's, Voltra 76 + 11 key-map + 13 GPU,
Chromi 74 + 20 GPU + 7 text-cache, Mokko 14 + 5, Auvia 74); a window capture of the GPU demo equals Chromi's CPU reference in
every pixel at 900x560 and, after the window manager resized it, at 1100x700,
and those references equal the earlier round's (0 differing pixels each).

What the profile shows now (`perf`, 10 activations, `tools/profile.py`):
~45% of the samples in Eco's program (the runtime's closure calls and memory
release, Ankra's loop, building the frame, packing quads; text is visible
only where a glyph is new), ~24% in the NVIDIA driver (mostly its own update
thread), ~15% in the kernel and ~14% in libc.

Sessions: 3 per configuration; one demo session was set aside as loaded
(other processes at 441% CPU) and three grid sessions as discarded (pointer
input from the machine's user), all rerun (`loaded-*`, `discarded-*`). The
`eco-demo-x11-final` run (Runika 131874b) was stopped after 2 clean sessions
and 4 discarded ones, while the machine's user was working over the test
window.

## After partial redraw

**Status (2026-10-07, early morning):** the bench's second ranked item,
"redraw less", is done: Eco keeps each frame as parts, redraws only what
changed, skips content outside the window and tells the compositor which
rectangles changed. The text cache of the previous section ran at the same
time (its Eco already had the first version of this work); the numbers
below say which changes each column includes. Earlier tables stay as they
were measured.

### What changed

| Repository | Commits | Change |
| --- | --- | --- |
| Chromi | [fccfc27](https://github.com/amage-si/chromi/commit/fccfc27) | Culling: a bitmap, mask or rounded box that cannot touch a pixel of its clip is not recorded; `S.visible` lets an app skip the work behind content that cannot show. |
| Chromi | [d4d3c2e](https://github.com/amage-si/chromi/commit/d4d3c2e) | Retained frames (`frame.bend`): a frame is a list of parts with stable ids (a Kairo or Mokko id for a control). The next frame keeps every part whose operations, or the app's stamp, did not change, and records as damage the old and new boxes of the parts that did. `R.repaint` paints only the damage on the CPU. |
| Chromi | [613ca7f](https://github.com/amage-si/chromi/commit/613ca7f) | `Gpu.render`: each damaged region is redrawn alone (the background, then the quads of every part that meets it, scissored). A part's quads are planned (atlas, packing) once and kept in the part; a kept part costs no lookup or packing. A first frame or a new size is drawn whole. |
| Chromi | [c59b59c](https://github.com/amage-si/chromi/commit/c59b59c), [95d6274](https://github.com/amage-si/chromi/commit/95d6274) | The demo and the grid keep their last frame. The grid's labels are one stamped part recorded once per window size, labels outside the window skipped; the button is keyed by its Kairo id. A click in the demo lays out only the status line again. |
| Voltra | [4fcd85f](https://github.com/amage-si/voltra/commit/4fcd85f), [264d689](https://github.com/amage-si/voltra/commit/264d689) | A canvas per target that keeps the picture between frames; `paint` redraws ranges of instances with the scissor on their rectangles, then copies the canvas into the acquired swapchain image (`vkCmdCopyImage`, one new command word in the bridge). |
| Voltra | [c8baef5](https://github.com/amage-si/voltra/commit/c8baef5) | `VK_KHR_incremental_present`: a partial frame's present names its rectangles. |
| Voltra | [314a747](https://github.com/amage-si/voltra/commit/314a747) | The canvas and the GPU policy record are passed boxed (the frame-width finding above): the grid's `WL_RESW` went 51 → 55 with the canvas, and is 45 now. |
| Voltra, Chromi | [1aed3ae](https://github.com/amage-si/voltra/commit/1aed3ae), [a8dc71f](https://github.com/amage-si/chromi/commit/a8dc71f) | New atlas content is copied inside the frame that needs it (texels after the instances in the frame's buffer, barriers in submission order) instead of `update`, which waited for the device to go idle and then for its copy. |

### Correctness

Every partial frame must equal a whole redraw, and that is checked three
ways. On the CPU (Chromi `tests.bend`, 73 checks), repainting only a frame's
damage over the last picture equals painting the frame whole for hover, a
focus ring, a translucent part moved over others, parts removed and added,
parts reordered and a new size, with a control that differs. On the GPU
(Chromi `gpu_tests.bend`, 27 checks; Voltra `gpu_tests.bend`, 14), frames
redrawn partly on Voltra's canvas and read back equal the CPU reference of
the whole frame in every pixel (400 to 12,000 of 64,000 pixels damaged per
step), including a glyph the atlas had not seen, uploaded inside the frame,
and a mask that did not fit, so the atlas started over inside the frame;
a changed frame stripped of its damage is seen to differ. On the window
(`grim -T`, `magick compare -metric AE`), the demo and the 5000-label grid,
driven through FocusIn, Tab, two activations and resizes to 1100x700,
640x760 and 900x560, equal the previous full-redraw binaries in every
capture (0 differing pixels), except the final demo's last capture, taken
after the machine's user moved the pointer through the window: its log shows
a focus-out, which removed the button's focus ring (153 pixels); that
step, a whole frame, matched with an earlier build of this work. All other
suites pass unchanged.

### Partial present: what the compositor gets

A partial frame redraws its regions on the canvas and copies the whole
canvas into the swapchain image, so the picture is always complete; with
`VK_KHR_incremental_present` the present also names the regions. To see
whether that reaches the compositor, [tools/damage.c](tools/damage.c) asks
the X server's DAMAGE extension for the raw damage of the test window
(an observer: no input, no focus change) while the 1000-label grid gets Tab
and two activations
([results/damage/](results/damage/)):

| Present | Damage per update (after the first frame) | Over 5 updates |
| --- | --- | --- |
| Without the extension | the whole window, 900x560 = 504,000 pixels | 2,520,000 pixels |
| With `VK_KHR_incremental_present` | the button (78x44) and, on activations, the counter (87x16): 3,432 to 4,824 pixels | 19,944 pixels |

So on this NVIDIA driver and XWayland the regions pass through: the X
server, and so the compositor, gets about a hundredth of the window per
update. Eco's own work is the same either way (the present call carries a
few rectangles); the gain is the compositor's. The extension is on wherever
the device offers it.

### Results after partial redraw

Same scenes, method, fairness rules and machine as above, Eco only (GPUI's
columns are the earlier sessions). Medians, ranges across sessions in
parentheses; latencies pool every update (median / p90). Columns, each
built on the one before: *text cache + first partial redraw* is the
previous section's Eco; *finished partial redraw* adds incremental present,
the boxed GPU record and the demo's status-only relayout (Voltra c8baef5,
Chromi 95d6274); *+ atlas uploads in the frame* also records atlas uploads
inside the frame (Voltra 1aed3ae, Chromi a8dc71f) and has Runika 131874b
(faster font load): it is the final build. Revisions: [results/versions-partial.txt](results/versions-partial.txt).
Every binary ran once before its sessions, so the driver's shader cache was
warm: one session that was a new binary's first run held about 40 MiB more
resident memory and started about 100 ms later, consistent with the driver
compiling the pipeline then (that session is `early-1` of the demo).

#### Demo scene (X11/XWayland, FIFO, 900x560)

| Metric | Eco before (Runika c2b4af9) | Eco, text cache + first partial redraw | Eco, finished partial redraw + text cache | Eco, + atlas uploads in the frame | GPUI |
| --- | --- | --- | --- | --- | --- |
| Sessions | 6 | 3 | 3 | 3 | 3 |
| Startup to first presented frame, ms | 537 (524–616) | 526 (478–552) | 517 (492–610) | 493 (477–530) | 481 (429–488) |
| Key-down → presented, ms (median / p90) | 1.9 / 2.2 | 0.7 / 0.8 | 0.7 / 0.8 | 0.6 / 0.8 | 5.0 / 8.4 |
| Key-up, activation → presented, ms (median / p90) | 7.3 / 9.2 | 0.9 / 2.9 | 0.8 / 2.2 | 0.8 / 1.0 | 5.3 / 8.5 |
| CPU per update, all threads, ms | 6.07 (5.85–6.42) | 2.36 (2.24–2.37) | 2.29 (2.14–2.38) | 2.24 (1.96–2.25) | 3.99 (3.93–4.01) |
| CPU per update minus idle rate, ms | 5.41 (5.09–5.56) | 1.60 (1.50–1.63) | 1.51 (1.50–1.59) | 1.41 (1.30–1.51) | 1.75 (1.68–1.91) |
| CPU per update, main thread, ms | 4.62 (4.43–4.85) | 0.80 (0.77–0.85) | 0.79 (0.77–0.80) | 0.74 (0.70–0.76) | 2.58 (2.56–2.63) |
| Idle 10 s: frames presented | 0 | 0 | 0 | 0 | 0 |
| Idle 10 s: CPU, ms | 22.1 (19.9–27.5) | 23.3 (23.0–24.3) | 24.6 (20.3–24.8) | 23.0 (20.8–26.6) | 70.8 (63.9–73.8) |
| Idle 10 s: main-thread wakeups | 0 | 0 | 0 | 0 | 1208 (1204–1209) |
| Idle 10 s: wakeups, all threads | 1145 (1142–1146) | 1143 (1140–1145) | 1141 (1139–1144) | 1143 (1139–1146) | 2350 (2347–2353) |
| RSS after idle / peak, MiB | 104 / 104 | 97 / 97 | 96 / 97 | 91 / 92 | 144 / 145 |
| Resize → presented at the new size, ms (median step) | 13.5 (11.9–18.4) | 8.7 (8.0–11.5) | 7.5 (7.2–9.7) | 9.4 (7.1–9.7) | 11.7 (11.7–19.0) |

#### Text grid (X11/XWayland)

| N | Build | Sessions | Startup, ms | Key-down → presented, ms (median / p90) | Activation → presented, ms (median / p90) | CPU per update, all threads / main, ms | Idle CPU 10 s, ms | Idle main-thread wakeups | RSS, MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 200 | Eco before | 6 | 320 (299–360) | 1.9 / 2.1 | 2.2 / 3.8 | 3.39 (3.25–3.64) / 2.01 (1.98–2.09) | 22 (20–25) | 0 | 99 |
| 200 | Eco, text cache + first partial redraw | 3 | 310 (306–339) | 0.5 / 0.6 | 0.6 / 1.8 | 2.04 (1.73–2.04) / 0.56 (0.55–0.58) | 22 (22–22) | 0 | 93 |
| 200 | Eco, finished partial redraw | 3 | 295 (265–304) | 0.5 / 0.6 | 0.6 / 1.9 | 2.08 (2.05–2.08) / 0.60 (0.59–0.60) | 23 (23–24) | 0 | 83 |
| 200 | Eco, + atlas uploads in the frame | 3 | 283 (275–431) | 0.5 / 0.6 | 0.6 / 0.8 | 1.98 (1.96–2.15) / 0.56 (0.55–0.59) | 23 (22–25) | 0 | 87 |
| 200 | GPUI | 3 | 444 (409–500) | 6.1 / 9.7 | 6.2 / 9.1 | 4.92 (4.78–4.96) / 3.53 (3.53–3.57) | 66 (64–75) | 1208 (1207–1222) | 146 |
| 1000 | Eco before | 6 | 332 (297–378) | 6.9 / 8.6 | 7.2 / 9.8 | 8.23 (7.83–10.89) / 6.84 (6.53–9.08) | 21 (18–28) | 0 | 101 |
| 1000 | Eco, text cache + first partial redraw | 3 | 271 (261–313) | 0.5 / 0.6 | 0.6 / 2.7 | 2.00 (1.99–2.07) / 0.60 (0.57–0.61) | 23 (22–24) | 0 | 95 |
| 1000 | Eco, finished partial redraw | 2 | 306 (303–308) | 0.6 / 0.6 | 0.6 / 1.8 | 2.10 (2.08–2.11) / 0.61 (0.61–0.62) | 23 (21–24) | 0 | 90 |
| 1000 | Eco, + atlas uploads in the frame | 3 | 274 (270–322) | 0.5 / 0.6 | 0.6 / 0.8 | 2.07 (1.94–2.19) / 0.57 (0.57–0.59) | 23 (22–24) | 0 | 91 |
| 1000 | GPUI | 2 | 490 (442–538) | 11.0 / 14.7 | 11.5 / 14.5 | 10.27 (10.04–10.51) / 8.85 (8.51–9.19) | 72 (67–78) | 1212 (1209–1214) | 160 |
| 5000 | Eco before | 5 | 483 (470–541) | 32.7 / 35.0 | 32.9 / 35.4 | 32.50 (32.24–33.88) / 31.20 (30.64–32.50) | 21 (20–23) | 0 | 117 |
| 5000 | Eco, text cache + first partial redraw | 3 | 319 (313–327) | 0.5 / 0.6 | 0.6 / 1.7 | 1.94 (1.86–2.05) / 0.58 (0.56–0.60) | 21 (21–22) | 0 | 97 |
| 5000 | Eco, finished partial redraw | 3 | 292 (281–311) | 0.5 / 0.6 | 0.6 / 1.8 | 2.03 (1.90–2.09) / 0.60 (0.58–0.61) | 23 (22–26) | 0 | 87 |
| 5000 | Eco, + atlas uploads in the frame | 3 | 282 (270–324) | 0.5 / 0.6 | 0.6 / 0.8 | 1.87 (1.81–2.13) / 0.55 (0.55–0.58) | 20 (19–25) | 0 | 93 |
| 5000 | GPUI | 2 | 521 (479–562) | 34.9 / 37.0 | 33.2 / 37.4 | 33.97 (33.85–34.10) / 32.50 (32.48–32.52) | 79 (75–83) | 1210 (1206–1214) | 215 |

Reading the tables:

- **Grid 5000:** an activation is presented 0.6 ms after the key (p90 0.8)
  against 32.9 ms before and GPUI's 33.2; the main thread spends 0.55 ms
  per update (31.2 before, GPUI 32.5). The frame draws the button and the
  counter (21 quads) instead of about 20,000. The first frame records the
  1,300 labels the window shows (5,226 quads); the 3,700 below it are not
  painted at all, so startup fell from 483 to 282 ms and resident memory
  from 117 to 93 MiB. Grids of 200 and 1000 labels cost the
  same as 5000: the update no longer depends on the content that did not
  change.
- **Demo:** activation 0.8 ms, p90 1.0 (GPUI 5.3 / 8.5); key-down 0.6 ms
  (GPUI 5.0). The p90 fell from 2.2 to 1.0 ms with the atlas uploads inside
  the frame: Voltra's `update` waited for the device to go idle and then
  for its own copy in every frame that showed a glyph for the first time
  (the status line's digits), 1–4 ms in those frames by the program's log
  (the previous section's observation).
- **Idle:** unchanged, 0 frames and 0 main-thread wakeups in 10 s.
- **Resize** (the demo's window resized by the compositor, each step drawn
  whole): 9.4 ms median step (7.1–9.7 across sessions) against 13.5 before
  and GPUI's 11.7; the earlier columns' 8.7 and 7.5 are within the same
  spread.
- The grid at 1000 labels has two sessions in the *finished partial
  redraw* column: its third slot was discarded six times for pointer input
  from the machine's user (`discarded-3-*`) and the batch gave up; the
  last column has three.

Sessions: three per configuration in `results/eco-*-x11-partial/` and
`results/eco-*-x11-retained/`; `loaded-*` and `discarded-*` were rerun as above,
and `early-*` are exploratory sessions of earlier builds of the same
configurations, not used.

Frame width (`WL_RESW`, see the finding above): the canvas made Voltra's
GPU record 4 words wider (the grid's widest record went 51 → 55 words);
boxing it brought the grid to 45. The demo's widest record is its model
(104 words), which this work did not change.

### What the profile shows now

`tools/profile.py`, 10 activations of the final binaries, all threads
(`perf`, user and kernel samples):

| | CPU per activation (key-down + key-up) | Eco's code | NVIDIA driver (both threads) | Kernel | libc |
| --- | --- | --- | --- | --- | --- |
| Grid 5000 | 5.8 ms | 41% | 24% | 22% | 9% |
| Demo | 6.5 ms | 48% | 26% | 11% | 10% |

Presenting is now most of an update: the driver's own threads, the kernel
(X11 and present system calls) and libc together are over half of the
samples. Inside Eco's share the largest items are rasterizing glyphs the
first time they show (Dithra, 7% of the grid's samples: the counter's
digits), the runtime's memory release (`term_drop`, `span_fade`) and
closure calls, recording and comparing the demo's parts every frame
(`F.part`, 3%), and building and validating Voltra's command words every
frame (about 3%).

## After the fast decoders

**Status (2026-10-09):** a startup baseline after Ocula's PNG decoder got
~20x faster (kitty.png 49 → ~2 ms, Ocula up to
[e4555c2](https://github.com/amage-si/ocula/commit/e4555c2)) and Dithra's
glyph rasterizer ~16x faster (70.5 → 4.35 µs per 16 px glyph,
[6a45456](https://github.com/amage-si/dithra/commit/6a45456)). This answers
pending item 5 below ("profile startup"). No other code changed. Revisions are in
[results/versions-fast0.txt](results/versions-fast0.txt); binaries
`build/bench/eco-fast0` and `grid-fast0` (`eco build demo grid`, dev -O3),
configurations `eco-demo-x11-fast0` and `eco-grid5000-x11-fast0`.

### Sessions and how far to trust them

The machine was not quiet. Two unrelated `python3` processes kept one core
busy each for the whole morning, so other processes used 310–690% CPU in
every session. `session.py`'s quiet wait (150%) could never be met, so these
sessions ran with `--quiet-pct 5000`. The machine's user also moved the
pointer over every test window during the update phase. **Only startup is
reported:** in every session the first frame was presented before any
foreign input arrived (the program's log shows `redraw 1` before
`moved`/`focus-in`/`enter`). The update, idle and resize metrics of these
sessions are not used. To measure under the same load, the previous final
demo (`eco-retained`, Ocula and Dithra before the rewrites; 493 ms in a quiet
session) ran interleaved with the new one. The session directories are
`pointer-*` in `results/eco-demo-x11-fast0/`,
`results/eco-grid5000-x11-fast0/` and `results/eco-demo-x11-retained/pointer-fast0-*`.
`loaded-1-*` is a first session that waited out the quiet limit (startup
393 ms, others at 444–689%).

| Startup, ms (launch → first presented frame) | Session 1 | Session 2 | Assets (program log) | Window + GPU (program log) |
| --- | --- | --- | --- | --- |
| Demo, `eco-fast0` | 300 | 285 | 20, 13 | 274, 267 |
| Demo, `eco-retained` (previous final; same load, interleaved) | 540 | 548 | 242, 267 | 290, 276 |
| Grid 5000, `grid-fast0` | 302 | 291 | 27, 30 | 268, 256 |

- **The demo now starts in ~290 ms, against ~545 ms for the previous build under the same load**,
  and 493–526 ms in earlier quiet sessions. GPUI's 481 ms (429–488, quiet sessions of
  2026-10-06; not rerun) is now ~190 ms slower than Eco. The whole gain is the asset phase.
  Font, PNG, SVG, text and layout took 13–20 ms, against 242–267 ms.
- Grid 5000 is unchanged at 291–302 ms (282 before). It decodes no PNG, and its
  28 glyphs were already cheap.
- Startup is now Ankra's window plus Voltra's Vulkan setup: 256–290 ms of
  the ~290 ms, in every build and both programs.

### Where startup goes now (profile)

`tools/profile.py --startup` (perf at 4000 Hz, all threads, from exec to
exit). Each run was preceded by one run of the same binary, so the driver's
shader cache was warm. Samples are binned by time since exec. Reports are in
`results/profile-startup-fast0/`.

| Phase (demo, warm) | Wall | CPU samples (≈ ms) | Where |
| --- | --- | --- | --- |
| 0–40 ms: runtime start, assets | ~40 ms | 174 (≈ 44 ms over threads) | Eco 76 samples (≈ 19 ms), kernel 51 (page faults, file read), driver loading 20 |
| 40–300 ms: window and Vulkan setup | ~260 ms | 197 (≈ 49 ms) | NVIDIA libraries 84, kernel 53, libc 43: the CPU is idle about 80% of this phase |
| 300–320 ms: first frame | ~20 ms | 49 | Eco 19 (scene, atlas, quads), driver 15 |

Inside the asset phase's Eco samples, Runika (font tree, `glyf` outlines)
accounts for 31, the runtime's memory release, allocation and closures for 25, Ocula
(inflate, rows) for 11, and Chromi's pixel list checks (`data_valid`, list
appends) for ~5 (≈ 1–2 ms). Dithra's rasterizer does not show (93 glyphs × 4.35 µs ≈
0.4 ms). The cold first run of a new binary spent another ~50 ms in
`libnvidia-gpucomp` compiling the pipeline (25% of its samples). The grid's
first warm run looked the same: Eco 109 samples in the first 40 ms (the
5000 labels), then the same mostly idle window/Vulkan phase.

What this means for the next steps:

- The Bend side of startup is now ~20 ms of ~290. Passing Ocula's pixels to
  Chromi as an array instead of a list could save at most the ~1–2 ms of
  list checks. Rasterizing missing glyphs in parallel could save at most
  part of ~0.4 ms of rasterizing plus the outline parsing. Neither is worth doing for
  startup. Their value would be structural (the pixel path) or a first
  experience with parallel calls.
- The ~260 ms of window and Vulkan setup is where startup is now. It is
  mostly waiting, not computing, and it was not broken down further here.
  Candidates, unmeasured: instance and device creation, swapchain creation,
  the window's map round trip through the compositor, pipeline creation
  against the cache. Each could be timed by printing timestamps around
  `A.open`, `Gpu.open` and Voltra's setup steps. Ankra's window and Voltra's
  device could also be opened while the assets load, but the assets now
  take ~20 ms, so this would save little.

## After the store

Voltra 45ee539 writes quads and region texels straight into `Array<U32>`
(no per-quad word lists); Voltra 4b9b257 adds the store, a vertex buffer
of quads kept on the GPU between frames, drawn through `C.Spans` runs;
Chromi af74189 writes each part's quads into the store once and draws
kept parts from there, instead of copying their cached word lists into
every frame. Configurations `eco-*-x11-lists` (Voltra 50c0e05, Chromi
b1a03b0) and `eco-*-x11-store`, 3 sessions each, interleaved; sessions with
foreign input or a loaded machine were rerun.

| Config | CPU per update, all threads, ms | Main thread, ms | Key-down -> presented, ms (median) |
| --- | --- | --- | --- |
| demo, lists | 1.99, 2.02 (3.67 with others at 173%) | 0.66, 0.65 (0.76) | 0.60, 0.60, 0.61 |
| demo, store | 2.00, 2.03 (2.87 with others at 377%) | 0.64, 0.67 (0.79) | 0.61, 0.62, 0.66 |
| grid 5000, lists | 1.89, 1.95, 1.91 | 0.536, 0.529, 0.536 | 0.51, 0.53, 0.52 |
| grid 5000, store | 1.90, 1.89, 1.90 | 0.523, 0.508, 0.513 | 0.50, 0.50, 0.52 |

No gain the sessions can tell apart in the demo; about 20 µs (3-4%) of
main-thread CPU per update in the grid. The reason is in the logs: these
updates redraw only parts that do not meet the large ones (the grid's
partial frames draw 9-22 quads; the 5000 labels are one kept part outside
the damage), so the per-frame copy the store removes was already small
there. The store pays where a large kept part meets the damage (a caret
blinking over a long text) or a whole frame redraws kept parts. Window
captures of both builds (demo: Tab, Space, Tab, Space; grid 5000) are
pixel-identical.

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
  layout and rebuilding the whole draw list. (After the text cache: main
  thread 0.80 ms; see [After the text cache](#after-the-text-cache).)
- Building Eco is slow: one compilation unit, 85–93 s and up to 5 GiB per
  change.

Highest-leverage improvements, ranked by expected gain (estimates, not
measured):

1. **Text caching:** memoize glyph id and advance per character in
   Syllo/Runika and keep the glyph cache in an array instead of a list
   searched linearly. Expected to bring the demo's activation from about 7
   toward 2 ms and to shorten every startup. *Done: activation 0.9 ms; see
   [After the text cache](#after-the-text-cache).*
2. **Redraw less:** retain the unchanged part of the frame (damage regions)
   and drop draw-list operations outside the window. With 5000 labels the
   ~33 ms per update is the full rebuild. *Done: retained frames, culling,
   damage-only redraws and incremental present; with 5000 labels an
   activation is presented in 0.6 ms (was 32.9); see
   [After partial redraw](#after-partial-redraw).*
3. **Flat font bytes:** an array instead of Runika's byte tree, O(1) per
   byte read. *Done as a word tree (8x faster reads); arrays are affine and
   cannot live in a shared font; see [After the text cache](#after-the-text-cache).*
4. **Incremental Bend builds** (toolchain): the largest cost in a day of
   work, 85–93 s per change against 2–4 s.
5. **Profile startup:** Eco's demo starts 56 ms after GPUI's; PNG decoding
   (Ocula) and SVG rasterization in Bend are the suspects. *Done: after
   Ocula's and Dithra's rewrites the assets take 13–20 ms and the demo starts
   in ~290 ms. What remains is window and Vulkan setup, ~260 ms and mostly
   waiting. See [After the fast decoders](#after-the-fast-decoders).*

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
- Profiles after the Runika fixes for GPUI and of Eco's startup (Eco's
  activations were profiled after the text cache).
- The grids with the partial redraw alone, to split the grids' gains
  between it and the text cache.
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

The configurations after the text cache run binaries named after them:
`build/bench/eco-text` and `build/bench/grid-text` (the commits listed in
[After the text cache](#after-the-text-cache) or later),
`build/bench/eco-redraw` (Chromi c59b59c and Voltra 264d689 with Runika
c2b4af9 and Syllo d360082):

```sh
python3 tools/batch.py eco-demo-x11-text eco-demo-x11-redraw --runs 3 --interleave
python3 tools/batch.py eco-demo-x11-final --runs 3              # build/bench/eco-final: Runika 131874b
python3 tools/batch.py eco-grid200-x11-text eco-grid1000-x11-text eco-grid5000-x11-text --runs 3 --interleave
```

The configurations [after partial redraw](#after-partial-redraw) run
`build/bench/eco-partial` and `grid-partial` (Chromi 95d6274, Voltra
c8baef5) and `build/bench/eco-retained` and `grid-retained` (Chromi a8dc71f,
Voltra 1aed3ae); run each binary once first, so the driver's shader cache is
warm:

```sh
python3 tools/batch.py eco-demo-x11-partial eco-grid200-x11-partial eco-grid1000-x11-partial \
  eco-grid5000-x11-partial --runs 3 --interleave
python3 tools/batch.py eco-demo-x11-retained eco-grid200-x11-retained eco-grid1000-x11-retained \
  eco-grid5000-x11-retained --runs 3 --interleave
cc -O2 -o /tmp/damage tools/damage.c -lX11 -lXdamage   # X damage of a window: damage TITLE SECONDS
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
| [tools/damage.c](tools/damage.c) | The X damage of one window, as rectangles (`cc -O2 -o tools/damage tools/damage.c -lX11 -lXdamage`). |
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
