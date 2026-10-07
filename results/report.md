### Demo scene (X11/XWayland, FIFO, 900x560)

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

### Text grid (X11/XWayland)

| N | Toolkit | Sessions | Startup, ms | Key-down / activation → presented, ms (median) | CPU per update, ms | Idle CPU 10 s, ms | RSS, MiB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 200 | Eco | 6 | 320 (299–360) | 1.9 / 2.2 | 3.4 (3.3–3.6) | 22 (20–25) | 99 |
| 200 | GPUI | 3 | 444 (409–500) | 6.1 / 6.2 | 4.9 (4.8–5.0) | 66 (64–75) | 146 |
| 1000 | Eco | 6 | 332 (297–378) | 6.9 / 7.2 | 8.2 (7.8–10.9) | 21 (18–28) | 101 |
| 1000 | GPUI | 2 | 490 (442–538) | 11.0 / 11.5 | 10.3 (10.0–10.5) | 72 (67–78) | 160 |
| 5000 | Eco | 5 | 483 (470–541) | 32.7 / 32.9 | 32.5 (32.2–33.9) | 21 (20–23) | 117 |
| 5000 | GPUI | 2 | 521 (479–562) | 34.9 / 33.2 | 34.0 (33.8–34.1) | 79 (75–83) | 215 |

### Eco before and after the Runika fixes (medians of 3 sessions)

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

### After the text cache: demo scene (X11/XWayland, FIFO, 900x560)

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

With Runika 131874b (the font's tree built in one pass), 2 sessions: startup 528 (509–548) ms, activation 0.8 / 1.9 ms, key-down 0.6 / 0.7 ms, CPU per update 2.21 (2.16–2.26) ms (main thread 0.76 (0.74–0.79)), RSS 93 MiB.

### After the text cache: text grid (X11/XWayland)

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

### After partial redraw: demo scene (X11/XWayland, FIFO, 900x560)

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

### After partial redraw: text grid (X11/XWayland)

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
