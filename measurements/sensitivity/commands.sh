#!/usr/bin/env bash
# single quotes are important (don't expand *)
# $0 '/*/b.out'
b_out=$1
suffix=$2

# common
rootdir=$(cd $(dirname $0) && pwd)

echo $rootdir/chart_sensitivity.py --input $(find $b_out.compare${suffix}-mean-statistics.csv) --title "\"Fraction drawn fake edges\""
echo $rootdir/chart_sensitivity.py --input $(find $b_out.compare${suffix}-smart-mean-statistics.csv) --title "\"Fraction drawn fake edges (smart attacker)\""
echo $rootdir/chart_sensitivity.py --input $(find $b_out.compare${suffix}-mean-statistics.csv) --title "\"Fraction drawn interlibrary edges\"" --column 9
echo $rootdir/chart_sensitivity.py --input $(find $b_out.compare${suffix}-smart-mean-statistics.csv) --title "\"Fraction drawn interlibrary edges (smart attacker)\"" --column 9
