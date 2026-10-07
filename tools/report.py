#!/usr/bin/env python3
"""The published result tables, from results/ (benchmark tool).

  report.py [RESULTS_DIR]     markdown tables on stdout; results/report.json beside

Which sessions count (see README, "Sessions used"):
- `<n>`, `prelim-<n>`: sessions of the main comparison (300 ms + 0..8.4 ms
  jitter between events);
- `nojitter-<n>` (Eco only): the same Eco binaries with exactly 300 ms
  between events; Eco draws as soon as an event arrives, so its results do
  not depend on the phase of a frame clock (compare the two sets);
- never: `lockstep-*` (GPUI with exactly 300 ms: phase-locked to its 120 Hz
  timer), `discarded-*`, `loaded-*`, `interrupted-*`, `failed-*`,
  `spacing150-*` (first trial with 150 ms between events);
- a session with input the benchmark did not send, or under load: other
  processes above 4 cores or I/O stalls above 10% during idle or update
  (sessions recorded before that was measured: 1-minute load average above
  6 when the session started).
"""

import glob
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze  # noqa: E402

START_LOAD_LIMIT = 6.0


def usable(rdir, m):
    if m["foreign_input"] or m.get("loaded"):
        return False
    s = json.load(open(os.path.join(rdir, "session.json")))
    measured = "machine_ticks" in s.get("idle", {}).get("s0", {})
    if not measured and float(s["machine_before"]["loadavg"][0]) > START_LOAD_LIMIT:
        return False
    return True


def sessions(results, config, patterns):
    out = []
    for pat in patterns:
        for rdir in sorted(glob.glob(os.path.join(results, config, pat))):
            name = os.path.basename(rdir)
            if pat == "[0-9]*" and not name.isdigit():
                continue
            if not os.path.exists(os.path.join(rdir, "session.json")):
                continue
            m = analyze.session(rdir)
            if usable(rdir, m):
                m["dir"] = os.path.relpath(rdir, results)
                out.append(m)
    return out


def med(xs):
    xs = [x for x in xs if x is not None]
    return {"median": statistics.median(xs), "min": min(xs), "max": max(xs)} if xs else None


def metrics(ms):
    def pooled(kind):
        return [x for m in ms for x in m["update"]["latency_ms"][kind]]
    r = {"sessions": [m["dir"] for m in ms],
         "startup_ms": med([m["startup_ms"] for m in ms]),
         "cpu_ms_per_update": med([m["update"]["cpu_ms_per_update"] for m in ms]),
         "cpu_ms_per_update_net": med([m["update"]["cpu_ms_per_update_net"] for m in ms]),
         "main_cpu_ms_per_update": med([m["update"]["main_cpu_ms_per_update"] for m in ms]),
         "idle_frames": med([m["idle"]["frames"] for m in ms]),
         "idle_cpu_ms": med([m["idle"]["cpu_ns"] / 1e6 for m in ms]),
         "idle_main_wakeups": med([m["idle"]["main"]["switches"] for m in ms]),
         "idle_wakeups": med([m["idle"]["switches"] for m in ms]),
         "rss_mib": med([m["idle"]["rss_mib"] for m in ms]),
         "peak_rss_mib": med([m["peak_rss_mib"] for m in ms]),
         "missed": sum(m["update"]["missed"] for m in ms),
         "extra": sum(m["update"]["extra_presents"] for m in ms)}
    for kind in ("down", "up"):
        xs = pooled(kind)
        r[f"latency_{kind}_ms"] = {"median": statistics.median(xs), "p90": analyze.pct(xs, 0.9), "n": len(xs)}
    rs = [m for m in ms if "resize" in m]
    if rs:
        r["resize_ms"] = med([statistics.median([s["latency_ms"] for s in m["resize"] if s["latency_ms"]])
                              for m in rs])
    return r


def f(x, d=1, unit=""):
    if not x:
        return "–"
    v = f"{x['median']:.{d}f}{unit}"
    return v if x["min"] == x["max"] else f"{v} ({x['min']:.{d}f}–{x['max']:.{d}f})"


def lat(r, kind):
    x = r[f"latency_{kind}_ms"]
    return f"{x['median']:.1f} / {x['p90']:.1f}"


def main():
    results = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "results")
    main_sets = {"eco": ["[0-9]*", "prelim-*", "nojitter-*"], "gpui": ["[0-9]*", "prelim-*"]}
    report = {}
    for scene in ("demo", "grid200", "grid1000", "grid5000"):
        for tk in ("eco", "gpui"):
            c = f"{tk}-{scene}-x11"
            ms = sessions(results, c, main_sets[tk])
            if ms:
                report[c] = metrics(ms)
    for c in ("eco-demo-x11-asfound", "eco-demo-x11-fix1", "eco-grid200-x11-asfound", "eco-grid200-x11-fix1",
              "eco-grid1000-x11-asfound", "eco-grid1000-x11-fix1", "eco-grid5000-x11-asfound",
              "eco-grid5000-x11-fix1", "eco-demo-x11-redraw", "eco-demo-x11-text", "eco-demo-x11-final",
              "eco-grid200-x11-text", "eco-grid1000-x11-text", "eco-grid5000-x11-text"):
        ms = sessions(results, c, ["[0-9]*"])
        if ms:
            report[c] = metrics(ms)
    json.dump(report, open(os.path.join(results, "report.json"), "w"), indent=1)

    e, g = report["eco-demo-x11"], report["gpui-demo-x11"]
    rows = [
        ("Sessions", lambda r: str(len(r["sessions"]))),
        ("Startup to first presented frame, ms", lambda r: f(r["startup_ms"], 0)),
        ("Key-down → presented, ms (median / p90)", lambda r: lat(r, "down")),
        ("Key-up, activation → presented, ms (median / p90)", lambda r: lat(r, "up")),
        ("CPU per update, all threads, ms", lambda r: f(r["cpu_ms_per_update"], 2)),
        ("CPU per update minus idle rate, ms", lambda r: f(r["cpu_ms_per_update_net"], 2)),
        ("CPU per update, main thread, ms", lambda r: f(r["main_cpu_ms_per_update"], 2)),
        ("Idle 10 s: frames presented", lambda r: f(r["idle_frames"], 0)),
        ("Idle 10 s: CPU, ms", lambda r: f(r["idle_cpu_ms"], 1)),
        ("Idle 10 s: main-thread wakeups", lambda r: f(r["idle_main_wakeups"], 0)),
        ("Idle 10 s: wakeups, all threads", lambda r: f(r["idle_wakeups"], 0)),
        ("RSS after idle / peak, MiB", lambda r: f"{r['rss_mib']['median']:.0f} / {r['peak_rss_mib']['median']:.0f}"),
        ("Resize → presented at the new size, ms (median step)", lambda r: f(r.get("resize_ms"), 1)),
    ]
    print("### Demo scene (X11/XWayland, FIFO, 900x560)\n")
    print("| Metric | AMAGE Eco | GPUI |\n| --- | --- | --- |")
    for name, fn in rows:
        print(f"| {name} | {fn(e)} | {fn(g)} |")
    print("\n### Text grid (X11/XWayland)\n")
    print("| N | Toolkit | Sessions | Startup, ms | Key-down / activation → presented, ms (median) | "
          "CPU per update, ms | Idle CPU 10 s, ms | RSS, MiB |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for n in (200, 1000, 5000):
        for tk, label in (("eco", "Eco"), ("gpui", "GPUI")):
            r = report.get(f"{tk}-grid{n}-x11")
            if not r:
                continue
            print(f"| {n} | {label} | {len(r['sessions'])} | {f(r['startup_ms'], 0)} | "
                  f"{r['latency_down_ms']['median']:.1f} / {r['latency_up_ms']['median']:.1f} | "
                  f"{f(r['cpu_ms_per_update'], 1)} | {f(r['idle_cpu_ms'], 0)} | {r['rss_mib']['median']:.0f} |")
    print("\n### Eco before and after the Runika fixes (medians of 3 sessions)\n")
    print("| Scene | Metric | As found (Runika 97bd37d) | Byte reads O(depth) (0ab65e3) | + cmap stops at the segment "
          "(c2b4af9) |\n| --- | --- | --- | --- | --- |")
    stages = [("asfound", None), ("fix1", None), ("", None)]
    def stage(scene, s):
        return report.get(f"eco-{scene}-x11-{s}" if s else f"eco-{scene}-x11")
    for scene, label in (("demo", "Demo"), ("grid200", "Grid 200"), ("grid1000", "Grid 1000"), ("grid5000", "Grid 5000")):
        rs = [stage(scene, s) for s, _ in stages]
        if not all(rs):
            continue
        print(f"| {label} | Startup, ms | " + " | ".join(f"{r['startup_ms']['median']:.0f}" for r in rs) + " |")
        print(f"| {label} | Activation → presented, ms | " +
              " | ".join(f"{r['latency_up_ms']['median']:.1f}" for r in rs) + " |")
        if scene == "demo":
            print(f"| {label} | CPU per update, ms | " +
                  " | ".join(f"{r['cpu_ms_per_update']['median']:.1f}" for r in rs) + " |")
            print(f"| {label} | Resize → presented, ms | " +
                  " | ".join(f"{r['resize_ms']['median']:.1f}" for r in rs) + " |")
    after(report, rows)


def after(report, rows):
    """The section after the text cache: the demo before, with the partial
    redraw alone, with the text cache on top of it, and GPUI; the grids
    before and after."""
    cols = [("eco-demo-x11", "Eco before (Runika c2b4af9)"), ("eco-demo-x11-redraw", "Eco, partial redraw alone"),
            ("eco-demo-x11-text", "Eco, text cache + partial redraw"), ("gpui-demo-x11", "GPUI")]
    cols = [(c, label) for c, label in cols if c in report]
    if "eco-demo-x11-text" not in report:
        return
    print("\n### After the text cache: demo scene (X11/XWayland, FIFO, 900x560)\n")
    print("| Metric | " + " | ".join(label for c, label in cols) + " |")
    print("| --- |" + " --- |" * len(cols))
    for name, fn in rows:
        print(f"| {name} | " + " | ".join(fn(report[c]) for c, label in cols) + " |")
    r = report.get("eco-demo-x11-final")
    if r:
        print(f"\nWith Runika 131874b (the font's tree built in one pass), {len(r['sessions'])} sessions: startup "
              f"{f(r['startup_ms'], 0)} ms, activation {lat(r, 'up')} ms, key-down {lat(r, 'down')} ms, CPU per "
              f"update {f(r['cpu_ms_per_update'], 2)} ms (main thread {f(r['main_cpu_ms_per_update'], 2)}), RSS "
              f"{r['rss_mib']['median']:.0f} MiB.")
    print("\n### After the text cache: text grid (X11/XWayland)\n")
    print("| N | Build | Sessions | Startup, ms | Key-down → presented, ms (median / p90) | "
          "Activation → presented, ms (median / p90) | CPU per update, all threads / main, ms | "
          "Idle CPU 10 s, ms | RSS, MiB |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for n in (200, 1000, 5000):
        for c, label in ((f"eco-grid{n}-x11", "Eco before"), (f"eco-grid{n}-x11-text", "Eco after"),
                         (f"gpui-grid{n}-x11", "GPUI")):
            r = report.get(c)
            if not r:
                continue
            print(f"| {n} | {label} | {len(r['sessions'])} | {f(r['startup_ms'], 0)} | "
                  f"{lat(r, 'down')} | {lat(r, 'up')} | "
                  f"{f(r['cpu_ms_per_update'], 1)} / {f(r['main_cpu_ms_per_update'], 1)} | "
                  f"{f(r['idle_cpu_ms'], 0)} | {r['rss_mib']['median']:.0f} |")


if __name__ == "__main__":
    main()
