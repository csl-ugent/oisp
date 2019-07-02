import lib.textualcfg as textualcfg
import lib.helpers as helpers

def readFunctions(filename):
    return textualcfg.readFunctions(filename)

# result = {
#     'objects': {
#         uid1: {
#             'name': 'path1.o',
#             'archive_uid': uid1
#         },
#         ...
#     },
#     'archives': {
#         uid1: 'library.a',
#         ...
#     }
# }
def readObjects(filename):
    result = {}

    for tokens in helpers.ReadFileTokens(filename):
        # lines have one of two forms:
        #  uid:path.o
        #  uid:path.a:file.o
        uid = int(tokens[0])
        name = tokens[1]

        if len(tokens) == 3:
            # need to construct the full name: archive(object)
            name = "%s(%s)" % (tokens[1], tokens[2])

        result[uid] = {
            'name': name
        }

    return result

def readArchives(filename):
    result = {}

    for tokens in helpers.ReadFileTokens(filename):
        uid = int(tokens[0])
        name = tokens[1]

        result[uid] = {
            'name': name
        }

    return result

def readPartitions(filename):
    result = {}

    for tokens in helpers.ReadFileTokens(filename):
        uid = int(tokens[0])
        scc_uid = int(tokens[1])
        associated_functions = helpers.StringToList(tokens[2])
        associated_objects = helpers.StringToList(tokens[3])
        associated_libraries = helpers.StringToList(tokens[4])

        result[uid] = {
            'scc_uid': scc_uid,
            'associated_functions': associated_functions,
            'associated_objects': associated_objects,
            'associated_libraries': associated_libraries
        }

    return result

def readSCCs(filename):
    result = {}

    for tokens in helpers.ReadFileTokens(filename):
        uid = int(tokens[0])
        reachable_functions = helpers.StringToList(tokens[1])
        reachable_objects = helpers.StringToList(tokens[2])
        reachable_libraries = helpers.StringToList(tokens[3])

        result[uid] = {
            'reachable_functions': reachable_functions,
            'reachable_objects': reachable_objects,
            'reachable_libraries': reachable_libraries
        }

    return result
