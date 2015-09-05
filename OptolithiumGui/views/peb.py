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

from qt import connect, disconnect, Slot, QtGui
from views.common import QStackWidgetTab, QLabel, QLineEditNumeric, QGraphPlot
from database import orm
from options import Abstract
from resources import Resources

import config
import helpers


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.DEBUG)
helpers.logStreamEnable(logging)


class TemperatureProfileGraph(QGraphPlot):

    def __init__(self, parent, peb=None):
        """
        :type parent: QtGui.QWidget
        :type peb: options.PostExposureBake
        """
        super(TemperatureProfileGraph, self).__init__(parent, 420, 315)

        self._ax = self.add_subplot()

        self.__peb = None

        if peb is not None:
            self.setObject(peb)

    # noinspection PyPep8Naming
    def setObject(self, p_object):
        if self.__peb is not None:
            disconnect(self.__peb.time.signals[Abstract], self.__onValueChanged)
            disconnect(self.__peb.temp.signals[Abstract], self.__onValueChanged)

        self.__peb = p_object

        connect(self.__peb.time.signals[Abstract], self.__onValueChanged)
        connect(self.__peb.temp.signals[Abstract], self.__onValueChanged)

        self.__onValueChanged()

    # noinspection PyPep8Naming
    @Slot()
    def __onValueChanged(self):
        self.draw_graph(self.__peb.time.value, self.__peb.temp.value)

    def draw_graph(self, time, temp):
        """
        :type time: float
        :type temp: float
        """
        self._ax.clear()

        self._ax.plot([0.0, time], [temp, temp], "r-")
        self._ax.set_xlabel("Time (sec)")
        self._ax.set_ylabel("Temperature (degree C)")

        self._ax.patch.set_alpha(0.0)

        self.redraw()


class TemperatureProfileBox(QtGui.QGroupBox):

    def __init__(self, parent, peb, resist):
        """
        :type parent: QtGui.QWidget
        :type peb: options.PostExposureBake
        :type resist: options.structures.Resist
        """
        super(TemperatureProfileBox, self).__init__("Post Exposure Bake (PEB) Temperature Profile", parent)

        self.__resist = None
        self.__peb = None

        self.__hlayout_resist = QtGui.QHBoxLayout()
        self.__resist_icon = QtGui.QLabel()
        self.__resist_icon.setFixedSize(24, 24)
        self.__resist_icon.setPixmap(QtGui.QPixmap(Resources(orm.Resist.icon, "path")))
        self.__resist_name = QLabel(self)
        self.__hlayout_resist.addWidget(self.__resist_icon)
        self.__hlayout_resist.addWidget(self.__resist_name)
        self.__hlayout_resist.addStretch()

        self.__diffusion_length = QtGui.QLabel(self)
        self.__profile_graph = TemperatureProfileGraph(self)

        self.__layout = QtGui.QVBoxLayout(self)

        self.__layout.addLayout(self.__hlayout_resist)
        self.__layout.addWidget(self.__diffusion_length)
        self.__layout.addWidget(self.__profile_graph)
        self.__layout.addStretch()

        self.setPeb(peb)
        self.setResist(resist)

    # noinspection PyPep8Naming
    def setResist(self, resist):
        """:type resist: options.structures.Resist"""
        if self.__resist is not None:
            disconnect(self.__resist.peb.signals[orm.PebParameters.ln_ar], self.__onValueChanged)
            disconnect(self.__resist.peb.signals[orm.PebParameters.ea], self.__onValueChanged)

        self.__resist = resist
        self.__resist_name.setObject(self.__resist.db, orm.Resist.name)

        connect(self.__resist.peb.signals[orm.PebParameters.ln_ar], self.__onValueChanged)
        connect(self.__resist.peb.signals[orm.PebParameters.ea], self.__onValueChanged)

        self.__onValueChanged()

    # noinspection PyPep8Naming
    def setPeb(self, peb):
        if self.__peb is not None:
            disconnect(self.__peb.time.signals[Abstract], self.__onValueChanged)
            disconnect(self.__peb.temp.signals[Abstract], self.__onValueChanged)

        self.__peb = peb
        self.__profile_graph.setObject(peb)

        connect(self.__peb.time.signals[Abstract], self.__onValueChanged)
        connect(self.__peb.temp.signals[Abstract], self.__onValueChanged)

        self.__onValueChanged()

    # noinspection PyPep8Naming
    @Slot()
    def __onValueChanged(self):
        if self.__resist is not None:
            self.__diffusion_length.setText(
                "PAC Diffusion Length (nm): %.1f" %
                self.__resist.peb.diffusion_length(self.__peb.temp.value, self.__peb.time.value))


class ParametersBox(QtGui.QGroupBox):

    def edit(self, p_object):
        result = QLineEditNumeric(self, p_object)
        result.setFixedWidth(config.DEFAULT_EDIT_WIDTH)
        return result

    def __init__(self, parent, peb):
        """
        :type parent: QtGui.QWidget
        :type peb: options.PostExposureBake
        """
        super(ParametersBox, self).__init__("Temperature profile parameters", parent)

        self.__hlayout_control = QtGui.QHBoxLayout()
        self.__load_button = QtGui.QPushButton("Load...", self)
        self.__load_button.setEnabled(False)
        self.__save_button = QtGui.QPushButton("Save to Database", self)
        self.__save_button.setEnabled(False)
        self.__hlayout_control.addWidget(self.__load_button)
        self.__hlayout_control.addWidget(self.__save_button)
        self.__hlayout_control.addStretch()

        self.__hlayout_name = QtGui.QHBoxLayout()
        self.__hlayout_name.addWidget(QtGui.QLabel("Model name:"))
        self.__model_edit = QtGui.QLineEdit("Ideal Model")
        self.__model_edit.setEnabled(False)
        self.__hlayout_name.addWidget(self.__model_edit)

        self.__form_layout = QtGui.QFormLayout()
        self.__form_layout.addRow("Temperature (C):", self.edit(peb.temp))
        self.__form_layout.addRow("Duration (sec):", self.edit(peb.time))

        self.__layout = QtGui.QVBoxLayout(self)
        self.__layout.addLayout(self.__hlayout_control)
        self.__layout.addLayout(self.__hlayout_name)
        self.__layout.addSpacing(30)
        self.__layout.addLayout(self.__form_layout)
        self.__layout.addStretch()

        self.setFixedWidth(350)


class PostExposureBakeView(QStackWidgetTab):
    def __init__(self, parent, opts):
        """
        :param QtGui.QWidget parent: Widget parent
        :param options.Options opts: Current application options
        """
        super(PostExposureBakeView, self).__init__(parent)

        self.__options = opts

        self.__parameters = ParametersBox(self, opts.peb)
        self.__profile = TemperatureProfileBox(self, opts.peb, opts.wafer_process.resist)

        self.__hlay = QtGui.QHBoxLayout()
        self.__hlay.addWidget(self.__parameters)
        self.__hlay.addWidget(self.__profile)
        self.__hlay.addStretch()

        self.__vlay = QtGui.QVBoxLayout(self)
        self.__vlay.addLayout(self.__hlay)
        self.__vlay.addStretch()

    def reset(self):
        self.__profile.setPeb(self.__options.peb)
        self.__profile.setResist(self.__options.wafer_process.resist)
