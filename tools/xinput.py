#!/usr/bin/env python3
"""Synthetic X11 input sent to one window only (benchmark tool).

Events go with XSendEvent to the window whose WM_NAME matches, without
propagation; nothing is injected globally and the desktop's real keyboard
focus does not change. Based on Auvia's tools/x11_input.py.

As a command:
  xinput.py TITLE KEY          a key press and, 80 ms later, its release
  xinput.py TITLE focus-in     a FocusIn (mode Normal, detail Nonlinear)

As a module, `Target(title)` keeps one connection open and returns the
CLOCK_MONOTONIC time (ns) taken right before each XSendEvent.
"""

import ctypes
import ctypes.util
import sys
import time

x = ctypes.cdll.LoadLibrary(ctypes.util.find_library("X11"))
x.XOpenDisplay.restype = ctypes.c_void_p
x.XOpenDisplay.argtypes = [ctypes.c_char_p]
x.XDefaultRootWindow.restype = ctypes.c_ulong
x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
x.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
                         ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)),
                         ctypes.POINTER(ctypes.c_uint)]
x.XFetchName.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_char_p)]
x.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]
x.XFlush.argtypes = [ctypes.c_void_p]
x.XFree.argtypes = [ctypes.c_void_p]
x.XCloseDisplay.argtypes = [ctypes.c_void_p]
x.XStringToKeysym.restype = ctypes.c_ulong
x.XStringToKeysym.argtypes = [ctypes.c_char_p]
x.XKeysymToKeycode.restype = ctypes.c_ubyte
x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]

KEY_PRESS, KEY_RELEASE, FOCUS_IN = 2, 3, 9
KEY_PRESS_MASK, KEY_RELEASE_MASK, FOCUS_CHANGE_MASK = 1, 2, 1 << 21


class KeyEvent(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong), ("send_event", ctypes.c_int),
                ("display", ctypes.c_void_p), ("window", ctypes.c_ulong), ("root", ctypes.c_ulong),
                ("subwindow", ctypes.c_ulong), ("time", ctypes.c_ulong), ("x", ctypes.c_int), ("y", ctypes.c_int),
                ("x_root", ctypes.c_int), ("y_root", ctypes.c_int), ("state", ctypes.c_uint),
                ("code", ctypes.c_uint), ("same_screen", ctypes.c_int)]


class FocusEvent(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong), ("send_event", ctypes.c_int),
                ("display", ctypes.c_void_p), ("window", ctypes.c_ulong), ("mode", ctypes.c_int),
                ("detail", ctypes.c_int)]


class Event(ctypes.Union):
    _fields_ = [("xkey", KeyEvent), ("xfocus", FocusEvent), ("pad", ctypes.c_long * 24)]


def _windows(dpy, w):
    root = ctypes.c_ulong()
    parent = ctypes.c_ulong()
    kids = ctypes.POINTER(ctypes.c_ulong)()
    n = ctypes.c_uint()
    if not x.XQueryTree(dpy, w, ctypes.byref(root), ctypes.byref(parent), ctypes.byref(kids), ctypes.byref(n)):
        return
    found = [kids[i] for i in range(n.value)]
    if kids:
        x.XFree(kids)
    for k in found:
        yield k
        yield from _windows(dpy, k)


class Target:
    """One X11 window, found by title, on a connection kept open."""

    def __init__(self, title):
        self.dpy = x.XOpenDisplay(None)
        if not self.dpy:
            raise RuntimeError("cannot open the X display")
        self.window = None
        want = title.encode()
        for w in _windows(self.dpy, x.XDefaultRootWindow(self.dpy)):
            name = ctypes.c_char_p()
            hit = x.XFetchName(self.dpy, w, ctypes.byref(name)) and name.value == want
            if name:
                x.XFree(name)
            if hit:
                self.window = w
                break
        if self.window is None:
            x.XCloseDisplay(self.dpy)
            raise LookupError(f"no X11 window titled {title!r}")

    def keycode(self, key):
        return x.XKeysymToKeycode(self.dpy, x.XStringToKeysym(key.encode()))

    def key(self, key, press):
        """Sends a KeyPress or KeyRelease; returns the send time (ns)."""
        ev = Event()
        ev.xkey.type = KEY_PRESS if press else KEY_RELEASE
        ev.xkey.send_event = 1
        ev.xkey.display = self.dpy
        ev.xkey.window = self.window
        ev.xkey.root = x.XDefaultRootWindow(self.dpy)
        ev.xkey.code = self.keycode(key)
        ev.xkey.same_screen = 1
        t = time.monotonic_ns()
        x.XSendEvent(self.dpy, self.window, 0, KEY_PRESS_MASK if press else KEY_RELEASE_MASK, ctypes.byref(ev))
        x.XFlush(self.dpy)
        return t

    def tap(self, key, hold=0.08):
        t = self.key(key, True)
        time.sleep(hold)
        self.key(key, False)
        return t

    def focus_in(self):
        ev = Event()
        ev.xfocus.type = FOCUS_IN
        ev.xfocus.send_event = 1
        ev.xfocus.display = self.dpy
        ev.xfocus.window = self.window
        ev.xfocus.mode = 0      # NotifyNormal
        ev.xfocus.detail = 3    # NotifyNonlinear
        t = time.monotonic_ns()
        x.XSendEvent(self.dpy, self.window, 0, FOCUS_CHANGE_MASK, ctypes.byref(ev))
        x.XFlush(self.dpy)
        return t

    def close(self):
        if self.dpy:
            x.XCloseDisplay(self.dpy)
            self.dpy = None


def main():
    title, what = sys.argv[1], sys.argv[2]
    target = Target(title)
    if what == "focus-in":
        target.focus_in()
    else:
        target.tap(what)
    target.close()
    print("sent", what, "to", hex(target.window))
    return 0


if __name__ == "__main__":
    sys.exit(main())
