#!/usr/bin/env bash
set -x

datadir=$1
texprefix=$2

~/repositories/af-metingen/generate-table.py $datadir/no-transformations/compare-stripped-noatk.log > ${texprefix}_unprotected.tex

~/repositories/af-metingen/generate-table.py $datadir/afdispatcher-all/compare-stripped-noatk.log > ${texprefix}_IDAdumb_ATKdumb.tex
~/repositories/af-metingen/generate-table.py $datadir/afdispatcher-all/compare-stripped-smart-atk-DB.log > ${texprefix}_IDAsmart_ATKsmart_DB.tex
~/repositories/af-metingen/generate-table.py $datadir/afdispatcher-all/compare-stripped-smart-noatk.log > ${texprefix}_IDAsmart_ATKdumb.tex
~/repositories/af-metingen/generate-table.py $datadir/afdispatcher-all/compare-stripped-smart-atk.log > ${texprefix}_IDAsmart_ATKsmart.tex
