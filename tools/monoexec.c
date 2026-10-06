// monoexec LOG CMD [ARGS...]: appends "launch_mono_ns <CLOCK_MONOTONIC ns>"
// to LOG, then execs CMD, so the timestamp is taken right before the
// benchmarked program starts.
#include <stdio.h>
#include <time.h>
#include <unistd.h>

int main(int argc, char **argv) {
  if (argc < 3) {
    fprintf(stderr, "usage: monoexec LOG CMD [ARGS...]\n");
    return 2;
  }
  FILE *log = fopen(argv[1], "a");
  if (!log) {
    perror(argv[1]);
    return 2;
  }
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  fprintf(log, "launch_mono_ns %llu\n", (unsigned long long)ts.tv_sec * 1000000000ull + (unsigned long long)ts.tv_nsec);
  fclose(log);
  execvp(argv[2], argv + 2);
  perror(argv[2]);
  return 127;
}
