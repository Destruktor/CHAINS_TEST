import re
import subprocess


class Chains(object):

    _executable_path = './kshort/HREA'

    @staticmethod
    def run_chains(self, k, number_of_destinations, graph_file_path):
        final_paths = dict()
        cmd = self.get_command_string(k, number_of_destinations, graph_file_path)
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
            final_paths.append(node_path_map[pair[0]][pair[1]])
        print '\nFinal paths'
        print self._paths
        return final_paths

    def _get_command_string(self, k, number_of_destinations, graph_file_path):
        return ' '.join(
            [self._executable_path, graph_file_path, str(k), "-paths -tdijkstra", str(number_of_destinations)]
        )
