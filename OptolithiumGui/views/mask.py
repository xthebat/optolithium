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
import math
import os
import tempfile

from matplotlib.patches import Rectangle, Polygon
import subprocess

from qt import connect, disconnect, Slot, QtGui, QtCore
from views.common import QStackWidgetTab, QFramedLabel, msgBox, ErrorBox, \
    ParameterGroupBox, QLoadDialogFactory, QGraphPlot, QuestionBox, rgbf
from options.common import Abstract
from database import orm, dbparser

import helpers
import config

__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.DEBUG)
helpers.logStreamEnable(logging)


class MaskParametersBox(ParameterGroupBox):
    def __init__(self, parent, mask=None):
        """
        :type parent: QtGui.QWidget
        :type mask: orm.Mask | orm.ConcretePluginMask | None
        """
        super(MaskParametersBox, self).__init__("Mask Parameters", parent)

        self.__layout = QtGui.QVBoxLayout(self)

        self.setMinimumHeight(50)

        if mask is not None:
            self.setObject(mask)

    # noinspection PyPep8Naming
    def setObject(self, mask):
        """:type mask: orm.Mask | orm.ConcretePluginMask | None"""
        self._add_plugin_parameters(mask, self.__layout)


class MaskCoordBox(ParameterGroupBox):

    def __init__(self, parent, mask=None):
        """
        :type parent: QtGui.QWidget
        :type mask: orm.Mask | orm.ConcretePluginMask | None
        """
        super(MaskCoordBox, self).__init__("Mask Coordinates", parent)

        self.__form_layout = QtGui.QGridLayout()

        self.__top_label = QtGui.QLabel("Top (nm):")
        self.__top_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.__left_label = QtGui.QLabel("Left (nm):")
        self.__bottom_label = QtGui.QLabel("Bottom (nm):")
        self.__bottom_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.__right_label = QtGui.QLabel("Right (nm)")

        self.__top_value = self.framed_label()
        self.__left_value = self.framed_label()
        self.__bottom_value = self.framed_label()
        self.__right_value = self.framed_label()

        self.__form_layout.addWidget(self.__top_label, 0, 0, 1, 2)
        self.__form_layout.addWidget(self.__left_label, 1, 0)
        self.__form_layout.addWidget(self.__bottom_label, 2, 0, 1, 2)
        self.__form_layout.addWidget(self.__right_label, 1, 5)

        self.__form_layout.addWidget(self.__top_value, 0, 2, 1, 2)
        self.__form_layout.addWidget(self.__left_value, 1, 1, 1, 2)
        self.__form_layout.addWidget(self.__bottom_value, 2, 2, 1, 2)
        self.__form_layout.addWidget(self.__right_value, 1, 3, 1, 2)

        self.__form_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.addLayout(self.__form_layout)

        self.__mask = None
        """:type: orm.Mask | orm.ConcretePluginMask | None"""

        if mask is not None:
            self.setObject(mask)

    # noinspection PyPep8Naming
    @Slot()
    def updateValues(self):
        [left, bottom] = self.__mask.boundary[0]
        [right, top] = self.__mask.boundary[1]
        if self.__mask.dimensions == 1:
            if top == 0.0 and bottom == 0.0:
                self.__top_value.setText(str())
                self.__bottom_value.setText(str())
                self.__right_value.setText("%.1f nm" % right)
                self.__left_value.setText("%.1f nm" % left)
            elif right == 0.0 and left == 0.0:
                self.__top_value.setText("%.1f nm" % top)
                self.__bottom_value.setText("%.1f nm" % bottom)
                self.__right_value.setText(str())
                self.__left_value.setText(str())
            else:
                raise RuntimeError("Unknown one-dimension mask direction nor X, nor Y (%.1f, %.1f, %.1f, %.1f)" %
                                   (left, bottom, right, top))

        elif self.__mask.dimensions == 2:
            self.__top_value.setText("%.1f nm" % top)
            self.__bottom_value.setText("%.1f nm" % bottom)
            self.__right_value.setText("%.1f nm" % right)
            self.__left_value.setText("%.1f nm" % left)
        else:
            raise RuntimeError("Wrong mask dimensions count")

    # noinspection PyPep8Naming
    def setObject(self, p_object):
        """:type p_object: orm.Mask | orm.ConcretePluginMask | None"""
        if self.__mask is not None:
            for variable in self.__mask.variables:
                disconnect(variable.signals[Abstract], self.updateValues)

        self.__mask = p_object

        for variable in self.__mask.variables:
            connect(variable.signals[Abstract], self.updateValues)

        self.updateValues()


class MaskBackgroundBox(ParameterGroupBox):

    def __init__(self, parent, mask=None):
        """
        :type parent: QtGui.QWidget
        :type mask: orm.Mask | orm.ConcretePluginMask | None
        """
        super(MaskBackgroundBox, self).__init__("Mask Background", parent)

        self.__mask = None
        """:type: orm.Mask | orm.ConcretePluginMask | None"""

        self.__hlayout = QtGui.QHBoxLayout()

        self.__transmittance_label = QtGui.QLabel("Transmittance:", self)
        self.__transmittance_edit = self.edit()

        self.__phase_label = QtGui.QLabel("Phase (deg):", self)
        self.__phase_edit = self.edit()

        self.__hlayout.addWidget(self.__transmittance_label)
        self.__hlayout.addWidget(self.__transmittance_edit)
        self.__hlayout.addSpacing(20)
        self.__hlayout.addWidget(self.__phase_label)
        self.__hlayout.addWidget(self.__phase_edit)
        self.__hlayout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.__layout = QtGui.QVBoxLayout(self)
        self.__layout.addLayout(self.__hlayout)
        self.__layout.addSpacing(5)

        if mask is not None:
            self.setObject(mask)

    # noinspection PyPep8Naming
    def setObject(self, p_object):
        """:type p_object: orm.Mask | orm.ConcretePluginMask | None"""
        if self.__mask is not None:
            self.__transmittance_edit.unsetObject()
            self.__phase_edit.unsetObject()

        self.__mask = p_object

        self.__transmittance_edit.setObject(self.__mask, orm.Mask.background)
        self.__phase_edit.setObject(self.__mask, orm.Mask.phase)


class PolygonHighlighter(helpers.DisposableInterface):
    def __init__(self, polygon, highlight_color="#FF0000", linewidth=5.0):
        """
        :type polygon: Polygon
        :type highlight_color: str
        """
        super(PolygonHighlighter, self).__init__()
        self.polygon = polygon
        self.highlight_color = highlight_color
        self.linewidth = linewidth
        self.highlighted = False
        self.backup_color = None
        self.backup_linewidth = None
        self.cid = polygon.figure.canvas.mpl_connect("motion_notify_event", self)

    def __call__(self, event):
        if event.inaxes == self.polygon.axes:
            if self.polygon.contains_point([event.x, event.y]):
                # Don't merge into one if - not working - highlight is blinking... I don't know why
                if not self.highlighted:
                    self.backup_color = self.polygon.get_edgecolor()
                    self.polygon.set_edgecolor(self.highlight_color)
                    self.polygon.set_linewidth(self.linewidth)
                    self.highlighted = True
                    self.polygon.figure.canvas.draw()
            elif self.highlighted:
                self.polygon.set_edgecolor(self.backup_color)
                self.polygon.set_linewidth(self.backup_linewidth)
                self.backup_color = None
                self.backup_linewidth = None
                self.highlighted = False
                self.polygon.figure.canvas.draw()

    def dispose(self):
        self.polygon.figure.canvas.mpl_disconnect(self.cid)
        self.polygon = None


class MaskPlot(QGraphPlot):

    #                       0.0    ,  30.0,      90.0,     150.0,     210.0,     270.0,     330.0
    phase_colormap = ["#FFFFFF", "#80FFFF", "#FFFF80", "#FF80FF", "#80FF80", "#8080FF", "#FFFFFF"]

    @staticmethod
    def _get_color(transmittance, phase):
        phase_color = MaskPlot.phase_colormap[int(math.floor((phase + 30.0) / 60.0))]
        rgb = rgbf(QtGui.QColor(phase_color))
        return rgb[0]*transmittance, rgb[1]*transmittance, rgb[2]*transmittance

    def __init__(self, parent, p_object=None):
        """
        :type parent: QtGui.QWidget
        :type p_object: orm.Mask | orm.ConcretePluginMask | None
        """
        super(MaskPlot, self).__init__(parent)

        self.setMinimumSize(200, 200)
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

        self.__mask = None
        """:type: orm.Mask | options.ConcretePluginMask | None"""

        self._ax = self.add_subplot()

        for axis in ['top', 'bottom', 'left', 'right']:
            self._ax.spines[axis].set_linewidth(2)

        self._highlighters = helpers.DisposableList()

        if p_object is not None:
            self.setObject(p_object)

    # noinspection PyPep8Naming
    def setObject(self, p_object):
        """:type p_object: orm.Mask | orm.ConcretePluginMask | None"""

        if self.__mask is not None:
            for variable in self.__mask.variables:
                disconnect(variable.signals[Abstract], self.__onValueChanged)
            disconnect(self.__mask.signals[orm.Mask.background], self.__onValueChanged)
            disconnect(self.__mask.signals[orm.Mask.phase], self.__onValueChanged)

        self.__mask = p_object

        for variable in self.__mask.variables:
            connect(variable.signals[Abstract], self.__onValueChanged)
        connect(self.__mask.signals[orm.Mask.background], self.__onValueChanged)
        connect(self.__mask.signals[orm.Mask.phase], self.__onValueChanged)

        self.__onValueChanged()

    # noinspection PyPep8Naming
    @Slot()
    def __onValueChanged(self):
        self.draw_graph()

    def draw_graph(self):
        self._highlighters.dispose()
        self._ax.clear()

        if self.__mask.dimensions == 2:

            [left, bottom] = self.__mask.boundary[0]
            [right, top] = self.__mask.boundary[1]
            self._ax.set_xlim(left, right)
            self._ax.set_ylim(bottom, top)

            bg_color = MaskPlot._get_color(self.__mask.background, self.__mask.phase)

            self._ax.add_patch(Rectangle([left, bottom], right-left, top-bottom, color=bg_color, linewidth=1.0))
            for region in self.__mask.regions:
                xy = [[p.x, p.y] for p in region.points]
                color = MaskPlot._get_color(region.transmittance, region.phase)
                polygon = Polygon(xy, facecolor=color, edgecolor=color, linewidth=1.0)
                self._ax.add_patch(polygon)
                self._highlighters.append(PolygonHighlighter(polygon))

            self._ax.set_aspect('equal')

        elif self.__mask.dimensions == 1:
            # TODO: Take into account Y-direction mask

            [left, _] = self.__mask.boundary[0]
            [right, _] = self.__mask.boundary[1]
            self._ax.set_xlim(left, right)
            self._ax.set_ylim(-1.0, 1.0)

            bg_color = MaskPlot._get_color(self.__mask.background, self.__mask.phase)

            self._ax.add_patch(Rectangle([left, -1.0], right-left, 2.0, color=bg_color, linewidth=1.0))
            for region in self.__mask.regions:
                xy = [[region.points[0].x, -1.0], [region.points[0].x, 1.0],
                      [region.points[1].x, 1.0], [region.points[1].x, -1.0]]
                color = MaskPlot._get_color(region.transmittance, region.phase)
                self._ax.add_patch(Polygon(xy, color=color))

            self._ax.set_aspect('auto')

        else:

            raise RuntimeError("Wrong mask dimensions count")

        self.redraw()


LoadMaskDialog = QLoadDialogFactory(orm.Mask, orm.AbstractPluginMask, MaskPlot)


class MaskView(QStackWidgetTab):
    def __init__(self, parent, opts, appdb):
        """
        :param QtGui.QWidget parent: Widget parent
        :param options.structures.Options opts: Current application options
        :param ApplicationDatabase appdb: Application database object
        """
        super(MaskView, self).__init__(parent)

        self.__mask = opts.mask
        self.__appdb = appdb

        self.__load_mask_dlg = LoadMaskDialog(self, appdb)

        self.__header_prms_hlay = QtGui.QHBoxLayout()
        self.__load_button = QtGui.QPushButton("Load Mask...")
        self.__edit_button = QtGui.QPushButton("Edit Mask...")
        self.__save_button = QtGui.QPushButton("Save Mask to Database")

        connect(self.__load_button.pressed, self._load_mask)
        connect(self.__edit_button.pressed, self._edit_mask)
        connect(self.__save_button.pressed, self._save_mask)

        self.__header_prms_hlay.addWidget(self.__load_button)
        self.__header_prms_hlay.addWidget(self.__edit_button)
        self.__header_prms_hlay.addWidget(self.__save_button)
        self.__header_prms_hlay.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.__label = QtGui.QLabel("Mask Type:")
        self.__type_label = QFramedLabel(self)

        self.__hlayout_type = QtGui.QHBoxLayout()
        self.__hlayout_type.addWidget(self.__label)
        self.__hlayout_type.addWidget(self.__type_label)
        self.__hlayout_type.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.__parameters = MaskParametersBox(self)
        self.__coordinates = MaskCoordBox(self)
        self.__background = MaskBackgroundBox(self)

        self.__parameters_vlay = QtGui.QVBoxLayout()
        self.__parameters_vlay.addLayout(self.__header_prms_hlay)
        self.__parameters_vlay.addLayout(self.__hlayout_type)
        self.__parameters_vlay.addWidget(self.__parameters)
        self.__parameters_vlay.addSpacing(20)
        self.__parameters_vlay.addWidget(self.__coordinates)
        self.__parameters_vlay.addWidget(self.__background)
        self.__parameters_vlay.addStretch()

        self.__header_plot_hlay = QtGui.QHBoxLayout()
        self.__name_label = QtGui.QLabel("Name:")
        self.__name_edit = QtGui.QLineEdit()
        self.__name_edit.setFixedWidth(400)
        self.__header_plot_hlay.addWidget(self.__name_label)
        self.__header_plot_hlay.addWidget(self.__name_edit)
        self.__transmit_comment_label = QtGui.QLabel(
            "Black = 0% transmittance\n"
            "White = 100% transmittance")
        self.__header_plot_hlay.addStretch()

        self.__mask_plot = MaskPlot(self)

        self.__plot_vlay = QtGui.QVBoxLayout()
        self.__plot_vlay.addLayout(self.__header_plot_hlay)
        self.__plot_vlay.addWidget(self.__transmit_comment_label)
        self.__plot_vlay.addSpacing(20)
        self.__plot_vlay.addWidget(self.__mask_plot)

        self.__hlay = QtGui.QHBoxLayout(self)
        self.__hlay.addLayout(self.__parameters_vlay)
        self.__hlay.addSpacing(20)
        self.__hlay.addLayout(self.__plot_vlay)

        self.__hlay.setStretchFactor(self.__parameters_vlay, 0.0)
        self.__hlay.setStretchFactor(self.__plot_vlay, 2.0)

        self.setObject(self.__mask.container)

    # noinspection PyPep8Naming
    def setObject(self, mask):
        """:rtype: orm.ConcretePluginMask | orm.Mask"""
        self.__mask.container = mask
        edit_save_enabled = isinstance(mask, orm.Mask)
        self.__edit_button.setEnabled(edit_save_enabled)
        self.__save_button.setEnabled(edit_save_enabled)
        self.__name_edit.setText(self.__mask.container.name)
        self.__type_label.setText("%dD" % self.__mask.container.dimensions)
        self.__mask_plot.setObject(self.__mask.container)
        self.__parameters.setObject(self.__mask.container)
        self.__coordinates.setObject(self.__mask.container)
        self.__background.setObject(self.__mask.container)

    @Slot()
    def _load_mask(self):
        if self.__load_mask_dlg.exec_():
            mask = self.__load_mask_dlg.object
            logging.info("Load mask: %s [%s]" % (mask.name, type(mask).__name__))
            self.setObject(mask)

    @Slot()
    def _edit_mask(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".gds2")
        is_ok = self.__mask.container.gds(tmp)
        tmp.close()

        if not is_ok:
            ErrorBox(self, "Can't covert to GDSII format current layout using this mapping file")
            os.unlink(tmp.name)
            return

        try:
            subprocess.call([config.KLAYOUT_PATH, "-e", "%s" % tmp.name])
        except OSError as error:
            if error.errno == 2:
                ErrorBox(self, "KLayout editor can't be found. Please download it if you wish to edit the layout.")
        else:
            p_object = dbparser.LayoutParser().parse(tmp.name)
            self.setObject(p_object)
        finally:
            os.unlink(tmp.name)

    @Slot()
    def _save_mask(self):
        mask_name = self.__name_edit.text()
        try:
            mask = self.__appdb[orm.Mask].filter(orm.Mask.name == mask_name).one()
            """:type: orm.Mask"""
        except orm.NoResultFound:
            self.__mask.container.name = mask_name
            self.__appdb.add(self.__mask.container.clone())
        else:
            replay = QuestionBox(self, "%s \"%s\" already existed, replace it?" % (mask.identifier, mask.name))
            if replay == msgBox.Yes:
                mask.container.assign(self.__mask.container)
                self.__appdb.commit()

    def reset(self):
        self.setObject(self.__mask.container)