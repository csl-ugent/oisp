#!/usr/bin/env python

import ast
import subprocess
import sys
import os

def fraction(a, b):
    if b == 0:
        return 0
    return a/b
#enddef

print("#", ' '.join(sys.argv))

logfilename=sys.argv[1]
index=3
for dirname in sys.argv[2::2]:
    xvalue = sys.argv[index]

    logfile = os.path.join(dirname, logfilename)

    # get data
    data = subprocess.check_output(['tail', '-1', logfile]).decode("utf-8")[0:-1]
    real_data = ast.literal_eval(data)

    nr_p = real_data['tuples_both_hanging'] + real_data['tuples_one_hanging'] + real_data['tuples_both_other'] + real_data['tuples_both_same']

    # fractions
    print("wrong pairs,%s,%f,%d" % (xvalue, fraction((real_data['tuples_both_other']+real_data['tuples_both_hanging']+real_data['tuples_one_hanging']), nr_p), real_data['gt_edge_count']))

    index += 2
#endfor
