#!/usr/bin/env python3
"""One benchmark session (benchmark tool; see ../README.md).

  session.py RUNDIR --mode x11|x11-xim|wayland --title TITLE --workdir DIR
             [--update xsend|auto|none] [--resize] [--idle 10] -- COMMAND...

Phases, in order: launch (tools/launch.sh) and first presented frame; the
window moved to (630, 310) on the laptop display; 2 s of settling; idle; update (30 Space key-down/key-up pairs, 300 ms apart,
after a FocusIn and a Tab, sent with XSendEvent to the window only, or
triggered by the program itself with --update auto); resize (a fixed
sequence through hyprctl); close by the window manager's close request.

Raw data only: RUNDIR/session.json holds the machine state before the run,
the window, per-thread CPU and context-switch samples around each phase,
memory and event timestamps; the program's log and the present-log layer's
log sit beside it. tools/analyze.py turns them into metrics.
"""

import argparse
import json
import os
import random
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xinput  # noqa: E402

SIZES = [(1100, 700), (640, 760), (1280, 480), (760, 560), (900, 560)]
PLACE = (630, 310)
ACTIVATIONS = 30
INTERVAL = 0.300
# 300 ms is exactly 36 periods of a 120 Hz frame timer: without jitter every
# event lands at the same phase of a program's frame clock for a whole
# session. Each wait adds a pseudo-random 0..JITTER s (fixed seed, the same
# schedule for every session and program), so event phases are spread.
JITTER = 0.0084
SEED = 2026
TAIL = 1.0


def mono():
    return time.monotonic_ns()


# Process sampling
# ----------------

def threads(pid):
    out = {}
    try:
        tids = os.listdir(f"/proc/{pid}/task")
    except FileNotFoundError:
        return out
    for tid in tids:
        base = f"/proc/{pid}/task/{tid}"
        try:
            name = open(f"{base}/comm").read().strip()
            sched_ns = int(open(f"{base}/schedstat").read().split()[0])
            fields = open(f"{base}/stat").read().rsplit(")", 1)[1].split()
            ticks = int(fields[11]) + int(fields[12])
            vol = inv = 0
            for line in open(f"{base}/status"):
                if line.startswith("voluntary_ctxt_switches"):
                    vol = int(line.split()[1])
                elif line.startswith("nonvoluntary_ctxt_switches"):
                    inv = int(line.split()[1])
            out[tid] = [name, sched_ns, ticks, vol, inv]
        except (FileNotFoundError, ProcessLookupError, IndexError, ValueError):
            pass
    return out


def memory(pid):
    vals = {}
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith(("VmRSS", "VmHWM")):
                k, v = line.split(":")
                vals[k] = int(v.split()[0])
    except FileNotFoundError:
        pass
    return vals


def machine_busy_ticks():
    """Busy CPU time of the whole machine (all cores), in clock ticks."""
    f = open("/proc/stat").readline().split()[1:]
    user, nice, system, idle, iowait, irq, softirq, steal = (int(x) for x in f[:8])
    return user + nice + system + irq + softirq + steal


def pressure(kind):
    """The 'some' line of /proc/pressure/<kind>: avg10 (%) and total (us)."""
    for line in open(f"/proc/pressure/{kind}"):
        w = line.split()
        if w[0] == "some":
            vals = dict(x.split("=") for x in w[1:])
            return float(vals["avg10"]), int(vals["total"])
    return 0.0, 0


def sample(pid):
    return {"t": mono(), "threads": threads(pid), "memory": memory(pid), "machine_ticks": machine_busy_ticks(),
            "loadavg": open("/proc/loadavg").read().split()[:3],
            "io_some_us": pressure("io")[1], "cpu_some_us": pressure("cpu")[1]}


# Machine state
# -------------

def cpu_table():
    out = {}
    for p in os.listdir("/proc"):
        if not p.isdigit():
            continue
        try:
            fields = open(f"/proc/{p}/stat").read().rsplit(")", 1)
            comm = fields[0].split("(", 1)[1]
            rest = fields[1].split()
            out[p] = (comm, int(rest[11]) + int(rest[12]))
        except (FileNotFoundError, ProcessLookupError, IndexError, ValueError):
            pass
    return out


def machine_state(seconds=1.0):
    """Load average and every process using more than 2% of a core."""
    a = cpu_table()
    time.sleep(seconds)
    b = cpu_table()
    hz = os.sysconf("SC_CLK_TCK")
    busy = []
    for pid, (comm, ticks) in b.items():
        if pid in a:
            pct = 100.0 * (ticks - a[pid][1]) / hz / seconds
            if pct > 2.0:
                busy.append({"pid": int(pid), "comm": comm, "cpu_pct": round(pct, 1)})
    busy.sort(key=lambda x: -x["cpu_pct"])
    return {"loadavg": open("/proc/loadavg").read().split()[:3], "busy": busy,
            "total_cpu_pct": round(sum(x["cpu_pct"] for x in busy), 1)}


def wait_quiet(limit_pct, max_wait):
    """Waits until the other processes use less than limit_pct of one core
    and tasks stalled on I/O less than 5% of the last 10 s."""
    start = time.time()
    while True:
        state = machine_state()
        state["io_some_avg10"] = pressure("io")[0]
        state["cpu_some_avg10"] = pressure("cpu")[0]
        state["quiet"] = state["total_cpu_pct"] < limit_pct and state["io_some_avg10"] < 5.0
        state["waited_s"] = round(time.time() - start, 1)
        if state["quiet"] or time.time() - start > max_wait:
            return state
        time.sleep(10)


# Hyprland
# --------

def clients():
    out = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True, text=True).stdout
    return json.loads(out)


def find_window(title, timeout):
    end = time.time() + timeout
    while time.time() < end:
        for c in clients():
            if c["title"] == title:
                return c
        time.sleep(0.05)
    return None


def dispatch(expr):
    t0 = mono()
    r = subprocess.run(["hyprctl", "dispatch", expr], capture_output=True, text=True)
    t1 = mono()
    return t0, t1, r.stdout.strip()


def cursor():
    r = subprocess.run(["hyprctl", "cursorpos"], capture_output=True, text=True)
    return r.stdout.strip()


def pointer_away(max_wait, hold=3.0):
    """Waits until the pointer has been on the external display (above the
    laptop display, y < 0) for `hold` seconds: someone working there is less
    likely to cross the test window on the laptop display. Gives up after
    max_wait seconds; answers the seconds waited."""
    start = time.time()
    since = None
    while time.time() - start < max_wait:
        try:
            y = int(cursor().split(",")[1])
        except (IndexError, ValueError):
            y = 0
        now = time.time()
        if y < 0:
            since = since or now
            if now - since >= hold:
                break
        else:
            since = None
        time.sleep(0.5)
    return round(time.time() - start, 1)


# Logs
# ----

def presents(path):
    out = []
    try:
        for line in open(path):
            w = line.split()
            if w and w[0] == "present":
                out.append((int(w[1]), int(w[2])))
    except FileNotFoundError:
        pass
    return out


def wait_for(pred, timeout, step=0.01):
    end = time.time() + timeout
    while time.time() < end:
        v = pred()
        if v:
            return v
        time.sleep(step)
    return None


def log_has(path, text):
    try:
        return text in open(path).read()
    except FileNotFoundError:
        return False


# The session
# -----------

def interrupted(signum, frame):
    raise KeyboardInterrupt


def main():
    # A stopped session still closes its window (the `finally` below).
    signal.signal(signal.SIGTERM, interrupted)
    ap = argparse.ArgumentParser()
    ap.add_argument("rundir")
    ap.add_argument("--mode", required=True, choices=["x11", "x11-xim", "wayland"])
    ap.add_argument("--title", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--update", default="xsend", choices=["xsend", "auto", "none"])
    ap.add_argument("--resize", action="store_true")
    ap.add_argument("--idle", type=float, default=10.0)
    ap.add_argument("--settle", type=float, default=2.0)
    ap.add_argument("--quiet-pct", type=float, default=150.0)
    argv = sys.argv[1:]
    if "--" not in argv:
        ap.error("the command follows --")
    cut = argv.index("--")
    args = ap.parse_args(argv[:cut])
    cmd = argv[cut + 1:]
    run = os.path.abspath(args.rundir)
    os.makedirs(run, exist_ok=True)
    app_log = os.path.join(run, "app.log")
    present_log = os.path.join(run, "present.log")
    record = {"mode": args.mode, "title": args.title, "workdir": args.workdir, "command": cmd,
              "schedule": {"activations": ACTIVATIONS, "interval_s": INTERVAL, "jitter_s": JITTER, "seed": SEED},
              "update": args.update, "resize": args.resize, "idle_s": args.idle, "settle_s": args.settle,
              "started_wall": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    record["machine_before"] = wait_quiet(args.quiet_pct, 300)
    record["pointer_wait_s"] = pointer_away(120)
    record["cursor_before"] = cursor()

    control = os.path.join(run, "control")
    if args.update == "auto":
        if os.path.exists(control):
            os.unlink(control)
        os.mkfifo(control)
    subprocess.run([os.path.join(HERE, "launch.sh"), run, args.mode, args.workdir] + cmd,
                   check=True, capture_output=True)
    win = None
    pid = None
    try:
        win = find_window(args.title, 120)
        if win is None:
            raise RuntimeError(f"window {args.title!r} not found")
        pid = win["pid"]
        record["window"] = {k: win[k] for k in ("address", "stableId", "pid", "size", "at", "workspace",
                                                "floating", "xwayland")}
        record["exe"] = os.readlink(f"/proc/{pid}/exe")
        first = wait_for(lambda: presents(present_log), 120)
        if not first:
            raise RuntimeError("no frame presented")
        # Both programs ask for the top-left corner of the laptop display,
        # right at its border with the external display above it, where the
        # pointer of someone using the machine crosses. Move the window away
        # from that border (every resize step still fits on the display).
        record["move"] = dispatch(
            f'hl.dsp.window.move({{ x = {PLACE[0]}, y = {PLACE[1]}, window = "address:{win["address"]}" }})')
        settle_until = mono() + int(args.settle * 1e9)
        time.sleep(max(0.0, (settle_until - mono()) / 1e9))
        placed = find_window(args.title, 5)
        record["window_placed"] = {k: placed[k] for k in ("at", "size")} if placed else None

        # Idle
        s0 = sample(pid)
        time.sleep(args.idle)
        s1 = sample(pid)
        record["idle"] = {"s0": s0, "s1": s1}

        # Update
        if args.update == "xsend":
            target = xinput.Target(args.title)
            focus = target.focus_in()
            time.sleep(0.3)
            tab = target.key("Tab", True)
            time.sleep(0.08)
            target.key("Tab", False)
            time.sleep(0.6)
            events = []
            rng = random.Random(SEED)
            u0 = sample(pid)
            for _ in range(ACTIVATIONS):
                events.append(["down", target.key("space", True)])
                time.sleep(INTERVAL + rng.uniform(0, JITTER))
                events.append(["up", target.key("space", False)])
                time.sleep(INTERVAL + rng.uniform(0, JITTER))
            time.sleep(TAIL - INTERVAL)  # the last frame may come late
            u1 = sample(pid)
            target.close()
            record["update"] = {"focus_in": focus, "tab": tab, "events": events, "s0": u0, "s1": u1}
        elif args.update == "auto":
            with open(control, "w") as ctl:
                u0 = sample(pid)
                ctl.write(f"auto {ACTIVATIONS} {int(INTERVAL * 1000)} {JITTER * 1000} {SEED}\n")
                ctl.flush()
                done = wait_for(lambda: log_has(app_log, "auto done"), 120, 0.005)
                time.sleep(TAIL)
                u1 = sample(pid)
            events = []
            for line in open(app_log):
                w = line.split()
                if len(w) == 3 and w[0] == "auto" and w[1] in ("down", "up"):
                    events.append([w[1], int(w[2])])
            record["update"] = {"events": events, "s0": u0, "s1": u1, "completed": bool(done)}

        # Resize
        if args.resize:
            steps = []
            for (w, h) in SIZES:
                r0 = sample(pid)
                t0, t1, out = dispatch(
                    f'hl.dsp.window.resize({{ x = {w}, y = {h}, window = "address:{win["address"]}" }})')
                time.sleep(1.5)
                r1 = sample(pid)
                steps.append({"w": w, "h": h, "t_dispatch": t0, "t_returned": t1, "reply": out,
                              "s0": r0, "s1": r1})
            record["resize_steps"] = steps

        record["memory_end"] = memory(pid)
        record["cursor_after"] = cursor()
    finally:
        if win is not None:
            t0, t1, out = dispatch(f'hl.dsp.window.close({{ window = "address:{win["address"]}" }})')
            record["close"] = {"t_dispatch": t0, "t_returned": t1}
            exited = wait_for(lambda: log_has(app_log, "exit="), 15, 0.05)
            record["close"]["exited"] = bool(exited)
            if not exited and pid and os.path.exists(f"/proc/{pid}"):
                os.kill(pid, 15)
                record["close"]["killed"] = True
        json.dump(record, open(os.path.join(run, "session.json"), "w"), indent=1)
        if os.path.exists(control):
            os.unlink(control)


if __name__ == "__main__":
    main()
