#!/usr/bin/python

import re
import subprocess


class Chains(object):

    def __init__(self, graph_file_path, number_of_shortest_paths):
        self._executable_path = "./kshort/HREA "
        self._graph_file_path = graph_file_path
        self._k = number_of_shortest_paths
        self._paths = []

    def get_paths(self):
        return self._paths

    def generate_paths_from_graph(self, latency_map, node_manager):
        cmd = self._get_command_string(latency_map.nodemapping_length())
        chains_output = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True).communicate()[0]

        re_match_paths = "(?:-\d+)+-\s+\(Cost:\s\d+\)"
        chains_output_filtered_paths = re.findall(re_match_paths, chains_output)

        # build a list of all paths for each node, with delay as key
        # dict ip dest_node -> delay -> path
        node_path_map = dict()
        for raw_path in chains_output_filtered_paths:
            path_cost = re.search("\d+(?=\))", raw_path).group(0)
            path = re.search("(\d+-)+", raw_path).group(0).split('-')[:-1]
            dest_node = path[0]
            if dest_node not in node_path_map:
                node_path_map[dest_node] = dict()
            node_path_map[dest_node][path_cost] = path
        print '\nNode PAth Map'
        print node_path_map

        # grab dest_node/delay pairs for MVC
        re_match_mvc = "Delay\s:.*\n"
        chains_output_filtered_mvc = re.findall(re_match_mvc, chains_output)
        dest_node_delay_pairs = []
        for line in chains_output_filtered_mvc:
            temp_delay = re.search("(?<=Delay\s:\s)\d+", line).group(0)
            temp_dest = re.search("(?<=Destination\s)\d+", line).group(0)
            dest_node_delay_pairs.append((temp_dest, temp_delay))
        print '\nNode Dest DElays'
        print dest_node_delay_pairs

        # get final list of paths
        for pair in dest_node_delay_pairs:
            self._paths.append(node_path_map[pair[0]][pair[1]])
        print '\nFinal paths'
        print self._paths


    def _get_command_string(self, number_of_nodes):
        return ' '.join((self._executable_path, self._graph_file_path, str(self._k), "-paths -tdijkstra", str(number_of_nodes)))


class MulticastForwardingTable(object):

    def __init__(self):
        pass

    def _build_tree(self, path_list):
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
        return head

    def build_table(self, head):
        forwarding_table = dict()
        for node in self._walk(head.children[0]):
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

    def _walk(self, n):
        # Based on: http://stackoverflow.com/a/3010038/2825538
        # iterate tree in pre-order depth-first search order
        yield n
        for c in n.children:
            for n_n in self._walk(c):
                yield n_n


class Node(object):
    def __init__(self, n_id=None, n_dest=None, n_parent=None):
        self.id = n_id  # Node id
        if n_dest is None:
            self.dest = tuple()
        else:
            self.dest = n_dest  # tuple of Node ids
        self.parent = n_parent  # another Node object#do i need this??
        self.children = tuple()  # tuple of Nodes




