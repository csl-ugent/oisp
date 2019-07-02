#!/usr/bin/env bash

# for i in $(find ${PWD} -name b.out | egrep "clusterchance"); do cd $(dirname $i); ~/repositories/af-metingen/do-all.sh ; done

cp b.out b.out.stripped

strip_binary=/bulk/A/diablo-toolchains/linux/gcc/arm/gcc-4.8.1/bin/arm-diablo-linux-gnueabi-strip
if [ ! -f $strip_binary ]; then
  strip_binary=$HOME/actc-data/diablo-toolchains/linux/gcc/arm/gcc-4.8.1/bin/arm-diablo-linux-gnueabi-strip
fi
$strip_binary b.out.stripped

# IDA ==================================================================================================================================================
# For (non)stripped versions:
#   1. not repartitioned
#   2. repartitioned
~/repositories/af-metingen/tools/idapro/run.sh ${PWD}/b.out -S notstripped -p 5 &
~/repositories/af-metingen/tools/idapro/run.sh ${PWD}/b.out -S notstripped-smart -p 5 -h -g -s -b -f &

~/repositories/af-metingen/tools/idapro/run.sh ${PWD}/b.out.stripped -S stripped-smart -p 5 -h -g -s -b -f &
~/repositories/af-metingen/tools/idapro/run.sh ${PWD}/b.out.stripped -S stripped -p 5 &
wait < <(jobs -p)

# COMPARE ==============================================================================================================================================
# For (non)stripped versions:
#   1. not repartitioned, not attacked
#   2. repartitioned, not attacked
#   3. repartitioned, attacked (GUI)
#   4. repartitioned, attacked (DB)
~/repositories/af-metingen/measure/compare.sh -b ${PWD}/b.out -o final -i notstripped -p 5 -s X > compare-notstripped-noatk.log &
~/repositories/af-metingen/measure/compare.sh -b ${PWD}/b.out -o final -i notstripped-smart -p 5 -s X > compare-notstripped-smart-noatk.log &
~/repositories/af-metingen/measure/compare.sh -b ${PWD}/b.out -o final -i notstripped-smart -p 5 -s X -S > compare-notstripped-smart-atk.log &
~/repositories/af-metingen/measure/compare.sh -b ${PWD}/b.out -o final -i notstripped-smart -p 5 -s X -S -d > compare-notstripped-smart-atk-DB.log &

~/repositories/af-metingen/measure/compare.sh -b ${PWD}/b.out.stripped -o final -i stripped -p 5 -s X > compare-stripped-noatk.log &
~/repositories/af-metingen/measure/compare.sh -b ${PWD}/b.out.stripped -o final -i stripped-smart -p 5 -s X > compare-stripped-smart-noatk.log &
~/repositories/af-metingen/measure/compare.sh -b ${PWD}/b.out.stripped -o final -i stripped-smart -p 5 -s X -S > compare-stripped-smart-atk.log &
~/repositories/af-metingen/measure/compare.sh -b ${PWD}/b.out.stripped -o final -i stripped-smart -p 5 -s X -S -d > compare-stripped-smart-atk-DB.log &
wait < <(jobs -p)

egrep IdaPro.*Ins.*functionless compare*.log
