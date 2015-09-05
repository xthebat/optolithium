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
import optolithiumc as oplc

from numpy import rot90, asfortranarray, linspace, round, arange
from scipy.interpolate import interp2d
from matplotlib.collections import PathCollection
from matplotlib.patches import Polygon, Rectangle
from matplotlib.colors import BoundaryNorm
# from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from qt import QtGui, QtCore, connect, Slot
from config import COMMON_LINES_COLOR, RESIST_FILL_COLOR, RESIST_LINES_COLOR, RESIST_CONTOUR_COLOR
from views.common import QStackWidgetTab, QGraphPlot, QMetrologyTable, \
    ProlithColormap, show_traceback, NavigationToolbar
from metrics import contour_sign

import helpers


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.DEBUG)
helpers.logStreamEnable(logging)


def get_selection_rectangle(x0, y0, event):
    right, left = (x0, event.xdata) if x0 > event.xdata else (event.xdata, x0)
    top, bottom = (y0, event.ydata) if y0 > event.ydata else (event.ydata, y0)
    return right, left, top, bottom


def get_selection_percentage(right, left, top, bottom, xlim, ylim):
    perc_x = float(right - left) / float(xlim[1] - xlim[0]) * 100
    perc_y = float(top - bottom) / float(ylim[1] - ylim[0]) * 100
    return perc_x, perc_y


class Ability(object):

    p1d = 0   # graph 1d
    xy2d = 1  # xy plot 2d
    xz2d = 2  # xz or yz plot 2d (image)
    p2d = 3   # profile 2d
    p3d = 4   # profile 3d

    def enable(self, axes):
        raise NotImplementedError("Ability enable method not implemented")

    def disable(self):
        raise NotImplementedError("Ability disable method not implemented")

    @property
    def suites(self):
        raise NotImplementedError("Suites property not implemented")


class RulerAbility(Ability):

    SNAP_DISTANCE = 10.0
    SINGLE_CLICK_DISTANCE = 10.0
    MEASURE_MOUSE_BUTTON = 1

    Arbitrary = 0
    Manhattan = 1
    Diagonal = 2

    def __init__(self):
        self.__axes = None
        self.__enabled = False

        self.__pressed_x = None
        self.__pressed_y = None
        self.__pressed = False

        self.__press_cid = None
        self.__release_cid = None
        self.__motion_cid = None
        self.__key_press_cid = None
        self.__key_release_cid = None

        self.__current_ruler = None

        self.__shift_held = False
        self.__ctrl_held = False

        self.__rulers = []

    def enable(self, axes):
        if not self.__enabled:
            self.__axes = axes
            self.__press_cid = self.__axes.figure.canvas.mpl_connect("button_press_event", self._on_mouse_press)
            self.__release_cid = self.__axes.figure.canvas.mpl_connect("button_release_event", self._on_mouse_release)
            self.__motion_cid = self.__axes.figure.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
            self.__key_press_cid = self.__axes.figure.canvas.mpl_connect("key_press_event", self._on_key_press)
            self.__key_release_cid = self.__axes.figure.canvas.mpl_connect("key_release_event", self._on_key_release)
            self.__enabled = True
        elif self.__axes is not axes:
            self.disable()
            self.enable(axes)

    def disable(self):
        if self.__enabled:
            self.__axes.figure.canvas.mpl_disconnect(self.__press_cid)
            self.__axes.figure.canvas.mpl_disconnect(self.__release_cid)
            self.__axes.figure.canvas.mpl_disconnect(self.__motion_cid)
            self.__axes.figure.canvas.mpl_disconnect(self.__key_press_cid)
            self.__axes.figure.canvas.mpl_disconnect(self.__key_release_cid)
            self.__axes = None
            self.__enabled = False

    @property
    def suites(self):
        return [Ability.p2d, Ability.xy2d]

    def _on_key_press(self, event):
        logging.info("key pressed = %s" % event)
        if event.key == "shift":
            self.__shift_held = True
        elif event.key == "ctrl":
            self.__ctrl_held = True

    def _on_key_release(self, event):
        if event.key == "shift":
            self.__shift_held = False
        elif event.key == "ctrl":
            self.__ctrl_held = False

    def _on_mouse_press(self, event):
        # logging.info("Mouse press event")
        if self.__enabled and event.inaxes == self.__axes and event.button == self.MEASURE_MOUSE_BUTTON:
            self.__pressed_x = event.xdata
            self.__pressed_y = event.ydata
            self.__pressed = True

    def _lookup_nearest_point(self, event):

        def _check_polygon(_points, _polygon, _clicked_point):
            for k in range(len(_polygon)-2):
                edge = oplc.Edge2d(_polygon[k][0], _polygon[k][1], _polygon[k+1][0], _polygon[k+1][1])
                normal_point = _clicked_point.normal_intersect(edge)
                if normal_point.classify(edge) == oplc.BETWEEN:
                    _points.append(normal_point)

        possible_points = []
        clicked_point = oplc.Point2d(event.xdata, event.ydata)
        # logging.info("Collections: %s" % self.__axes.collections)
        for collection in filter(lambda c: isinstance(c, PathCollection), self.__axes.collections):
            for path in collection.get_paths():
                for polygon in path.to_polygons():
                    # logging.info("POLYGON: %s" % len(polygon))
                    # Matplotlib duplicate the last point of the polygon to times
                    # (also this point is close polygon, e.i. equal to first)
                    _check_polygon(possible_points, polygon, clicked_point)

                    # for k in range(len(polygon)-2):
                    #     edge = oplc.Edge(polygon[k][0], polygon[k][1], polygon[k+1][0], polygon[k+1][1])
                    #     normal_point = clicked_point.normal_intersect(edge)
                    #     if normal_point.classify(edge) == oplc.BETWEEN:
                    #         possible_points.append(normal_point)

        for polygon in filter(lambda p: isinstance(p, Polygon), self.__axes.patches):
            _check_polygon(possible_points, polygon.xy, clicked_point)

        # logging.info("POINTS: %s" % possible_points)
        if possible_points:
            nearest_point = min(possible_points, key=lambda p: oplc.Edge2d(p, clicked_point).length())
            e = oplc.Edge2d(nearest_point, clicked_point)
            xlim = self.__axes.get_xlim()
            ylim = self.__axes.get_ylim()
            p_x = abs(e.dx()) / (xlim[1] - xlim[0]) * 100
            p_y = abs(e.dy()) / (ylim[1] - ylim[0]) * 100
            if p_x < self.SNAP_DISTANCE and p_y < self.SNAP_DISTANCE:
                return nearest_point

        return None

    def _normalize_last_point(self, edge):
        """:type edge: oplc.Edge2d """
        if self.__shift_held:
            if edge.dx() < edge.dy():
                edge.org.x = edge.dst.x
            else:
                edge.org.y = edge.dst.y

    def _on_mouse_release(self, event):
        # logging.info("Mouse release event")
        if self.__enabled and event.inaxes == self.__axes and event.button == self.MEASURE_MOUSE_BUTTON:
            right, left, top, bottom = get_selection_rectangle(self.__pressed_x, self.__pressed_y, event)
            perc_x, perc_y = get_selection_percentage(
                right, left, top, bottom, self.__axes.get_xlim(), self.__axes.get_ylim())

            if perc_x < 1.0 and perc_y < 1.0:
                nearest_point = self._lookup_nearest_point(event)
                if nearest_point is not None:
                    if self.__current_ruler is None:
                        self.__current_ruler = self.__axes.annotate(
                            '', xy=(nearest_point.x, nearest_point.y), xycoords="data",
                            xytext=(event.xdata, event.ydata), textcoords="data", size=20, color="r",
                            arrowprops=dict(arrowstyle="<|-|>", mutation_scale=20, edgecolor="k",
                                            linewidth=2, shrinkA=0, shrinkB=0))
                        # self.__axes.add_line(self.__current_ruler)
                    else:
                        x0 = self.__current_ruler.xy[0]
                        y0 = self.__current_ruler.xy[1]
                        edge = oplc.Edge2d(nearest_point.x, nearest_point.y, x0, y0)
                        self._normalize_last_point(edge)
                        self.__rulers.append(self.__current_ruler)
                        self.__current_ruler = None
                        self.__rulers[-1].xytext = (edge.org.x, edge.org.y)
                        text = "%.1f" % edge.length()
                        self.__rulers[-1].set_text(text)

        self.__pressed_x = self.__pressed_y = None
        self.__pressed = False
        self.__axes.figure.canvas.draw()

    def _on_mouse_move(self, event):
        # logging.info("Mouse moved")
        if event.inaxes == self.__axes and self.__current_ruler is not None:
            x0 = self.__current_ruler.xy[0]
            y0 = self.__current_ruler.xy[1]
            self.__current_ruler.xytext = (event.xdata, event.ydata)
            self.__current_ruler.set_text("%.1f" % oplc.Edge2d(event.xdata, event.ydata, x0, y0).length())
            self.__axes.figure.canvas.draw()


class GetPointAbility(Ability):

    def __init__(self):
        self.__axes = None
        self.__enabled = False
        self.__press_cid = None
        self.__interp = None

    def enable(self, axes):
        if not self.__enabled:
            self.__axes = axes
            self.__press_cid = self.__axes.figure.canvas.mpl_connect("button_press_event", self._on_mouse_press)
            data = self.__axes.images[0].get_array()
            rows, cols = data.shape
            xlim = self.__axes.get_xlim()
            ylim = self.__axes.get_ylim()
            self.__interp = interp2d(x=linspace(xlim[0], xlim[1], cols), y=linspace(ylim[1], ylim[0], rows), z=data)
            self.__enabled = True
        elif self.__axes is not axes:
            self.disable()
            self.enable(axes)

    def disable(self):
        if self.__enabled:
            self.__axes.figure.canvas.mpl_disconnect(self.__press_cid)
            self.__axes = None
            self.__enabled = False

    @property
    def suites(self):
        return [Ability.xz2d]

    def _on_mouse_press(self, event):
        # logging.info("Mouse press event")
        if self.__enabled and event.inaxes == self.__axes and event.button == 1 and event.dblclick:
            z = self.__interp(event.xdata, event.ydata)
            self.__axes.text(event.xdata, event.ydata, "%.3f" % z, fontsize=20, color='crimson')
            self.__axes.plot(event.xdata, event.ydata, "o", color=COMMON_LINES_COLOR)
            logging.info("X = %.2f Y = %.2f Z = %.2f" % (event.xdata, event.ydata, z))
            self.__axes.figure.canvas.draw()


AXES_NAMES_MAPPING = {
    oplc.X_1D: ["X Position (nm)", "Intensity"],
    oplc.Y_1D: ["Y Position (nm)", "Intensity"],
    oplc.XY_2D: ["X Position (nm)", "Y Position (nm)"],
    oplc.XZ_2D: ["X Position (nm)", "Z Position (nm)"],
    oplc.YZ_2D: ["Y Position (nm)", "Z Position (nm)"],
    oplc.XYZ_3D: ["X Position (nm)", "Y Position (nm)", "Z Position (nm)"]
}


class _ResistSimulationsGraphBase(QGraphPlot):

    _extent_coef = 1.2
    _aspect_thresh = 10.0
    _aspect_coef = 2.0
    _abilities_types = []

    def __init__(self, parent, options):
        """
        :type parent: QtGui.QWidget
        :type options: options.structures.Options
        """
        super(_ResistSimulationsGraphBase, self).__init__(parent)
        self.setMinimumSize(600, 600)

        self._options = options

        self.__current_axes = None
        self.__resist_volume = None
        self.__draw_mask = False
        self.__mask_polygons = []

        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

        self._abilities = [cls() for cls in self.__class__._abilities_types]

    def _plot1d(self, x, values, **kwargs):
        raise NotImplementedError("Plot of the 1D resist volume data is not implemented")

    def _plot2dxy(self, x, y, values, **kwargs):
        raise NotImplementedError("Plot of the 2D top view resist volume data is not implemented")

    def _plot2dxz(self, x, z, values, **kwargs):
        raise NotImplementedError("Plot of the 2D cross section view resist volume data is not implemented")

    def _plot3d(self, x, y, z, values, **kwargs):
        raise NotImplementedError("Plot of the 3D resist volume data is not implemented")

    def _plot2d_profile(self, x, z, polygons, **kwargs):
        raise NotImplementedError("Plot of the 2D resist profile data is not implemented")

    def _plot3d_profile(self, x, y, z, polygons, **kwargs):
        raise NotImplementedError("Plot of the 3D resist profile data is not implemented")

    def _enable_abilities(self, axes, suite):
        """:param int suite: One of Ability suite"""
        for ability in self._abilities:
            if suite in ability.suites:
                ability.enable(axes)

    def _disable_abilities(self):
        for ability in self._abilities:
            ability.disable()

    def _draw_resist_volume(self, resist_volume, **kwargs):
        self.__resist_volume = resist_volume
        if resist_volume.has_x and resist_volume.has_y:
            if resist_volume.has_z:
                ax = self._plot3d(resist_volume.x, resist_volume.y, resist_volume.z, resist_volume.values, **kwargs)
                self._enable_abilities(ax, Ability.p3d)
            else:
                ax = self._plot2dxy(resist_volume.x, resist_volume.y, resist_volume.values[:, :, 0], **kwargs)
                self._enable_abilities(ax, Ability.xy2d)
        elif resist_volume.has_x:
            if not resist_volume.has_z:
                ax = self._plot1d(resist_volume.x, resist_volume.values[0, :, 0], **kwargs)
                self._enable_abilities(ax, Ability.p1d)
            else:
                ax = self._plot2dxz(resist_volume.x, resist_volume.z, resist_volume.values[0, :, :], **kwargs)
                self._enable_abilities(ax, Ability.xz2d)
        elif resist_volume.has_y:
            if not resist_volume.has_z:
                ax = self._plot1d(resist_volume.y, resist_volume.values[:, 0, 0], **kwargs)
                self._enable_abilities(ax, Ability.p1d)
            else:
                ax = self._plot2dxz(resist_volume.y, resist_volume.z, resist_volume.values[:, 0, :], **kwargs)
                self._enable_abilities(ax, Ability.xz2d)
        else:
            raise RuntimeError("Can't plot given empty data")
        axes_names = AXES_NAMES_MAPPING[resist_volume.axes]
        ax.set_xlabel(axes_names[0])
        ax.set_ylabel(axes_names[1])
        return ax

    def _draw_resist_profile(self, resist_profile, **kwargs):
        """:type resist_profile: oplc.ResistProfile"""
        if resist_profile.axes == oplc.XYZ_3D:
            ax = self._plot3d_profile(
                resist_profile.x, resist_profile.y,
                resist_profile.z, resist_profile.polygons, **kwargs)
            self._enable_abilities(ax, Ability.p3d)
        elif resist_profile.axes == oplc.XZ_2D:
            ax = self._plot2d_profile(resist_profile.x, resist_profile.z, resist_profile.polygons, **kwargs)
            self._enable_abilities(ax, Ability.p2d)
        elif resist_profile.axes == oplc.YZ_2D:
            ax = self._plot2d_profile(resist_profile.y, resist_profile.z, resist_profile.polygons, **kwargs)
            self._enable_abilities(ax, Ability.p2d)
        else:
            raise RuntimeError("Wrong resist profile data")
        axes_names = AXES_NAMES_MAPPING[resist_profile.axes]
        ax.set_xlabel(axes_names[0])
        ax.set_ylabel(axes_names[1])
        return ax

    def _add_mask(self, axes):
        if axes is None:
            logging.warning("Trying to draw mask on non-existing axes")
            return

        mask = self._options.mask.container
        # Centering mask - that required for diffraction calculation and aerial_image will be centered also in core
        offset = mask.boundary[0] + (mask.boundary[1] - mask.boundary[0]) / 2.0
        """:type: Point"""
        for region in mask.regions:
            xy = [[p.x - offset.x, p.y - offset.y] for p in region.points]
            self.__mask_polygons.append(axes.add_patch(Polygon(xy, alpha=0.25, facecolor="black")))
            self.__mask_polygons.append(axes.add_patch(Polygon(xy, fill=False, edgecolor="crimson", linewidth=1.25)))
        self.__draw_mask = True

    def _clear_mask(self):
        for polygon in self.__mask_polygons:
            polygon.remove()
        self.__mask_polygons = []
        self.__draw_mask = False

    @property
    def draw_mask(self):
        return self.__draw_mask

    @draw_mask.setter
    def draw_mask(self, enabled):
        if not enabled:
            self._clear_mask()
            self.redraw()
        elif self.__resist_volume.axes == oplc.XY_2D:
            self._add_mask(self.__current_axes)
            self.redraw()

    _drawers = {
        oplc.RESIST_VOLUME: _draw_resist_volume,
        oplc.RESIST_PROFILE: _draw_resist_profile
    }

    def draw_graph(self, resist_data, graph_title, **kwargs):
        was_mask_enabled = self.draw_mask
        self._clear_mask()
        self._figure.clear()
        # noinspection PyCallingNonCallable
        self.__current_axes = self._drawers[resist_data.type](self, resist_data, **kwargs)
        self.__current_axes.set_title(graph_title)
        self.__current_axes.grid()
        if was_mask_enabled:
            self._add_mask(self.__current_axes)
        self.redraw()


class _CommonResistSimulationsGraph(_ResistSimulationsGraphBase):

    def _draw_graph_2dxz(self, ax, cb, x, z, values, **kwargs):
        raise NotImplementedError("Class %s has not implemented method" % self.__class__.__name__)

    # noinspection PyUnusedLocal
    def _plot1d(self, x, values, **kwargs):
        ax = self.add_subplot()
        ax.set_ylabel("Intensity")
        ax.plot(x, values, linewidth=3.5, color=COMMON_LINES_COLOR)
        ax.set_xlim(min(x), max(x))
        ax.set_ylim(0.0, max(values) * self._extent_coef)
        ax.set_aspect("auto")
        return ax

    def _plot2dxy(self, x, y, values, **kwargs):
        ax = self.add_subplot()

        ax.set_xlabel("X coordinates (nm)")
        ax.set_ylabel("Y coordinates (nm)")

        ax.set_xlim(left=min(x), right=max(x))
        ax.set_ylim(bottom=min(y), top=max(y))

        level = kwargs.get("level")

        ax.contourf(x, y, values[:, :], colors=RESIST_FILL_COLOR, levels=[0.0, level])
        ax.contour(x, y, values[:, :], colors=RESIST_LINES_COLOR, levels=[0.0, 0.3])

        ax.set_aspect("equal")

        return ax

    @staticmethod
    def _set_scale(ax, left, right, top, bottom):
        aspect = (right - left) / (top - bottom)
        if 1.0/_ResistSimulationsGraphBase._aspect_thresh < aspect < _ResistSimulationsGraphBase._aspect_thresh:
            ax.set_aspect("equal")
        else:
            ax.set_aspect((right - left) / (top - bottom) / _ResistSimulationsGraphBase._aspect_coef)
            ax.set_title(ax.title.get_text() + " (NOT IN SCALE)")

    def _plot2dxz(self, x, z, values, **kwargs):
        # Rotate required because when slices row-slice or col-slice matrix is rotated
        values = rot90(values)

        ax = self.add_subplot(211)
        cb = self.add_subplot(212)

        self._draw_graph_2dxz(ax, cb, x, z, values, **kwargs)

        left, right, bottom, top = min(x), max(x), min(z), max(z)
        ax.set_xlim(left, right)
        ax.set_ylim(bottom, top)

        level = kwargs.get("level")

        negative = contour_sign(self._options.mask.container.background, **kwargs)

        polygons = oplc.contours(asfortranarray(x), asfortranarray(z), asfortranarray(values), level, negative)
        # logging.info("Total contours found: %s" % len(polygons))
        for polygon in polygons:
            # logging.info("Contour: %s" % polygon)
            xy = [[edge.org.x, edge.org.y] for edge in polygon]
            ax.add_patch(Polygon(xy, fill=False, edgecolor=COMMON_LINES_COLOR, linewidth=3.0))

        _CommonResistSimulationsGraph._set_scale(ax, left, right, top, bottom)

        return ax

    def _plot3d(self, x, y, z, values, **kwargs):
        """
        This is only for testing not complete yet!!!
        """
        import numpy
        from matplotlib import cm
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        from matplotlib.tri import Triangulation

        ax = self.add_subplot(projection="3d")
        ax.set_aspect("equal")

        # ax.set_xlabel("X coordinates (nm)")
        # ax.set_ylabel("Y coordinates (nm)")
        # ax.set_zlabel("Z coordinates (nm)")

        level = kwargs.get("level")
        negative = contour_sign(self._options.mask.container.background, **kwargs)
        surface = oplc.isosurface(
            asfortranarray(x), asfortranarray(y), asfortranarray(z[::-1]),
            asfortranarray(values), level, negative)

        # logging.info("X = %s, Y = %s, Z = %s" % (surface.x, surface.y, surface.z))

        # ax.plot_trisurf(
        #     surface.x, surface.y, surface.z,
        #     shade=True, color=RESIST_FILL_COLOR, linewidth=0.1, edgecolor="white")
        #
        # vx = max(x) - min(x)
        # vy = max(y) - min(y)
        # vz = max(z) - min(z)
        # max_v = max(vx, vy, vz)
        # ax.pbaspect = [vx / max_v, vy / max_v, vz / max_v]
        # ax.auto_scale_xyz(x, y, z, True)

        normals = []
        faces = []
        for triangle in surface.triangles:
            face = numpy.asarray([
                (triangle.a.x, triangle.a.y, triangle.a.z),
                (triangle.b.x, triangle.b.y, triangle.b.z),
                (triangle.c.x, triangle.c.y, triangle.c.z)])
            faces.append(face)
            n = triangle.normal()
            normals.append(numpy.asarray([n.x, n.y, n.z]))

        # colset = ax._shade_colors(RESIST_FILL_COLOR, normals)
        polyc = Poly3DCollection(faces, facecolors=RESIST_FILL_COLOR, linewidths=0.01, edgecolors="black")
        # polyc.set_facecolors(colset)
        ax.add_collection(polyc)
        max_x, min_x = max(x), min(x)
        max_y, min_y = max(y), min(y)
        max_z, min_z = max(z), min(z)
        vx = max_x - min_x
        vy = max_y - min_y
        vz = max_z - min_z
        max_v = max(vx, vy, vz)
        ax.pbaspect = [vx / max_v, vy / max_v, vz / max_v]
        ax.auto_scale_xyz([min_x, max_x], [min_y, max_y], [min_z, max_z], True)

        return ax


class ImageResistSimulationsGraph(_CommonResistSimulationsGraph):

    _abilities_types = [RulerAbility, GetPointAbility]

    def _draw_graph_2dxz(self, ax, cb, x, z, values, **kwargs):
        title = kwargs.get("title")
        left, right, bottom, top = min(x), max(x), min(z), max(z)
        img = ax.imshow(
            values, cmap=ProlithColormap, interpolation='nearest',
            extent=[left, right, bottom, top], vmin=values.min(), vmax=values.max())
        ticks = round(linspace(start=float(values.min()), stop=float(values.max()), num=10), 4)
        self._figure.colorbar(img, cax=cb, ticks=ticks, orientation='horizontal')
        cb.set_aspect(0.05)
        cb.set_title(title)


class ContourResistSimulationsGraph(_CommonResistSimulationsGraph):

    _abilities_types = []
    _max_time = 20000.0

    @staticmethod
    def _levels(values, development):
        base = development.develop_time.value / 8.0
        levels = 2 ** arange(0, 9) * base
        """:type: numpy.multiarray.ndarray"""
        levels[0] = 0.0
        levels[-1] = max(ContourResistSimulationsGraph._max_time, values.max(), levels.max())
        return round(levels, 3)

    def _draw_graph_2dxz(self, ax, cb, x, z, values, **kwargs):
        title = kwargs.get("title")
        levels = self._levels(values, self._options.development)
        boundary_norm = BoundaryNorm(levels, ProlithColormap.N)
        img = ax.contourf(x, z, values, cmap=ProlithColormap, levels=levels, norm=boundary_norm)
        ax.contour(x, z, values, colors=RESIST_CONTOUR_COLOR, levels=levels)
        self._figure.colorbar(img, cax=cb, ticks=levels, orientation='horizontal')
        cb.set_aspect(0.05)
        cb.set_title(title)


class ProfileResistSimulationsGraph(_CommonResistSimulationsGraph):

    _abilities_types = [RulerAbility]

    def _plot2d_profile(self, x, z, polygons, **kwargs):
        ax = self.add_subplot()

        left, right, bottom, top = min(x), max(x), min(z), max(z)
        ax.set_xlim(left, right)
        ax.set_ylim(bottom, top)

        # logging.info("Total contours found: %s" % len(polygons))
        for polygon in polygons:
            # logging.info("Contour: %s" % polygon)
            xy = [[edge.org.x, edge.org.y] for edge in polygon]
            ax.add_patch(Polygon(xy, facecolor=RESIST_FILL_COLOR, edgecolor=RESIST_LINES_COLOR, linewidth=3.0))

        # Test of angle determination
        # from numpy import isnan
        # from metrics import _calculate_lstsq_v2
        # from matplotlib.lines import Line2D
        # a_b = _calculate_lstsq_v2(polygons)
        # if isinstance(a_b, tuple):
        #     a, b = a_b
        #     f = lambda x: a*x+b
        #     x = [f(bottom), f(top)]
        #     y = [bottom, top]
        #     logging.info("x = %s, y = %s" % (x, y))
        #     ax.add_line(Line2D(x, y, lw=5., color='r'))

        _CommonResistSimulationsGraph._set_scale(ax, left, right, top, bottom)

        return ax


# noinspection PyPep8Naming
def SimulationViewsFactory(graph_class):

    class _AbstractSimulationsView(QStackWidgetTab):

        _graph_class = None

        def __init__(self, parent, stage, options):
            """
            :param QtGui.QWidget parent: Resist simulation view widget parent
            """
            super(_AbstractSimulationsView, self).__init__(parent)

            self.__options = options
            self.__stage = stage

            self.__metrology_label = QtGui.QLabel("Metrology results:", self)

            self._parameters = QMetrologyTable(self, stage.metrics)

            self.__x_axis_label = QtGui.QLabel("X Axis:", self)
            self._x_axis_edit = QtGui.QLineEdit(self)
            self._x_axis_edit.setEnabled(False)
            self._x_axis_edit.setFixedWidth(self._parameters.width())

            self.__y_axis_label = QtGui.QLabel("Y Axis:", self)
            self._y_axis_edit = QtGui.QLineEdit(self)
            self._y_axis_edit.setEnabled(False)
            self._y_axis_edit.setFixedWidth(self._parameters.width())

            self._draw_mask_chkbox = QtGui.QCheckBox("Draw original mask", self)
            connect(self._draw_mask_chkbox.toggled, self.on_draw_mask_chkbox_toggled)
            self._draw_mask_chkbox.setChecked(False)

            self.__parameters_layout = QtGui.QVBoxLayout()
            self.__parameters_layout.addWidget(self.__x_axis_label)
            self.__parameters_layout.addWidget(self._x_axis_edit)
            self.__parameters_layout.addSpacing(10)
            self.__parameters_layout.addWidget(self.__y_axis_label)
            self.__parameters_layout.addWidget(self._y_axis_edit)
            self.__parameters_layout.addSpacing(30)
            self.__parameters_layout.addWidget(self.__metrology_label)
            self.__parameters_layout.addWidget(self._parameters)
            self.__parameters_layout.addWidget(self._draw_mask_chkbox)
            self.__parameters_layout.addStretch()

            self._graph = graph_class(self, options)
            self._toolbar = NavigationToolbar(self._graph, self)

            self.__graph_layout = QtGui.QVBoxLayout()
            # self.__graph_layout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
            self.__graph_layout.addWidget(self._toolbar)
            self.__graph_layout.addWidget(self._graph)
            self.__graph_layout.addStretch()

            self.__layout = QtGui.QHBoxLayout(self)
            self.__layout.addLayout(self.__parameters_layout)
            self.__layout.addLayout(self.__graph_layout)

        @property
        def options(self):
            return self.__options

        @Slot(bool)
        def on_draw_mask_chkbox_toggled(self, state):
            self._graph.draw_mask = state

        @show_traceback
        def onSetActive(self):
            data = self.__stage.calculate()
            axes_names = AXES_NAMES_MAPPING[data.axes]
            self._x_axis_edit.setText(axes_names[0])
            self._y_axis_edit.setText(axes_names[1])
            self._draw_mask_chkbox.setEnabled(data.axes == oplc.XY_2D)
            self._graph.draw_graph(data, self.__stage.name, **self.__stage.metrics_kwargs)
            self._parameters.setObject(data, **self.__stage.metrics_kwargs)

    return _AbstractSimulationsView


_ImageViewClass = SimulationViewsFactory(ImageResistSimulationsGraph)
_ContourViewClass = SimulationViewsFactory(ContourResistSimulationsGraph)
_ProfileViewClass = SimulationViewsFactory(ProfileResistSimulationsGraph)


AerialImageView = ImageInResistView = LatentImageView = PebLatentImageView = _ImageViewClass
DevelopContoursView = _ContourViewClass
ResistProfileView = _ProfileViewClass