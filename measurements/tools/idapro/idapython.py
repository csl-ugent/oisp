import idaapi
import idautils
import idc

ida_version = 0
IDA_V7 = 700
fn_print = None

REG_PC = 15
NR_GPREGS = 16
CONDITION_AL = 14

do_wait = True

BADADDR = 0xffffffff

def args():
  return idc.ARGV

def analysed_binary():
  return idaapi.get_root_filename()

def find_section(name):
  sec = idaapi.get_segm_by_name(name)

  S = 0
  E = 0

  if sec is not None:
    S = sec.startEA
    E = sec.endEA
    print "found %s (%x - %x)" % (name, S, E)

  return S, E

def section_end(i):
  sec = idaapi.getseg(i)
  assert sec, "no section for 0x%x" % i

  return sec.endEA
#enddef

# iterators
def iter_hanging(S, E):
  # search downwards (1)
  addr = idaapi.find_not_func(S, 1)

  nr_hanging = 0
  while (addr != idaapi.BADADDR) and (addr < E):
    yield addr

    addr = idaapi.find_not_func(addr, 1)

def iter_insns(B):
  for insn in idautils.Heads(B.startEA, B.endEA):
    yield insn

# [a,b)
def iter_insns_range(a, b):
  for insn in idautils.Heads(a, b):
    yield insn

def iter_blocks_in_function_no_lookup(f):
  cfg = idaapi.FlowChart(f)

  for block in cfg:
    # this check is VERY important!
    # IDA may put empty blocks in a function (empty = startEA==endEA),
    # but these should not be considered because they may be associated with another function
    if block.startEA < block.endEA:
      yield block

def iter_blocks_in_function(f):
  func = idaapi.get_func(f)

  if func is None:
    return

  cfg = idaapi.FlowChart(func)

  for block in cfg:
    # this check is VERY important!
    # IDA may put empty blocks in a function (empty = startEA==endEA),
    # but these should not be considered because they may be associated with another function
    if block.startEA < block.endEA:
      yield block

def iter_blocks(S, E):
  for f in idautils.Functions(S, E):
    for block in iter_blocks_in_function(f):
      yield block

def iter_all_insns(S, E):
  for B in iter_blocks(S, E):
    for I in iter_insns(B):
      yield I

# instruction operands
def operand_registers(operand):
  result = set()

  if operand.type == idc.o_reg:
    # General Register (al,ax,es,ds...).
    reg = operand.reg

    result.add(reg)

    # common.print_debug("o_reg r%d" % (reg))

  elif operand.type == idc.o_displ:
    # Memory Reg [Base Reg + Index Reg + Displacement].
    base_reg = operand.phrase
    index_reg = operand.specflag1
    displacement = operand.addr

    result.add(base_reg)
    result.add(index_reg)

    # common.print_debug("o_displ r%d r%d %d" % (base_reg, index_reg, displacement))

  elif operand.type == idc.o_phrase:
    # Memory Ref [Base Reg + Index Reg].
    base_reg = operand.phrase
    index_reg = operand.specflag1

    result.add(base_reg)
    result.add(index_reg)

    # common.print_debug("o_phrase r%d r%d" % (base_reg, index_reg))

  elif operand.type == idc.o_reglist:
    # .specval contains bitmask
    for reg in range(NR_GPREGS):
      if operand.specval & (1<<reg):
        result.add(reg)

    # common.print_debug("o_reglist %s" % (result))

  elif operand.type == idc.o_idpspec0:
    # shifted operand
    # .specflag1 is register number for shift-by-register
    # .specflag2 is shift type (0=LSL, 1=LSR, 2=ASR, 4=ROR (amount==0 --> RRX))
    # .value is shift amount
    shift_reg = operand.phrase
    shift_type = operand.specflag2

    # default: shift by number
    shift_by_reg = False
    shift_amount = operand.value

    # other case: shift by register
    if shift_amount == 0:
      shift_by_reg = True
      shift_amount = operand.specflag1
      result.add(shift_amount)

    result.add(shift_reg)

    # if shift_by_reg:
    #   common.print_debug("o_idpspec0 r%d, %d r%d" % (shift_reg, shift_type, shift_amount))
    # else:
    #   common.print_debug("o_idpspec0 r%d, %d %d" % (shift_reg, shift_type, shift_amount))

  elif operand.type == idc.o_void or \
        operand.type == idc.o_imm or \
        operand.type == idc.o_near or \
        operand.type == idc.o_idpspec4 or \
        operand.type == idc.o_idpspec5 or \
        operand.type == idc.o_mem or \
        operand.type == idc.o_idpspec2 or \
        operand.type == idc.o_idpspec3:
    # No Operand.
    # Immediate Value.
    # Immediate Near Address (CODE).
    # Seems to be related to vector instructions
    # Seems to be related to vector instructions
    # Direct Memory Reference (DATA).
    # Coprocessor register list.
    # Coprocessor register.

    # documentation: https://github.com/EiNSTeiN-/idapython/blob/master/python/idc.py
    # don't look at this operand
    pass

  else:
    assert False, "unknown operand type %d" % (operand.type)

  return result

def InsRegisters(I):
  referenced_registers = set()
  all_operand_registers = list()

  for operand in I.Operands:
    regs = operand_registers(operand)
    referenced_registers |= regs
    all_operand_registers.append(regs)

  return referenced_registers, all_operand_registers

# instructions
def InsIsHanging(i):
  return InsIsCode(i) and (idaapi.get_func(i) is None)

def InsIsData(i):
  return idc.isData(idaapi.getFlags(i))

def InsIsUnknown(i):
  return idc.isUnknown(idaapi.getFlags(i))

def InsIsCode(i):
  return idc.isCode(idaapi.getFlags(i))

def InsAssembled(i):
  return idc.Dword(i)

def InsIsThumb(i):
  return idc.GetReg(i, "T") == 1

def InsOpcode(i):
  return idc.GetMnem(i)

def InsIsLastInBbl(i, B):
  if (B.startEA == B.endEA) and (i == B.startEA):
    # this is a single-instruction BBL
    return True

  # cross-check instruction address with last address in block
  return i == idc.PrevHead(B.endEA)

def InsIsCall(I):
  if I is None:
    DumpDatabase('assertion.idb')
  assert I is not None, "got None for decoded instruction"
  cf = I.get_canon_feature()

  return cf & idaapi.CF_CALL

def InsIsConditional(I):
  opcode = idc.GetMnem(I.ea)
  return I.segpref != CONDITION_AL or opcode == 'CBZ' or opcode == 'CBNZ'

def InsIsBranch(I):
  cf = I.get_canon_feature()
  opcode = I.get_canon_mnem()

  return cf & idaapi.CF_JUMP or \
          opcode == 'B' or \
          opcode == 'CBZ' or \
          opcode == 'CBNZ'

def InsDefinesPC(I):
  # For example, IDA does _not_ mark LDM sp, {pc} as a jump...
  cf = I.get_canon_feature()
  opcode = I.get_canon_mnem()
  referenced_registers, all_operand_registers = InsRegisters(I)

  if opcode == 'LDM':
    return REG_PC in all_operand_registers[1]
  else:
    for op_index, op_regs in enumerate(all_operand_registers):
      if (REG_PC in op_regs) and (cf & (idaapi.CF_CHG1 << op_index)):
        return True

  return False

def InsIsFlow(I):
  is_call = InsIsCall(I)
  is_branch = InsIsBranch(I)
  is_other = InsDefinesPC(I)
  return is_call or is_branch or is_other, is_call, is_branch or is_other

def InsNotInTextSection(i):
  seg_name = idaapi.get_segm_name(idaapi.getseg(i))
  return seg_name != ".text", seg_name

def InsString(i):
  return idc.GetDisasm(i)

def InsOpcode(i):
  return idc.GetMnem(i)

def InsNext(I):
  return I.ea + I.size

def InsIsNop(I):
  # SDK: allins.hpp, ARM_nop==2
  return I.itype == 2

def InsIsMacro(I):
  return I.is_macro()

def InsSwitchInfo(i):
  switch_info = idaapi.get_switch_info_ex(i)
  if switch_info is None:
    return False, None, None

  cases = idaapi.calc_switch_cases(i, switch_info)
  return bool(cases), switch_info, cases

def SwitchDefault(switch_info):
  condition = False
  if ida_version >= IDA_V7:
    condition = (switch_info.defjump != BADADDR)
  else:
    condition = (switch_info.flags & idaapi.SWI_DEFAULT)

  if condition:
    return switch_info.defjump

  return None

def SwitchNrCases(switch_info):
  return switch_info.ncases

def DumpDatabase(idb_name):
  fn_print("Saving database to %s" % idb_name)
  idc.SaveBase(idb_name)

# basic block
def BblIncomingInsns(i):
  return list(idautils.CodeRefsTo(i, 1))

def BblOutgoingInsns(i):
  return list(idautils.CodeRefsFrom(i, 1))

# functions
def FunctionCreateAt(i, endaddr = BADADDR):
  idc.MakeCode(i)
  result = idc.MakeFunction(i, endaddr)
  if do_wait:
    idc.Wait()
  return result

def FunctionAppendChunk(function_address, A, B_ex):
  # CAVEAT this function also adds successor hanging instructions!
  if idaapi.get_func(A) is not None:
    fn_print("0x%x-0x%x already in function" % (A, B_ex))
    return False

  fn_print("append chunk 0x%x-0x%x to function 0x%x" % (A, B_ex, function_address))

  # watch out with hanging instructions
  if (idaapi.get_func(A) is None) and (idaapi.get_func(idc.PrevHead(B_ex)) is not None):
    fn_print("chunk 0x%x-0x%x is part hanging, only moving hanging part" % (A, B_ex))
    B_ex = A
    while idaapi.get_func(B_ex) is None:
      B_ex = idc.NextHead(B_ex)
    fn_print("  ... instead moving 0x%x-0x%x" % (A, B_ex))

  result = idc.AppendFchunk(function_address, A, B_ex)
  if do_wait:
    idc.Wait()

  fn_print("append-chunk 0x%x-0x%x to 0x%x: %d" % (A, B_ex, function_address, result))

  if result:
    now_address = idc.GetFunctionAttr(A, idc.FUNCATTR_START)
    f2 = idc.GetFunctionAttr(function_address, idc.FUNCATTR_START)
    assert f2 == now_address, "0x%x/0x%x/0x%x" % (function_address, now_address, f2)
  return result

def FunctionRemoveChunk(any_ins_in_chunk):
  chunk_function = idc.GetFunctionAttr(any_ins_in_chunk, idc.FUNCATTR_START)
  result = idc.RemoveFchunk(chunk_function, any_ins_in_chunk)
  if do_wait:
    idc.Wait()
  fn_print("remove-chunk 0x%x: %d" % (any_ins_in_chunk, result))
  return result

def DisableAutoAnalysis():
  global do_wait
  idc.SetCharPrm(idc.INF_AUTO, False)
  do_wait = False

def EnableAutoAnalysis():
  global do_wait
  idc.SetCharPrm(idc.INF_AUTO, True)
  do_wait = True
  idc.Wait()

def FunctionChunks(addr):
  result = []
  entry = idc.GetFunctionAttr(addr, idc.FUNCATTR_START)

  chunk = idc.FirstFuncFchunk(entry)
  if chunk == BADADDR:
    return result

  # list the function chunks
  result.append([chunk, idc.GetFchunkAttr(chunk, idc.FUNCATTR_END)])
  while chunk != BADADDR:
    chunk = idc.NextFuncFchunk(entry, chunk)
    if chunk != BADADDR:
      result.append([chunk, idc.GetFchunkAttr(chunk, idc.FUNCATTR_END)])

  return result
#enddef

# This function moves parts of IDA Pro's function chunks around.
# We first extract the chunk from any existing function,
# then we add the desired part to the specified function,
# and finally we move the pre- and postamble of the function chunk
# back to the original function.
# These actions need to be perfomed in this order because of the
# auto-analysis done by IDA Pro: when the pre-amble is added to the
# original function BEFORE the selected part has been added to the
# desired function, that part too will be added back to the original
# function.
def _ChunkMovePart(inner_start, inner_end_ex, function_address):
  moved_blocks = []

  fn_print("MICRO move 0x%x-0x%x to 0x%x" % (inner_start, inner_end_ex, function_address))
  outer_function = idc.GetFunctionAttr(inner_start, idc.FUNCATTR_START)
  outer_start = idc.GetFchunkAttr(inner_start, idc.FUNCATTR_START)
  outer_end_ex = idc.GetFchunkAttr(inner_start, idc.FUNCATTR_END)

  function_address2 = idc.GetFunctionAttr(function_address, idc.FUNCATTR_START)

  if outer_start == 0xffffffff:
    fn_print("outer start not defined")
    outer_start = inner_start
  if outer_end_ex == 0xffffffff:
    fn_print("outer end not defined")
    outer_end_ex = inner_end_ex

  if function_address2 == outer_function:
    fn_print("don't move, already in function")
    return moved_blocks

  # remove chunk from function
  remove_chunk_ok = True
  if outer_function == BADADDR:
    fn_print("already hanging 0x%x-0x%x" % (outer_start, outer_end_ex))
  else:
    fn_print("remove 0x%x-0x%x from 0x%x" % (outer_start, outer_end_ex, outer_function))
    remove_chunk_ok = FunctionRemoveChunk(outer_start)
    moved_blocks.append([outer_start, outer_end_ex])

    if not remove_chunk_ok:
      fn_print("  could not remove chunk")

      chunks = FunctionChunks(outer_start)
      if len(chunks) == 1:
        fn_print("  deleting function, moving entire chunk")
        if (inner_start != outer_start) or (inner_end_ex != outer_end_ex):
          fn_print("  changed function bounds!")
        remove_chunk_ok = idaapi.del_func(outer_start)
        assert remove_chunk_ok
        inner_start = outer_start
        inner_end_ex = outer_end_ex
      else:
        fn_print("  function contains chunks %s" % [['0x%x-0x%x' % (i, j)] for i, j in chunks])

        # to disable function chunk isolation
        # return moved_blocks

        if (chunks[0][0] <= inner_start) and (inner_start < chunks[0][1]):
          fn_print("have to move first chunk, need to work around this...")

          fn_print("removing all but first chunk")
          for i in range(1, len(chunks)):
            remove_chunk_ok_2 = FunctionRemoveChunk(chunks[i][0])
            assert remove_chunk_ok_2

            current_address = chunks[i][0]
            while current_address < chunks[i][1]:
              assert InsIsData(current_address) or InsIsHanging(current_address), "0x%x does not hang nor is data" % current_address
              current_address = idc.NextHead(current_address)
            #endwhile
          #endfor

          fn_print("create new function starting at second chunk (0x%x-0x%x)" % (chunks[1][0], chunks[1][1]))
          create_function_ok = FunctionCreateAt(chunks[1][0], chunks[1][1])
          moved_blocks.append([chunks[1][0], chunks[1][1]])
          assert create_function_ok

          if len(chunks) > 2:
            for i in range(2, len(chunks)):
              moved_blocks_sub = _ChunkMovePart(chunks[i][0], chunks[i][1], chunks[1][0])
              moved_blocks.extend(moved_blocks_sub)
              assert len(moved_blocks_sub) > 0
            #endfor
          #endif

          fn_print("finally removing entire function for first chunk")
          remove_chunk_ok = idaapi.del_func(chunks[0][0])
          moved_blocks.append([chunks[0][0], chunks[0][1]])
          assert remove_chunk_ok

          for i in range(1, len(chunks)):
            ii = chunks[i][0]
            while ii < chunks[i][1]:
              assert not InsIsHanging(ii), "0x%x hangs" % ii
              ii = idc.NextHead(ii)
            #endif
          #endfor

          inner_start = outer_start
          inner_end_ex = outer_end_ex
        else:
          assert False
        #endif
      #endif
    #endif
  #endif

  assert remove_chunk_ok

  move_block_ok = False

  # regular move
  # append the desired part to the correct function
  restored_whole_chunk = False

  fn_print("moving 0x%x-0x%x" % (inner_start, inner_end_ex))

  move_block_ok = FunctionAppendChunk(function_address, inner_start, inner_end_ex)
  fn_print("   move-block %d" % move_block_ok)

  if not move_block_ok:
    if outer_start == outer_function:
      fn_print("error-restore: start of function 0x%x-(0x%x-0x%x)-0x%x to 0x%x" % (outer_start, inner_start, inner_end_ex, outer_end_ex, outer_function))
      assert outer_end_ex == inner_end_ex
      restored_whole_chunk = FunctionCreateAt(outer_start, outer_end_ex)
      moved_blocks.append([outer_start, outer_end_ex])
      assert restored_whole_chunk
    else:
      fn_print("restoring 0x%x-0x%x to 0x%x" % (outer_start, outer_end_ex, outer_function))
      restored_whole_chunk = FunctionAppendChunk(outer_function, outer_start, outer_end_ex)
      moved_blocks.append([outer_start, outer_end_ex])
      if not restored_whole_chunk:
        real_function = idc.GetFunctionAttr(outer_start, idc.FUNCATTR_START)
        should_be_function = outer_function
        if real_function == should_be_function:
          restored_whole_chunk = True
        else:
          fn_print("0x%x/0x%x" % (real_function, should_be_function))
      #endif
      assert restored_whole_chunk
  else:
    moved_blocks.append([inner_start, inner_end_ex])

  if not restored_whole_chunk:
    # add PRE-part to original function, if needed
    if outer_start < inner_start:
      fn_print(" prefix...")

      if InsIsHanging(outer_start):
        prefixmove = FunctionAppendChunk(outer_function, outer_start, inner_start)
        moved_blocks.append([outer_start, inner_start])
        if not prefixmove:
          fn_print("could not restore prefix 0x%x-0x%x, instead adding it to the new function too" % (outer_start, inner_start))
          prefixmove = FunctionAppendChunk(function_address, outer_start, inner_start)
          assert prefixmove
          moved_blocks.append([outer_start, inner_start, function_address])
        else:
          fn_print("restored prefix 0x%x-0x%x" % (outer_start, inner_start))
        #endif
      #endif
    #endif

    # add POST-part to original function, if needed
    if inner_end_ex < outer_end_ex:
      fn_print(" postfix...")

      post_start = inner_end_ex
      while post_start < outer_end_ex:
        if InsIsData(post_start):
          # skip data
          post_start = idc.NextHead(post_start)
        else:
          # found start of a block of code
          subpost_start = post_start
          fn_print("found subpost start 0x%x" % subpost_start)

          subpost_end = idc.NextHead(subpost_start)
          while subpost_end < outer_end_ex:
            if not InsIsHanging(subpost_end):
              break
            subpost_end = idc.NextHead(subpost_end)
          #endwhile subpost_start

          # don't go past the end of the section
          E = section_end(subpost_start)
          if subpost_end > E:
            subpost_end = E

          fn_print("found subpost 0x%x-0x%x" % (subpost_start, subpost_end))
          postfixmove = FunctionAppendChunk(outer_function, subpost_start, subpost_end)
          moved_blocks.append([subpost_start, subpost_end])
          if not postfixmove:
            fn_print("could not restore postfix 0x%x-0x%x, instead adding it to the new function too" % (subpost_start, subpost_end))
            postfixmove = FunctionAppendChunk(function_address, subpost_start, subpost_end)
            if not postfixmove:
              DumpDatabase('assertion.idb')
            assert postfixmove
            moved_blocks.append([subpost_start, subpost_end])
          else:
            fn_print("restored postfix 0x%x-0x%x" % (subpost_start, subpost_end))
          #endif

          post_start = subpost_end
        #endif
      #endwhile post_start
    #endif
  #endif

  ii = outer_start
  while ii < outer_end_ex:
    assert not InsIsHanging(ii), "0x%x hangs" % ii
    ii = idc.NextHead(ii)
  #endif

  return moved_blocks

def ChunkMovePart(inner_start, inner_end_ex, function_address):
  # maybe the given range covers multiple chunks
  result = []
  fn_print("MACRO move 0x%x-0x%x to 0x%x" % (inner_start, inner_end_ex, function_address))

  DisableAutoAnalysis()

  current_inner_start = inner_start
  while current_inner_start < inner_end_ex:
    chunk_start = idc.GetFchunkAttr(current_inner_start, idc.FUNCATTR_START)
    chunk_end_ex = idc.GetFchunkAttr(current_inner_start, idc.FUNCATTR_END)

    new_inner_end_ex = inner_end_ex
    if chunk_end_ex < inner_end_ex:
      new_inner_end_ex = chunk_end_ex

    result.extend(_ChunkMovePart(current_inner_start, new_inner_end_ex, function_address))

    current_inner_start = idc.GetFchunkAttr(current_inner_start, idc.FUNCATTR_END)
    while not InsIsCode(current_inner_start):
      current_inner_start = idc.NextHead(current_inner_start)
      assert current_inner_start != BADADDR
    #endwhile
  #endwhile

  EnableAutoAnalysis()

  return result
