# src/twin/graph_builder.py

import sumolib
import networkx as nx


class GraphBuilder:
    def __init__(self, net_file):
        self.net_file = net_file

    def build(self):
        net = sumolib.net.readNet(self.net_file)
        G = nx.DiGraph()

        for edge in net.getEdges():
            # bỏ internal edges
            if edge.getID().startswith(":"):
                continue

            from_node = edge.getFromNode().getID()
            to_node = edge.getToNode().getID()

            G.add_edge(
                from_node,
                to_node,
                id=edge.getID(),
                length=edge.getLength(),
                speed=edge.getSpeed(),
                density=0,
                queue=0,
                flow=0
            )

        return G