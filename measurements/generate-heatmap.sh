#!/usr/bin/env bash
set -x

rootdir=$(cd $(dirname $0) && pwd)

diablolog=$1
prefix=$2
outfile=$3

$rootdir/lib/heatmap.py -l $diablolog -f $rootdir/data/${prefix}_tf.csv -g $rootdir/data/${prefix}_slice.csv -s archives
echo "heatmap to $outfile.tex"
$rootdir/R/heatmap.R data/${prefix}_slice.csv FALSE > $outfile.tex
echo "heatmap legend to ${outfile}_legend.tex"

tmpfile=$(mktemp)
$rootdir/R/heatmap.R data/${prefix}_slice.csv TRUE > $tmpfile
$rootdir/heatmap-legend.pl $tmpfile > ${outfile}_legend.tex
rm $tmpfile
