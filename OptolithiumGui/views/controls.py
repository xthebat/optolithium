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

from qt import QtGui, QtCore, connect

import helpers
import logging as module_logging


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


class ControlBar(QtCore.QObject):

    class ActionData(object):
        def __init__(self, name, text, icon=None, callback=None, status_tip=None, shortcut=None, enabled=True):
            """
            :type name: str
            :type text: str
            :type icon: QtGui.QIcon
            :type status_tip: str or None
            :type shortcut: str or None
            :type enabled: bool
            """
            self.name = name
            self.text = text
            self.icon = icon
            self.callback = callback
            self.status_tip = status_tip
            self.shortcut = shortcut
            self.enabled = enabled and self.callback is not None

    def __init__(self, parent, name, text):
        """:type parent: QtGui.QMainWindow"""
        QtCore.QObject.__init__(self, parent)

        self.setObjectName(name)

        self.__text = text

        self.__actions = dict()
        """:type: dict from str to QtGui.QAction"""

        self.__parent = parent
        """:type parent: QtGui.QMainWindow"""

        self.__menubar = QtGui.QMenu(text, self.__parent.menuBar())
        """:type parent: tGui.QMenu"""

        self.__menubar.setObjectName("MenuBar_" + name)

        self.__toolbar = None
        """:type: QtGui.QToolBar or None"""

        self.__parent.menuBar().addMenu(self.__menubar)

    def add_separator(self):
        logging.debug("Create separator")
        self.__menubar.addSeparator()

        if self.__toolbar is not None:
            self.__toolbar.addSeparator()

    def add_action(self, data):
        """
        :type data: ControlBar.ActionData
        :rtype: QtGui.QAction
        """

        logging.debug("Create action: %s" % data.name)

        if data.icon is not None:
            logging.debug("Set action icon")
            if self.__toolbar is None:
                self.__toolbar = QtGui.QToolBar(self.__text, self.__parent)
                self.__toolbar.setObjectName("ToolBar_" + self.objectName())
                self.__parent.addToolBar(self.__toolbar)

            self.__actions[data.name] = QtGui.QAction(data.icon, data.text, self)
            self.__toolbar.addAction(self.__actions[data.name])
        else:
            self.__actions[data.name] = QtGui.QAction(data.text, self)

        if data.status_tip is not None:
            logging.debug("Set action status tip")
            self.__actions[data.name].setStatusTip(data.status_tip)

        if data.shortcut is not None:
            logging.debug("Set action shortcut")
            self.__actions[data.name].setShortcut(data.shortcut)

        if data.callback is not None:
            logging.debug("Set action callback")
            connect(self.__actions[data.name].triggered, data.callback)

        logging.debug("Add action to menubar")
        self.__menubar.addAction(self.__actions[data.name])

        logging.debug("Set object name")
        self.__actions[data.name].setObjectName("%s.%s" % (self.objectName(), data.name))

        logging.debug("Enable action")
        self.__actions[data.name].setEnabled(data.enabled)

        logging.debug("Action %s created successfully" % data.name)
        return self.__actions[data.name]

    def set_group(self, group):
        """:type group: QtGui.QActionGroup"""
        checkable = group.isExclusive()
        for action in self.__actions.values():
            action.setCheckable(checkable)
            group.addAction(action)

    def __getitem__(self, item):
        """:type item: str"""
        return self.__actions[item]

    @property
    def parent(self):
        """:rtype: QtGui.QMainWindow"""
        return self.__parent

    @staticmethod
    def group(controls_list, exclusive=True):
        """
        :type controls_list: list of ControlBar
        :type exclusive: bool
        """
        different_parents = set([control.parent for control in controls_list])

        if len(different_parents) > 1:
            raise ValueError("Parent of the control bars must be the same when adding into action group!")
        elif len(different_parents) == 0:
            raise IndexError("Input list must not be empty!")

        parent = different_parents.pop()

        action_group = QtGui.QActionGroup(parent)
        action_group.setExclusive(exclusive)

        for control in controls_list:
            control.set_group(action_group)


class ControlsView(QtCore.QObject):

    class ControlData(object):
        def __init__(self, name, text, actions):
            """
            :type name: str
            :type text: str
            :type actions: list[ControlBar.ActionData|None]
            """
            self.name = name
            self.text = text
            self.actions = actions

    def __init__(self, parent, controls_data, groups=None):
        """
        :param QtGui.QMainWindow parent: Where
        :param list of ControlsView.ControlData controls_data: Required data to create control view
        :param list[tuple[str]] or None groups: Create action groups for the toolbars
        """
        QtCore.QObject.__init__(self, parent)

        self.__controls = dict()
        """:type: dict from str to ControlBar"""

        for control in controls_data:
            logging.debug("Create control: %s" % control.name)
            self.__controls[control.name] = ControlBar(parent, control.name, control.text)
            for action_data in control.actions:
                if action_data is not None:
                    self.__controls[control.name].add_action(action_data)
                else:
                    self.__controls[control.name].add_separator()

        if groups is not None:
            for group in groups:
                ControlBar.group([self.__controls[control_name] for control_name in group])

    def __getitem__(self, item):
        """
        :type item: str
        :rtype: ControlBar
        """
        return self.__controls[item]
