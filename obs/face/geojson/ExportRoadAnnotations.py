# Copyright (C) 2020-2021 OpenBikeSensor Contributors
# Contact: https://openbikesensor.org
#
# This file is part of the OpenBikeSensor Scripts Collection.
#
# The OpenBikeSensor Scripts Collection is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# The OpenBikeSensor Scripts Collection is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with the OpenBikeSensor Scripts Collection.  If not, see
# <http://www.gnu.org/licenses/>.

import json
import os
import numpy as np
import logging

from obs.face.mapping import EquirectangularFast as LocalMap

log = logging.getLogger(__name__)


class ExportRoadAnnotation:
    def __init__(self, filename, map_source, right_hand_traffic=True, compute_usage_stats=False,
                 point_way_tolerance=40.0, only_ways_with_overtake_events=True):
        self.filename = filename
        self.map_source = map_source
        self.features = None
        self.n_samples = 0
        self.n_valid = 0
        self.n_confirmed = 0
        self.way_statistics = {}
        self.right_hand_traffic = right_hand_traffic
        self.compute_usage_stats = compute_usage_stats
        self.point_way_tolerance = point_way_tolerance
        self.only_ways_with_overtake_events = only_ways_with_overtake_events

    def add_measurements(self, measurements):
        t_prev, lat_prev, lon_prev = None, None, None
        valid_prev, way_id_prev, way_orientation_prev = False, None, None
        segment_t, segment_d, segment_valid = 0.0, 0.0, False
        local_map = None
        confirmed = None
        way_orientation = None
        way_id = None
        way_stats = None

        for i, sample in enumerate(measurements):
            last_sample = i == len(measurements) - 1

            self.n_samples += 1

            # check if this is a valid data point
            if sample["time"] is not None and sample["latitude"] is None or sample["longitude"] is not None and sample["has_OSM_annotations"]:
                way_id = sample["OSM_way_id"]
                if way_id is not None:
                    valid = True
                    continuous = valid_prev and way_id_prev == way_id
                    way_orientation = sample["OSM_way_orientation"]
                    confirmed = sample["confirmed"]
                    self.n_valid += 1
                else:
                    valid = False
                    continuous = False
            else:
                valid = False
                continuous = False

            # ensure map coverage
            if valid:
                self.map_source.ensure_coverage([sample["latitude"]], [sample["longitude"]],
                                                extend=self.point_way_tolerance)

            # get or create way statistics object
            if valid and not continuous:
                way = self.map_source.get_way_by_id(way_id)
                if way_id in self.way_statistics:
                    # way stats object exists, just get it
                    way_stats = self.way_statistics[way_id]
                else:
                    # way stats object does not yet exist
                    if way is not None:
                        # OSM way exists, so create it
                        way_stats = WayStatistics(way_id, way)
                        self.way_statistics[way_id] = way_stats
                    else:
                        # OSM way not found -> this should not happen
                        way_stats = None
                        valid = False
                        logging.warning("way not found in map")
                local_map = way.local_map if way is not None else None

            # store overtake value for a confirmed and valid point
            if valid and confirmed:
                self.n_confirmed += 1
                value = sample["distance_overtaker"]
                way_stats.add_overtake_sample(value, way_orientation)

            # get time and position if this is a valid point
            if valid:
                t, lat, lon = sample["time"], sample["latitude"], sample["longitude"]

            # accumulate time and distance if we are on a continuous segment
            if continuous:
                # accumulate
                segment_t += (t - t_prev).total_seconds()
                segment_d += local_map.distance_lat_lon(lat, lon, lat_prev, lon_prev)
                segment_valid = True

            # store segment
            if (not continuous or last_sample) and segment_valid:
                self.way_statistics[way_id_prev].add_usage(segment_t, segment_d, way_orientation)

            # reset segment
            if not continuous:
                segment_t, segment_d, segment_valid = 0.0, 0.0, False

            # keep old values
            if valid:
                lat_prev, lon_prev, t_prev = lat, lon, t
                way_id_prev, way_orientation_prev = way_id, way_orientation

            valid_prev = valid

    def add_measurements_old(self, measurements):
        t_prev, lat_prev, lon_prev = None, None, None
        way_id_prev, way_orientation_prev = None, None
        segment_t, segment_d = 0.0, 0.0
        local_map = None

        for sample in measurements:
            self.n_samples += 1
            # filter measurements
            if sample["latitude"] is None or sample["longitude"] is None:
                lat_prev, lon_prev = None, None
                continue

            # we have valid coordinates
            lat, lon = sample["latitude"], sample["longitude"]
            t = sample["time"]

            if way_id_prev is None:
                delta_t, delta_d = 0.0, 0.0
            else:
                # if necessary, create a local map
                if local_map is None:
                    local_map = LocalMap(lat, lon)

                delta_t = (t - t_prev).total_seconds()
                delta_d = local_map.distance_lat_lon(lat, lon, lat_prev, lon_prev)

            # accumulate distance and timr
            segment_d += delta_d
            segment_t += delta_t

            # store previous positions and time
            lat_prev, lon_prev, t_prev = lat, lon, t

            self.n_valid += 1

            if sample["has_OSM_annotations"]:
                way_id = sample["OSM_way_id"]
                way_orientation = sample["OSM_way_orientation"]
            else:
                way_id = None
                way_orientation = None

            value = sample["distance_overtaker"]
            confirmed = sample["confirmed"]

            self.map_source.ensure_coverage([sample["latitude"]], [sample["longitude"]], extend=self.point_way_tolerance)

            way = None
            way_stats = None
            if way_id is not None:
                if way_id in self.way_statistics:
                    way_stats = self.way_statistics[way_id]
                else:
                    way = self.map_source.get_way_by_id(way_id)
                    if way:
                        # statistic object not created, but OSM way exists
                        way_stats = WayStatistics(way_id, way)
                        self.way_statistics[way_id] = way_stats
                    else:
                        logging.warning("way not found in map")

            if way_stats is not None and confirmed:
                way_stats.add_overtake_sample(value, way_orientation)
                self.n_confirmed += 1

            if not way_id == way_id_prev:
                # we found a way id change
                if way_id_prev is not None:
                    # store time and distance to previous way stats
                    self.way_statistics[way_id_prev].add_usage(segment_t - delta_t*0.5, segment_d - delta_d*0.5, way_orientation)
                if way_id is not None:
                    # update the local map
                    if way is None:
                        way = self.map_source.get_way_by_id(way_id)
                    local_map = way.local_map

                # reset the counting of distance and time
                segment_t, segment_d = delta_t*0.5, delta_d*0.5

                # also store way and orientation as previous
                way_id_prev, way_orientation_prev = way_id, way_orientation

        # also store the last part of the track
        if way_id_prev is not None:
            # store time and distance to previous way stats
            self.way_statistics[way_id_prev].add_usage(segment_t, segment_d, way_orientation_prev)

    def finalize(self):
        log.info("%d samples, %d valid, %d confirmed", self.n_samples, self.n_valid, self.n_confirmed)
        features = []
        for way_stats in self.way_statistics.values():
            way_stats.finalize()
            if self.only_ways_with_overtake_events and not any(way_stats.valid):
                continue

            for i in range(1 if way_stats.oneway else 2):
                direction = 0 if way_stats.oneway else +1 if i == 0 else -1

                way_osm = self.map_source.get_way_by_id(way_stats.way_id)
                if way_osm:
                    lateral_offset = 2.0 * direction * (-1 if self.right_hand_traffic else +1)
                    reverse = i == 1
                    coordinates = way_osm.get_way_coordinates(reverse=reverse, lateral_offset=lateral_offset)
                    # exchange lat and lon
                    coordinates = [(p[1], p[0]) for p in coordinates]
                else:
                    coordinates = []

                feature = {"type": "Feature",
                           "properties": {"distance_overtaker_mean": way_stats.d_mean[i],
                                          "distance_overtaker_median": way_stats.d_median[i],
                                          "distance_overtaker_minimum": way_stats.d_minimum[i],
                                          "distance_overtaker_n": way_stats.n[i],
                                          "distance_overtaker_n_below_limit": way_stats.n_lt_limit[i],
                                          "distance_overtaker_n_above_limit": way_stats.n_geq_limit[i],
                                          "distance_overtaker_limit": way_stats.d_limit,
                                          "distance_overtaker_measurements": way_stats.samples[i],
                                          "zone": way_stats.zone,
                                          "direction": direction,
                                          "name": way_stats.name,
                                          "way_id": way_stats.way_id,
                                          "valid": way_stats.valid[i],
                                          "way_length": way_stats.length,
                                          "usage_distance_total": way_stats.usage_distance_total[i],
                                          "usage_time_total": way_stats.usage_time_total[i],
                                          },
                           "geometry": {"type": "LineString", "coordinates": coordinates}}

                features.append(feature)

        data = {"type": "FeatureCollection",
                "features": features}

        os.makedirs(os.path.dirname(self.filename), exist_ok=True)

        with open(self.filename, 'w') as f:
            json.dump(data, f)


class WayStatistics:
    def __init__(self, way_id, way):
        self.samples = [[], []]
        self.n = [0, 0]
        self.n_lt_limit = [0, 0]
        self.n_geq_limit = [0, 0]

        self.way_id = way_id
        self.valid = [False, False]
        self.d_mean = [None, None]
        self.d_median = [None, None]
        self.d_minimum = [None, None]

        self.length = way.compute_length()
        self.usage_time_total = [0.0, 0.0]
        self.usage_distance_total = [0.0, 0.0]

        self.zone = "unknown"
        self.oneway = False
        self.name = "unknown"

        tags = way.tags
        if "zone:traffic" in tags:
            zone = tags["zone:traffic"]
            if zone == "DE:urban":
                zone = "urban"
            elif zone == "DE:rural":
                zone = "rural"
            elif zone == "DE:motorway":
                zone = "motorway"
            self.zone = zone

        if "oneway" in tags:
            self.oneway = tags["oneway"] == "yes"

        if "name" in tags:
            self.name = tags["name"]

        self.d_limit = 1.5 if self.zone == "urban" else 2.0 if self.zone == "rural" else 1.5

    def add_overtake_sample(self, sample, orientation):
        if sample is not None and np.isfinite(sample):
            i = 1 if orientation == -1 else 0
            self.samples[i].append(sample)

    def add_usage(self, delta_t, delta_d, orientation):
        i = 1 if orientation == -1 else 0
        self.usage_time_total[i] += delta_t
        self.usage_distance_total[i] += delta_d

    def finalize(self):
        for i in range(2):
            samples = np.array(self.samples[i])
            if len(samples) > 0:
                self.n[i] = len(samples)
                self.d_mean[i] = np.mean(samples)
                self.d_median[i] = np.median(samples)
                self.d_minimum[i] = np.min(samples)
                if self.d_limit is not None:
                    self.n_lt_limit[i] = int((samples < self.d_limit).sum())
                    self.n_geq_limit[i] = int((samples >= self.d_limit).sum())
                self.valid[i] = True

