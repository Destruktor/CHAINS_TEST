import unittest
import socket
import xml.etree.cElementTree as et

__author__ = 'no295d'


class TestNodeServer(unittest.TestCase):
    def test__test_application(self):
        self.fail()

    def test__synchronize(self):
        self.fail()

    def test__process_packet(self):
        table_as_xml = self.build_mft()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg='0'+table_as_xml

        sock.sendto(msg, ('128.42.142.45',50007))
        data = sock.recv(64)
        print data

    def test__update_table(self):
        self.fail()

    def test__node_server_socket(self):
        self.fail()

    def build_mft(self):
        mft = [(2, 2), (3, 5), (5, 3)]
        table = et.Element('table')
        source_node = et.SubElement(table, 'source_node')
        source_node.attrib['broadcast_node'] = 1
        for dest, next_hop in mft:
            temp_node = et.SubElement(source_node, "destination_node")
            temp_node.attrib['next_hop'] = next_hop
            temp_node.text = dest

        xml_table = et.tostring(table)
        return xml_table

if __name__=='__main__':
    unittest.main()