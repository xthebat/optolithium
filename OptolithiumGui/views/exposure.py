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

from matplotlib.patches import Rectangle

from qt import QtGui, connect, Slot
from views.common import QStackWidgetTab, QLineEditNumeric, QComboBoxEnum, QGraphPlot
from options.structures import Abstract

import helpers
import config


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


class ExposureDoseBox(QtGui.QGroupBox):
    def __init__(self, parent, exposure_focus):
        """
        :type parent: QtGui.QWidget
        :type exposure_focus: options.structures.ExposureFocus
        """
        QtGui.QGroupBox.__init__(self, "Exposure Dose", parent)

        self.__exposure_focus = exposure_focus
        self.__dose_edit = QLineEditNumeric(self, self.__exposure_focus.exposure)

        self.__hlayout = QtGui.QHBoxLayout()
        self.__hlayout.addStretch()
        self.__hlayout.addWidget(QtGui.QLabel("Exposure Energy (mJ/cm2):"))
        self.__hlayout.addWidget(self.__dose_edit)

        self.__layout = QtGui.QVBoxLayout(self)
        self.__layout.addLayout(self.__hlayout)
        # self.__layout.addStretch()


class DoseCalibrationBox(QtGui.QGroupBox):
    def __init__(self, parent, exposure_focus):
        """
        :type parent: QtGui.QWidget
        :type exposure_focus: options.structures.ExposureFocus
        """
        QtGui.QGroupBox.__init__(self, "Dose Calibration", parent)
        self.__exposure_focus = exposure_focus
        self.__correctable_edit = QLineEditNumeric(self, self.__exposure_focus.dose_correctable)

        self.__hlayout = QtGui.QHBoxLayout()
        self.__hlayout.addStretch()
        self.__hlayout.addWidget(QtGui.QLabel("Dose correctable (mJ/cm2):"))
        self.__hlayout.addWidget(self.__correctable_edit)

        self.__layout = QtGui.QVBoxLayout(self)
        self.__label = QtGui.QLabel("Note: Stepper's dose meter located at the mask side")
        self.__layout.addWidget(self.__label)
        self.__layout.addLayout(self.__hlayout)
        # self.__layout.addStretch()


class WaferFocus(QtGui.QGroupBox):
    def __init__(self, parent, exposure_focus):
        """
        :type parent: QtGui.QWidget
        :type exposure_focus: options.structures.ExposureFocus
        """
        QtGui.QGroupBox.__init__(self, "Wafer Focus", parent)
        self.__exposure_focus = exposure_focus
        self.__position_edit = QLineEditNumeric(self, self.__exposure_focus.focus)
        self.__relative_combo = QComboBoxEnum(self, self.__exposure_focus.focal_relative_to)
        self.__direction_combo = QComboBoxEnum(self, self.__exposure_focus.focal_direction)

        self.__pos_layout = QtGui.QHBoxLayout()
        self.__pos_layout.addStretch()
        self.__pos_layout.addWidget(QtGui.QLabel("Focal Position (microns):"))
        self.__pos_layout.addWidget(self.__position_edit)

        self.__rel_layout = QtGui.QHBoxLayout()
        self.__rel_layout.addStretch()
        self.__rel_layout.addWidget(QtGui.QLabel("Position is relative to "))
        self.__rel_layout.addWidget(self.__relative_combo)
        self.__rel_layout.addWidget(QtGui.QLabel(" of resist"))

        self.__dir_layout = QtGui.QHBoxLayout()
        self.__dir_layout.addStretch()
        self.__dir_layout.addWidget(QtGui.QLabel("Positive numbers move the Focal Position "))
        self.__dir_layout.addWidget(self.__direction_combo)

        self.__layout = QtGui.QVBoxLayout(self)
        self.__layout.addLayout(self.__pos_layout)
        self.__layout.addLayout(self.__rel_layout)
        self.__layout.addLayout(self.__dir_layout)
        # self.__layout.addStretch()


class FocusGraph(QGraphPlot):

    def __init__(self, parent, exposure_focus, wafer_stack):
        """
        :type parent: QtGui.QWidget
        :type exposure_focus: options.structures.ExposureFocus
        :type wafer_stack: options.structures.WaferProcess
        """
        QGraphPlot.__init__(self, parent, width=320, height=400)
        self.__exposure_focus = exposure_focus
        self.__wafer_stack = wafer_stack
        self._ax = self.add_subplot()
        connect(self.__exposure_focus.focus.signals[Abstract], self.update_graph)
        connect(self.__exposure_focus.focal_direction.signals[Abstract], self.update_graph)
        connect(self.__exposure_focus.focal_relative_to.signals[Abstract], self.update_graph)

    def draw_graph(self, focus, relative_to, direction, thickness):
        """
        :type focus: float
        :type relative_to: float
        :type direction: float
        :type thickness: float
        """
        top_focus = self.__exposure_focus.focal_plane
        bottom_focus = thickness - top_focus
        max_y = max(thickness, bottom_focus) + thickness/5.0
        min_y = min(0.0, thickness, bottom_focus) - thickness/5.0

        self._ax.clear()

        self._ax.set_xlim(0.0, 1.0)
        self._ax.set_ylim(min_y, max_y)

        self._ax.add_patch(Rectangle([0.2, 0.0], 0.4, thickness, facecolor=config.RESIST_FILL_COLOR))
        self._ax.add_patch(Rectangle([0.0, min_y], 1.0, abs(min_y), color='b', linewidth=0, fill=None, hatch="///"))
        self._ax.plot([0.1, 0.7], [bottom_focus, bottom_focus], color='k', linestyle='-', linewidth=2)

        logging.debug("Focus: %s, relative: %s, direction: %s, thickness: %s -> top: %s, bottom: %s" %
                      (focus, relative_to, direction, thickness, top_focus, bottom_focus))

        self._ax.grid()

        self._ax.set_title("Relative Wafer Focal Position")
        self._ax.get_xaxis().set_visible(False)
        self._ax.patch.set_alpha(0.0)

        self.redraw()

    @Slot()
    def update_graph(self):
        self.draw_graph(
            self.__exposure_focus.focus.value,
            self.__exposure_focus.focal_relative_to.value,
            self.__exposure_focus.focal_direction.value,
            self.__wafer_stack.resist.thickness)


class ExposureFocusView(QStackWidgetTab):

    def __init__(self, parent, exposure_focus, wafer_stack):
        """
        :param QtGui.QWidget parent: Exposure and focus view widget parent
        :param options.structures.ExposureFocus exposure_focus: Exposure and focus options parameters
        :param options.structures.WaferProcess wafer_stack: Wafer stack
        """
        QStackWidgetTab.__init__(self, parent)

        self.__exposure = ExposureDoseBox(self, exposure_focus)
        self.__calibration = DoseCalibrationBox(self, exposure_focus)
        self.__focus = WaferFocus(self, exposure_focus)
        self.__focus_graph = FocusGraph(self, exposure_focus, wafer_stack)

        self.__layout = QtGui.QVBoxLayout()
        self.__layout.addWidget(self.__exposure)
        self.__layout.addWidget(self.__calibration)
        self.__layout.addSpacing(10)
        self.__layout.addWidget(self.__focus)
        self.__layout.addStretch()

        self.__graph_layout = QtGui.QVBoxLayout()
        self.__graph_layout.addWidget(self.__focus_graph)
        self.__graph_layout.addStretch()

        self.__hlayout = QtGui.QHBoxLayout(self)
        self.__hlayout.addLayout(self.__layout)
        self.__hlayout.addSpacing(10)
        self.__hlayout.addLayout(self.__graph_layout)
        self.__hlayout.addStretch()

    def onSetActive(self):
        self.__focus_graph.update_graph()
