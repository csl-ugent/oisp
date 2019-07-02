#!/usr/bin/env python


import common

import getopt
import os
import sys

import tools.diablo.Diablo as Diablo

diablo_logs_basename = ""
diablo_origin_logs_basename = ""

def print_help_exit():
    print("%s\n"\
""
    % (sys.argv[0]))
    sys.exit(1)

def parse_args():
    global diablo_logs_basename, diablo_origin_logs_basename

    try:
        opts, _ = getopt.getopt(sys.argv[1:], "b:", ["binary="])
    except getopt.GetoptError as err:
        print("ERROR:", err)
        sys.exit(1)

    arg_binary = ""
    for opt, arg in opts:
        if opt in ("-b", "--binary"):
            arg_binary = arg

    binary_name = os.path.dirname(arg_binary) + "/" + os.path.basename(arg_binary)

    diablo_logs_basename = os.path.dirname(binary_name) + "/" + os.path.basename(binary_name)
    diablo_origin_logs_basename = os.path.dirname(binary_name) + "/origin_final"

parse_args()

D = Diablo.Diablo(False)
D.Load(diablo_logs_basename, diablo_origin_logs_basename)

dispatchers = set()
dispatchers_exec_out = {}
for edge_uid, edge in D.EdgeIterator(False):
  print("doing diablo edge %d" % edge_uid)
  goes_to_dispatcher = edge_uid in D._af_dispatchers_incoming_edges
  comes_from_dispatcher = edge_uid in D._af_dispatchers_outgoing_edges

  if not comes_from_dispatcher:
    continue

  dispatcher_ins = edge['branch']
  dispatchers.add(dispatcher_ins)

  # coming from dispatcher
  if D.EdgeIsExecuted(edge_uid):
    if dispatcher_ins not in dispatchers_exec_out:
      dispatchers_exec_out[dispatcher_ins] = set()
    dispatchers_exec_out[dispatcher_ins].add(edge_uid)
  #endif
#endfor

nr_dispatchers = len(dispatchers)

nr_dispatchers_multipath = 0
nr_dispatchers_singlepath = 0
for _, y in dispatchers_exec_out.items():
  if len(y) > 1:
    nr_dispatchers_multipath += 1
  elif len(y) == 1:
    nr_dispatchers_singlepath += 1
  #endif
#endfor

print("MULTIPATH DISPATCHER FRACTION %d/%d: %.3f" % (nr_dispatchers_multipath, nr_dispatchers, nr_dispatchers_multipath/nr_dispatchers*100))
print("SINGLEPATH DISPATCHER FRACTION %d/%d: %.3f" % (nr_dispatchers_singlepath, nr_dispatchers, nr_dispatchers_singlepath/nr_dispatchers*100))
