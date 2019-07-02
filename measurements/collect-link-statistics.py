#!/usr/bin/env python
import ast
import os
import subprocess
import sys

def percent(a, b):
    if b == 0:
        return 0
    return round(a/b * 100, 0)
#enddef

print("#", ' '.join(sys.argv))

print("# name, total, wrong, wrong %%, correct, correct %%")

benchname=sys.argv[1]
logfilename=sys.argv[2]
for dirname in sys.argv[3:]:
    logfile = os.path.join(dirname, logfilename)

    # get data
    data = subprocess.check_output(['tail', '-1', logfile]).decode("utf-8")[0:-1]
    real_data = ast.literal_eval(data)

    nr_wrong = real_data['tuples_both_hanging'] + real_data['tuples_one_hanging'] + real_data['tuples_both_other']
    nr_correct = real_data['tuples_both_same']
    nr_total = nr_wrong + nr_correct

    print("%s/%s,%d,%d,%d,%d,%d" % (benchname, dirname, nr_total, nr_wrong, percent(nr_wrong, nr_total), nr_correct, percent(nr_correct, nr_total)))
#endfor
