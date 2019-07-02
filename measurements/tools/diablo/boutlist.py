import re
import lib.helpers as helpers

PHASE_FLOWGRAPH = 0
PHASE_DEFLOWGRAPH = 1
PHASE_ADVANCEDFACTORING = 2
PHASE_OBFUSCATION = 3
PHASE_CALLCHECKS = 4
PHASE_SOFTVM = 5
PHASE_SELFDEBUGGING = 6
PHASE_REACTIONS = 7
PHASE_CODE_MOBILITY = 8

def readDiabloListing(filename):
    old_new = {}
    new_old = {}
    data_insns = set()
    pcrel_constant = {}
    info = {}
    switch_add = set()
    switch_ldr = set()
    addresses = {}

    # 1. new/old address pair or single address (unchanged)
    #       (New\s+(0x[0-9a-f]+)\s+Old\s+(0x[0-9a-f]+)|(0x[0-9a-f]+))
    #   (a) new/old address pair
    #       New (0x...) Old (0x...)
    #   (b) single address
    #       (0x...)
    # 2. optional, data to first colon
    #       (\s*[^:\|]*:)?
    #   don't look past the '|' (pipe) characters because these denote ASCII output of raw data, which can include the ':'.
    # (whitespace) \s+
    # 3. instruction opcode
    #       ([^\s]+)
    # (whitespace) \s+
    # 4. optional, instruction operands
    #       (.+)?
    # (optional whitespace) \s*
    # 5. Diablo phase, within parentheses
    #       \(phase:\s*([^\)]+)\)
    # (whitespace) \s+
    # 6. Diablo transformation, within parentheses
    #       \(transformation:\s*([^\)]+)\)
    # (whitespace) \s+
    # 7. Diablo flags, within parentheses
    #       \(flags:\s*([^\)]+)\)
    line_pattern = re.compile(r"^(New\s+(0x[0-9a-f]+)\s+Old\s+(0x[0-9a-f]+)|(0x[0-9a-f]+))(\s*[^:\|]*:)?\s+([^\s]+)\s+(.+)?\s*\(phase:\s*([^\)]+)\)\s+\(transformation:\s*([^\)]+)\)\s+\(flags:\s*([^\)]+)\)")

    operands_pcrel_constant = re.compile(r"^(r[0-9]+),r15,#0(x[0-9a-f]+)?")
    operands_switch_add = re.compile(r"^r15,r15,r[0-9]+,LSL #2")
    operands_switch_ldr = re.compile(r"^r15,\[r15,r[0-9]+,LSL #2\]")

    print("reading %s" % (filename))
    for line in open(filename):
        line = line.strip()

        matches = line_pattern.match(line)
        if not matches:
            continue

        new_address = 0
        old_address = 0
        if matches.group(2) is not None:
            # new/old
            new_address = int(matches.group(2), 16)
            old_address = int(matches.group(3), 16)
        else:
            # single address
            new_address = int(matches.group(4), 16)
            old_address = new_address

        opcode = matches.group(6)
        operands = matches.group(7)
        phase = matches.group(8)
        transformation_id = helpers.signed64(int(matches.group(9), 16))
        flags = int(matches.group(10), 16)

        new_old[new_address] = old_address
        if old_address != 0:
            old_new[old_address] = new_address

        if opcode == "DATA":
            data_insns.add(new_address)
        elif opcode == "ADD":
            if operands_pcrel_constant.match(operands):
                pcrel_constant[new_address] = matches.group(1)
                addresses[new_address] = matches.group(1)
            elif operands_switch_add.match(operands):
                switch_add.add(new_address)
        elif opcode == "LDR":
            if operands_switch_ldr.match(operands):
                switch_ldr.add(new_address)
        elif opcode == "SUB":
            if operands_pcrel_constant.match(operands):
                addresses[new_address] = matches.group(1)

        numeric_phase = -1
        if phase == 'Flowgraph':
            numeric_phase = PHASE_FLOWGRAPH
        elif phase == 'Deflowgraph':
            numeric_phase = PHASE_DEFLOWGRAPH
        elif phase == 'AdvancedFactoring':
            numeric_phase = PHASE_ADVANCEDFACTORING
        elif phase == 'Obfuscation':
            numeric_phase = PHASE_OBFUSCATION
        elif phase == 'CallChecks':
            numeric_phase = PHASE_CALLCHECKS
        elif phase == 'SoftVM':
            numeric_phase = PHASE_SOFTVM
        elif phase == 'Self-Debugging':
            numeric_phase = PHASE_SELFDEBUGGING
        elif phase == 'Reactions':
            numeric_phase = PHASE_REACTIONS
        elif phase == 'Code Mobility':
            numeric_phase = PHASE_CODE_MOBILITY
        else:
            assert False, line

        info[new_address] = {
            'phase': numeric_phase,
            'transformation': transformation_id,
            'flags': flags,
            'opcode': opcode
        }

    return {'old2new': old_new, 'new2old': new_old, 'data_instructions': data_insns, 'constants': pcrel_constant, 'info': info, 'switch_add': switch_add, 'switch_ldr': switch_ldr, 'addresses': addresses}

def readDiabloKilledList(filename):
    add_to_initial = True
    killed_before_initial = []
    killed_before_final = []

    print("reading %s" % (filename))
    for line in open(filename):
        line = line.strip()

        # special line to mark the end of initial killed list
        if line.startswith("ORIGIN_TRACKING"):
            add_to_initial = False
            continue

        old_address = int(line, 16)

        if add_to_initial:
            killed_before_initial.append(old_address)
        killed_before_final.append(old_address)

    return {'before_initial': killed_before_initial, 'before_final': killed_before_final}
