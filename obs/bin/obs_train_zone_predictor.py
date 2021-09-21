#!/usr/bin/python

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

import argparse
import logging
import pickle
import time
import coloredlogs
import requests
import numpy as np
import os
import dill

from obs.face.osm.TileSource import TileSource
from obs.face.annotate.ZonePredictor import ZonePredictor


log = logging.getLogger(__name__)


def get_region_geometry(region_name, admin_level=None, user_agent='OpenBikeSensor-FACE'):
    overpass_url = "http://overpass-api.de/api/interpreter"

    query_template = """
        [out:json];
        relation["boundary"="administrative"]["admin_level"="{admin_level}"]["name"="{region_name}"];
        out geom;"""

    if not admin_level:
        admin_level = "*"

    parameters = {"admin_level": admin_level, "region_name": region_name}

    query = query_template.format(**parameters)

    success = False
    for try_count in range(3):
        # send query and receive answer
        response = requests.get(overpass_url,
                                params={'data': query},
                                headers={'User-Agent': user_agent})

        response.close()

        if response.status_code == 200:
            success = True
            break

        logging.warning('could not retrieve region, server returned %s (%d)', response.reason, response.status_code)
        time.sleep((try_count + 1) * 3)

    if success:
        # decode to JSON
        response_json = response.json()
    else:
        response_json = None

    return response_json


def main():
    parser = argparse.ArgumentParser(description='trains a classificator for predicting the traffic zone of an OSM way')

    parser.add_argument('-v', '--verbose', action='store_true', help='be verbose')

    args = parser.parse_args()

    coloredlogs.install(level=logging.DEBUG if args.verbose else logging.INFO,
                        fmt="%(asctime)s %(name)s %(levelname)s %(message)s")

    country_name = "Deutschland"
    tile_zoom = 10
    n_samples = 10000

    tiles = get_tiles_coordinates_for_region(country_name, tile_zoom)
    #with open('tiles_Deutschland.pickle', 'rb') as f:
    #   tiles = pickle.load(f)

    log.info("identified %d tiles for country %s", len(tiles), country_name)

    # ways = get_ways_in_country("Stuttgart", admin_level=6, user_agent='OpenBikeSensor-FACE')

    # create samples
    samples = create_way_samples(tiles, n_samples, country_name)

    # train a support vector machine
    p = ZonePredictor()

    p.train(samples)

    filename = os.path.join(os.path.dirname(__file__), "..", "data", "face_zone_predictor", "Germany.test.pickle")

    p.store(filename)

    q = ZonePredictor("Germany.test")

    q.predict(samples[0])
    pass


def get_ways_in_country(country_name, admin_level=2, user_agent='OpenBikeSensor-FACE', cache_dir='./cache'):
    filename_cache = os.path.join(cache_dir, 'obs_train_predictor', 'ways_with_zone_tag',
                                  "{}-{}".format(admin_level, country_name), 'data.pickle')

    ways = {}
    request_ways = True
    if os.path.isfile(filename_cache):
        logging.debug("loading zone-tagged ways cached in %s", filename_cache)
        request_ways = False
        try:
            with open(filename_cache, 'rb') as infile:
                ways = pickle.load(infile)
        except IOError as e:
            logging.debug("loading tile %s failed", filename_cache)
            request_ways = True

    if request_ways:
        overpass_url = "http://overpass-api.de/api/interpreter"

        query_template = """
            [out:json];
            area["boundary"="administrative"]["admin_level"="{admin_level}"]["name"="{country_name}"];
            (way["highway"~"trunk|primary|secondary|tertiary|unclassified|residential|trunk_link|primary_link|secondary_link|tertiary_link|living_street|service|track|road"]["zone:traffic"](area););
            out body;"""

        parameters = {"country_name": country_name, "admin_level": admin_level}

        query = query_template.format(**parameters)

        data = None
        for try_count in range(3):
            # send query and receive answer
            response = requests.get(overpass_url,
                                    params={'data': query},
                                    headers={'User-Agent': user_agent})

            if response.status_code == 200:
                # decode to JSON
                data = response.json()
                break

            logging.warning('could not retrieve ways, server returned %s (%d)', response.reason, response.status_code)
            time.sleep((try_count + 1) * 3)

        if data:
            for e in data["elements"]:
                if "type" in e and e["type"] == "way" and "id" in e:
                    ways[e["id"]] = e

            os.makedirs(os.path.dirname(filename_cache), exist_ok=True)
            with open(filename_cache, 'wb') as outfile:
                pickle.dump(ways, outfile)
    return ways


def get_tiles_coordinates_for_region(country_name, tile_zoom):
    g = get_region_geometry(country_name, admin_level=2)

    lat_range = [g["elements"][0]["bounds"]["minlat"], g["elements"][0]["bounds"]["maxlat"]]
    lon_range = [g["elements"][0]["bounds"]["minlon"], g["elements"][0]["bounds"]["maxlon"]]

    tile_source = TileSource()

    tiles = tile_source.get_required_tiles_bounding_box(lat_range, lon_range, tile_zoom)

    return tiles


def create_way_samples(tiles, n_max_samples, country_name, n_max_samples_per_tile=100, seed=1234567890):
    rng = np.random.default_rng(seed)
    tile_source = TileSource(use_overpass_state=True)

    n_tiles = len(tiles)
    ix_tiles = rng.permutation(n_tiles)

    sample_ways = []

    for i in ix_tiles:
        if len(sample_ways) >= n_max_samples:
            break

        tile = tiles[i]
        nodes, ways, relations = tile_source.get_tile(tile[0], tile[1], tile[2],
                                                      filter_id="in_country_with_zone_traffic",
                                                      country_name=country_name)
        # convert ways dict to ways
        ways = list(ways.values())

        # define tile indices in a random order
        ix_ways = rng.permutation(len(ways)).tolist()

        n_samples_tile = min([n_max_samples - len(sample_ways), n_max_samples_per_tile, len(ways)])

        sample_ways = sample_ways + [ways[ix] for ix in ix_ways[:n_samples_tile]]

        log.info("tile (%d, %d, %d): from %d ways retrieved %d samples, total number of samples is %d",
                 tile[0], tile[1], tile[2], len(ways), n_samples_tile, len(sample_ways))

    return sample_ways


if __name__ == "__main__":
    main()
