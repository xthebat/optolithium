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

import numpy
import logging as module_logging
from matplotlib.patches import Circle
from scipy import interpolate

from qt import QtGui, connect, Slot
from views.common import QStackWidgetTab, QGraphPlot, ProlithColormap, show_traceback

import helpers
from auxmath import middle, cartesian


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.DEBUG)
helpers.logStreamEnable(logging)


class DiffractionPatternGraph(QGraphPlot):

    _extent_coef = 1.2
    _continuous_threshold = 75

    ABS = 0
    PHASE = 1

    type_map = {
        ABS: "Diffraction Pattern Amplitude",
        PHASE: "Diffraction Pattern Phase"
    }

    _inverse_map = {v: k for k, v in type_map.items()}

    type_handlers = {
        ABS: numpy.abs,
        PHASE: lambda z: numpy.angle(z, deg=True)
    }

    @staticmethod
    def type_by_name(name):
        return DiffractionPatternGraph._inverse_map[name]

    @staticmethod
    def _calculate_graphs_bbox(main_size, left, right, top, bottom, hgap, vgap):
        main_bbox = [left, bottom, main_size, main_size]

        bottom_xplot = bottom + main_size + vgap
        xplot_height = 1.0 - bottom_xplot - top
        xplot_bbox = [left, bottom_xplot, main_size, xplot_height]

        left_yplot = left + main_size + hgap
        yplot_width = 1.0 - left_yplot - right
        yplot_bbox = [left_yplot, bottom, yplot_width, main_size]

        return main_bbox, xplot_bbox, yplot_bbox

    def __init__(self, parent, options):
        """:type parent: QtGui.QWidget"""
        super(DiffractionPatternGraph, self).__init__(parent)
        self.setMinimumSize(600, 600)

        self._options = options

        self._pattern = None
        self._x0 = None
        self._y0 = None
        self._current_x = 0
        self._current_y = 0
        self._output_type = DiffractionPatternGraph.ABS
        self._draw_zero_term = True
        self._block_redraw = False

        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

        main_bbox, xplot_bbox, yplot_bbox = self._calculate_graphs_bbox(
            main_size=0.6, left=0.10, right=0.01, top=0.01, bottom=0.10, hgap=0.05, vgap=0.05)

        self._axis_main = self._figure.add_axes(main_bbox, frameon=True)
        self._axis_xplot = self._figure.add_axes(xplot_bbox, frameon=True)
        self._axis_yplot = self._figure.add_axes(yplot_bbox, frameon=True)

    def resizeEvent(self, event=None):
        # Require to fix square aspect ration of the figure.
        # Because matplotlib can only set aspect ratio only for axes not for full figure
        if isinstance(event, QtGui.QResizeEvent) and event.size().height() != event.size().width():
            width = event.size().width()
            height = event.size().height()
            if width < height:
                height = width
            else:
                width = height
            self.resize(height, width)
        else:
            super(DiffractionPatternGraph, self).resizeEvent(event)

    def redraw(self):
        # Disable tight_layout because here a custom multi-component plot
        if self._figure.get_axes():
            self.draw()

    def draw_graph(self):
        if self._block_redraw:
            return
        self._update_main(redraw=False)
        self._update_xplot(redraw=False)
        self._update_yplot(redraw=False)
        self.redraw()

    def block_redraw(self, value):
        self._block_redraw = value

    @property
    def pattern(self):
        return self._pattern

    @pattern.setter
    def pattern(self, value):
        self._pattern = value
        self._x0 = middle(self._pattern.frqx)
        self._y0 = middle(self._pattern.frqy)
        self.draw_graph()

    @property
    def current_x(self):
        return self._current_x

    @current_x.setter
    def current_x(self, indx):
        self._current_x = indx
        # When we change x index then Y-PLOT will update
        self._update_yplot()

    @property
    def current_y(self):
        return self._current_y

    @current_y.setter
    def current_y(self, indx):
        self._current_y = indx
        # When we change y index then X-PLOT will update
        self._update_xplot()

    @property
    def output_type(self):
        return self._output_type

    @output_type.setter
    def output_type(self, value):
        self._output_type = value
        self.draw_graph()

    @property
    def draw_zero_term(self):
        return self._draw_zero_term

    @draw_zero_term.setter
    def draw_zero_term(self, value):
        self._draw_zero_term = value
        self.draw_graph()

    def _update_main(self, redraw=True):
        if self._block_redraw:
            return

        self._axis_main.clear()

        output_handler = self.type_handlers[self.output_type]

        na = self._options.imaging_tool.numerical_aperture.value
        wvl = self._options.imaging_tool.wavelength.value

        vlim = self._extent_coef * na

        if self._pattern.frqx.size < self._continuous_threshold and \
           self._pattern.frqy.size < self._continuous_threshold:
            # Discrete data
            xy = cartesian(wvl*self.pattern.frqy, wvl*self.pattern.frqx)
            cy, cx = xy[:, 1], xy[:, 0]
            v = output_handler(self.pattern.values)

            if not self._draw_zero_term:
                v[self._y0, self._x0] = "nan"

            # Remove points outer the objective
            # ym, xm = numpy.meshgrid(wvl*self.pattern.frqy, wvl*self.pattern.frqx)
            # v[(xm**2 + ym**2) > na*na] = "nan"
            v[self._pattern.cxy > na] = "nan"

            # TODO: Set to nan value outer the circle...
            self._axis_main.scatter(cy, cx, c=v, cmap=ProlithColormap, s=75, zorder=1)

            self._axis_main.grid()
        else:
            # Continuous data
            xi = yi = numpy.linspace(-na, na, 101)
            lookup_table = interpolate.interp1d(xi, xrange(len(xi)), kind="nearest")

            cols = lookup_table(wvl*self.pattern.frqx)
            rows = lookup_table(wvl*self.pattern.frqy)
            data = numpy.zeros([len(xi), len(yi)], dtype=float)
            for k, (row, col) in enumerate(cartesian(rows, cols)):
                data[row, col] = output_handler(self.pattern.values.item(k))

            # Cut elements that not in pupil (can't use direction cosines matrix because data was upsampled)
            xm, ym = numpy.meshgrid(xi, yi)
            data[(xm**2 + ym**2) > na*na] = "nan"
            # self._axis_main.contour(xi, yi, data, cmap=ProlithColormap)
            image = self._axis_main.imshow(data, cmap=ProlithColormap, zorder=1)
            image.set_extent([-na, na, -na, na])

        circle = Circle(xy=[0.0, 0.0], radius=na, edgecolor="k", facecolor="#DDDDDD", linewidth=4, zorder=0)
        self._axis_main.add_patch(circle)

        self._axis_main.set_xlim(-vlim, vlim)
        self._axis_main.set_ylim(-vlim, vlim)

        self._axis_main.set_xlabel("X Pupil Position")
        self._axis_main.set_ylabel("Y Pupil Position")

        self._axis_main.patch.set_alpha(0.0)

        if redraw:
            self.redraw()

    def _update_xplot(self, redraw=True):
        if self._block_redraw:
            return

        self._axis_xplot.clear()

        na = self._options.imaging_tool.numerical_aperture.value

        output_handler = self.type_handlers[self.output_type]

        values = output_handler(self.pattern.values[self._y0 + self.current_y, :])
        values[abs(self.pattern.cx) > na] = "nan"

        if self._pattern.frqx.size < self._continuous_threshold:
            # Discrete data

            if not self._draw_zero_term and self._pattern.frqx.size != 1:
                values[self._x0] = "nan"

            markerline, stemlines, _ = self._axis_xplot.stem(self.pattern.cx, values, "k-", markerfmt="k^")
            markerline.set_markersize(10)
            for k, item in enumerate(stemlines):
                item.set_linewidth(2)
        else:
            # Continuous data
            self._axis_xplot.plot(self.pattern.cx, values, "k-", linewidth=2)

        vlim = self._extent_coef * na
        self._axis_xplot.set_xlim(-vlim, vlim)

        if self.output_type == DiffractionPatternGraph.ABS:
            self._axis_xplot.set_ylim(0.0, numpy.nanmax(values)*self._extent_coef)
        elif self.output_type == DiffractionPatternGraph.PHASE:
            self._axis_xplot.set_yticks(numpy.arange(-180.0, 240.0, 60.0))
            self._axis_xplot.set_ylim(-210.0, 210.0)
        else:
            raise RuntimeError("Unknown output type diffraction pattern type")

        self._axis_xplot.patch.set_alpha(0.0)

        if redraw:
            self.redraw()

    def _update_yplot(self, redraw=True):
        if self._block_redraw:
            return

        def swap(line2d):
            xdata = line2d.get_xdata()
            ydata = line2d.get_ydata()
            line2d.set_xdata(ydata)
            line2d.set_ydata(xdata)

        self._axis_yplot.clear()

        na = self._options.imaging_tool.numerical_aperture.value

        output_handler = self.type_handlers[self.output_type]

        values = output_handler(self.pattern.values[:, self._x0 + self.current_x])
        values[abs(self.pattern.cy) > na] = "nan"

        vlim = self._extent_coef * self._options.imaging_tool.numerical_aperture.value

        if self._pattern.frqy.size < self._continuous_threshold:
            # Discrete data

            if not self._draw_zero_term and self._pattern.frqy.size != 1:
                values[self._y0] = "nan"

            markerline, stemlines, baseline = self._axis_yplot.stem(self.pattern.cy, values, 'k-', markerfmt="k>")
            swap(markerline)
            swap(baseline)
            markerline.set_markersize(10)
            for k, item in enumerate(stemlines):
                swap(item)
                item.set_linewidth(2)
            self._axis_yplot.set_xlim(*self._axis_yplot.get_ylim())
        else:
            # Continuous data
            self._axis_yplot.plot(values, self.pattern.cy, "k-", linewidth=2)

        self._axis_yplot.set_ylim(-vlim, vlim)
        if self.output_type == DiffractionPatternGraph.ABS:
            vmax = numpy.nanmax(values)*self._extent_coef
            self._axis_yplot.set_xlim(0.0, vmax if vmax != 0.0 else 0.1)
        elif self.output_type == DiffractionPatternGraph.PHASE:
            self._axis_yplot.set_xticks(numpy.arange(-180.0, 240.0, 60.0))
            self._axis_yplot.set_xlim(-210.0, 210.0)
        else:
            raise RuntimeError("Unknown output type diffraction pattern type")

        for label in self._axis_yplot.get_xticklabels():
            label.set_rotation(270.0)

        self._axis_yplot.patch.set_alpha(0.0)

        if redraw:
            self.redraw()


class DiffractionPatternView(QStackWidgetTab):

    def __init__(self, parent, simulation):
        """
        :param QtGui.QWidget parent: Diffraction pattern view widget parent
        :param core.Core simulation: Simulation Core
        """
        super(DiffractionPatternView, self).__init__(parent)
        self.__simulation = simulation

        self.__type_label = QtGui.QLabel("Display:", self)
        self.__type_combo = QtGui.QComboBox(self)
        for type_index in sorted(DiffractionPatternGraph.type_map):
            self.__type_combo.addItem(DiffractionPatternGraph.type_map[type_index])
        self.__show_zero_chkbox = QtGui.QCheckBox("Draw (0, 0) order term", self)
        self.__show_zero_chkbox.setChecked(True)
        self.__kx_spinbox = QtGui.QSpinBox(self)
        self.__kx_spinbox.setFixedWidth(80)
        self.__ky_spinbox = QtGui.QSpinBox(self)
        self.__ky_spinbox.setFixedWidth(80)

        self.__graph = DiffractionPatternGraph(self, simulation.options)

        self.__options_layout = QtGui.QVBoxLayout()
        self.__options_layout.addWidget(self.__type_label)
        self.__options_layout.addWidget(self.__type_combo)

        self.__options_layout.addSpacing(15)

        self.__options_layout.addWidget(self.__show_zero_chkbox)

        self.__options_layout.addSpacing(15)

        self.__kxy_layout = QtGui.QFormLayout()
        self.__kxy_layout.addRow("X-Axis at:", self.__kx_spinbox)
        self.__kxy_layout.addRow("Y-Axis at:", self.__ky_spinbox)
        self.__options_layout.addLayout(self.__kxy_layout)

        self.__options_layout.addStretch()

        self.__graph_layout = QtGui.QVBoxLayout()
        self.__graph_layout.addWidget(self.__graph)

        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.addLayout(self.__options_layout)
        self.__layout.addLayout(self.__graph_layout)

        connect(self.__type_combo.currentIndexChanged, self.on_combobox_changed)
        connect(self.__show_zero_chkbox.stateChanged, self.on_chkbox_toggled)
        connect(self.__kx_spinbox.valueChanged, self.on_kx_spin_changed)
        connect(self.__ky_spinbox.valueChanged, self.on_ky_spin_changed)

    @Slot(int)
    def on_combobox_changed(self, indx):
        self.__graph.output_type = indx

    @Slot(bool)
    def on_chkbox_toggled(self, state):
        self.__graph.draw_zero_term = state

    @Slot(int)
    def on_kx_spin_changed(self, value):
        self.__graph.current_x = value

    @Slot(int)
    def on_ky_spin_changed(self, value):
        self.__graph.current_y = value

    @show_traceback
    def onSetActive(self):
        pattern = self.__simulation.diffraction.calculate()

        self.__graph.block_redraw(True)

        self.__kx_spinbox.setRange(numpy.min(pattern.kx), numpy.max(pattern.kx))
        self.__ky_spinbox.setRange(numpy.min(pattern.ky), numpy.max(pattern.ky))
        self.__kx_spinbox.setValue(0)
        self.__ky_spinbox.setValue(0)
        self.__type_combo.setCurrentIndex(DiffractionPatternGraph.ABS)
        self.__graph.pattern = pattern

        self.__graph.block_redraw(False)
        self.__graph.draw_graph()
