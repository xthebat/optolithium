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

from qt import QtGui, QtWebKit
from resources import Resources
from views.common import QStackWidgetTab

import helpers
import options


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


class SummaryView(QStackWidgetTab):

    def __init__(self, parent, opts):
        """
        :type parent: QtGui.QWidget
        :param options.Options opts: Program options
        """
        QStackWidgetTab.__init__(self, parent)

        self.__options = opts
        self.__template = Resources("xhtml/report")
        """:type: str"""

        self.web_view = QtWebKit.QWebView(self)

        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.addWidget(self.web_view)

    def onSetActive(self):
        html = self.__template % {"filename": self.__options.filename, "body": self.__options.report()}
        self.web_view.setHtml(html)

    def print_(self, printer):
        self.web_view.print_(printer)

    def reset(self):
        self.onSetActive()
