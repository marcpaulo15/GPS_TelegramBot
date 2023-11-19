"""
Graph Module. This module defines a Graph class for working with street network
graphs using the osmnx library.
"""

import os
import pickle
from typing import Any

import osmnx as ox


class Graph:
    """
    Graph Class. The Graph class represents a street network graph for a
    specific location and network type.

    Class Attributes:
        - saved_graphs_dir (str): Directory path for saving and loading graphs.

    Instance Attributes:
        - place: string in '<city>, <country>' format which represents a city.
        - network_type: type of street network: 'walk' or 'drive'
        - graph: NetworkX Graph instance from osmnx [main attribute]
        - pkl_filepath: path of the file where the graph is saved / loaded from
        - city: name of the city (extracted from the given place)
        - country: name of the country (extracted from the given place)

    Private Methods:
        - _download_graph: Download and create a graph for a specific place.
        - _save_graph: Save the graph attribute in a pickle file.
        - _load_graph: Load the graph attribute from a pickle file.
    """

    saved_graphs_dir = '/'.join(
        os.path.abspath(__file__).split('/')[:-2]
    ) + '/saved_graphs'

    def __init__(self, place: str, network_type: str) -> None:
        """
        Initialize a Graph instance.

        :param place: '<city>, <country>'. Place whose graph is downloaded.
        :param network_type: 'walk' or 'drive' for different graph edges.
        :return: None
        """

        # Sanity check of input parameters
        if network_type not in ('walk', 'drive'):
            raise ValueError(
                "network_type must be one of ('walk', 'drive'), "
                f"but '{network_type}' was found instead"
            )
        if len(place.split(',')) != 2:
            raise ValueError(
                "place does not follow the format '<city>, <country>'"
            )

        # place: query to geocode to get place boundary polygons
        self.place = place  # '<city>, <country>' format
        self.network_type = network_type  # type of street network

        # File where the graph will be saved or loaded from
        self.pkl_filename = (
                place.lower().replace(' ', '_').replace(',', '_') +
                '_' + network_type + '.pkl'
        )
        self.pkl_filepath = self.saved_graphs_dir + '/' + self.pkl_filename
        self.city = self.place.split(',')[0].split()
        self.country = self.place.split(',')[1].split()

        self.graph = None
        try:
            # try to load a saved graph for the given place and network type
            self._load_graph()
        except FileNotFoundError:  # if pkl_filepath does not exist:
            # download and save the graph, so it will be loaded the next time
            self._download_graph()
            self._save_graph()

    def _download_graph(self) -> None:
        """
        Download and create a graph within the boundaries of the given place.
        The place (query) must be geocodable and OSM must have polygon
        boundaries for the geocode result (osmnx library).

        :raise ValueError: if network_type is neither 'walk' nor 'drive'
        :raise TypeError: if the given place (query) is not geocodable
        :return: None. Updates the graph attribute
        """

        # Download and create a graph within the boundaries of the given place
        graph = ox.graph_from_place(
            query=self.place,
            network_type=self.network_type,
            simplify=True  # if True, simplify graph topology
        )

        # Simplify the graph: remove unnecessary information (like 'geometry')
        # and remove multi-name streets
        for node1, info1 in graph.nodes.items():
            for node2, info2 in graph.adj[node1].items():
                edge = info2[0]
                # Remove 'geometry' (unnecessary) to free space in memory
                if 'geometry' in edge:
                    del edge['geometry']
                # Deal with multi-name streets:
                if 'name' in edge:
                    if isinstance(edge['name'], list):
                        # If street has several names, select the first one
                        edge['name'] = edge['name'][0]
        self.graph = graph

    def __len__(self) -> int:
        return len(self.graph)

    def __getitem__(self, item: Any) -> Any:
        """
        Basically used for accessing list items.
        Index the 'graph' attribute values.

        :param item: item to get
        :return: item index of 'graph' attribute
        """
        return self.graph[item]

    def __getattr__(self, name: str) -> Any:
        """
        If the attribute <name> is not found in the class instance,
        try to access it from the 'graph' attribute

        Code Example:
            g = Graph(...)
            g.nodes  # gets g.graph.nodes because instance has no attr 'nodes'

        :param name: attribute name
        :raise AttributeError: if 'graph' attribute has no attribute <name>
        :return: <name> attribute value if 'graph' has <name> attribute
        """

        # If the attribute is not found in the instance,
        # try to access it from the 'graph' attribute
        if hasattr(self.graph, name):
            return getattr(self.graph, name)
        else:
            # If the attribute is not found in both the instance and the graph,
            # raise an AttributeError
            raise AttributeError(f"'Graph' object has no attribute '{name}'")

    def _save_graph(self) -> None:
        """
        Save the graph attribute in the pkl_filepath location.
        Overwrite the pkl_filepath content if it already exists.

        :raise AttributeError: if graph attribute is not defined
        :return: None
        """

        if self.graph is None:
            raise AttributeError('graph attribute is not defined')

        with open(self.pkl_filepath, 'wb+') as pkl_file:
            pickle.dump(obj=self.graph, file=pkl_file)
        pkl_file.close()

    def _load_graph(self) -> None:
        """
        Load the graph attribute from the pkl_filepath location.

        :raise FileNotFoundError: if pkl_filepath does not exist
        :return: None. Updates the 'graph' attribute
        """

        with open(self.pkl_filepath, 'rb') as pkl_file:
            graph = pickle.load(file=pkl_file)
        pkl_file.close()
        self.graph = graph


if __name__ == '__main__':
    # DEMO:

    place_ = 'Barcelona, Spain'
    network_type_ = 'drive'

    graph_ = Graph(place=place_, network_type=network_type_)
    print('ok')
