import numpy
import matplotlib.pyplot as plt

colors = ['r', 'b', 'g', 'k', 'c', 'y', 'm']

def moving_average(values, window_size):
  weights = numpy.repeat(1, window_size)/window_size
  return numpy.convolve(values, weights, 'valid')

def weighted_mean(values, weights):
  weighted = []
  for index, x in enumerate(values):
    weighted.extend([x] * int(weights[index]))
  return sum(weighted)/len(weighted)

def hline(ax, value, fmt):
  if 'label' in fmt:
    ax.axhline(y=value, linestyle=fmt['style'], c=fmt['color'], label=fmt['label'])
  else:
    ax.axhline(y=value, linestyle=fmt['style'], c=fmt['color'])

def scatter_data(x, y, ax, weights, fmt, draw_mean=True, draw_moving=True):
  if draw_mean:
    # weighted mean
    weighted_mn = weighted_mean(y, weights)
    hfmt = fmt['mean']
    hfmt['style'] = '--'
    hline(ax, weighted_mn, hfmt)

    fmt['scatter']['label'] += ' (%.3f)' % weighted_mn

  # scatter plot with raw data
  ax.scatter(x, y, marker=fmt['scatter']['marker'], c=fmt['scatter']['color'], label=fmt['scatter']['label'])

  if draw_moving:
    # moving average
    moving_avg = moving_average(y, 4)
    ax.plot(x[len(x) - len(moving_avg):], moving_avg, linestyle='-', c=fmt['moving']['color'], label='Moving average')

def double_y_axis():
  fig, ax = plt.subplots()
  ax2 = ax.twinx()
  return fig, ax, ax2

def load_data(file):
  # skiprows: skip first row as that denotes column titles
  # delimiter: separator
  # unpack: 1 row in the data = 1 column in the file
  return numpy.loadtxt(file, skiprows=1, delimiter=',', unpack=True)
