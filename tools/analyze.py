#!/usr/bin/env python3
"""Metrics from benchmark sessions (benchmark tool; see ../README.md).

  analyze.py session RUNDIR          metrics of one session, as JSON
  analyze.py summary RESULTS_DIR     every session under RESULTS_DIR/<config>/<run>/,
                                     medians and ranges per configuration, as JSON

A session directory holds session.json (tools/session.py), app.log (the
program's output after the launcher's `launch_mono_ns` line) and
present.log (the present-log layer). All times are CLOCK_MONOTONIC.
"""

import json
import os
import statistics
import sys

# Pointer and focus changes the benchmark never sends: a session whose log
# shows one was touched by someone and is discarded.
FOREIGN_INPUT = {"move", "press", "release", "enter", "leave", "wheel", "focus-out", "unmapped"}
OTHERS_CPU_LIMIT = 400.0
IO_STALL_LIMIT = 10.0


def read_present_log(path):
    """Presents (each with the extent of the swapchain it presented to: a
    swapchain handle can be reused after its swapchain is destroyed, so the
    extent is that of the latest creation of the handle before the present),
    swapchain creations and acquires."""
    presents, swapchains, acquires = [], [], []
    for line in open(path):
        w = line.split()
        if not w:
            continue
        if w[0] == "present":
            presents.append({"t0": int(w[1]), "t1": int(w[2]), "result": int(w[3]), "swapchain": w[4]})
        elif w[0] == "swapchain":
            ww, hh = w[5].split("x")
            swapchains.append({"t1": int(w[2]), "handle": w[4], "w": int(ww), "h": int(hh), "mode": int(w[7])})
        elif w[0] == "acquire":
            acquires.append({"t0": int(w[1]), "t1": int(w[2]), "result": int(w[3])})
    presents.sort(key=lambda p: p["t0"])
    for p in presents:
        made = [sc for sc in swapchains if sc["handle"] == p["swapchain"] and sc["t1"] <= p["t0"]]
        sc = max(made, key=lambda sc: sc["t1"]) if made else None
        p["w"], p["h"], p["mode"] = (sc["w"], sc["h"], sc["mode"]) if sc else (None, None, None)
    return presents, swapchains, acquires


def cpu_delta(s0, s1, main_tid):
    """CPU ns, ticks and context switches between two samples, per thread."""
    total_ns = total_ticks = total_switches = 0
    main = {"ns": 0, "switches": 0}
    per_thread = []
    for tid, (name, ns, ticks, vol, inv) in s1["threads"].items():
        b = s0["threads"].get(tid, [name, 0, 0, 0, 0])
        d_ns, d_ticks, d_sw = ns - b[1], ticks - b[2], (vol - b[3]) + (inv - b[4])
        total_ns += d_ns
        total_ticks += d_ticks
        total_switches += d_sw
        if tid == main_tid:
            main = {"ns": d_ns, "switches": d_sw}
        per_thread.append({"tid": int(tid), "name": name, "main": tid == main_tid, "cpu_ms": d_ns / 1e6,
                           "switches": d_sw})
    gone = [t for t in s0["threads"] if t not in s1["threads"]]
    seconds = (s1["t"] - s0["t"]) / 1e9
    others = None
    if "machine_ticks" in s0 and "machine_ticks" in s1:
        hz = os.sysconf("SC_CLK_TCK")
        machine_s = (s1["machine_ticks"] - s0["machine_ticks"]) / hz
        others = round(100.0 * (machine_s - total_ns / 1e9) / seconds, 1)
    stall = {}
    for k in ("io", "cpu"):
        key = f"{k}_some_us"
        if key in s0 and key in s1:
            stall[f"{k}_stall_pct"] = round(100.0 * (s1[key] - s0[key]) / (seconds * 1e6), 2)
    return {"cpu_ns": total_ns, "ticks": total_ticks, "switches": total_switches, "main": main,
            "threads": sorted(per_thread, key=lambda t: t["tid"]), "threads_gone": len(gone),
            "seconds": seconds, "others_cpu_pct": others, **stall}


def in_window(presents, a, b):
    return [p for p in presents if a <= p["t0"] < b]


def session(run):
    s = json.load(open(os.path.join(run, "session.json")))
    lines = open(os.path.join(run, "app.log")).read().splitlines()
    presents, swapchains, acquires = read_present_log(os.path.join(run, "present.log"))
    launch = next(int(l.split()[1]) for l in lines if l.startswith("launch_mono_ns"))
    main_tid = str(s["window"]["pid"])
    out = {"run": run, "mode": s["mode"], "title": s["title"], "update_mode": s["update"],
           "window": s["window"], "machine_before": s["machine_before"]}

    # Foreign input anywhere in the session's log.
    foreign = []
    for l in lines:
        if l.startswith("input:"):
            words = set(l[len("input:"):].split())
            hit = sorted(words & FOREIGN_INPUT)
            if hit:
                foreign.append(l)
    out["foreign_input"] = foreign
    out["exit_ok"] = any(l == "exit=0" for l in lines)

    out["startup_ms"] = (presents[0]["t1"] - launch) / 1e6 if presents else None
    out["first_frame_size"] = f'{presents[0]["w"]}x{presents[0]["h"]}' if presents else None
    out["present_mode"] = presents[0]["mode"] if presents else None

    idle = s.get("idle")
    if idle:
        d = cpu_delta(idle["s0"], idle["s1"], main_tid)
        d["frames"] = len(in_window(presents, idle["s0"]["t"], idle["s1"]["t"]))
        d["rss_mib"] = idle["s1"]["memory"].get("VmRSS", 0) / 1024
        out["idle"] = d

    upd = s.get("update")
    if upd and upd.get("events"):
        events = upd["events"]
        end = upd["s1"]["t"]
        frames = in_window(presents, events[0][1], end)
        lat = {"down": [], "up": []}
        missed = extra = 0
        if len(frames) == len(events):
            # Every event produced exactly one frame: pair them in order, so a
            # frame that comes after the next event was sent still counts for
            # its own event.
            pairing = "order"
            for (kind, t), p in zip(events, frames):
                lat[kind].append((p["t1"] - t) / 1e6)
        else:
            # Otherwise the first frame after each event, before the next one.
            pairing = "window"
            for i, (kind, t) in enumerate(events):
                t_next = events[i + 1][1] if i + 1 < len(events) else end
                got = in_window(presents, t, t_next)
                if not got:
                    missed += 1
                    continue
                extra += len(got) - 1
                lat[kind].append((got[0]["t1"] - t) / 1e6)
        late = sum(1 for i, (kind, t) in enumerate(events[:-1])
                   if pairing == "order" and frames[i]["t0"] >= events[i + 1][1])
        d = cpu_delta(upd["s0"], upd["s1"], main_tid)
        n = len(events)
        idle_rate = out["idle"]["cpu_ns"] / out["idle"]["seconds"] if idle else 0.0
        out["update"] = {
            "events": n, "pairing": pairing, "missed": missed, "extra_presents": extra,
            "frames_after_next_event": late,
            "latency_ms": lat,
            "frames": len(in_window(presents, upd["s0"]["t"], upd["s1"]["t"])),
            "cpu_ms_per_update": d["cpu_ns"] / n / 1e6,
            "cpu_ms_per_update_net": (d["cpu_ns"] - idle_rate * d["seconds"]) / n / 1e6,
            "main_cpu_ms_per_update": d["main"]["ns"] / n / 1e6,
            "seconds": d["seconds"], "threads": d["threads"], "others_cpu_pct": d["others_cpu_pct"],
            "io_stall_pct": d.get("io_stall_pct"), "cpu_stall_pct": d.get("cpu_stall_pct"),
        }

    steps = s.get("resize_steps")
    if steps:
        rs = []
        for st in steps:
            want = (st["w"], st["h"])
            got = [p for p in in_window(presents, st["t_dispatch"], st["s1"]["t"])]
            sized = [p for p in got if (p["w"], p["h"]) == want]
            d = cpu_delta(st["s0"], st["s1"], main_tid)
            rs.append({"size": f"{st['w']}x{st['h']}",
                       "latency_ms": (sized[0]["t1"] - st["t_returned"]) / 1e6 if sized else None,
                       "hyprctl_ms": (st["t_returned"] - st["t_dispatch"]) / 1e6,
                       "frames": len(got), "cpu_ms": d["cpu_ns"] / 1e6})
        out["resize"] = rs

    # Load the benchmark did not cause: other processes using more than 4 of
    # the 16 cores, or tasks stalled on I/O more than 10% of a measured phase.
    loaded = []
    for phase in ("idle", "update"):
        p = out.get(phase)
        if not p:
            continue
        if (p.get("others_cpu_pct") or 0) > OTHERS_CPU_LIMIT:
            loaded.append(f"{phase}: other processes {p['others_cpu_pct']}% CPU")
        if (p.get("io_stall_pct") or 0) > IO_STALL_LIMIT:
            loaded.append(f"{phase}: I/O stall {p['io_stall_pct']}%")
    out["loaded"] = loaded

    mem_end = s.get("memory_end", {})
    out["peak_rss_mib"] = mem_end.get("VmHWM", 0) / 1024
    out["end_rss_mib"] = mem_end.get("VmRSS", 0) / 1024
    out["closed"] = s.get("close", {})
    return out


def med_range(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {"median": statistics.median(xs), "min": min(xs), "max": max(xs), "n": len(xs)}


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summary(results):
    configs = {}
    for config in sorted(os.listdir(results)):
        cdir = os.path.join(results, config)
        if not os.path.isdir(cdir) or config.startswith(("_", ".")) or config in ("build", "shots", "profile"):
            continue
        sessions, discarded = [], []
        for r in sorted(os.listdir(cdir)):
            rdir = os.path.join(cdir, r)
            if not os.path.exists(os.path.join(rdir, "session.json")):
                continue
            if not r.isdigit():  # discarded, interrupted or superseded sessions
                if r.startswith("discarded"):
                    discarded.append({"run": rdir})
                continue
            m = session(rdir)
            (discarded if (m["foreign_input"] or m["loaded"]) else sessions).append(m)
        if not sessions:
            continue
        c = {"sessions": len(sessions), "discarded": [d["run"] for d in discarded]}
        c["startup_ms"] = med_range([m["startup_ms"] for m in sessions])
        if all("idle" in m for m in sessions):
            c["idle"] = {k: med_range([m["idle"][k] for m in sessions]) for k in ("frames", "ticks", "switches")}
            c["idle"]["cpu_ms"] = med_range([m["idle"]["cpu_ns"] / 1e6 for m in sessions])
            c["idle"]["main_switches"] = med_range([m["idle"]["main"]["switches"] for m in sessions])
            c["steady_rss_mib"] = med_range([m["idle"]["rss_mib"] for m in sessions])
        c["peak_rss_mib"] = med_range([m["peak_rss_mib"] for m in sessions])
        ups = [m["update"] for m in sessions if "update" in m]
        if ups:
            u = {}
            for kind in ("down", "up"):
                pooled = [x for up in ups for x in up["latency_ms"][kind]]
                u[f"latency_{kind}_ms"] = {"median": statistics.median(pooled) if pooled else None,
                                           "p90": pct(pooled, 0.9),
                                           "min": min(pooled) if pooled else None,
                                           "max": max(pooled) if pooled else None,
                                           "session_medians": [statistics.median(up["latency_ms"][kind])
                                                               for up in ups if up["latency_ms"][kind]]}
            pooled = [x for up in ups for k in ("down", "up") for x in up["latency_ms"][k]]
            u["latency_all_ms"] = {"median": statistics.median(pooled) if pooled else None, "p90": pct(pooled, 0.9)}
            for k in ("cpu_ms_per_update", "cpu_ms_per_update_net", "main_cpu_ms_per_update"):
                u[k] = med_range([up[k] for up in ups])
            u["missed"] = sum(up["missed"] for up in ups)
            u["extra_presents"] = sum(up["extra_presents"] for up in ups)
            u["events"] = sum(up["events"] for up in ups)
            c["update"] = u
        rss = [m["resize"] for m in sessions if "resize" in m]
        if rss:
            c["resize"] = {
                "median_step_latency_ms": med_range([statistics.median([s["latency_ms"] for s in r if s["latency_ms"] is not None]) for r in rss]),
                "max_step_latency_ms": med_range([max(s["latency_ms"] for s in r if s["latency_ms"] is not None) for r in rss]),
                "cpu_ms_total": med_range([sum(s["cpu_ms"] for s in r) for r in rss]),
                "frames_total": med_range([sum(s["frames"] for s in r) for r in rss]),
                "missing_steps": sum(1 for r in rss for s in r if s["latency_ms"] is None),
                "per_step_latency_ms": {s["size"]: med_range([r[i]["latency_ms"] for r in rss])
                                        for i, s in enumerate(rss[0])},
            }
        configs[config] = c
    return configs


def main():
    if sys.argv[1] == "session":
        print(json.dumps(session(sys.argv[2]), indent=1))
    elif sys.argv[1] == "summary":
        print(json.dumps(summary(sys.argv[2]), indent=1))


if __name__ == "__main__":
    main()
