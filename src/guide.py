"""
Guide module.

Compute the shortest route between two points in the same city
and display the rute in a map.
"""

import os
from typing import NewType, Optional, Any, Tuple, Union, Dict, List

import yaml
import osmnx as ox
import networkx as nx
import staticmap as sm
from haversine import haversine

from src.graph import Graph


# Define new variable types (aliases) to make the code easier to read
RouteLeg = NewType(
    name='RouteLeg',
    tp=Dict[str, Union[float, Tuple[float, float], str]]
)  # dictionary that contains the information describing a leg of the route
Coordinates = NewType(name='Coordinates', tp=Tuple[float, float])  # (lat, lon)
OSMid = int  # OpenStreetMap ID


class Guide:
    """
    Guide Class. A class for computing the shortest route between two points
    in the same city and displaying the route on a map.
    """

    # Directory where the icons (part of the route) are stored
    route_images_dir = '/'.join(
        os.path.abspath(__file__).split('/')[:-2]
    ) + '/route_images'

    # Directory containing the icons to display on the map
    icons_dir = '/'.join(
        os.path.abspath(__file__).split('/')[:-2]
    ) + '/icons'

    def __init__(self, place: str, walk_or_drive: str = 'drive') -> None:
        """
        Initialize a Guide instance.

        :param place: '<city>, <country>' format. Query to get the graph.
        :param walk_or_drive: network type. 'walk' or 'drive'. For the graph.
        :return: None
        """

        self.graph = Graph(place=place, network_type=walk_or_drive)
        self.config = self._get_config()

        # Select icon (person or car) depending on the network type
        if walk_or_drive == 'walk':
            self.icon_filename = self.config['person_icon_filename']
        else:  # walk_or_drive == 'drive'
            self.icon_filename = self.config['car_icon_filename']

    @staticmethod
    def _get_config() -> Dict[str, Any]:
        """
        Read the configuration file and return it as a python dictionary.
        The configuration file is named 'config/config.yml'

        :return: configuration dictionary
        """

        this_file_path = os.path.abspath(__file__)
        this_project_dir_path = '/'.join(this_file_path.split('/')[:-2])

        config_path = this_project_dir_path + '/config/config.yml'

        with open(config_path, 'r') as yml_file:
            config = yaml.safe_load(yml_file)[0]['config']
        return config

    def get_directions(
            self,
            src_coords: Coordinates,
            dst_coords: Coordinates
    ) -> List[RouteLeg]:
        """
        Compute the directions for the shortest route between source and
        destination coordinates.

        :param src_coords: (latitude, longitude) source coordinates (first)
        :param dst_coords: (latitude, longitude) destination coordinates (last)
        :return: Sequence of steps and guides (legs) that form a route
        """

        # src_coords and dst_coords may not be nodes of the graph. But in order
        # to operate with the graph, we need to use its nodes.
        # First of all, let's find the nearest nodes to the points src_coords
        # and dst_coords.
        src_node = self._get_nearest_node(coords=src_coords)
        dst_node = self._get_nearest_node(coords=dst_coords)
        # NOTE that a Node is represented by its OpenStreetMap (OSM) ID [int]

        # Compute the shortest path between src_node and dst_node in the graph
        route = nx.shortest_path(
            G=self.graph.graph,  # A NetworkX Graph instance
            source=src_node,  # Starting node for path (source)
            target=dst_node  # Ending node for path (destination)
        )
        # NOTE that the actual src and dst points (coordinates) are not
        # included in the route yet because they are not nodes of the graph

        # Now, insert the src_coords and the dst_coords at the beginning and
        # the end of the route, respectively. Now. the route is complete.
        route.insert(0, src_coords)
        route.append(dst_coords)
        # NOTE that the first and last elements are coordinate points, whereas
        # the intermediate elements are OMS IDs (nodes of the graph)
        route.append(None)  # indicator of the end of the route

        # Define the directions: instructions to go grom the src to the dst
        # Compute the legs of the route, and add info like street name or angle
        directions = []
        for i in range(len(route)-2):
            next_leg = self._compute_leg_of_the_route(
                src=route[i], mid=route[i+1], dst=route[i+2]
            )
            directions.append(next_leg)

        # Post-processing step: when the destination is found between the last
        # node and the penultimate node, we can skip the last node and go
        # straight from the penultimate node to the destination (dst_coords)
        if len(directions) >= 3:
            # :source + at least two nodes + destination => at least 3 legs
            # The penultimate leg references the last two nodes and the
            # destination point.
            penult_leg = directions[-2]
            # Compute distances between the penutlimate and last nodes with
            # respect of the destination point
            penult_dist = haversine(penult_leg['src'], penult_leg['dst'])
            last_dist = haversine(penult_leg['mid'], penult_leg['dst'])
            # If the penultimate node is closer to the destination,
            if penult_dist > last_dist:
                # The penultimate leg will become the last leg, and will go
                # from the penultimate node to the destination point (skipping
                # the last node)
                directions[-2]['mid'] = directions[-2]['dst']
                directions[-2]['dst'] = None
                directions[-2]['length'] = haversine(
                    directions[-2]['src'], directions[-2]['mid'], unit='m'
                )
                directions.pop()  # the last leg is skipped, remove it.

        return directions

    def _get_nearest_node(self, coords: Coordinates) -> OSMid:
        """
        Given a pair of coordinates (latitude, longitude), find the nearest
        node in the graph attribute. Return the OpenStreetMap ID of that node.

        METHOD: instead of looking for the nearest node directly, look for the
        nearest edge. Then, find the nearest of the two extreme node of that
        edge. WHY? Because the priority is to go from the source point (coords)
        to the closest street (edge), not to the closes corner (node)

        Haversine (or great circle) distance:
        It's the angular distance between two points on the surface of a sphere

        :param coords: (latitude, longitude) geographic coordinates
        :return: OpenStreetMap ID of the nearest node in the graph attribute.
        """

        nearest_edge = ox.distance.nearest_edges(
            G=self.graph.graph, X=coords[1], Y=coords[0]
        )
        u, v, _ = nearest_edge
        point_u = (self.graph.nodes[u]['y'], self.graph.nodes[u]['x'])
        point_v = (self.graph.nodes[v]['y'], self.graph.nodes[v]['x'])

        du, dv = haversine(coords, point_u), haversine(coords, point_v)
        return u if du == min(du, dv) else v

    def _get_coordinates(self, node: OSMid) -> Coordinates:
        """
        Given a node represented by an OpenStreetMap ID (OMD id), use the graph
        information to compute the coordinates (latitude, longitude)

        :param node: OpenStreetMap ID
        :return: (latitude, longitude) geographic coordinates
        """

        latitude = self.graph.nodes[node]['y']
        longitude = self.graph.nodes[node]['x']
        return latitude, longitude

    def _compute_leg_of_the_route(
            self,
            src: Union[RouteLeg, OSMid],
            mid: Union[RouteLeg, OSMid],
            dst: Union[RouteLeg, OSMid],
    ) -> RouteLeg:
        """
        Compute information about a leg of the route.

        :param src: Source coordinates or OpenStreetMap ID
        :param mid: Intermediate coordinates or OpenStreetMap ID
        :param dst: Destination coordinates or OpenStreetMap ID
        :return: Dictionary containing information about the leg
        """

        # Values by default (will be changed within this function)
        leg = {
            'src': src,
            'current_name': None,
            'length': None,
            'mid': mid,
            'next_name': None,
            'dst': dst,
            'angle': None
        }

        if dst is None:  # Last Step: from the last node to the dst point
            # no angle, no street name. Just turn every OSM id to coordinates.
            if isinstance(src, OSMid):
                leg['src'] = self._get_coordinates(node=src)
            return leg

        if isinstance(src, OSMid):  # All but the First Step.
            # Get the street name and distance (length)
            leg['src'] = self._get_coordinates(node=src)
            leg['current_name'] = self.graph[src][mid][0].get('name', None)
            leg['length'] = self.graph[src][mid][0].get('length', None)

        # MID will be always a node of the graph
        leg['mid'] = self._get_coordinates(node=mid)

        if isinstance(dst, OSMid):  # All but the Penultimate Step
            leg['dst'] = self._get_coordinates(node=dst)
            leg['next_name'] = self.graph[mid][dst][0].get('name', None)

        # If the angle can be computed, do it
        if isinstance(src, OSMid) and isinstance(dst, OSMid):
            leg['angle'] = self._compute_angle(
                src_node=src, mid_node=mid, dst_node=dst
            )

        return leg

    def _compute_angle(
            self,
            src_node: OSMid,
            mid_node: OSMid,
            dst_node: OSMid
    ) -> float:
        """
        Compute the angle between three nodes on the route.
        Returns the angle between the lines (src,mid) and (mid,dst)

        :param src_node: Source node (OpenStreetMap ID)
        :param mid_node: Intermediate node (OpenStreetMap ID)
        :param dst_node: Destination node (OpenStreetMap ID)
        :return: Angle between the three nodes
        """

        src_coords = self._get_coordinates(node=src_node)
        mid_coords = self._get_coordinates(node=mid_node)
        dst_coords = self._get_coordinates(node=dst_node)

        angle1 = ox.bearing.calculate_bearing(*src_coords, *mid_coords)
        angle2 = ox.bearing.calculate_bearing(*mid_coords, *dst_coords)
        angle = angle2 - angle1

        if abs(angle) < 180:
            return angle
        return angle + 360 if angle < 0 else angle - 360

    def plot_directions(
            self,
            directions: List[RouteLeg],
            current_leg: int,
            size: Tuple[int, int] = (400, 400),
            file_name: Optional[str] = None
    ) -> None:
        """
        Plot the directions on a map.

        :param directions: List of route legs
        :param current_leg: Index of the current leg being plotted
        :param size: Size of the map (width, height). Default (400, 400)
        :param file_name: Name of the file to save the map
        :return: None
        """

        map_ = sm.StaticMap(*size)
        # Display the part of the route that is already done
        for leg_idx, leg in enumerate(directions):
            if leg_idx < current_leg:
                line_color_ = self.config['done_route_color']
            else:
                line_color_ = self.config['remaining_route_color']

            # Swaps the coordinates because StaticMap requires so.
            _src_coords = leg['src'][1], leg['src'][0]
            _dst_coords = leg['mid'][1], leg['mid'][0]
            line_ = sm.Line(
                coords=(_src_coords, _dst_coords),
                color=line_color_,
                width=self.config['line_width'],
            )
            map_.add_line(line_)
            circle_marker_ = sm.CircleMarker(
                coord=_src_coords,
                color=self.config['intermediate_points_color'],
                width=self.config['intermediate_circles_radius']
            )
            map_.add_marker(circle_marker_)

        # Add initial and last markers (circles)
        src_coords = directions[0]['src'][1], directions[0]['src'][0]
        src_circle_marker = sm.CircleMarker(
            coord=src_coords,
            color=self.config['source_point_color'],
            width=self.config['source_circle_radius']
        )
        map_.add_marker(src_circle_marker)
        dst_coords = directions[-1]['mid'][1], directions[-1]['mid'][0]
        dst_circle_marker = sm.CircleMarker(
            coord=dst_coords,
            color=self.config['destination_point_color'],
            width=self.config['destination_circle_radius']
        )
        map_.add_marker(dst_circle_marker)

        # Add the person or car icon in the current coordinates
        if current_leg < len(directions):
            current_coords = (
                directions[current_leg]['src'][1],
                directions[current_leg]['src'][0]
            )
        else:  # current_leg == len(directions)
            current_coords = (
                directions[current_leg-1]['mid'][1],
                directions[current_leg-1]['mid'][0]
            )
        current_icon = sm.IconMarker(
            coord=current_coords,
            file_path=self.icons_dir + '/' + self.icon_filename,
            offset_x=10,
            offset_y=20
        )
        map_.add_marker(current_icon)

        # Add the destination icon in the destination coordinates
        destination_icon = sm.IconMarker(
            coord=dst_coords,
            file_path=(
                self.icons_dir + '/' + self.config['destination_icon_filename']
            ),
            offset_x=10,
            offset_y=30
        )
        map_.add_marker(destination_icon)

        # Render and save the image
        image = map_.render()
        if file_name is not None:
            image.save(self.route_images_dir + '/' + file_name)


if __name__ == '__main__':
    from pprint import pprint

    place_ = "Barcelona, Spain"
    walk_or_drive_ = 'drive'

    src_coords_ = (41.409560, 2.183529)  # Barcelona, C/ de Mallorca, 549-535
    dst_coords_ = (41.408366, 2.175050)  # Barcelona, C/ de Còrsega, 611-599

    guide_ = Guide(place=place_, walk_or_drive=walk_or_drive_)

    directions_ = guide_.get_directions(
        src_coords=src_coords_, dst_coords=dst_coords_
    )
    for leg_idx_ in range(len(directions_)+1):
        guide_.plot_directions(
            directions=directions_,
            current_leg=leg_idx_,
            file_name=f'demo_{leg_idx_}.png'
        )

    pprint(directions_)
