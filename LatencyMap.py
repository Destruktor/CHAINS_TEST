#!/usr/bin/python

import socket
import struct
from threading import Thread, Lock


class LatencyMap(object):
    def __init__(self):
        self._table_lock = Lock()
        self._latency_table = dict()
        self._node_mapping = dict() # Node mapping should be passed in

    def generate_node_mapping(self, node_hostnames, output_to_file=False):
        for count, nodeA in enumerate(node_hostnames):
            self._latency_table[nodeA] = {}
            self._node_mapping[nodeA] = count+1
            self._node_mapping[count+1] = nodeA

        if(output_to_file):
            # Write Node Mapping to file
            nm_f = open('node_mapping', 'w')
            for i in range(1, len(node_hostnames) + 1):
                nm_f.write( str(i) + ' ' +
                            self._node_mapping[i][0] + ' ' +
                            self._node_mapping[i][1] + '\n')
            nm_f.close()

    def _get_node_latency(self, target_node_id, measurement_nodes):
        """
        :param target_node_id: ID of node that should perform the measurements
        :param measurement_nodes: nodes that target ip will measure measure latency
        :return: None
        """
        target_ip = self._node_mapping[target_node_id]
        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        response_received = False
        measurement_node_ips = '5' + ''.join([socket.inet_aton(socket.gethostbyname(self._node_mapping[x]))
                                              for x in measurement_nodes])
        while not response_received:
            lat_data = ''
            try:
                temp_sock.sendto(measurement_node_ips, (target_ip, 50007))
                # return data [(node ip, latecy), ...]
                temp_sock.settimeout(240)
                lat_data = temp_sock.recv(2048)
                response_received = True
            except socket.timeout, msg:
                print 'Socket timeout on %s' % target_ip
                print msg
                continue
        i = 0
        while i < len(lat_data):
            temp_node = socket.inet_ntoa(lat_data[i:i+4])
            temp_lat = struct.unpack('d', lat_data[i+4:i+12])[0]
            node_id_from_ip = socket.gethostbyaddr(temp_node)
            self._table_lock.acquire(True)
            self._latency_table[target_node_id][self._node_mapping[node_id_from_ip]] = temp_lat
            self._table_lock.release()
            i += 12
        temp_sock.close()

    def generate_latency_map(self):
        threads_to_join = []
        i = 0
        length_node_mapping = len(self._node_mapping)
        MAX_NODES_PER=(length_node_mapping-1)/2
        for node_id, node_hostname in self._node_mapping.iteritems():
            i+=1
            self._latency_table[node_id] = dict()
            # build a list of nodes for each node to ping
            adj = 0
            if i <= length_node_mapping/2+length_node_mapping % 2:
                adj = (length_node_mapping+1) % 2
            temp_node_list = [self._node_mapping[k%length_node_mapping] for k in xrange(i,i+MAX_NODES_PER+adj)]
            # print "Temp Node List: " + temp_node_list
            temp_thread = Thread(target=self._get_node_latency, args=(node_id, temp_node_list))
            temp_thread.start()
            threads_to_join.append(temp_thread)

        for t in threads_to_join:
            t.join()

    def write_latency_graph_tofile(self, path):
        # f = open('./kshort/latency_file', 'w')
        f = open(path, 'w')
        for nodeA, dest in self._latency_table.iteritems():
            for nodeB, values in dest.iteritems():
                one_way_latency = values
                if one_way_latency < 10.00:#maximum resolution of 10 ms, try to limit low latency links
                    one_way_latency = 1000.0#don't use these connections
                print("one way latency: %f" % one_way_latency)
                one_way_str = str(one_way_latency).split('.')[0]
                print("One way string: %s" % one_way_str)
                f.write("a %d %d %s\n" % (nodeA, nodeB, one_way_str))
                f.write("a %d %d %s\n" % (nodeB, nodeA, one_way_str))

        f.close()

    def get_node_mapping(self):
        return self._node_mapping

    def get_latency_table(self):
        return self._latency_table

    def node_mapping_length(self):
        return len(self._node_mapping)
