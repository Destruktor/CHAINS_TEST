#!/usr/bin/python

import xmlrpclib
import random
import socket
import xml.etree.cElementTree as et

__author__ = 'no295d'


class OverlayConfigError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Node(object):
    _valid_ip_regex = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
    _valid_hostname_regex = "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$"

    def __init__(self, url):
        self._url = url
        self._active = False


class NodeManager(object):
    _api_server = xmlrpclib.ServerProxy('https://www.planet-lab.org/PLCAPI/', allow_none=True)
    _auth = {'AuthMethod': 'password', 'Username': 'nicklausrhodes@gmail.com', 'AuthString': '3pestUC6'}

    def __init__(self):
        self._authorized = self._api_server.AuthCheck(self._auth)
        self._populate_available_nodes()

    def _populate_available_nodes(self):
        node_ids = self._api_server.GetSlices(self._auth, ["citadel_nrhodes"], ['node_ids'])[0]['node_ids']
        node_hostnames = [node['hostname'] for node in
                          self._api_server.GetNodes(self._auth, node_ids, ['hostname', 'boot_state']) if
                          (node['boot_state'] == 'boot')]
        self._available_nodes = set([Node(x) for x in node_hostnames])

    def get_experiment_nodes(self, num_source_nodes, num_overlay_nodes, randomized=False):
        experiment_nodes = {}
        if randomized:
            experiment_nodes['overlay_nodes'] = random.sample(self._available_nodes, num_overlay_nodes)
            experiment_nodes['source_nodes'] = random.sample(experiment_nodes['overlay_nodes'], num_source_nodes)
        else:
            experiment_nodes['overlay_nodes'] = self._available_nodes[:num_overlay_nodes]
            experiment_nodes['source_nodes'] = experiment_nodes['overlay_nodes'][:num_source_nodes]
        return experiment_nodes


class Experiment(object):
    _session_inc = 0

    def __init__(self, num_source_nodes, num_overlay_nodes):
        if not isinstance(num_source_nodes, int):
            raise ValueError
        if not isinstance(num_overlay_nodes, int):
            raise ValueError
        if not self._validate_overlay_conf(num_source_nodes, num_overlay_nodes):
            raise OverlayConfigError("Overlay Configuration is not valid!")
        node_manager = NodeManager()
        self._experiment_nodes = node_manager.get_experiment_nodes(num_source_nodes, num_overlay_nodes)
        Experiment._session_inc += 1
        self._session_id = Experiment._session_inc

    def _validate_overlay_conf(self, num_source_nodes, num_overlay_nodes):
        if num_source_nodes > num_overlay_nodes:
            return False
        return True

    def generate_latency_graph(self):
        """call build the latency graph file
        returns file name"""
        pass

    def generate_node_tables(self):
        """builds the MFTs and sends to each destination"""
        pass

    def start_multicast_session(self):
        """signals each node to begin transmiting"""
        pass

    def stop_multicast_session(self):
        """signals each node to stop transmission"""
        pass

    def get_session_data(self):
        """get the session data from Central Node"""
        pass

