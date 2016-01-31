#!/usr/bin/python

import subprocess
import socket
import struct
from threading import Thread, Lock
import Queue
import re
import sys
import xml.etree.cElementTree as et
from NodeManager import NodeManager

#Central Node acts as the hub for session requests as well as
#  data collection
#-Accept requests to start broadcast sessions
#-keep updated latency_file
#-generate new graph_file for each session
#-broadcast tabel updates to nodes
#-gather data


class CentralNode(object):
    _NUM_PROCESSING_THREADS = 25
    _HOST = ''
    _PORT = 50006

    def __init__(self):
        self._node_mapping = dict()
        self.node_manager = NodeManager()
        self._table = dict()
        self._table_lock = Lock()
        self._latency_map = LatencyMap()
        #dict to store test data
        self._time_data_final = dict()

        #shared queue for broadcasting packets
        # each queue entry should be a tuple
        # containing the next hop ip and data
        # (next_hop_ip, data)
        self._packet_queue = Queue.Queue(maxsize=0)
        for i in range(self._NUM_PROCESSING_THREADS):
             t = Thread(target=self._process_packet)
             t.setDaemon(True)
             t.start()

        t_server = Thread(target=self._central_node_server)
        t_server.setDaemon(True)
        t_server.start()

    def _init_session(self, broadcast_node_id, destination_node_ids):
        # create time data structure
        self._time_data_final[broadcast_node_id] = dict()
        for node in destination_node_ids:
            self._time_data_final[broadcast_node_id][node] = []

        # get node latency data

        f = open('./kshort/latency_file', 'r')
        latency_data = f.read()
        f.close()

        #get node mapping
        #node_mapping = dict()
        nm_f = open('./node_mapping', 'r')
        node_count = 0
        for line in nm_f:
            node_count += 1
            node_num = int(re.search('^(\d+)', line).group(0))
            print node_num
            node_hostname = re.search('(?<=\s)(.+?)\s', line).group(0)
            print node_hostname
            node_ip = re.search('([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', line).group(0)
            print node_ip
            node_mapping[node_num] = (node_hostname, node_ip)
            node_mapping[node_ip] = node_num
        print node_mapping
        nm_f.close()

        arc_count = 0
        for line in latency_data.split('\n'):
            arc_count += 1
            #print "Count / line"
            #print str(arc_count) + " / " + line

        n = node_count
        m = arc_count - 1

        destinations = [node_mapping[x] for x in destination_node_ids]

        file_name = './kshort/graph_file' + str(node_mapping[broadcast_node_id])
        f = open(file_name, 'w')

        f.write("n %d\n"% n)
        f.write("m %d\n"% m)
        f.write("s %d\n"% node_mapping[broadcast_node_id])
        f.write("t")
        for i in destinations:
            f.write(" %d"% i)
        f.write("\n")
        f.write(latency_data)
        f.close()
        subprocess.Popen(['./GenerateNodeTable.py', file_name, '100'])

    def _process_packet(self):
        global node_mapping
        control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        #Enter a loop to check shared queue and send any outstnding packets
        while 1:

            packet = self._packet_queue.get(block=True)
            bytes = packet[0]
            addr = packet[1]

            control_bit = bytes[0]

            if control_bit == '0':#init session
                # what data do we need
                # broadcast node, set of destinations

                broadcast_node_id = socket.inet_ntoa(bytes[1:5])
                broad_node_socket = bytes
                destination_node_ids = []
                temp_len = len(bytes)#will this work maybe?????
                i = 5
                while i < temp_len:
                    temp_dest = socket.inet_ntoa(bytes[i:i+4])
                    #print "Adding destination: " + temp_dest
                    destination_node_ids.append(temp_dest)
                    i += 4

                self._init_session(broadcast_node_id, destination_node_ids)

                #send confirmation of session initialization
                ###**Do this in Generate Node Table

            elif control_bit == '1':#data from node for session
                #[control_bit][broadcast node][dest node][(source_time_float, dest_time_float),..]
                broadcast_node_id = socket.inet_ntoa(bytes[1:5])

                destination_node_id = socket.inet_ntoa(bytes[5:9])

                time_offset = struct.unpack("d",''.join(bytes[9:17]))[0]
                print "Time Offset: "
                print time_offset
                print "Length of data Packet: " + str(len(bytes[17:]))
                #[(source_timestamp1, dest_timestamp1), (source_timestamp2, dest_timestamp2),...]
                i = 17
                data = []
                while i < len(bytes):
                    t1_temp = struct.unpack("d",''.join(bytes[i:i+8]))[0]
                    t2_temp = struct.unpack("d", ''.join(bytes[i+8:i+16]))[0]
                    #print "Adding Time Values: "
                    #print t1_temp, t2_temp
                    data.append((t1_temp, t2_temp))
                    i += 16
                if broadcast_node_id not in self._time_data_final:
                    self._time_data_final[broadcast_node_id] = dict()
                self._time_data_final[broadcast_node_id][destination_node_id] = (time_offset, data)
                #print "Time Data Final"
                #print time_data_final

            elif control_bit == '2':#terminate transmission

                broadcast_node_id = socket.inet_ntoa(bytes[1:5])
                broadcast_t_offset = struct.unpack("d", bytes[5:13])[0]

                print "Session " + broadcast_node_id + " terminated..."
                print "Processing session data..."

                f_out = open('test_out', 'w')
                #process data
                f_out.write(broadcast_node_id + "\n")
                for node, t_data in self._time_data_final[broadcast_node_id].iteritems():
                    #print "Packet Data for node: " + node + ": "
                    #print t_data
                    dest_t_offset = t_data[0]
                    f_out.write(node + "," + str(node_mapping[node]) + ",")
                    for d in t_data[1]:
                        time_correction = broadcast_t_offset - dest_t_offset
                        raw_t_diff = d[1] - d[0]
                        delta = raw_t_diff + time_correction
                        #print "("+str(d[0])+", "+str(d[1])+") ~ " +  str(delta)
                        f_out.write(str(delta * 1000) + ",")
                    f_out.write("\n")
                    #calculate useful stuffs

                    #print
                #delete session data
                f_out.close()
                self._time_data_final[broadcast_node_id] = {}
            elif control_bit == '3':#get data for diagnostic session
                #data in xml
                #print bytes
                root = et.fromstring(bytes[1:])
                #print root
                destination_node_id = root.attrib['destination_node_id']
                broadcast_node_id = root.attrib['broadcast_node_id']


                time_offset = root.attrib['time_offset']
                print "Time Offset: "
                print time_offset
                print "Length of data Packet: " + str(len(bytes[1:]))
                data = []
                #each destination will have a dict of lists. each list represents a single packet
                #time_data_final[broadcast_node_id][destination_node_id] = {1:[(ip, receive_time, transmit_time),...],...}
                packet_data_dict = dict()
                for packet_data in root:
                    packet_data_list = []
                    for entry in packet_data:
                        temp_ip = entry.attrib['ip']
                        temp_delta_t = float(entry.attrib['time_offset'])
                        receive_time = float(entry.attrib['receive_time'])
                        transmit_time = float(entry.attrib['transmit_time'])
                        hop_number = int(entry.attrib['hop_number'])
                        packet_data_list.append((temp_ip, temp_delta_t, receive_time,transmit_time,hop_number))
                    packet_data_dict[packet_data.attrib['number']]=packet_data_list

                if broadcast_node_id not in self._time_data_final:
                    self._time_data_final[broadcast_node_id] = dict()
                self._time_data_final[broadcast_node_id][destination_node_id] = packet_data_dict
                #print "Time Data Final"
                #print time_data_final
            elif control_bit == '4':#closeout diagnostic session
                broadcast_node_id = socket.inet_ntoa(bytes[1:5])
                broadcast_t_offset = struct.unpack("d", bytes[5:13])

                print "Session " + broadcast_node_id + " terminated..."
                print "Processing session data..."

                f_out = open('test_out', 'w')
                #process data
                f_out.write(broadcast_node_id + "\n")
                for node, t_data in self._time_data_final[broadcast_node_id].iteritems():
                    print "Packet Data for node: " + node + ": "
                    #print t_data
                    f_out.write(node + "," + str(node_mapping[node]) + "\n")
                    for key in sorted(t_data.iterkeys()):#dictionary of lists
                        values = t_data[key]
                        f_out.write(str(key) + ',' + str(node_mapping[node]) + '\n')
                        values.sort(key=lambda tup: tup[4])
                        old_transmit_time = None
                        for entry in values:
                            corrected_receive_time = None
                            corrected_send_time = None
                            temp_node_id = ''
                            format_string = "%d,%s,%s,%f,%f,%f"
                            if entry[0] == 'destination' or entry[0] == 'source':
                                temp_node_id = entry[0]
                            else:
                                temp_node_id = str(node_mapping[entry[0]])
                            if entry[1] > 0.0:
                                corrected_receive_time = entry[1] + entry[2]
                                format_string += ",%f"
                            else:
                                corrected_receive_time = 'Null'
                                format_string += ",%s"
                            if entry[2] > 0.0:
                                corrected_send_time = entry[1] + entry[3]
                                format_string += ",%f"
                            else:
                                corrected_send_time = 'Null'
                                format_string += ",%s"
                            if corrected_send_time is not 'Null' and corrected_receive_time is not 'Null':
                                processing_time = corrected_send_time - corrected_receive_time
                                format_string += ",%f"
                            else:
                                processing_time = 'Null'
                                format_string += ",%s"
                            if corrected_receive_time is not 'Null' and old_transmit_time is not 'Null':
                                transmit_time = corrected_receive_time - old_transmit_time
                                format_string += ",%f"
                            else:
                                transmit_time = 'Null'
                                format_string += ",%s"
                            if corrected_send_time != 'Null':
                                old_transmit_time = corrected_send_time
                            format_string += "\n"
                            f_out.write(format_string % (entry[4], temp_node_id, entry[0], entry[1], entry[2], entry[3], corrected_receive_time, corrected_send_time, processing_time, transmit_time))
                        f_out.write('\n')

                    #print
                #delete session data
                f_out.close()
                self._time_data_final[broadcast_node_id] = {}

    def _central_node_server(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        this_node_id = socket.gethostbyname(socket.gethostname())
        print 'Central Node ip: ' + this_node_id
        print 'Socket Created. Initializing...'
        try:
            s.bind((self._HOST, self._PORT))
        except socket.error, msg:
            print 'Bind failed. Error code: ' + str(msg[0]) + ', Error message : ' + msg[1]
            sys.exit();

        print 'Socket bound on port: ' + str(self._PORT)

        #hang out and listen for stuffs
        while 1:
            data, addr = s.recvfrom(16384)
            print 'Connected with', addr[0] + ':' + str(addr[1])
            #process data

            self._packet_queue.put((data, addr))

    def update_node_multicast_forwarding_table(self, node, table):
        #
        PORT = 50007
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        for key, value in table.iteritems():
            table = et.Element('table')
            source_node = et.SubElement(table, 'source_node')
            source_node.attrib['broadcast_node'] = node_mapping[1][1]
            for pair in value:
                temp_node = et.SubElement(source_node, "destination_node")
                temp_node.attrib['next_hop'] = pair[1]
                temp_node.text = pair[0]#should capture ips for each node

            xml_table = et.tostring(table)
            print xml_table
            s.sendto('0' + xml_table, (key, PORT))

if __name__=="main":
    c_node = CentralNode()
    while True:
        pass
