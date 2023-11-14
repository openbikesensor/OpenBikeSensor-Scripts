import numpy as np
import math
from obs.face.mapping import EquirectangularFast as LocalMap


class Way:
    def __init__(self, way_id, way, nodes_way):
        self.way_id = way_id

        if "tags" in way:
            self.tags = way["tags"]
        else:
            self.tags = {}

        # determine points
        lat = np.array([n["lat"] for n in nodes_way])
        lon = np.array([n["lon"] for n in nodes_way])
        self.points_lat_lon = np.stack((lat, lon), axis=1)

        # bounding box
        self.a = (min(lat), min(lon))
        self.b = (max(lat), max(lon))

        # define the local map around the center of the bounding box
        lat_0 = (self.a[0] + self.b[0]) * 0.5
        lon_0 = (self.a[1] + self.b[1]) * 0.5
        self.local_map = LocalMap(lat_0, lon_0)

        # transfer way points to local coordinate system
        x, y = self.local_map.transfer_to(lat, lon)
        self.points_xy = np.stack((x, y), axis=1)

        # direction
        dx = np.diff(x)
        dy = np.diff(y)
        self.seg_length = np.hypot(dx, dy)
        self.direction = np.arctan2(dy, dx)

        self.directionality_bicycle, self.directionality_motorized = self.get_way_directionality(way)

    @staticmethod
    def create(way_id, way, all_nodes, max_len):
        ways = {}
        # determine points
        nodes = [all_nodes[i] for i in way["nodes"]]
        lat = np.array([n["lat"] for n in nodes])
        lon = np.array([n["lon"] for n in nodes])

        # bounding box
        a = (min(lat), min(lon))
        b = (max(lat), max(lon))

        # define the local map around the center of the bounding box
        lat_0 = (a[0] + b[0]) * 0.5
        lon_0 = (a[1] + b[1]) * 0.5
        local_map = LocalMap(lat_0, lon_0)
        x, y = local_map.transfer_to(lat, lon)
        dx = np.diff(x)
        dy = np.diff(y)
        seg_length = np.hypot(dx, dy)

        slen = 0
        first = 0
        if len(dx) > 0:
            for i in range(len(seg_length)):
                slen += seg_length[i]
                if (slen > max_len and i != first):
                    id = str(way_id)+'.'+str(i)
                    ways[id] = Way(id, way, nodes[first:i+1])
                    first = i
                    slen = 0
        id = str(way_id)
        ways[id] = Way(id, way, nodes[first:])
        return ways
        

    def get_axis_aligned_bounding_box(self):
        return self.a, self.b

    def axis_aligned_bounding_boxes_overlap(self, a, b):
        return np.all(self.a < b) and np.all(a < self.b)

    def distance_of_point(self, lat_lon, direction_sample):
        # transfer lat_lon to local coordinate system
        xy = np.array(self.local_map.transfer_to(lat_lon[0], lat_lon[1]))

        # determine closest point on way
        p0 = None
        dist_x_best = math.inf
        i_best = None
        x_projected_best = None
        for i, p in enumerate(self.points_xy):
            if p0 is not None:
                d = p - p0
                dist, x_projected = self.point_line_distance(p0, d, xy)
                if dist < dist_x_best:
                    dist_x_best = dist
                    x_projected_best = x_projected
                    i_best = i
            p0 = p

        # transfer projected point to lat_lon
        lat_lon_projected_best = self.local_map.transfer_from(x_projected_best[0], x_projected_best[1])

        # also check deviation from way direction
        direction_best = self.direction[i_best - 1]
        if self.directionality_bicycle == +1:
            # way is direction-bound for bicyclist, and follows the way direction
            dist_direction_best = self.distance_periodic(direction_sample, direction_best)
            way_orientation = +1
        elif self.directionality_bicycle == -1:
            # way is direction-bound for bicyclist, and follows the reverse way direction
            dist_direction_best = self.distance_periodic(direction_sample + math.pi, direction_best)
            way_orientation = -1
        else:
            # way is not direction-bound for bicyclist, so both directions are OK
            d0 = self.distance_periodic(direction_sample, direction_best)
            d180 = self.distance_periodic(direction_sample + math.pi, direction_best)
            if d0 <= d180:
                # we go along the way direction
                way_orientation = +1
                dist_direction_best = d0
            else:
                # we go along the reverse way direction
                way_orientation = -1
                dist_direction_best = d180

        return dist_x_best, lat_lon_projected_best, dist_direction_best, way_orientation

    def get_way_coordinates(self, reverse=False, lateral_offset=0):
        if lateral_offset == 0:
            coordinates = list(reversed(self.points_lat_lon)) if reverse else self.points_lat_lon
        else:
            c = self.points_xy

            # compute normals, pointing to the left
            n = []
            for i in range(len(c) - 1):
                n_i = c[i + 1] - c[i]
                n_i = n_i / np.linalg.norm(n_i)
                n_i = np.array([-n_i[1], +n_i[0]])
                n.append(n_i)

            # move points
            coordinates = []
            for i in range(len(c)):
                # create an average normal for each node
                n_prev = n[max(0, i - 1)]
                n_next = n[min(len(n) - 1, i)]
                n_i = 0.5 * (n_prev + n_next)
                # make sure it is normalized
                n_i = n_i / np.linalg.norm(n_i)
                # then move the point
                c_i = c[i] + n_i * lateral_offset
                c_i = self.local_map.transfer_from(c_i[0], c_i[1])
                coordinates.append([c_i[0], c_i[1]])

        return coordinates

    @staticmethod
    def point_line_distance(p0, d, x):
        c = x - p0

        dd = np.inner(d, d)
        if dd > 0:
            # line has non-zero length
            # optimal lambda
            lambda_star = np.inner(d, c) / dd
            # project (clip) to [0,1]
            # lambda_star = np.clip(lambda_star, a_min=0.0, a_max=1.0)
            lambda_star = max(0.0, min(1.0, lambda_star))
            # compute  nearest point on line
            x_star = p0 + lambda_star * d
        else:
            # line has zero length
            x_star = p0

        # compute actual distance to line
        d_star = np.linalg.norm(x_star - x)

        return d_star, x_star

    @staticmethod
    def distance_periodic(a, b, p=2 * math.pi):
        p2 = 0.5*p
        d = a - b
        return abs((d + p2) % p - p2)

    @staticmethod
    def get_way_directionality(way):
        if "tags" not in way:
            return 0, 0
        tags = way["tags"]

        d_motorized = 0

        # roundabouts imply a one-way street
        if "junction" in tags and tags["junction"] == "roundabout":
            d_motorized = 1

        # derive motorized directionality
        if "oneway" in tags:
            v = tags["oneway"]
            if v in ["yes", "true", "1"]:
                d_motorized = +1
            elif v in ["no", "false", "0"]:
                d_motorized = 0
            elif v in ["-1", "reverse"]:
                d_motorized = -1

        # derive bicycle directionality
        d_bicycle = d_motorized
        if "oneway:bicycle" in tags:
            v = tags["oneway:bicycle"]
            if v in ["yes", "true", "1"]:
                d_bicycle = +1
            elif v in ["no", "false", "0"]:
                d_bicycle = 0
            elif v in ["-1", "reverse"]:
                d_bicycle = -1

        return d_bicycle, d_motorized
