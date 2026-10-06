#!/usr/bin/env python3
"""Profiles a configuration's updates with perf (benchmark tool).

  profile.py CONFIG OUTDIR [--activations 10] [--startup]

Opens the program as tools/batch.py does, sends FocusIn and Tab, then
records `perf record -g` of the process while it handles N Space
activations (key-down, 300 ms, key-up, 500 ms), and writes perf.data,
report.txt (self time by symbol) and children.txt (inclusive time).
With --startup, records from launch to the first presented frame instead.
"""

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import batch  # noqa: E402
import session  # noqa: E402
import xinput  # noqa: E402


def report(out, extra):
    with open(os.path.join(out, extra[0]), "w") as f:
        subprocess.run(["perf", "report", "-i", os.path.join(out, "perf.data"), "--stdio"] + extra[1:],
                       stdout=f, stderr=subprocess.DEVNULL)


def main():
    config, out = sys.argv[1], os.path.abspath(sys.argv[2])
    n = int(sys.argv[sys.argv.index("--activations") + 1]) if "--activations" in sys.argv else 10
    startup = "--startup" in sys.argv
    c = batch.CONFIGS[config]
    os.makedirs(out, exist_ok=True)
    data = os.path.join(out, "perf.data")
    if startup:
        # perf starts the program itself through the launcher's environment.
        cmd = ["perf", "record", "-F", "4000", "-g", "-o", data, "--"] + c["command"]
        subprocess.run([os.path.join(HERE, "launch.sh"), out, c["mode"], c["workdir"]] + cmd, check=True,
                       capture_output=True)
        win = session.find_window(c["title"], 120)
        session.wait_for(lambda: session.presents(os.path.join(out, "present.log")), 120)
        time.sleep(1.0)
        session.dispatch(f'hl.dsp.window.close({{ window = "address:{win["address"]}" }})')
        session.wait_for(lambda: session.log_has(os.path.join(out, "app.log"), "exit="), 30, 0.1)
    else:
        subprocess.run([os.path.join(HERE, "launch.sh"), out, c["mode"], c["workdir"]] + c["command"], check=True,
                       capture_output=True)
        win = session.find_window(c["title"], 120)
        pid = win["pid"]
        session.wait_for(lambda: session.presents(os.path.join(out, "present.log")), 120)
        time.sleep(2.0)
        t = xinput.Target(c["title"])
        t.focus_in()
        time.sleep(0.3)
        t.tap("Tab")
        time.sleep(0.5)
        perf = subprocess.Popen(["perf", "record", "-F", "4000", "-g", "-p", str(pid), "-o", data],
                                stdout=subprocess.DEVNULL, stderr=open(os.path.join(out, "perf.err"), "w"))
        time.sleep(0.5)
        s0 = session.sample(pid)
        for _ in range(n):
            t.key("space", True)
            time.sleep(0.3)
            t.key("space", False)
            time.sleep(0.5)
        s1 = session.sample(pid)
        perf.send_signal(2)
        perf.wait()
        t.close()
        cpu = sum(v[1] for v in s1["threads"].values()) - sum(
            s0["threads"].get(k, [0, 0])[1] for k in s1["threads"])
        with open(os.path.join(out, "cpu.txt"), "w") as f:
            f.write(f"{n} activations: {cpu / 1e6:.1f} ms CPU, {cpu / 1e6 / n:.2f} ms per activation "
                    f"(key-down + key-up)\n")
        session.dispatch(f'hl.dsp.window.close({{ window = "address:{win["address"]}" }})')
        session.wait_for(lambda: session.log_has(os.path.join(out, "app.log"), "exit="), 30, 0.1)
    report(out, ["report.txt", "--no-children", "--sort", "dso,symbol", "-g", "none", "--percent-limit", "0.3"])
    report(out, ["children.txt", "--children", "--sort", "symbol", "-g", "none", "--percent-limit", "2"])
    print(open(os.path.join(out, "cpu.txt")).read() if not startup else "startup profile written")


if __name__ == "__main__":
    main()
