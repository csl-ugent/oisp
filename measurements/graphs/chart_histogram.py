#!/usr/bin/env python

import argparse
import matplotlib.pyplot as plt
import matplotlib.ticker as tck
import numpy
import math

parser = argparse.ArgumentParser(description='Draw a bar-chart.')
parser.add_argument('--datafile', action='store')
parser.add_argument('--xlabel', action='store')
parser.add_argument('--ylabel', action='store')
parser.add_argument('--title', action='store')
parser.add_argument('--outfile', action='store')
parser.add_argument('--swap', action='store_true')

def nearest_power_10_L(x):
  return math.pow(10, math.floor(math.log(x, 10)))

def nearest_power_10_H(x):
  return math.pow(10, math.ceil(math.log(x, 10)))

def plot_binned_data(file, xlabel, ylabel, title, outfile):
    # read the data
    columns=(1, 2)
    if args.swap:
        columns=(2, 1)

    xlabels, data = numpy.loadtxt(file, unpack=True, usecols=columns, delimiter=':', ndmin=2)

    # create suitable data for plotting a histogram
    hist_data = []
    for index, x in enumerate(xlabels):
      print("adding %d %d times" % (x, data[index]))
      hist_data.extend([x] * int(data[index]))

    _, ax = plt.subplots()

    lst = list(xlabels)
    lst.append(max(xlabels)+1)
    plt.hist(x=hist_data, bins=lst, histtype='step', align='left', cumulative=True)#, log=True
    plt.xlim([min(xlabels)-0.5, max(xlabels)+0.5])

    # y limits, take car for log axis!
    plt.ylim([nearest_power_10_L(data[0]), math.ceil(sum(data)/1000)*1000])

    # chart markup
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)

    # prevent clipping of ylabel
    plt.subplots_adjust(left=0.15)

    if args.outfile is not None:
        plt.savefig(outfile)
    else:
        plt.show()

args = parser.parse_args()
plot_binned_data(args.datafile, args.xlabel, args.ylabel, args.title, args.outfile)
