#!/usr/bin/env python
# ./generate-table.py [path to Diablo output]/compare-stripped-smart-noatk.log

import ast
import subprocess
import sys

logfile=sys.argv[1]

# get data
data = subprocess.check_output(['tail', '-1', logfile]).decode("utf-8")[0:-1]
real_data = ast.literal_eval(data)

# get number of total instructions
egrep = subprocess.Popen(['egrep', '-o', 'IdaPro.*Ins\\s+:\\s+[0-9]+\\s+total', logfile], stdout=subprocess.PIPE)
output = subprocess.check_output(('egrep', '-o', '[0-9]+'), stdin=egrep.stdout).decode("utf-8")[0:-1]
egrep.wait()
total_insns = ast.literal_eval(output)

# the real script
nr_t = real_data['gt_edge_count'] - real_data['gt_fake_edge_count']
nr_f = real_data['gt_fake_edge_count']
nr_p = real_data['tuples_both_hanging'] + real_data['tuples_one_hanging'] + real_data['tuples_both_other'] + real_data['tuples_both_same']
nr_g = real_data['false_positives_gui'] + (nr_t - real_data['false_negatives_gui'])

def percent(x, y):
    value = 0
    if y != 0:
        value = round(x/y * 100, 0)
    # return '\\perc\{%d\\%\}' % value
    return '\\perc{{%d\\%%}}' % value

def number(x):
    if x < 1000:
        return '%d' % x
    return '%.1fk' % (x/1000)

print("%", ' '.join(sys.argv))

# print(r"\begin{table*}[t]")
print(r"  \centering")
print(r"  \scriptsize")
print(r"  \begin{tabular}{|l|c|ccc|ccc|c|ccc|ccc|}")

print(r"    \cline{2-15}")
print(r"    \multicolumn{1}{l|}{} & \multicolumn{7}{|c|}{\textbf{FP/FN CFG edges drawn in GUI}} & \multicolumn{7}{|c|}{\textbf{FP/FN CFG edges stored in database}}\\")

print(r"    \cline{2-15}")
print(r"    \multicolumn{1}{l|}{} & \textbf{Total} & \textbf{IA} & \textbf{IO} & \textbf{IF} & \textbf{iA} & \textbf{iO} & \textbf{iF} & \textbf{Total} & \textbf{IA} & \textbf{IO} & \textbf{IF} & \textbf{iA} & \textbf{iO} & \textbf{iF}\\")
print(r"    \cline{1-15}")

print( '    \\textbf{{\\# FP}} & {fp_T} & {fp_IA} & {fp_IO} & {fp_IF} & {fp_iA} & {fp_iO} & {fp_iF} & {fp_T2} & {fp_IA2} & {fp_IO2} & {fp_IF2} & {fp_iA2} & {fp_iO2} & {fp_iF2}\\\\'.format(fp_T=number(real_data['false_positives_gui']), fp_IA=number(real_data['false_positives_gui_inter_archive']), fp_IO=number(real_data['false_positives_gui_inter_object']), fp_IF=number(real_data['false_positives_gui_inter_function']), fp_iA=number(real_data['false_positives_gui_intra_archive']), fp_iO=number(real_data['false_positives_gui_intra_object']), fp_iF=number(real_data['false_positives_gui_intra_function']), fp_T2=number(real_data['false_positives_api']), fp_IA2=number(real_data['false_positives_api_inter_archive']), fp_IO2=number(real_data['false_positives_api_inter_object']), fp_IF2=number(real_data['false_positives_api_inter_function']), fp_iA2=number(real_data['false_positives_api_intra_archive']), fp_iO2=number(real_data['false_positives_api_intra_object']), fp_iF2=number(real_data['false_positives_api_intra_function'])))
print( '    \\textbf{{\\perc{{FPR}}}} & {fp_T} & {fp_IA} & {fp_IO} & {fp_IF} & {fp_iA} & {fp_iO} & {fp_iF} & {fp_T2} & {fp_IA2} & {fp_IO2} & {fp_IF2} & {fp_iA2} & {fp_iO2} & {fp_iF2}\\\\'.format(fp_T=percent(real_data['false_positives_gui'], nr_f), fp_IA=percent(real_data['false_positives_gui_inter_archive'], nr_f), fp_IO=percent(real_data['false_positives_gui_inter_object'], nr_f), fp_IF=percent(real_data['false_positives_gui_inter_function'], nr_f), fp_iA=percent(real_data['false_positives_gui_intra_archive'], nr_f), fp_iO=percent(real_data['false_positives_gui_intra_object'], nr_f), fp_iF=percent(real_data['false_positives_gui_intra_function'], nr_f), fp_T2=percent(real_data['false_positives_api'], nr_f), fp_IA2=percent(real_data['false_positives_api_inter_archive'], nr_f), fp_IO2=percent(real_data['false_positives_api_inter_object'], nr_f), fp_IF2=percent(real_data['false_positives_api_inter_function'], nr_f), fp_iA2=percent(real_data['false_positives_api_intra_archive'], nr_f), fp_iO2=percent(real_data['false_positives_api_intra_object'], nr_f), fp_iF2=percent(real_data['false_positives_api_intra_function'], nr_f)))
print(r"    \cline{1-15}")

print( '    \\textbf{{\\# FN}} & {fn_T} & {fn_IA} & {fn_IO} & {fn_IF} & {fn_iA} & {fn_iO} & {fn_iF} & {fn_T2} & {fn_IA2} & {fn_IO2} & {fn_IF2} & {fn_iA2} & {fn_iO2} & {fn_iF2}\\\\'.format(fn_T=number(real_data['false_negatives_gui']), fn_IA=number(real_data['false_negatives_gui_inter_archive']), fn_IO=number(real_data['false_negatives_gui_inter_object']), fn_IF=number(real_data['false_negatives_gui_inter_function']), fn_iA=number(real_data['false_negatives_gui_intra_archive']), fn_iO=number(real_data['false_negatives_gui_intra_object']), fn_iF=number(real_data['false_negatives_gui_intra_function']), fn_T2=number(real_data['false_negatives_api']), fn_IA2=number(real_data['false_negatives_api_inter_archive']), fn_IO2=number(real_data['false_negatives_api_inter_object']), fn_IF2=number(real_data['false_negatives_api_inter_function']), fn_iA2=number(real_data['false_negatives_api_intra_archive']), fn_iO2=number(real_data['false_negatives_api_intra_object']), fn_iF2=number(real_data['false_negatives_api_intra_function'])))
print( '    \\textbf{{\\perc{{FNR}}}} & {fn_T} & {fn_IA} & {fn_IO} & {fn_IF} & {fn_iA} & {fn_iO} & {fn_iF} & {fn_T2} & {fn_IA2} & {fn_IO2} & {fn_IF2} & {fn_iA2} & {fn_iO2} & {fn_iF2}\\\\'.format(fn_T=percent(real_data['false_negatives_gui'], nr_t), fn_IA=percent(real_data['false_negatives_gui_inter_archive'], nr_t), fn_IO=percent(real_data['false_negatives_gui_inter_object'], nr_t), fn_IF=percent(real_data['false_negatives_gui_inter_function'], nr_t), fn_iA=percent(real_data['false_negatives_gui_intra_archive'], nr_t), fn_iO=percent(real_data['false_negatives_gui_intra_object'], nr_t), fn_iF=percent(real_data['false_negatives_gui_intra_function'], nr_t), fn_T2=percent(real_data['false_negatives_api'], nr_t), fn_IA2=percent(real_data['false_negatives_api_inter_archive'], nr_t), fn_IO2=percent(real_data['false_negatives_api_inter_object'], nr_t), fn_IF2=percent(real_data['false_negatives_api_inter_function'], nr_t), fn_iA2=percent(real_data['false_negatives_api_intra_archive'], nr_t), fn_iO2=percent(real_data['false_negatives_api_intra_object'], nr_t), fn_iF2=percent(real_data['false_negatives_api_intra_function'], nr_t)))
print(r"    \cline{1-15}")
print(r"  \end{tabular}")
print(r"")

print(r"  \vspace{1em}")

print(r"  \begin{tabular}{|c|cc|}")
print(r"    \hline")
print( '    \\multicolumn{{3}}{{|c|}}{{\\textbf{{Pairs of fragments split by factorization}}}}\\\\'.format())
print(r"    \hline")
print( '    Total & Wrong & Correct\\\\'.format())
print( '    {T} & {W} ({Wp}) & {C} ({Cp})\\\\'.format(T=number(nr_p), W=number(real_data['tuples_both_other']+real_data['tuples_both_hanging']+real_data['tuples_one_hanging']), Wp=percent((real_data['tuples_both_other']+real_data['tuples_both_hanging']+real_data['tuples_one_hanging']), nr_p), C=number(real_data['tuples_both_same']), Cp=percent(real_data['tuples_both_same'], nr_p)))
print(r"    \hline")
print(r"  \end{tabular}")

print(r"  \begin{tabular}{|c|cc|c|}")
print(r"    \hline")
print( '    \\multicolumn{{4}}{{|c|}}{{\\textbf{{CFG edges}}}}\\\\'.format())
print(r"    \hline")
print( '    Total & True & Fake & Drawn in GUI\\\\'.format())
print( '    {Te} & {te} ({tep}) & {fe} ({fep}) & {ge} ({gep})\\\\'.format(Te=number(real_data['gt_edge_count']), te=number(nr_t), tep=percent(nr_t, real_data['gt_edge_count']), fe=number(nr_f), fep=percent(nr_f, real_data['gt_edge_count']), ge=number(nr_g), gep=percent(nr_g, real_data['gt_edge_count'])))
print(r"    \hline")
print(r"  \end{tabular}")

print(r"  \begin{tabular}{|c|c|}")
print(r"    \hline")
print( '    \\multicolumn{{2}}{{|c|}}{{\\textbf{{Instructions}}}}\\\\'.format())
print(r"    \hline")
print( '    Total & Functionless\\\\'.format())
print( '    {Ti} & {fli} ({flip})\\\\'.format(Ti=number(total_insns), fli=number(real_data['functionless']), flip=percent(real_data['functionless'], total_insns)))
print(r"    \hline")
print(r"  \end{tabular}")

print(r"  \begin{tabular}{|c|c|}")
print(r"    \hline")
print( '    \\multicolumn{{2}}{{|c|}}{{\\textbf{{Opaque predicates}}}}\\\\'.format())
print(r"    \hline")
print( '    Total & Resolved\\\\'.format())
print( '    {T} & {E} ({Ep})\\\\'.format(T=number(real_data['nr_obfuscations']), E=number(real_data['nr_obfuscations_eliminated']), Ep=percent(real_data['nr_obfuscations_eliminated'], real_data['nr_obfuscations'])))
print(r"    \hline")
print(r"  \end{tabular}")

# print(r"  \caption{\tablecaption}")
# print(r"  \label{\tablelabel}")
# print(r"\end{table*}")
