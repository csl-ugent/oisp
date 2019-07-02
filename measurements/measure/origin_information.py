#!/usr/bin/env python
import getopt
import os
import re
import sys

import lib.common

diablo_log = None

def parse_args():
  global diablo_log

  try:
    opts, _ = getopt.getopt(sys.argv[1:], "l:", ["log="])
  except getopt.GetoptError as err:
    print("ERROR:", err)
    sys.exit(1)

  for opt, arg in opts:
    if opt in ("-l", "--log"):
      diablo_log = os.path.dirname(arg) + "/" + os.path.basename(arg)

parse_args()

# parse Diablo log with regex
rgx_tracking_origin = re.compile(r'^\s+Tracking origin_([^_]+)_insns_([^:]+):(\d+):(\d+)$')
rgx_total_nr_instructions = re.compile(r'^\s+Done: processed (\d+) instructions$')

# Diablo data
tracking_origin = {}
total_nr_instructions = 0

f = open(diablo_log, 'r')
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

  m = re.search(rgx_total_nr_instructions, line)
  if m is not None:
    total_nr_instructions = int(m.group(1))

    continue

f.close()

print('# %s\n' % common.argstring())

for cat, whats in tracking_origin.items():
  for what, xs in whats.items():
    for x, y in xs.items():
      print("%s,%s,%d,%d,%0.6f" % (cat, what, x, y, y/total_nr_instructions))
