import os
import common
import tools.Tool as Tool
import lib.partitioning as partitioning

# given an original functio UID, know which edges are associated with it
original_functions = {}
# given an edge UID, know which functions it is associated with
edge_associations = {}
# inter or intra information
edge_information = {
  'interlib': set(),
  'intralib': set(),

  'interobj': set(),
  'intraobj': set(),

  'interfun': set(),
  'intrafun': set()
}

debug = False
nr_eliminated = 0
nr_eliminated_drawn = 0

ida_instance = None

g_edges_eliminated = None
counter = 0

eliminated_statistics = {}
ELIMINATED_STATE_SKIP = 0
ELIMINATED_STATE_FAKE_IN = 1
ELIMINATED_STATE_NOT_SAME_FUNCTION = 2
ELIMINATED_STATE_ELIMINATED = 3

I = None

def dbg(x):
  if debug:
    print(x)

def add(f, e, c, fake):
  global original_functions, edge_associations

  if f not in original_functions:
    original_functions[f] = {
      'in': set(), 'in_fake': set(),
      'intra': set(), 'intra_fake': set(),
      'out': set(), 'out_fake': set(),

      'ida_gui': set(), 'ida_gui_fake': set(),
      'ida_python': set(), 'ida_python_fake': set(),
    }
  if e not in edge_associations:
    edge_associations[e] = []

  if fake:
    c += '_fake'

  # dbg("    edge %d as '%s' to function %d" % (e, c, f))
  original_functions[f][c].add(e)
  edge_associations[e].append((f, c))

def process_edge(head_f, tail_f, diablo_edge_uid, diablo_edge_fake, edge_head, edge_tail, edge_type):
  if len(head_f) == 1 and len(tail_f) == 1:
    fH = head_f[0]
    fT = tail_f[0]
    if fH == fT:
      add(fH, diablo_edge_uid, 'intra', diablo_edge_fake)
    else:
      add(fH, diablo_edge_uid, 'out', diablo_edge_fake)
      add(fT, diablo_edge_uid, 'in', diablo_edge_fake)

  elif len(head_f) > 1 and len(tail_f) == 1:
    fT = tail_f[0]
    if fT in head_f:
      add(fT, diablo_edge_uid, 'intra', diablo_edge_fake)
    else:
      add(fT, diablo_edge_uid, 'in', diablo_edge_fake)

    for fH in set(head_f)-set(tail_f):
      add(fH, diablo_edge_uid, 'out', diablo_edge_fake)

  elif len(head_f) == 1 and len(tail_f) > 1:
    fH = head_f[0]
    if fH in tail_f:
      add(fH, diablo_edge_uid, 'intra', diablo_edge_fake)
    else:
      add(fH, diablo_edge_uid, 'out', diablo_edge_fake)

    for fT in set(tail_f)-set(head_f):
      add(fT, diablo_edge_uid, 'in', diablo_edge_fake)

  elif set(head_f) == set(tail_f):
    for f in head_f:
      add(f, diablo_edge_uid, 'intra', diablo_edge_fake)

  elif not set(head_f).intersection(set(tail_f)):
    # head_f and tail_f have no elements in common
    for fH in head_f:
      add(fH, diablo_edge_uid, 'out', diablo_edge_fake)
    for fT in tail_f:
      add(fT, diablo_edge_uid, 'in', diablo_edge_fake)

  else:
    intersect = set(head_f).intersection(set(tail_f))
    nointersectH = set(head_f) - intersect
    nointersectT = set(tail_f) - intersect

    for x in intersect:
      add(x, diablo_edge_uid, 'intra', diablo_edge_fake)

    for x in nointersectH:
      add(x, diablo_edge_uid, 'out', diablo_edge_fake)
    for x in nointersectT:
      add(x, diablo_edge_uid, 'in', diablo_edge_fake)

    #assert False, "[%d] 0x%x -> 0x%x (%d) head F(%s), tail F(%s)" % (diablo_edge_uid, edge_head, edge_tail, edge_type, head_f, tail_f)

def factor(l):
  total = sum(l)
  return 0 if total == 0 else 1/total

def same_function(a, b):
  if I.InsNotInFunction(a) or I.InsNotInFunction(b):
    return False
  elif I.InsFunction(a) != I.InsFunction(b):
    return False

  # I.InsFunction(a) == I.InsFunction(b)
  return True

def set_eliminated_tf_state(tf_uid, state):
  old_state = -1
  if tf_uid in eliminated_statistics:
    old_state = eliminated_statistics[tf_uid]

  if state > old_state:
    eliminated_statistics[tf_uid] = state

  if (state == ELIMINATED_STATE_ELIMINATED) and (old_state == ELIMINATED_STATE_ELIMINATED):
    print("TF%d already eliminated" % tf_uid)
#enddef

# returns list of IDA edge UIDs that are not drawn in the GUI
def eliminate(D, I):
  global nr_eliminated, nr_eliminated_drawn
  global g_edges_eliminated

  global_change = False
  if not common.smart_attacker:
    return global_change

  print("ELIMINATE total %d edges in tool" % (I.EdgeCount()))

  change = True
  nr_passes = 0
  while change:
    change = False
    nr_passes += 1

    # iterate over the transformations
    # and eliminate the edges that an attacker may remove,
    # assuming that he is smart enough to recognise the opaque predicate calculations as such
    for tf_uid, data in I.ObfuscationTransformationIterator():
      if D.SkipTransformation(tf_uid):
        print("SKIP transformation %d" % tf_uid)
        set_eliminated_tf_state(tf_uid, ELIMINATED_STATE_SKIP)
        continue

      print("ELIMINATE transformation %d" % tf_uid)

      # iterate over the basic blocks of this transformation
      incoming_fake = False
      all_in_same_function = True
      entry_address = I.BblAddress(data['entry_bbl'])
      for bbl_uid in data['bbls']:
        if bbl_uid == data['entry_bbl']:
          continue

        if not same_function(I.BblAddress(bbl_uid), entry_address):
          all_in_same_function = False

        # look up fake incoming edges
        for edge_uid, all_mapped_edge_uid in I.BblIncomingMappedEdgeIterator(bbl_uid):
          for mapped_edge_uid in all_mapped_edge_uid:
            if D.EdgeIsFake(mapped_edge_uid) and (edge_uid not in g_edges_eliminated) and I.EdgeDrawn(edge_uid, common.db_attack):
              #print("[TF %d] has incoming fake" % tf_uid)
              incoming_fake = True
              break
        #endfor incoming mapped

        if incoming_fake:
          break
      #endfor bbls

      # at least one incoming fake edge to this transformation (inside)
      if incoming_fake:
        print("  ELIMINATE-FAIL incoming fake edge")
        set_eliminated_tf_state(tf_uid, ELIMINATED_STATE_FAKE_IN)
        continue

      if (not common.db_attack) and (not all_in_same_function):
        print("  ELIMINATE-FAIL not all blocks in same function")
        set_eliminated_tf_state(tf_uid, ELIMINATED_STATE_NOT_SAME_FUNCTION)
        continue

      # SANITY CHECK
      for edge_uid, all_mapped_edge_uid in I.BblIncomingMappedEdgeIterator(data['entry_bbl']):
        for mapped_edge_uid in all_mapped_edge_uid:
          if D.EdgeIsFake(mapped_edge_uid) and (edge_uid not in g_edges_eliminated) and I.EdgeDrawn(edge_uid, common.db_attack):
            # maybe this block starts with another transformation
            # and thus, the fake edge is incoming to the other transformation, for example:
            #
            # loc_98FD4
            # LDMFD           SP!, {R1,R5}        (TF-obf 0x1387)
            # EOR             R7, R3, R7          (TF-af  0x32b)
            # EOR             R3, R3, R7          (TF-af  0x32b)
            # STR             R12, [LR,R3]        (vanilla)
            # STMFD           SP!, {R4,R5} ; int  (TF-obf 0x1386)
            # AND             R5, R7, #0xEE       (TF-obf 0x1386)
            #
            # this bbl has an incoming fake edge, of which we would think that it goes to transformation 0x1386
            # but rather it goes to transformation 0x1387.
            # As IDA puts all these instructions in one BBL, however, this conclusion is incorrect.
            for i in I.BblInsIterator(data['entry_bbl']):
              if D.InsTransformationID(i) == tf_uid:
                # we should not have redirected _any_ fake edge to the beginning of a transformation
                edge = I.EdgeByUID(edge_uid)
                assert False, "entry of TF %d (0x%x) has incoming fake 0x%x (0x%x) -> 0x%x" % (tf_uid, tf_uid, edge['head'], edge['branch'], edge['tail'])
              #endif tf_uid

              break
            #endfor BblInsIterator
          #endif EdgeIsFake
      #endfor incoming mapped

      # eliminate all outgoing fake edges
      for bbl_uid in data['bbls']:
        for edge_uid, all_mapped_edge_uid in I.BblOutgoingMappedEdgeIterator(bbl_uid):
          for mapped_edge_uid in all_mapped_edge_uid:
            if D.EdgeIsFake(mapped_edge_uid) and (edge_uid not in g_edges_eliminated):
              nr_eliminated += 1
              if I.EdgeDrawn(edge_uid, False):
                nr_eliminated_drawn += 1

              edge = I.EdgeByUID(edge_uid)
              print("  ELIMINATE-SUCCESS edge 0x%x->0x%x" % (edge['branch'], edge['tail']))
              set_eliminated_tf_state(tf_uid, ELIMINATED_STATE_ELIMINATED)

              g_edges_eliminated.add(edge_uid)
              partitioning.IgnoreEdge(edge['branch'], edge['tail'])

              change = True
            #endif
        #endfor outgoing
      #endfor bbls
    #endfor transformations

    global_change |= change
  #endwhile

  print("ELIMINATE   eliminated %d fake edges in %d passes, of which %d were drawn previously" % (nr_eliminated, nr_passes, nr_eliminated_drawn))

  return global_change

g_moved_blocks = {}
def reassoc_function(D, I):
  global counter, g_moved_blocks

  if not common.smart_attacker:
    return False

  global_change = False

  def BblInsIterator(address):
    for ins in I.BblInsIterator(I.InsBbl(address)):
      yield ins
  #enddef BblInsIterator

  def OutgoingInsIterator(address):
    for euid, _ in I.BblOutgoingMappedEdgeIterator(I.InsBbl(address)):
      yield I.EdgeByUID(euid)['tail']
  #enddef OutgoingInsIterator

  def IncomingInsIterator(address):
    for euid, _ in I.BblIncomingMappedEdgeIterator(I.InsBbl(address)):
      yield I.EdgeByUID(euid)['branch']
  #enddef IncomingInsIterator

  def ConsiderEdge(a, b):
    return I.EdgeDrawn(I.EdgeFromToUID(a, b), common.db_attack)
  #enddef ConsiderEdge

  def BlockStartAddress(address):
    return I.BblAddress(I.InsBbl(address))
  #enddef BlockStartAddress

  def BlockEndAddress(address):
    return I.BblEndAddress(I.InsBbl(address))
  #enddef BlockEndAddress

  def MoveBlock(block_start, block_end, function_uid):
    global g_moved_blocks

    block_uid = I.InsBbl(block_start)
    assert block_uid == I.InsBbl(block_end)

    function_uid = I.InsFunction(function_uid)
    dbg("moving 0x%x-0x%x to %d" % (block_start, block_end, function_uid))
    I.BblMoveToFunction(block_uid, I.BblByUID(block_uid), function_uid)

    # record move in links
    for i in I.BblInsIterator(block_uid):
      D.record_links(i, same_function)

    g_moved_blocks[block_start] = {
      'start': block_start,
      'end': block_end,
      'target': function_uid
    }
  #enddef MoveBlock

  def GetFunctionStart(x):
    # given function UID, return address
    # here, we want to use the function UID in MoveBlock, so do nothing
    return x
  #enddef GetFunctionStart

  def InsIsInBbl(address):
    return I.InsBbl(address) != -1
  #enddef InsIsInBbl

  # set up partitioning algorithm
  partitioning.prioritize_fallthrough = common.prioritize_ft

  partitioning.fn_ins_iterator = BblInsIterator
  partitioning.fn_ins_is_call = I.InsIsCall
  partitioning.fn_outgoing_insns = OutgoingInsIterator
  partitioning.fn_incoming_insns = IncomingInsIterator
  partitioning.fn_edge_consider = ConsiderEdge
  partitioning.fn_get_function = I.InsFunction
  partitioning.fn_move_block = MoveBlock
  partitioning.fn_get_block_end_address = BlockEndAddress
  partitioning.fn_get_function_start = GetFunctionStart
  partitioning.fn_get_block_start_address = BlockStartAddress
  partitioning.fn_ins_in_block = InsIsInBbl
  partitioning.fn_print = print

  already_moved = set()

  nr_passes = 0
  nr_reassoc = 0
  change = True
  while change:
    change = False
    nr_passes += 1

    for bbl_uid, bbl in I.BblIterator():
      if bbl_uid in already_moved:
        # don't recalculate unnecessary stuff:
        # blocks that previously had no incoming edges, and thus have been researched
        # to be moved, don't need to be looked at again.
        continue

      # don't move function entry points
      if I.BblIsFunctionEntry(bbl_uid):
        continue

      # check whether one or more incoming edges are drawn
      drawn_incoming = False
      for edge_uid, _ in I.BblIncomingMappedEdgeIterator(bbl_uid):
        if I.EdgeDrawn(edge_uid, common.db_attack) and (edge_uid not in g_edges_eliminated):
          drawn_incoming = True
          break
      #endfor

      if not drawn_incoming:
        # no more incoming edges are drawn
        already_moved.add(bbl_uid)

        # thumb code
        if not D.InsExists(bbl['address']):
          dbg("WARNING ignoring block at 0x%x" % bbl['address'])
          continue

        # maybe this is a function entry point
        if D.BblIsPossiblyFunctionEntry(D.InsBbl(bbl['address'])):
          dbg("0x%x is function entry point" % bbl['address'])
          continue

        # mark the blocks in this function
        partitioning.UnmarkAllBlocks()
        for b_uid, b in I.FunctionBblIterator(bbl['function_uid']):
          partitioning.MarkBlock(b['address'], I.BblEndAddress(b_uid))

        dbg("================================================================================================ %d" % counter)
        counter += 1

        # select the candidate blocks to be moved
        partitioning.subcfg_forward = True
        partitioning.subcfg_backward = False
        partitioning.subcfg_backforth = False
        blocks, _, succs = partitioning.SelectSubCfgFromMarkedBlocks(bbl['address'], True, True)

        # repartition partially
        for block in blocks:
          partitioning.MarkBlock2(block)

        dbg(" = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =")

        if len(succs) == 0:
          dbg("no successors")
          continue
        #endif len(succs) == 0

        g_moved_blocks.clear()

        partitioning.subcfg_forward = False
        partitioning.subcfg_backward = False
        partitioning.subcfg_backforth = False
        _, _, nr_moved_blocks = partitioning.repartition([0], succs, True, False, True, False, True, False, True, 2)

        for k in sorted(g_moved_blocks.keys()):
          v = g_moved_blocks[k]
          dbg("MOVED 0x%x-0x%x to %d" % (v['start'], v['end'], v['target']))

        nr_reassoc += nr_moved_blocks

        if nr_moved_blocks > 0:
          change = True
      #endif no incoming edges
    #endfor bbl iterator

    global_change |= change
  #endwhile fixpoint

  dbg("  reassociated %d basic blocks in %d passes" % (nr_reassoc, nr_passes))

  return global_change

def fraction_inter(x, selector):
  interlib_edges = x & (edge_information['inter%s' % selector])
  return len(interlib_edges) * factor([len(x)])

def diablo_number_incoming(D, i):
  counter = 0

  if D.InsExists(i):
    for _ in D.BblIncomingEdgeIterator(D.InsBbl(i), True, False):
      counter += 1

  return counter

def diablo_number_outgoing(D, i):
  counter = 0

  if D.InsExists(i):
    for _ in D.BblOutgoingEdgeIterator(D.InsBbl(i), True, False):
      counter += 1

  return counter

def have_to_consider(D, I, edge):
  result = True
  reason = ""

  branch_ins = edge['branch']
  tail_ins = edge['tail']

  p_branch_ins = I.HandleProducers(branch_ins)

  # filter out edges that don't have to be drawn
  if (edge['type'] == Tool.EDGE_FALLTHROUGH) and (not I.InsIsCall(p_branch_ins) or (not I.InsExists(p_branch_ins) or not I.InsExists(edge['tail'])) or I.InsInSameBbl(p_branch_ins, edge['tail'])): #(I.InsInSameBbl(p_branch_ins, edge['tail']) or ((I.InsBbl(edge['branch']) == Tool.INVALID_BBL) and (I.InsBbl(edge['tail']) == Tool.INVALID_BBL))):
    # check if successor has more than one incoming edge
    nr_succ_incoming = diablo_number_incoming(D, tail_ins)
    nr_outgoing = 0
    for _ in D.BblOutgoingEdgeIterator(D.InsBbl(p_branch_ins), True, True):
      nr_outgoing += 1

    if not(nr_succ_incoming > 1) and not(nr_outgoing > 1):
      # fallthrough edge is drawn in Diablo, but IDA put head and tail in the same block
      reason = "fallthrough in same block"
      result = False
    else:
      dbg("FALLTHROUGH 0x%x->0x%x has multiple in/out edges %d/%d" % (p_branch_ins, tail_ins, nr_outgoing, nr_succ_incoming))

  if edge['type'] == Tool.EDGE_CALLFALLTHROUGH:
    nr_succ_incoming = diablo_number_incoming(D, tail_ins)

    if not(nr_succ_incoming > 1):
      # call fallthrough edges are pseudo-edges
      reason = "call-fallthrough (%d)" % I.InsExists(edge['head'])
      result = False
    else:
      dbg("CALL-FALLTHROUGH 0x%x->0x%x has multiple in edges %d" % (p_branch_ins, tail_ins, nr_succ_incoming))

  if (edge['type'] == Tool.EDGE_FALLTHROUGH) and I.InsIsCall(p_branch_ins):
    # conditional branch-and-link is rare
    reason = "fallthrough from call"
    result = False

  if I.InsIsSwitch(branch_ins) and (tail_ins in I.SwitchTargets(branch_ins) or tail_ins == I.SwitchDefault(branch_ins)):
    # direct switch edge
    reason = "switch"
    result = False

  if D.InsIsData(edge['tail']):
    # e.g., where ARMv8 code is compiled into the binary
    reason = "going to data"
    result = False

  return result, reason

def calculate(D, pI):
  global I
  I = pI

  global nr_eliminated, nr_eliminated_drawn, g_edges_eliminated

  # edge UIDs of edges that are not drawn
  g_edges_eliminated = set()

  # repartition
  partitioning.Init()
  for start, end in D.PartitioningIgnoreSwitchRelatedEdges():
      partitioning.IgnoreEdge(start, end)

  D.collect_links(same_function)

  change = True
  iteration = 1
  while change:
    dbg("iteration %d" % iteration)
    # STEP 0.1: eliminate not-drawn edges
    change1 = eliminate(D, I)
    # STEP 0.2: reassociate functions
    change2 = reassoc_function(D, I)

    change = change1 & change2

    print("STATUS for iteration %d" % iteration)
    D.collect_links(same_function)

    iteration += 1
  #endwhile

  # STEP 4.1: calculate number of false positives (= fake edge drawn)
  # STEP 4.2: calculate number of false negatives (= real edge not drawn)
  print("calculating false positives/negatives...")
  result = {
    'gt_edge_count': 0,
    'gt_fake_edge_count': 0,
    'functionless': I.InsCountNotInFunction(),

    'false_positives_gui': 0,
    'false_positives_gui_inter_archive': 0,
    'false_positives_gui_inter_object': 0,
    'false_positives_gui_inter_function': 0,
    'false_positives_gui_intra_archive': 0,
    'false_positives_gui_intra_object': 0,
    'false_positives_gui_intra_function': 0,

    'false_positives_api': 0,
    'false_positives_api_inter_archive': 0,
    'false_positives_api_inter_object': 0,
    'false_positives_api_inter_function': 0,
    'false_positives_api_intra_archive': 0,
    'false_positives_api_intra_object': 0,
    'false_positives_api_intra_function': 0,

    'false_positives_eliminated': 0,
    'false_positives_callfallthrough': 0,
    'false_positives_callfallthrough_to_dispatcher': 0,
    'false_positives_callfallthrough_from_dispatcher': 0,
    'false_positives_fallthrough': 0,
    'false_positives_fallthrough_to_dispatcher': 0,
    'false_positives_fallthrough_from_dispatcher': 0,
    'false_positives_jump': 0,
    'false_positives_jump_to_dispatcher': 0,
    'false_positives_jump_from_dispatcher': 0,
    'false_positives_from_obfuscation': 0,
    'false_positives_from_uncond_branch': 0,
    'false_positives_from_factoring': 0,

    'false_negatives_gui': 0,
    'false_negatives_gui_inter_archive': 0,
    'false_negatives_gui_inter_object': 0,
    'false_negatives_gui_inter_function': 0,
    'false_negatives_gui_intra_archive': 0,
    'false_negatives_gui_intra_object': 0,
    'false_negatives_gui_intra_function': 0,

    'false_negatives_api': 0,
    'false_negatives_api_inter_archive': 0,
    'false_negatives_api_inter_object': 0,
    'false_negatives_api_inter_function': 0,
    'false_negatives_api_intra_archive': 0,
    'false_negatives_api_intra_object': 0,
    'false_negatives_api_intra_function': 0,

    'false_negatives_gui_mapped': 0,
    'false_negatives_gui_mapped_to_dispatcher': 0,
    'false_negatives_gui_mapped_from_dispatcher': 0,
    'false_negatives_gui_mapped_switch': 0,

    'false_negatives_callfallthrough': 0,
    'false_negatives_callfallthrough_from_data': 0,
    'false_negatives_callfallthrough_to_data': 0,
    'false_negatives_callfallthrough_fromto_data': 0,
    'false_negatives_callfallthrough_to_dispatcher': 0,
    'false_negatives_callfallthrough_from_dispatcher': 0,
    'false_negatives_fallthrough': 0,
    'false_negatives_fallthrough_from_data': 0,
    'false_negatives_fallthrough_to_data': 0,
    'false_negatives_fallthrough_fromto_data': 0,
    'false_negatives_fallthrough_to_dispatcher': 0,
    'false_negatives_fallthrough_from_dispatcher': 0,
    'false_negatives_jump': 0,
    'false_negatives_jump_from_data': 0,
    'false_negatives_jump_to_data': 0,
    'false_negatives_jump_fromto_data': 0,
    'false_negatives_jump_to_dispatcher': 0,
    'false_negatives_jump_from_dispatcher': 0,

    'tuples_both_hanging': 0,
    'tuples_one_hanging': 0,
    'tuples_both_other': 0,
    'tuples_both_same': 0,

    'nr_obfuscations': 0,
    'nr_obfuscations_eliminated': 0,
  }

  fn_statistics = {}
  fn_statistics_addresses = {}

  def RecordFN(d_edge):
    _, _, a, _, _ = D.InsOrigin(d_edge['branch'])
    if len(a) > 1:
      dbg("not recording FN from 0x%x because multiple archives %s" % (d_edge['branch'], a))
      return
    assert len(a) == 1, "0x%x" % d_edge['branch']
    a = a[0]

    if a not in fn_statistics:
      fn_statistics[a] = {}
      fn_statistics_addresses[a] = {}

    opcode = D.InsOpcode(d_edge['branch'])
    if opcode not in fn_statistics[a]:
      fn_statistics[a][opcode] = 0
      fn_statistics_addresses[a][opcode] = set()

    fn_statistics[a][opcode] += 1
    fn_statistics_addresses[a][opcode].add('0x%x' % d_edge['branch'])

  def RecordEdge(diablo_edge_uid, prefix):
    is_inter_fun, is_inter_obj, is_inter_arc = D.EdgeIsInter(diablo_edge_uid)

    result[prefix] += 1

    # inter
    if is_inter_arc:
      result['%s_inter_archive' % prefix] += 1
      result['%s_inter_object' % prefix] += 1
      result['%s_inter_function' % prefix] += 1
    elif is_inter_obj:
      result['%s_inter_object' % prefix] += 1
      result['%s_inter_function' % prefix] += 1
    elif is_inter_fun:
      result['%s_inter_function' % prefix] += 1

    # intra
    if not is_inter_fun:
      edge_type = 'UNKNOWN'
      if D.EdgeIsOriginallySwitch(diablo_edge_uid):
        edge_type = 'SWITCH'
      elif D.EdgeIsSwitchFallthrough(diablo_edge_uid):
        edge_type = 'SWITCH-FT'

      dbg("intra function edge %s (%s) %s" % (edge_type, prefix, D.EdgeToString(diablo_edge_uid)))
      result['%s_intra_function' % prefix] += 1
      result['%s_intra_object' % prefix] += 1
      result['%s_intra_archive' % prefix] += 1
    elif not is_inter_obj:
      result['%s_intra_object' % prefix] += 1
      result['%s_intra_archive' % prefix] += 1
    elif not is_inter_arc:
      result['%s_intra_archive' % prefix] += 1
  #enddef RecordEdge

  def InsPartOfObfuscationFactoring(i):
    obf = False
    af = False

    if D.InsIsPartOfObfuscationTransformation(i):
      obf = True
    elif D.InsIsPartOfFactoringTransformation(i):
      af = True
    else:
      # need to check for trampoline
      b = D.InsBbl(i)
      if (D.BblIsTrampoline(b)):
        # incoming edges
        count = 0
        for _, edge in D.BblIncomingEdgeIterator(b, True, True):
          obf, af = InsPartOfObfuscationFactoring(edge['branch'])
          count += 1
        #endfor
        # this test seems to fail in some legit cases
        # assert count == 1, "Expected only one incoming edge for 0x%x" % i
      #endif
    #endif

    return obf, af
  #enddef InsPartOfObfuscationFactoring

  diablo_mapped_edges = set()
  for ida_edge_uid, all_diablo_edge_uid in I.MappedEdgeIterator():
    for diablo_edge_uid in all_diablo_edge_uid:
      diablo_mapped_edges.add(diablo_edge_uid)

      if ida_edge_uid in g_edges_eliminated:
        result['false_positives_eliminated'] += 1
        continue
      #endif

      if D.EdgeIsFake(diablo_edge_uid):
        RecordEdge(diablo_edge_uid, 'false_positives_api')

        if I.EdgeDrawn(ida_edge_uid, False):

          edge = I.EdgeByUID(ida_edge_uid)

          edge_type = 'UNKNOWN'
          if D.EdgeIsOriginallySwitch(diablo_edge_uid):
            edge_type = 'SWITCH'
          elif D.EdgeIsSwitchFallthrough(diablo_edge_uid):
            edge_type = 'SWITCH-FT'
          transformation_type = 'UNKNOWN'
          if D.InsIsPartOfFactoringTransformation(edge['branch']):
            transformation_type = 'factoring'
          elif D.InsIsPartOfObfuscationTransformation(edge['branch']):
            transformation_type = 'obfuscation'

          dbg("FP(%s) %s(%d) %s" % (edge_type, transformation_type, D._TransformationIdUID(D.InsTransformationID(edge['branch'])), D.EdgeToString(diablo_edge_uid)))
          RecordEdge(diablo_edge_uid, 'false_positives_gui')

          reason = ""
          if edge['type'] == Tool.EDGE_CALLFALLTHROUGH:
            reason = "callfallthrough"
          elif edge['type'] == Tool.EDGE_FALLTHROUGH:
            reason = "fallthrough"
          elif edge['type'] == Tool.EDGE_JUMP:
            reason = "jump"
          #endif

          goes_to_dispatcher = diablo_edge_uid in D._af_dispatchers_incoming_edges
          comes_from_dispatcher = diablo_edge_uid in D._af_dispatchers_outgoing_edges
          if goes_to_dispatcher:
            result['false_positives_%s_to_dispatcher' % (reason)] += 1
          elif comes_from_dispatcher:
            result['false_positives_%s_from_dispatcher' % (reason)] += 1

          obf, af = InsPartOfObfuscationFactoring(edge['branch'])
          assert not (obf and af), "0x%x can't be part of obfuscation and factoring at the same time! %s" % (edge['branch'], D.EdgeToString(diablo_edge_uid))

          if obf:
            result['false_positives_from_obfuscation'] += 1
          elif af:
            result['false_positives_from_factoring'] += 1
          else:
            print("WARNING 0x%x not part of expected transformation! %s" % (edge['branch'], D.EdgeToString(diablo_edge_uid)))
            # assert False, "0x%x not part of expected transformation! %s" % (edge['branch'], D.EdgeToString(diablo_edge_uid))

        # EdgeDrawn
      # EdgeIsFake
    #endfor
  # MappedEdgeIterator

  # maybe not all Diablo (ground truth) edges are drawn
  diablo_hard_ignored = set()

  # count number of fallthrough edges that will be removed by IDA
  nr_fallthrough = 0
  nr_callfallthrough = 0

  gt_not_considered = {}
  for edge_uid, edge in D.EdgeIterator(False):
    dbg("doing diablo edge %d" % edge_uid)
    if edge_uid % 5000 == 0:
      print("PROGRESS diablo edge %d" % edge_uid)
    goes_to_dispatcher = edge_uid in D._af_dispatchers_incoming_edges
    comes_from_dispatcher = edge_uid in D._af_dispatchers_outgoing_edges

    if (not D.InsInBbl(edge['branch'])) or (not D.InsInBbl(edge['tail'])):
      # no need to count if not possible, we don't do anything with these counts for now anyways
      # should we do that in the future, however, we should take care to handle this case
      print("ERROR(%s) %d %d %d" % (D.EdgeToString(edge_uid), D.InsInBbl(edge['branch']), D.InsInBbl(edge['tail']), edge_uid in diablo_mapped_edges))
      pass
    else:
      if D.InsIsData(edge['tail']) or ((D.BblNrIncomingEdges(D.InsBbl(edge['tail'])) == 1) and (D.BblNrOutgoingEdges(D.InsBbl(edge['branch'])) == 1)):
        if edge['type'] == Tool.EDGE_FALLTHROUGH:
          nr_fallthrough += 1
        elif edge['type'] == Tool.EDGE_CALLFALLTHROUGH:
          nr_callfallthrough += 1
      #endif
    #endif

    if edge_uid in diablo_mapped_edges:
      # for the ground truth:
      #  we have found an equivalent edge in the IDA CFG
      dbg("  mapped: %s" % D.EdgeToString(edge_uid))

      skip_count = False
      reason = ""
      if edge['type'] == Tool.EDGE_CALLFALLTHROUGH:
        if I.InsInSameBbl(edge['branch'], edge['tail']):
          reason = "call-ft-same-block-0"
          skip_count = True

      if skip_count:
        diablo_hard_ignored.add(edge_uid)
        dbg("NOTEDGE %s: %s" % (D.EdgeToString(edge_uid), reason))
        if reason not in gt_not_considered:
          gt_not_considered[reason] = 0
        gt_not_considered[reason] += 1
      else:
        dbg("COUNTING %s" % D.EdgeToString(edge_uid))

        result['gt_edge_count'] += 1
        if D.EdgeIsFake(edge_uid):
          result['gt_fake_edge_count'] += 1
        else:
          ida_edge_uid = I.GroundTruthEdgeToSelf(edge_uid)
          assert ida_edge_uid is not None
          if (ida_edge_uid in g_edges_eliminated) or (not I.EdgeDrawn(ida_edge_uid, False)):
            RecordEdge(edge_uid, 'false_negatives_gui')
            RecordFN(edge)
            dbg("FALSE_NEGATIVE mapped %s %d/%d" % (D.EdgeToString(edge_uid), goes_to_dispatcher, comes_from_dispatcher))

            suffix = ''
            if goes_to_dispatcher:
              suffix = '_to_dispatcher'
            elif comes_from_dispatcher:
              suffix = '_from_dispatcher'

            result['false_negatives_gui_mapped%s' % suffix] += 1
            if D.EdgeIsOriginallySwitch(edge_uid):
              result['false_negatives_gui_mapped_switch'] += 1
      #endif

    else:
      # for the ground truth:
      #  we have _NOT_ found an equivalent edge in the IDA CFG
      dbg("  not mapped: %s" % (D.EdgeToString(edge_uid)))

      one_hanging = I.InsNotInFunction(edge['branch']) or I.InsNotInFunction(edge['tail'])

      handled = False
      reason = ""

      if D.InsIsData(edge['tail']):
        dbg("going to data")
        reason = "to-data"
        handled = True

      elif edge['type'] == Tool.EDGE_CALLFALLTHROUGH:
        # call to PLT?
        if edge['branch'] in D._plt_calls:
          names = D._plt_entries[D._plt_calls[edge['branch']]]
          if ("abort" in names) or ("exit" in names) or ("__assert_fail" in names) or ("siglongjmp" in names):
            dbg("calling abort-like function from 0x%x: %s" % (edge['branch'], names))
            reason = "call-ft-abort"
            handled = True
        if not handled and not one_hanging and I.InsInSameBbl(edge['branch'], edge['tail']):
          dbg("call-ft in same block 1")
          reason = "call-ft-same-block-1"
          handled = True
        if not handled and one_hanging and (diablo_number_incoming(D, edge['tail']) == 1):
          dbg("call-ft in same block 2")
          reason = "call-ft-same-block-2"
          handled = True

      elif edge['type'] == Tool.EDGE_FALLTHROUGH:
        if (not one_hanging) and I.InsInSameBbl(edge['branch'], edge['tail']):
          # fallthrough where
          # - no instructions are functionless
          # - both have been put in the same block by IDA
          # here we assume that IDA was able to analyse the instruction proper
          dbg("handled fallthrough in same block 1")
          reason = "ft-same-block-1"
          handled = True
        elif one_hanging and (((diablo_number_incoming(D, edge['tail']) == 1) and (diablo_number_outgoing(D, edge['branch']) == 1)) or D.InsInSameBbl(edge['tail'], edge['branch'])):
          # fallthrough where
          # - one or both instructions are functionless
          # - head block has only the fallthrough edge outgoing
          # - tail block has only the fallthrough edge incoming
          # - Diablo put both instructions in the same block
          dbg("handled fallthrough in same block 2")
          reason = "ft-same-block-2"
          handled = True
        #endif
      #endif

      if not handled:
        dbg("COUNTING %s" % D.EdgeToString(edge_uid))

        result['gt_edge_count'] += 1
        if D.EdgeIsFake(edge_uid):
          result['gt_fake_edge_count'] += 1

        count_edge_as_false_negative = False

        if edge['type'] == Tool.EDGE_CALLFALLTHROUGH:
          count_edge_as_false_negative = True
          reason = "callfallthrough"

        elif edge['type'] == Tool.EDGE_FALLTHROUGH:
          count_edge_as_false_negative = True
          reason = "fallthrough"

        elif edge['type'] == Tool.EDGE_JUMP:
          count_edge_as_false_negative = True
          reason = "jump"

        assert count_edge_as_false_negative

        if count_edge_as_false_negative:
          dbg("counting as false negative")
          if not D.EdgeIsFake(edge_uid):
            # this can be a false negative
            ida_edge_uid = I.GroundTruthEdgeToSelf(edge_uid)

            suffix = ''
            if goes_to_dispatcher:
              suffix = '_to_dispatcher'
            elif comes_from_dispatcher:
              suffix = '_from_dispatcher'

            if ida_edge_uid is None:
              # edge is not found in IDA at all
              dbg("GT edge %d not found %s: %s" % (edge_uid, D.EdgeToString(edge_uid), reason))

              RecordFN(edge)
              RecordEdge(edge_uid, 'false_negatives_gui')
              RecordEdge(edge_uid, 'false_negatives_api')

              dbg("FALSE_NEGATIVE %s %s %d/%d" % (reason, D.EdgeToString(edge_uid), goes_to_dispatcher, comes_from_dispatcher))
              result['false_negatives_%s%s' % (reason, suffix)] += 1

              if I.InsIsData(edge['branch']) and I.InsIsData(edge['tail']):
                dbg("fromto data")
                result['false_negatives_%s_fromto_data' % (reason)] += 1
              elif I.InsIsData(edge['branch']):
                dbg("from data")
                result['false_negatives_%s_from_data' % (reason)] += 1
              elif I.InsIsData(edge['tail']):
                dbg("to data")
                result['false_negatives_%s_to_data' % (reason)] += 1
              #endif

            elif (ida_edge_uid in g_edges_eliminated) or (not I.EdgeDrawn(ida_edge_uid, False)):
              # edge is found in IDA, but not drawn
              RecordEdge(edge_uid, 'false_negatives_gui')

              dbg("FALSE_NEGATIVE not_drawn %s %s %d/%d" % (reason, D.EdgeToString(edge_uid), goes_to_dispatcher, comes_from_dispatcher))
              result['false_negatives_gui_notdrawn_%s%s' % (reason, suffix)] += 1
      else:
        diablo_hard_ignored.add(edge_uid)
        dbg("NOTEDGE %s: %s" % (D.EdgeToString(edge_uid), reason))
        if reason not in gt_not_considered:
          gt_not_considered[reason] = 0
        gt_not_considered[reason] += 1
      #endif
  print("Edges from ground truth not considered: %s" % gt_not_considered)
  print("nr fallthrough %d, nr callfallthrough %d" % (nr_fallthrough, nr_callfallthrough))

  # collect information on the separated code (due to factoring)
  for a, b in D._af_splits:
    # 'a' and 'b' should have been put in the same function
    if I.InsNotInFunction(a) and I.InsNotInFunction(b):
      result['tuples_both_hanging'] += 1
    elif I.InsNotInFunction(a) or I.InsNotInFunction(b):
      result['tuples_one_hanging'] += 1
    elif I.InsFunction(a) != I.InsFunction(b):
      result['tuples_both_other'] += 1
    elif I.InsFunction(a) == I.InsFunction(b):
      result['tuples_both_same'] += 1
    else:
      assert False
  #endfor

  # STEP 1: construct list of edges per original (!) function
  print("ordering Diablo edges per original function...")
  not_considered = {}
  for diablo_edge_uid, diablo_edge in D.EdgeIterator(False):
    if diablo_edge_uid in diablo_hard_ignored:
      continue

    diablo_edge_head = diablo_edge['branch']
    diablo_edge_tail = diablo_edge['tail']
    diablo_edge_type = diablo_edge['type']
    diablo_edge_fake = diablo_edge['fake']

    # don't consider CALL-FT edges to data
    # this is due to limitations in Diablo's modeling of libc::exit()
    if diablo_edge_type == Tool.EDGE_CALLFALLTHROUGH and D.InsIsData(diablo_edge_tail):
      continue

    # don't do REAL edges going to DATA
    if D.InsIsData(diablo_edge_tail) and not diablo_edge_fake:
      continue

    # dbg("[%d] 0x%x -> 0x%x (%d)" % (diablo_edge_uid, diablo_edge_head, diablo_edge_tail, diablo_edge_type))

    # original functions
    head_f, _, _, _, _ = D.InsOrigin(diablo_edge_head)
    tail_f, _, _, _, _ = D.InsOrigin(diablo_edge_tail)
    # dbg("    H: %s" % head_f)
    # dbg("    T: %s" % tail_f)

    process_edge(head_f, tail_f, diablo_edge_uid, diablo_edge_fake, diablo_edge_head, diablo_edge_tail, diablo_edge_type)
  print("Edges not considered: %s" % not_considered)

  # assert len(set(gt_not_considered.items()) ^ set(not_considered.items())) == 0

  # STEP 2: process IDA edges
  print("processing IDA edges...")
  for ida_edge_uid, all_diablo_edge_uid in I.MappedEdgeIterator():
    for diablo_edge_uid in all_diablo_edge_uid:
      if diablo_edge_uid in diablo_hard_ignored:
        continue

      # fakeness, based on the Diablo result
      suffix = ''
      if D.EdgeIsFake(diablo_edge_uid):
        suffix = '_fake'

      # inter or intra library edge?
      is_inter_fun, is_inter_obj, is_inter_arc = D.EdgeIsInter(diablo_edge_uid)

      # determine category of IDA edge
      categories = ['ida_python' + suffix]
      if not((ida_edge_uid in g_edges_eliminated) or (not I.EdgeDrawn(ida_edge_uid, False))):
        categories.append('ida_gui' + suffix)

      for f, _ in edge_associations[diablo_edge_uid]:
        # don't look at 'c' for now, maybe later TODO
        for cat in categories:
          original_functions[f][cat].add(ida_edge_uid)

          if is_inter_arc:
            edge_information['interlib'].add(ida_edge_uid)
          else:
            edge_information['intralib'].add(ida_edge_uid)

            if is_inter_obj:
              edge_information['interobj'].add(ida_edge_uid)
            else:
              edge_information['intraobj'].add(ida_edge_uid)

              if is_inter_fun:
                edge_information['interfun'].add(ida_edge_uid)
              else:
                edge_information['intrafun'].add(ida_edge_uid)
              # is_inter_fun
            # is_inter_obj
          # is_inter_arc
        # categories
      # edge_associations
    #endfor all_diablo_edge_uid
  #endfor mapped edges

  data_by_function_size = {}
  for f_uid, _ in original_functions.items():
    f_size = D.FunctionSize(f_uid)
    if f_size not in data_by_function_size:
      data_by_function_size[f_size] = []
    data_by_function_size[f_size].append(f_uid)

  # STEP 3: emit data to CSV file
  outf_all = open(common.output_basename + "-all-statistics.csv", "w")
  print("Writing all data to %s" % os.path.realpath(outf_all.name))
  outf_all.write("function_size,fraction_python_real,fraction_python_fake,fraction_drawn_real,fraction_drawn_fake,fraction_total,fraction_total_drawn,fraction_drawn_real_interlib,fraction_drawn_fake_interlib\n")

  outf_mean = open(common.output_basename + "-mean-statistics.csv", "w")
  print("Writing mean data to %s" % os.path.realpath(outf_mean.name))
  outf_mean.write("function_size,function_count,fraction_python_real,fraction_python_fake,fraction_drawn_real,fraction_drawn_fake,fraction_total,fraction_total_drawn,fraction_drawn_real_interlib,fraction_drawn_fake_interlib\n")

  for f_size, f_uids in common.SortedDictionaryIterator(data_by_function_size):
    total_fraction_total = 0
    total_fraction_total_drawn = 0

    total_fraction_real = 0
    total_fraction_drawn_real = 0
    total_fraction_drawn_real_interlib = 0
    total_fraction_drawn_real_interobj = 0
    total_fraction_drawn_real_interfun = 0

    total_fraction_fake = 0
    total_fraction_drawn_fake = 0
    total_fraction_drawn_fake_interlib = 0
    total_fraction_drawn_fake_interobj = 0
    total_fraction_drawn_fake_interfun = 0

    mean_factor = 1/len(f_uids)

    for f_uid in f_uids:
      # doing function with original uid 'f_uid'
      data = original_functions[f_uid]

      diablo_total_real = len(data['in']) + len(data['intra']) + len(data['out'])
      diablo_total_fake = len(data['in_fake']) + len(data['intra_fake']) + len(data['out_fake'])

      # real control flow
      fraction_real = len(data['ida_python']) * factor([diablo_total_real])
      fraction_drawn_real = len(data['ida_gui']) * factor([diablo_total_real])
      fraction_drawn_real_interlib = fraction_inter(data['ida_gui'], 'lib')
      fraction_drawn_real_interobj = fraction_inter(data['ida_gui'], 'obj')
      fraction_drawn_real_interfun = fraction_inter(data['ida_gui'], 'fun')

      # fake control flow
      fraction_fake = len(data['ida_python_fake']) * factor([diablo_total_fake])
      fraction_drawn_fake = len(data['ida_gui_fake']) * factor([diablo_total_fake])
      fraction_drawn_fake_interlib = fraction_inter(data['ida_gui_fake'], 'lib')
      fraction_drawn_fake_interobj = fraction_inter(data['ida_gui_fake'], 'obj')
      fraction_drawn_fake_interfun = fraction_inter(data['ida_gui_fake'], 'fun')

      fraction_total = (len(data['ida_python']) + len(data['ida_python_fake'])) * factor([diablo_total_real, diablo_total_fake])
      fraction_total_drawn = (len(data['ida_gui']) + len(data['ida_gui_fake'])) * factor([diablo_total_real, diablo_total_fake])

      outf_all.write("%d,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f\n" % (f_size, fraction_real, fraction_fake, fraction_drawn_real, fraction_drawn_fake, fraction_total, fraction_total_drawn, fraction_drawn_real_interlib, fraction_drawn_fake_interlib, fraction_drawn_real_interobj, fraction_drawn_fake_interobj, fraction_drawn_real_interfun, fraction_drawn_fake_interfun))

      # TOTAL real control flow
      total_fraction_real                += fraction_real * mean_factor
      total_fraction_drawn_real          += fraction_drawn_real * mean_factor
      total_fraction_drawn_real_interlib += fraction_drawn_real_interlib * mean_factor
      total_fraction_drawn_real_interobj += fraction_drawn_real_interobj * mean_factor
      total_fraction_drawn_real_interfun += fraction_drawn_real_interfun * mean_factor

      # TOTAL fake control flow
      total_fraction_fake                += fraction_fake * mean_factor
      total_fraction_drawn_fake          += fraction_drawn_fake * mean_factor
      total_fraction_drawn_fake_interlib += fraction_drawn_fake_interlib * mean_factor
      total_fraction_drawn_fake_interobj += fraction_drawn_fake_interobj * mean_factor
      total_fraction_drawn_fake_interfun += fraction_drawn_fake_interfun * mean_factor

      total_fraction_total               += fraction_total * mean_factor
      total_fraction_total_drawn         += fraction_total_drawn * mean_factor

    outf_mean.write("%d,%d,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f\n" % (f_size, len(f_uids), total_fraction_real, total_fraction_fake, total_fraction_drawn_real, total_fraction_drawn_fake, total_fraction_total, total_fraction_total_drawn, total_fraction_drawn_real_interlib, total_fraction_drawn_fake_interlib, total_fraction_drawn_real_interobj, total_fraction_drawn_fake_interobj, total_fraction_drawn_real_interfun, total_fraction_drawn_fake_interfun))

  outf_all.close()
  outf_mean.close()

  outf_data = open(common.output_basename + "-data.txt", "w")
  outf_data.write("gt_edges:%d\n" % result['gt_edge_count'])
  outf_data.write("gt_edges_fake:%d\n" % result['gt_fake_edge_count'])
  outf_data.write("false_positives_gui:%d\n" % result['false_positives_gui'])
  outf_data.write("false_positives_api:%d\n" % result['false_positives_api'])
  outf_data.write("false_negatives_gui:%d\n" % result['false_negatives_gui'])
  outf_data.write("false_negatives_api:%d\n" % result['false_negatives_api'])
  outf_data.write("gt_instructions:%d\n" % D.InsCount())
  outf_data.write("ida_instructions:%d\n" % I.InsCount())
  outf_data.write("ida_instructions_hanging:%d\n" % I.InsCountNotInFunction())
  outf_data.write("eliminated:%d\n" % nr_eliminated)
  outf_data.write("eliminated_and_drawn:%d\n" % nr_eliminated_drawn)
  outf_data.close()

  result['nr_obfuscations'] = D._nr_obfuscations
  result['nr_obfuscations_eliminated'] = nr_eliminated

  # collect elimination statistics
  elimination_stats = {
    'skipped': 0,
    'eliminated': 0,
    'not_in_same_function': 0,
    'incoming_fake': 0,
    'total': 0,
  }
  for tf_uid, state in eliminated_statistics.items():
    if state == ELIMINATED_STATE_ELIMINATED:
      elimination_stats['eliminated'] += 1
    elif state == ELIMINATED_STATE_FAKE_IN:
      elimination_stats['incoming_fake'] += 1
    elif state == ELIMINATED_STATE_NOT_SAME_FUNCTION:
      elimination_stats['not_in_same_function'] += 1
    elif state == ELIMINATED_STATE_SKIP:
      elimination_stats['skipped'] += 1

    elimination_stats['total'] += 1
  #endfor

  print(elimination_stats)
  # print(fn_statistics)
  # print(fn_statistics_addresses)
  return result
