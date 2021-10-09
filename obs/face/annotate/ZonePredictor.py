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
import os.path
import numpy as np
import logging
from sklearn import svm
import dill as pickle

from obs.face.osm.Way import Way


log = logging.getLogger(__name__)


class ZonePredictor:

    def __init__(self, load_classifier_from=None):
        self.y_urban = 1
        self.y_rural = 2

        # define features
        self.x_features = [Feature("highway"),
                           Feature("maxspeed"),
                           Feature("oneway"),
                           Feature("surface"),
                           Feature("lanes"),
                           Feature("lit"),
                           Feature("sidewalk"),
                           Feature("smoothness"),
                           Feature("ref", f=lambda v: v[0]),
                           Feature("name", f=lambda v: len(v) > 0)]

        self.y_feature = Feature("zone:traffic", x_mapped={"DE:urban": self.y_urban, "DE:rural": self.y_rural},
                                 grow_enumeration=False,
                                 allow_undefined=False)

        self.classifier = None
        self.evaluation_test = None
        self.evaluation_train = None

        if load_classifier_from:
            if load_classifier_from == "Germany.test":
                load_classifier_from = os.path.join(os.path.dirname(__file__), "..", "..", "data", "face_zone_predictor",
                                                    "Germany.test.pickle")
            else:
                log.exception("invalid zone predictor: %s", load_classifier_from)
                load_classifier_from = None
            self.load(load_classifier_from)

    def predict(self, way):
        if self.classifier:
            x = np.hstack([f.encode_to_one_hot(f.way_to_enumeration(way)) for f in self.x_features]).reshape(1, -1)
            y = self.classifier.predict(x)

            zone = "DE:urban" if y == self.y_urban else "DE:rural" if y == self.y_rural else None
        else:
            zone = None

        return zone

    def train(self, samples, split=0.7):
        # encode samples
        x, y = self.encode_samples(samples)

        n = len(y)
        n_split = round(split * n)

        ix = np.random.permutation(n)

        ix_train, ix_test = ix[:n_split], ix[n_split:]
        x_train, x_test = x[ix_train], x[ix_test]
        y_train, y_test = y[ix_train], y[ix_test]

        c = svm.SVC(kernel='rbf')
        c.fit(x_train, y_train)

        self.classifier = c

        self.evaluation_train = self.evaluate(c, x_train, y_train)
        self.evaluation_test = self.evaluate(c, x_test, y_test)

        fmt = "{n} samples: {N} urban, {P} rural\n" \
              "hit rate for 'urban': {specificity}\n" \
              "hit rate for 'rural': {recall}\n" \
              "accuracy            : {accuracy}"

        print("evaluation on training data")
        print(fmt.format(**self.evaluation_train))

        print("evaluation on test data")
        print(fmt.format(**self.evaluation_test))

    def evaluate(self, c, x, y):
        yp = c.predict(x)

        e = {
            "n": len(y),
            "P": np.count_nonzero(y == self.y_rural),
            "N": np.count_nonzero(y == self.y_urban),
            "TP": np.count_nonzero(np.logical_and(y == self.y_rural, yp == self.y_rural)),
            "TN": np.count_nonzero(np.logical_and(y == self.y_urban, yp == self.y_urban)),
            "FP": np.count_nonzero(np.logical_and(y == self.y_rural, yp == self.y_urban)),
            "FN": np.count_nonzero(np.logical_and(y == self.y_urban, yp == self.y_rural)),
        }

        e["accuracy"] = (e["TP"] + e["TN"]) / (e["P"] + e["N"])

        e["recall"] = e["TP"] / e["P"]
        e["specificity"] = e["TN"] / e["N"]

        return e

    def encode_samples(self, way_samples):
        # first determine range of values, create one enumerations per feature
        samples = []
        for way in way_samples:
            x = [f.way_to_enumeration(way) for f in self.x_features]
            y = self.y_feature.way_to_enumeration(way)

            # check for validity
            if y < 0 or any(v < 0 for v in x):
                continue

            # store sampled
            sample = {'x': x, 'y': y}
            samples.append(sample)

        # then convert to one-hot-encoding
        x = np.vstack(
            [np.hstack([f.encode_to_one_hot(x_) for x_, f in zip(sample["x"], self.x_features)]) for sample in samples])
        y = np.hstack([self.y_feature.encode_to_identity(sample["y"]) for sample in samples])
        return x, y

    def store(self, filename):
        with open(filename, "wb") as file:
            data = {"classifier": self.classifier, "x_features": self.x_features, "y_feature": self.y_feature,
                    "y_rural": self.y_rural, "y_urban": self.y_urban, "evaluation_test": self.evaluation_test,
                    "evaluation_train": self.evaluation_train}
            pickle.dump(data, file)

    def load(self, filename):
        with open(filename, 'rb') as file:
            data = pickle.load(file)

        assert isinstance(data["classifier"], svm.SVC) and \
               all([isinstance(f, Feature) for f in data["x_features"]]) and \
               isinstance(data["y_feature"], Feature), \
               "invalid data types when reading classifier from " + filename

        self.classifier = data["classifier"]
        self.x_features = data["x_features"]
        self.y_feature = data["y_feature"]
        self.y_urban = data["y_urban"]
        self.y_rural = data["y_rural"]
        self.evaluation_test = data["evaluation_test"]
        self.evaluation_train = data["evaluation_train"]


class Feature:
    def __init__(self, tag, x_invalid=-1, x_undefined=0, x_mapped=None, grow_enumeration=True, allow_undefined=True,
                 f=None):
        self.tag = tag
        self.x_invalid = x_invalid
        self.x_undefined = x_undefined
        self.x_mapped = x_mapped if x_mapped else {}
        self.ix_max = max([self.x_undefined] + list(self.x_mapped.values()))
        self.grow_enumeration = grow_enumeration
        self.allow_undefined = allow_undefined
        self.f = f if f else lambda v: v

    def way_to_enumeration(self, way):
        x = self.x_invalid
        if isinstance(way, Way):
            tags = way.tags
        else:
            tags = way["tags"]
        if self.tag not in tags:
            if self.allow_undefined:
                x = self.x_undefined
        else:
            v = tags[self.tag]
            v = self.f(v)
            if v in self.x_mapped:
                x = self.x_mapped[v]
            elif self.grow_enumeration:
                self.ix_max += 1
                self.x_mapped[v] = self.ix_max
                x = self.ix_max
        return x

    def encode_to_one_hot(self, x):
        return np.array([1 if i == x else 0 for i in range(self.ix_max + 1)])

    @staticmethod
    def encode_to_identity(x):
        return x
