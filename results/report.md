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
