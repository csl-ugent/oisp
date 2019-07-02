# ./idaq -c -A -S"/home/jens/repositories/ida-plugins/test.py [<argument>]*" <binary path and name>
import os
import sys

sys.path.append('/usr/lib/python2.7/site-packages')

import getopt
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

import idaapi
import idautils
import idapython
import tools.diablo.Diablo as Diablo
import tools.diablo.log as DiabloLog
import tools.Tool as Tool
import lib.partitioning as partitioning

INVALID = -1

# debug
debug = True
stop = False

# output files
ifile = None
ffile = None
bfile = None
efile = None
sfile = None
vfile = None

D = None

# global statistics
nr_hanging = 0
function_id = 0
block_id = 0
edge_id = 0

# global variables
plt_start = 0
plt_end = 0

# arguments
suffix = ''
prioritize_ft = 0

blacklist_addresses = set()

old_goods = {}
old_bads = {}

process_hanging = False
repartition_hanging = False
repartition_hanging_rehang = False
repartition_targets = False
repartition_targets_bx = False
repartition_sources = False

def Verbose(s):
    global vfile
    vfile.write("%s\n" % s)

def DumpDatabaseName(s):
    return "%s.%s.idb" % (database_basename, s)

def DumpDatabase(s):
    idapython.DumpDatabase(DumpDatabaseName(s))

def IsDecodable(i):
    return idautils.DecodeInstruction(i) is not None

def AddressInPLT(address):
    return plt_start <= address and address < plt_end

def AddressInRange(S, E, address):
    return S <= address and address < E

def print_edge(src, branch, dst, etype, decoded):
    global edge_id

    if etype == Tool.EDGE_FALLTHROUGH:
        delta = dst - branch
        if delta > 4:
            assert decoded.is_macro(), "0x%x (0x%x) -> 0x%x (type %d) expected delta of 8, got %d" % (src, branch, dst, etype, delta)
            # here, IDA has probably merged two instructions, for example MOVW/MOVT
            branch += decoded.size - 4

    efile.write("%d:0x%x:0x%x:0x%x:%d:%d:%d\n" % (edge_id, src, branch, dst, AddressInPLT(dst), etype, 0))

    edge_id += 1

def dangerous_flow_instruction(i):
    result = False

    asm = idapython.InsAssembled(i)

    # Certain instruction cause IDA to infinitely loop in its analysis phase.
    # This is the case in cactusADM (AF/swo, max4, address 0xecdc): LDMEQFD SP!, {R4, PC}
    if (asm & 0xffff8000) == 0x08bd8000:
        Verbose("dangerous instruction 0x%x %s" % (i, idapython.InsString(i)))
        result = True

    return result

def put_in_bbl(i):
    return idapython.InsIsHanging(i) and \
            (not idapython.InsIsData(i)) and \
            (not idapython.InsIsUnknown(i))

def InsIsCall(i):
    return idapython.InsIsCall(idautils.DecodeInstruction(i))

# collect function information
block_end_to_start = {}
block_start_to_end = {}
def ins_to_functions(S, E):
    global block_end_to_start, block_start_to_end

    block_end_to_start.clear()
    block_start_to_end.clear()

    f_uid = 0
    for f in Functions(S, E):
        for block in idapython.iter_blocks_in_function(f):
            insn = PrevHead(block.endEA)
            assert (block.startEA <= insn) and (insn < block.endEA), "what? 0x%x-0x%x (0x%x)" % (block.startEA, block.endEA, insn)
            block_end_to_start[insn] = block.startEA
            block_start_to_end[block.startEA] = insn
        f_uid += 1

def get_function(i):
    result = idc.GetFunctionAttr(i, idc.FUNCATTR_START)
    if result == BADADDR:
        result = None
    return result

def same_function(i, j):
    f = get_function(i)
    g = get_function(j)

    if f is None or j is None:
        return False

    return f == g

def InsInBlock(i):
    return get_function(i) is not None

def get_function_start(f):
    return f

def block_start_address(i):
    if i not in block_end_to_start:
        return None
    return block_end_to_start[i]

def block_end_address(i):
    result = None

    if i not in block_start_to_end:
        # special handling: look for function and then for block
        f = idaapi.get_func(i)
        assert f, "0x%x not in function" % i

        b = None
        for block in idapython.iter_blocks_in_function_no_lookup(f):
            if (block.startEA <= i) and (i < block.endEA):
                b = block
                break
            #endif
        #endfor
        assert b, "0x%x not found" % i

        result = PrevHead(block.endEA)
        Verbose("found block end for 0x%x: 0x%x" % (i, result))
    else:
        result = block_start_to_end[i]
    #endif

    return result

def move_block(start, end, destination):
    global D, old_bads, old_goods

    # move the chunk
    all_moved_blocks = idapython.ChunkMovePart(start, NextHead(end), destination)

    # construct set of instructions for which links should be checked
    instructions_to_check = set()
    for begin, end in all_moved_blocks:
        i = begin
        while i < end:
            instructions_to_check.add(i)
            i = NextHead(i)
        #endwhile
    #endfor

    Verbose("checking links for %d instructions" % len(instructions_to_check))

    for i in instructions_to_check:
        D.record_links(i, same_function)
    #endfor
#enddef

def do_hanging(S, E):
    if not process_hanging:
        return

    Verbose("STATUS put all hanging instructions in functions")

    partitioning.Init()

    # fixed parameters
    partitioning.subcfg_forward = False
    partitioning.subcfg_backward = True
    partitioning.subcfg_backforth = False

    # PHASE 1a: mark hanging blocks
    #           Here we have a problem, as basic blocks and control flow edges are not known for hanging instructions.
    #           We solve this by letting IDA define a function at the hanging instruction address.
    hanging_functions = set()
    marked_block_count = 0
    change = True
    while change:
        change = False

        for i in idapython.iter_hanging(S, E):
            if not MakeFunction(i):
                # could not create function
                Verbose("could not create function for hanging instruction at 0x%x" % i)
                continue

            # print("hanging 0x%x" % i)
            change = True

            f_start = GetFunctionAttr(i, FUNCATTR_START)
            hanging_functions.add(f_start)

            # print("START 0x%x" % f_start)
            for block in idapython.iter_blocks_in_function(f_start):
                # print("marking block 0x%x-0x%x" % (block.startEA, PrevHead(block.endEA)))
                partitioning.MarkBlock(block.startEA, PrevHead(block.endEA))
                marked_block_count += 1
            #endfor blocks
        #endfor iter_hanging
    #endwhile change

    # PHASE 1b: mark ignored edges
    #TODO

    ins_to_functions(S, E)

    # PHASE 2: iteratively associate hanging blocks with function
    D.collect_links(same_function)

    if not repartition_hanging:
        return
    idapython.DumpDatabase(DumpDatabaseName('before-hanging-repart'))

    Verbose("STATUS repartition hanging instructions")

    # collect possible start points:
    # blocks that have one or more non-hanging incoming/outgoing blocks
    start_points = set()
    for block in partitioning.MarkedBlockIterator():
        added = False
        for x in idapython.BblIncomingInsns(block):
            start = block_start_address(x)
            if (start is not None) and (not partitioning.IsBlockMarked(start)):
                start_points.add(block)
                added = True
                break
        #endfor incoming

        # early continue if possible
        if added:
            continue

        for x in idapython.BblOutgoingInsns(block_end_address(block)):
            if not partitioning.IsBlockMarked(x):
                start_points.add(block)
                break
        #endfor outgoing
    #endfor marked
    Verbose("STATUS start with %d/%d" % (len(start_points), marked_block_count))

    total_iterations = 0
    total_moved_blocks = 0

    configurations = [
        [False, False, False, False, False],
        [False, False, False, True, False],
        [False, False, False, False, True],
        [False, False, True, False, False],
        [True, True, False, False, False],
        [True, True, False, True, False],
        [True, True, False, False, True],
        [True, True, True, False, False]
    ]
    for conf in configurations:
        start_points, nr_iterations, nr_moved_blocks = partitioning.repartition(start_points, [], conf[0], conf[1], conf[2], conf[3], conf[4], True, False)
        total_iterations += nr_iterations
        total_moved_blocks += nr_moved_blocks

    # final pass: iterate remaining hanging blocks
    for block in partitioning.MarkedBlockIterator():
        start_points.add(block)
    # hardcoded flags here
    start_points, nr_iterations, nr_moved_blocks = partitioning.repartition(start_points, [], True, True, True, False, False, True, False)
    total_iterations += nr_iterations
    total_moved_blocks += nr_moved_blocks

    Verbose("STATUS moved %d/%d blocks in %d iterations" % (total_moved_blocks, marked_block_count, total_iterations))

    if repartition_hanging_rehang:
        nr_rehang = 0
        for block in partitioning.MarkedBlockIterator():
            Verbose("deleting block 0x%x" % block)
            idaapi.del_func(block)
            nr_rehang += 1
        Verbose("STATUS rehung %d blocks" % nr_rehang)

def PartitioningIgnoreSwitchRelatedEdges():
    Verbose("STATUS ignoring switch related edges")
    for start, end in D.PartitioningIgnoreSwitchRelatedEdges():
        partitioning.IgnoreEdge(start, end)
#enddef

def do_repartition_targets(targets, foo = False):
    total_moved_block_count = 0
    for case_target in targets:
        partitioning.UnmarkAllBlocks()
        partitioning.UnmarkAllBlocks2()

        Verbose("TARGET 0x%x" % case_target)
        if idapython.InsIsHanging(case_target):
            Verbose("  skip hanging")
            continue
        #endif

        if idapython.InsIsThumb(case_target):
            Verbose("  skip thumb")
            continue
        #endif

        # mark the basic blocks in the switch function
        for block in idapython.iter_blocks_in_function(case_target):
            partitioning.MarkBlock(block.startEA, PrevHead(block.endEA))

        # select the sub-CFG: all reachable blocks from the case target
        partitioning.subcfg_forward = foo
        partitioning.subcfg_backward = True
        partitioning.subcfg_backforth = foo
        blocks, _, succs = partitioning.SelectSubCfgFromMarkedBlocks(case_target, True, True)
        Verbose("got %d blocks" % len(blocks))

        for block in blocks:
            partitioning.MarkBlock2(block)

        # reconfigure for backwards-only
        partitioning.subcfg_forward = False
        partitioning.subcfg_backward = False
        partitioning.subcfg_backforth = False
        _, _, nr_moved_blocks = partitioning.repartition([0], succs, True, False, False, False, True, False, True, 2)

        total_moved_block_count += nr_moved_blocks
    #endfor insns

    Verbose("STATUS moved %d blocks to other functions" % total_moved_block_count)
#enddef

def GetAnalysisFlags():
    if idapython.ida_version >= idapython.IDA_V7:
        return idc.get_inf_attr(idc.INF_AF)
    else:
        return idc.GetShortPrm(idc.INF_START_AF)
#enddef

def SetAnalysisFlags(v):
    if idapython.ida_version >= idapython.IDA_V7:
        idc.set_inf_attr(idc.INF_AF, v)
    else:
        idc.SetShortPrm(idc.INF_START_AF, v)
#enddef

def process_segment(S, E):
    global D
    global nr_hanging, function_id, block_id, edge_id, old_goods, old_bads

    D.collect_links(same_function)
    idapython.DumpDatabase(DumpDatabaseName('before-hanging'))

    PartitioningIgnoreSwitchRelatedEdges()
    do_hanging(S, E)
    idapython.DumpDatabase(DumpDatabaseName('after-hanging'))

    D.collect_links(same_function)

    #####
    # move function chunks around if needed

    # disable some analysis passes that cause the auto analysis to enter an infinite loop
    analysis_flags = GetAnalysisFlags()
    analysis_flags &= ~idc.AF_PROC
    analysis_flags &= ~idc.AF_USED
    Verbose("setting analysis flags to 0x%x" % analysis_flags)
    SetAnalysisFlags(analysis_flags)

    if repartition_targets:
        Verbose("STATUS moving switch destinations to tail function...")
        ins_to_functions(S, E)

        partitioning.Init()
        PartitioningIgnoreSwitchRelatedEdges()

        # list switch targets to move
        targets = set()

        for insn in idapython.iter_all_insns(S, E):
            is_switch, switch_info, switch_cases = idapython.InsSwitchInfo(insn)
            insn_fun = get_function(insn)

            if insn_fun is None:
                continue

            if is_switch:
                # sinks
                for range_index in xrange(idapython.SwitchNrCases(switch_info)):
                    # target of one switch edge, assuming the range only covers one destination
                    assert len(switch_cases.cases[range_index]) == 1
                    case_target = switch_cases.targets[range_index]

                    if idapython.InsIsHanging(case_target):
                        # the target is not part of any function
                        Verbose("switch 0x%x target 0x%x hangs" % (insn, case_target))
                        continue

                    if get_function(case_target) != insn_fun:
                        # the target is not part of the switch function
                        continue

                    Verbose("adding switch target 0x%x-0x%x" % (insn, case_target))
                    targets.add(case_target)
                #endfor range

            elif repartition_targets_bx and idapython.InsOpcode(insn) == 'BX':
                nr_targets = 0
                for target in idapython.BblOutgoingInsns(insn):
                    if idapython.InsIsHanging(target):
                        Verbose("BX 0x%x target 0x%x hangs" % (insn, target))
                        continue

                    if get_function(target) != insn_fun:
                        continue

                    Verbose("adding BX target 0x%x-0x%x" % (insn, target))
                    targets.add(target)
                    nr_targets += 1

                nr_outgoing_edges = 0
                if D.InsExists(insn):
                    nr_outgoing_edges = D.BblNrOutgoingEdges(D.InsBbl(insn))
                Verbose("BX 0x%x %d/%d" % (insn, nr_outgoing_edges, nr_targets))
            #endif
        #endfor all instructions

        do_repartition_targets(targets)
        idapython.DumpDatabase(DumpDatabaseName("after-switch-repart"))
        D.collect_links(same_function)
    #endif switch dest to tail

    if repartition_sources:
        Verbose("STATUS moving dispatcher sources to head function...")
        ins_to_functions(S, E)

        targets = set()

        # collect predecessors for dispatchers
        for _, dispatcher_data in D._af_dispatchers.items():
            for incoming_edge in dispatcher_data['incoming']:
                from_insn = D.EdgeByUID(incoming_edge)['branch']

                if from_insn not in block_end_to_start:
                    Verbose("WARNING 0x%x(-0x%x) not found" % (from_insn, dispatcher_data['entry']))
                else:
                    targets.add(block_end_to_start[from_insn])
            #endfor incoming
        #endfor dispatchers

        do_repartition_targets(targets, True)
        idapython.DumpDatabase(DumpDatabaseName("after-source-repart"))
        D.collect_links(same_function)
    #endif

    #####
    # still hanging instructions should be put in a list
    Verbose("listing hanging instructions...")
    for insn in idapython.iter_hanging(S, E):
        ifile.write("0x%x:%d:%d:%d:0x%x:%d:%d:%d\n" % (insn, INVALID, INVALID, INVALID, 0xffffffff, INVALID, INVALID, INVALID))
        nr_hanging += 1
    Verbose("  found %d hanging instructions" % nr_hanging)

    # hanging instructions belong to a special function
    ffile.write("%d:(null):%d:%d\n" % (INVALID, INVALID, INVALID))

    #####
    # process the CFG and emit a list of functions, bbls and instructions
    Verbose("processing instructions...")
    for f in Functions(S, E):
        for block in idapython.iter_blocks_in_function(f):
            block_nins = 0

            #####
            # instructions
            # 'block.startEA' is the address of the first instruction in the BBL
            # 'block.endEA' is the address of the first instruction AFTER the BBL (last address + 4)
            for insn in idapython.iter_insns(block):
                if AddressInPLT(insn):
                    continue
                if not AddressInRange(S, E, insn):
                    continue

                # decode the instruction and construct sets of operand registers
                decoded_insn = idautils.DecodeInstruction(insn)
                if not decoded_insn:
                    Verbose("error, no decoded instruction 0x%x in block 0x%x-0x%x" % (insn, block.startEA, block.endEA))
                    continue

                # print the instruction
                ifile.write("0x%x:%d:%d:%d:0x%x:%d:%d:%d\n" % (insn, block_id, function_id, INVALID, idapython.InsAssembled(insn), idapython.InsIsThumb(insn), idapython.InsIsNop(decoded_insn), idapython.InsIsMacro(decoded_insn)))
                block_nins += 1

                # print switch information, if any
                is_switch, switch_info, switch_cases = idapython.InsSwitchInfo(insn)
                if is_switch:
                    # begin new switch record
                    nr_cases = idapython.SwitchNrCases(switch_info)
                    sfile.write("0x%x:%d:" % (insn, nr_cases))

                    # conditional switch instruction has a default case
                    default_case = idapython.SwitchDefault(switch_info)
                    if default_case is None:
                        default_case = INVALID
                    sfile.write("0x%x:" % (default_case))

                    # build ordered set of destinations
                    max_index = 0
                    index_to_dest = {}
                    for range_index in xrange(len(switch_cases.cases)):
                        current_range = switch_cases.cases[range_index]
                        target = switch_cases.targets[range_index]

                        for index in current_range:
                            # update entry in map
                            assert index not in index_to_dest, "index %d already in list %s for switch at 0x%x" % (index, index_to_dest, insn)
                            index_to_dest[index] = target

                            # update max_index
                            if index > max_index:
                                max_index = index
                        #endfor
                    #endfor

                    for _, target in index_to_dest.items():
                        sfile.write("0x%x," % target)
                    #endfor

                    # end of switch record
                    sfile.write("\n")

                # we want to consider _all_ possible branch instructions
                is_flow, is_call, is_branch = idapython.InsIsFlow(decoded_insn)
                if is_flow:
                    if (not idapython.InsIsLastInBbl(insn, block)):
                        if D.IsLoaded() and D.InsIsDispatcher(insn):
                            pass

                        elif idapython.InsIsCall(decoded_insn):
                            # calls are commonly placed in the middle of basic blocks by IDA
                            pass

                        elif D.IsLoaded() and D.InsIsOriginal(insn):
                            # sometimes an original switch instruction is not recognised by IDA as such
                            Verbose("vanilla flow instruction not at end of BBL 0x%x-0x%x and is not call 0x%x %s, probably an unrecognised switch" % (block.startEA, block.endEA, insn, idapython.InsString(insn)))

                        elif D.IsLoaded() and D.InsIsData(insn):
                            Verbose("DATA at 0x%x marked as flow instruction not at end of BBL 0x%x-0x%x %s" % (insn, block.startEA, block.endEA, idapython.InsString(insn)))

                        else:
                            # something is very wrong...
                            assert False, "flow instruction not at end of BBL 0x%x-0x%x and is not call 0x%x %s" % (block.startEA, block.endEA, insn, idapython.InsString(insn))

                    #####
                    # outgoing edges

                    # take special care for conditional branches that have the fallthrough case identical to the jump case
                    drew_fallthrough = False
                    already_done_dest = set()
                    for dst in idapython.BblOutgoingInsns(insn):
                        # check destination section
                        dst_not_text, section_name = idapython.InsNotInTextSection(insn)
                        if dst_not_text:
                            Verbose("0x%x -> 0x%x goes to section %s" % (insn, dst, section_name))
                            continue

                        gone = (dst != (insn + decoded_insn.size))

                        edge_type = Tool.EDGE_FALLTHROUGH
                        if is_call:
                            #print("CALL 0x%x -> 0x%x, gone? %d" % (insn, dst, gone))
                            edge_type = Tool.EDGE_CALL if gone else Tool.EDGE_CALLFALLTHROUGH

                        elif is_branch:
                            #print("JUMP 0x%x -> 0x%x, gone? %d" % (insn, dst, gone))
                            if idapython.InsIsConditional(decoded_insn):
                                edge_type = Tool.EDGE_JUMP if (gone or drew_fallthrough) else Tool.EDGE_FALLTHROUGH
                            else:
                                edge_type = Tool.EDGE_JUMP

                        else:
                            edge_type = Tool.EDGE_FALLTHROUGH
                        #endif

                        if dst in already_done_dest:
                            # this destination has already been processed
                            if idapython.InsOpcode(insn) == 'BX':
                                # don't add the same destination twice for BX instructions
                                continue
                            #endif
                        #endif

                        # print("edge1 0x%x->0x%x (type %d)" % (insn, dst, edge_type))
                        print_edge(block.startEA, insn, dst, edge_type, decoded_insn)
                        if edge_type == Tool.EDGE_FALLTHROUGH:
                            drew_fallthrough = True

                        already_done_dest.add(dst)
                    #endfor

                elif idapython.InsIsLastInBbl(insn, block):
                    # TODO: we can have 0 outgoing edges here, e.g. in the case where the instruction following
                    #       a switch instruction, which should be data (offset-based switch) is marked as code by IDA.
                    #       As such, IDA will try to draw FT edges from this DATA instruction to the next DATA.
                    done = False
                    for i in idapython.BblOutgoingInsns(insn):
                        assert not done, "0x%x" % (insn)
                        # print("edge2 0x%x->0x%x (type %d)" % (insn, i, Tool.EDGE_FALLTHROUGH))
                        print_edge(block.startEA, insn, i, Tool.EDGE_FALLTHROUGH, decoded_insn)
                        done = True

            bfile.write("%d:0x%x:%d:%d:%d\n" % (block_id, block.startEA, block_nins, function_id, INVALID))
            block_id += 1

        ffile.write("%d:%s:%d:%d\n" % (function_id, idaapi.get_func_name(f).replace(":", "_"), INVALID, INVALID))
        function_id += 1

def parse_args(args):
    global suffix, prioritize_ft
    global process_hanging, repartition_hanging, repartition_hanging_rehang, repartition_targets, repartition_targets_bx, repartition_sources

    try:
        opts, _ = getopt.getopt(args, "hgHsbfS:p:", ["hanging", "hanging-repart", "hanging-rehang", "switch-repart", "bx-repart", "source-repart", "suffix", "prioft"])
    except getopt.GetoptError as err:
        print("ERROR:", err)
        sys.exit(1)

    for opt, arg in opts:
        print("doing option %s with value %s" % (opt, arg))
        if opt in ("-h", "--hanging"):
            process_hanging = True
        elif opt in ("-g", "--hanging-repart"):
            repartition_hanging = True
        elif opt in ("-H", "--hanging-rehang"):
            repartition_hanging_rehang = True
        elif opt in ("-s", "--switch-repart"):
            repartition_targets = True
        elif opt in ("-b", "--bx-repart"):
            repartition_targets_bx = True
        elif opt in ("-f", "--source-repart"):
            repartition_sources = True

        elif opt in ("-S", "--suffix"):
            print("  suffix: %s" % arg)
            suffix = "." + arg
        elif opt in ("-p", "--prioft"):
            print("  prioritize FT: %d" % int(arg))
            prioritize_ft = int(arg)

# create a list of instructions based on IDA's analysis results
def run_ida():
    global ifile, ffile, bfile, efile, sfile, vfile, blacklist_addresses, prioritize_ft, D, database_basename

    Wait()
    parse_args(idapython.args()[1:])

    input_file = idapython.analysed_binary()
    basename = input_file + ".ida" + suffix
    database_basename = basename

    # open this file first as it contains logging output
    vfile = open(basename + ".verbose", "w", buffering=1)
    print("Writing verbose log to %s" % os.path.realpath(vfile.name))
    Verbose("START LOG")

    # read version
    idapython.ida_version = idc.GetShortPrm(idc.INF_VERSION)
    Verbose("Detected IDA Pro version: %d" % idapython.ida_version)

    # blacklist file
    blacklist_file = os.path.join(os.path.dirname(input_file) + 'ida.blacklist')
    if os.path.isfile(blacklist_file):
        # read the file line by line
        print("Blacklist file: %s" % blacklist_file)
        for line in open(blacklist_file):
            line = line.strip()

            print("line >%s<: %d" % (line, int(line, 0)))
            blacklist_addresses.add(int(line, 0))
    else:
        print("Blacklist file not found: %s" % blacklist_file)

    # Diablo files, for dispatcher indicators
    D = Diablo.Diablo(False)
    D.fn_print = Verbose
    D.Load(input_file, os.path.join(os.path.dirname(input_file) + 'origin_final'))

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

    # statically linked binaries don't have a PLT section
    global plt_start, plt_end
    plt_start, plt_end = idapython.find_section(".plt")

    # initialise partitioning
    partitioning.fn_incoming_insns = idapython.BblIncomingInsns
    partitioning.fn_outgoing_insns = idapython.BblOutgoingInsns
    partitioning.fn_next_ins = NextHead
    partitioning.fn_ins_is_call = InsIsCall
    partitioning.fn_get_block_start_address = block_start_address
    partitioning.fn_get_function = get_function
    partitioning.fn_get_function_start = get_function_start
    partitioning.fn_move_block = move_block
    partitioning.fn_get_block_end_address = block_end_address
    partitioning.fn_ins_iterator = None
    partitioning.prioritize_fallthrough = prioritize_ft
    partitioning.fn_filter_predsucc = AddressInPLT
    partitioning.fn_ins_in_block = InsInBlock
    partitioning.fn_dump_ida_db = DumpDatabase
    partitioning.fn_decodable = IsDecodable
    partitioning.fn_print = Verbose

    idapython.fn_print = Verbose

    # we only look at the contents of the .text section
    S, E = idapython.find_section(".text")
    if S > 0:
        process_segment(S, E)

    S, E = idapython.find_section(".init")
    if S > 0:
        process_segment(S, E)

    ifile.close()
    ffile.close()
    bfile.close()
    efile.close()
    sfile.close()
    vfile.close()

    # make sure IDA exits, and does not show a GUI
    Exit(0)

# when this script is loaded as the main program (i.e., a plugin in IDA),
# execute the 'run_ida' function
if __name__ == "__main__":
    run_ida()
