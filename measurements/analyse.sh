#!/usr/bin/env bash
root=$(cd $(dirname $0) && pwd)
binary=$1

echo "Analysing binary $binary..."

# run 'dumb' IDA pro
echo "  IDA 'dumb'..."
$root/tools/idapro/run.sh $binary

# run 'smart' IDA pro
echo "  IDA 'smart'..."
$root/tools/idapro/run.sh $binary -j -h th -s -S jths

# compare 'dumb'
echo "  compare 'dumb' 1/2..."
$root/measure/compare.py -b $binary -o final > $binary.compare.log
echo "  compare 'dumb' 2/2..."
$root/measure/compare.py -b $binary -o final -i jths -s jths > $binary.compare-jths.log

# compare 'smart'
echo "  compare 'smart' 1/2..."
$root/measure/compare.py -b $binary -o final -s smart -S > $binary.compare-smart.log
echo "  compare 'smart' 2/2..."
$root/measure/compare.py -b $binary -o final -i jths -s jths-smart -S > $binary.compare-jths-smart.log
