#!/usr/bin/env bash
binary=$1

function doit {
  local binary=$1
  shift

  echo "IDA..."
  ./ida.sh $binary $@

  echo "Compare $binary.compare"
  ./compare.py -b $binary -B $binary -o final > $binary.compare
}

for x in "" "s"; do
  for y in "" h t ht th; do
    args=()
    newname=$binary
    if [ ! -z "$x" ]; then
      newname="$newname-$x"
      args+=("-s")
    fi
    if [ ! -z "$y" ]; then
      newname="$newname-$y"
      args+=("-h $y")
    fi

    cp $binary $newname
    cp $binary.list $newname.list
    cp $binary.killed $newname.killed
    doit $newname ${args[@]}

    cp $binary.stripped $newname.stripped
    doit $newname.stripped ${args[@]}
  done
done
