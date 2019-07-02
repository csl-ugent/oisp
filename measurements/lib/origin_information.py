#!/usr/bin/env python
import re
import common

def doit():
  # parse Diablo log with regex
  rgx_tracking_origin = re.compile(r'^\s+Tracking origin_([^_]+)_insns_([^:]+):(\d+):(\d+)$')
  rgx_tracking_origin_total = re.compile(r'^\s+Tracking origin_([^_]+)_insns_reachable:(\d+)$')

  totals = {}

  # Diablo data
  tracking_origin = {}

  f = open(common.conf['diablo-log'], 'r')
  for line in f.readlines():
    line = line.rstrip()

    m = re.search(rgx_tracking_origin, line)
    if m is not None:
      cat = m.group(1)
      what = m.group(2)
      x = int(m.group(3))
      y = int(m.group(4))

      if cat not in tracking_origin:
        tracking_origin[cat] = {}

      if what not in tracking_origin[cat]:
        tracking_origin[cat][what] = {}
      tracking_origin[cat][what][x] = y

      continue

    m = re.search(rgx_tracking_origin_total, line)
    if m is not None:
      cat = m.group(1)
      x = int(m.group(2))
      totals[cat] = x
      continue

  f.close()

  print('# %s' % common.argstring())

  for cat, whats in tracking_origin.items():
    nr_total = totals[cat]
    for what, xs in whats.items():
      for x, y in xs.items():
        print("%s,%s,%d,%d,%0.6f" % (cat, what, x, y, y/nr_total))

if __name__ == "__main__":
  # filename1: Diablo log file
  common.parse_args()
  doit()
