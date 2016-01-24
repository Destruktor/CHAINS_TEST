#!/usr/bin/python

import subprocess
import re
import time

number_of_destinations = 5
edge_chance = .9
scale = 10

# list of tuples containng ( # of destinations, avg path length, final_paths)
final_data = []

#create graph file
g = open('./gt-itm/graphs_new/rand_graph','w')
seed = time.time()
g.write("geo 1 " + str(seed) + "\n")
g.write("100 " + str(scale) + " 3 " + str(edge_chance) + "\n")
g.close()

# call random graph generator
subprocess.call(['/home/citadel_nrhodes/gt-itm/bin/itm', '/home/citadel_nrhodes/gt-itm/graphs_new/rand_graph'])
subprocess.call(['/home/citadel_nrhodes/gt-itm/bin/sgb2alt', '/home/citadel_nrhodes/gt-itm/graphs_new/rand_graph-0.gb', '/home/citadel_nrhodes/gt-itm/graphs_new/out'])

# get latency measurements from outfile
o = open('./gt-itm/graphs_new/out')

while o.readline().split()[0] != 'GRAPH':
    #print "Looking for GRAPH\n"
    continue
file_info = o.readline().split()
print file_info
n = file_info[0]
m = file_info[1]
while o.readline() == '':
    #print "Looking for VERTICES\n"
    continue
while not o.readline().startswith('EDGES'):
    #print "Looking for EDGES\n"
    continue
edges = ''
while file_info:
    file_info = o.readline()
    match = re.match('^\d+ \d+ \d+', file_info)
    if match:
        temp = match.group(0).split()
        temp[0] = str(int(temp[0])+1)
        temp[1] = str(int(temp[1])+1)
        edges += 'a ' + ' '.join(temp) + '\n'
        edges += 'a ' + temp[1] + ' ' + temp[0] + ' ' + temp[2] + '\n'
o.close()

#print edges
# write formated graph file
f = open('./gt-itm/graphs_new/chains_in', 'w')
f.write("n " + n + "\n")
f.write("m " + m + "\n")
f.write("s 1\n")
f.write("t")
for i in range(2, number_of_destinations+2):
    f.write(" %d"% i)
f.write("\n")
f.write(edges)
f.close()

# call chains
cmd = "./kshort/HREA ./gt-itm/graphs_new/chains_in 100 -paths -tdijkstra " + str(n)
print cmd
chains_output = subprocess.Popen([cmd], stdout=subprocess.PIPE,bufsize=1000000, shell=True).communicate()[0]
#print chains_output

# get finals paths data
re_match_paths = "(?:-\d+)+-\s+\(Cost:\s\d+\)"
chains_output_filtered_paths = re.findall(re_match_paths, chains_output)

#build a list of all paths for each node, with delay as key
#dict ip dest_node -> delay -> path
node_path_map = dict()
for raw_path in chains_output_filtered_paths:
    path_cost = re.search("\d+(?=\))", raw_path).group(0)
    path = re.search("(\d+-)+", raw_path).group(0).split('-')[:-1]
    dest_node = path[0]
    if dest_node not in node_path_map:
        node_path_map[dest_node] = dict()
    node_path_map[dest_node][path_cost] = path
#print '\nNode PAth Map'
#print node_path_map

#grab dest_node/delay pairs for MVC
re_match_mvc = "Delay\s:.*\n"
chains_output_filtered_mvc = re.findall(re_match_mvc, chains_output)
dest_node_delay_pairs = []
for line in chains_output_filtered_mvc:
    temp_delay = re.search("(?<=Delay\s:\s)\d+", line).group(0)
    temp_dest = re.search("(?<=Destination\s)\d+", line).group(0)
    dest_node_delay_pairs.append((temp_dest, temp_delay))
print '\nNode Dest DElays'
print dest_node_delay_pairs

#get final list of paths
final_paths = []
for pair in dest_node_delay_pairs:
    final_paths.append(node_path_map[pair[0]][pair[1]])
print '\nFinal paths'
print final_paths
sum = 0
for item in final_paths:
    sum += len(item)
avg_path_length = str(float(sum)/len(final_paths))
print "Average path length: " + avg_path_length

final_data.append((number_of_destinations, avg_path_length, final_paths))