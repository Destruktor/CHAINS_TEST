#!/usr/bin/python

__author__ = 'no295d'

import socket
import time
import xml.etree.cElementTree as et
from threading import Thread, Lock
from sets import Set
import Queue
import sys
import struct
import logging


class NodeServer(object):

    TS_ADDR = '192.12.33.102'
    TS_PORT = 50008
    HOST = ''                 # Symbolic name meaning all available interfaces
    PORT = 50007              # Arbitrary non-privileged port
    APP_PORT = 50009
    NUM_BROADCAST_THREADS = 100

    def __init__(self):
        self._this_node_id = socket.gethostbyname(socket.gethostname())
        self._time_data = {}
        self._delta_t = self._synchronize()
        logging.info('Time Syncronized with delta of: ' + str(self._delta_t) + ' milliseconds')

        # Stores a Mapping from Source/Destination to Next Hop
        #  Need to store ip for each node instead of id
        # |------------------------------------------------|
        # | Source   |   Destination   |    Next Hop       |
        # |------------------------------------------------|
        # |   1      |       5         |       3           |
        # |------------------------------------------------|
        #
        self._table = dict()
        self._table_lock = Lock()

        #dict to store test data
        self._time_data = dict()

        # shared queue for broadcasting packets
        # each queue entry should be a tuple
        # containing the next hop ip and data
        # (next_hop_ip, data)
        self._packet_queue = Queue.Queue(maxsize=0)

        self._thread_bag = Set()
        for i in range(self.NUM_BROADCAST_THREADS):
             t = Thread(target=self._process_packet)
             t.setDaemon(True)
             t.start()
             self._thread_bag.add(t)

        #start test application
        t = Thread(target=self._test_application)
        t.setDaemon(True)
        t.start()

        # start server socket to listen
        t_server = Thread(target=self._node_server_socket)
        t_server.setDaemon(True)
        t_server.start()

    def _test_application(self):
        global time_data
        sync_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # test appliaction thread will mimic a real application
        # listen for packets
        # write the data
        try:
            sync_sock.bind(('', self._APP_PORT))
        except socket.error, msg:
            print 'Bind failed. Error code: ' + str(msg[0]) + ', Error message : ' + msg[1]
            return
        while 1 :
            app_data, app_addr = sync_sock.recvfrom(1024)

            t = time.time() #float
            control_bit = app_data[0]
            if control_bit == '1':

                broadcast_node_id = socket.inet_ntoa(app_data[1:5])

                destination_node_id = socket.inet_ntoa(app_data[5:9])

                msg = struct.unpack('d',app_data[9:])[0]


                logging.debug( app_addr )
                logging.debug( app_data )
                if broadcast_node_id not in time_data:
                    time_data[broadcast_node_id] = []

                time_data[broadcast_node_id].append((msg, t))
                logging.info( 'Message received... @%f: %f' % (t, msg))
            elif control_bit == '6':
                # control_bit|broadcast_node_id|destination_node_id|hop_count|source_offset|source_transmit|hop_1|hop_1_time_offset|hop_1_receive|hop_1_transmit....
                logging.debug("Diagnostic packet received")
                broadcast_node_id = socket.inet_ntoa(app_data[1:5])

                destination_node_id = socket.inet_ntoa(app_data[5:9])
                hop_count = struct.unpack('!i', app_data[9:13])[0]
                source_time_offset = struct.unpack('d', app_data[13:21])[0]
                source_transmit_time = struct.unpack('d', app_data[21:29])[0]
                logging.debug("Hop count: %d, Source time offset: %f, Source Tranmit time: %f" % (hop_count, source_time_offset, source_transmit_time))
                debug_time_data = dict()
                debug_time_data['source'] = (source_time_offset,0,source_transmit_time,0)

                for i in range(hop_count):
                    temp_node_ip = socket.inet_ntoa(app_data[29+i*28:33+i*28])
                    temp_node_time_offset = struct.unpack('d', app_data[33+i*28:41+i*28])[0]
                    temp_node_receive_time = struct.unpack('d', app_data[41+i*28:49+i*28])[0]
                    temp_node_transmit_time = struct.unpack('d', app_data[49+i*28:57+i*28])[0]
                    logging.debug("Node ip: %s, time_offset: %f, receive_time: %f, transmit_time: %f" % (temp_node_ip,temp_node_time_offset,temp_node_receive_time,temp_node_transmit_time))
                    debug_time_data[temp_node_ip]=(temp_node_time_offset,temp_node_receive_time,temp_node_transmit_time,i+1)
                debug_time_data['destination'] = (self._delta_t,t,0,1000000)

                time_data[broadcast_node_id].append(debug_time_data)

        sync_sock.close()

    def _synchronize(self):
        def sync_helper():
            sync_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # generate time offset
            # |------------ts-------------- timeserver
            #          /      \
            #       send      reply
            #       /            \
            # |----t0-----ts'-----t1-------- node
            #
            # ts' ~ ( t1 + t0 ) / 2
            # ts = ts' + delta_t -> delta_t = ts - ts'
            # delta_t ~ -( t1 + t0 ) / 2 + ts

            t0 = time.time()
            sync_sock.sendto('time', (self.TS_ADDR, self.TS_PORT))

            time_sync = sync_sock.recv(64)

            t1 = time.time()

            t_sync = struct.unpack('d', time_sync)[0]

            delta = -1 * (t1 + t0) / 2 + t_sync

            sync_sock.close()

            return delta

        delta_t_1 = sync_helper()
        delta_t_2 = 1000000.0
        while(abs(delta_t_2-delta_t_1)>0.001):
            delta_t_2 = delta_t_1
            delta_t_1 = sync_helper()
        return delta_t_1

    def _process_packet(self):
        global time_data
        # structure of packet
        # |------------------------------------------------
        # | Function     | Control Bit | Data
        # |----------------------------------------------
        # | Update Table |     0       | <xml data>
        # |-----------------------------------------------
        # | Broadcast    |     1       | <PacketNumber, BroadcastNodeID, SourceNodeID, DestinationNodeID, Data>
        # |----------------------------------------------------

        broad_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while 1:

            broad_sock.settimeout(None)
            bytes, addr, t_received = self._packet_queue.get(block=True)
            control_bit = bytes[0]
            logging.info( 'Message recieved with control bit: ' + control_bit )
            #branch on control bit
            if control_bit == '0':
                #do stuff for updatring table
                temp_bnode = self._update_table(bytes[1:])
                logging.debug( self._table )
                #add time_data entry for the broadcast node
                if temp_bnode not in time_data:
                    time_data[temp_bnode] = []

            elif control_bit == '1':
                #broadcast the data
                # need to determine if this node is the destination
                # in that case, need to get timing info
                broadcast_node_id = socket.inet_ntoa(bytes[1:5])

                destination_node_id = socket.inet_ntoa(bytes[5:9])

                msg = struct.unpack('d',bytes[9:])[0]

                #Add packet to queue
                new_p = (broadcast_node_id, destination_node_id, msg)
                logging.debug( new_p )
                dest_ip = self._table[broadcast_node_id][destination_node_id] #correct for setup
                logging.debug( "Destination ip from table:" )
                logging.debug( dest_ip )

                for dest in dest_ip:
                    if dest[0] == self._this_node_id:
                        dest_port = self._APP_PORT
                        logging.debug( "Received Message bound for this node. Forwarding to application..." )
                    else:
                        dest_port = self._PORT
                    new_msg = '1'+socket.inet_aton(broadcast_node_id)+socket.inet_aton(dest[1])+struct.pack('d',msg)
                    broad_sock.sendto(new_msg, (dest[0], dest_port))

                '''
                if destination_node_id == this_node_id:

                    t = time.time() #float
                    time_data[broadcast_node_id].append((msg, t))
                    logging.info( 'Message received... @%f: %f' % (t, msg))
                else:

                    #Add packet to queue
                    new_p = (broadcast_node_id, destination_node_id, bytes)
                    logging.debug( new_p )
                    packet_queue.put(new_p)
                '''

            elif control_bit == '2':#test
                #send debugging info
                #  right now just number of threads
                t_count = 0
                for t in self._thread_bag:
                    if t.isAlive:
                        t_count += 1

                thread_debug_msg = 'Number of threads active: ' + str(t_count)
                broad_sock.sendto(thread_debug_msg, addr)#changed this to reply with msg sent
                logging.debug( thread_debug_msg )

            elif control_bit == '3':#terminate transmission
                #incoming packet structure
                # : '3' + packed ip broadcast_node_id
                central_node_ip = '128.42.142.45'# could change
                central_node_port = 50006
                broadcast_node_id = socket.inet_ntoa(bytes[1:5])
                #delete routingtable
                goat = 3
                #process data
                #time_data[broadcast_node] = [(broad_time_float, recv_time_float), ...]
                temp_float_list = [item for sublist in time_data[broadcast_node_id] for item in sublist]
                logging.info( "Time Data List: " )
                logging.info( temp_float_list )
                time_data_string = struct.pack(str(len(temp_float_list)) + 'd', *temp_float_list)
                packed_time_offset = struct.pack("d", self._delta_t)
                #send data
                #[control_bit][broadcast node][dest node][(source_time_float, dest_time_float),..]
                # control bit = 1
                new_msg = '1' + bytes[1:5] + bytes[5:9] + packed_time_offset + time_data_string

                broad_sock.sendto(new_msg, (central_node_ip, central_node_port))

                #delete time data
                time_data[broadcast_node_id] = []


            elif control_bit == '4':
                logging.info('Exit signal received...')
                broad_sock.sendto('Ack', addr)
                sys.exit()

            elif control_bit == '5':
                #ping each node 10 times
                #calculate average RTT
                #estimate Oneway latency
                temp_node_list = [socket.inet_ntoa(bytes[1:][i:i+4]) for i in range(0, len(bytes[1:]), 4)]

                #[(node_ip, oneway latecy), ...]
                temp_latency_list = []

                for temp_node in temp_node_list:
                    logging.debug("Sending packet to: %s", temp_node)
                    temp_addr = (temp_node, self._PORT)
                    #send ten packets
                    delay = 0.0
                    broad_sock.settimeout(2)
                    i=0
                    while i < 100:#if we can converge in 100 messages
                        #do stuff and test the remaining values
                        #we want to grab a sequence of times and then wait to converge
                        # try
                        #    get 10 values
                        #    take the average
                        #    keep getting values
                        #       if the new value is greater than some threshold of error, discard
                        #       else take the average of the remaining (total / (10+i))
                        #       when successive iterations differ by less than some threshold, end
                        t0 = time.time()

                        broad_sock.sendto('2', temp_addr)
                        try:
                            broad_sock.recvfrom(64)

                        except socket.error, msg:
                            print msg
                            continue

                        t1 = time.time()
                        delay_i = ((t1 - t0) * 500)
                        if i< 10:
                            i+=1
                            delay = delay_i/i + delay * (i-1) / i
                        elif abs(delay_i - delay) < delay:#if value is twice what we have averaged so far, discard
                            i+=1
                            temp = delay
                            delay = delay_i/i + delay * (i-1) / i
                            if (temp - delay) < .03*temp:#should we divide by i?
                                valid=True
                                break
                        time.sleep(.02)

                    temp_latency_list.append((temp_node,delay))

                #broadcast latency list
                ret_val = ''
                for item in temp_latency_list:
                    temp_ip = socket.inet_aton(item[0])
                    temp_time = struct.pack('d', item[1])
                    ret_val += temp_ip + temp_time

                broad_sock.sendto(ret_val, addr)
            elif control_bit == '6':
                #used for diagnostic
                # each node will add time received and time transmitted to each packet
                # packet structure
                # control_bit|broadcast_node_id|destination_node_id|hop_count|source_offset|source_transmit|hop_1|hop_1_time_offset|hop_1_receive|hop_1_transmit....
                broadcast_node_id = socket.inet_ntoa(bytes[1:5])

                destination_node_id = socket.inet_ntoa(bytes[5:9])

                hop_count = struct.unpack('!i',bytes[9:13])[0]
                hop_count += 1
                old_chain = bytes[13:]
                t_trans = time.time()
                new_msg = struct.pack('!i', hop_count) + old_chain + socket.inet_aton(self._this_node_id) + struct.pack('d', self._delta_t) + struct.pack('d',t_received) + struct.pack('d', t_trans)
                dest_ip = self._table[broadcast_node_id][destination_node_id] #correct for setup
                logging.debug( "Destination ip from table:" )
                logging.debug( dest_ip )

                for dest in dest_ip:
                    if dest[0] == self._this_node_id:
                        dest_port = self._APP_PORT
                        logging.debug( "Received Message bound for this node. Forwarding to application..." )
                    else:
                        dest_port = self._PORT
                    temp_msg = '6'+socket.inet_aton(broadcast_node_id)+socket.inet_aton(dest[1])+new_msg
                    broad_sock.sendto(temp_msg, (dest[0], dest_port))

            elif control_bit == '7':
                #terminate dignostic tranmit
                central_node_ip = '128.42.142.45'# could change
                central_node_port = 50006
                broadcast_node_id = socket.inet_ntoa(bytes[1:5])
                #delete routingtable
                goat = 3
                #process data
                #time_data[broadcast_node] = [{'source':time, 'destination':time, node_ip:time...}, ...]
                #  where time is a tuple (time_received, time_transmit)
                temp_time_data = time_data[broadcast_node_id]
                #create xml representation
                final_time_data= et.Element('final_time_data')
                packet_number = 0
                final_time_data.attrib['broadcast_node_id']=broadcast_node_id
                final_time_data.attrib['destination_node_id']=self._this_node_id
                final_time_data.attrib['time_offset']="%f" % self._delta_t


                for item in temp_time_data:
                    packet_number+=1
                    packet_data = et.SubElement(final_time_data, 'packet_number')
                    packet_data.attrib['number'] = "%d" % packet_number

                    for key, value in item.iteritems():
                        time_element = et.SubElement(packet_data, 'link_delay')
                        time_element.attrib['ip'] = key
                        time_element.attrib['time_offset'] = "%f" % value[0]
                        time_element.attrib['receive_time'] = "%f" % value[1]
                        time_element.attrib['transmit_time'] = "%f" % value[2]
                        time_element.attrib['hop_number'] = "%d" % value[3]

                xml_time_data = et.tostring(final_time_data)
                broad_sock.sendto('3' + xml_time_data, (central_node_ip, central_node_port))

                #delete time data
                time_data[broadcast_node_id] = []

            elif control_bit == '8':#experiment with alternate delay measurement
                t_corrected = t_received + self._delta_t
                ret_msg = struct.pack('d', t_corrected)
                broad_sock.sendto(ret_msg, addr)
            elif control_bit == '9':
                #ping each node 10 times
                #calculate average RTT
                #estimate Oneway latency
                temp_node_list = [socket.inet_ntoa(bytes[1:][i:i+4]) for i in range(0, len(bytes[1:]), 4)]

                #[(node_ip, oneway latecy), ...]
                temp_latency_list = []

                for temp_node in temp_node_list:
                    logging.debug("Sending packet to: %s", temp_node)
                    temp_addr = (temp_node, self._PORT)
                    #send ten packets
                    delay = 0.0
                    broad_sock.settimeout(2)
                    i=0
                    while i < 100:#if we can converge in 100 messages
                        #do stuff and test the remaining values
                        #we want to grab a sequence of times and then wait to converge
                        # try
                        #    get 10 values
                        #    take the average
                        #    keep getting values
                        #       if the new value is greater than some threshold of error, discard
                        #       else take the average of the remaining (total / (10+i))
                        #       when successive iterations differ by less than some threshold, end
                        t0 = time.time()

                        broad_sock.sendto('8', temp_addr)
                        try:
                            _latency_data, _temp_addr = broad_sock.recvfrom(64)

                        except socket.error, msg:
                            print msg
                            continue

                        t1 = struct.unpack('d', _latency_data)[0]
                        delay_i = (t1 - (t0 + self._delta_t)) * 1000
                        if i< 10:
                            i+=1
                            delay = delay_i/i + delay * (i-1) / i
                        elif abs(delay_i - delay) < delay:#if value is twice what we have averaged so far, discard
                            i+=1
                            temp = delay
                            delay = delay_i/i + delay * (i-1) / i
                            if (temp - delay) < .03*temp:#should we divide by i?
                                valid=True
                                break
                        time.sleep(.02)

                    temp_latency_list.append((temp_node,delay))

                #broadcast latency list
                ret_val = ''
                for item in temp_latency_list:
                    temp_ip = socket.inet_aton(item[0])
                    temp_time = struct.pack('d', item[1])
                    ret_val += temp_ip + temp_time

                broad_sock.sendto(ret_val, addr)

        broad_sock.close()
        return True

    def _update_table(self, bytes):
        root = et.fromstring(bytes)

        for child in root:
            # print child.tag + child.attrib
            self._table_lock.acquire(True)
            self._table[child.attrib['broadcast_node']] = dict()
            for child2 in child:
                self._table[child.attrib['broadcast_node']][child2.attrib['incoming_destination']] = tuple()
                for child3 in child2:
                    self._table[child.attrib['broadcast_node']][child2.attrib['incoming_destination']]+=((child3.attrib['next_hop'], child3.attrib['dest']),)
            self._table_lock.release()
        logging.debug( self._table )
        return root[0].attrib['broadcast_node']

    def _node_server_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logging.info('Node ip: ' + self._this_node_id)
        logging.info('Socket Created. Initializing...')
        try:
            s.bind((self._HOST, self._PORT))
        except socket.error, msg:
            logging.error('Bind failed. Error code: ' +str(msg[0]) + ', Error message : ' + msg[1])
            sys.exit();

        print 'Socket bound on port: ' + str(self._PORT)

        #hang out and listen for stuffs
        while 1:
            data, addr = s.recvfrom(4096)
            logging.info( 'Connected with' + addr[0] + str(addr[1]))
            #process data
            #temp_tread = Thread(target=process_packet, args=(data, addr))
            #temp_tread.st()
            t_received = time.time()
            if data[0]=='4':
                sys.exit()
            self._packet_queue.put((data, addr, t_received))
