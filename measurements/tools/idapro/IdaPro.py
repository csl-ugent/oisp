import tools.idapro.log as IdaLog
import tools.Tool as Tool

class IdaPro(Tool.Tool):
  def __init__(self, vanilla):
    super().__init__("IdaPro", vanilla)

    self._switches = None
    self._edges_mapped_to_ground_truth = {}
    self._edges_ground_truth_to_self = {}

  def Load(self, ground_truth, logs):
    self._instructions, self._bbls, self._functions, self._edges, self._switches = IdaLog.readIDAFiles(logs)

    nr_executed_edges = 0
    for uid, edge in self.EdgeIterator():
      # executed edge?
      executed = ground_truth.InsExecuted(edge['head']) and ground_truth.InsExecuted(edge['tail'])
      self._edges['edges'][uid]['executed'] = executed
      if executed:
        nr_executed_edges += 1

    self.__FunctionSize()

    if not self._vanilla:
      self._CollectTransformationInformation(ground_truth)
      self.__CollectTransformationEntryExit(ground_truth)

    self.__MapEdgesToGroundTruth(ground_truth)

    nr_fake_edges = 0
    nr_fake_edges_drawn = 0
    for edge_uid, all_mapped_edge_uid in self.MappedEdgeIterator():
      for mapped_edge_uid in all_mapped_edge_uid:
        if ground_truth.EdgeIsFake(mapped_edge_uid):
          nr_fake_edges += 1
          if self.EdgeDrawn(edge_uid, False):
            nr_fake_edges_drawn += 1

    for block_uid, block in self.BblIterator():
      self._functions[block['function_uid']]['bbls'].add(block_uid)

    self.Print("INPUT STATISTICS")
    self.Print("  Ins      : %d total, %d functionless" % (self.InsCount(), self.InsCountNotInFunction()))
    self.Print("  Bbls     : %d total" % (self.BblCount()))
    self.Print("  Functions: %d total" % (self.FunctionCount()))
    self.Print("  Edges    : %d total, %d executed, %d fake, %d fake-drawn" % (self.EdgeCount(), nr_executed_edges, nr_fake_edges, nr_fake_edges_drawn))
    self.Print("  Transformations: %d total" % (self.TransformationCount()))

  def __FunctionSize(self):
    self.Print("calculating size of functions...")

    for function_uid, _ in self.FunctionIterator():
      self._functions[function_uid]['nr_bbls'] = 0

    for _, b in self.BblIterator():
      self._functions[self.BblFunction(b)]['nr_bbls'] += 1

  def __CollectTransformationEntryExit(self, ground_truth):
    self.Print("collecting transformation entry/exit blocks from ground truth...")

    to_be_deleted = set()
    for tf_nr, data in self.ObfuscationTransformationIterator():
      # entry/exit according to ground truth
      if ground_truth.SkipTransformation(tf_nr):
        continue

      gt_data = ground_truth.TransformationData(tf_nr)
      gt_entry_address = ground_truth.BblAddress(gt_data['entry_bbl'])
      gt_exit_address = ground_truth.BblAddress(gt_data['exit_bbl'])

      gt_entry_ins = ground_truth.FirstInsInBblForTransformation(gt_data['entry_bbl'], tf_nr)
      assert gt_entry_ins is not None, "transformation %d: GT(%x) %s" % (tf_nr, gt_entry_address, gt_data)
      gt_exit_ins = ground_truth.FirstInsInBblForTransformation(gt_data['exit_bbl'], tf_nr)
      assert gt_exit_ins is not None

      # IDA only
      if self.InsNotInFunction(gt_entry_ins) or self.InsNotInFunction(gt_exit_ins):
        to_be_deleted.add(tf_nr)
        continue

      # data?
      if not self.InsExists(gt_entry_ins) or not self.InsExists(gt_exit_ins):
        self.Print("eliminating transformation %d as the entry and/or exit address is not found" % tf_nr)
        to_be_deleted.add(tf_nr)
        continue

      # entry/exit according to this tool
      entry_bbl = self.InsBbl(gt_entry_ins)
      exit_bbl = self.InsBbl(gt_exit_ins)

      self._transformations['transformation_data'][tf_nr]['entry_bbl'] = entry_bbl
      self._transformations['transformation_data'][tf_nr]['exit_bbl'] = exit_bbl

      # self.Print("TF %d has entry 0x%x, exit 0x%x" % (tf_nr, self.BblByUID(entry_bbl)['address'], self.BblByUID(exit_bbl)['address']))

      if entry_bbl not in data['bbls']:
        # verify that the found entry BBL has a fallthrough edge to a bbl that _is_ part of the transformation
        fallthrough_block = -1
        for _, edge in self.BblOutgoingEdgeIterator(entry_bbl):
          if edge['type'] == Tool.EDGE_FALLTHROUGH:
            assert fallthrough_block == -1
            fallthrough_block = self.InsBbl(edge['tail'])

        #assert fallthrough_block != -1, "no fallthrough block for 0x%x" % (gt_entry_address)
        entry_bbl = fallthrough_block

      if entry_bbl == -1:
        self.Print("eliminating transformation %d as the entry block is not found" % tf_nr)
        to_be_deleted.add(tf_nr)
      else:
        entry_address = self.BblAddress(entry_bbl)
        if self.InsIsThumb(entry_address):
          self.Print("eliminating transformation %d as the entry block %d at 0x%x is THUMB" % (tf_nr, entry_bbl, entry_address))
          to_be_deleted.add(tf_nr)
        #endif
      #endif

      if exit_bbl not in data['bbls']:
        self.Print("eliminating transformation %d as the exit block is not found" % tf_nr)
        to_be_deleted.add(tf_nr)

      if tf_nr not in to_be_deleted:
        assert entry_bbl in data['bbls'], "transformation %d, entry block GT(0x%x), I(%d) %s" % (tf_nr, gt_entry_address, entry_bbl, data)
        assert exit_bbl in data['bbls'], "transformation %d, exit block GT(0x%x), I(%d) %s" % (tf_nr, gt_exit_address, exit_bbl, data)

    if len(to_be_deleted) > 0:
      self.Print("eliminated %d transformations with hanging entry or exit blocks" % len(to_be_deleted))
      for x in to_be_deleted:
        del self._transformations['transformation_data'][x]

  def __MapEdgesToGroundTruth(self, ground_truth):
    self.Print("mapping edges to ground truth...")

    for edge_uid, edge in self.EdgeIterator(False, True):
      edge_head = edge['branch']
      edge_tail = edge['tail']
      edge_type = edge['type']

      # self.Print("process edge %s" % self.EdgeToString(edge_uid))

      # take care of unreachable code, which has been killed by Diablo before the initial origin information was emitted
      if self._vanilla and ground_truth.InsIsKilled(edge_head) and ground_truth.InsIsKilled(edge_head):
        continue

      # edges from DATA should be skipped
      # .text:0000175C                 EXPORT DYNABSRELOC_.LANCHOR0
      # .text:0000175C DYNABSRELOC_.LANCHOR0                   ; Alternative name is '$diablo::4:.LANCHOR0-(.LPIC0+8)'
      # .text:0000175C                 LDREQD          R10, [LR],-R0 ; .LVL2_1
      # .text:00001760
      # .text:00001760 .LVL6_1                                 ; CODE XREF: OPENSSL_cpuid_setup+48j
      # .text:00001760                 ADD             R5, R4, #0x18C
      #
      # X-ref to 0x1760 exists, but data at 0x175c is DATA according to Diablo, not CODE.
      # No X-ref exists to 0x175c, but IDA erroneously marked it as CODE.
      if ground_truth.InsIsData(edge_head):
        continue

      # edges to DATA should be skipped
      # .text:0017DF68 loc_17DF68                              ; CODE XREF: .LVL319_1+1790B0j
      # .text:0017DF68                 VST1.32         {D6-D7}, [R2]!
      # .text:0017DF6C                 VST1.32         {D16-D17}, [R2]!
      # .text:0017DF6C ; END OF FUNCTION CHUNK FOR .LVL319_1
      # .text:0017DF6C ; ---------------------------------------------------------------------------
      # .text:0017DF70                 DCD 0xF3F04300
      if ground_truth.InsIsData(edge_tail):
        continue

      ok, gt_edge_uid, _ = ground_truth.GetEdge(edge_head, edge_tail, edge_type)
      # self.Print("edge %d result %d 0x%x-0x%x %d" % (edge_uid, gt_edge_uid, edge_head, edge_tail, edge_type))
      if ok:
        # self.Print("  GT-edge: %s" % ground_truth.EdgeToString(gt_edge_uid))

        # e.g., for switches where multiple outgoing edges go to the same destination
        pars = ground_truth.ParallelEdges(gt_edge_uid, True)

        self._edges_mapped_to_ground_truth[edge_uid] = set()
        for x in pars:
          self._edges_mapped_to_ground_truth[edge_uid].add(x)
          # print("map GT edge %d to IDA edge %d" % (x, edge_uid))
          assert x not in self._edges_ground_truth_to_self
          self._edges_ground_truth_to_self[x] = edge_uid
        #endfor

      else:
        ida_edge_head = self.HandleProducers(edge_head)

        if edge_type == Tool.EDGE_CALLFALLTHROUGH:
          # tail calls don't have a call-FT edge in Diablo
          # also, fallthrough to other ground truth function is possible
          pass

        elif gt_edge_uid == -1:
          if self.InsIsThumb(ida_edge_head):
            pass

          else:
            head_block = ground_truth.InsBbl(edge_head)
            tail_block = ground_truth.InsBbl(edge_tail)
            if edge_type == Tool.EDGE_FALLTHROUGH and head_block == tail_block:
              # IDA draws FT edge where Diablo put the two blocks together
              pass

            else:
              # self.Print("[%d] no outgoing edges from head 0x%x -> 0x%x (type %d)" % (edge_uid, edge_head, edge_tail, edge_type))
              pass

        elif gt_edge_uid == -2:
          if self.InsIsSwitch(edge_head) and (edge_tail in self.SwitchTargets(edge_head) or edge_tail == self.SwitchDefault(edge_head)):
            # this is a switch edge
            #print("[%d] direct switch edge 0x%x -> 0x%x" % (ida_edge_uid, head, tail))
            pass

          else:
            # this is not a switch edge
            #self.Print("tail not found [%d] 0x%x -> 0x%x (type %d)" % (edge_uid, edge_head, edge_tail, edge_type))
            pass

        else:
          assert False

  def EdgeDrawn(self, e, db_attack):
    if db_attack:
      return True

    e = self.EdgeByUID(e)

    f1 = self.InsFunction(e['head'])
    f2 = self.InsFunction(e['tail'])

    return f1 == f2

  def GroundTruthEdgeToSelf(self, e):
    if e not in self._edges_ground_truth_to_self:
      return None

    return self._edges_ground_truth_to_self[e]

  def InsIsSwitch(self, i):
    return i in self._switches

  def SwitchTargets(self, i):
    return self._switches[i]['targets']

  def SwitchDefault(self, i):
    return self._switches[i]['default_case']

  # compensate for IDA-created constant producer instructions, if needed.
  def HandleProducers(self, i):
      next_address = i-4

      if i not in self._instructions['instructions'] and \
          next_address in self._instructions['instructions']:
          if self._instructions['instructions'][next_address]['macro']:
              i = next_address

      return i

  def InsIsUnconditionalBranch(self, i):
    return (self.InsAssembled(i) & 0xff000000) == 0xea000000

  def InsIsCall(self, i):
    if not self.InsExists(i):
      return False

    return (self.InsAssembled(i) & 0x0f000000) == 0x0b000000

  def MappedEdgeIterator(self):
    for x, y in self._edges_mapped_to_ground_truth.items():
      yield x, y

  def BblIncomingMappedEdgeIterator(self, b):
    for x, _ in self.BblIncomingEdgeIterator(b):
      if x in self._edges_mapped_to_ground_truth:
        yield x, self._edges_mapped_to_ground_truth[x]

  def BblOutgoingMappedEdgeIterator(self, b):
    for x, _ in self.BblOutgoingEdgeIterator(b):
      if x in self._edges_mapped_to_ground_truth:
        yield x, self._edges_mapped_to_ground_truth[x]

  def InsIsThumb(self, i):
    return self._instructions['instructions'][i]['thumb']

  def BblMoveToFunction(self, b, B, f):
    # update function size
    old_function = self.BblFunction(B)
    self._functions[old_function]['nr_bbls'] -= 1
    if self._functions[old_function]['nr_bbls'] == 0:
      self.Print("function %d has no more BBLs" % old_function)

    self._functions[f]['nr_bbls'] += 1

    # instruction/function association
    for i in self.BblInsIterator(b):
      self.InsMoveToFunction(i, f)

    # BBL field
    self._bbls[b]['function_uid'] = f

    self._functions[old_function]['bbls'].remove(b)
    self._functions[f]['bbls'].add(b)

  def BblIsFunctionEntry(self, b):
    for _, edge in self.BblIncomingEdgeIterator(b, True, False):
      if edge['type'] == Tool.EDGE_CALL:
        return True

    return False

  def InsIsData(self, i):
    return i not in self._instructions['instructions']
