from enum import Enum, auto
import numpy as np


EARTH_CIRCUMFERENCE_VERTICAL = 40_007  # km
EARTH_CIRCUMFERENCE_HORIZONTAL = 40_075  # km
DEGREES_CIRCUMFERENCE = 360  # deg


class Approximation(Enum):
    FIRST = auto()
    SECOND = auto()
    ALL = auto()


def area_first(mhs, mvs, *args):
    return mhs * mvs


def area_second(mhs, mvs, lat, *args):
    return mhs * mvs * (np.cos(np.deg2rad(lat)))


area_functions = {Approximation.FIRST: area_first,
                  Approximation.SECOND: area_second}

