#!/usr/bin/env python

import argparse
import matplotlib.pyplot as plt
import matplotlib.ticker as tck
import numpy

parser = argparse.ArgumentParser(description='Draw a bar-chart.')
parser.add_argument('--datafile', action='store')
parser.add_argument('--xlabel', action='store')
parser.add_argument('--ylabel', action='store')
parser.add_argument('--title', action='store')
parser.add_argument('--outfile', action='store')
parser.add_argument('--swap', action='store_true')

def plot_binned_data(file, xlabel, ylabel, title, outfile):
    # read the data
    columns=(1, 2)
    if args.swap:
        columns=(2, 1)

    xlabels, data = numpy.loadtxt(file, unpack=True, usecols=columns, delimiter=':', ndmin=2)

    # 'a' contains the bin indices
    # 'b' contains the bin values
    binwidth = 0.7

    _, ax = plt.subplots()

    # data
    #plt.bar(a, b, width=0.7, tick_label=a, align='center')
    bins = range(len(data))
    plt.bar(bins, data, width=binwidth, align='center', tick_label=xlabels)
    plt.xlim([min(bins)-binwidth, max(bins)+binwidth])

    # axis
    #ax.xaxis.set_major_formatter(tck.FormatStrFormatter('%d'))
    #ax.xaxis.set_minor_formatter(tck.FormatStrFormatter('%d'))
    ax.set_yscale('symlog')
    #ax.set_xscale('log')

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                 ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(10)

    # rotate X-labels 90 degrees
    _, labels = plt.xticks()
    plt.setp(labels, rotation=90)

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
