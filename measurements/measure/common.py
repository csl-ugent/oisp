import importlib
import pathlib
import sys

def import_parents(level=1):
  global __package__
  file = pathlib.Path(__file__).resolve()
  parent, top = file.parent, file.parents[level]

  sys.path.append(str(top))
  try:
    sys.path.remove(str(parent))
  except ValueError: # already removed
     pass

  __package__ = '.'.join(parent.parts[len(top.parts):])
  importlib.import_module(__package__) # won't be needed after that
import_parents(level=1)

executed = False
output_basename = ""
smart_attacker = False
prioritize_ft = 0
db_attack = False

def SortedDictionaryIterator(dct):
  for key in sorted(dct):
    yield key, dct[key]
