#!/usr/bin/env python
import common

import xlsxwriter

import measure.xlsx as xlsx

data = {'gt_edge_count': 319550, 'gt_fake_edge_count': 49812, 'functionless': 358382, 'false_positives_gui': 30015, 'false_positives_gui_inter_archive': 12898, 'false_positives_gui_inter_object': 20538, 'false_positives_gui_inter_function': 20713, 'false_positives_gui_intra_archive': 17117, 'false_positives_gui_intra_object': 9477, 'false_positives_gui_intra_function': 9302, 'false_positives_api': 40106, 'false_positives_api_inter_archive': 18594, 'false_positives_api_inter_object': 29850, 'false_positives_api_inter_function': 30083, 'false_positives_api_intra_archive': 21512, 'false_positives_api_intra_object': 10256, 'false_positives_api_intra_function': 10023, 'false_negatives_gui': 152585, 'false_negatives_gui_inter_archive': 1, 'false_negatives_gui_inter_object': 231, 'false_negatives_gui_inter_function': 687, 'false_negatives_gui_intra_archive': 152584, 'false_negatives_gui_intra_object': 152354, 'false_negatives_gui_intra_function': 151898, 'false_negatives_api': 98000, 'false_negatives_api_inter_archive': 1, 'false_negatives_api_inter_object': 133, 'false_negatives_api_inter_function': 475, 'false_negatives_api_intra_archive': 97999, 'false_negatives_api_intra_object': 97867, 'false_negatives_api_intra_function': 97525, 'false_negatives_gui_mapped': 20003, 'false_negatives_gui_mapped_to_dispatcher': 34370, 'false_negatives_gui_mapped_from_dispatcher': 212, 'false_negatives_gui_mapped_switch': 141, 'false_negatives_callfallthrough': 771, 'false_negatives_callfallthrough_from_data': 7, 'false_negatives_callfallthrough_to_data': 0, 'false_negatives_callfallthrough_fromto_data': 478, 'false_negatives_callfallthrough_to_dispatcher': 0, 'false_negatives_callfallthrough_from_dispatcher': 0, 'false_negatives_fallthrough': 15266, 'false_negatives_fallthrough_from_data': 695, 'false_negatives_fallthrough_to_data': 1, 'false_negatives_fallthrough_fromto_data': 2235, 'false_negatives_fallthrough_to_dispatcher': 3379, 'false_negatives_fallthrough_from_dispatcher': 107, 'false_negatives_jump': 22420, 'false_negatives_jump_from_data': 1569, 'false_negatives_jump_to_data': 1573, 'false_negatives_jump_fromto_data': 117, 'false_negatives_jump_to_dispatcher': 14091, 'false_negatives_jump_from_dispatcher': 41966, 'tuples_both_hanging': 3800, 'tuples_one_hanging': 13048, 'tuples_both_other': 12294, 'tuples_both_same': 2020}

outfile='test.xlsx'
sheetname='testsheet'

workbook = xlsxwriter.Workbook(outfile)

worksheet = xlsx.create_or_get_worksheet(workbook, sheetname)

# labels
worksheet.write_column(1, 0, ['false positives (GUI)', '', 'false positives (API)', '', 'false negatives (GUI)', '', 'false negatives (API)', '', 'all edge count', 'false edge count', 'true edge count', 'functionless instructions', 'links'])
worksheet.write_row(0, 1, ['Total', 'inter-A', 'inter-O', 'inter-F', 'intra-A', 'intra-O', 'intra-F'])

crow = 1
ccol = 1

# false positives (GUI)
worksheet.write_row(crow, ccol, [data['false_positives_gui'], data['false_positives_gui_inter_archive'], data['false_positives_gui_inter_object'], data['false_positives_gui_inter_function'], data['false_positives_gui_intra_archive'], data['false_positives_gui_intra_object'], data['false_positives_gui_intra_function']])
crow += 1
formulas = []
for i in range(7):
  formulas.append('=%s/%s' % (xlsxwriter.utility.xl_rowcol_to_cell(crow-1, 1+i), xlsxwriter.utility.xl_rowcol_to_cell(10, 1)))
#endfor
worksheet.write_row(crow, 1, formulas)
crow += 1

# false positives (API)
worksheet.write_row(crow, 1, [data['false_positives_api'], data['false_positives_gui_inter_archive'], data['false_positives_gui_inter_object'], data['false_positives_gui_inter_function'], data['false_positives_gui_intra_archive'], data['false_positives_gui_intra_object'], data['false_positives_gui_intra_function']])
crow += 1
formulas = []
for i in range(7):
  formulas.append('=%s/%s' % (xlsxwriter.utility.xl_rowcol_to_cell(crow-1, 1+i), xlsxwriter.utility.xl_rowcol_to_cell(10, 1)))
#endfor
worksheet.write_row(crow, 1, formulas)
crow += 1

# false negatives (GUI)
worksheet.write_row(crow, 1, [data['false_negatives_gui'], data['false_negatives_gui_inter_archive'], data['false_negatives_gui_inter_object'], data['false_negatives_gui_inter_function'], data['false_negatives_gui_intra_archive'], data['false_negatives_gui_intra_object'], data['false_negatives_gui_intra_function']])
crow += 1
formulas = []
for i in range(7):
  formulas.append('=%s/%s' % (xlsxwriter.utility.xl_rowcol_to_cell(crow-1, 1+i), xlsxwriter.utility.xl_rowcol_to_cell(11, 1)))
#endfor
worksheet.write_row(crow, 1, formulas)
crow += 1

# false negatives (API)
worksheet.write_row(crow, 1, [data['false_negatives_api'], data['false_negatives_api_inter_archive'], data['false_negatives_api_inter_object'], data['false_negatives_api_inter_function'], data['false_negatives_api_intra_archive'], data['false_negatives_api_intra_object'], data['false_negatives_api_intra_function']])
crow += 1
formulas = []
for i in range(7):
  formulas.append('=%s/%s' % (xlsxwriter.utility.xl_rowcol_to_cell(crow-1, 1+i), xlsxwriter.utility.xl_rowcol_to_cell(11, 1)))
#endfor
worksheet.write_row(crow, 1, formulas)
crow += 1

# counts
worksheet.merge_range(crow, 1, crow, 7, data['gt_edge_count'])
crow += 1
worksheet.merge_range(crow, 1, crow, 7, data['gt_fake_edge_count'])
crow += 1
worksheet.merge_range(crow, 1, crow, 7, '=%s-%s' % (xlsxwriter.utility.xl_rowcol_to_cell(crow-2, 1), xlsxwriter.utility.xl_rowcol_to_cell(10, 1)))
crow += 1

# instructions
worksheet.write(crow, 1, data['functionless'])
#TODO: write total nr of instructions
worksheet.write(crow, 3, '=%s/%s' % (xlsxwriter.utility.xl_rowcol_to_cell(crow, 1), xlsxwriter.utility.xl_rowcol_to_cell(crow, 2)))
crow += 1

# links
worksheet.write_row(crow, 1, ['bt. h', 'one h', 'broken', 'fixed', 'total'])
crow += 1
worksheet.write_row(crow, 1, [data['tuples_both_hanging'], data['tuples_one_hanging'], data['tuples_both_other'], data['tuples_both_same']])
worksheet.write(crow, 5, '=_xlfn.SUM(%s:%s)' % (xlsxwriter.utility.xl_rowcol_to_cell(crow, 1), xlsxwriter.utility.xl_rowcol_to_cell(crow, 4)))
crow += 1
formulas = []
for i in range(4):
  formulas.append('=%s/%s' % (xlsxwriter.utility.xl_rowcol_to_cell(crow-1, 1+i), xlsxwriter.utility.xl_rowcol_to_cell(crow-1, 5)))
#endfor
worksheet.write_row(crow, 1, formulas)
crow += 1

workbook.close()