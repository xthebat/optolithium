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

import sys
import config
from qt import QtGui, QtCore
from optolithium import MainWindow
from info import __version__
from config import application_style


__author__ = 'Alexei Gladkikh'


def main():
    app = QtGui.QApplication(sys.argv)

    QtCore.QThread.currentThread().setObjectName("MainThread")

    # QtGui.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    # noinspection PyCallByClass,PyTypeChecker
    QtGui.QApplication.setStyle(application_style)
    QtGui.QApplication.setApplicationName(config.APPLICATION_NAME)
    QtGui.QApplication.setApplicationVersion(__version__)
    # noinspection PyUnusedLocal
    main_window = MainWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
