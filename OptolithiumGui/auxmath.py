# This file is part of Optolithium lithography modelling software.
#
# Copyright (C) 2015 Alexei Gladkikh
#
# This software is dual-licensed: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version only for NON-COMMERCIAL usage.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# If you are interested in other licensing models, including a commercial-
# license, please contact the author at gladkikhalexei@gmail.com

import numpy


__author__ = 'Alexei Gladkikh'


def cartesian(*arrays):
    """
    Generate a cartesian product of input arrays.

    :param tuple of ndarray arrays: 1-D arrays to form the cartesian product of.
    :return: 2-D array of shape (M, len(arrays)) containing cartesian products formed of input arrays.
    :rtype: ndarray

    Examples
    --------
    >>> cartesian([1, 2, 3], [4, 5], [6, 7])
    array([[1, 4, 6],
           [1, 4, 7],
           [1, 5, 6],
           [1, 5, 7],
           [2, 4, 6],
           [2, 4, 7],
           [2, 5, 6],
           [2, 5, 7],
           [3, 4, 6],
           [3, 4, 7],
           [3, 5, 6],
           [3, 5, 7]])

    """
    def _cartesian(_arrays, _out):
        _n = numpy.prod([_x.size for _x in _arrays])
        m = _n / _arrays[0].size
        _out[:, 0] = numpy.repeat(_arrays[0], m)
        if _arrays[1:]:
            _cartesian(_arrays[1:], _out=_out[0:m, 1:])
            for j in xrange(1, _arrays[0].size):
                _out[j*m:(j+1)*m, 1:] = _out[0:m, 1:]
        return _out

    arrays = [numpy.asarray(x) for x in arrays]
    n = numpy.prod([x.size for x in arrays])
    out = numpy.zeros([n, len(arrays)], dtype=arrays[0].dtype)
    _cartesian(arrays, out)
    return out


def middle(vec):
    """
    Calculate zero index of frequency vector
    :param ndarray or list vec: Input numpy array
    :rtype: int

    Examples
    --------
    >>> middle(numpy.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    2
    >>> middle([5.0])
    0
    """
    return int(numpy.floor(len(vec) / 2.0))


def point_line_distance(point, line):
    """
    Calculate the minimum distance between point and line specified by two points

    :type point: list[float | int]
    :type line: list[list[float | int]]

    Examples
    --------
    >>> round(point_line_distance([-1, 3], [[0, 1.5], [10, -6]]), 1)
    0.6
    """
    a = -float(line[1][1] - line[0][1])
    b = float(line[1][0] - line[0][0])
    c = line[0][0] * line[1][1] - line[1][0] * line[0][1]
    return abs(a*point[0] + b*point[1] + c) / numpy.sqrt(a**2 + b**2)


def point_inside_polygon(point, polygon):
    """
    Check whether point belongs to the polygon

    :rtype: bool

    Examples
    --------
    >>> class Point(object):
    ...     def __init__(self, x, y):
    ...         self.x = x
    ...         self.y = y
    >>> class Polygon(object):
    ...     def __init__(self, points):
    ...         self.points = points
    >>> polygon = Polygon([
    ...     Point(35.0, 120.5), Point(37.9, 129.1),
    ...     Point(46.9, 129.1), Point(39.7, 134.5),
    ...     Point(42.3, 143.1), Point(35.0, 139.0),
    ...     Point(27.7, 143.1), Point(30.3, 134.5),
    ...     Point(23.1, 129.1), Point(32.1, 129.1)])
    >>> point_inside_polygon(Point(35.0, 134.5), polygon)
    True
    >>> point_inside_polygon(Point(100.0, 100.5), polygon)
    False
    >>> polygon = Polygon([Point(10.0, 0.0), Point(15.0, 0.0)])
    >>> point_inside_polygon(Point(12.0, 0.0), polygon)
    True
    >>> point_inside_polygon(Point(54.0, 0.0), polygon)
    False
    >>> polygon = Polygon([Point(0.0, 21.0), Point(0.0, 30.5)])
    >>> point_inside_polygon(Point(0.0, 22.0), polygon)
    True
    >>> point_inside_polygon(Point(0.0, -1.0), polygon)
    False
    """
    n = len(polygon.points)
    if n == 2:
        return polygon.points[0].x <= point.x <= polygon.points[1].x and \
            polygon.points[0].y <= point.y <= polygon.points[1].y
    else:
        inside = False

        p1x, p1y = polygon.points[0].x, polygon.points[0].y
        for k in range(n + 1):
            p2x, p2y = polygon.points[k % n].x, polygon.points[k % n].y
            if min(p1y, p2y) < point.y <= max(p1y, p2y) and point.x <= max(p1x, p2x):
                if (p1y != p2y and point.x < (point.y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x) or p1x == p2x:
                    inside = not inside
            p1x, p1y = p2x, p2y

        return inside


if __name__ == "__main__":
    import doctest
    doctest.testmod()