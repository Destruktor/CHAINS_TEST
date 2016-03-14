#!/usr/bin/python

import re
import subprocess
import xml.etree.cElementTree as et


class Chains(object):

    _executable_path = './kshort/HREA'
    _input_file_path_prefix = './kshort/graph_file'

    @staticmethod
    def run_chains(k, number_of_destinations, graph_file_path):
        final_paths = dict()
        cmd = Chains._get_command_string(k, number_of_destinations, graph_file_path)
        print "Running CHAINS: " + cmd
        chains_output = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True).communicate()[0]
        print chains_output

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
            final_paths.append(node_path_map[pair[0]][pair[1]])
        print '\nFinal paths'
        #print self._paths
        return final_paths

    @staticmethod
    def write_chains_input_file(n, m, broadcast_node_id, destination_ids, latency_map):
        file_name = Chains._input_file_path_prefix + str(broadcast_node_id)
        f = open(file_name, 'w')

        f.write("n %d\n"% n)
        f.write("m %d\n"% m)
        f.write("s %d\n"% broadcast_node_id)
        f.write("t")
        for i in destination_ids:
            f.write(" %d"% i)
        f.write("\n")
        f.write(latency_map.get_formatted_latency_data())
        f.close()
        return file_name

    @staticmethod
    def _get_command_string(k, number_of_destinations, graph_file_path):
        return ' '.join(
            [Chains._executable_path, graph_file_path, str(k), "-paths -tdijkstra", str(number_of_destinations)]
        )


class MulticastForwardingTable(object):

    def __init__(self):
        pass

    @staticmethod
    def build_MFT(path_list):
        head = MulticastForwardingTable._build_tree(path_list)
        table = MulticastForwardingTable._build_table(head)
        return table

    @staticmethod
    def _build_tree(path_list):
        head = MFTNode()
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
                    temp = MFTNode(n_id=node_id, n_dest=(destination,), n_parent=curr_node)
                    curr_node.children += (temp,)
                    curr_node = temp
        return head

    @staticmethod
    def _build_table(head):
        forwarding_table = dict()
        for node in MulticastForwardingTable._walk(head.children[0]):
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

    @staticmethod
    def _walk(n):
        # Based on: http://stackoverflow.com/a/3010038/2825538
        # iterate tree in pre-order depth-first search order
        yield n
        for c in n.children:
            for n_n in MulticastForwardingTable._walk(c):
                yield n_n


class MFTNode(object):
    def __init__(self, n_id=None, n_dest=None, n_parent=None):
        self.id = n_id  # Node id
        if n_dest is None:
            self.dest = tuple()
        else:
            self.dest = n_dest  # tuple of Node ids
        self.parent = n_parent  # another Node object#do i need this??
        self.children = tuple()  # tuple of Nodes




