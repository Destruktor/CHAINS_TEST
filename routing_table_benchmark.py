__author__ = 'no295d'

import routing_table_benchmark_constants as CONSTANTS
import timeit
import os
import random
import fianl_paths

# build a tree with the given strings
class Node:
    def __init__(self, n_id=None, n_dest=None, n_parent=None):
        self.id = n_id  # Node id
        if n_dest is None:
            self.dest = tuple()
        else:
            self.dest = n_dest  # tuple of Node ids
        self.parent = n_parent  # another Node object#do i need this??
        self.children = tuple()  # tuple of Nodes


def walk(n):
    # Based on: http://stackoverflow.com/a/3010038/2825538
    # iterate tree in pre-order depth-first search order
    yield n
    for c in n.children:
        for n_n in walk(c):
            yield n_n


def make_tree():
    ret_list = []
    # print "Total Nodes | total dest | avg path len | total nodes | expected nodes | packing factor"
    counts = {}
    for overlay_node_count, value in fianl_paths.final_paths.iteritems():
        counts[overlay_node_count] = {}
        for destination_count, path_list in value.iteritems():
            # doo some stuff
            for index, path in enumerate(path_list):
                path[-2] = str(index+2+destination_count)# added to mimic worst case scenario
            # print path_list
            head = Node()
            node_count = 0###
            path_length = 0###
            for path in path_list:
                path_length += len(path)###
                destination = int(path[0])
                curr_node = head
                for node_id in reversed([int(x) for x in path]):
                    for t_id in curr_node.children:
                        if node_id == t_id.id:
                            curr_node = t_id
                            curr_node.dest += (destination,)
                            break
                    else:
                        node_count += 1###
                        temp = Node(n_id=node_id, n_dest=(destination,), n_parent=curr_node)
                        curr_node.children += (temp,)
                        curr_node = temp
            avg_path_length = path_length / float(len(path_list))
            expected_nodes = len([temp for sublist in path_list for temp in sublist]) - len(path_list) + 1
            packing_factor = float(node_count)/expected_nodes
            # print "{0:^12}|{1:^12}|{2:^14.2}|{3:^13}|{4:^16}|{5:.2}".format(overlay_node_count, destination_count, avg_path_length, node_count, expected_nodes, packing_factor)
            counts[overlay_node_count][destination_count] = (avg_path_length, node_count, expected_nodes, packing_factor)
    return counts


def build_table(head):
    # dictionary representing forwarding table
    forwarding_table = dict()
    for node in walk(head.children[0]):
        # build dictionary of form
        # {node: ((destinations), next_hop)
        if node.id not in forwarding_table:
            forwarding_table[node.id] = dict()
        forwarding_table[node.id][node.dest[0]] = tuple()
        if node.id in node.dest:
            # in this case we will deliver to application
            forwarding_table[node.id][node.id] += ((node.id, node.id),)
        for c_node in node.children:
            forwarding_table[node.id][node.dest[0]] += ((c_node.id, c_node.dest[0]),)
    return forwarding_table

# get a random set of paths for testing
def build_paths_chains(number_of_nodes, number_of_destinations):
    # build random latency file
    with open('latency_file','w') as latency_file:
        latency_file.write('n '+number_of_nodes+'\n')# write header stuff
        latency_file.write('s 1\n')# write header stuff
        latency_file.write('d ')
        for dest in xrange(number_of_destinations):
            latency_file.write(dest+' ')# write header stuff
        latency_file.write('\n')

        for nodeA in xrange(number_of_nodes):
            for nodeB in xrange(nodeA+1,number_of_nodes):
                latency = int(random.gauss(100,10))
                latency_file.write('a '+nodeA+' '+nodeB+' '+str(latency)+'\n')

    # feed file to chains
    cmd = "./kshort/HREA " + latency_file + " " + "100" + " -paths -tdijkstra " + str(number_of_nodes)
    chains_output = os.popen(cmd)

def build_paths(number_of_destinations, avg_path_length, overlay_size):
    min_nodes_in_path = avg_path_length - 3
    max_node_in_path = avg_path_length - 1
    paths = []
    for dest in xrange(2,number_of_destinations+2):
        path_len = random.randint(min_nodes_in_path, max_node_in_path)
        s=set()
        while len(s) < path_len:
            next_node = random.randint(number_of_destinations+2,number_of_destinations+overlay_size+2)
            # print "adding node {} for numb dest {} and apl {} with overlay size {}".format( next_node, dest, path_len, overlay_size)
            s.add(next_node)
        paths.append([str(dest)] + [str(x) for x in s] + ['1'])
    return paths


def under_test():
    head = Node()
    for path in path_list:
        destination = int(path[0])
        curr_node = head
        for node_id in reversed([int(x) for x in path]):
            for t_id in curr_node.children:
                if node_id == t_id.id:
                    curr_node = t_id
                    curr_node.dest += (destination,)
                    break
            else:
                temp = Node(n_id=node_id, n_dest=(destination,), n_parent=curr_node)
                curr_node.children += (temp,)
                curr_node = temp


if __name__ == "__main__":
    # get the values for node count, etc

    setup='import routing_table_benchmark\n'
    # final_paths = {}
    # for n_dest in xrange(5, 101, 1):
    #     o_size = n_dest
    #     final_paths[o_size] = {}
    #     for a_path_len in xrange(3, o_size-1, 3):
    #         final_paths[o_size][a_path_len] = build_paths(n_dest,a_path_len, o_size)
    # counts = make_tree()
    results={}
    print "Total nodes in overlay | Destinations | Avg path len | time per cycle"
    for destination_count, value in fianl_paths.final_paths.iteritems():
        for average_path_length, path_list in value.iteritems():
            ##doo some stuff
            head = Node()
            #node_count = counts[overlay_node_count][average_path_length][1]
            #avg_path_length = counts[overlay_node_count][average_path_length][0]
            _setup = setup+'routing_table_benchmark.path_list='+str(path_list)+'\n'
            results[destination_count] = results.get(destination_count, {})
            results[destination_count][average_path_length] = timeit.timeit(stmt="routing_table_benchmark.under_test()",setup=_setup,number=CONSTANTS.number)
            print "{:23}|{:14}|{:14}|{:15f}".format( 100, destination_count, average_path_length, results[destination_count][average_path_length]/CONSTANTS.number)

