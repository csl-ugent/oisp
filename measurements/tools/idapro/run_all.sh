#!/usr/bin/env bash
scriptdir=$(cd $(dirname $0) && pwd)
binary=$1

$scriptdir/run_ida.sh $binary
$scriptdir/run_ida.sh $binary -s -S s

have_hanging=0
nr_hanging=$(egrep "found [0-9]+ hanging instructions" $binary.ida.log | egrep -o "[0-9]+")
if [ $nr_hanging != "0" ]; then
  have_hanging=1
fi

if [ $have_hanging -eq 1 ]; then
  for x in t h ht th; do
    $scriptdir/run.sh $binary -h $x    -S $x
    $scriptdir/run.sh $binary -h $x -s -S s$x

    if [ $x != t ]; then
      $scriptdir/run.sh $binary -h $x    -j -S j$x
      $scriptdir/run.sh $binary -h $x -s -j -S js$x
    fi
  done
fi
