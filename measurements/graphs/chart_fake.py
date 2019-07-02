#!/usr/bin/env python

import argparse
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as tck
import numpy
import math

from common import *

parser = argparse.ArgumentParser(description='Draw a chart.')
parser.add_argument('--datafile', action='store')
parser.add_argument('--outfile', action='store')

def foo(file):
  all_data = load_data(file)

  # extract data
  function_sizes = all_data[0]
  counters = all_data[1]
  fraction_drawn_fake = all_data[5]
  fraction_drawn_fake_interlib = all_data[9]

  fig, ax, ax2 = double_y_axis()

  # Y-axis
  ax.set_ylim([0, 1])
  ax.set_ylabel('Fraction')

  # common X-axis
  ax.set_xscale('log')
  ax.set_xlabel('input function size (# BBLs)')
  ax.set_xlim([min(function_sizes), max(function_sizes)])

  drawn_fake_format = {
    'scatter': {
      'marker': 'x',
      'color': 'red',
      'label': 'Fraction drawn fake edges'
    },
    'moving': {
      'color': 'green'
    },
    'mean': {
      'color': 'brown'
    }
  }
  scatter_data(function_sizes, fraction_drawn_fake, ax, counters, drawn_fake_format)

  drawn_fake_interlib_format = {
    'scatter': {
      'marker': '.',
      'color': 'blue',
      'label': 'Fraction drawn interlibrary fake edges'
    },
    'moving': {
      'color': 'blue'
    },
    'mean': {
      'color': 'blue'
    }
  }
  scatter_data(function_sizes, fraction_drawn_fake_interlib, ax, counters, drawn_fake_interlib_format)

  # function size histogram
  # create histogram data
  hist_function_sizes = []
  for index, x in enumerate(function_sizes):
    hist_function_sizes.extend([x] * int(counters[index]))

  bins = list(function_sizes)
  bins.append(max(function_sizes) + 1)

  ax2.hist(x=hist_function_sizes, bins=bins, histtype='step', align='left', log=True, label='Function count')
  ax2.set_ylabel('Function count')

  ax.legend()
  ax2.legend()

  plt.title(file)
  fig.set_size_inches(17.5, 9)
  plt.tight_layout()

  if args.outfile is not None:
      plt.savefig(args.outfile)
  else:
      plt.show()

args = parser.parse_args()
foo(args.datafile)
