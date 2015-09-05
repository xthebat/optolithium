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
import psutil

from qt import QtGui, QtCore, connect, Slot
from views.common import QStackWidgetTab, QFramedLabel, QSliderNumeric, QLineEditNumeric, QComboBoxEnum

from config import MEGABYTE
from options.structures import Abstract, Numeric, Variable

import config
import helpers


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


class SourceGridView(QtGui.QGroupBox):
    def __init__(self, numerics, parent):
        """
        :param options.Numerics numerics: Programs options
        :param QtGui.QWidget parent: View parent
        """
        QtGui.QGroupBox.__init__(self, "Source Grid", parent)
        self._slow_label = QtGui.QLabel("Slower,\nMore Accurate")
        self._slow_label.setAlignment(QtCore.Qt.AlignCenter)
        self._fast_label = QtGui.QLabel("Faster,\nLess Accurate")
        self._fast_label.setAlignment(QtCore.Qt.AlignCenter)
        self._factor_label = QtGui.QLabel("Speed Factor")
        self._factor_label_slider = QFramedLabel(self, numerics.speed_factor)
        self._factor_slider = QSliderNumeric(self, numerics.speed_factor, orientation=QtCore.Qt.Horizontal)
        self._grid_layout = QtGui.QGridLayout(self)
        self._grid_layout.addWidget(self._slow_label, 0, 2, 1, 2)
        self._grid_layout.addWidget(self._fast_label, 0, 8, 1, 2)
        self._grid_layout.addWidget(self._factor_label, 1, 1)
        self._grid_layout.addWidget(self._factor_label_slider, 1, 2)
        self._grid_layout.addWidget(self._factor_slider, 1, 3, 1, 8)


class TargetGridView(QtGui.QGroupBox):
    def __init__(self, numerics, parent):
        """
        :param options.Numerics numerics: Programs options
        :param QtGui.QWidget parent: View parent
        """
        QtGui.QGroupBox.__init__(self, "Target Grid Sizes", parent)

        self._xy_edit = QLineEditNumeric(self, numerics.grid_xy)
        self._xy_edit.setMaximumWidth(60)
        self._xy_edit.setAlignment(QtCore.Qt.AlignRight)
        self._z_edit = QLineEditNumeric(self, numerics.grid_z)
        self._z_edit.setMaximumWidth(60)
        self._z_edit.setAlignment(QtCore.Qt.AlignRight)
        self.__form_layout = QtGui.QFormLayout(self)
        self.__form_layout.addRow("X/Y (nm):", self._xy_edit)
        self.__form_layout.addRow("Z (nm):", self._z_edit)


class SystemMemoryView(QtGui.QGroupBox):

    double_precision = 8
    stages_count = 4

    class GridLayout(QtGui.QGridLayout):
        def __init__(self, *args, **kwargs):
            super(SystemMemoryView.GridLayout, self).__init__(*args, **kwargs)
            self.__current_row = 0

        # noinspection PyPep8Naming
        def addRow(self, name, widget):
            self.addWidget(QtGui.QLabel(name), self.__current_row, 0)
            self.addWidget(widget, self.__current_row, 1)
            self.__current_row += 1

    def __init__(self, numerics, mask, resist, parent):
        """
        :param options.structures.Numerics numerics: Mask steps and source steps
        :param options.structures.Mask mask: Mask required to get X/Y dimensions to calculate memory consumption
        :param options.structures.Resist resist: Resist required to get thickness for Z direction
        :param QtGui.QWidget parent: View parent
        """
        fmt = QFramedLabel.memory_format

        QtGui.QGroupBox.__init__(self, "System memory state", parent)

        self.__mask = mask
        self.__resist = resist
        self.__numerics = numerics

        connect(self.__numerics.grid_xy.signals[Abstract], self.__grid_updated)
        connect(self.__numerics.grid_z.signals[Abstract], self.__grid_updated)
        connect(self.__numerics.speed_factor.signals[Abstract], self.__speed_factor_updated)

        usage = psutil.phymem_usage()
        mem_ai_required = self.__calc_required_memory_ai()
        mem_3d_required = self.__calc_required_memory_3d()
        self.__mem_used = Variable(Numeric(dtype=float), value=float(usage.used), name="UsedMemory")
        self.__mem_free = Variable(Numeric(dtype=float), value=float(usage.free), name="FreeMemory")
        self.__mem_total = Variable(Numeric(dtype=float), value=float(usage.total), name="TotalMemory")
        self.__mem_ai_required = Variable(Numeric(dtype=float), value=mem_ai_required, name="RequiredAIMemory")
        self.__mem_3d_required = Variable(Numeric(dtype=float), value=mem_3d_required, name="Required3DMemory")

        self.__source_shape_grid = Variable(
            Numeric(dtype=float), value=float(numerics.source_stepxy), name="SourceShapeGrid")

        self.__info_layout = SystemMemoryView.GridLayout()
        self.__info_layout.addRow("Virtual memory used:", QFramedLabel(self, self.__mem_used, frmt=fmt))
        self.__info_layout.addRow("Memory available:", QFramedLabel(self, self.__mem_free, frmt=fmt))
        self.__info_layout.addRow("Memory total:", QFramedLabel(self, self.__mem_total, frmt=fmt))
        self.__info_layout.addRow("Aerial image memory req.:", QFramedLabel(self, self.__mem_ai_required, frmt=fmt))
        self.__info_layout.addRow("Resist 2D/3D memory req.:", QFramedLabel(self, self.__mem_3d_required, frmt=fmt))
        self.__info_layout.addRow("Source shape grid:", QFramedLabel(self, self.__source_shape_grid, frmt="%.03f um"))

        self.__layout = QtGui.QVBoxLayout(self)
        self.__layout.addLayout(self.__info_layout)
        self.__layout.addStretch()

        self.__mem_update_timer = QtCore.QTimer(self)
        connect(self.__mem_update_timer.timeout, self.__update_memory)
        self.__mem_update_timer.start(config.Configuration.memory_update_interval)

        self.__grid_updated()

    # noinspection PyPep8Naming
    def setObject(self, options):
        self.__mask = options.mask
        self.__resist = options.wafer_process.resist
        self.__grid_updated()

    @Slot()
    def __speed_factor_updated(self):
        self.__source_shape_grid.value = self.__numerics.source_stepxy

    @Slot()
    def __grid_updated(self):
        self.__update_memory()
        self.__mem_ai_required.value = self.__calc_required_memory_ai()
        self.__mem_3d_required.value = self.__calc_required_memory_3d()

    def __calc_required_memory_ai(self):
        # return 8 * (1000.0/self.__numerics.grid_xy.value)**2 * (1000.0/self.__numerics.grid_z.value)
        sizes = self.__mask.container.boundary[1] - self.__mask.container.boundary[0]

        vx = (sizes.x / self.__numerics.grid_xy.value + 1.0) if sizes.x != 0.0 else 1.0
        vy = (sizes.y / self.__numerics.grid_xy.value + 1.0) if sizes.y != 0.0 else 1.0

        return self.double_precision * vx * vy

    def __calc_required_memory_3d(self):
        # return 8 * (1000.0/self.__numerics.grid_xy.value)**2 * (1000.0/self.__numerics.grid_z.value)
        vz = self.__resist.thickness / self.__numerics.grid_z.value + 1.0
        return self.stages_count * self.__calc_required_memory_ai() * vz

    @Slot()
    def __update_memory(self):
        usage = psutil.virtual_memory()
        self.__mem_used.value = float(usage.used)
        self.__mem_free.value = float(usage.available)
        self.__mem_total.value = float(usage.total)


class NumericsView(QStackWidgetTab):

    def __init__(self, parent, options):
        """
        :type parent: QtGui.QWidget
        :param options.structures.Options options: Programs options
        """
        QStackWidgetTab.__init__(self, parent)

        self.__options = options

        self.__calc_mode_combobox = QComboBoxEnum(self, self.__options.numerics.calculation_model)
        # TODO: Add vector model
        self.__calc_mode_combobox.setEnabled(False)

        self.__form_layout = QtGui.QFormLayout()
        self.__form_layout.addRow("Image calculation mode:", self.__calc_mode_combobox)

        self.__source_grid_groupbox = SourceGridView(self.__options.numerics, self)
        self.__target_grid_groupbox = TargetGridView(self.__options.numerics, self)
        self.__system_memory_groupbox = SystemMemoryView(
            self.__options.numerics, self.__options.mask, self.__options.wafer_process.resist, self)

        self.__grid_layout = QtGui.QGridLayout()
        self.__grid_layout.addLayout(self.__form_layout, 0, 0)
        self.__grid_layout.addWidget(self.__source_grid_groupbox, 1, 0)
        self.__grid_layout.addWidget(self.__target_grid_groupbox, 2, 0)
        self.__grid_layout.addWidget(self.__system_memory_groupbox, 1, 1, 2, 1)

        self.setUnstretchable(self.__grid_layout)

    def onSetActive(self):
        self.__system_memory_groupbox.setObject(self.__options)

    def reset(self):
        self.__system_memory_groupbox.setObject(self.__options)