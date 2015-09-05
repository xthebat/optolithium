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

import PySide
import PySide.QtCore as _QtCore
import PySide.QtGui as _QtGui
import PySide.QtWebKit as _QtWebKit

import helpers
import logging as module_logging


backend_name = 'PySide'


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


QtCore = _QtCore
QtGui = _QtGui
QtWebKit = _QtWebKit


Signal = QtCore.Signal
Slot = QtCore.Slot


core_version = QtCore.__version__
version = PySide.__version__


def connect(signal, *slots, **kwargs):
    """
    :type signal: Signal
    :type slot: Slot
    """
    connection_type = kwargs.get("connection_type", QtCore.Qt.AutoConnection)
    logging.debug("Connect %s with %s" % (signal, slots))
    for slot in slots:
        # noinspection PyUnresolvedReferences
        signal.connect(slot, connection_type)


def disconnect(signal, slot):
    """
    :type signal: Signal
    :type slot: Slot
    """
    logging.debug("Disconnect %s with %s" % (signal, slot))
    # noinspection PyUnresolvedReferences
    signal.disconnect(slot)


class _GlobalSignalsClass(QtCore.QObject):

    changed = Signal()

    # noinspection PyPep8Naming
    @Slot()
    def onChanged(self):
        # noinspection PyUnresolvedReferences
        self.changed.emit()


GlobalSignals = _GlobalSignalsClass()
