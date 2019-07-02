import lib.textualcfg as textualcfg
import lib.helpers as helpers

def readSwitches(filename):
    result = {}

    for tokens in helpers.ReadFileTokens(filename):
        insn = int(tokens[0], 16)
        nr_cases = int(tokens[1])
        default_case = int(tokens[2], 16)
        targets = helpers.StringToListHex(tokens[3])

        result[insn] = {
            'nr_cases': nr_cases,
            'default_case': default_case,
            'targets': targets
        }

    return result

def readIDAFiles(basename):
    i = textualcfg.readInstructions(basename + ".instructions")
    e = textualcfg.readEdges(basename + ".edges")
    b = textualcfg.readBasicBlocks(basename + ".bbls", e)
    f = textualcfg.readFunctions(basename + ".functions")

    s = readSwitches(basename + ".switches")

    return i, b, f, e, s
