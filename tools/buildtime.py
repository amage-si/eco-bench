#!/usr/bin/env python3
"""Times a build (benchmark tool).

  buildtime.py LOG LABEL -- COMMAND...

Runs COMMAND, samples the resident memory of its whole process tree every
100 ms, and appends one JSON line to LOG: label, command, exit status, wall
seconds, user and system CPU seconds of every descendant that was waited for
(getrusage RUSAGE_CHILDREN), and the peak sampled tree RSS in MiB.
"""

import json
import os
import resource
import subprocess
import sys
import time


def children(pid):
    out = []
    try:
        for tid in os.listdir(f"/proc/{pid}/task"):
            try:
                out += [int(c) for c in open(f"/proc/{pid}/task/{tid}/children").read().split()]
            except FileNotFoundError:
                pass
    except FileNotFoundError:
        pass
    return out


def tree_rss_kib(root):
    total, stack, seen = 0, [root], set()
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        try:
            for line in open(f"/proc/{pid}/status"):
                if line.startswith("VmRSS"):
                    total += int(line.split()[1])
                    break
        except FileNotFoundError:
            continue
        stack += children(pid)
    return total


def main():
    log, label = sys.argv[1], sys.argv[2]
    cmd = sys.argv[sys.argv.index("--") + 1:]
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.monotonic()
    p = subprocess.Popen(cmd)
    peak = 0
    while p.poll() is None:
        peak = max(peak, tree_rss_kib(p.pid))
        time.sleep(0.1)
    wall = time.monotonic() - t0
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    rec = {"label": label, "command": cmd, "exit": p.returncode, "wall_s": round(wall, 2),
           "user_s": round(after.ru_utime - before.ru_utime, 2), "sys_s": round(after.ru_stime - before.ru_stime, 2),
           "peak_tree_rss_mib": round(peak / 1024, 1), "when": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    with open(log, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(json.dumps(rec))
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()
