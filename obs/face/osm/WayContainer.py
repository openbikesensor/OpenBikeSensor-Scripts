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


import numpy as np
import math

from aabbtree import AABB
from aabbtree import AABBTree


class WayContainerAABBTree:
    def __init__(self, d_max=0):
        self.d_max = d_max
        self.data = AABBTree()

    def __del__(self):
        pass

    def insert(self, element):
        a, b = element.get_axis_aligned_bounding_box()
        aabb = AABB([(a[0], b[0]), (a[1], b[1])])
        self.data.add(aabb, element)

    def find_near_candidates(self, x, d_max):
        if not math.isfinite(x[0]) or not math.isfinite(x[1]):
            return []

        # the point x and a square environment
        bb = AABB([(x[0] - d_max, x[0] + d_max), (x[1] - d_max, x[1] + d_max)])

        candidates = self.data.overlap_values(bb)

        return candidates

    @staticmethod
    def axis_aligned_bounding_boxes_overlap(a1, b1, a2, b2):
        return np.all(a1 < b2) and np.all(a2 < b1)
