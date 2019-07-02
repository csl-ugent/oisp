import measure.xlsx as xlsx

def generate_sheet(workbook, sheetname, data):
  worksheet = xlsx.create_or_get_worksheet(workbook, sheetname)

  data_sorted = sorted(data.items(), key=lambda t: t[1]['added_insns_dynamic'], reverse=True)

  row_data = ['UID', 'type', 'added_insns_static', 'added_insns_dynamic', 'added_data_static']
  worksheet.write_row(0, 0, row_data)

  current_row = 1
  for k, v in data_sorted:
    row_data = [k, v['type'], v['added_insns_static'], v['added_insns_dynamic'], v['added_data_static']]
    worksheet.write_row(current_row, 0, row_data)
    current_row += 1
