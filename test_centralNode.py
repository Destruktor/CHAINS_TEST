import unittest
from CentralNode import CentralNode
import socket
import struct
__author__ = 'no295d'


class TestCentralNode(unittest.TestCase):
    def test__init_session(self):
        self.fail()

    def test__process_packet(self):

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = '0' + struct.pack('i', 1)
        for i in range(5):
            msg += struct.pack('i', i+2)
            sock.sendto(msg, ('128.42.142.45',50006))
            data = sock.recv(64)
            print data

        self.fail()

    def test__central_node_server(self):
        self.fail()

    def test_update_node_multicast_forwarding_table(self):
        self.fail()

    def _setup_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return sock
if __name__=='__main__':
    unittest.main()
