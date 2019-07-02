#!/usr/bin/env python

# ~/repositories/af-metingen/generate-sensitivity.py compare-stripped-smart-atk.log opaquepreds-0 0 opaquepreds-5 5 opaquepreds-20 20 opaquepreds-50 50 opaquepreds-100 100 > /tmp/foo.csv

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
    print("Reading file %s" % logfile, file=sys.stderr)

    # get data
    data = subprocess.check_output(['tail', '-1', logfile]).decode("utf-8")[0:-1]
    real_data = ast.literal_eval(data)

    nr_t = real_data['gt_edge_count'] - real_data['gt_fake_edge_count']
    nr_f = real_data['gt_fake_edge_count']

    # fractions
    print("FPR (GUI),%s,%f,%d" % (xvalue, fraction(real_data['false_positives_gui'], nr_f), nr_f))
    print("FPR (DB),%s,%f,%d" % (xvalue, fraction(real_data['false_positives_api'], nr_f), nr_f))
    print("FNR (GUI),%s,%f,%d" % (xvalue, fraction(real_data['false_negatives_gui'], nr_t), nr_t))
    print("FNR (DB),%s,%f,%d" % (xvalue, fraction(real_data['false_negatives_api'], nr_t), nr_t))

    index += 2
#endfor
