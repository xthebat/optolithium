#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import logging as module_logging

from numpy import NaN, rot90, mean, abs, interp, asfortranarray, where, squeeze, \
    degrees, arctan, sin, cos, array, ones, vstack, dot, diff, average
from numpy import max as amax
from numpy import min as amin
from numpy.linalg import lstsq

import optolithiumc as oplc

# noinspection PyUnresolvedReferences
import helpers
import abc


__author__ = 'Alexei Gladkikh'


# Quirk for forward compatibility
try:
    oplc.Edge2d
    oplc.Point2d
except NameError:
    oplc.Edge2d = oplc.Edge
    oplc.Edge2d.cross_type = oplc.Edge.cross
    oplc.Point2d = oplc.Point


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.DEBUG)
helpers.logStreamEnable(logging)


MASK_CLEAR = "clear"
MASK_OPAQUE = "opaque"

IMAGE_NEGATIVE = "negative"
IMAGE_POSITIVE = "positive"

VARIATE_HEIGHT_TRUE = "Yes"
VARIATE_HEIGHT_FALSE = "No"


def _get_target_mask(mask):
    left = right = None
    for region in mask.container.regions:
        x_direct, y_direct = [], []
        for point in region.points:
            if point.y == 0:
                x_direct.append(point.x)
            if point.x == 0:
                y_direct.append(point.y)
        if len(x_direct) == len(region.points):
            axis_direct = x_direct
        elif len(y_direct) == len(region.points):
            axis_direct = y_direct
        for x in axis_direct:
            if (left is None and x < 0) or 0 > x > left:
                left = x
            if (right is None and x > 0) or 0 < x < right:
                right = x
    return left, right


def _is_mask_negative(mask):
    center_transmit, left_transmit, right_transmit = _get_mask_type(mask)
    side_transmit = mean([left_transmit, right_transmit])
    background = mask.container.background
    if center_transmit >= side_transmit:
        tonality = MASK_CLEAR
    else:
        tonality = MASK_OPAQUE
    if tonality is None:
        is_mask_negative = True if background == 0.0 else False
    else:
        is_mask_negative = {MASK_CLEAR: True, MASK_OPAQUE: False}[tonality]
    return is_mask_negative


def contour_sign(mask, **kwargs):
    image_tonality = kwargs.get("image_tonality")
    is_image_negative = {IMAGE_NEGATIVE: True, IMAGE_POSITIVE: False}[image_tonality]
    return not is_image_negative


def _get_mask_type(mask):
    left, right = _get_target_mask(mask)
    center_transmit, left_transmit, right_transmit = -1, -1, -1
    for region in mask.container.regions:
        has_left, has_right = False, False
        for point in region.points:
            if point.x == left:
                has_left = True
            if point.x == right:
                has_right = True
        if has_left and has_right:
            center_transmit = region.transmittance
            side_transmit = mask.container.background
            return center_transmit, side_transmit, side_transmit
        if has_left and not has_right:
            center_transmit = mask.container.background
            left_transmit = region.transmittance
        if not has_left and has_right:
            center_transmit = mask.container.background
            right_transmit = region.transmittance
    return center_transmit, left_transmit, right_transmit


class MetricNotImplementedError(Exception):
    pass


class MetrologyInterface(object):

    __metaclass__ = abc.ABCMeta

    def __calculate_1d_wrap(self, sim_data, **kwargs):
        """:type sim_data: oplc.ResistVolume"""
        if sim_data.has_x:
            x, values = sim_data.x, sim_data.values[0, :, 0]
        else:
            x, values = sim_data.y, sim_data.values[:, 0, 0]
        return self._calculate_1d(x, values, **kwargs)

    def __calculate_2d_wrap(self, sim_data, **kwargs):
        """:type sim_data: oplc.ResistVolume"""
        if sim_data.has_x:
            x, z, values = sim_data.x, sim_data.z, sim_data.values[0, :, :]
        else:
            x, z, values = sim_data.y, sim_data.z, sim_data.values[:, 0, :]
        return self._calculate_2d(x, z, rot90(values), **kwargs)

    def _calculate_1d(self, x, values, **kwargs):
        raise MetricNotImplementedError

    def _calculate_xy(self, sim_data, **kwargs):
        raise MetricNotImplementedError

    def _calculate_2d(self, x, z, values, **kwargs):
        raise MetricNotImplementedError

    def _calculate_3d(self, sim_data, **kwargs):
        raise MetricNotImplementedError

    def _calculate_profile(self, profile, **kwargs):
        raise MetricNotImplementedError

    def _calculate_common(self, sim_data, **kwargs):
        raise MetricNotImplementedError

    def __init__(self, stage):
        self.__stage = stage
        self.__routines = {
            oplc.X_1D: self.__calculate_1d_wrap,
            oplc.Y_1D: self.__calculate_1d_wrap,
            oplc.XY_2D: self._calculate_xy,
            oplc.XZ_2D: self.__calculate_2d_wrap,
            oplc.YZ_2D: self.__calculate_2d_wrap,
            oplc.XYZ_3D: self._calculate_3d
        }

    @property
    def options(self):
        return self.__stage.options

    @property
    def stage(self):
        return self.__stage

    @abc.abstractproperty
    def caption(self):
        pass

    @abc.abstractproperty
    def format(self):
        pass

    def __call__(self, sim_data, **kwargs):
        """:type sim_data: oplc.AbstractResistSimulations"""
        if isinstance(sim_data, dict):
            return self._calculate_common(sim_data, **kwargs)
        elif sim_data.type == oplc.RESIST_VOLUME:
            callback = self.__routines[sim_data.axes]
            return callback(sim_data, **kwargs)
        elif sim_data.type == oplc.RESIST_PROFILE:
            return self._calculate_profile(sim_data, **kwargs)
        else:
            raise RuntimeError("Unknown simulation data type")


def _image_values_at_height(x, z, values, **kwargs):
    height = kwargs.get("height")
    absolute_height = max(z) * height / 100.0
    qx = asfortranarray(x)
    f = oplc.LinearInterpolation2d(qx, asfortranarray(z), asfortranarray(values))
    return squeeze(f.interpolate(qx, asfortranarray(absolute_height)))


class Average(MetrologyInterface):

    caption = property(lambda self: "Average")
    format = property(lambda self: "%.3f")

    def _calculate_1d(self, x, values, **kwargs):
        return mean(values)

    def _calculate_2d(self, x, z, values, **kwargs):
        return mean(_image_values_at_height(x, z, values, **kwargs))


def _calculate_lstsq(polygons, is_left=True):
    s = 1 if is_left else -1
    for polygon in polygons:
        if not(all([edge.org.x > 0 for edge in polygon]) or all([edge.org.x < 0 for edge in polygon])):
            avg_x = average([min(edge.org.x for edge in polygon), max(edge.org.x for edge in polygon)])
            sw_x = [edge.org.y for edge in polygon if s * (edge.org.x - avg_x) < 0]
            sw_y = [edge.org.x for edge in polygon if s * (edge.org.x - avg_x) < 0]
            sw_x_matrix = vstack([sw_x, ones(len(sw_x))]).T
            a, b = lstsq(sw_x_matrix, sw_y)[0]
            return a, b
    raise LookupError


def _calculate_lstsq_v2(polygons):
    nxor = lambda a, b: a and b or not a and not b
    found = False
    a, b = 0.0, 0.0
    for polygon in polygons:
        _do_lstsq = False
        if all([edge.org.x < 0 for edge in polygon]):
            start_point = max([edge.org.x for edge in polygon if edge.org.y == 0])
            max_y = 0.9 * max(edge.org.y for edge in polygon)
            angle_new = 0.0
            _to_left = True
            i = 0
            sw_x, sw_y = [], []
            for edge in reversed(polygon):
                if _do_lstsq and edge.org.y != 0 and edge.org.y >= old_edge.org.y:
                    angle_old = angle_new
                    angle_new = (edge.org.x - start_point)/edge.org.y
                    sw_x.append(edge.org.y)
                    sw_y.append(edge.org.x)
                    if nxor(_to_left, angle_new > angle_old):
                        end_sw_x = sw_x[:]
                        end_sw_y = sw_y[:]
                        _to_left = not _to_left
                        i += 1
                elif edge.org.y == 0.0 and edge.org.x == start_point:
                    _do_lstsq = True
                    old_edge = edge
                elif edge.org.y < old_edge.org.y and edge.org.y != 0:
                    end_sw_x = sw_x[:]
                    end_sw_y = sw_y[:]
                    break
            if i < 3:
                _do_lstsq = False
                for edge in reversed(polygon):
                    if _do_lstsq and edge.org.y != 0 and edge.org.y <= max_y:
                        end_sw_x.append(edge.org.y)
                        end_sw_y.append(edge.org.x)
                    elif edge.org.y == 0.0 and edge.org.x == start_point:
                        _do_lstsq = True
            sw_x_matrix = vstack([end_sw_x, ones(len(end_sw_x))]).T
            found = True
            a, b = lstsq(sw_x_matrix, end_sw_y)[0]
    if not found:
        raise LookupError
    return a, b


class SidewallAngle(MetrologyInterface):

    caption = property(lambda self: "Sidewall Angle Avg. (deg.)")
    format = property(lambda self: "%.1f")

    @staticmethod
    def _calculate_sidewall_angle(polygons):
        a_left, _ = _calculate_lstsq(polygons, is_left=True)
        a_right, _ = _calculate_lstsq(polygons, is_left=False)
        sa_left = 90.0 - abs(degrees(arctan(a_left)))
        sa_right = 90.0 - abs(degrees(arctan(a_right)))
        return mean([sa_left, sa_right])

    @staticmethod
    def _calculate_sidewall_angle_v2(polygons):
        a, _ = _calculate_lstsq_v2(polygons)
        return 90.0 - abs(degrees(arctan(a)))

    def _calculate_2d(self, x, z, values, **kwargs):
        level = kwargs.get("level")
        negative = contour_sign(self.options.mask, **kwargs)
        polygons = oplc.contours(asfortranarray(x), asfortranarray(z), asfortranarray(values), level, negative)
        try:
            if _is_mask_negative(self.options.mask):
                return SidewallAngle._calculate_sidewall_angle_v2(polygons)
            else:
                return SidewallAngle._calculate_sidewall_angle(polygons)
        except LookupError:
            return NaN

    def _calculate_profile(self, profile, **kwargs):
        try:
            if _is_mask_negative(self.options.mask):
                return SidewallAngle._calculate_sidewall_angle_v2(profile.polygons)
            else:
                return SidewallAngle._calculate_sidewall_angle(profile.polygons)
        except LookupError:
            return NaN


class StandingWaveAmpl(MetrologyInterface):

    caption = property(lambda self: "SW Amplitude Avg. (nm)")
    format = property(lambda self: "%.3f")

    @staticmethod
    def _calculate_swamp(polygons, is_left=True):
        a, b = _calculate_lstsq(polygons, is_left)
        s = 1 if is_left else -1
        rotate_matrix = array([[cos(arctan(a)), -sin(arctan(a))], [sin(arctan(a)), cos(arctan(a))]])
        for polygon in polygons:
            if not(all([edge.org.x > 0 for edge in polygon]) or all([edge.org.x < 0 for edge in polygon])):
                sw_points = []
                for edge in polygon:
                    if s * edge.org.x < 0:
                        old_point = array([edge.org.y, edge.org.x])
                        new_point = dot(old_point, rotate_matrix) - [0, b]
                        sw_points.append(new_point[1])
                sw_points = array(sw_points)
                # Getting average of absolute maximum values of resist profile edge (standing wave curve)
                # by mean of derivative analysis
                d = diff(sw_points)
                result = average(abs([sw_points[k+1] for k, (cur, nxt) in enumerate(zip(d, d[1:])) if cur*nxt < 0]))
                return result
        raise LookupError

    @staticmethod
    def _calculate_swamp_v2(polygons):
        a, b = _calculate_lstsq_v2(polygons)
        rotate_matrix = array([[cos(arctan(a)), -sin(arctan(a))], [sin(arctan(a)), cos(arctan(a))]])
        for polygon in polygons:
            _do_lstsq = False
            if all([edge.org.x < 0 for edge in polygon]):
                sw_points = []
                start_point = max([edge.org.x for edge in polygon if edge.org.y == 0])
                for edge in reversed(polygon):
                    if _do_lstsq and edge.org.y != 0 and edge.org.y >= old_edge.org.y:
                        old_point = array([edge.org.y, edge.org.x])
                        new_point = dot(old_point, rotate_matrix) - [0, b]
                        sw_points.append(new_point[1])
                    elif edge.org.y == 0.0 and edge.org.x == start_point:
                        _do_lstsq = True
                        old_edge = edge
                sw_points = array(sw_points)
                # Getting average of absolute maximum values of resist profile edge (standing wave curve)
                # by mean of derivative analysis
                d = diff(sw_points)
                result = average(abs([sw_points[k+1] for k, (cur, nxt) in enumerate(zip(d, d[1:])) if cur*nxt < 0]))
                return result
        raise LookupError

    def _calculate_2d(self, x, z, values, **kwargs):
        level = kwargs.get("level")
        negative = contour_sign(self.options.mask, **kwargs)
        # center_transmit, left_transmit, right_transmit = _get_mask_type(self.options.mask)
        polygons = oplc.contours(asfortranarray(x), asfortranarray(z), asfortranarray(values), level, negative)
        try:
            if _is_mask_negative(self.options.mask):
                return StandingWaveAmpl._calculate_swamp_v2(polygons)
            else:
                swamp_left = StandingWaveAmpl._calculate_swamp(polygons, is_left=True)
                swamp_right = StandingWaveAmpl._calculate_swamp(polygons, is_left=False)
                return mean([swamp_left, swamp_right])
        except LookupError:
            return NaN

    def _calculate_profile(self, profile, **kwargs):
        try:
            if _is_mask_negative(self.options.mask):
                return StandingWaveAmpl._calculate_swamp_v2(profile.polygons)
            else:
                swamp_left = StandingWaveAmpl._calculate_swamp(profile.polygons, is_left=True)
                swamp_right = StandingWaveAmpl._calculate_swamp(profile.polygons, is_left=False)
                return mean([swamp_left, swamp_right])
        except LookupError:
            return NaN


class Contrast(MetrologyInterface):

    caption = property(lambda self: "Contrast")
    format = property(lambda self: "%.3f")

    @staticmethod
    def __contrast_expr(values):
        return (amax(values) - amin(values)) / (amax(values) + amin(values))

    def _calculate_1d(self, x, values, **kwargs):
        return self.__contrast_expr(values)

    def _calculate_2d(self, x, z, values, **kwargs):
        return self.__contrast_expr(_image_values_at_height(x, z, values, **kwargs))

    def _calculate_xy(self, aerial_image, **kwargs):
        """:type aerial_image: oplc.ResistVolume"""
        # TODO: Wrong result compare to Prolith
        return self.__contrast_expr(aerial_image.values)


class ResistMagReflectivity(MetrologyInterface):

    caption = property(lambda self: "Resist Mag. Reflectivity")
    format = property(lambda self: "%.3f")

    def _calculate_common(self, sim_data, **kwargs):
        return sim_data["resist_reflectivity"]


class SubstrateMagReflectivity(MetrologyInterface):

    caption = property(lambda self: "Substrate Mag. Reflectivity")
    format = property(lambda self: "%.3f")

    def _calculate_common(self, sim_data, **kwargs):
        return sim_data["substrate_reflectivity"]


class ResistPhaseReflectivity(MetrologyInterface):

    caption = property(lambda self: "Resist Phase Reflectivity")
    format = property(lambda self: "%.3f")

    def _calculate_common(self, sim_data, **kwargs):
        return sim_data["resist_phase"]


class SubstratePhaseReflectivity(MetrologyInterface):

    caption = property(lambda self: "Substrate Phase Reflectivity")
    format = property(lambda self: "%.3f")

    def _calculate_common(self, sim_data, **kwargs):
        return sim_data["substrate_phase"]


def _calculate_thickness(polygons):
    if not len(polygons):
        return NaN

    return max([max(polygon, key=lambda e: e.org.y).org.y for polygon in polygons])


class ResistLoss(MetrologyInterface):

    caption = property(lambda self: "Resist lost (nm):")
    format = property(lambda self: "%.3f")

    def _calculate_profile(self, profile, **kwargs):
        """:type profile: oplc.ResistProfile"""
        return amax(profile.z) - _calculate_thickness(profile.polygons)


class CriticalDimension(MetrologyInterface):

    caption = property(lambda self: "CD (nm)")
    format = property(lambda self: "%.3f")

    def _calculate_1d(self, x, values, **kwargs):
        level = kwargs.get("level")
        level_edge = oplc.Edge2d(min(x), level, amax(x), level)
        cross_points = []
        for k in xrange(len(values)-1):
            current_edge = oplc.Edge2d(x[k], values[k], x[k+1], values[k+1])
            if level_edge.cross_type(current_edge) == oplc.SKEW_CROSS:
                cross_points.append(level_edge.point(current_edge))

        if len(cross_points) != 2:
            return NaN

        return oplc.Edge2d(cross_points[0], cross_points[1]).length()

    @staticmethod
    def __calculate_cd(x, z, polygons, **kwargs):
        height = kwargs.get("height")
        variate = kwargs.get("variate_height")
        # tonality = kwargs.get("mask_tonality")

        if variate == VARIATE_HEIGHT_TRUE:
            thickness = _calculate_thickness(polygons)
        elif variate == VARIATE_HEIGHT_FALSE or variate is None:
            thickness = amax(z)
        else:
            raise RuntimeError("Wrong variate height option: %s" % variate)

        absolute_height = height * thickness / 100.0

        x_min, x_max = amin(x), amax(x)

        level_edge = oplc.Edge2d(oplc.Point2d(x_min, absolute_height), oplc.Point2d(x_max, absolute_height))
        # logging.info("Level edge: %s" % level_edge)

        cross_points = set()
        for polygon in polygons:
            for edge in polygon:
                # logging.info("Edge: %s" % edge)
                if level_edge.cross_type(edge) == oplc.SKEW_CROSS:
                    point = level_edge.point(edge)
                    # logging.info("=======> Cross point: %s <=======" % point)
                    cross_points.add(point.round(3))
                    # logging.info("Current: %s" % cross_points)

        if not cross_points:
            return NaN

        # Lookup two points nearest to the center of the given area (because mask feature for 1D mask always centered)
        xmin1 = min(cross_points, key=lambda p: oplc.Edge2d(p, oplc.Point2d(0.0, p.y)).length())
        cross_points.remove(xmin1)
        xmin2 = min(cross_points, key=lambda p: oplc.Edge2d(p, oplc.Point2d(0.0, p.y)).length())

        return oplc.Edge2d(xmin1, xmin2).length()

    def _calculate_2d(self, x, z, values, **kwargs):
        level = kwargs.get("level")
        negative = contour_sign(self.options.mask, **kwargs)
        polygons = oplc.contours(asfortranarray(x), asfortranarray(z), asfortranarray(values), level, negative)
        return CriticalDimension.__calculate_cd(x, z, polygons, **kwargs)

    def _calculate_profile(self, profile, **kwargs):
        """:type profile: oplc.ResistProfile"""

        if profile.has_x:
            x = profile.x
        elif profile.has_y:
            x = profile.y
        else:
            return NaN

        return CriticalDimension.__calculate_cd(x, profile.z, profile.polygons, **kwargs)


class CriticalDimensionAbsoluteError(CriticalDimension):

    caption = property(lambda self: "CD Error (nm)")
    format = property(lambda self: "%.3f")

    def _calculate_1d(self, x, values, **kwargs):
        cd = super(CriticalDimensionAbsoluteError, self)._calculate_1d(x, values, **kwargs)
        left, right = _get_target_mask(self.options.mask)
        return cd - (right - left)

    def _calculate_2d(self, x, z, values, **kwargs):
        cd = super(CriticalDimensionAbsoluteError, self)._calculate_2d(x, z, values, **kwargs)
        left, right = _get_target_mask(self.options.mask)
        return cd - (right - left)

    def _calculate_profile(self, profile, **kwargs):
        cd = super(CriticalDimensionAbsoluteError, self)._calculate_profile(profile, **kwargs)
        left, right = _get_target_mask(self.options.mask)
        return cd - (right - left)


class CriticalDimensionRelativeError(CriticalDimension):

    caption = property(lambda self: "CD Error (%)")
    format = property(lambda self: "%.3f")

    def _calculate_1d(self, x, values, **kwargs):
        cd = super(CriticalDimensionRelativeError, self)._calculate_1d(x, values, **kwargs)
        left, right = _get_target_mask(self.options.mask)
        target = right - left
        return float(cd - target)/float(target)*100.0

    def _calculate_2d(self, x, z, values, **kwargs):
        cd = super(CriticalDimensionRelativeError, self)._calculate_2d(x, z, values, **kwargs)
        left, right = _get_target_mask(self.options.mask)
        target = right - left
        return float(cd - target)/float(target)*100.0

    def _calculate_profile(self, profile, **kwargs):
        cd = super(CriticalDimensionRelativeError, self)._calculate_profile(profile, **kwargs)
        left, right = _get_target_mask(self.options.mask)
        target = right - left
        return float(cd - target)/float(target)*100.0


class TimeToClear(MetrologyInterface):

    caption = property(lambda self: "Time to Clear (sec)")
    format = property(lambda self: "%.1f")

    def _calculate_2d(self, x, z, values, **kwargs):
        return amin(values[where(z == 0), :])


class Slope(MetrologyInterface):

    caption = property(lambda self: "Slope Avg. (1/um)")
    format = property(lambda self: "%.3f")

    @staticmethod
    def _calc_dvalue(left, right, dx, x, values):
        v0 = interp([left-dx, right-dx], x, values)
        v1 = interp([left+dx, right+dx], x, values)
        return abs(v1 - v0)

    def _calc_slope(self, left, right, x, values):
        dx = float(self.options.numerics.grid_xy.value)/10.0
        dv = Slope._calc_dvalue(left, right, dx, x, values)
        return mean(dv)/2.0/dx*1000.0

    def _calculate_1d(self, x, values, **kwargs):
        left, right = _get_target_mask(self.options.mask)
        return self._calc_slope(left, right, x, values)

    def _calculate_2d(self, x, z, values, **kwargs):
        left, right = _get_target_mask(self.options.mask)
        return self._calc_slope(left, right, x, _image_values_at_height(x, z, values, **kwargs))


class LogSlope(Slope):

    caption = property(lambda self: "Log Slope Avg. (1/um)")
    format = property(lambda self: "%.3f")

    def _calc_logslope(self, left, right, x, values):
        s = self._calc_slope(left, right, x, values)
        v = mean(interp([left, right], x, values))
        return s/v

    def _calculate_1d(self, x, values, **kwargs):
        left, right = _get_target_mask(self.options.mask)
        return self._calc_logslope(left, right, x, values)

    def _calculate_2d(self, x, z, values, **kwargs):
        left, right = _get_target_mask(self.options.mask)
        return self._calc_logslope(left, right, x, _image_values_at_height(x, z, values, **kwargs))


class NILS(LogSlope):

    caption = property(lambda self: "NILS (Avg.)")
    format = property(lambda self: "%.3f")

    def _calc_nils(self, left, right, x, values):
        s = self._calc_slope(left, right, x, values)
        v = mean(interp([left, right], x, values)) * 1000.0
        return s * (right - left) / v

    def _calculate_1d(self, x, values, **kwargs):
        left, right = _get_target_mask(self.options.mask)
        return self._calc_nils(left, right, x, values)

    def _calculate_2d(self, x, z, values, **kwargs):
        left, right = _get_target_mask(self.options.mask)
        return self._calc_nils(left, right, x, _image_values_at_height(x, z, values, **kwargs))

# _calculate_1d, _calculate_2d
IMAGE_METRICS = [
    Average,
    Contrast,
    CriticalDimension,
    CriticalDimensionAbsoluteError,
    CriticalDimensionRelativeError,
    Slope,
    LogSlope,
    NILS,
    StandingWaveAmpl
]

# _calculate_common
STANDING_WAVES_METRICS = [
    ResistMagReflectivity,
    ResistPhaseReflectivity,
    SubstrateMagReflectivity,
    SubstratePhaseReflectivity
]

# _calculate_2d
CONTOUR_METRICS = [
    TimeToClear,
    CriticalDimension,
    CriticalDimensionAbsoluteError,
    CriticalDimensionRelativeError,
    # SidewallAngle,
    # StandingWaveAmpl
]

# _calculate_profile
PROFILE_METRICS = [
    CriticalDimension,
    CriticalDimensionAbsoluteError,
    CriticalDimensionRelativeError,
    ResistLoss,
    SidewallAngle,
    StandingWaveAmpl
]