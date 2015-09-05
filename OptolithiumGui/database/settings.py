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

__author__ = 'Alexei Gladkikh'


class DummyProvider(object):

    def __init__(self, *args, **kwargs):
        pass

    def emit(self, *args, **kwargs):
        pass

    def connect(self, *args, **kwargs):
        pass


try:
    from qt import Signal, QtCore
    _GUI_PROVIDER_OBJECT = QtCore.QObject
    _GUI_PROVIDER_SIGNAL = Signal
except ImportError:
    Signal = None
    QObject = None
    _GUI_PROVIDER_OBJECT = DummyProvider
    _GUI_PROVIDER_SIGNAL = DummyProvider


def set_gui_provider(object_class, signal_class):
    global _GUI_PROVIDER_OBJECT, _GUI_PROVIDER_SIGNAL
    _GUI_PROVIDER_OBJECT = object_class
    _GUI_PROVIDER_SIGNAL = signal_class


def get_gui_provider_object():
    return _GUI_PROVIDER_OBJECT


def get_gui_provider_signal():
    return _GUI_PROVIDER_SIGNAL
