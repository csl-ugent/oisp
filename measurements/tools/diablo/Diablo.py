import pathlib
import subprocess
import re

import tools.diablo.log as DiabloLog
import tools.Tool as Tool
import tools.diablo.boutlist as DiabloList

class Diablo(Tool.Tool):
  # from diabloflowgraph_edge.h
  __ET_FALLTHROUGH = 1<<1
  __ET_CALL = 1<<2
  __ET_JUMP = 1<<5
  __ET_IPFALLTHRU = 1<<9
  __ET_IPJUMP = 1<<11
  __ET_SWITCH = 1<<14
  __ET_IPSWITCH = 1<<15

  # from diabloflowgraph_ins.h
  __IF_AF_INDEX_INSTRUCTION = 0x400000

  #
  __TFID_FLOWGRAPH = -1
  __TFID_DEFLOWGRAPH = -1

  __EDGE_FLAG_TO_AF_FUNCTION = 0x1
  __EDGE_FLAG_FROM_AF_FUNCTION = 0x2
  __EDGE_FLAG_INSIDE_AF_FUNCTION = __EDGE_FLAG_TO_AF_FUNCTION | __EDGE_FLAG_FROM_AF_FUNCTION
  __EDGE_FLAG_EXECUTED = 0x4

  def __init__(self, vanilla):
    super(Diablo, self).__init__("Diablo", vanilla)

    self._loaded = False
    self._objects = None
    self._archives = None
    self._partitions = None
    self._sccs = None
    self._listing = None
    self._killed = None

    self._af_tfids = None
    self._af_slices = None
    self._af_dispatchers = {}
    self._af_dispatchers_incoming_edges = set()
    self._af_dispatchers_outgoing_edges = set()
    self._af_index_instructions = {}
    self._af_splits = []
    self._af_splits_linked = {}

    self._unstripped_binary = None
    self._binary = None

    self._possible_function_entries = set()
    self._original_edge_type = {}
    self._plt_entries = {}
    self._plt_calls = {}

    self._good_links = {}
    self._bad_links = {}

    self._ignored_transformations = set()

    self._nr_obfuscations = 0

    # default value for measurements on Pegasus
    self._objdump_binary = "/bulk/A/diablo-toolchains/linux/gcc/arm/gcc-4.8.1/bin/arm-diablo-linux-gnueabi-objdump"

  def Load(self, logs, origin_logs):
    # binary
    self._binary = logs
    self.Print("loading %s" % self._binary)

    if not pathlib.Path(self._objdump_binary).is_file():
      self.Print("Assuming Dockerized run")
      self._objdump_binary = "/data/diablo-toolchains/linux/gcc/arm/gcc-4.8.1/bin/arm-diablo-linux-gnueabi-objdump"

    # collect unstripped binary
    self._unstripped_binary = self._binary
    if self._unstripped_binary.endswith(".stripped"):
      self._unstripped_binary = self._unstripped_binary.replace(".stripped", "")

    # name of list file
    f_list = self._unstripped_binary + ".list"
    if not pathlib.Path(f_list).is_file():
      self.Print("no Diablo information for %s, could not find list file %s" % (logs, f_list))
      return

    self._loaded = True

    self._instructions, self._bbls, self._functions, self._objects, self._archives, self._partitions, self._sccs, self._edges, self._listing, self._killed, self._af_tfids, self._af_slices = DiabloLog.readDiabloFiles(origin_logs, self._unstripped_binary)

    nr_executed_edges, nr_fake_edges = self.__UpdateEdgeInformation()
    self.__CollectFunctionEntryPoints()

    self.__CollectSliceInformation()

    if not self._vanilla:
      self.__CollectAFDispatchers()
      self.__CollectAFIndexInstructions()

    self.__FunctionSize()

    if not self._vanilla:
      self._CollectTransformationInformation(self)
      self.__CollectTransformationEntryExit()

    self.Print("INPUT STATISTICS")
    self.Print("  Ins      : %d total, %d functionless" % (self.InsCount(), self.InsCountNotInFunction()))
    self.Print("  Bbls     : %d total" % (self.BblCount()))
    self.Print("  Functions: %d total" % (self.FunctionCount()))
    self.Print("  Edges    : %d total, %d executed, %d fake" % (self.EdgeCount(), nr_executed_edges, nr_fake_edges))
    self.Print("  Transformations: %d total" % (self.TransformationCount()))
    self.Print("  Obfuscation count: %d total" % (self._nr_obfuscations))

  def __UpdateEdgeInformation(self):
    nr_executed_edges = 0
    nr_fake_edges = 0
    for uid, edge in self.EdgeIterator(True, False, False):
      edge_type = edge['type']
      translated_edge_type = edge_type

      # diabloflowgraph_edge.h ET_* preprocessor definitions
      self._original_edge_type[uid] = edge_type

      if edge_type == self.__ET_FALLTHROUGH or edge_type == self.__ET_IPFALLTHRU:
        translated_edge_type = Tool.EDGE_FALLTHROUGH
      elif edge_type == self.__ET_JUMP or edge_type == self.__ET_IPJUMP:
        translated_edge_type = Tool.EDGE_JUMP
      elif edge_type == self.__ET_CALL:
        translated_edge_type = Tool.EDGE_CALL
      elif edge_type == self.__ET_SWITCH or edge_type == self.__ET_IPSWITCH:
        translated_edge_type = Tool.EDGE_JUMP
      elif edge_type == -1:
        # special: fallthrough edge for call
        translated_edge_type = Tool.EDGE_CALLFALLTHROUGH
      else:
        assert False, "unsupported Diablo edge type %x" % (edge_type)

      self._edges['edges'][uid]['type'] = translated_edge_type

      # executed edge?
      executed = self.InsExecuted(edge['head']) and self.InsExecuted(edge['tail'])
      self._edges['edges'][uid]['executed'] = executed
      if executed:
        nr_executed_edges += 1

      # fake?
      if edge['fake']:
        nr_fake_edges += 1

    return nr_executed_edges, nr_fake_edges

  def __CollectSliceInformation(self):
    down = {}
    up = {}

    def link_down(a, b):
      if a not in down:
        down[a] = set()
      # print("link down 0x%x->0x%x" % (a, b))
      down[a].add(b)
    #enddef

    def unlink_down(x, target = None):
      result = set()
      if x not in down:
        return result

      if target == None:
        result = down[x]
        del down[x]
      else:
        down[x].remove(target)
      #endif

      return result
    #enddef

    def link_up(a, b):
      if a not in up:
        up[a] = set()
      # print("link up 0x%x->0x%x" % (a, b))
      up[a].add(b)
    #enddef

    def unlink_up(x, target = None):
      result = set()
      if x not in up:
        return result

      if target == None:
        result = up[x]
        del up[x]
      else:
        up[x].remove(target)
      #endif

      return result
    #enddef

    def fatal(condition, message = "(no message)"):
      if condition:
        return

      self.Print("Assertion failure: %s" % message)
      for k, v in down.items():
        self.Print("DOWN 0x%x: %s" % (k, ['0x%x' % i for i in v]))
      for k, v in up.items():
        self.Print("UP 0x%x: %s" % (k, ['0x%x' % i for i in v]))

      assert False, message
    #enddef fatal

    factored_insns = set()
    for tf_uid, tf_data in self._af_slices['transformations'].items():
      tf_slices = tf_data['slices']
      for slice_nr, slice_data in tf_slices.items():
        # print("TF%d SLICE%d ins(%s)" % (tf_uid, slice_nr, ['0x%x' % i for i in slice_data['slice']]))
        # print("TF%d SLICE%d pre(%s)" % (tf_uid, slice_nr, ['0x%x' % i for i in slice_data['pre']]))
        # print("TF%d SLICE%d pos(%s)" % (tf_uid, slice_nr, ['0x%x' % i for i in slice_data['post']]))
        # print(" ")

        assert len(slice_data['post'])<=1
        post_ins = None
        if len(slice_data['post']) == 1:
          post_ins = list(slice_data['post'])[0]

        for factored_ins in slice_data['slice']:
          # print("doing 0x%x" % factored_ins)
          factored_insns.add(factored_ins)

          for i in unlink_up(factored_ins):
            self.Print("unlinking 0x%x from 0x%x" % (i, factored_ins))
            unlink_down(i, factored_ins)

            if post_ins is not None:
              if post_ins in factored_insns:
                self.Print("WARNING 1 already factored post instruction 0x%x" % post_ins)

              link_down(i, post_ins)
              link_up(post_ins, i)
          #endfor

          for i in unlink_down(factored_ins):
            unlink_up(i, factored_ins)

            for pre_ins in slice_data['pre']:
              if pre_ins in factored_insns:
                # DIRTY HACK, should probably look at this in the future
                self.Print("WARNING 2 already factored pre instruction 0x%x" % pre_ins)
                continue
              link_down(pre_ins, i)
              link_up(i, pre_ins)
          #endfor
        #endfor

        # for each predecessor
        if post_ins is not None:
          for pre_ins in slice_data['pre']:
            if pre_ins in factored_insns:
              # DIRTY HACK, see higher
              self.Print("WARNING 3 already factored pre instruction 0x%x" % pre_ins)
              continue
            link_down(pre_ins, post_ins)
            link_up(post_ins, pre_ins)
        #endif post_ins
      #endfor tf_data
      # print("====================================================================================================")
    #endfor _af_slices

    # sanity checks and unique tuple collection
    # only collect tuples in one direction (UP is symmetrical to DOWN)
    self._af_splits = []
    for k, v in down.items():
      fatal(len(v & factored_insns) == 0, 'DOWN 0x%x' % k)
      for w in v:
        if k not in self._listing['old2new']:
          self.Print("WARNING source 0x%x does not exist" % k)
        elif w not in self._listing['old2new']:
          self.Print("WARNING sink 0x%x does not exist" % w)
        else:
          kstar = self._listing['old2new'][k]
          wstar = self._listing['old2new'][w]

          self._af_splits.append([kstar, wstar])

          if kstar not in self._af_splits_linked:
            self._af_splits_linked[kstar] = set()
          self._af_splits_linked[kstar].add(wstar)

          if wstar not in self._af_splits_linked:
            self._af_splits_linked[wstar] = set()
          self._af_splits_linked[wstar].add(kstar)
      #endfor
    #endfor

    # for k, v in up.items():
    #   fatal(len(v & factored_insns) == 0, 'UP 0x%x' % k)

    index = 0
    for a, b in self._af_splits:
      self.Print("%d: 0x%x-0x%x" % (index, a, b))
      index += 1
  #enddef __CollectSliceInformation

  def __CollectAFDispatchers(self):
    dispatcher_data = {}

    def record_edge(cat, insn, edge_uid):
      dispatcher_function_uid = self.InsFunction(insn)
      # print("processing edge %s: %d (%s)" % (self.EdgeToString(edge_uid), dispatcher_function_uid, cat))

      if dispatcher_function_uid not in dispatcher_data:
        dispatcher_data[dispatcher_function_uid] = {
          'start': set(),
          'end': set(),
          'incoming': set(), # set of incoming edge uids
          'outgoing': set(), # set of outgoing edge uids
        }
      #endif

      dispatcher_data[dispatcher_function_uid][cat].add(insn)
      if cat == 'start':
        dispatcher_data[dispatcher_function_uid]['incoming'].add(edge_uid)
      else:
        dispatcher_data[dispatcher_function_uid]['outgoing'].add(edge_uid)
    #enddef

    # don't do anything with vanilla applications
    if self._vanilla:
      return

    # iterate over the edges
    for edge_uid, edge in self.EdgeIterator():
      if self.EdgeIsFake(edge_uid):
        continue

      if (edge['flags'] & self.__EDGE_FLAG_INSIDE_AF_FUNCTION) == self.__EDGE_FLAG_INSIDE_AF_FUNCTION:
        # edge is entirely inside AF function
        if self.InsFunction(edge['branch']) != self.InsFunction(edge['tail']):
          # edge goes between two AF functions
          record_edge('start', edge['tail'], edge_uid)
          self._af_dispatchers_incoming_edges.add(edge_uid)
          record_edge('end', edge['branch'], edge_uid)
          self._af_dispatchers_outgoing_edges.add(edge_uid)
        #endif
      elif edge['flags'] & self.__EDGE_FLAG_TO_AF_FUNCTION:
        # edge goes to AF function
        record_edge('start', edge['tail'], edge_uid)
        self._af_dispatchers_incoming_edges.add(edge_uid)
      elif edge['flags'] & self.__EDGE_FLAG_FROM_AF_FUNCTION:
        # edge comes from AF function
        record_edge('end', edge['branch'], edge_uid)
        self._af_dispatchers_outgoing_edges.add(edge_uid)
      else:
        # neither flag is set
        continue
      #endif
    #endfor edges

    # collect information
    for _, v in dispatcher_data.items():
      assert len(v['start']) == 1, "unexpected %s" % ['0x%x' % i for i in v['start']]

      if len(v['end']) > 1:
        new_ends = set()
        for end_insn in v['end']:
          if not self.BblIsTrampoline(self.InsBbl(end_insn)):
            new_ends.add(end_insn)
          else:
            self.Print("remove trampoline 0x%x from list" % end_insn)
        #endfor
        v['end'] = new_ends
      #endif

      assert len(v['end']) == 1, "unexpected %s: %s" % (['0x%x' % i for i in v['end']], v)

      start_address = list(v['start'])[0]
      end_address = list(v['end'])[0]

      self._af_dispatchers[end_address] = {'entry': start_address, 'tf_uid': self._TransformationIdUID(self.InsTransformationID(end_address)), 'incoming': v['incoming'], 'outgoing': v['outgoing']}
    #endfor
  #enddef

  def __CollectAFIndexInstructions(self):
    # index instruction pairs
    self._index_instructions = {}
    for i in self.InsIterator():
      if not self.InsIsIndexSecondPart(i):
        continue
      # self.Print("second part %x" % i)

      # found the second part, need to look for the first part
      first_ins = None
      second_ins = i
      #print("looking for first part of 0x%x" % (second_ins))

      # find the first part
      block = self.InsBbl(i)

      while first_ins is None:
        pred_blocks = list(self.BblIncomingBbls(block, False))

        for incoming_block in pred_blocks:
          # search for the first part of the index instruction
          for j in self.BblInsIterator(incoming_block):
            if not self.InsIsIndexRelated(j):
              continue

            assert first_ins is None, "multiple index instructions! 0x%x 0x%x" % (first_ins, j)
            first_ins = j

        # the block chain may be broken by opaque predicates or other transformations
        block = pred_blocks[0]

      assert first_ins is not None, "first part not found for 0x%x" % (second_ins)
      #print("found index pair 0x%x-0x%x" % (first_ins, second_ins))
      self._index_instructions[first_ins] = second_ins

  def __FunctionSize(self):
    for _, bbl in self.BblIterator():
      f, _, _, _, _ = self.InsOrigin(bbl['address'])
      for f_uid in f:
        if 'nr_bbls' not in self._functions[f_uid]:
          self._functions[f_uid]['nr_bbls'] = 0
        self._functions[f_uid]['nr_bbls'] += 1

  def __CollectFunctionEntryPoints(self):
    # use 'readelf' to collect sections
    text_section = [0, 0]
    plt_section = [0, 0]

    out_lines = subprocess.check_output(["readelf", "-S", self._unstripped_binary]).split(b'\n')

    readelf_section_header = re.compile(r"^\s+\[\s*[0-9]+\]\s+(\.[^\s]+)?\s*[^\s]+\s+([0-9a-f]+)\s+[0-9a-f]+\s+([0-9a-f]+)")
    for line in out_lines:
      line = line.decode().rstrip()

      matches = readelf_section_header.match(line)
      if not matches:
          continue

      section_name = matches.group(1)
      section_address = int(matches.group(2), 16)
      section_size = int(matches.group(3), 16)

      if section_name == '.text':
        assert text_section[0] == 0, "already found a text section!"

        text_section[0] = section_address
        text_section[1] = section_address + section_size

        self.Print(".text 0x%x-0x%x" % (text_section[0], text_section[1]))
      elif section_name == '.plt':
        assert plt_section[0] == 0, "already found a PLT section!"

        plt_section[0] = section_address
        plt_section[1] = section_address + section_size

        self.Print(".plt 0x%x-0x%x" % (plt_section[0], plt_section[1]))
      #endif
    #endfor

    # use 'nm' to collect symbol information
    out_lines = subprocess.check_output(["nm", self._unstripped_binary]).split(b'\n')
    for line in out_lines:
      line = line.decode().rstrip()

      tokens = line.split(' ')
      # "         w $tls_start"
      if tokens[0] == '':
        continue

      address = int(tokens[0], 16)
      if not ((text_section[0] <= address) and (address < text_section[1])) and not ((plt_section[0] <= address) and (address < plt_section[1])):
        continue

      symbol_type = tokens[1]
      if not ((symbol_type == 't') or (symbol_type == 'T')):
        continue

      function_name = tokens[2]
      if function_name.startswith('$') or function_name.startswith('.'):
        continue

      # don't do symbols to DATA instructions
      if self.InsIsData(address, False):
        # don't translate if vanilla binary, as we're reading the b.out here
        continue

      if (plt_section[0] <= address) and (address < plt_section[1]):
        # PLT entry
        self.Print("PLT entry 0x%x: %s" % (address, function_name))
        if address not in self._plt_entries:
          self._plt_entries[address] = set()
        self._plt_entries[address].add(function_name)

      elif (text_section[0] <= address) and (address < text_section[1]):
        # skip padding instructions
        if not self.InsExists(address):
          continue

        self.Print("possible entry 0x%x %d: %s" % (address, self.InsBbl(address), line))
        self._possible_function_entries.add(self.InsBbl(address))
    #endfor

    # use 'objdump' to collect function calls
    # do some prefiltering here to prevent out-of-memory errors
    out_lines = subprocess.check_output('%s -d %s | egrep "\\sbl\\s"' % (self._objdump_binary, self._unstripped_binary), shell=True).split(b'\n')
    call_regex = re.compile(r"^\s*([0-9a-f]+):\s+[0-9a-f]+\s+bl\s+([0-9a-f]+)")
    for line in out_lines:
      line = line.decode().rstrip()

      matches = call_regex.match(line)
      if not matches:
          continue

      From = int(matches.group(1), 16)
      To = int(matches.group(2), 16)

      if To in self._plt_entries:
        self._plt_calls[From] = To
    #endfor

  def BblIsPossiblyFunctionEntry(self, b):
    return b in self._possible_function_entries

  def __TransformationDataToString(self, data):
    return "[FUID: %s, BBLs: %s, phases: %s, INS: %s]" % (data['functions'], ['%d@0x%x' % (b, self.BblAddress(b)) for b in data['bbls']], data['phases'], ['0x%x' % i for i in data['instructions']])
  #enddef

  def __CollectTransformationEntryExit(self):
    tf_to_delete = set()
    for tf_nr, data in self.ObfuscationTransformationIterator():
      self._nr_obfuscations += 1

      ignore_this_transformation = False
      ignore_reason = ""

      tf_bbls = data['bbls']

      entry_bbl = -1
      exit_bbl = -1
      if len(data['bbls']) == 1:
        entry_bbl = list(tf_bbls)[0]
        exit_bbl = entry_bbl

      else:
        # DEBUG print list of blocks in this transformation
        # self.Print("Transformation %d" % (tf_nr))
        # for bbl_uid in tf_bbls:
        #   self.Print("  block %d: 0x%x" % (bbl_uid, self._bbls[bbl_uid]['address']))

        entries = set()
        for bbl_uid in tf_bbls:
          # self.Print("incoming blocks for %d (%x)" % (bbl_uid, self._bbls[bbl_uid]['address']))
          incoming = self.BblIncomingBbls(bbl_uid, False, True, False) - tf_bbls
          # self.Print("     blocks %s" % incoming)
          if len(incoming) > 0:
            # print("adding1 %d" % bbl_uid)
            entries.add(bbl_uid)

          #all_incoming = self.BblIncomingBbls(bbl_uid, True, True, False) - tf_bbls
          #if len(all_incoming) == 0:
          if len(incoming) == 0 and self.BblIsPossiblyFunctionEntry(bbl_uid):
            # print("adding2 %d" % bbl_uid)
            entries.add(bbl_uid)

        if len(entries) == 0:
          # no entry points from real blocks found
          ignore_this_transformation = True
          ignore_reason = "no true entry blocks found"
        else:
          if len(entries) > 1:
            next_entries = set()
            for possible_entry in entries:
              incoming = self.BblIncomingBbls(possible_entry, False, True) & tf_bbls
              if len(incoming) == 0:
                next_entries.add(possible_entry)
            # print("next entries: %s, old: %s" % (next_entries, entries))
            entries = next_entries
          #endif

          assert len(entries) == 1, "multiple possible entry points %s for transformation %d: %s" % (entries, tf_nr, data)
          entry_bbl = list(entries)[0]
          # print("using entry %d" % entry_bbl)

          exits = set()
          for bbl_uid in tf_bbls:
            outgoing = self.BblOutgoingBbls(bbl_uid, False, True) - tf_bbls
            if len(outgoing) > 0:
              exits.add(bbl_uid)

            all_outgoing = self.BblOutgoingBbls(bbl_uid, True, True)
            if len(all_outgoing) == 0:
              exits.add(bbl_uid)
          #endfor

          if len(exits) > 1:
            next_exits = set()
            for possible_exit in exits:
              outgoing = self.BblOutgoingBbls(possible_exit, False, True) & tf_bbls
              if len(outgoing) == 0:
                next_exits.add(possible_exit)
            exits = next_exits
          #endif

          if len(exits) > 1:
            ignore_this_transformation = True
            ignore_reason = "multiple possible exit points"
          else:
            assert len(exits) == 1, "multiple possible exit points %s for transformation %d: %s" % (exits, tf_nr, self.__TransformationDataToString(data))
            exit_bbl = list(exits)[0]
        #endif
      #endif

      if not ignore_this_transformation:
        assert entry_bbl != -1, "no entry block found for transformation %d: %s" % (tf_nr, data)
        assert exit_bbl != -1, "no exit block found for transformation %d: %s" % (tf_nr, data)

        # self.Print("[TF %d] entry 0x%x" % (tf_nr, self._bbls[entry_bbl]['address']))
        # self.Print("[TF %d] exit 0x%x" % (tf_nr, self._bbls[exit_bbl]['address']))
        self._transformations['transformation_data'][tf_nr]['entry_bbl'] = entry_bbl
        self._transformations['transformation_data'][tf_nr]['exit_bbl'] = exit_bbl

      else:
        self.Print("ignoring transformation %d because: %s" % (tf_nr, ignore_reason))
        tf_to_delete.add(tf_nr)

        self._ignored_transformations.add(tf_nr)
      #endif
    #endfor

    for x in tf_to_delete:
      del self._transformations['transformation_data'][x]

  def InsIsData(self, i, do_translate = True):
    if self._vanilla and do_translate:
      i = self._listing['old2new'][i]

    return i in self._listing['data_instructions']

  def InsIsKilled(self, i):
    return i in self._killed['before_initial']

  def InsTransformationID(self, i):
    return self._listing['info'][i]['transformation']

  def _TransformationIdUID(self, x):
    return (x >> 32) & 0xffffffff

  def SkipTransformation(self, x):
    if x == self.__TFID_FLOWGRAPH:
      return True
    if x == self.__TFID_DEFLOWGRAPH:
      return True
    if x in self._ignored_transformations:
      return True

    return False

  def InsPhase(self, i):
    return self._listing['info'][i]['phase']

  def InsExecuted(self, i):
    return (i in self._instructions['instructions']) and (self._instructions['instructions'][i]['executed'] != 0)

  def InsFlags(self, i):
    return self._listing['info'][i]['flags']

  def InsOpcode(self, i):
    return self._listing['info'][i]['opcode']

  def InsIsIndexRelated(self, i):
    return self.InsFlags(i) & self.__IF_AF_INDEX_INSTRUCTION

  def InsIsIndexSecondPart(self, i):
    assert i in self._listing['info'], "instruction %x not in info" % (i)
    opcode = self._listing['info'][i]['opcode']

    return self.InsFlags(i) & self.__IF_AF_INDEX_INSTRUCTION and \
            (opcode == 'ADD' or opcode == 'SUB') and \
            i not in self._listing['addresses']

  def FunctionToOriginal(self, f):
    return self._functions[f]['original_uid']

  def FunctionToPartition(self, f):
    return self._functions[f]['partition_uid']

  def PartitionAssociatedWith(self, p):
    return self._partitions[p]['associated_functions'], self._partitions[p]['associated_objects'], self._partitions[p]['associated_libraries']

  def InsOrigin(self, address):
    # negative numbers are printed as unsigned by Diablo (*.partitions)
    function_uid = self.InsFunction(address)
    if function_uid is None:
      # maybe an entry in a branch-based switch table

      # incoming edge should be switch
      assert address in self._edges['incoming']
      already = False
      for i_edge_uid in self._edges['incoming'][address]:
        i_edge = self.EdgeByUID(i_edge_uid)
        assert not already, "expected only one incoming edge for 0x%x" % address
        assert i_edge['type'] == Tool.EDGE_JUMP, "unexpected incoming edge type for 0x%x: %d" % (address, i_edge['type'])
        already = True

      # outgoing edge should be jump
      assert address in self._edges['outgoing']
      already = False
      for o_edge_uid in self._edges['outgoing'][address]:
        o_edge = self.EdgeByUID(o_edge_uid)
        assert not already, "expected only one outgoing edge for 0x%x" % address
        assert o_edge['type'] == Tool.EDGE_JUMP, "unexpected outgoing edge type for 0x%x: %d" % (address, o_edge['type'])
        already = True

      # assume that this bbl belongs to the original function
      address2 = self._edges['edges'][i_edge_uid]['head']
      self.Print("address 0x%x not found in origin tracking, using address 0x%x instead" % (address, address2))
      function_uid = self.InsFunction(address2)

      assert function_uid is not None

    original_uid = self.FunctionToOriginal(function_uid)
    partition_uid = self.FunctionToPartition(function_uid)

    functions, objects, archives = self.PartitionAssociatedWith(partition_uid)

    if original_uid == -1:
      # this is an original function
      assert len(functions) == 1, "instruction 0x%x in original function, but multiple associated functions %s" % (address, functions)
      assert len(objects) == 1, "instruction 0x%x in original function, but multiple associated object files %s" % (address, objects)
      assert len(archives) == 1, "instruction 0x%x in original function, but multiple associated libraries %s" % (address, archives)

      original_uid = function_uid

    # remove 'negative' functions
    # TODO this is a _very_ dirty hack
    filtered_functions = [x for x in functions if not (x & 0xff000000)]
    functions = filtered_functions

    return functions, objects, archives, original_uid, function_uid

  def GetEdge(self, head, tail, etype=None):
    if head not in self._edges['outgoing']:
      # head not found
      return False, -1, None

    for edge_uid in self._edges['outgoing'][head]:
      edge = self._edges['edges'][edge_uid]
      if edge['tail'] == tail:
        if etype == None or (etype == edge['type']):
          return True, edge_uid, edge

    # edge not found, maybe a switch edge?
    return False, -2, None

  def EdgeIsInterLib(self, edge_uid):
    edge = self.EdgeByUID(edge_uid)

    _, _, libs_head, _, _ = self.InsOrigin(edge['branch'])
    _, _, libs_tail, _, _ = self.InsOrigin(edge['tail'])

    return len(set(libs_head) & set(libs_tail)) == 0

  def EdgeIsExecuted(self, edge_uid):
    edge = self.EdgeByUID(edge_uid)
    return (edge['flags'] & self.__EDGE_FLAG_EXECUTED) != 0

  def EdgeIsInter(self, edge_uid):
    edge = self.EdgeByUID(edge_uid)

    hFun, hObj, hArc, _, _ = self.InsOrigin(edge['branch'])
    tFun, tObj, tArc, _, _ = self.InsOrigin(edge['tail'])

    return len(set(hFun) & set(tFun)) == 0, len(set(hObj) & set(tObj)) == 0, len(set(hArc) & set(tArc)) == 0

  # compensate for Diablo-created constant producer instructions, if needed.
  # Only do this for the case where a vanilla binary is being processed.
  def HandleProducers(self, i):
    if self._vanilla:
      next_address = i+4

      if i not in self._listing['old2new'] and \
          next_address in self._listing['old2new']:
        new_address = self._listing['old2new'][next_address]

        # check if it is a constant producer
        if new_address in self._listing['constants']:
          self.Print("constant producer at 0x%x, returning 0x%x" % (i, next_address))
          i = next_address

    return i

  def InsIsUnconditionalBranch(self, i):
    return self._listing['info'][i]['opcode'] == 'B'

  def EdgeIsFake(self, e):
    return self.EdgeByUID(e)['fake']

  def InsIsThumb(self, i):
    return False

  def EdgeIsOriginallySwitch(self, e):
    return (self._original_edge_type[e] == self.__ET_SWITCH) or (self._original_edge_type[e] == self.__ET_IPSWITCH)

  def EdgeIsSwitchFallthrough(self, e):
    edge = self.EdgeByUID(e)

    if edge['type'] != Tool.EDGE_FALLTHROUGH:
      return False

    for euid, _ in self.InsOutgoingEdgeIterator(edge['branch']):
      if self.EdgeIsOriginallySwitch(euid):
        return True

    return False

  def EdgeIsSwitchFallthroughUnreachable(self, e):
    edge = self.EdgeByUID(e)

    if edge['type'] != Tool.EDGE_FALLTHROUGH:
      return False

    switch_ins = edge['branch']

    if switch_ins in self._listing['switch_add']:
      self.Print("0x%x is switch-add instruction" % (switch_ins))
      return True

    if switch_ins in self._listing['switch_ldr']:
      self.Print("0x%x is switch-ldr instruction" % (switch_ins))
      return True

    return False

  def InsIsSpecial(self, i, assembled):
    return assembled == 0xbdb00bdb

  # for IDA plugin
  def InsIsDispatcher(self, i):
    return i in self._af_dispatchers

  def InsIsOriginal(self, i):
    if i in self._listing['new2old']:
      return self._listing['new2old'][i] != 0

    return False

  def IsLoaded(self):
    return self._loaded

  def InsTransformationUID(self, i):
    return self._TransformationIdUID(self.InsTransformationID(i))

  def FirstInsInBblForTransformation(self, b, tf):
    for i in self.BblInsIterator(b):
      if self.InsTransformationUID(i) == tf:
        return i

    return None

  def InsIsPartOfObfuscationTransformation(self, i):
    obf = False
    if DiabloList.PHASE_OBFUSCATION in self._transformations['transformation_by_phase']:
      obf = self.InsTransformationUID(i) in self._transformations['transformation_by_phase'][DiabloList.PHASE_OBFUSCATION]

    csc = False
    if DiabloList.PHASE_CALLCHECKS in self._transformations['transformation_by_phase']:
      csc = self.InsTransformationUID(i) in self._transformations['transformation_by_phase'][DiabloList.PHASE_CALLCHECKS]

    return obf or csc

  def InsIsPartOfFactoringTransformation(self, i):
    return self.InsTransformationUID(i) in self._transformations['transformation_by_phase'][DiabloList.PHASE_ADVANCEDFACTORING]

  def collect_links(self, fn_same_function):
    self._good_links = {}
    self._bad_links = {}

    nr_linked = 0
    nr_broken = 0

    for a, b in self._af_splits:
        key = a if a < b else b
        value = b if a < b else a

        if fn_same_function(a, b):
            nr_linked += 1
            if key not in self._good_links:
                self._good_links[key] = set()
            self._good_links[key].add(value)
        else:
            nr_broken += 1
            if key not in self._bad_links:
                self._bad_links[key] = set()
            self._bad_links[key].add(value)
        #endif
    #endfor

    self.Print("STATUS Collected links: %d linked, %d broken (%d total)" % (nr_linked, nr_broken, nr_linked+nr_broken))

  def links_with(self, i):
    if i not in self._af_splits_linked:
      # print("0x%x not in linked pairs" % i)
      return set()

    self.Print("0x%x links with %s" % (i, ['0x%x' % (x) for x in self._af_splits_linked[i]]))
    return self._af_splits_linked[i]

  def link_is_ok(self, i, j):
    key = i if i < j else j
    value = j if i < j else i

    return (key in self._good_links) and (value in self._good_links[key])

  def record_link(self, i, j, is_broken):
    key = i if i < j else j
    value = j if i < j else i

    if is_broken:
      self._good_links[key].discard(value)
      if key not in self._bad_links:
        self._bad_links[key] = set()
      self._bad_links[key].add(value)
    else:
      self._bad_links[key].discard(value)
      if key not in self._good_links:
        self._good_links[key] = set()
      self._good_links[key].add(value)
    #endif
  #enddef

  def record_links(self, i, fn_same_function):
    # check links for instruction 'i', if any
    for j in self.links_with(i):
        # 'j' should be linked with 'i'
        # i.e., both should be put in the same function
        were_together = self.link_is_ok(i, j)
        are_together = fn_same_function(i, j)

        if were_together and not are_together:
            self.Print("LINK BROKEN 0x%x-0x%x" % (i, j))
            self.record_link(i, j, True)
        elif not were_together and are_together:
            self.Print("LINK FIXED 0x%x-0x%x" % (i, j))
            self.record_link(i, j, False)
    #endfor
  #enddef

  def PartitioningIgnoreSwitchRelatedEdges(self):
    self.Print("STATUS selecting edges to ignore")

    incoming_per_type = {}
    total_types = {}
    for dispatcher_insn, dispatcher_data in self._af_dispatchers.items():
      #TODO: explicitely skip conditional branch dispatchers
      tf_uid = dispatcher_data['tf_uid']
      dispatcher_type = self._af_slices['transformations'][tf_uid]['type']

      if dispatcher_type not in total_types:
        total_types[dispatcher_type] = 0
      total_types[dispatcher_type] += 1

      if dispatcher_type == DiabloLog.DISPATCHER_CONDITIONAL_BRANCH:
        self.Print("dispatcher at 0x%x is conditional branch" % dispatcher_insn)
        continue

      self.Print("ignoring edges to dispatcher (type %d) at 0x%x (entry 0x%x)" % (dispatcher_type, dispatcher_insn, dispatcher_data['entry']))

      if dispatcher_type not in incoming_per_type:
        incoming_per_type[dispatcher_type] = 0

      # ignore incoming edges
      nr_incoming = 0
      for diablo_edge_uid in dispatcher_data['incoming']:
        diablo_edge = self.EdgeByUID(diablo_edge_uid)
        nr_incoming += 1
        self.Print("ignoring incoming 0x%x-0x%x" % (diablo_edge['branch'], diablo_edge['tail']))
        yield diablo_edge['branch'], diablo_edge['tail']
      #endfor

      self.Print("dispatcher type %d has %d incoming edges" % (dispatcher_type, nr_incoming))
      incoming_per_type[dispatcher_type] += nr_incoming

      # For a branch-based switch dispatchers, we observed the following CFG in IDA:
      #
      #  (dispatcher)
      #     |      \
      #     |   (branch)
      #     |      /
      #  (destination)
      #
      # So, for those dispatchers we need to ignore 3 edges:
      # (1) from the dispatcher to the destination
      # (2) from the dispatcher to the branch
      # (3) from the branch to the destination

      # ignore outgoing edges
      for diablo_edge_uid in dispatcher_data['outgoing']:
        diablo_edge = self.EdgeByUID(diablo_edge_uid)

        # edge (1)
        self.Print("ignoring outgoing 0x%x-0x%x" % (diablo_edge['branch'], diablo_edge['tail']))
        yield diablo_edge['branch'], diablo_edge['tail']

        # also ignore the branch-to-destination edge
        # for branch-based switch dispatchers
        if dispatcher_type == DiabloLog.DISPATCHER_BRANCH_SWITCH:
          branch_bbl_uid = self.InsBbl(diablo_edge['tail'])

          seen_edge = False
          for diablo_edge_uid_2, diablo_edge_2 in self.BblOutgoingEdgeIterator(branch_bbl_uid, True, True):
            assert not seen_edge
            assert diablo_edge_2['type'] == Tool.EDGE_JUMP, self.EdgeToString(diablo_edge_uid_2)

            seen_edge = True

            # edge (2)
            self.Print("ignoring edge 0x%x-0x%x" % (diablo_edge['branch'], diablo_edge_2['tail']))
            yield diablo_edge['branch'], diablo_edge_2['tail']

            # edge (3)
            self.Print("ignoring branch edge 0x%x-0x%x" % (diablo_edge_2['branch'], diablo_edge_2['tail']))
            yield diablo_edge_2['branch'], diablo_edge_2['tail']
          #endfor
        #endif
      #endfor
    #endfor
    self.Print("STATUS nr incoming edges per dispatcher type: %s" % incoming_per_type)
    self.Print("STATUS nr dispatchers of type: %s" % total_types)
  #enddef
