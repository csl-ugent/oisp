#!/usr/bin/env python

import common

from tools.diablo import log as DiabloLog

def generate_csv(csvfile_transformation, csvfile_slice, selector):
  csvtf = open(csvfile_transformation, 'w')
  csvtf.write('# %s\n' % common.argstring())
  csvtf.write('# File 1/2: transformations\n')
  print("GENERATING transformation heatmap data in %s" % csvfile_transformation)

  csvsl = open(csvfile_slice, 'w')
  csvsl.write('# %s\n' % common.argstring())
  csvsl.write('# File 2/2: slices\n')
  print("GENERATING slice heatmap data in %s" % csvfile_slice)

  # slice lengths
  x = set()
  for _, v in common.data['factoring-log']['raw'].items():
    x.add(v['slice_size'])

  # data processing
  slice_data = {}
  tf_data = {}

  for _, v in common.data['factoring-log']['raw'].items():
    nr = v[selector]
    nr_exec = v['exec_%s' % selector]

    # slice length
    length_idx = list(x).index(v['slice_size'])

    if nr not in slice_data:
      slice_data[nr] = {}
      tf_data[nr] = {}
    if nr_exec not in slice_data[nr]:
      slice_data[nr][nr_exec] = [0 for i in range(len(x))]
      tf_data[nr][nr_exec] = [0 for i in range(len(x))]

    # slice count
    slice_data[nr][nr_exec][length_idx] += v['slices']

    # transformation count
    tf_data[nr][nr_exec][length_idx] += 1

  # header line
  header = 'Y'
  to_write = []
  empty_data = {}
  for i_index, i in enumerate(sorted(slice_data.keys())):
    # collect non-zero lengths
    valid_lengths = set()
    for j in range(len(x)):
      # calculate sum
      S = 0
      for k in slice_data[i]:
        S += slice_data[i][k][j]
      if S > 0:
        valid_lengths.add(j)

    # mark valid data
    for j in slice_data[i]:
      for k, v in enumerate(slice_data[i][j]):
        if k not in valid_lengths:
          assert v == 0, v

          slice_data[i][j][k] = -1
          tf_data[i][j][k] = -1

    # collect header
    header += ',' + ','.join(['%d/%d' % (i, list(x)[ii]) for ii in valid_lengths])

    to_write.append(False)
    empty_data[i_index] = ','.join(['' for ii in valid_lengths])

  # CSV file contents
  csvtf.write(header+'\n')
  csvsl.write(header+'\n')

  csv_tf_lines = {}
  csv_sl_lines = {}
  todo = {}

  for i_index, i in enumerate(sorted(slice_data.keys())):
    for j in sorted(slice_data[i].keys()):
      # initialisation
      if j not in csv_tf_lines:
        todo[j] = [False for i in to_write]
        csv_tf_lines[j] = '%d' % j
        csv_sl_lines[j] = '%d' % j

      prefix = ''
      for ii in range(i_index):
        if todo[j][ii] == False:
          prefix += ',' + empty_data[ii]
          todo[j][ii] = True

      csv_sl_lines[j] += prefix + ',' + ','.join([str(k) for k in slice_data[i][j] if k != -1])
      todo[j][i_index] = True

  for _, l in csv_tf_lines.items():
    csvtf.write(l + '\n')
  for _, l in csv_sl_lines.items():
    csvsl.write(l + '\n')

  csvtf.close()
  csvsl.close()

if __name__ == "__main__":
  # filename1: transformation heatmap CSV file
  # filename2: slice heatmap CSV file
  # selector: archives, objects, functions, blocks (=contexts)

  common.parse_args()
  selector = common.conf['selector']
  common.data['factoring-log'] = DiabloLog.readFactoringLog(common.conf['factoring-log'])
  generate_csv(common.conf['outfile1'], common.conf['outfile2'], selector)
