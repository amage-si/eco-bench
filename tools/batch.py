#!/usr/bin/env python3
"""Runs benchmark sessions for named configurations (benchmark tool).

  batch.py CONFIG [CONFIG...] [--runs 3]

Each session goes to results/<config>/<k>/ (tools/session.py). A session
whose log shows input the benchmark did not send (someone using the
machine moved the pointer over the window, clicked it or took its focus)
is renamed results/<config>/discarded-<k>-<time>/ and run again, at most
three times per slot. Prints one summary line per session.
"""

import json
import os
import shutil
import signal
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
ROOT = os.path.dirname(BENCH)
CHROMI = os.path.join(ROOT, "Chromi")
GPUI = os.path.join(BENCH, "gpui", "target", "release", "gpui-bench")
RESULTS = os.path.join(BENCH, "results")
sys.path.insert(0, HERE)
import analyze  # noqa: E402

ECO_DEMO_TITLE = "AMAGE Eco - Ankra, Voltra, Chromi"


def eco(binary, args, title, **kw):
    return dict(mode="x11", update="xsend", workdir=CHROMI, title=title,
                command=[binary] + args + ["--threads", "2", "--gpu", "off"], **kw)


def gpui(args, title, mode="x11", update="xsend", **kw):
    return dict(mode=mode, update=update, workdir=BENCH, title=title, command=[GPUI] + args, **kw)


CONFIGS = {
    "eco-demo-x11": eco("./build/bench/eco", [], ECO_DEMO_TITLE, resize=True),
    "eco-demo-x11-asfound": eco("./build/bench/eco-asfound", [], ECO_DEMO_TITLE, resize=True),
    "eco-demo-x11-fix1": eco("./build/bench/eco-fix1", [], ECO_DEMO_TITLE, resize=True),
    # After the text cache (Runika 47a95f0 + c651a8d, Syllo 484d2b7, Voltra
    # 8b26312 + 52f51a6, Chromi 182f1ab), on top of the partial redraw
    # (Chromi c59b59c, Voltra 264d689); "redraw" is the partial redraw alone.
    "eco-demo-x11-text": eco("./build/bench/eco-text", [], ECO_DEMO_TITLE, resize=True),
    "eco-demo-x11-redraw": eco("./build/bench/eco-redraw", [], ECO_DEMO_TITLE, resize=True),
    # eco-text plus Runika 131874b (the font's tree built in one pass).
    "eco-demo-x11-final": eco("./build/bench/eco-final", [], ECO_DEMO_TITLE, resize=True),
    "gpui-demo-x11": gpui(["demo"], "GPUI bench - demo", resize=True),
    "gpui-demo-x11-xim": gpui(["demo"], "GPUI bench - demo", mode="x11-xim", resize=True),
    "gpui-demo-x11-auto": gpui(["demo"], "GPUI bench - demo", update="auto", resize=True),
    "gpui-demo-wayland-auto": gpui(["demo"], "GPUI bench - demo", mode="wayland", update="auto", resize=True),
}
for n in (200, 1000, 5000):
    CONFIGS[f"eco-grid{n}-x11"] = eco("./build/bench/grid", [str(n)], f"AMAGE Eco - grid {n}")
    CONFIGS[f"eco-grid{n}-x11-asfound"] = eco("./build/bench/grid-asfound", [str(n)], f"AMAGE Eco - grid {n}")
    CONFIGS[f"eco-grid{n}-x11-fix1"] = eco("./build/bench/grid-fix1", [str(n)], f"AMAGE Eco - grid {n}")
    CONFIGS[f"eco-grid{n}-x11-text"] = eco("./build/bench/grid-text", [str(n)], f"AMAGE Eco - grid {n}")
    CONFIGS[f"gpui-grid{n}-x11"] = gpui(["grid", str(n)], f"GPUI bench - grid {n}")
    CONFIGS[f"gpui-grid{n}-x11-auto"] = gpui(["grid", str(n)], f"GPUI bench - grid {n}", update="auto")
    CONFIGS[f"gpui-grid{n}-wayland-auto"] = gpui(["grid", str(n)], f"GPUI bench - grid {n}", mode="wayland",
                                                 update="auto")


def run_session(config, rundir):
    c = CONFIGS[config]
    cmd = [sys.executable, "-I", os.path.join(HERE, "session.py"), rundir, "--mode", c["mode"],
           "--title", c["title"], "--workdir", c["workdir"], "--update", c["update"]]
    if c.get("resize"):
        cmd.append("--resize")
    cmd += ["--"] + c["command"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)  # the session closes its window first
        p.wait()
        raise
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


def line(m):
    parts = [f"startup {m['startup_ms']:.0f} ms" if m.get("startup_ms") else "startup ?"]
    if "idle" in m:
        i = m["idle"]
        parts.append(f"idle {i['frames']} frames {i['cpu_ns'] / 1e6:.1f} ms cpu main-wakeups {i['main']['switches']}"
                     f" all {i['switches']}")
    if "update" in m:
        u = m["update"]
        med = {k: (statistics.median(v) if v else float("nan")) for k, v in u["latency_ms"].items()}
        parts.append(f"update down {med['down']:.2f} up {med['up']:.2f} ms, cpu/upd {u['cpu_ms_per_update']:.2f}"
                     f" (net {u['cpu_ms_per_update_net']:.2f}) missed {u['missed']} extra {u['extra_presents']}")
    if "resize" in m:
        lat = [r["latency_ms"] for r in m["resize"] if r["latency_ms"] is not None]
        parts.append(f"resize median {statistics.median(lat):.1f} ms" if lat else "resize ?")
    parts.append(f"rss {m['idle']['rss_mib']:.0f}/{m['peak_rss_mib']:.0f} MiB" if "idle" in m else "")
    if "update" in m and m["update"].get("others_cpu_pct") is not None:
        u = m["update"]
        parts.append(f"others {u['others_cpu_pct']:.0f}% io-stall {u.get('io_stall_pct', 0):.1f}%")
    if m["foreign_input"]:
        parts.append(f"FOREIGN INPUT x{len(m['foreign_input'])}")
    if m.get("loaded"):
        parts.append("LOADED: " + "; ".join(m["loaded"]))
    return "; ".join(p for p in parts if p)


# Sessions write their logs to tmpfs and move to results/ when done, so the
# programs' log writes never wait on the disk.
SCRATCH = "/tmp/eco-bench-runs"


def run_slot(config, k):
    cdir = os.path.join(RESULTS, config)
    for attempt in range(6):
        scratch = os.path.join(SCRATCH, f"{config}-{k}-{os.getpid()}")
        if os.path.exists(scratch):
            shutil.rmtree(scratch)
        r = run_session(config, scratch)
        rundir = os.path.join(cdir, str(k))
        shutil.move(scratch, rundir)
        try:
            m = analyze.session(rundir)
        except Exception as e:  # a failed session keeps its files for inspection
            m = None
            err = f"{type(e).__name__}: {e}; session stderr: {r.stderr.strip()[-400:]}"
        if m is not None and not m["foreign_input"] and not m["loaded"] and m.get("startup_ms"):
            print(f"{config} #{k}: {line(m)}", flush=True)
            return
        tag = "failed" if m is None else ("discarded" if m["foreign_input"] else "loaded")
        dest = os.path.join(cdir, f"{tag}-{k}-{time.strftime('%H%M%S')}")
        shutil.move(rundir, dest)
        print(f"{config} #{k}: {tag} ({line(m) if m else err}) -> {os.path.basename(dest)}", flush=True)
    print(f"{config} #{k}: gave up after 6 attempts", flush=True)


def main():
    """batch.py CONFIG... [--runs 3] [--interleave]: with --interleave, run
    session 1 of every configuration, then session 2, and so on, so slow
    changes in the machine's state spread over all configurations."""
    args = sys.argv[1:]
    runs = 3
    if "--runs" in args:
        i = args.index("--runs")
        runs = int(args[i + 1])
        del args[i:i + 2]
    interleave = "--interleave" in args
    args = [a for a in args if a != "--interleave"]
    for config in args:
        if config not in CONFIGS:
            sys.exit(f"unknown config {config}; known: {', '.join(sorted(CONFIGS))}")
    first = {}
    for config in args:
        cdir = os.path.join(RESULTS, config)
        os.makedirs(cdir, exist_ok=True)
        first[config] = len([d for d in os.listdir(cdir) if d.isdigit()]) + 1
    if interleave:
        for j in range(runs):
            for config in args:
                run_slot(config, first[config] + j)
    else:
        for config in args:
            for j in range(runs):
                run_slot(config, first[config] + j)


if __name__ == "__main__":
    main()
