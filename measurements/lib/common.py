#!/usr/bin/env python
import getopt
import importlib
import os
import pathlib
import sys

def import_parents(level=1):
  global __package__
  file = pathlib.Path(__file__).resolve()
  parent, top = file.parent, file.parents[level]

  sys.path.append(str(top))
  try:
    sys.path.remove(str(parent))
  except ValueError: # already removed
     pass

  __package__ = '.'.join(parent.parts[len(top.parts):])
  importlib.import_module(__package__) # won't be needed after that
import_parents(level=1)

# configuration
conf = {
  'filemode': 'w',
  'lineprefix': None,
  'executed': False,
  'covered-executed': False,
}

# for storing data read from e.g., log files
data = {}

def print_help_exit():
  print("%s\n"\
""
  % (sys.argv[0]))
  sys.exit(1)

def parse_args():
  global conf

  try:
    opts, _ = getopt.getopt(sys.argv[1:], "l:f:g:s:aP:xc", ["log=", "filename1=", "filename2=", "selector=", "append", "lineprefix", "executed", "covered-executed"])
  except getopt.GetoptError as err:
    print("ERROR:", err)
    sys.exit(1)

  for opt, arg in opts:
    if opt in ("-l", "--log"):
      conf['diablo-log'] = arg
      conf['diablo-dir'] = os.path.dirname(arg)
    elif opt in ("-f", "--filename1"):
      conf['outfile1'] = arg
    elif opt in ("-g", "--filename2"):
      conf['outfile2'] = arg
    elif opt in ("-s", "--selector"):
      conf['selector'] = arg
    elif opt in ("-a", "--append"):
      conf['filemode'] = 'a+'
    elif opt in ("-P", "--lineprefix"):
      conf['lineprefix'] = arg
    elif opt in ("-x", "--executed"):
      conf['executed'] = True
    elif opt in ("-c", "--covered-executed"):
      conf['covered-executed'] = True

  # Diablo log: factoring
  factoring_log = None
  if os.path.exists(conf['diablo-dir'] + '/b.out.advanced_factoring.log'):
    factoring_log = "/b.out.advanced_factoring.log"
  elif os.path.exists(conf['diablo-dir'] + '/b.out.bbl_factoring.log'):
    factoring_log = "/b.out.bbl_factoring.log"

  if factoring_log is not None:
    conf['factoring-log'] = conf['diablo-dir'] + factoring_log
    conf['factoring-statistics'] = conf['diablo-dir'] + factoring_log + '.statistics'
    conf['factoring-instructions'] = conf['diablo-dir'] + factoring_log + '.instructions'

  # Diablo log: original origin tracking
  conf['initial-archives'] = conf['diablo-dir'] + "/origin_initial.archives"
  conf['initial-objects'] = conf['diablo-dir'] + "/origin_initial.objectfiles"
  conf['initial-functions'] = conf['diablo-dir'] + "/origin_initial.functions"

  # Diablo log: complexity
  conf['initial-global-static-complexity'] = conf['diablo-dir'] + "/origin_initial.stat_complexity_info.non-origin"
  conf['initial-global-dynamic-complexity'] = conf['diablo-dir'] + "/origin_initial.dynamic_complexity_info.non-origin"

def argstring():
  return ' '.join(sys.argv)