import unittest
from CentralNode import CentralNode
import socket
__author__ = 'no295d'


class TestCentralNode(unittest.TestCase):
    def test__init_session(self):
        self.fail()

    def test__process_packet(self):
        cn = CentralNode()

        sock = self._setup_socket()

        sock.sendto('0', ('localhost',CentralNode.PORT))

        data = sock.recv(1024)


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
