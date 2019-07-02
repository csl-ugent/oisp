def ReadFileTokens(filename):
    print("reading %s" % (filename))
    for line in open(filename):
        line = line.strip()
        if line[0] == '#':
            continue

        yield line.split(':')

def StringToList(str_list):
    return [int(x) for x in str_list.split(',') if x.isdigit()]

def StringToListHex(str_list):
    return [int(x, 16) for x in str_list.split(',') if len(x) > 0]

def signed64(x):
    return -(x & 1<<63) | (x & ~(1<<63))
