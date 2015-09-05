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

import collections
import logging as module_logging

from qt import QtGui, QtCore, connect, Signal, Slot, GlobalSignals
from resources import Resources
from database import orm
from database.common import ApplicationDatabase
from views.common import QStackWidgetTab, QLineEditNumeric, QLabelMulti, \
    QGraphPlot, QuestionBox, msgBox, calculate_table_width

import options.structures

import config
import helpers


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


class MaterialPlot(QGraphPlot):

    def __init__(self, parent, stack_layer=None, width=600, height=300):
        """
        :type parent: QtGui.QWidget
        :type stack_layer: options.WaferStackLayer
        :type width: int
        :type height: int
        """
        QGraphPlot.__init__(self, parent, width=width, height=height)
        if stack_layer is not None:
            self.draw_layer(stack_layer)

    # noinspection PyPep8Naming
    def draw_layer(self, stack_layer, wavelength=None):
        """
        :type stack_layer: options.WaferStackLayer
        :type wavelength: float or None
        """
        self.clear()

        real_ax = self.add_subplot()
        imag_ax = real_ax.twinx()

        if wavelength is not None:
            re, im = stack_layer.refraction_at(wavelength)
            real_ax.set_title("Refractive index at %.0f nm: %.2f%+.2fi" % (wavelength, re, im))
        else:
            real_ax.set_title("Refractive index data of %s" % stack_layer.name)

        wvl = stack_layer.wavelength
        real, imag = stack_layer.refraction

        real_ax.plot(wvl, real, "r-", label="real")
        imag_ax.plot(wvl, imag, "g-", label="imag")

        real_ax.legend(loc=0)
        real_ax.grid()

        real_ax.set_xlabel("Wavelength (nm)")
        real_ax.set_ylabel("Refractive index (real)")
        imag_ax.set_ylabel("Refractive index (imag)")

        real_ax.patch.set_alpha(0.0)

        self.redraw()


class LoadMaterialDialog(QtGui.QDialog):

    def __init__(self, parent, appdb):
        """
        :type parent: QtGui.QMainWindow
        :type appdb: ApplicationDatabase
        """
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle("Load Material")
        self.setWindowIcon(parent.windowIcon())

        self.__appdb = appdb

        self.__select_group = QtGui.QGroupBox("Select Material", self)
        self.__select_group_layout = QtGui.QHBoxLayout(self.__select_group)
        self.__material_list = QtGui.QListWidget(self.__select_group)
        self.__select_group_layout.addWidget(self.__material_list)

        self.__material_plot = MaterialPlot(self)

        self.__buttons_layout = QtGui.QHBoxLayout()
        self.__parametric_checkbox = QtGui.QCheckBox("Parametric", self)
        self.__load_button = QtGui.QPushButton("Load material", self)
        self.__load_button.setFixedWidth(config.MAXIMUM_DIALOG_BUTTON_WIDTH)
        self.__cancel_button = QtGui.QPushButton("Cancel", self)
        self.__cancel_button.setFixedWidth(config.MAXIMUM_DIALOG_BUTTON_WIDTH)

        self.__buttons_layout.addWidget(self.__parametric_checkbox)
        self.__buttons_layout.addStretch()
        self.__buttons_layout.addWidget(self.__load_button)
        self.__buttons_layout.addWidget(self.__cancel_button)

        connect(self.__load_button.clicked, self.accept)
        connect(self.__cancel_button.clicked, self.reject)
        connect(self.__parametric_checkbox.stateChanged, self._accept_state_handler)
        connect(self.__material_list.itemSelectionChanged, self._accept_state_handler)
        connect(self.__material_list.itemSelectionChanged, self._change_material)

        self.__layout = QtGui.QVBoxLayout(self)
        self.__layout.addWidget(self.__select_group)
        self.__layout.addWidget(self.__material_plot)
        self.__layout.addLayout(self.__buttons_layout)

        self.__parametric_checkbox.setCheckState(QtCore.Qt.Unchecked)
        self._accept_state_handler()

    def update_materials(self):
        self.__material_list.clear()
        for material in self.__appdb[orm.Material]:
            self.__material_list.addItem(material.name)

    def showEvent(self, *args, **kwargs):
        self.update_materials()
        super(LoadMaterialDialog, self).showEvent(*args, **kwargs)

    # noinspection PyUnusedLocal
    def _accept_state_handler(self, *args):
        self.__select_group.setEnabled(not self.is_parametric)
        self.__material_plot.setEnabled(not self.is_parametric)
        self.__load_button.setEnabled(self.is_parametric or self.is_item_selected)

    def _change_material(self):
        # material = self.__appdb[orm.Material].filter(orm.Material.name == self.material).one()
        if self.material is not None:
            self.__material_plot.draw_layer(options.structures.Substrate(self.material))

    @property
    def material(self):
        """:rtype: orm.Material or None"""
        if self.is_parametric:
            return None

        name = str(self.__material_list.currentItem().text())
        return self.__appdb[orm.Material].filter(orm.Material.name == name).one()

    @property
    def is_item_selected(self):
        return bool(self.__material_list.selectedItems())

    @property
    def is_parametric(self):
        return bool(self.__parametric_checkbox.checkState())


class QProcessStackModel(QtCore.QAbstractTableModel):

    class ColumnDescriptor(object):
        def __init__(self, index, name, width, flags):
            """
            :param int index: Index of table column
            :param str name: Name of the column
            :param int width: Width of the column
            :param int flags: Column flags
            """
            self.index = index
            self.name = name
            self.width = width
            self.flags = flags

        def __eq__(self, other):
            """:type other: int"""
            return self.index == other

    colormap = ["#B89F9F", "#61A1C2", "#CCD7C1", "#7CABA4", "#DEC68B", "#D2A882", "#B18D9E", "#8F6169",
                "#DEBF56", "#C4D19A", "#73BB9C", "#8CA5C1", "#9AC9C9", "#ECDA9D", "#BD8C8F", "#74A9AF",
                "#888EBD", "#B6ABAD", "#BC9481", "#2E8B57", "#B8860B", "#8B0A50", "#473C8B", "#8B3A3A",
                "#EEE9BF", "#4682B4", "#D8BFD8", "#CDBA96", "#B03060", "#8B7355", "#8B7355"]

    READONLY = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
    EDITABLE = QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    height = 20

    columns = collections.OrderedDict([
        ("Step", ColumnDescriptor(index=0, name="Step", width=48, flags=READONLY)),
        ("Type", ColumnDescriptor(index=1, name="Type", width=80, flags=READONLY)),
        ("Name", ColumnDescriptor(index=2, name="Name", width=140, flags=READONLY)),
        ("Thickness", ColumnDescriptor(index=3, name="Thickness", width=70, flags=EDITABLE))
    ])
    """:type: dict from str to QProcessStackModel.ColumnDescriptor"""

    def __init__(self, parent, wafer_process):
        """
        :type parent: QtGui.QWidget
        :type wafer_process: options.WaferProcess
        """
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._wafer_process = wafer_process

    def __getitem__(self, item):
        """
        :type item: int
        :rtype: options.WaferStackLayer
        """
        return self._wafer_process[item]

    def __setitem__(self, row, layer):
        """
        :type row: int
        :type layer: options.WaferStackLayer
        """
        self._wafer_process[row] = layer
        self.rowChanged(row)

    # noinspection PyPep8Naming
    def rowChanged(self, row):
        """:type row: int"""
        # noinspection PyUnresolvedReferences
        self.dataChanged.emit(self.createIndex(row, 0), self.createIndex(row, self.columnCount()-1))

    @property
    def resist(self):
        """:rtype: options.Resist"""
        return self._wafer_process.resist

    @property
    def substrate(self):
        """:rtype: options.Substrate"""
        return self._wafer_process.substrate

    def headerData(self, section, orientation, role=None):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return QProcessStackModel.columns.values()[section].name
            elif orientation == QtCore.Qt.Vertical:
                return str(len(self._wafer_process) - section)
        return None

    def columnCount(self, index_parent=None, *args, **kwargs):
        return len(QProcessStackModel.columns)

    def rowCount(self, index_parent=None, *args, **kwargs):
        return len(self._wafer_process)

    def flags(self, index):
        """:type index: QtCore.QModelIndex"""
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        if index.column() == QProcessStackModel.columns["Thickness"] and \
           isinstance(self._wafer_process[index.row()], options.structures.Substrate):
            return QProcessStackModel.READONLY

        return QProcessStackModel.columns.values()[index.column()].flags

    def data(self, index, role=None):
        """
        :type index: QtCore.QModelIndex
        :type role: int
        """
        if index.isValid() and index.row() < len(self._wafer_process):
            if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
                stack_layer = self._wafer_process[index.row()]
                if index.column() == QProcessStackModel.columns["Step"]:
                    return str(len(self._wafer_process) - index.row())
                elif index.column() == QProcessStackModel.columns["Type"]:
                    return str(stack_layer.type)
                elif index.column() == QProcessStackModel.columns["Name"]:
                    return str(stack_layer.name)
                elif index.column() == QProcessStackModel.columns["Thickness"]:
                    if isinstance(stack_layer, options.structures.StandardLayer):
                        return str(stack_layer.thickness)
                    elif isinstance(stack_layer, options.structures.Substrate):
                        return None
            elif role == QtCore.Qt.SizeHintRole:
                width = QProcessStackModel.columns.values()[index.column()].width
                return QtCore.QSize(width, QProcessStackModel.height)
            elif role == QtCore.Qt.BackgroundColorRole:
                if index.column() == QProcessStackModel.columns["Step"]:
                    return QtGui.QColor(QProcessStackModel.colormap[index.row()])
        return None

    def setData(self, index, value, role=None):
        """
        :type index: QtCore.QModelIndex
        :type value: QtCore.QVariant
        :type role: int
        :rtype: bool
        """
        if not index.isValid() or role != QtCore.Qt.EditRole:
            return False

        if index.column() == QProcessStackModel.columns["Thickness"]:
            stack_layer = self._wafer_process[index.row()]
            if isinstance(stack_layer, (options.structures.StandardLayer, options.structures.Resist)):
                # try:
                #     stack_layer.thickness = float(value)
                # except ValueError:
                #     return False
                #
                # return True
                try:
                    thickness = float(value)
                except ValueError:
                    return False
                else:
                    if stack_layer.thickness != thickness:
                        stack_layer.thickness = thickness
                        GlobalSignals.changed.emit()
                    return True

        return False

    # noinspection PyMethodOverriding
    def insertRow(self, row, stack_layer):
        index = QtCore.QModelIndex()
        self.beginInsertRows(index, row, row)
        self._wafer_process.insert(row, stack_layer)
        self.endInsertRows()

        GlobalSignals.changed.emit()
        return True

    # noinspection PyMethodOverriding
    def removeRow(self, row):
        index = QtCore.QModelIndex()
        self.beginRemoveRows(index, row, row)
        self._wafer_process.remove(row)
        self.endRemoveRows()

        GlobalSignals.changed.emit()
        return True

    # noinspection PyPep8Naming
    def moveRows(self, source_row, dest_row):
        if source_row == dest_row:
            return False

        # PyQt4 crash if source index lower than destination index
        if source_row < dest_row:
            source_row, dest_row = dest_row, source_row

        wp = self._wafer_process
        source_parent = QtCore.QModelIndex()
        dest_parent = QtCore.QModelIndex()
        self.beginMoveRows(source_parent, source_row, source_row, dest_parent, dest_row)
        wp[source_row], wp[dest_row] = wp[dest_row], wp[source_row]
        self.endMoveRows()

        GlobalSignals.changed.emit()
        return True


class QProcessStackTable(QtGui.QTableView):

    def __init__(self, parent, model):
        """
        :type parent: QtGui.QWidget
        :type model: QProcessStackModel
        """
        QtGui.QTableView.__init__(self, parent)
        self.setModel(model)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.horizontalHeader().setClickable(False)
        self.verticalHeader().setClickable(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(QProcessStackModel.height)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.resizeColumnsToContents()
        self.setMinimumWidth(calculate_table_width(self))

    def current_row(self):
        """:rtype: int"""
        return self.selectionModel().currentIndex().row()


class QProcessStack(QtGui.QGroupBox):

    rowChanged = Signal(int)

    def _create_button(self, icon_directory, handler):
        button = QtGui.QPushButton(str(), self)
        button.setIcon(Resources(icon_directory))
        button.setIconSize(QtCore.QSize(26, 26))
        button.setFixedSize(QtCore.QSize(36, 36))
        button.setEnabled(False)
        connect(button.clicked, handler)
        self.__header_layout.addWidget(button)
        return button

    def __init__(self, parent, model, load_dialog):
        """
        :param QtGui.QWidget parent: Widget parent
        :param QProcessStackModel model: GUI data model
        :param LoadMaterialDialog load_dialog: Material dialog loader
        """
        QtGui.QGroupBox.__init__(self, "Process Stack", parent)
        self.setObjectName("QProcessStack")

        self.__data_model = model
        self.__load_material_dlg = load_dialog

        self.__header_layout = QtGui.QHBoxLayout()
        self.__add_button = self._create_button("icons/Plus", self.insert_layer)
        self.__remove_button = self._create_button("icons/Minus", self.remove_layer)
        self.__up_button = self._create_button("icons/ArrowUp", self.layer_upper)
        self.__down_button = self._create_button("icons/ArrowDown", self.layer_lower)
        self.__header_layout.addStretch(1)

        self.__process_table = QProcessStackTable(self, self.__data_model)
        
        # PySide crash if not create temporary variable 
        selection_model = self.__process_table.selectionModel()
        connect(selection_model.selectionChanged, self._item_changed)
        # Even selection automatically changed when endMoveRows perform selectionChanged not emitted
        connect(self.__data_model.rowsMoved, self._item_changed)

        self.__layout = QtGui.QVBoxLayout(self)
        self.__layout.addLayout(self.__header_layout)
        self.__layout.addWidget(self.__process_table)

    def _can_stack_be_edit(self, *rows):
        """
        Check if layer can be removed, move up or down in the stack

        :type rows: tuple of int
        :rtype: bool
        """
        for row in rows:
            if row >= self.__data_model.rowCount() or \
               isinstance(self.__data_model[row], (options.structures.Substrate, options.structures.Resist)):
                return False
        return True

    @Slot(QtCore.QModelIndex, int, int, QtCore.QModelIndex, int)
    @Slot(QtGui.QItemSelection, QtGui.QItemSelection)
    def _item_changed(self, *args):
        self.__add_button.setEnabled(True)

        row = self.__process_table.current_row()

        self.__remove_button.setEnabled(self._can_stack_be_edit(row))

        # Because the top layer always must be resist
        self.__up_button.setEnabled(self._can_stack_be_edit(row-1, row))
        # Because bottom layer always must be substrate
        self.__down_button.setEnabled(self._can_stack_be_edit(row, row+1))

        self.rowChanged.emit(row)

    def insert_layer(self):
        logging.info("Insert layer")
        if self.__load_material_dlg.exec_():
            logging.info("%s, parametric: %s" %
                         (self.__load_material_dlg.material,
                          self.__load_material_dlg.is_parametric))
            # If top layer selected then add index because top layer must be resist
            row = self.__process_table.current_row() if self.__process_table.current_row() != 0 else 1

            if self.__load_material_dlg.is_parametric:
                stack_layer = options.structures.StandardLayer.parametric(
                    self.__data_model.resist.exposure.wavelength,
                    config.DEFAULT_LAYER_REAL_INDEX,
                    config.DEFAULT_LAYER_IMAG_INDEX,
                    config.DEFAULT_LAYER_THICKNESS)
            else:
                stack_layer = options.structures.StandardLayer(
                    self.__load_material_dlg.material, config.DEFAULT_LAYER_THICKNESS)

            self.__data_model.insertRow(row, stack_layer)
            self.__process_table.selectRow(row)

    def remove_layer(self):
        self.__data_model.removeRow(self.__process_table.current_row())

    def layer_upper(self):
        row = self.__process_table.current_row()
        self.__data_model.moveRows(row, row-1)

    def layer_lower(self):
        row = self.__process_table.current_row()
        self.__data_model.moveRows(row+1, row)

    def current_row(self):
        return self.__process_table.current_row()


class QProcessStepResistConfig(QStackWidgetTab):

    def __init__(self, parent):
        """:type parent: QtGui.QWidget"""
        QStackWidgetTab.__init__(self, parent)
        self.__label = QtGui.QLabel("Resist can be loaded from application database or "
                                    "resist parameters could be changed at \"Resist\" tabs")
        self.__label.setAlignment(QtCore.Qt.AlignCenter)
        self.__label.setWordWrap(True)
        self.__layout = QtGui.QVBoxLayout(self)
        self.__layout.addWidget(self.__label)
        self.__layout.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        self.__layout.addStretch()


class QProcessStepDepositDbConfig(QStackWidgetTab):

    def __init__(self, parent):
        """:type parent: QtGui.QWidget"""
        QStackWidgetTab.__init__(self, parent)
        self.material_plot = MaterialPlot(self, width=500, height=250)
        self.__layout = QtGui.QVBoxLayout(self)
        self.__layout.addWidget(self.material_plot)


class QProcessStepDepositPrmConfig(QStackWidgetTab):

    class IndexEdit(QLineEditNumeric):
        def __init__(self, *__args):
            QLineEditNumeric.__init__(self, *__args)
            self.setAlignment(QtCore.Qt.AlignRight)
            self.setMinimumWidth(50)
            self.setMaximumWidth(100)

    def __init__(self, parent):
        """:type parent: QtGui.QWidget"""
        QStackWidgetTab.__init__(self, parent)
        self.__layout = QtGui.QVBoxLayout(self)
        self.__layout_form = QtGui.QFormLayout()

        self.__real = self.IndexEdit(self)
        self.__imag = self.IndexEdit(self)

        self.__label = QLabelMulti(self, frmt="Refractive index %.3f+%.3fi @ wavelength %.1f nm")
        self.__label.setAlignment(QtCore.Qt.AlignCenter)

        self.__layout.addWidget(self.__label)
        self.__layout_form.addRow("Real part:", self.__real)
        self.__layout_form.addRow("Imag part:", self.__imag)
        self.__layout.addLayout(self.__layout_form)
        self.__layout.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)

    # noinspection PyPep8Naming
    def setObjects(self, layer, resist):
        """
        :type layer: options.structures.MaterialLayer or options.structures.Substrate
        :type resist: options.Resist
        """
        self.__label.setObject([
            (layer, options.structures.MaterialLayer.real),
            (layer, options.structures.MaterialLayer.imag),
            (resist.exposure, orm.ExposureParameters.wavelength)
        ])
        self.__real.setObject(layer, options.structures.MaterialLayer.real)
        self.__imag.setObject(layer, options.structures.MaterialLayer.imag)


class QProcessStepProperty(QtGui.QGroupBox):

    def __init__(self, parent, model, appdb, load_dialog):
        """
        :param QtGui.QWidget parent: Widget parent
        :param QProcessStackModel model: GUI data model
        :param ApplicationDatabase appdb: Application database
        :param LoadMaterialDialog load_dialog: Material dialog loader
        """
        QtGui.QGroupBox.__init__(self, "Process Properties Step", parent)
        self.setObjectName("QProcessStepProperty")

        self.__data_model = model
        self.__appdb = appdb
        self.__load_material_dlg = load_dialog
        self.__current_row = None

        self.__layout = QtGui.QVBoxLayout(self)

        self.__label_name = QtGui.QLabel("Name:")
        self.__edit_name = QtGui.QLineEdit()
        self.__edit_name.setFixedWidth(250)

        self.__load_button = QtGui.QPushButton("Load")
        connect(self.__load_button.clicked, self._load_material)

        self.__save_button = QtGui.QPushButton("Save to database")
        connect(self.__save_button.clicked, self._save_material)

        self._controls_set_enabled(False)

        self.__header_layout = QtGui.QHBoxLayout()
        self.__header_layout.setObjectName("QProcessStepProperty.QHBoxLayout")
        self.__header_layout.addWidget(self.__label_name)
        self.__header_layout.addWidget(self.__edit_name)
        self.__header_layout.addWidget(self.__load_button)
        self.__header_layout.addWidget(self.__save_button)

        self.__parameters_widgets = QtGui.QStackedWidget(self)
        self.__db_view = QProcessStepDepositDbConfig(self)
        self.__prm_view = QProcessStepDepositPrmConfig(self)
        self.__resist_view = QProcessStepResistConfig(self)
        self.__parameters_widgets.addWidget(self.__db_view)
        self.__parameters_widgets.addWidget(self.__prm_view)
        self.__parameters_widgets.addWidget(self.__resist_view)

        self.__layout.addLayout(self.__header_layout)
        self.__layout.addWidget(self.__parameters_widgets)

    def _load_material(self):
        if self.__load_material_dlg.exec_():
            # FIXME: Exception here self.__current_row IndexError
            wavelength = self.__data_model.resist.exposure.wavelength
            layer_class = type(self.__data_model[self.__current_row])
            layer = layer_class.default_parametric(wavelength) if self.__load_material_dlg.is_parametric \
                else layer_class.db_stored(self.__load_material_dlg.material, config.DEFAULT_LAYER_THICKNESS)

            self.__data_model[self.__current_row] = layer
            self.changeMaterial(self.__current_row)
            GlobalSignals.changed.emit()

    def _save_material(self):
        row = self.__current_row

        material = self.__data_model[row].db.clone()
        material.name = str(self.__edit_name.text())

        if QProcessStepProperty.AddObjectToDb(self, self.__appdb, material):
            layer_class = type(self.__data_model[row])
            self.__data_model[row] = layer_class.db_stored(material, config.DEFAULT_LAYER_THICKNESS)
            self.changeMaterial(row)

    # noinspection PyPep8Naming
    @staticmethod
    def AddObjectToDb(parent, appdb, p_object):
        """
        :type parent: QtGui.QWidget
        :type appdb: ApplicationDatabase
        :type p_object: orm.Generic
        """
        try:
            appdb.add(p_object)
        except ApplicationDatabase.ObjectExisted as existed:
            replay = QuestionBox(
                parent, "%s \"%s\" already existed, replace it?" %
                        (existed.object.identifier, existed.object.name)
            )
            if replay == msgBox.Yes:
                appdb.replace(existed.object)
            else:
                return False

        return True

    def _controls_set_enabled(self, enabled):
        """:type enabled: bool"""
        self.__edit_name.setEnabled(enabled)
        self.__load_button.setEnabled(enabled)
        self.__save_button.setEnabled(enabled)

    # noinspection PyPep8Naming
    @Slot(int)
    def changeMaterial(self, index):
        layer = self.__data_model[index]
        resist = self.__data_model.resist
        self.__current_row = index
        self.setTitle("Process Properties Step: %d Type: %s" % (self.__data_model.rowCount() - index, layer.type))

        if isinstance(layer, options.structures.Resist):
            self.__parameters_widgets.setCurrentWidget(self.__resist_view)
            self._controls_set_enabled(False)
        elif isinstance(layer, (options.structures.Substrate, options.structures.StandardLayer)):
            if layer.is_parametric:
                self.__parameters_widgets.setCurrentWidget(self.__prm_view)
                self.__prm_view.setObjects(layer, resist)
            else:
                self.__parameters_widgets.setCurrentWidget(self.__db_view)
                self.__db_view.material_plot.draw_layer(layer, self.__data_model.resist.exposure.wavelength)
            self._controls_set_enabled(True)

        self.__edit_name.setText(layer.name)


class WaferProcessView(QStackWidgetTab):
    def __init__(self, parent, wafer_process, appdb):
        """
        :type parent: QtGui.QWidget
        :param options.WaferProcess wafer_process: Wafer stack process options
        :type appdb: ApplicationDatabase
        """
        QStackWidgetTab.__init__(self, parent)
        self.setObjectName("WaferProcessView")
        self.__wafer_process = wafer_process
        self.__appdb = appdb

        self.__load_material_dlg = LoadMaterialDialog(self, self.__appdb)

        self.__data_model = QProcessStackModel(self, wafer_process)
        self.__process_stack = QProcessStack(self, self.__data_model, self.__load_material_dlg)
        self.__process_step_property = QProcessStepProperty(
            self, self.__data_model, self.__appdb, self.__load_material_dlg)
        
        self.__layout = QtGui.QGridLayout()
        self.__layout.addWidget(self.__process_stack, 0, 0)
        self.__layout.addWidget(self.__process_step_property, 0, 1)

        connect(self.__process_stack.rowChanged, self.__process_step_property.changeMaterial)

        self.setUnstretchable(self.__layout)

    def reset(self):
        self.__data_model.reset()
        self.__process_step_property.changeMaterial(self.__process_stack.current_row())