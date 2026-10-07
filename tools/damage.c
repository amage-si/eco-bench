// Logs the damage the X server reports on one window (benchmark tool).
//
//   damage TITLE SECONDS
//
// Finds the top-level window whose WM_NAME is TITLE, asks the DAMAGE
// extension for its raw damage rectangles, and prints one line per
// rectangle for SECONDS:
//   damage <CLOCK_MONOTONIC ns> <x> <y> <width> <height>
// then a summary line. It only observes: no input is sent and the
// window's focus does not change. On XWayland this is the damage the X
// server forwards to the compositor for the window's buffer, so it shows
// whether a presentation updated the whole window or only a region.
//
// cc -O2 -o tools/damage tools/damage.c -lX11 -lXdamage
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/Xdamage.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long long mono(void) {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return (long long)t.tv_sec * 1000000000LL + t.tv_nsec;
}

static Window find(Display* d, Window w, const char* title) {
  char* name = NULL;
  if (XFetchName(d, w, &name) && name != NULL) {
    int hit = strcmp(name, title) == 0;
    XFree(name);
    if (hit) {
      return w;
    }
  }
  Window root, parent, *kids = NULL;
  unsigned int n = 0;
  if (!XQueryTree(d, w, &root, &parent, &kids, &n)) {
    return 0;
  }
  Window found = 0;
  for (unsigned int i = 0; i < n && found == 0; i += 1) {
    found = find(d, kids[i], title);
  }
  if (kids != NULL) {
    XFree(kids);
  }
  return found;
}

int main(int argc, char** argv) {
  if (argc < 3) {
    fprintf(stderr, "usage: damage TITLE SECONDS\n");
    return 2;
  }
  Display* d = XOpenDisplay(NULL);
  if (d == NULL) {
    fprintf(stderr, "damage: no display\n");
    return 1;
  }
  int events, errors;
  if (!XDamageQueryExtension(d, &events, &errors)) {
    fprintf(stderr, "damage: no DAMAGE extension\n");
    return 1;
  }
  Window w = find(d, DefaultRootWindow(d), argv[1]);
  if (w == 0) {
    fprintf(stderr, "damage: window '%s' not found\n", argv[1]);
    return 1;
  }
  XDamageCreate(d, w, XDamageReportRawRectangles);
  XFlush(d);
  long long end = mono() + (long long)(atof(argv[2]) * 1e9);
  long long n = 0, area = 0, whole = 0;
  XWindowAttributes at;
  XGetWindowAttributes(d, w, &at);
  printf("window %d %d\n", at.width, at.height);
  fflush(stdout);
  struct pollfd p = { ConnectionNumber(d), POLLIN, 0 };
  while (mono() < end) {
    while (XPending(d)) {
      XEvent e;
      XNextEvent(d, &e);
      if (e.type == events + XDamageNotify) {
        XDamageNotifyEvent* de = (XDamageNotifyEvent*)&e;
        printf("damage %lld %d %d %d %d\n", mono(), de->area.x, de->area.y,
          de->area.width, de->area.height);
        n += 1;
        area += (long long)de->area.width * de->area.height;
        whole += de->area.width >= at.width && de->area.height >= at.height;
      }
    }
    fflush(stdout);
    long long left = (end - mono()) / 1000000;
    poll(&p, 1, left > 100 ? 100 : (int)(left > 0 ? left : 0));
  }
  printf("summary %lld rectangles, %lld pixels, %lld whole-window\n", n, area, whole);
  XCloseDisplay(d);
  return 0;
}
