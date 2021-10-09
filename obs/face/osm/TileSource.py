import datetime

import requests
import numpy as np
import logging
import math
import os
import pickle
import time

import re

from obs.face.mapping.LocalMap import EquirectangularFast as LocalMap


class TileSource:
    def __init__(self, cache_dir='./cache', use_cache=True, max_tries=3, use_overpass_state=False):
        self.overpass_url = "http://overpass-api.de/api/interpreter"
        self.overpass_status_url = "http://overpass-api.de/api/status"

        self.use_overpass_state = use_overpass_state

        self.user_agent = 'OpenBikeSensor-FACE'

        self.query_template = dict()

        self.cache_dir = cache_dir
        self.use_cache = use_cache

        self.max_tries = max_tries
        # [out:json]
        # [{{bbox}}];
        # (way["highway"~"primary|secondary"];>;);
        # out body;

        self.query_template["default"] = """
        [out:json];
        (way({bbox[0]:},{bbox[1]:},{bbox[2]:},{bbox[3]:})["highway"~"trunk|primary|secondary|tertiary|unclassified|residential|trunk_link|primary_link|secondary_link|tertiary_link|living_street|service|track|road"];>;);
        out body;"""

        self.query_template["in_country_with_zone_traffic"] = """
        [out:json];
        area["boundary"="administrative"]["admin_level"="2"]["name"="{country_name}"];
        (way["highway"~"trunk|primary|secondary|tertiary|unclassified|residential|trunk_link|primary_link|secondary_link|tertiary_link|living_street|service|track|road"]["zone:traffic"]({bbox[0]:},{bbox[1]:},{bbox[2]:},{bbox[3]:})(area);>;);
        out body;"""

    def get_tile(self, zoom, x_tile, y_tile, filter_id="default", country_name=None):
        logging.debug("tile requested: zoom=%d, x=%d, y=%d, filter_id=%s", zoom, x_tile, y_tile, filter_id)

        # try to read from cache
        if country_name:
            filename_cache = os.path.join(self.cache_dir, 'TileSource', filter_id, country_name, str(zoom),
                                          str(x_tile), str(y_tile), 'tile.pickle')
        else:
            filename_cache = os.path.join(self.cache_dir, 'TileSource', filter_id, str(zoom), str(x_tile), str(y_tile),
                                          'tile.pickle')

        nodes, ways, relations = None, None, None

        request_tile = True
        if self.use_cache and os.path.isfile(filename_cache):
            logging.debug("loading tile cached in %s", filename_cache)
            request_tile = False
            try:
                with open(filename_cache, 'rb') as infile:
                    data = pickle.load(infile)
                nodes, ways, relations = data["nodes"], data["ways"], data["relations"]
            except IOError as e:
                logging.debug("loading tile %s failed", filename_cache)
                request_tile = True

                # try to retrieve from server
        if request_tile:
            # request from OSM server
            response = self.request_tile(zoom, x_tile, y_tile, filter_id, country_name=country_name)

            # convert to nodes and ways
            nodes, ways, relations = self.convert_to_dict(response)

            # write to cache if
            if self.use_cache:
                logging.debug("writing tile to %s", filename_cache)
                data = {"nodes": nodes, "ways": ways, "relations": relations}
                os.makedirs(os.path.dirname(filename_cache), exist_ok=True)
                with open(filename_cache, 'wb') as outfile:
                    # outfile.write(data)
                    pickle.dump(data, outfile)

        return nodes, ways, relations

    def request_tile(self, zoom, x_tile, y_tile, filter_id="default", country_name=""):
        # construct the query
        parameters = {"bbox": self.get_tile_bounding_box(zoom, x_tile, y_tile), "country_name": country_name}
        query = self.query_template[filter_id].format(**parameters)

        success = False
        for try_count in range(self.max_tries):
            if self.use_overpass_state:
                status = self.query_overpass_status()
                dt = status["slots_available_after"][0]
            else:
                dt = try_count * 3
            if dt > 0:
                logging.debug("idling %f seconds", dt)
                time.sleep(dt)

            # send query and receive answer
            response = requests.get(self.overpass_url,
                                    params={'data': query},
                                    headers={"User-Agent": self.user_agent})

            if response.status_code == 200:
                success = True
                break

            logging.warning('could not retrieve tile, server returned %s (%d)', response.reason, response.status_code)

        if success:
            # decode to JSON
            response_json = response.json()
        else:
            response_json = None

        return response_json

    def get_tile_bounding_box(self, zoom, x_tile, y_tile):
        south, east = self.tile2latlon(zoom, x_tile + 1, y_tile + 1)
        north, west = self.tile2latlon(zoom, x_tile, y_tile)
        return south, west, north, east

    def get_required_tiles_bounding_box(self, lat, lon, zoom, tolerance_lat=0, tolerance_lon=0):
        lat_min = np.amin(lat) - tolerance_lat
        lat_max = np.amax(lat) + tolerance_lat
        lon_min = np.amin(lon) - tolerance_lon
        lon_max = np.amax(lon) + tolerance_lon

        x_min, y_min = self.latlon2tile(zoom, lat_max, lon_min)
        x_max, y_max = self.latlon2tile(zoom, lat_min, lon_max)

        tiles = [(zoom, x, y) for x in range(x_min, x_max + 1) for y in range(y_min, y_max + 1)]
        return tiles

    def get_required_tiles(self, lat, lon, zoom, extend=0):
        # derive tolerance, measured in degree
        i = len(lat) // 2
        s_lat, s_lon = LocalMap.get_scale_at(lat[i], lon[i])
        tol_lat = s_lat * extend
        tol_lon = s_lon * extend

        tiles = set()

        # go through each point in the lat-lon-list
        for lat_, lon_ in zip(lat, lon):
            # make sure it's a valid coordinate
            if lat_ and lon_:
                # consider the corners of a box, centered at the point (lat_, lon_) and size 2 tol_lat x 2 tol_lan
                for lat__ in (lat_ - tol_lat, lat_ + tol_lat):
                    for lon__ in (lon_ - tol_lon, lon_ + tol_lon):
                        # make sure it's a valid coordinate
                        if -90 <= lat__ <= +90 and -180.0 <= lon__ <= +180:
                            # get tile position
                            x, y = self.latlon2tile(zoom, lat_, lon_)
                            # and add to set
                            tiles.add((zoom, x, y))

        return tiles

    def query_overpass_status(self):
        response = requests.get(self.overpass_status_url,
                                headers={"User-Agent": self.user_agent})

        # r = re.compile(
        #    "Connected as: ([^\n]+)\nCurrent time: ([^\n]+)\nRate limit: ([^\n]+)\n(\d+) slots available (now)|after [^,]+, in (\d+) seconds.")

        lines = response.text.split("\n")

        r1 = re.compile(r"(\d+) slots available now.")
        r2 = re.compile(r"Slot available after: [^,]+, in (\d+) seconds.")

        m1 = r1.match(lines[3])
        if m1:
            i0 = 4
            n = int(m1.group(1))
            t = [0.0] * n
        else:
            i0 = 3
            t = []

        for i in range(i0, len(lines) - 1):
            m2 = r2.match(lines[i])
            if m2:
                t.append(float(m2.group(1)))

        status = {
            "slots_available_after": t
        }

        return status

    @staticmethod
    def latlon2tile(zoom, lat_deg, lon_deg):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        x_tile = int((lon_deg + 180.0) / 360.0 * n)
        y_tile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x_tile, y_tile

    @staticmethod
    def tile2latlon(zoom, x_tile, y_tile):
        n = 2.0 ** zoom
        lon_deg = x_tile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y_tile / n)))
        lat_deg = math.degrees(lat_rad)
        return lat_deg, lon_deg

    @staticmethod
    def convert_to_dict(data):
        nodes = {}
        ways = {}
        relations = {}

        for e in data["elements"]:
            type_e = e["type"]
            id_e = e["id"]
            if type_e == "node":
                nodes[id_e] = e
            elif type_e == "way":
                ways[id_e] = e
            elif type_e == "relation":
                relations[id_e] = e

        return nodes, ways, relations
