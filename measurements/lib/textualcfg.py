import lib.helpers as Helpers

# result = {
#     'instructions': {
#         0x1234: {
#             'function_uid': [f1, f2],
#             'bbl_uid': [b1, b2],
#             'executed': 0
#         },
#         0x5678: {
#             'function_uid': [f1],
#             'bbl_uid': [b3],
#             'executed': 1
#         },
#         ...
#     }
#     'functions': {
#         f1: [0x1234, 0x5678],
#         f2: [0x1234],
#         ...
#     }
# }
def readInstructions(filename):
    insns = {}

    # we can't base the function association on BBLs because IDA has a different concept of what a BBL is
    # hence, we have to base the ordering on an instruction level
    functions = {}

    # sort instructions per basic block
    bbls = {}

    for tokens in Helpers.ReadFileTokens(filename):
        numeric_address = int(tokens[0], 16)
        bbl_uid = int(tokens[1])
        # we need to include the function UID here because IDA sometimes puts the same instruction in multiple functions
        function_uid = int(tokens[2])
        executed = int(tokens[3]) == 1
        assembled = 0
        if len(tokens) > 4:
            assembled = int(tokens[4], 16)
        is_thumb = False
        if len(tokens) > 5:
            is_thumb = bool(int(tokens[5]) == 1)
        is_nop = False
        if len(tokens) > 6:
            is_nop = bool(int(tokens[6]) == 1)
        is_macro = False
        if len(tokens) > 7:
            is_macro = bool(int(tokens[7]) == 1)

        if numeric_address in insns:
            # apparently IDA sometimes associates the same instruction with multiple functions
            # and thus with multiple basic blocks too
            insns[numeric_address]['function_uid'].append(function_uid)
            insns[numeric_address]['bbl_uid'].append(bbl_uid)
            insns[numeric_address]['executed'] |= executed
            insns[numeric_address]['assembled'] = assembled
            insns[numeric_address]['thumb'] = is_thumb
            insns[numeric_address]['nop'] = is_nop
            insns[numeric_address]['macro'] = is_macro
        else:
            insns[numeric_address] = {
                'function_uid': [function_uid],
                'bbl_uid': [bbl_uid],
                'executed': executed,
                'assembled': assembled,
                'thumb': is_thumb,
                'nop': is_nop,
                'macro': is_macro
            }

        if function_uid not in functions:
            functions[function_uid] = []
        functions[function_uid].append(numeric_address)

        if bbl_uid not in bbls:
            bbls[bbl_uid] = set()
        bbls[bbl_uid].add(numeric_address)

    return {'instructions': insns, 'functions': functions, 'bbls': bbls}

# result = {
#     b1: {
#         'address': 0x1234,
#         'nins': 2,
#         'function_uid': f1
#     },
#     ...
# }
def readBasicBlocks(filename, all_edges):
    result = {}

    for tokens in Helpers.ReadFileTokens(filename):
        uid = int(tokens[0])
        address = int(tokens[1], 16)
        nins = int(tokens[2])
        function_uid = int(tokens[3])

        incoming = []
        if address in all_edges['incoming']:
            incoming = all_edges['incoming'][address]

        result[uid] = {
            'address': address,
            'nins': nins,
            'function_uid': function_uid,
            'incoming': incoming,
            'is_function_entry': False
        }

    return result

# result = {
#     f1: {
#         'name': 'foo'
#     },
#     ...
# }
def readFunctions(filename):
    result = {}

    for tokens in Helpers.ReadFileTokens(filename):
        uid = int(tokens[0])
        name = ':'.join(tokens[1:-2])
        original_uid = int(tokens[-2])
        partition_uid = int(tokens[-1])

        result[uid] = {
            'name': name,
            'original_uid': original_uid,
            'partition_uid': partition_uid,
            'bbls': set()
        }

    return result

# result = [
#   {
#       'head': BBL address (from),
#       'tail': BBL address (to)
#   },
#   ...
# ]
def readEdges(filename):
    edges = {}
    outgoing = {}
    incoming = {}
    to_uid = {}

    for tokens in Helpers.ReadFileTokens(filename):
        uid = int(tokens[0])
        head_address = int(tokens[1], 16)
        insn_address = int(tokens[2], 16)
        tail_address = int(tokens[3], 16)
        to_plt = bool(int(tokens[4]))
        edge_type = int(tokens[5])
        fake = bool(int(tokens[6]))

        flags = 0
        if len(tokens) > 7:
            flags = int(tokens[7])

        edges[uid] = {
            'head': head_address,
            'tail': tail_address,
            'branch': insn_address,
            'to_plt': to_plt,
            'type': edge_type,
            'fake': fake,
            'flags': flags
        }

        if insn_address not in outgoing:
            outgoing[insn_address] = []
        outgoing[insn_address].append(uid)

        if tail_address not in incoming:
            incoming[tail_address] = []
        incoming[tail_address].append(uid)

        if insn_address not in to_uid:
            to_uid[insn_address] = {}
        if tail_address not in to_uid[insn_address]:
            to_uid[insn_address][tail_address] = set()
        to_uid[insn_address][tail_address].add(uid)

    return {'edges': edges, 'outgoing': outgoing, 'incoming': incoming, 'to_uid': to_uid}
