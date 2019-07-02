import os
import sys

# check if __file__ is defined
try:
  __file__
except NameError:
  # not defined,
  # assume that we're running in a container
  # and that the script is located at this directory
  __file__ = "/af-metingen/tools/ghidra/plugin.py"

sys.path.append('/usr/lib/python2.7/site-packages') # Arch
sys.path.append('/usr/lib/python2.7/dist-packages') # Debian

import importlib
import pathlib

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
import_parents(level=2)

import tools.Tool as Tool

from ghidra.program.model.address import AddressSet
from ghidra.app.services import BlockModelService
from ghidra.program.model.address import Address
from ghidra.program.model.symbol import SourceType
from ghidra.app.cmd.function import CreateFunctionCmd

ifile = None
ffile = None
bfile = None
efile = None
sfile = None
logfile = None
listing = None
plt_section = None

INVALID = -1

block_uid = 0
function_uid = 0
edge_uid = 0

def GetGhidraAddress(addr):
  return toAddr(addr)

def CreateFunctionAt(g_addr):
  print("Creating function at 0x%x" % g_addr.getOffset())

  # create a new function at the specified address
  address_set = createAddressSet()
  address_set.add(g_addr)
  listing.createFunction(None, g_addr, address_set, SourceType.DEFAULT)

  # re-create the function
  result = CreateFunctionCmd(g_addr).fixupFunctionBody(currentProgram, listing.getInstructionAt(g_addr), monitor)
  if not result:
    print("ERROR could not create function at 0x%x" % g_addr.getOffset())
#enddef

def InsGetAssembled(insn):
  result = 0

  #TODO: need to get length of current instruction and read those bytes
  #      the current method will yield erroneous results for x86 as it
  #      assumes fixed-length (4-byte) instructions
  try:
    result = insn.getUnsignedByte(0)
    result = insn.getUnsignedShort(0)
    result = insn.getUnsignedInt(0)
  except:
    pass

  return result

def InsIsThumb(insn):
  tmode_register = currentProgram.getProgramContext().getRegister("TMode")

  result = False
  if tmode_register:
    tmode_register_value = currentProgram.getProgramContext().getRegisterValue(tmode_register, insn.getAddress())

    #(tmode_register_value.getUnsignedValue() == BigInteger.ONE) ? 1 : 0
    result = (tmode_register_value == 1)

  return result
#enddef

def AddressInPLT(addr):
  result = False

  if plt_section:
    result = plt_section.contains(addr)

  return result
#enddef

def InsIsSwitch(insn):
  flow = insn.getFlowType()

  result = False
  destinations = []
  default_switch_destination = INVALID
  if flow.isJump() and flow.isComputed():
    refs_from = insn.getReferencesFrom()
    # Ghidra returns references to the destinations,
    # including one reference to the data table

    for ref in refs_from:
      to_insn = listing.getInstructionAt(ref.getToAddress())
      if not to_insn:
        # data block
        #TODO: verify that 'to' is of type 'DATA' or similar
        continue

      destinations.append(ref.getToAddress())
    #endfor

    print("switch instruction at 0x%x: %s" % (insn.getAddress().getOffset(), destinations))
    result = True
  #endif

  return result, destinations, default_switch_destination
#enddef

def move_block(start, end, destination):
  # move block [start, end) to function of destination
  print("moving [0x%x, 0x%x) to function at 0x%x" % (start, end, destination))

  # Ghidra needs the last byte to be inclusive
  end -= 1

  g_start = toAddr(start)
  g_end = toAddr(end)
  g_destination = toAddr(destination)

  function_mgr = currentProgram.getFunctionManager()

  # get the original function
  original_function = function_mgr.getFunctionContaining(g_start)
  removed_original_function = False
  if original_function:
    # need to remove the range from the original function

    # special care when the entry point is in range
    original_entry = original_function.getEntryPoint()
    new_original_body = original_function.getBody().subtract(AddressSet(g_start, g_end))

    if (g_start <= original_entry) and (original_entry < g_end):
      # PROBLEM: entry point of function is in block,
      # remove the entire function
      print("removing function...")
      removed_original_function = function_mgr.removeFunction(original_entry)
      assert removed_original_function

      new_entrypoint = new_original_body.getMinAddress()
      print("recreating function at 0x%x" % (new_entrypoint.getOffset()))
      listing.createFunction(None, new_entrypoint, new_original_body, SourceType.DEFAULT)
    else:
      # remove this block from the function
      original_function.setBody(new_original_body)
    #endif
  #endif

  # move the block to the destination function
  destination_function = function_mgr.getFunctionContaining(g_destination)
  assert destination_function

  # original body
  destination_entry = destination_function.getEntryPoint()
  print("adding to destination function at 0x%x" % destination_entry.getOffset())
  destination_body = destination_function.getBody()
  destination_function.setBody(destination_body.union(AddressSet(g_start, g_end)))
#enddef

def process_functionless(section_range):
  function_mgr = currentProgram.getFunctionManager()

  insn_it = listing.getInstructions(section_range, True)
  while insn_it.hasNext():
    insn = insn_it.next()
    func = function_mgr.getFunctionContaining(insn.getAddress())

    if not func:
      CreateFunctionAt(insn.getAddress())
  #endwhile
#enddef

def process_section(memory_block):
  global block_uid, function_uid, edge_uid

  section_range = AddressSet(memory_block.getStart(), memory_block.getEnd())

  # functionless instructions
  process_functionless(section_range)

  function_mgr = currentProgram.getFunctionManager()

  # functionless instructions
  nr_functionless = 0
  hanging_insn_it = listing.getInstructions(section_range, True)
  while hanging_insn_it.hasNext():
    insn = hanging_insn_it.next()
    func = function_mgr.getFunctionContaining(insn.getAddress())

    if not func:
      # functionless
      ifile.write("0x%x:%d:%d:%d:0x%x:%d:%d:%d\n" % (insn.getAddress().getOffset(), INVALID, INVALID, INVALID, InsGetAssembled(insn), InsIsThumb(insn), 0, 0))

      nr_functionless += 1
    #endif
  #endwhile
  logfile.write("Found %d functionless instructions\n" % nr_functionless)

  # functions
  function_it = function_mgr.getFunctions(section_range, True)
  while function_it.hasNext():
    f = function_it.next()
    logfile.write("Doing function %s\n" % f.toString())

    # basic blocks
    bms = state.getTool().getService(BlockModelService)
    cbm = bms.getActiveBlockModel()
    cbi = cbm.getCodeBlocksContaining(f.getBody(), monitor)
    while cbi.hasNext():
      cb = cbi.next()

      bbl_first_byte = cb.getFirstStartAddress()
      bbl_last_byte = cb.getAddresses(False).next()

      logfile.write("  block %x\n" % bbl_first_byte.getOffset())

      insn_it = listing.getInstructions(AddressSet(bbl_first_byte, bbl_last_byte), True)
      insn = None
      bbl_nins = 0
      while insn_it.hasNext():
        insn = insn_it.next()
        logfile.write("    instruction %s\n" % insn.toString())

        ifile.write("0x%x:%d:%d:%d:0x%x:%d:%d:%d\n" % (insn.getAddress().getOffset(), block_uid, function_uid, INVALID, InsGetAssembled(insn), InsIsThumb(insn), 0, 0))

        # switch instructions
        is_switch, switch_destinations, default_switch_destination = InsIsSwitch(insn)
        if is_switch and len(switch_destinations) > 0:
          #TODO: instruction can be marked as switch with length 0
          #      this is probably an unanalysed switch

          # take note of the switch instruction
          sfile.write("0x%x:%d:0x%x:" % (insn.getAddress().getOffset(), len(switch_destinations), default_switch_destination))
          for d in switch_destinations:
            sfile.write("0x%x," % d.getOffset())
          sfile.write("\n")
        #endif

        bbl_nins += 1
      #endwhile

      # last instruction determines control flow
      block_addr = bbl_first_byte.getOffset()
      branch_addr = insn.getAddress().getOffset()

      ft = insn.getFallThrough()
      non_ft = insn.getFlows()

      flow_type = insn.getFlowType()

      jump_type = Tool.EDGE_JUMP
      ft_type = Tool.EDGE_FALLTHROUGH
      if flow_type.isCall():
        # call
        logfile.write("CALL 0x%x %s\n" % (insn.getAddress().getOffset(), insn.toString()))

        jump_type = Tool.EDGE_CALL
        ft_type = Tool.EDGE_CALLFALLTHROUGH
      #endif

      if ft:
        # fallthrough edge
        logfile.write("  ft: 0x%x->0x%x\n" % (insn.getAddress().getOffset(), ft.getOffset()))
        efile.write("%d:0x%x:0x%x:0x%x:%d:%d:%d\n" % (edge_uid, block_addr, branch_addr, ft.getOffset(), AddressInPLT(ft), ft_type, 0))
        edge_uid += 1
      #endif

      if non_ft:
        # flow edges
        for i in non_ft:
          logfile.write("  jp: 0x%x->0x%x\n" % (insn.getAddress().getOffset(), i.getOffset()))
          efile.write("%d:0x%x:0x%x:0x%x:%d:%d:%d\n" % (edge_uid, block_addr, branch_addr, i.getOffset(), AddressInPLT(i), jump_type, 0))
          edge_uid += 1
        #endfor
      #endif

      bfile.write("%d:0x%x:%d:%d:%d\n" % (block_uid, bbl_first_byte.getOffset(), bbl_nins, function_uid, INVALID))
      block_uid += 1
    #endwhile

    ffile.write("%d:%s:%d:%d\n" % (function_uid, f.getName().replace(':', '_'), INVALID, INVALID))
    function_uid += 1
  #endwhile
#enddef

def main():
  global ifile, ffile, bfile, efile, sfile, logfile
  global listing, plt_section

  #TODO: add suffix
  basename = currentProgram.getExecutablePath() + ".ghidra"

  # output files
  ifile = open(basename + ".instructions", "w")
  print("Writing instructions to %s" % os.path.realpath(ifile.name))

  ffile = open(basename + ".functions", "w")
  print("Writing functions to %s" % os.path.realpath(ffile.name))

  bfile = open(basename + ".bbls", "w")
  print("Writing BBLs to %s" % os.path.realpath(bfile.name))

  efile = open(basename + ".edges", "w")
  print("Writing edges to %s" % os.path.realpath(efile.name))

  sfile = open(basename + ".switches", "w")
  print("Writing switch information to %s" % os.path.realpath(sfile.name))

  logfile = open(basename + ".log", "w")

  listing = currentProgram.getListing()

  # PLT section
  plt_section = getMemoryBlock(".plt")

  # process code
  section = getMemoryBlock(".text")
  if section:
    process_section(section)

  section = getMemoryBlock(".init")
  if section:
    process_section(section)

  ifile.close()
  ffile.close()
  bfile.close()
  efile.close()
  sfile.close()

if __name__ == "__main__":
  main()
