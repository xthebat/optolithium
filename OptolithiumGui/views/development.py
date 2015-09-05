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

from database import orm
from qt import QtGui, connect, disconnect, Slot
from views.common import QStackWidgetTab, QLineEditNumeric, QGraphPlot

import config
import helpers


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.DEBUG)
helpers.logStreamEnable(logging)


# noinspection PyPep8Naming
class sproperty(object):
    """Property descriptor that can only be set"""
    def __init__(self, func, doc=None):
        self.func = func
        self.__doc__ = doc if doc is not None else func.__doc__

    def __set__(self, obj, value):
        return self.func(obj, value)


class DevelopmentGraph(QGraphPlot):

    pac_data = numpy.arange(0.0, 1.0, config.DEV_RATE_PAC_STEP)

    def __init__(self, parent):
        """:type parent: QtGui.QWidget"""
        QGraphPlot.__init__(self, parent, width=320, height=240)

        self._ax = self.add_subplot()

        self.__developer = None
        """:type: orm.DeveloperInterface"""

    def __draw_graph(self, developer):
        """:type developer: orm.DeveloperInterface"""
        self._ax.clear()

        pac_data = DevelopmentGraph.pac_data
        # rate_data = [developer.rate(pac) for pac in pac_data]
        rate_data = developer.rate(pac_data, [0.0])

        self._ax.plot(pac_data, rate_data, "r-")

        self._ax.grid()

        self._ax.set_xlabel("Photo-active component concentration")
        self._ax.set_ylabel("Development Rate (nm/s)")

        self._ax.patch.set_alpha(0.0)

        self._ax.set_ylim([min(rate_data), max(rate_data)])

        self.redraw()

    @sproperty
    def developer(self, developer):
        """:type developer: orm.DeveloperInterface or None"""
        if developer is not None:
            self.__developer = developer
            self.update_graph()

            if isinstance(developer, orm.DeveloperExpr):
                for obj in developer.object_values:
                    connect(obj.signals[orm.DeveloperExprArgValue.value], self.update_graph)
        else:
            if isinstance(self.__developer, orm.DeveloperExpr):
                for obj in self.__developer.object_values:
                    disconnect(obj.signals[orm.DeveloperExprArgValue.value], self.update_graph)
            self.__developer = None
            self._ax.clear()
            self.redraw()

    @Slot()
    def update_graph(self):
        self.__draw_graph(self.__developer)


class DevelopmentView(QStackWidgetTab):

    def __init__(self, parent, development, wafer_stack):
        """
        :param QtGui.QWidget parent: Exposure and focus view widget parent
        :param options.structures.Development development: Development options parameters
        :param options.structures.WaferProcess wafer_stack: Wafer stack
        """
        QStackWidgetTab.__init__(self, parent)

        self.__wafer_stack = wafer_stack

        self.__dev_time_label = QtGui.QLabel("Development Time (sec):")
        self.__dev_time = QLineEditNumeric(self, development.develop_time)
        self.__dev_rate_graph = DevelopmentGraph(self)

        self.__hlay = QtGui.QHBoxLayout()
        self.__hlay.addStretch()
        self.__hlay.addWidget(self.__dev_time_label)
        self.__hlay.addWidget(self.__dev_time)

        self.__vlay = QtGui.QVBoxLayout()
        self.__vlay.addSpacing(30)
        self.__vlay.addLayout(self.__hlay)
        self.__vlay.addStretch()

        self.__glay = QtGui.QVBoxLayout()
        self.__vlay.addSpacing(20)
        self.__glay.addWidget(self.__dev_rate_graph)
        self.__glay.addStretch()

        # self.__graph_layout.addWidget(self.__dev_rate_graph)

        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.addLayout(self.__vlay)
        self.__layout.addLayout(self.__glay)
        self.__layout.addStretch()

    def onSetActive(self):
        self.__dev_rate_graph.developer = self.__wafer_stack.resist.developer

    def reset(self):
        self.__dev_rate_graph.developer = self.__wafer_stack.resist.developer
