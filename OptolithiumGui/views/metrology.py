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

from qt import QtGui
from views.common import QStackWidgetTab, QLineEditNumeric, QComboBoxEnum


__author__ = 'Alexei Gladkikh'


class _MetrologyBoxBase(QtGui.QGroupBox):

    def _add_edit(self, p_object, _class=QLineEditNumeric):
        layout = QtGui.QHBoxLayout()
        layout.addWidget(QtGui.QLabel(p_object.name + ": "))
        edit = _class(self, p_object)
        layout.addStretch()
        layout.addWidget(edit)
        self._layout.addLayout(layout)
        return edit


class LevelsBox(_MetrologyBoxBase):

    def __init__(self, parent, metrology):
        """
        :type parent: QtGui.QWidget
        :type metrology: options.structures.Metrology
        """
        super(LevelsBox, self).__init__("Levels", parent)
        self._metrology = metrology
        self._layout = QtGui.QVBoxLayout(self)
        self._edits = [
            self._add_edit(self._metrology.aerial_image_level),
            self._add_edit(self._metrology.image_in_resist_level),
            self._add_edit(self._metrology.latent_image_level),
            self._add_edit(self._metrology.peb_latent_image_level),
        ]


class MiscBox(_MetrologyBoxBase):

    def __init__(self, parent, metrology):
        """
        :type parent: QtGui.QWidget
        :type metrology: options.structures.Metrology
        """
        super(MiscBox, self).__init__("Miscellaneous", parent)
        self._metrology = metrology
        self._layout = QtGui.QVBoxLayout(self)
        self._edits = [
            self._add_edit(self._metrology.mask_tonality, _class=QComboBoxEnum),
            self._add_edit(self._metrology.measurement_height),
            self._add_edit(self._metrology.variate_meas_height, _class=QComboBoxEnum),
            self._add_edit(self._metrology.cd_bias),
        ]


class MetrologyView(QStackWidgetTab):

    def __init__(self, parent, options):
        """
        :param QtGui.QWidget parent: Widget parent
        :param options.structures.Options options: Program options
        """
        QStackWidgetTab.__init__(self, parent)

        self.__options = options

        self.__vlayout = QtGui.QVBoxLayout()

        self.__levels_box = LevelsBox(self, self.__options.metrology)
        self.__misc_box = MiscBox(self, self.__options.metrology)

        self.__vlayout.addWidget(self.__levels_box)
        self.__vlayout.addWidget(self.__misc_box)
        self.__vlayout.addStretch()

        self.__hlayout = QtGui.QHBoxLayout(self)
        self.__hlayout.addLayout(self.__vlayout)
        self.__hlayout.addStretch()