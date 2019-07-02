#!/usr/bin/env bash
t=$1
arg=$2

d=$(cd $(dirname $0) && pwd)

# suffix
s=

if [[ "x$arg" == "x-x" ]]; then
  s="${s}_exec"
fi

file=${HOME}/repositories/af-metingen/data/dispatchers_${t}${s}.csv
rm -f $file

for benchmark in 436.cactusADM 445.gobmk 454.calculix; do for disp in all ib swb disttbl icondjp; do ${d}/dispatchers.py -f ${file} -l /bulk/A/measurements/tests/${benchmark}/sensitivity-train/afdispatcher-afPartialScore-${disp}-on-10/log -P ${benchmark},$disp -a -s ${t} ${arg}; done; done

for usecase in diamante drm/drm drm/crypto; do for disp in all ib swb disttbl icondjp; do ${d}/dispatchers.py -f ${file} -l /bulk/A/measurements/tests/${usecase}/sensitivity/afdispatcher-afPartialScore-${disp}-on-10/log -P ${usecase},$disp -a -s ${t} ${arg}; done; done

echo "WROTE TO $file"
