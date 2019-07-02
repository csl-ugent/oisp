#!/usr/bin/python
# documentation: https://xlsxwriter.readthedocs.io/

# ./collect_single.py -l (path to Diablo log) [-f (path to output XLSX file)]
#   (if '-f' is not provided, a default path is constructed)
# example:
# for i in $(find /bulk/A/measurements/tests/436.cactusADM/sensitivity/*Partial* -name log); do ./collect_single.py -l $i -f $(dirname $i)/$(basename $(dirname $i)).xlsx; done

import common

import getopt
import os
import re
import sys
import xlsxwriter

import tools.diablo.log as DiabloLog
import tools.diablo.origintracking as origintracking
import lib.textualcfg as textualcfg
import lib.transformations as transformations
import lib.complexity as complexity
import measure.xlsx as xlsx

# import getopt
# import os.path
# import re
# import sys
# import xlsx
# import xlsxwriter

# import statistics_files
# import reconstruction_files

diablo_log = ""
xlsx_file = None

def print_help_exit():
  print("%s\n"\
""
  % (sys.argv[0]))
  sys.exit(1)

def parse_args():
  global diablo_log, xlsx_file

  try:
    opts, _ = getopt.getopt(sys.argv[1:], "l:f:", ["log=", "filename="])
  except getopt.GetoptError as err:
    print("ERROR:", err)
    sys.exit(1)

  for opt, arg in opts:
    if opt in ("-l", "--log"):
      diablo_log = arg
    elif opt in ("-f", "--filename"):
      xlsx_file = arg

parse_args()

diablo_dir = os.path.dirname(diablo_log)
file_prefix = diablo_dir + '/' + os.path.basename(diablo_dir)
if xlsx_file is None:
  xlsx_file = file_prefix + '.xlsx'

print("GENERATING DATA FOR %s" % (diablo_log))
print("                 TO %s" % (xlsx_file))

diablo_files = {}
diablo_files['log'] = diablo_log
diablo_files['complexity-static-initial'] = diablo_dir + "/origin_initial.stat_complexity_info"
diablo_files['complexity-dynamic-initial'] = diablo_dir + "/origin_initial.dynamic_complexity_info"
diablo_files['complexity-static-final'] = diablo_dir + "/origin_final.stat_complexity_info"
diablo_files['complexity-dynamic-final'] = diablo_dir + "/origin_final.dynamic_complexity_info"
diablo_files['obfuscation-log'] = diablo_dir + "/b.out.diablo.obfuscation.log"
diablo_files['initial-functions'] = diablo_dir + "/origin_initial.functions"
diablo_files['initial-objectfiles'] = diablo_dir + "/origin_initial.objectfiles"
diablo_files['initial-archives'] = diablo_dir + "/origin_initial.archives"
diablo_files['initial-instructions'] = diablo_dir + "/origin_initial.instructions"
diablo_files['initial-partitions'] = diablo_dir + "/origin_initial.partitions"

outfiles = {}
outfiles['excel'] = xlsx_file
outfiles['heatmap_transformations'] = file_prefix + '_heatmap_tf.csv'
outfiles['heatmap_slices'] = file_prefix + '_heatmap_slice.csv'
outfiles['function_order'] = file_prefix + '_function_order.csv'

factoring_log = None
if os.path.exists(diablo_dir + '/b.out.advanced_factoring.log'):
  factoring_log = "/b.out.advanced_factoring.log"
elif os.path.exists(diablo_dir + '/b.out.bbl_factoring.log'):
  factoring_log = "/b.out.bbl_factoring.log"

if factoring_log is not None:
  diablo_files['factoring-log'] = diablo_dir + factoring_log
  diablo_files['factoring-statistics'] = diablo_dir + factoring_log + '.statistics'
  diablo_files['factoring-instructions'] = diablo_dir + factoring_log + '.instructions'

workbook = xlsxwriter.Workbook(outfiles['excel'])

# read information about the original binary
original_functions = origintracking.readFunctions(diablo_files['initial-functions'])
original_objects = origintracking.readObjects(diablo_files['initial-objectfiles'])
original_archives = origintracking.readArchives(diablo_files['initial-archives'])
original_instructions = textualcfg.readInstructions(diablo_files['initial-instructions'])

# parse Diablo log
rgx_tracking_origin = re.compile(r'^\s+Tracking origin_([^_]+)_insns_([^:]+):(\d+):(\d+)$')
rgx_input_instructions = re.compile(r'^Disassembled (\d+) instructions$')
rgx_total_nr_instructions = re.compile(r'^\s+Done: processed (\d+) instructions$')
rgx_gain = re.compile(r'^\s+GAIN (\-?[\d\.]+)%\s+(.*)$')
rgx_create_fake_edge = re.compile(r'^\s+Chose new target selector \'([^\']+)\'.*$')

# Diablo data
tracking_origin = {}
total_nr_instructions = 0
total_input_instructions = 0
gains = {}
fake_edges = {}
af_factored = {}

f = open(diablo_files['log'], 'r')
for line in f.readlines():
  line = line.rstrip()

  m = re.search(rgx_tracking_origin, line)
  if m is not None:
    cat = m.group(1)
    what = m.group(2)
    x = int(m.group(3))
    y = int(m.group(4))

    if cat not in tracking_origin:
      tracking_origin[cat] = {}

    if what not in tracking_origin[cat]:
      tracking_origin[cat][what] = {}
    tracking_origin[cat][what][x] = y
    continue

  m = re.search(rgx_input_instructions, line)
  if m is not None:
    total_input_instructions += int(m.group(1))
    continue

  m = re.search(rgx_total_nr_instructions, line)
  if m is not None:
    total_nr_instructions = int(m.group(1))
    continue

  m = re.search(rgx_gain, line)
  if m is not None:
    gains[m.group(2)] = float(m.group(1))
    continue

  m = re.search(rgx_create_fake_edge, line)
  if m is not None:
    where = m.group(1)

    if where not in fake_edges:
      fake_edges[where] = 0
    fake_edges[where] += 1
    continue

f.close()

# advanced factoring log file parsing
factoring_log = None
factored_stats = None
if 'factoring-log' in diablo_files:
  factoring_log = DiabloLog.readFactoringLog(diablo_files['factoring-log'])
  factored_stats = DiabloLog.readFactoringStatistics(diablo_files['factoring-statistics'])

all_tf_data = {}
if factoring_log is not None:
  all_tf_data = factoring_log['raw'].copy()

# read transformation effects
if os.path.exists(diablo_files['obfuscation-log']):
  obf_log_data = DiabloLog.readObfuscationLog(diablo_files['obfuscation-log'])
  # merge transformation data, as the keys are unique anyways
  all_tf_data.update(obf_log_data)

transformations.generate_sheet(workbook, 'transformations', all_tf_data)

total_nr_archives = len(original_archives)
factored_insn_data = [0 for k in range(total_nr_archives+1)]
total_factored_insns = 0
total_original_insns = 0

# complexity metrics (whole program)
Sl, Sb, Sa, Dcl, Dcb, Dca, Dtl, Dtb, Dta = complexity.before_after(".non-origin", diablo_files)
assert Sl.index('nr_ins')==0
total_original_insns = Sb[-1][0]
coverage_position = [0, 0]
trace_position = [20, 0]
static_position = [0, 13]
xlsx.add_column_chart(workbook, 'compl-all', [Dcb[-1], Dca[-1]], ["before", "after"], Dcl, start_row=coverage_position[0], start_column=coverage_position[1], title="coverage")
xlsx.add_column_chart(workbook, 'compl-all', [Dtb[-1], Dta[-1]], ["before", "after"], Dtl, start_row=trace_position[0], start_column=trace_position[1], title="trace length")
xlsx.add_column_chart(workbook, 'compl-all', [Sb[-1], Sa[-1]], ["before", "after"], Sl, start_row=static_position[0], start_column=static_position[1], title="static")

# even more data: compare coverage/static
perc_before = []
perc_after = []
for i in range(0, len(Sl)):
  perc_before.append(Dcb[-1][i]/Sb[-1][i]*100)
  perc_after.append(Dca[-1][i]/Sa[-1][i]*100)

xlsx.add_column_chart(workbook, 'compl-all', [perc_before, perc_after], ["before", "after"], Sl, start_row=20, start_column=13, title="coverage/static %", delta_subtract=True, datagenerator=complexity.generate_relative, debug=True)

Sl, Sb, Sa, Dcl, Dcb, Dca, Dtl, Dtb, Dta = complexity.before_after("-functions", diablo_files)
complexity.generate_sheet(workbook, 'compl-functions', Sl, Sb, Sa, Dcl, Dcb, Dca, Dtl, Dtb, Dta, original_functions)
Sl, Sb, Sa, Dcl, Dcb, Dca, Dtl, Dtb, Dta = complexity.before_after("-objects", diablo_files)
complexity.generate_sheet(workbook, 'compl-objects', Sl, Sb, Sa, Dcl, Dcb, Dca, Dtl, Dtb, Dta, original_objects)
Sl, Sb, Sa, Dcl, Dcb, Dca, Dtl, Dtb, Dta = complexity.before_after("-archives", diablo_files)
complexity.generate_sheet(workbook, 'compl-archives', Sl, Sb, Sa, Dcl, Dcb, Dca, Dtl, Dtb, Dta, original_archives)

def to_categorized_exec_notexec(total, selected):
  cats = {}

  for k, v in total.items():
    cats[k] = {}

    x = 0
    if k in selected:
      x = selected[k]

    cats[k]['executed'] = x
    cats[k]['not executed'] = v - x

  return cats

def sort_percents(data):
  filtered = {k:v for (k,v) in data.items() if v['total'] != 0}
  return sorted(filtered.items(), key=lambda t: t[1]['n']/(t[1]['total']))

# ===================================================================================================================================================
# collect information about initial functions
functions_per_archive = {}
original_functions_uids = set()
function_uid_to_original_uid = {}
initial_partitions = origintracking.readPartitions(diablo_files['initial-partitions'])
for f_uid, f_data in original_functions.items():
  f_original_uid = f_data['original_uid']

  if f_data['original_uid'] != -1:
    function_uid_to_original_uid[f_uid] = f_original_uid
    continue

  # for sanity checks
  original_functions_uids.add(f_uid)

  # archive this function belongs to
  associated_libs = initial_partitions[f_data['partition_uid']]['associated_libraries']
  assert len(associated_libs) == 1, "function %s (%d) has multiple libraries %s" % (f_data['name'], f_uid, associated_libs)

  for lib_uid in associated_libs:
    if lib_uid not in functions_per_archive:
      functions_per_archive[lib_uid] = set()
    functions_per_archive[lib_uid].add(f_uid)

# read factored instructions to construct a list with the factored functions
functions_transformed_at_least_once = set()

factored_instructions = None
if factoring_log is not None:
  factored_instructions = DiabloLog.readFactoringInstructions(diablo_files['factoring-instructions'])
  for insn_address, _ in factored_instructions.items():
    # transformed function original UID
    function_for_insn = original_instructions['instructions'][insn_address]['function_uid']
    assert len(function_for_insn) == 1, "multiple functions for instruction 0x%x: %s" % (insn_address, function_for_insn)

    original_function_uid = function_for_insn[0]
    if original_function_uid in function_uid_to_original_uid:
      original_function_uid = function_uid_to_original_uid[original_function_uid]
    functions_transformed_at_least_once.add(original_function_uid)

assert len(functions_transformed_at_least_once - original_functions_uids) == 0

# calculate function sizes
function_sizes = {}
for insn_address, insn_data in original_instructions['instructions'].items():
  # original function UID this instruction belongs to
  insn_fuid = insn_data['function_uid'][0]
  if insn_fuid in function_uid_to_original_uid:
    insn_fuid = function_uid_to_original_uid[insn_fuid]

  if insn_fuid not in function_sizes:
    function_sizes[insn_fuid] = 0
  function_sizes[insn_fuid] += 1

# X-axis: average function size per archive
# Y-axis: fraction of functions transformed at least once
# 1 data point = 1 archive
plot_data = {}
comments = {}

for lib_uid, lib_functions in functions_per_archive.items():
  # X, Y data
  plot_data[lib_uid] = {}

  avg_size = 0
  for f_uid in lib_functions:
    if f_uid not in function_sizes:
      # in libdiamante, _armv8_sha256_probe is an ARMv8 specific function, which is decoded as DATA by Diablo
      # it will thus not be present in the list of instructions
      continue
    avg_size += function_sizes[f_uid]/len(lib_functions)
  plot_data[lib_uid]['avg_size'] = avg_size

  frac_tf = (len(lib_functions) - len(lib_functions - functions_transformed_at_least_once)) / len(lib_functions)
  plot_data[lib_uid]['frac_tf'] = frac_tf

comments = ['%s (%d functions)' % (original_archives[lib_uid]['name'], len(functions_per_archive[lib_uid])) for lib_uid, _ in plot_data.items()]
point_labels = [len(functions_per_archive[k]) for k, _ in plot_data.items()]
x_data = [v['avg_size'] for _, v in plot_data.items()]
y_data = [v['frac_tf'] for _, v in plot_data.items()]

xlsx.add_scatter_xy(workbook, 'fraction-tffn-archive', x_data, y_data, point_labels, comments)
# ===================================================================================================================================================

def boxplots(sheetname):
  worksheet = xlsx.create_or_get_worksheet(workbook, sheetname)

  q_base_col = len(original_archives) + 1

  for i in range(0, 5):
    worksheet.write(1+i, q_base_col, 'Q%d' % i)
  worksheet.write(6, q_base_col, 'AVG')
  worksheet.write(7, q_base_col, 'N')
  worksheet.write(8, q_base_col, 'TF')
  worksheet.write(9, q_base_col, 'frac')

  for lib_uid, lib_functions in functions_per_archive.items():
    worksheet.write(0, lib_uid, 'Archive %d' % lib_uid)
    worksheet.write(0, q_base_col + lib_uid + 1, 'Archive %d' % lib_uid)
    data = []
    for f_uid in lib_functions:
      if f_uid not in function_sizes:
        continue
      data.append(function_sizes[f_uid])
    worksheet.write_column(1, lib_uid, data)

    firstcell = xlsxwriter.utility.xl_rowcol_to_cell(1, lib_uid)
    lastcell = xlsxwriter.utility.xl_rowcol_to_cell(len(lib_functions), lib_uid)

    for i in range(0, 5):
      worksheet.write(1+i, q_base_col + lib_uid + 1, '=_xlfn.QUARTILE.INC(%s:%s,%d)' % (firstcell, lastcell, i))

    worksheet.write(6, q_base_col + lib_uid + 1, '=AVERAGE(%s:%s)' % (firstcell, lastcell))
    worksheet.write(7, q_base_col + lib_uid + 1, len(lib_functions))
    worksheet.write(8, q_base_col + lib_uid + 1, len(lib_functions) - len(lib_functions - functions_transformed_at_least_once))
    worksheet.write(9, q_base_col + lib_uid + 1, '=%s/%s' % (xlsxwriter.utility.xl_rowcol_to_cell(8, q_base_col + lib_uid + 1), xlsxwriter.utility.xl_rowcol_to_cell(7, q_base_col + lib_uid + 1)))
boxplots('func-sizes-per-archive')

if factoring_log is not None:
  xlsx.add_column_chart_cats(workbook, 'Slice size', to_categorized_exec_notexec(factored_stats['hist_slicesize'], factoring_log['length2x']), 'Number of transformed slices per slice size', xlabel='slice size (# instructions)', ylabel='Number of slices')
  xlsx.add_column_chart_cats(workbook, 'Set size', to_categorized_exec_notexec(factored_stats['hist_setsize'], factoring_log['set2x']), 'Number of transformed sets of X slices', xlabel='set size (# slices)', ylabel='Number of sets')
  xlsx.add_column_chart_cats(workbook, 'Covered archives', to_categorized_exec_notexec(factored_stats['hist_archives'], factoring_log['a2x']), 'Number of archives covered by sets', xlabel='covered archive count', ylabel='Number of sets')
  xlsx.add_column_chart_cats(workbook, 'Covered objects', to_categorized_exec_notexec(factored_stats['hist_objects'], factoring_log['o2x']), 'Number of objects covered by sets', xlabel='covered object count', ylabel='Number of sets')
  xlsx.add_column_chart_cats(workbook, 'Covered functions', to_categorized_exec_notexec(factored_stats['hist_functions'], factoring_log['f2x']), 'Number of functions covered by sets', xlabel='covered function count', ylabel='Number of sets')
xlsx.add_percent_chart(workbook, 'Final reachable (lib)', 'Number of libraries', 'Instruction count', tracking_origin['final']['reachable_by_library'].items(), 'Number of instructions reachable by X libraries', total_nr_instructions)
xlsx.add_percent_chart(workbook, 'Final reachable (obj)', 'Number of objects', 'Instruction count', tracking_origin['final']['reachable_by_object'].items(), 'Number of instructions reachable by X objects', total_nr_instructions)
xlsx.add_percent_chart(workbook, 'Final reachable (fun)', 'Number of functions', 'Instruction count', tracking_origin['final']['reachable_by_functions'].items(), 'Number of instructions reachable by X functions', total_nr_instructions)
xlsx.add_percent_chart(workbook, 'Final associated (lib)', 'Number of libraries', 'Instruction count', tracking_origin['final']['associated_with_library'].items(), 'Number of instructions associated with X libraries', total_nr_instructions)
xlsx.add_percent_chart(workbook, 'Final associated (obj)', 'Number of objects', 'Instruction count', tracking_origin['final']['associated_with_object'].items(), 'Number of instructions associated with X objects', total_nr_instructions)
xlsx.add_percent_chart(workbook, 'Final associated (fun)', 'Number of functions', 'Instruction count', tracking_origin['final']['associated_with_functions'].items(), 'Number of instructions associated with X functions', total_nr_instructions)
if factoring_log is not None:
  xlsx.add_percent_chart(workbook, 'Factored per archive', 'Archive UID', 'Number of factored instructions', sort_percents(factored_stats['archive']), 'Number of instructions factored per archive', comments=original_archives)
  xlsx.add_percent_chart(workbook, 'Factored per object', 'Object UID', 'Number of factored instructions', sort_percents(factored_stats['object']), 'Number of instructions factored per object', comments=original_objects)
  xlsx.add_percent_chart(workbook, 'Factored per function', 'Function UID', 'Number of factored instructions', sort_percents(factored_stats['function']), 'Number of instructions factored per function', comments=original_functions)

# various data
worksheet = xlsx.create_or_get_worksheet(workbook, 'data')
current_row = 0

# stacked cluster data
labels = ['original_insns', 'factored_insns']
for i in range(len(factored_insn_data)):
  labels.append('X%d' % i)
worksheet.write_row(current_row, 0, labels)
current_row += 1
worksheet.write(current_row, 0, total_original_insns)
worksheet.write(current_row, 1, total_factored_insns)
worksheet.write_row(current_row, 2, factored_insn_data)
current_row += 1
print("%d,%d,%s" % (total_original_insns, total_factored_insns, ','.join([str(x) for x in factored_insn_data])))

# function ordering
original_function_order = {}
for k, _ in original_functions.items():
  original_function_order[k] = 0

# iterate over factored instructions and assign a category to each function
max_order = 0
for insn_address, data in factored_instructions.items():
  function_for_insn = original_instructions['instructions'][insn_address]['function_uid'][0]
  tf_uid = data['tf_uid']

  assert tf_uid in factoring_log['raw']
  tf_data = factoring_log['raw'][tf_uid]

  new_order = tf_data['archives']
  if new_order > original_function_order[function_for_insn]:
    original_function_order[function_for_insn] = new_order
  if new_order > max_order:
    max_order = new_order

# f = open(outfiles['function_order'], 'w')
# print("  generating function order data in %s" % outfiles['function_order'])
# for k, v in original_function_order.items():
#   f.write('%d,%d\n' % (k, v))
# f.close()

# calculate number of functions per category
functions_per_order = [0 for _ in range(max_order+1)]
for _, v in original_function_order.items():
  functions_per_order[v] += 1

labels = ['original_functions', 'factored_functions']
for i in [x for x in range(max_order+1)]:
  labels.append('X%d' % i)
worksheet.write_row(current_row, 0, labels)
current_row += 1
worksheet.write(current_row, 0, len(original_function_order))
worksheet.write(current_row, 1, len(original_function_order)-functions_per_order[0])
worksheet.write_row(current_row, 2, [x for x in functions_per_order])
current_row += 1
print("%d,%d,%s" % (len(original_function_order), len(original_function_order)-functions_per_order[0], ','.join([str(x) for x in functions_per_order])))

workbook.close()
