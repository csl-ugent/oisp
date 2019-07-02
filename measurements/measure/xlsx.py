import math
import xlsxwriter
import os

def create_or_get_worksheet(workbook, worksheet_name):
  worksheet = None

  try:
    worksheet = workbook.add_worksheet(worksheet_name)
  except:
    worksheet = workbook.get_worksheet_by_name(worksheet_name)

  return worksheet

def add_log_log_chart(worksheet_name, xlabel, ylabel, data, title):
  # worksheet: slice size histogram
  worksheet = workbook.add_worksheet(worksheet_name)
  current_row = 0

  # data
  worksheet.write(current_row, 0, xlabel)
  worksheet.write(current_row, 1, ylabel)
  current_row += 1
  for k, v in data:
    worksheet.write(current_row, 0, k)
    worksheet.write(current_row, 1, v)
    current_row += 1

  # chart
  chart = workbook.add_chart({'type': 'column'})
  chart.add_series({
    # sheet name, first row, first col, last row, last col
    'categories': [worksheet_name, 1, 0, current_row-1, 0],
    'values': [worksheet_name, 1, 1, current_row-1, 1]
  })
  chart.set_title({'name': title})
  chart.set_x_axis({
    'name': [worksheet_name, 0, 0],
    'log_base': 10
  })
  chart.set_y_axis({
    'name': [worksheet_name, 0, 1],
    'log_base': 10
  })
  chart.set_size({'x_scale': 2, 'y_scale': 2})
  chart.set_legend({'none': True})
  worksheet.insert_chart('C1', chart)

def add_percent_chart(workbook, worksheet_name, xlabel, ylabel, data, title, fixed_total = None, comments = None):
  # worksheet: slice size histogram
  worksheet = workbook.add_worksheet(worksheet_name)
  current_row = 0

  # data
  worksheet.write(current_row, 0, xlabel)
  worksheet.write(current_row, 1, "%s (%%)" % ylabel)
  current_row += 1
  for k, v in data:
    worksheet.write(current_row, 0, k)

    if comments is not None:
      if k not in comments:
        continue

      worksheet.write_comment(current_row, 0, comments[k]['name'])

    if fixed_total is None:
      worksheet.write(current_row, 1, v['n'])
      worksheet.write(current_row, 2, v['total'])
    else:
      worksheet.write(current_row, 1, v)
      worksheet.write(current_row, 2, fixed_total)

    worksheet.write(current_row, 3, '=B%d/C%d*100' % (current_row+1, current_row+1))
    current_row += 1

  # chart
  chart = workbook.add_chart({'type': 'column'})#, 'subtype': 'stacked'})
  chart.add_series({
    # sheet name, first row, first col, last row, last col
    'categories': [worksheet_name, 1, 0, current_row-1, 0],
    'values': [worksheet_name, 1, 3, current_row-1, 3]
  })
  # chart.add_series({
  #   # sheet name, first row, first col, last row, last col
  #   'categories': [worksheet_name, 1, 0, current_row-1, 0],
  #   'values': [worksheet_name, 1, 2, current_row-1, 2]
  # })
  chart.set_title({'name': title})
  chart.set_x_axis({
    'name': [worksheet_name, 0, 0]
  })
  chart.set_y_axis({
    'name': [worksheet_name, 0, 1]
  })
  chart.set_size({'x_scale': 2, 'y_scale': 2})
  chart.set_legend({'none': True})
  worksheet.insert_chart('E1', chart)

def add_stacked_chart(workbook, worksheet_name, xlabel, ylabel, data, title, ylog = True, xlog = True, label1 = "", label2 = ""):
  # worksheet: slice size histogram
  worksheet = workbook.add_worksheet(worksheet_name)
  current_row = 0

  # data
  worksheet.write(current_row, 0, xlabel)
  worksheet.write(current_row, 1, label1)
  worksheet.write(current_row, 2, label2)
  worksheet.write(current_row, 3, "total")
  worksheet.write(current_row, 4, ylabel)
  current_row += 1
  for k, v in data[0].items():
    worksheet.write(current_row, 0, k)
    worksheet.write(current_row, 1, v - data[1][k])
    worksheet.write(current_row, 2, data[1][k])
    worksheet.write(current_row, 3, v)
    current_row += 1

  # chart
  chart = workbook.add_chart({'type': 'column', 'subtype': 'stacked'})
  chart.add_series({
    # sheet name, first row, first col, last row, last col
    'categories': [worksheet_name, 1, 0, current_row-1, 0],
    'values': [worksheet_name, 1, 1, current_row-1, 1],
    'name': label1
  })
  chart.add_series({
    # sheet name, first row, first col, last row, last col
    'categories': [worksheet_name, 1, 0, current_row-1, 0],
    'values': [worksheet_name, 1, 2, current_row-1, 2],
    'name': label2
  })
  chart.set_title({'name': title})
  if xlog:
    chart.set_x_axis({
      'name': [worksheet_name, 0, 0],
      'log_base': 10
    })
  else:
    chart.set_x_axis({'name': [worksheet_name, 0, 0]})
  if ylog:
    chart.set_y_axis({
      'name': [worksheet_name, 0, 4],
      'log_base': 10
    })
  else:
    chart.set_y_axis({'name': [worksheet_name, 0, 4]})
  chart.set_size({'x_scale': 2, 'y_scale': 2})
  chart.set_legend({'position': 'bottom'})
  worksheet.insert_chart('E1', chart)

def add_scatter_xy(workbook, worksheet_name, x_data, y_data, point_labels, label_comments):
  worksheet = create_or_get_worksheet(workbook, worksheet_name)

  # write data
  for i in range(0, len(point_labels)):
    worksheet.write(i, 0, point_labels[i])
    worksheet.write_comment(i, 0, label_comments[i])

  worksheet.write_column(0, 1, x_data)
  worksheet.write_column(0, 2, y_data)

  # create chart
  chart = workbook.add_chart({'type': 'scatter'})

  chart.add_series({
    'name': 'DATA',
    'categories': [worksheet_name, 0, 1, len(x_data)-1, 1],
    'values': [worksheet_name, 0, 2, len(y_data)-1, 2]
  })

  chart.set_y_axis({
    'name': 'fraction',
    'min': 0,
    'max': 1
  })

  chart.set_size({'x_scale': 2, 'y_scale': 2})
  chart.set_legend({'none': True})

  # add chart to the worksheet
  worksheet.insert_chart(0, 3, chart)

def add_scatter(workbook, worksheet_name, series):
  worksheet = create_or_get_worksheet(workbook, worksheet_name)

  chart = workbook.add_chart({'type': 'scatter'})

  for data in series:
    chart.add_series(data)

  chart.set_x_axis({
    'name': 'function size (blocks)',
    'log_base': 10
  })
  chart.set_y_axis({
    'name': 'fraction',
    'min': 0,
    'max': 1
  })

  chart.set_size({'x_scale': 4, 'y_scale': 2.25})

  worksheet.insert_chart('A1', chart)

def add_column_chart(workbook, worksheet_name, series, series_labels, categories, delta = True, title = None, start_row = 0, start_column = 0, delta_subtract=False, datagenerator=None, xlabel=None, ylabel=None, debug=False):
  worksheet = create_or_get_worksheet(workbook, worksheet_name)

  chart = workbook.add_chart({'type': 'column'})

  worksheet.write_column(start_row+1, start_column+0, categories)
  worksheet.write_row(start_row+0, start_column+1, series_labels)

  # data
  current_column = start_column+1
  series_index = 0
  for i in series_labels:
    if datagenerator is None:
      worksheet.write_column(start_row+1, current_column, series[series_index])
    else:
      datagenerator(worksheet, i, start_row+1, current_column)

    if not delta:
      chart.add_series({
        'name': [worksheet_name, start_row+0, current_column],
        'values': [worksheet_name, start_row+1, current_column, start_row+len(categories), current_column],
        'categories': [worksheet_name, start_row+1, start_column+0, start_row+len(categories), start_column+0]
      })

    current_column += 1
    series_index += 1

  if delta:
    assert len(series) == 2

    if delta_subtract:
      worksheet.write(start_row+0, current_column, 'delta')
    else:
      worksheet.write(start_row+0, current_column, 'delta (%)')

    m = -100
    M = 100

    for i in range(0, len(series[0])):
      current_row = start_row+1+i

      beforecell = xlsxwriter.utility.xl_rowcol_to_cell(current_row, current_column-2)
      aftercell = xlsxwriter.utility.xl_rowcol_to_cell(current_row, current_column-1)

      value = 0
      if delta_subtract:
        worksheet.write(current_row, current_column, '=%s-%s' % (aftercell, beforecell))
        value = series[1][i] - series[0][i]
      else:
        worksheet.write(current_row, current_column, '=(%s-%s)/%s*100' % (aftercell, beforecell, beforecell))
        value = (series[1][i] - series[0][i])/series[0][i] *100

      if value > M:
        M = math.ceil(value)
      if value < m:
        m = math.floor(value)

    chart.add_series({
      'name': [worksheet_name, start_row+0, current_column],
      'values': [worksheet_name, start_row+1, current_column, start_row+len(series[0]), current_column],
      'categories': [worksheet_name, start_row+1, start_column+0, start_row+len(series[0]), start_column+0]
    })

    chart.set_y_axis({
      'name': [worksheet_name, start_row+0, current_column],
      'min': m,
      'max': M
    })

    current_column += 1

    chart.set_legend({'none': True})

  if title is None:
    chart.set_title({'none': True})
  else:
    chart.set_title({'name': title})

  if xlabel is not None:
    chart.set_x_axis({'name': xlabel})
  if ylabel is not None:
   chart.set_y_axis({'name': ylabel})

  worksheet.insert_chart(start_row+0, current_column, chart)

  return start_row + 1 + len(series[0])

def add_column_chart_cats(workbook, worksheet_name, data, title, xlabel, ylabel):
  series = []
  name_to_index = {}
  labels = []
  names = []

  for k, v in data.items():
    labels.append(k)

    for name, value in v.items():
      series_index = -1
      if name not in name_to_index:
        name_to_index[name] = len(series)
        series_index = len(series)
        series.append([])
        names.append(name)
      else:
        series_index = name_to_index[name]

      series[series_index].append(value)

  add_column_chart(workbook, worksheet_name, series, names, labels, title=title, delta=False, xlabel=xlabel, ylabel=ylabel)

def csv_to_worksheet(filename, workbook, separator=',', name=None):
  pass
  # sheetname = name
  # if name is None:
  #   sheetname = os.path.basename(filename)

  # assert len(sheetname) <= 31, "sheet name too long: %s (%d, max 31)" % (sheetname, len(sheetname))
  # worksheet = workbook.add_worksheet(sheetname)
  # #worksheet = create_or_get_worksheet(workbook, sheetname)
  # current_row = 0

  # print("reading to CSV %s" % (filename))
  # for line in open(filename):
  #   data = [for x in ]
  #   worksheet.write_row(current_row, 0, line.strip().split(separator))
  #   current_row += 1
