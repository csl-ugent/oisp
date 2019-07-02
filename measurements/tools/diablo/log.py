import os
import re

import lib.textualcfg as textualcfg
import tools.diablo.origintracking as origintracking
import tools.diablo.boutlist as boutlist

DISPATCHER_INDIRECT_BRANCH = 0
DISPATCHER_BRANCH_SWITCH = 1
DISPATCHER_OFFSET_SWITCH = 2
DISPATCHER_DYNAMIC_SWITCH = 3
DISPATCHER_CONDITIONAL_BRANCH = 4

def readAFTransformationIDs(filename):
    result = set()
    line_pattern = re.compile(r"^([0-9]+),AdvancedFactoring")

    if not os.path.isfile(filename):
        print("WARNING file not found %s, skipping" % (filename))

    else:
        print("reading %s" % (filename))
        for line in open(filename):
            line = line.strip()

            matches = line_pattern.match(line)
            if not matches:
                continue

            tf_id = int(matches.group(1))
            result.add(tf_id)

    return sorted(result)

def readFactoredInstructionLog(filename):
    result = {}

    ins_pattern = re.compile(r"^(0x[0-9a-f]+).*")

    for tokens in ReadFileTokens(filename):
        if tokens[0] == '':
            continue

        uid = int(tokens[0])
        reason = tokens[1]

        if reason == "FACTORED":
            slice_id = int(tokens[2])
            # skip AF_PHASE
            executed = bool(int(tokens[4]) == 1)

            matches = ins_pattern.match(':'.join(tokens[5:]))
            assert matches, "instruction >%s< not matched" % (tokens[5:])

            ins_address = int(matches.group(1), 16)

            result[ins_address] = {
                'transformation': uid,
                'slice': slice_id,
                'executed': executed
            }

    return result

# transformation logging
def readFactoringLog(filename):
  result = {}

  print("reading %s" % (filename))
  for line in open(filename):
    if line[0] == '#':
      continue
    tokens = line.strip().split(',')

    tf_uid = int(tokens[0])
    result[tf_uid] = {}

    result[tf_uid] = {
      'type': tokens[2],

      'archives': int(tokens[-10]),
      'objects': int(tokens[-9]),
      'functions': int(tokens[-8]),
      'slices': int(tokens[-12]),

      'exec_archives': int(tokens[-7]),
      'exec_objects': int(tokens[-6]),
      'exec_functions': int(tokens[-5]),
      'exec_slices': int(tokens[-11]),

      'added_insns_static': int(tokens[-4]),
      'added_data_static': int(tokens[-3]),
      'added_insns_dynamic': int(tokens[-2]),
      'factored_insns': int(tokens[-1]),

      'slice_size': int(tokens[4])
    }

  slice_size_to_exec = {}
  set_size_to_exec = {}
  covered_archives_to_exec = {}
  covered_objects_to_exec = {}
  covered_functions_to_exec = {}
  for _, v in result.items():
    slice_size = v['slice_size']
    set_size = v['slices']
    nr_exec_slices = v['exec_slices']
    covered_archives = v['archives']
    covered_objects = v['objects']
    covered_functions = v['functions']

    if slice_size not in slice_size_to_exec:
      slice_size_to_exec[slice_size] = 0
    slice_size_to_exec[slice_size] += nr_exec_slices

    if nr_exec_slices > 0:
      if set_size not in set_size_to_exec:
        set_size_to_exec[set_size] = 0
      set_size_to_exec[set_size] += 1

      if covered_archives not in covered_archives_to_exec:
        covered_archives_to_exec[covered_archives] = 0
      covered_archives_to_exec[covered_archives] += 1

      if covered_objects not in covered_objects_to_exec:
        covered_objects_to_exec[covered_objects] = 0
      covered_objects_to_exec[covered_objects] += 1

      if covered_functions not in covered_functions_to_exec:
        covered_functions_to_exec[covered_functions] = 0
      covered_functions_to_exec[covered_functions] += 1

  return {'raw': result, 'length2x': slice_size_to_exec, 'set2x': set_size_to_exec, 'a2x': covered_archives_to_exec, 'o2x': covered_objects_to_exec, 'f2x': covered_functions_to_exec}

def readFactoringInstructions(filename):
  factored_insns = {}
  transformations = {}

  if not os.path.isfile(filename):
      print("WARNING file not found %s, skipping" % (filename))

  else:
    print("reading %s" % (filename))
    for line in open(filename):
      if line[0] == '#':
        continue
      tokens = line.strip().split(':')

      tag = None
      if tokens[1] == 'FACTORED':
        tag = 'slice'
      elif tokens[1] == 'FACTOREDPRE':
        tag = 'pre'
      elif tokens[1] == 'FACTOREDPOST':
        tag = 'post'
      elif tokens[1].startswith('MERGED_DISPATCHER_'):
        # don't set the tag, but instead get the dispatcher type
        dispatcher_type = None

        if tokens[1] == 'MERGED_DISPATCHER_IB':
          dispatcher_type = DISPATCHER_INDIRECT_BRANCH
        elif tokens[1] == 'MERGED_DISPATCHER_DTBL':
          dispatcher_type = DISPATCHER_DYNAMIC_SWITCH
        elif tokens[1] == 'MERGED_DISPATCHER_ICONDJP':
          dispatcher_type = DISPATCHER_CONDITIONAL_BRANCH
        elif tokens[1] == 'MERGED_DISPATCHER_SWB':
          dispatcher_type = DISPATCHER_BRANCH_SWITCH
        elif tokens[1] == 'MERGED_DISPATCHER_SWO':
          dispatcher_type = DISPATCHER_OFFSET_SWITCH
        elif tokens[1] == 'MERGED_DISPATCHER_SWDEFAULTB' or tokens[1] == 'MERGED_DISPATCHER_SWDATA' or tokens[1] == 'MERGED_DISPATCHER_SWINF':
          dispatcher_type = None
        else:
          assert False, line

        if dispatcher_type is not None:
          tf_uid = int(tokens[0])
          if tf_uid not in transformations:
            transformations[tf_uid] = {'slices': {}, 'type': None}
          transformations[tf_uid]['type'] = dispatcher_type
        #endif
      #endif

      if tag is not None:
        tf_uid = int(tokens[0])
        slice_nr = int(tokens[2])

        instr_tokens = tokens[5].split(' ')
        if instr_tokens[0] == 'New':
          address = int(instr_tokens[6], 16)
        else:
          address = int(instr_tokens[0], 16)

        factored_insns[address] = {'tf_uid': tf_uid}

        if tf_uid not in transformations:
          transformations[tf_uid] = {'slices': {}, 'type': None}
        if slice_nr not in transformations[tf_uid]['slices']:
          transformations[tf_uid]['slices'][slice_nr] = {
            'slice': set(),
            'pre': set(),
            'post': set()
          }

        transformations[tf_uid]['slices'][slice_nr][tag].add(address)
      #endif tag

  return {'factored': factored_insns, 'transformations': transformations}

def readFactoringStatistics(filename):
  result = {}

  print("reading %s" % (filename))
  for line in open(filename):
    if line[0] == '#':
      continue
    tokens = line.strip().split(':')

    if len(tokens) == 3:
      # histogram name:x:n
      name = tokens[0]
      x = int(tokens[1])
      n = int(tokens[2])

      assert name.startswith("hist_")

      if name not in result:
        result[name] = {}
      result[name][x] = n

    elif len(tokens) == 2:
      # value:number
      name = tokens[0]
      value = int(tokens[1])

      assert name not in result

      result[name] = value

    elif len(tokens) == 4:
      # name:uid:n_factored:n_total
      lname = tokens[0]
      uid = int(tokens[1])
      n_factored = int(tokens[2])
      n_total = int(tokens[3])

      assert lname.endswith("_factored_total_insns")
      # only keep the first part
      name = lname.split('_')[0]

      if name not in result:
        result[name] = {}
      result[name][uid] = {'n': n_factored, 'total': n_total}

    else:
      assert False

  return result

def readObfuscationLog(filename):
  result = {}

  print("reading %s" % (filename))
  for line in open(filename):
    if line[0] == '#':
        continue
    tokens = line.strip().split(',')

    tf_uid = int(tokens[0])
    result[tf_uid] = {}

    result[tf_uid] = {
      'type': tokens[2],
      'address': tokens[3],
      'function': tokens[4],
      'name': tokens[5],

      'added_insns_static': int(tokens[6]),
      'added_data_static': int(tokens[7]),
      'added_insns_dynamic': int(tokens[8])
    }

  return result

# static complexity
def readStaticComplexity(filename):
  result = {}

  print("reading %s" % (filename))
  for line in open(filename):
    if line[0] == '#':
        continue

    tokens = line.strip().split(',')

    data = {}
    data['nr_ins'] = int(tokens[1])
    data['nr_src_oper'] = int(tokens[2])
    data['nr_dst_oper'] = int(tokens[3])
    data['halstead'] = int(tokens[4])
    data['nr_edges'] = int(tokens[5])
    data['cfim'] = int(tokens[6])
    data['cyclomatic'] = int(tokens[7])

    result[int(tokens[0])] = data

  return result

# dynamic complexity
def readDynamicComplexity(filename):
  result = {}

  print("reading %s" % (filename))
  for line in open(filename):
    if line[0] == '#':
        continue

    tokens = line.strip().split(',')

    trace = {}
    trace['nr_ins'] = int(tokens[1])
    trace['nr_src_oper'] = int(tokens[2])
    trace['nr_dst_oper'] = int(tokens[3])
    trace['halstead'] = int(tokens[4])
    trace['nr_edges'] = int(tokens[5])
    trace['cfim'] = int(tokens[6])

    coverage = {}
    coverage['nr_ins'] = int(tokens[7])
    coverage['nr_src_oper'] = int(tokens[8])
    coverage['nr_dst_oper'] = int(tokens[9])
    coverage['halstead'] = int(tokens[10])
    coverage['nr_edges'] = int(tokens[11])
    coverage['cfim'] = int(tokens[12])
    coverage['cyclomatic'] = int(tokens[13])

    result[int(tokens[0])] = {'trace': trace, 'coverage': coverage}

  return result

def readDiabloFiles(basename, outfilebase):
    i = textualcfg.readInstructions(basename + ".instructions")
    e = textualcfg.readEdges(basename + ".edges")
    b = textualcfg.readBasicBlocks(basename + ".bbls", e)
    f = textualcfg.readFunctions(basename + ".functions")

    o = origintracking.readObjects(basename + ".objectfiles")
    a = origintracking.readArchives(basename + ".archives")
    s = origintracking.readPartitions(basename + ".partitions")
    c = origintracking.readSCCs(basename + ".sccs")

    l = boutlist.readDiabloListing(outfilebase + ".list")
    k = boutlist.readDiabloKilledList(outfilebase + ".killed")
    t_af = readAFTransformationIDs(outfilebase + ".advanced_factoring.log")
    slices_af = readFactoringInstructions(outfilebase + ".advanced_factoring.log.instructions")

    return i, b, f, o, a, s, c, e, l, k, t_af, slices_af
