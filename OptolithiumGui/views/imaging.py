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

from scipy import ndimage
from qt import connect, disconnect, Slot, QtGui, QtCore
from views.common import QStackWidgetTab, ParameterGroupBox, QLoadDialogFactory, QGraphPlot, ProlithColormap
from options.common import Abstract
from database import orm

import numpy
import helpers


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.DEBUG)
helpers.logStreamEnable(logging)


class StandardImagingPlot(QGraphPlot):
    """
    Abstract class. Method _get_values must be reimplemented.
    """

    @staticmethod
    def _get_values(p_object, x, y):
        raise NotImplementedError

    def __init__(self, parent, p_object=None):
        """
        :type parent: QtGui.QWidget
        # :type p_object: orm.SourceShape | orm.ConcretePluginSourceShape | None
        """
        super(StandardImagingPlot, self).__init__(parent)

        self.setFixedSize(290, 290)
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

        self.__interp = None
        """:type: scipy.interpolate.interp2d"""

        self.__p_object = None
        # """:type: orm.SourceShape | orm.ConcretePluginSourceShape | None"""

        self._ax = self.add_subplot()
        self._ax.set_aspect("equal")

        if p_object is not None:
            self.setObject(p_object)

    # noinspection PyPep8Naming
    def setObject(self, p_object):
        # """:type p_object: orm.SourceShape | orm.ConcretePluginSourceShape"""

        if self.__p_object is not None:
            for variable in self.__p_object.variables:
                disconnect(variable.signals[Abstract], self.__onValueChanged)

        self.__p_object = p_object

        for variable in self.__p_object.variables:
            connect(variable.signals[Abstract], self.__onValueChanged)

        self.__onValueChanged()

    # noinspection PyPep8Naming
    @Slot()
    def __onValueChanged(self):
        self.draw_graph()

    def draw_graph(self):
        self._ax.clear()

        self._ax.set_xlabel("X Pupil Position")
        self._ax.set_ylabel("Y Pupil Position")

        self._ax.set_xlim(left=-1.0, right=1.0)
        self._ax.set_ylim(bottom=-1.0, top=1.0)

        x = y = numpy.arange(-1.0, 1.01, 0.02)

        values = self._get_values(self.__p_object, x, y)

        values = ndimage.gaussian_filter(values, 0.8)
        values = ndimage.median_filter(values, 5)
        # self._ax.imshow(intensity, cmap=ProlithColormap, interpolation='nearest', extent=[-1.0, 1.0, -1.0, 1.0])
        self._ax.contourf(x, y, values, cmap=ProlithColormap)

        self._ax.set_aspect("equal")

        self._ax.grid()

        self.redraw()


class SourceShapePlot(StandardImagingPlot):

    @staticmethod
    def _get_values(p_object, x, y):
        return p_object.intensity(x, y)


class PupilFilterPlot(StandardImagingPlot):

    @staticmethod
    def _get_values(p_object, x, y):
        return numpy.abs(p_object.coefficients(x, y))


LoadSourceShapeDialog = QLoadDialogFactory(orm.SourceShape, orm.AbstractPluginSourceShape, SourceShapePlot)
LoadPupilFilterDialog = QLoadDialogFactory(orm.PupilFilter, orm.AbstractPluginPupilFilter, PupilFilterPlot)


class SourceShapeBox(ParameterGroupBox):

    def __init__(self, parent, imaging_tool, appdb):
        """
        :type imaging_tool: options.structures.ImagingTool
        :type appdb: ApplicationDatabase
        """
        super(SourceShapeBox, self).__init__("Source Shape", parent)

        self.__imaging_tools = imaging_tool

        self.__load_source_shape_dlg = LoadSourceShapeDialog(self, appdb)

        # -- Buttons section --

        self.__buttons_hlayout = QtGui.QHBoxLayout()

        self.__load_source_shape_button = QtGui.QPushButton("Load Source Shape", self)
        connect(self.__load_source_shape_button.pressed, self.__load_source_shape)

        self.__save_source_shape_button = QtGui.QPushButton("Save to Database", self)
        connect(self.__save_source_shape_button.pressed, self.__save_source_shape)
        # TODO 15: Add saving of the source shape to the database from plugin state
        self.__save_source_shape_button.setEnabled(False)

        self.__buttons_hlayout.addWidget(self.__load_source_shape_button)
        self.__buttons_hlayout.addWidget(self.__save_source_shape_button)
        self.__buttons_hlayout.addStretch()

        # -- Name section --

        self.__name_hlayout = QtGui.QHBoxLayout()

        self.__name_label = QtGui.QLabel("Name:", self)
        self.__name_edit = QtGui.QLineEdit(self)
        self.__name_edit.setMinimumWidth(200)

        self.__name_hlayout.addWidget(self.__name_label)
        self.__name_hlayout.addWidget(self.__name_edit)
        # self.__name_hlayout.addStretch()

        # -- Plot section --

        self.__source_shape_hlay = QtGui.QHBoxLayout()
        self.__source_shape_plot = SourceShapePlot(self)
        self.__source_shape_hlay.addWidget(self.__source_shape_plot)
        self.__source_shape_hlay.setAlignment(QtCore.Qt.AlignCenter)

        # -- Parameters section --

        self.__prms = {}
        self.__parameters_vlayout = QtGui.QVBoxLayout()

        # -- Body --

        self.__vlayout = QtGui.QVBoxLayout(self)
        self.__vlayout.addLayout(self.__buttons_hlayout)
        self.__vlayout.addLayout(self.__name_hlayout)
        self.__vlayout.addLayout(self.__parameters_vlayout)
        self.__vlayout.addLayout(self.__source_shape_hlay)

        self.setObject(imaging_tool.source_shape)

    # noinspection PyPep8Naming
    def setObject(self, p_object):
        """:type p_object: orm.SourceShape | orm.ConcretePluginSourceShape"""
        self.__imaging_tools.source_shape = p_object
        self.__name_edit.setText(p_object.name)
        self._add_plugin_parameters(p_object, self.__parameters_vlayout)
        self.__source_shape_plot.setObject(p_object)

    @Slot()
    def __load_source_shape(self):
        if self.__load_source_shape_dlg.exec_():
            source_shape = self.__load_source_shape_dlg.object
            logging.info("Load source shape: %s [%s]" % (source_shape.name, type(source_shape).__name__))
            self.setObject(source_shape)

    @Slot()
    def __save_source_shape(self):
        pass

    def reset(self):
        self.setObject(self.__imaging_tools.source_shape)


class SpectrumBox(ParameterGroupBox):

    def __init__(self, parent, imaging_tool):
        """:type imaging_tool: options.structures.ImagingTool"""
        super(SpectrumBox, self).__init__("Spectrum", parent)
        self.__wavelength_label = QtGui.QLabel("Wavelength (nm):")
        self.__wavelength_edit = self.edit(imaging_tool.wavelength)
        self.__hlayout = QtGui.QHBoxLayout(self)
        self.__hlayout.addWidget(self.__wavelength_label)
        self.__hlayout.addStretch()
        self.__hlayout.addWidget(self.__wavelength_edit)


class PupilFilterBox(ParameterGroupBox):

    def __init__(self, parent, imaging_tool, appdb):
        """:type imaging_tool: options.structures.ImagingTool"""
        super(PupilFilterBox, self).__init__("Pupil Filter", parent)

        self.__imaging_tool = imaging_tool

        self.__load_pupil_filter_dlg = LoadPupilFilterDialog(self, appdb)

        self.__body = QtGui.QWidget(self)
        self.__body_layout = QtGui.QVBoxLayout(self.__body)

        # -- Buttons section --

        self.__buttons_hlayout = QtGui.QHBoxLayout()

        self.__load_pupil_filter_button = QtGui.QPushButton("Load Pupil Filter", self)
        connect(self.__load_pupil_filter_button.pressed, self.__load_pupil_filter)

        self.__unload_pupil_filter_button = QtGui.QPushButton("Unload", self)
        connect(self.__unload_pupil_filter_button.pressed, self.__unload_pupil_filter)

        self.__save_pupil_filter_button = QtGui.QPushButton("Save to Database", self)
        connect(self.__save_pupil_filter_button.pressed, self.__save_pupil_filter)

        # TODO 15: Add saving of the pupil filter to the database from plugin state
        self.__save_pupil_filter_button.setEnabled(False)

        self.__buttons_hlayout.addWidget(self.__load_pupil_filter_button)
        self.__buttons_hlayout.addWidget(self.__unload_pupil_filter_button)
        self.__buttons_hlayout.addWidget(self.__save_pupil_filter_button)
        self.__buttons_hlayout.addStretch()

        # -- Name section --

        self.__name_hlayout = QtGui.QHBoxLayout()

        self.__name_label = QtGui.QLabel("Name:", self.__body)
        self.__name_edit = QtGui.QLineEdit(self.__body)
        self.__name_edit.setMinimumWidth(200)

        self.__name_hlayout.addWidget(self.__name_label)
        self.__name_hlayout.addWidget(self.__name_edit)

        # -- Plot section --

        self.__pupil_filter_hlay = QtGui.QHBoxLayout()
        self.__pupil_filter_plot = PupilFilterPlot(self.__body)
        self.__pupil_filter_hlay.addWidget(self.__pupil_filter_plot)
        self.__pupil_filter_hlay.setAlignment(QtCore.Qt.AlignCenter)

        # -- Parameters section --

        self.__prms = {}
        self.__parameters_vlayout = QtGui.QVBoxLayout()

        # -- Body --

        self.__body_layout.addLayout(self.__name_hlayout)
        self.__body_layout.addLayout(self.__parameters_vlayout)
        self.__body_layout.addLayout(self.__pupil_filter_hlay)

        self.__vlayout = QtGui.QVBoxLayout(self)
        self.__vlayout.addLayout(self.__buttons_hlayout)
        self.__vlayout.addWidget(self.__body)

        self.setObject(self.__imaging_tool.pupil_filter)

    # noinspection PyPep8Naming
    def setObject(self, p_object):
        """:type p_object: orm.PupilFilter | orm.ConcretePluginPupilFilter | None"""

        is_present = p_object is not None

        self.__save_pupil_filter_button.setEnabled(is_present)
        self.__body.setVisible(is_present)

        if is_present:
            self.__name_edit.setText(p_object.name)
            self._add_plugin_parameters(p_object, self.__parameters_vlayout)
            self.__pupil_filter_plot.setObject(p_object)

    @Slot()
    def __load_pupil_filter(self):
        if self.__load_pupil_filter_dlg.exec_():
            pupil_filter = self.__load_pupil_filter_dlg.object
            logging.info("Load pupil filter: %s [%s]" % (pupil_filter.name, type(pupil_filter).__name__))
            self.__imaging_tool.pupil_filter = pupil_filter
            self.setObject(self.__imaging_tool.pupil_filter)
            self.__imaging_tool.dirty = True
            # self.__imaging_tool.changed.emit()

    @Slot()
    def __unload_pupil_filter(self):
        self.__imaging_tool.pupil_filter = None
        self.setObject(None)
        self.__imaging_tool.dirty = True
        self.__imaging_tool.changed.emit()

    @Slot()
    def __save_pupil_filter(self):
        pass

    def reset(self):
        self.setObject(self.__imaging_tool.pupil_filter)


class ObjectiveLensBox(ParameterGroupBox):

    def __init__(self, parent, imaging_tool):
        """:type imaging_tool: options.structures.ImagingTool"""
        super(ObjectiveLensBox, self).__init__("Objective Lens", parent)

        self.__numerical_aperture_hlay = QtGui.QHBoxLayout()
        self.__numerical_aperture_label = QtGui.QLabel("Numerical Aperture:")
        self.__numerical_aperture_edit = self.edit(imaging_tool.numerical_aperture)
        self.__numerical_aperture_hlay.addWidget(self.__numerical_aperture_label)
        self.__numerical_aperture_hlay.addStretch()
        self.__numerical_aperture_hlay.addWidget(self.__numerical_aperture_edit)

        self.__reduction_ratio_hlay = QtGui.QHBoxLayout()
        self.__reduction_ratio_label = QtGui.QLabel("Reduction Ratio:")
        self.__reduction_ratio_edit = self.edit(imaging_tool.reduction_ratio)
        self.__reduction_ratio_hlay.addWidget(self.__reduction_ratio_label)
        self.__reduction_ratio_hlay.addStretch()
        self.__reduction_ratio_hlay.addWidget(self.__reduction_ratio_edit)

        self.__flare_hlay = QtGui.QHBoxLayout()
        self.__flare_label = QtGui.QLabel("Flare:")
        self.__flare_edit = self.edit(imaging_tool.flare)
        self.__flare_hlay.addWidget(self.__flare_label)
        self.__flare_hlay.addStretch()
        self.__flare_hlay.addWidget(self.__flare_edit)

        self.__vlayout = QtGui.QVBoxLayout(self)
        self.__vlayout.addLayout(self.__numerical_aperture_hlay)
        self.__vlayout.addLayout(self.__reduction_ratio_hlay)
        self.__vlayout.addLayout(self.__flare_hlay)

        # self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)


class ImmersionBox(ParameterGroupBox):

    def __init__(self, parent, imaging_tool):
        """:type imaging_tool: options.structures.ImagingTool"""
        super(ImmersionBox, self).__init__("Immersion Lithography", parent)

        self.__imaging_tool = imaging_tool

        self.__immersion_enable_checkbox = QtGui.QCheckBox("Enable Immersion", self)
        connect(self.__immersion_enable_checkbox.stateChanged, self.immersionStateChanged)
        # TODO: Add immersion calculation
        self.__immersion_enable_checkbox.setEnabled(False)

        self.__refraction_index_label = QtGui.QLabel("Refractive Index:")
        self.__refraction_index_edit = self.edit(self.__imaging_tool.immersion)

        self.__hlayout = QtGui.QHBoxLayout(self)
        self.__hlayout.addWidget(self.__immersion_enable_checkbox)
        self.__hlayout.addStretch()
        self.__hlayout.addWidget(self.__refraction_index_label)
        self.__hlayout.addWidget(self.__refraction_index_edit)

        self.immersionStateChanged(self.__imaging_tool.immersion_enabled)

    # noinspection PyPep8Naming
    @Slot()
    def immersionStateChanged(self, immersion_enabled):
        self.__imaging_tool.immersion_enabled = immersion_enabled
        self.__refraction_index_label.setEnabled(immersion_enabled)
        self.__refraction_index_edit.setEnabled(immersion_enabled)


class ImagingView(QStackWidgetTab):
    def __init__(self, parent, opts, appdb):
        """
        :param QtGui.QWidget parent: Widget parent
        :param options.structures.Options opts: Current application options
        :param ApplicationDatabase appdb: Application database object
        """
        super(ImagingView, self).__init__(parent)

        self.__objective_lens = ObjectiveLensBox(self, opts.imaging_tool)
        self.__immersion = ImmersionBox(self, opts.imaging_tool)
        self.__spectrum = SpectrumBox(self, opts.imaging_tool)
        self.__source_shape = SourceShapeBox(self, opts.imaging_tool, appdb)
        self.__pupil_filer = PupilFilterBox(self, opts.imaging_tool, appdb)

        self.__vlayout_left = QtGui.QVBoxLayout()
        self.__vlayout_left.addWidget(self.__spectrum)
        self.__vlayout_left.addWidget(self.__source_shape)
        self.__vlayout_left.addWidget(self.__immersion)
        self.__vlayout_left.addStretch()

        # self.__vlayout_middle = QtGui.QVBoxLayout()
        # self.__vlayout_middle.addStretch()

        self.__vlayout_right = QtGui.QVBoxLayout()
        self.__vlayout_right.addWidget(self.__objective_lens)
        self.__vlayout_right.addWidget(self.__pupil_filer)
        self.__vlayout_right.addStretch()

        self.__hlayout = QtGui.QHBoxLayout(self)
        self.__hlayout.addLayout(self.__vlayout_left)
        # self.__hlayout.addLayout(self.__vlayout_middle)
        self.__hlayout.addLayout(self.__vlayout_right)
        self.__hlayout.addStretch()

    def reset(self):
        self.__source_shape.reset()
        self.__pupil_filer.reset()