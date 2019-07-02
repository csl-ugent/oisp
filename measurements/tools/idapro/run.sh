#!/usr/bin/env bash
# $0 <executable path and name>
docker=1

IDA_VERSION=${IDA_VERSION:-6.8}

# remove crashes
rm -f /tmp/ida/*

root_dir=$(cd $(dirname $0) && pwd)
binary=$1
shift
args_arr=($@)
args=$@

suffix=""
dbname=""
for ((index=0; index <= ${#args_arr[@]}; index++)); do
  if [ "x${args_arr[$index]}" == "x-S" ]; then
    suffix=".${args_arr[$index+1]}"
    dbname="${args_arr[$index+1]}"
  fi
done

echo "Running IDA Pro with arguments '$args'"

have_to_run=0
logfile=$binary.ida${suffix}.log
if [ ! -e "$logfile" ]; then
  # log file does not exist yet
  have_to_run=1
elif ! $(tail -n5 $logfile | grep -q Unloading); then
  # previous run did not complete successfully
  have_to_run=1
fi

if [ $have_to_run -eq 0 ]; then
  echo "  log file exists and IDA ended successfully"
  echo "  delete $logfile to rerun IDA"
  #exit
fi

# rm -f $logfile

# -o<file base>: specify the output database (implies -c)
# -A: autonomous mode. IDA will not display dialog boxes.
# -L<file>: name of the log file
# -S"<plugin> <arg>*": Execute a script file when the database is opened.
touch $logfile
if [ $docker -eq 1 ]; then
  echo "Running in Docker..."
  $root_dir/$IDA_VERSION/idaq -c -o$(dirname $binary)/${dbname} -A -L$logfile -S"$root_dir/plugin.py $args" $binary
else
  echo "Running on host..."
  ${HOME}/software/ida-$IDA_VERSION/idaq -c -o$(dirname $binary)/${dbname} -A -L$logfile -S"$root_dir/plugin.py $args" $binary
fi

# error code checking
echo "Finishing up..."
if [[ $? -ne 0 ]]; then
  echo "ERROR $logfile"
  echo "NOT_OK" >> $logfile
else
  echo "Log: $logfile"
fi
