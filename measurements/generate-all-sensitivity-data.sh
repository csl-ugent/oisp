#!/usr/bin/env bash
rootdir=$(cd $(dirname $0) && pwd)
repodir=$HOME/repositories/af-metingen

texprefix=$1

function generate {
  data="$1"
  csvprefix="$2"

  $repodir/generate-sensitivity.py compare-stripped-smart-noatk.log $data > $csvprefix-before.csv
  $repodir/generate-sensitivity.py compare-stripped-smart-atk.log $data | grep -v " (DB)" > $csvprefix-after.csv
  $repodir/generate-sensitivity.py compare-stripped-smart-atk-DB.log $data | grep -v " (GUI)" > $csvprefix-after-DB.csv

  $repodir/R/sensitivity_scatter.R $csvprefix-before.csv "No attack" $csvprefix-after-DB.csv "Sound attack" $csvprefix-after.csv "Unsound attack" > ${texprefix}${csvprefix}.tex
}

function generate_links {
  data1="$1"
  data2="$2"
  csvprefix="$3"

  $repodir/generate-sensitivity-afchance.py compare-stripped-smart-noatk.log $data1 > $csvprefix-before1.csv
  $repodir/generate-sensitivity-afchance.py compare-stripped-smart-atk.log $data1 | grep -v " (DB)" > $csvprefix-after1.csv
  $repodir/generate-sensitivity-afchance.py compare-stripped-smart-atk-DB.log $data1 | grep -v " (GUI)" > $csvprefix-after-DB1.csv

  $repodir/generate-sensitivity-afchance.py compare-stripped-smart-noatk.log $data2 > $csvprefix-before2.csv
  $repodir/generate-sensitivity-afchance.py compare-stripped-smart-atk.log $data2 | grep -v " (DB)" > $csvprefix-after2.csv
  $repodir/generate-sensitivity-afchance.py compare-stripped-smart-atk-DB.log $data2 | grep -v " (GUI)" > $csvprefix-after-DB2.csv

  $repodir/R/sensitivity_scatter_afchance.R $csvprefix-before1.csv $csvprefix-before2.csv "No attack" $csvprefix-after-DB1.csv $csvprefix-after-DB2.csv "Sound attack" $csvprefix-after1.csv $csvprefix-after2.csv "Unsound attack" > ${texprefix}${csvprefix}.tex
  # $repodir/R/sensitivity_scatter_afchance.R $csvprefix-before1.csv $csvprefix-before2.csv "No attack" > ${texprefix}${csvprefix}.tex
}

generate "afchance-1 1 afchance-10 10 afchance-25 25 afchance-50 50 afchance-75 75 afchance-100 100" afchance
generate "clusterchance-0 0 clusterchance-25 25 clusterchance-50 50 clusterchance-75 75 clusterchance-100 100" clusterchance
generate "clustersize-1 1 clustersize-2 2 clustersize-4 4 clustersize-6 6 clustersize-10 10" clustersize
generate "fakeentry-0 0 fakeentry-10 10 fakeentry-20 20 fakeentry-30 30" fakeentry
generate "fakeft-0 0 fakeft-25 25 fakeft-50 50 fakeft-75 75 fakeft-100 100" fakeft
generate "opaquepreds-0 0 opaquepreds-2 2 opaquepreds-5 5 opaquepreds-20 20 opaquepreds-50 50 opaquepreds-75 75 opaquepreds-100 100" opaque
generate "masterseed-1 1 masterseed-2 2 masterseed-3 3 masterseed-4 4 masterseed-5 5 masterseed-6 6 masterseed-7 7 masterseed-8 8 masterseed-9 9 masterseed-10 10" masterseed
generate "orderseed-1 1 orderseed-100 100 orderseed-20 20 orderseed-30 30 orderseed-40 40 orderseed-50 50 orderseed-60 60 orderseed-70 70 orderseed-80 80 orderseed-90 90 orderseed-100 100" orderseed

generate_links "afchance-opaque0-1 1 afchance-opaque0-10 10 afchance-opaque0-25 25 afchance-opaque0-50 50 afchance-opaque0-75 75 afchance-opaque0-100 100" "afchance-1 1 afchance-10 10 afchance-25 25 afchance-50 50 afchance-75 75 afchance-100 100" links
