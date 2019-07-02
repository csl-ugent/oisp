#!/usr/bin/env python

# To analyse the vanilla binary:
# ./compare.py -b ~/repositories/framework/projects/metingen/bzip2-vanilla/bzip2 -B ~/repositories/framework/projects/metingen/bzip2-protected/b.out -o initial

# To analyse the rewritten binary:
# ./compare.py -b ~/repositories/framework/projects/metingen/bzip2-protected/b.out -o final
import common

import getopt
import os
import sys

import tools.diablo.Diablo as Diablo
import tools.idapro.IdaPro as IdaPro

# change this line to do other measurements
import measure.fake as Measure

arg_executed = False
do_vanilla = False
ida_logs_basename = ""
diablo_logs_basename = ""

def print_help_exit():
    print("%s\n"\
""
    % (sys.argv[0]))
    sys.exit(1)

def parse_args():
    global do_vanilla
    global ida_logs_basename, diablo_logs_basename, diablo_origin_logs_basename

    try:
        opts, _ = getopt.getopt(sys.argv[1:], "b:B:o:i:es:Sp:d", ["binary=", "rewritten=", "origin=", "idasuffix=", "executed", "suffix", "smart", "prioft=", "db"])
    except getopt.GetoptError as err:
        print("ERROR:", err)
        sys.exit(1)

    arg_binary = ""
    arg_rewritten = ""
    arg_origin = ""
    arg_idasuffix = ""
    suffix = ""
    for opt, arg in opts:
        if opt in ("-b", "--binary"):
            arg_binary = arg
        elif opt in ("-B", "--rewritten"):
            arg_rewritten = arg
        elif opt in ("-o", "--origin"):
            # 'initial' or 'final'
            arg_origin = arg
        elif opt in ("-i", "--idasuffix"):
            arg_idasuffix = "." + arg
        elif opt in ("-e", "--executed"):
            common.executed = True
        elif opt in ("-s", "--suffix"):
            suffix = arg
        elif opt in ("-S", "--smart"):
            common.smart_attacker = True
        elif opt in ("-p", "--prioft"):
            common.prioritize_ft = int(arg)
        elif opt in ("-d", "--db"):
            common.db_attack = True

    if arg_origin == "initial":
        print("doing vanilla!")
        do_vanilla = True

    if arg_rewritten == '':
        arg_rewritten = arg_binary

    binary_name = os.path.dirname(arg_binary) + "/" + os.path.basename(arg_binary)

    ida_logs_basename = binary_name + ".ida" + arg_idasuffix
    diablo_logs_basename = os.path.dirname(arg_rewritten) + "/" + os.path.basename(arg_rewritten)
    diablo_origin_logs_basename = os.path.dirname(arg_rewritten) + "/origin_" + arg_origin
    common.output_basename = binary_name + ".compare" + suffix

parse_args()

D = Diablo.Diablo(do_vanilla)
D.Load(diablo_logs_basename, diablo_origin_logs_basename)

I = IdaPro.IdaPro(do_vanilla)
I.Load(D, ida_logs_basename)

print(Measure.calculate(D, I))
