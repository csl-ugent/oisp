#!/usr/bin/env python

# for benchmark in 436.cactusADM 445.gobmk 454.calculix; do for disp in all ib swb disttbl icondjp; do ./lib/dispatchers.py -f ~/repositories/af-metingen/data/dispatchers_archives.csv -l /bulk/A/measurements/tests/${benchmark}/sensitivity/afdispatcher-afPartialScore-${disp}-on-10/log -P ${benchmark},$disp -a -s archives; done; done

# for disp in all ib swb disttbl icondjp; do ./lib/dispatchers.py -f ~/repositories/af-metingen/data/dispatchers_archives.csv -l /bulk/A/measurements/tests/usecases/diamante_new/sensitivity/afdispatcher-afPartialScore-${disp}-on-10/log -P SLM,$disp -a -s archives; done
# for disp in all ib swb disttbl icondjp; do ./lib/dispatchers.py -f ~/repositories/af-metingen/data/dispatchers_archives.csv -l /bulk/A/measurements/tests/usecases/drm_new/sensitivity-drm/afdispatcher-afPartialScore-${disp}-on-10/log -P DRM,$disp -a -s archives; done

import common

from tools.diablo import log as DiabloLog

def generate_csv(csvfile, selector):
  csv = open(csvfile, common.conf['filemode'])
  csv.write('# %s\n' % common.argstring())
  print("GENERATING dispatcher data in %s" % csvfile)

  # construct data from factoring statistics
  factored = {}
  total_factored = 0
  for _, v in common.data['factoring-log']['raw'].items():
    nr_covered = v[selector]

    # initialisation
    if nr_covered not in factored:
      factored[nr_covered] = 0

    multiplier = v['slices']
    if common.conf['executed']:
      multiplier = v['exec_slices']

    factored[nr_covered] += v['slice_size'] * multiplier

  # total number of factored instructions
  total_factored = 0
  for _, j in factored.items():
    total_factored += j

  # number of instructions in the original binary
  total_insns = 0
  if common.conf['executed']:
    total_insns = common.data['initial-global-dynamic-complexity'][-1]['coverage']['nr_ins']
  else:
    total_insns = common.data['initial-global-static-complexity'][-1]['nr_ins']

  data = [common.conf['lineprefix'], total_insns, total_factored]

  for i in range(max(factored.keys())+1):
    if i not in factored:
      data.append(0)
    else:
      data.append(factored[i])

  line = ','.join(str(x) for x in data if x is not None)
  print(line)
  csv.write('%s\n' % line)

  csv.close()

if __name__ == "__main__":
  common.parse_args()

  if common.conf['executed']:
    common.data['initial-global-dynamic-complexity'] = DiabloLog.readDynamicComplexity(common.conf['initial-global-dynamic-complexity'])
  else:
    common.data['initial-global-static-complexity'] = DiabloLog.readStaticComplexity(common.conf['initial-global-static-complexity'])

  selector = common.conf['selector']
  if common.conf['covered-executed']:
    selector = 'exec_%s' % selector

  common.data['factoring-log'] = DiabloLog.readFactoringLog(common.conf['factoring-log'])

  generate_csv(common.conf['outfile1'], selector)
