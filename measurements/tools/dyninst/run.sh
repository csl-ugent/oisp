#!/usr/bin/env bash
# $0 <executable path and name>
set -x
root_dir=$(cd $(dirname $0) && pwd)
binary=$1

binary_name=$(basename $binary)
binary_dir=$(dirname $binary)

### 1. Generate JSON files with Dyninst
dyninst_container=$(docker ps | grep dyninst | awk '{print $1}')
dyninst_pwd=$(docker inspect --format='{{range .Mounts}}{{if eq .Destination "/pwd"}}{{.Source}}{{end}}{{end}}' $dyninst_container)

# set up input files and run dyninst
cp $binary $dyninst_pwd/
echo "running Dyninst in $dyninst_container"
docker exec $dyninst_container /code/functionsimsearch/bin/text --format=ELF --input=/pwd/$binary_name --output=/pwd/$binary_name.dyninst

# copy output files
cp $dyninst_pwd/$binary_name.dyninst.* $binary_dir

# clean up dyninst output directory
rm -f $dyninst_pwd/$binary_name*

### 2. Aggregate the Dyninst output
#$root_dir/dyninst_aggregate.py -b $binary -d $binary-dyninst
