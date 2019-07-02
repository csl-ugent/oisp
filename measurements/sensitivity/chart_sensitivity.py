#!/usr/bin/env python

# loop IDA:
# for x in $(find /storage/measurements/diamante/sensitivity/orderseed-*/b.out); do ./run_ida.sh $x; done

# loop compare:
# for x in $(find /storage/measurements/diamante/sensitivity/cluster-*/b.out); do ./compare.py -b $x -o final > $x.compare.log; ./compare.py -b $x -o final -s "-smart" -S > $x.compare-smart.log; done

# graph commands:
# ./graphs/commands.sh '/storage/measurements/diamante/sensitivity/orderseed-*/b.out'

import argparse
import os

from common import *
import generate_random_color

parser = argparse.ArgumentParser(description='Draw a chart.')
parser.add_argument('--input', nargs='+', type=str, default=[])
parser.add_argument('--outfile', action='store')
parser.add_argument('--title', action='store')
parser.add_argument('--column', type=int, default=5)

colors = []
color_index = 0

def boxplot(data, labels):
  plt.boxplot(data, whis='range', labels=labels, showmeans=True)

def single_file(file, F_scatter, F_box, max_fsize):
  global color_index
  all_data = load_data(file)

  # extract data
  function_sizes = all_data[0]
  counters = all_data[1]
  # fraction_drawn_fake = all_data[5]
  # fraction_drawn_fake_interlib = all_data[9]
  data_to_plot = all_data[args.column]

  label = os.path.basename(os.path.dirname(file))

  drawn_fake_format = {
    'scatter': {
      'marker': 'x',
      'color': colors[color_index],
      'label': label
    },
    'moving': {
      'color': 'green'
    },
    'mean': {
      'color': colors[color_index]
    }
  }

  plt.figure(F_scatter[0].number)
  scatter_data(function_sizes, data_to_plot, F_scatter[1], counters, drawn_fake_format, True, False)

  box_data = []
  for idx, val in enumerate(function_sizes):
    box_data.extend([val for i in range(int(counters[idx]))])
  box_label = label

  if max(function_sizes) > max_fsize:
    max_fsize = max(function_sizes)

  color_index += 1
  return max_fsize, box_data, box_label

def foo():
  # colors
  global colors
  colors = generate_random_color.generate_colors(len(args.input))

  fig, ax = plt.subplots()
  fig.set_size_inches(17.5, 9)

  fig2, ax2 = plt.subplots()

  max_fsize = 0
  all_box_data = []
  all_box_label = []
  for x in args.input:
    max_fsize, box_data, box_label = single_file(x, [fig, ax], [fig2, ax2], max_fsize)
    all_box_data.append(box_data)
    all_box_label.append(box_label)

  # FIGURE 1
  plt.figure(fig.number)

  # X-axis
  ax.set_xscale('log')
  ax.set_xlabel('input function size (# BBLs)')
  ax.set_xlim([1, max_fsize])

  # Y-axis
  ax.set_ylim([0, 1])
  ax.set_ylabel('Fraction')

  # text
  ax.legend()
  plt.title(args.title)

  # textbox with statistics
  # tbox = ''
  # tbox += 'GT: %d edges (%d fake)\n' % (81876, 10177)
  # tbox += 'False positives: %d/%d\n' % (7752, 10177)
  # tbox += 'False negatives: %d\n' % (12)
  # tbox += 'IDA instructions: %d (%d)\n' % (251966, 94)
  # tbox += 'GT instructions: %d\n' % (252476)
  # ax.text(0.01, 0.99, tbox, verticalalignment='top', transform=ax.transAxes, fontsize=14)

  # layout
  plt.tight_layout()
  plt.get_current_fig_manager().window.showMaximized()
  # ---

  # FIGURE 2
  plt.figure(fig2.number)
  boxplot(all_box_data, all_box_label)

  # Y-axis
  ax2.set_yscale('log')
  ax2.set_ylabel('function size (# BBLs)')
  ax2.set_ylim([1, max_fsize])

  # layout
  plt.tight_layout()
  plt.get_current_fig_manager().window.showMaximized()
  # ---

  plt.show()

args = parser.parse_args()
foo()
