#!/usr/bin/env bash
set -x

rootdir=$(cd $(dirname $0) && pwd)

diablolog=$1
csvfile=$2
outfile=$3

$rootdir/lib/origin_information.py -l $diablolog > $csvfile
$rootdir/R/reachable.R $csvfile > $outfile
