import xlsxwriter

import measure.xlsx as xlsx
import tools.diablo.log as DiabloLog

def complexity_collect(X):
  labels = []
  data = []

  for k, v in X.items():
    labels.append(k)
    data.append(v)

  return labels, data

def before_after(suffix, diablo_files):
  static_complexity_labels = []
  dynamic_complexity_coverage_labels = []
  dynamic_complexity_trace_labels = []

  # static complexity
  static_complexity_before = DiabloLog.readStaticComplexity(diablo_files['complexity-static-initial'] + suffix)
  static_complexity_data_before = {}
  for k, v in static_complexity_before.items():
    static_complexity_labels, d = complexity_collect(v)
    static_complexity_data_before[k] = d

  static_complexity_after = DiabloLog.readStaticComplexity(diablo_files['complexity-static-final'] + suffix)
  static_complexity_data_after = {}
  for k, v in static_complexity_after.items():
    _, d = complexity_collect(v)
    static_complexity_data_after[k] = d

  # dynamic complexity
  dynamic_complexity_before = DiabloLog.readDynamicComplexity(diablo_files['complexity-dynamic-initial'] + suffix)
  dynamic_complexity_coverage_before = {}
  dynamic_complexity_trace_before = {}
  for k, v in dynamic_complexity_before.items():
    dynamic_complexity_coverage_labels, d = complexity_collect(v['coverage'])
    dynamic_complexity_coverage_before[k] = d

    dynamic_complexity_trace_labels, d = complexity_collect(v['trace'])
    dynamic_complexity_trace_before[k] = d

  dynamic_complexity_after = DiabloLog.readDynamicComplexity(diablo_files['complexity-dynamic-final'] + suffix)
  dynamic_complexity_coverage_after = {}
  dynamic_complexity_trace_after = {}
  for k, v in dynamic_complexity_after.items():
    _, d = complexity_collect(v['coverage'])
    dynamic_complexity_coverage_after[k] = d

    _, d = complexity_collect(v['trace'])
    dynamic_complexity_trace_after[k] = d

  return static_complexity_labels, static_complexity_data_before, static_complexity_data_after, dynamic_complexity_coverage_labels, dynamic_complexity_coverage_before, dynamic_complexity_coverage_after, dynamic_complexity_trace_labels, dynamic_complexity_trace_before, dynamic_complexity_trace_after

# complexity metrics (per category)
def generate_sheet(workbook, sheetname, Sl, Sb, Sa, Dcl, Dcb, Dca, Dtl, Dtb, Dta, comments):
  worksheet = xlsx.create_or_get_worksheet(workbook, sheetname)

  merge_format = {}

  fmt_raw_data = workbook.add_format({'font_color': '#aaaaaa'})
  fmt_inc_data = workbook.add_format({'font_color': '#006100', 'bold': True})
  fmt_dec_data = workbook.add_format({'font_color': '#9c0006', 'bold': True})

  cell_fmt_inc = {
    'type': 'cell',
    'criteria': '>=',
    'value': 0,
    'format': fmt_inc_data
  }
  cell_fmt_dec = {
    'type': 'cell',
    'criteria': '<',
    'value': 0,
    'format': fmt_dec_data
  }

  # static complexity
  static_first_column = 1
  worksheet.merge_range(0, static_first_column, 0, static_first_column+len(Sl)-1, 'STATIC', merge_format)
  worksheet.write_row(1, static_first_column, Sl)

  # dynamic complexity
  dynamic_coverage_first_column = static_first_column + len(Sl)
  worksheet.merge_range(0, dynamic_coverage_first_column, 0, dynamic_coverage_first_column+len(Dcl)-1, 'DYNAMIC (coverage)', merge_format)
  worksheet.write_row(1, dynamic_coverage_first_column, Dcl)

  dynamic_trace_first_column = dynamic_coverage_first_column + len(Dcl)
  worksheet.merge_range(0, dynamic_trace_first_column, 0, dynamic_trace_first_column+len(Dtl)-1, 'DYNAMIC (trace length)', merge_format)
  worksheet.write_row(1, dynamic_trace_first_column, Dtl)

  # data
  current_row = 2

  for k, _ in Sb.items():
    if Sb[k][0] == 0 and Sa[k][0] == 0:
      continue

    # labels
    worksheet.write(current_row, 0, k)
    worksheet.write_comment(current_row, 0, comments[k]['name'])

    for i in range(0, len(Sl)+len(Dcl)+len(Dtl)):
      before_cell = xlsxwriter.utility.xl_rowcol_to_cell(current_row+1, 1+i)
      after_cell = xlsxwriter.utility.xl_rowcol_to_cell(current_row+2, 1+i)

      worksheet.write_formula(current_row, 1+i, '=IF(%s=0, "", (%s-%s)/%s*100)' % (before_cell, after_cell, before_cell, before_cell))
    worksheet.conditional_format(current_row, 1, current_row, len(Sl)+len(Dcl)+len(Dtl), cell_fmt_inc)
    worksheet.conditional_format(current_row, 1, current_row, len(Sl)+len(Dcl)+len(Dtl), cell_fmt_dec)

    # before
    worksheet.write(current_row+1, 0, 'before', fmt_raw_data)
    worksheet.write_row(current_row+1, static_first_column, Sb[k], fmt_raw_data)
    worksheet.write_row(current_row+1, dynamic_coverage_first_column, Dcb[k], fmt_raw_data)
    worksheet.write_row(current_row+1, dynamic_trace_first_column, Dtb[k], fmt_raw_data)

    # after
    worksheet.write(current_row+2, 0, 'after', fmt_raw_data)
    worksheet.write_row(current_row+2, static_first_column, Sa[k], fmt_raw_data)
    worksheet.write_row(current_row+2, dynamic_coverage_first_column, Dca[k], fmt_raw_data)
    worksheet.write_row(current_row+2, dynamic_trace_first_column, Dta[k], fmt_raw_data)

    current_row += 3

def generate_relative(worksheet, series, start_row, start_col):
  column_offset = 0
  if series == "after":
    column_offset = 1

  for i in range(0, 7):
    covcell = xlsxwriter.utility.xl_rowcol_to_cell(1+i, 1+column_offset)
    statcell = xlsxwriter.utility.xl_rowcol_to_cell(1+i, 14+column_offset)

    worksheet.write(start_row+i, start_col, '=%s/%s*100' % (covcell, statcell))
