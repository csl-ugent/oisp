_marked_blocks_start = set()
_marked_blocks_start_2 = set()
_marked_blocks_start_to_end = {}
_marked_blocks_end_to_start = {}
_ignored_edges = {}

_debug = False

fn_incoming_insns = None
fn_outgoing_insns = None
fn_next_ins = None
fn_ins_is_call = None
fn_get_block_start_address = None
fn_get_block_end_address = None
fn_get_function = None
fn_get_function_start = None
fn_move_block = None
fn_ins_iterator = None
fn_edge_consider = None
fn_ins_in_block = None
fn_filter_predsucc = None
fn_dump_ida_db = None
fn_decodable = None
fn_print = None

subcfg_forward = True
subcfg_backward = True
subcfg_backforth = True
# integer to indicate how many additional times a fallthrough block is considered
prioritize_fallthrough = 0

_repartition_count = 0

def Init():
  global _marked_blocks_start, _marked_blocks_start_to_end, _marked_blocks_end_to_start
  global _ignored_edges
  global _repartition_count

  _marked_blocks_start.clear()
  _marked_blocks_start_2.clear()
  _marked_blocks_start_to_end.clear()
  _marked_blocks_end_to_start.clear()
  _ignored_edges.clear()

  _repartition_count = 0

def MarkBlock(i, i_end):
  global _marked_blocks_start, _marked_blocks_start_to_end, _marked_blocks_end_to_start

  _marked_blocks_start.add(i)
  _marked_blocks_start_to_end[i] = i_end
  _marked_blocks_end_to_start[i_end] = i

def MarkBlock2(i):
  _marked_blocks_start_2.add(i)

def IgnoreEdge(From, To):
  global _ignored_edges

  if From not in _ignored_edges:
    _ignored_edges[From] = set()

  _ignored_edges[From].add(To)

def IsEdgeIgnored(From, To):
  if From not in _ignored_edges:
    return False

  return To in _ignored_edges[From]

def UnmarkBlock(i):
  global _marked_blocks_start, _marked_blocks_start_to_end, _marked_blocks_end_to_start, _marked_blocks_start_2

  assert IsBlockMarked(i)

  _marked_blocks_start.discard(i)
  _marked_blocks_start_2.discard(i)
  i_end = _marked_blocks_start_to_end[i]
  del _marked_blocks_start_to_end[i]
  del _marked_blocks_end_to_start[i_end]

def UnmarkAllBlocks():
  global _marked_blocks_start, _marked_blocks_start_to_end, _marked_blocks_end_to_start

  _marked_blocks_start.clear()
  _marked_blocks_start_to_end.clear()
  _marked_blocks_end_to_start.clear()

def UnmarkAllBlocks2():
  _marked_blocks_start_2.clear()

def IsBlockMarked(i, selector = 1):
  if selector == 2:
    return i in _marked_blocks_start_2

  return i in _marked_blocks_start

def IsBlockMarkedEnd(i, selector = 1):
  if selector == 2:
    if i in _marked_blocks_end_to_start:
      return _marked_blocks_end_to_start[i] in _marked_blocks_start_2
    else:
      return False

  return i in _marked_blocks_end_to_start

def MarkedBlockIterator():
  for i in _marked_blocks_start:
    yield i

def _IgnoreEdge(a, b, is_successor_edge = False):
  if is_successor_edge:
    return IsEdgeIgnored(a, b)

  return ((fn_edge_consider is not None) and (not fn_edge_consider(a, b))) or IsEdgeIgnored(a, b)

def IncomingMarkedBlockIterator(i, selector = 1):
  for incoming_ins in fn_incoming_insns(i):
    if (not IgnoreEdge(incoming_ins, i)) and IsBlockMarkedEnd(incoming_ins, selector):
      yield _marked_blocks_end_to_start[incoming_ins]

def OutgoingMarkedBlockIterator(i, selector = 1):
  for outgoing_ins in fn_outgoing_insns(i):
    if (not IgnoreEdge(i, outgoing_ins)) and IsBlockMarked(outgoing_ins, selector):
      yield outgoing_ins

def OutgoingBlockIterator(i, selector = 1):
  for outgoing_ins in fn_outgoing_insns(i):
    if not IgnoreEdge(i, outgoing_ins):
      yield outgoing_ins

def InsAreFallthrough(a, b):
  # if fn_next_ins is not None:
  #   return b == fn_next_ins(a)

  # assuming ARM here
  return b == a+4

def IsDecodable(i):
  if fn_decodable is not None:
    return fn_decodable(i)

  return True

# last 3 arguments are to speed up the process and avoid unnecessary work
def SelectSubCfgFromMarkedBlocks(start, allow_marked_in, allow_marked_out, selector = 1):
  def StopAt(successor, selector):
    for predecessor in fn_incoming_insns(successor):
      if _IgnoreEdge(predecessor, successor):
        fn_print("  ignore edge 0x%x-0x%x" % (predecessor, successor))
        continue

      if not IsBlockMarkedEnd(predecessor, selector):
        # block is not marked
        return True
      #endif
    #endfor incoming

    return False
  #end StopAt

  if not IsBlockMarked(start, selector):
    if fn_dump_ida_db is not None:
      fn_dump_ida_db('assertion-failure')
  assert IsBlockMarked(start, selector)

  if _debug:
    fn_print("START at 0x%x" % start)

  marked_instructions = set()
  marked_blocks = set()
  succs = []
  preds = []

  # starting from the 'start' block,
  # - we select the marked blocks that are forward-reachable until a block is reached that has an incoming edge from a non-marked block
  # - we select the marked blocks that are backward-reachable
  visited = {}
  worklist = [[start, True]]
  while len(worklist) > 0:
    data = worklist.pop()
    subject = data[0]
    do_succs = data[1]

    assert IsBlockMarked(subject, selector)
    subject_end = _marked_blocks_start_to_end[subject]

    if subject not in visited:
      visited[subject] = []
    if do_succs in visited[subject]:
      # this combination has been done already
      continue
    visited[subject].append(do_succs)

    if _debug:
      fn_print("BLOCK 0x%x-0x%x (%d)" % (subject, subject_end, do_succs))

    # MARK BLOCK AND INSTRUCTIONS =============================================
    if _debug:
      fn_print("  MARK")
    marked_blocks.add(subject)

    if fn_ins_iterator is None:
      assert fn_next_ins is not None

      mark_address = subject
      while True:
        # mark one instruction
        marked_instructions.add(mark_address)

        # entire basic block done?
        if mark_address == subject_end:
          break
        mark_address = fn_next_ins(mark_address)
      #endwhile
    else:
      for mark_address in fn_ins_iterator(subject):
        marked_instructions.add(mark_address)
    #endif fn_ins_iterator

    # PROCESS SUCCESSORS ======================================================
    process_successors = do_succs and subcfg_forward

    look_at_successors = True
    if not IsDecodable(subject_end) or fn_ins_is_call(subject_end):
      # block ends in call, don't process successors
      # as they are supposed to be part of another function
      if _debug:
        fn_print("  NOT MARKING SUCCESSORS (outgoing call) 0x%x" % subject_end)
      look_at_successors = False

    # process successors if needed
    # but also collect successors
    if look_at_successors:
      for successor in fn_outgoing_insns(subject_end):
        if _IgnoreEdge(subject_end, successor, True):
          if _debug:
            fn_print("ignoring edge 0x%x-0x%x" % (subject_end, successor))
          continue

        if fn_filter_predsucc and fn_filter_predsucc(successor):
          if _debug:
            fn_print("filter out successor 0x%x" % successor)
          continue

        if successor == subject:
          # skip self-refering BBLs
          if _debug:
            fn_print("ignoring self loop")
          continue

        if (not process_successors) or (not IsBlockMarked(successor, selector)) or StopAt(successor, selector):
          # don't do anything with this successor
          if _debug:
            fn_print("  OUTGOING 0x%x" % successor)

          if (prioritize_fallthrough > 1) and InsAreFallthrough(subject, successor):
            succs.extend([successor for i in range(prioritize_fallthrough-1)])
          succs.append(successor)

          if (not allow_marked_out) and IsBlockMarked(successor, selector):
            if _debug:
              fn_print("not allowed marked out, early exit")
            return None, None, None
        else:
          worklist.append([successor, True])
        #endif
      #endfor outgoing
    #endif process_successors

    # PROCESS PREDECESSORS ====================================================
    process_predecessors = subcfg_backward

    if process_predecessors:
      for predecessor in fn_incoming_insns(subject):
        if not IsBlockMarkedEnd(predecessor, selector):
          process_predecessors = False
      #endfor incoming
    #endif process_predecessors

    for predecessor_ in fn_incoming_insns(subject):
      if _IgnoreEdge(predecessor_, subject):
        if _debug:
          fn_print("ignoring2 0x%x-0x%x" % (predecessor_, subject))
        continue

      if fn_filter_predsucc and fn_filter_predsucc(predecessor_):
        if _debug:
          fn_print("filter out predecessor 0x%x" % predecessor_)
        continue

      predecessor = fn_get_block_start_address(predecessor_)
      if predecessor is None:
        # still a hanging block
        continue

      if predecessor == subject:
        continue

      if process_predecessors:
        if IsBlockMarked(predecessor):
          worklist.append([predecessor, subcfg_backforth])
      else:
        # don't do anything with this predecessor
        if _debug:
          fn_print("  INCOMING 0x%x" % predecessor)

        if (prioritize_fallthrough > 1) and InsAreFallthrough(predecessor_, subject):
          succs.extend([predecessor for i in range(prioritize_fallthrough-1)])
        preds.append(predecessor)

        if (not allow_marked_in) and IsBlockMarked(predecessor, selector):
          if _debug:
            fn_print("not allowed marked in, early exit")
          return None, None, None
      #endif
    #endfor
  #endwhile worklist

  # here we filter out the predecessors that have been selected
  real_preds = [i for i in preds if i not in marked_blocks]

  if fn_ins_in_block is not None:
    succs = [i for i in succs if fn_ins_in_block(i)]

  # collect results:
  # - BBLs in the sub-CFG
  # - list of predecessor nodes
  # - list of successor nodes
  # - no incoming from marked blocks?
  # - no outgoing to marked blocks?
  if _debug:
    fn_print("RESULT in(%s) out(%s) blocks(%s)" % ([hex(i) for i in set(real_preds)], [hex(i) for i in set(succs)], [hex(i) for i in set(marked_blocks)]))
  return marked_blocks, real_preds, succs

# given a sub-CFG, select a function to associate the blocks in the sub-CFG with
# returns 'None' when no function can be found
def SelectFunctionToAssociateSubCfgWith(pred_blocks, succ_blocks, allow_marked_pred, allow_marked_succ, allow_multiple_functions, isolated_pred, isolated_succ, pred_succ_combined, selector = 1):
  # decide what function to move the blocks to

  #if (not allow_marked_pred) and (len(set(pred_blocks) & _marked_blocks_start) > 0):
  if (not allow_marked_pred) and (len([i for i in pred_blocks if (IsBlockMarked(i, selector) or IsBlockMarked(i))]) > 0):
    # incoming from marked blocks, but not allowed
    if _debug:
      fn_print("not allowed: marked predecessor")
    return None, None, None
  #if (not allow_marked_succ) and (len(set(succ_blocks) & _marked_blocks_start) > 0):
  if (not allow_marked_succ) and (len([i for i in succ_blocks if (IsBlockMarked(i, selector) or IsBlockMarked(i))]) > 0):
    # outgoing to marked blocks, but not allowed
    if _debug:
      fn_print("not allowed: marked successor")
    return None, None, None

  # calculate real pred/succ functions, ignoring marked blocks
  fun_to_address = {}

  pred_functions = []
  for i in pred_blocks:
    if (not IsBlockMarked(i, selector) and (not IsBlockMarked(i))):
      f = fn_get_function(i)
      pred_functions.append(f)

      if f not in fun_to_address:
        fun_to_address[f] = set()
      fun_to_address[f].add(i)

  succ_functions = []
  for i in succ_blocks:
    if (not IsBlockMarked(i, selector) and (not IsBlockMarked(i))):
      f = fn_get_function(i)
      succ_functions.append(f)

      if f not in fun_to_address:
        fun_to_address[f] = set()
      fun_to_address[f].add(i)

  def find_best_function(data):
    if len(data) == 0:
      # no data provided
      return -1, None

    # count the number of unique elements
    counts = {}
    for i in set(data):
      N = data.count(i)
      if N not in counts:
        counts[N] = set()
      counts[N].add(i)

    # try the element with the most associations
    possible = list(counts[max(counts.keys())])
    assert len(possible) > 0

    if len(possible) == 1:
      # one function found
      return 0, possible[0]

    else:
      # pick random
      return -2, possible[0]

    assert False, "should not come here"

  if pred_succ_combined:
    code, result = find_best_function(pred_functions + succ_functions)
    if (code == 0) or (allow_multiple_functions and code == -2):
      return code-10, result, fun_to_address
  #endif pred_succ_combined

  if isolated_pred:
    code, result = find_best_function(pred_functions)
    if (code == 0) or (allow_multiple_functions and code == -2):
      return code-20, result, fun_to_address
  #endif isolated_pred

  if isolated_succ:
    code, result = find_best_function(succ_functions)
    if (code == 0) or (allow_multiple_functions and code == -2):
      return code-30, result, fun_to_address
  #endif isolated_succ

  return None, None, None

def repartition(start_points, succs, allow_marked_in, allow_marked_out, multiple_pick_random, isolated_pred, isolated_succ, pred_succ_combined, partial, selector = 1):
  global _repartition_count

  iteration_count = 0
  moved_block_count = 0

  summary = {}

  if partial:
    # partial: do single-option assignments only
    # assert len(succs) > 0

    partial_iteration = 0

    while len(succs) > 0:
      if _debug:
        fn_print("parial iteration %d" % partial_iteration)
      partial_iteration += 1

      reachable = CalculateReachableFromSuccessors(succs, selector)

      # convert reachable blocks to functions
      reachable_funs = {}
      for k, v in reachable.items():
        data = set([fn_get_function(i) for i in v])
        # if len(data) > 0:
        #   fn_print("0x%x: %s" % (k, ["%s:%d" % (hex(i), fn_get_function(i)) for i in v]))
        data.discard(None)
        reachable_funs[k] = data

      # reassign blocks with their only function
      start_points = set()
      for block, functions in reachable_funs.items():
        if len(functions) == 1:
          if _debug:
            fn_print("moving block 0x%x-0x%x" % (block, fn_get_block_end_address(block)))
          fn_move_block(block, fn_get_block_end_address(block), list(reachable[k])[0])

          UnmarkBlock(block)
          moved_block_count += 1
        else:
          if _debug:
            fn_print("can't do 0x%x: %s" % (block, [hex(i) for i in reachable[block]]))
          start_points.add(block)
      #endfor reachable_funs

      succs = set()
      if multiple_pick_random:
        for block in start_points:
          assert IsBlockMarked(block, selector), "0x%x is not marked" % block

          # only blocks that only have unmarked outgoing edges
          all_unmarked = True
          outgoing_blocks = set()
          for succ in OutgoingBlockIterator(block, selector):
            if IsBlockMarked(succ, selector) or (succ in start_points):
              all_unmarked = False
              break

            outgoing_blocks.add(succ)
          #endfor

          if not all_unmarked:
            if _debug:
              fn_print("can't redo 0x%x, marked out" % block)
            continue

          if _debug:
            fn_print("doing 0x%x" % block)

          # only associate forward
          _, function, function_to_address = SelectFunctionToAssociateSubCfgWith([], outgoing_blocks, False, True, True, False, True, False, selector)
          if _debug:
            fn_print("for 0x%x, found function %d" % (block, function))

          # move the block
          fn_move_block(block, fn_get_block_end_address(block), list(function_to_address[function])[0])

          UnmarkBlock(block)
          moved_block_count += 1

          succs.add(block)
        #endfor start_points
      #endif multiple_pick_random
    #endwhile len(succs) > 0
  else:
    # regular: try to select as large a CFG as possible
    change = True
    while change:
      if _debug:
        fn_print("ITERATION %d/%d" % (_repartition_count, iteration_count))
      change = False

      new_start_points = set()
      for subject in start_points:
        if not IsBlockMarked(subject):
          continue
        if _debug:
          fn_print("doing 0x%x" % subject)
        blocks, incoming_blocks, outgoing_blocks = SelectSubCfgFromMarkedBlocks(subject, allow_marked_in, allow_marked_out, selector)

        if blocks is None:
          if _debug:
            fn_print("ERROR 0x%x returned None" % subject)
          new_start_points.add(subject)
          continue

        code, to_function, fun_to_address = SelectFunctionToAssociateSubCfgWith(incoming_blocks, outgoing_blocks, allow_marked_in, allow_marked_out, multiple_pick_random, isolated_pred, isolated_succ, pred_succ_combined, selector)

        if to_function is not None:
          if _debug:
            fn_print("found function %d" % to_function)

          to_function_address = fn_get_function_start(to_function)
          if _debug:
            fn_print("0x%x (but also %s)" % (to_function_address, [hex(i) for i in fun_to_address[to_function]]))
          # move each selected block to the selected function
          for block in blocks:
            # move the block itself
            fn_move_block(block, fn_get_block_end_address(block), to_function_address)

            # unmark the block from partitioning
            UnmarkBlock(block)
            moved_block_count += 1

            change = True
          #endfor blocks

          for block in outgoing_blocks:
            if IsBlockMarked(block, selector):
              new_start_points.add(block)
          #endfor outgoing_blocks

          if code not in summary:
            summary[code] = 0
          summary[code] += 1
        else:
          # can't move for now
          new_start_points.add(subject)
        #endif to_function
      #endfor start_points

      start_points = new_start_points
      iteration_count += 1
    #endwhile change
  #endif partial

  fn_print("repartition pass %d: %d blocks moved in %d iterations, %d start points remain - %s" % (_repartition_count, moved_block_count, iteration_count, len(start_points), summary))

  _repartition_count += 1
  return start_points, iteration_count, moved_block_count

def CalculateReachableFromSuccessors(succs, selector = 1):
  result = {}

  for succ in succs:
    visited = set()
    worklist = []

    if (fn_ins_in_block is not None) and (not fn_ins_in_block(succ)):
      continue

    for pred in IncomingMarkedBlockIterator(succ, selector):
      if pred not in result:
        result[pred] = set()
      result[pred].add(succ)

      worklist.append(pred)
    #endfor incoming

    while len(worklist) > 0:
      subject = worklist.pop()

      if subject in visited:
        continue
      visited.add(subject)

      for pred in IncomingMarkedBlockIterator(subject, selector):
        if pred not in result:
          result[pred] = set()
        result[pred] |= result[subject]

        worklist.append(pred)
      #endfor
    #endwhile
  #endfor succs

  return result

def CalculateReachableFromPredecessors(preds, selector = 1):
  result = {}

  for succ in preds:
    visited = set()
    worklist = []

    if (fn_ins_in_block is not None) and (not fn_ins_in_block(succ)):
      continue

    for pred in OutgoingMarkedBlockIterator(succ, selector):
      if pred not in result:
        result[pred] = set()
      result[pred].add(succ)

      worklist.append(pred)
    #endfor incoming

    while len(worklist) > 0:
      subject = worklist.pop()

      if subject in visited:
        continue
      visited.add(subject)

      for pred in OutgoingMarkedBlockIterator(subject, selector):
        if pred not in result:
          result[pred] = set()
        result[pred] |= result[subject]

        worklist.append(pred)
      #endfor
    #endwhile
  #endfor preds

  return result
