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

from copy import deepcopy
from auxmath import cartesian
from numpy import arange, array, ndarray, savetxt, NaN
from cStringIO import StringIO
from config import COMMON_LINES_COLOR
from qt import QtGui, QtCore, connect, disconnect, Signal, Slot
from views.common import QObjectNumeric, QStackWidgetTab, QGraphPlot, calculate_table_width, msgBox, NavigationToolbar
from options.structures import Options, AbstractOptionsBase, Variable, StandardLayer, Resist, Numeric
from database.orm import StandardObject, ConcretePluginCommon, DeveloperExprArgValue, \
    DeveloperInterface, DeveloperExpr, DeveloperSheet, PebParameters, ExposureParameters
from resources import Resources

import helpers


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


_MINIMUM_HEIGHT = 230


def thread_name():
    # noinspection PyArgumentList
    return QtCore.QThread.currentThread().objectName()


def listify(data):
    return [str(value) for index, value in sorted(data.iteritems())]


class AbstractGroupBox(QtGui.QGroupBox):

    def __init__(self, title, parent):
        super(AbstractGroupBox, self).__init__(title, parent)

    # noinspection PyPep8Naming
    def setObject(self, options):
        pass


class InputVariablesTree(QtGui.QTreeWidget):

    NAME_COLUMN = 0
    VALUE_COLUMN = 1
    INDEX_COLUMN = 2

    HEADER = {
        INDEX_COLUMN: "VariableIndex",
        NAME_COLUMN: "Variable name",
        VALUE_COLUMN: "Value",
    }

    EXPOSURE_N_NAME = "Exposure Resist n"
    EXPOSURE_A_NAME = "Exposure Dill A"
    EXPOSURE_B_NAME = "Exposure Dill B"
    EXPOSURE_C_NAME = "Exposure Dill C"

    PEB_LN_AR_NAME = "PEB Ln(Ar)"
    PEB_EA_NAME = "PEB Ea"

    THICKNESS = "Thickness"
    REFRACTIVE_INDEX_REAL = "Refractive Index Real"
    REFRACTIVE_INDEX_IMAG = "Refractive Index Imag"

    SELECTABLE = QtCore.Qt.ItemIsSelectable

    def __init__(self, parent, options):
        """
        :param QtGui.QWidget parent: Parent
        :param options.structures.Options options: Program options
        """
        super(InputVariablesTree, self).__init__(parent)
        self.setColumnCount(3)
        self.setColumnWidth(InputVariablesTree.INDEX_COLUMN, 40)
        self.setColumnWidth(InputVariablesTree.NAME_COLUMN, 250)
        self.setColumnWidth(InputVariablesTree.VALUE_COLUMN, 40)
        self.setHeaderLabels(listify(InputVariablesTree.HEADER))

        self.setColumnHidden(InputVariablesTree.INDEX_COLUMN, True)

        self.setMinimumHeight(_MINIMUM_HEIGHT)
        self.setFixedWidth(400)

        self.__root = self.invisibleRootItem()

        self.__options = None
        """:type: options.structures.Options"""

        self.__nodes = dict()
        """:type: dict[int, QObjectNumeric]"""
        self.__counter = 0

        self.setObject(options)

    @staticmethod
    def set_selectable(row, value):
        flags = row.flags() | InputVariablesTree.SELECTABLE \
            if value else row.flags() & ~InputVariablesTree.SELECTABLE
        row.setFlags(flags)

    def variable_by_indx(self, index):
        return self.__nodes[index]

    def indx_by_variable(self, variable):
        for indx, stored_variable in self.__nodes.iteritems():
            if variable.object == stored_variable.object:
                return indx
        return None

    def lookup_item(self, check):
        def __search(_node):
            for _k in xrange(_node.childCount()):
                _child = _node.child(_k)
                # logging.info("Node = %s value = %s index = %r/%r" %
                #              (_child.text(0), _child.text(1), _child.text(2), index))
                if check(_child):
                    return _child
                _result = __search(_child)
                if _result is not None:
                    return _result
            return None

        for k in xrange(self.__root.childCount()):
            node = self.__root.child(k)
            result = __search(node)
            if result is not None:
                return result

    def item_by_indx(self, index):
        return self.lookup_item(lambda node: node.text(InputVariablesTree.INDEX_COLUMN) == index)

    def item_by_name(self, name):
        return self.lookup_item(lambda node: node.text(InputVariablesTree.NAME_COLUMN) == name)

    def clear(self):
        super(InputVariablesTree, self).clear()
        self.__nodes.clear()
        self.__counter = 0
        self.__root = self.invisibleRootItem()

    def __add_indexed_node(self, root, container, field=Numeric, title=None):
        self.__counter += 1

        index_str = str(self.__counter)
        name_str = title if title is not None else container.name

        wrapper = QObjectNumeric(self, container, field)

        data = {
            self.INDEX_COLUMN: index_str,
            self.NAME_COLUMN: name_str,
            self.VALUE_COLUMN: str(wrapper.value)
        }

        self.__nodes[index_str] = wrapper

        values = listify(data)
        # logging.info("Add indexed node: %s" % values)

        node = QtGui.QTreeWidgetItem(values)
        root.addChild(node)
        return node

    def __add_header_node(self, root, name, value=None):
        value_str = str(value) if value is not None else str()

        data = {
            self.INDEX_COLUMN: str(),
            self.NAME_COLUMN: str(name),
            self.VALUE_COLUMN: value_str
        }

        node = QtGui.QTreeWidgetItem(listify(data))
        root.addChild(node)
        return node

    def __add_wafer_process(self, root, wafer_stack):
        node_stack = self.__add_header_node(root, "Wafer Process")
        for stack_layer in wafer_stack:
            node_layer = self.__add_header_node(node_stack, stack_layer.name)
            if isinstance(stack_layer, StandardLayer):
                self.__add_indexed_node(node_layer, stack_layer, StandardLayer.thickness, title=self.THICKNESS)
            if not isinstance(stack_layer, Resist) and stack_layer.is_parametric:
                self.__add_indexed_node(node_layer, stack_layer, StandardLayer.real, title=self.REFRACTIVE_INDEX_REAL)
                self.__add_indexed_node(node_layer, stack_layer, StandardLayer.imag, title=self.REFRACTIVE_INDEX_IMAG)

    def __add_exposure(self, root, exposure):
        self.__add_indexed_node(root, exposure, ExposureParameters.n, self.EXPOSURE_N_NAME)
        self.__add_indexed_node(root, exposure, ExposureParameters.a, self.EXPOSURE_A_NAME)
        self.__add_indexed_node(root, exposure, ExposureParameters.b, self.EXPOSURE_B_NAME)
        self.__add_indexed_node(root, exposure, ExposureParameters.c, self.EXPOSURE_C_NAME)

    def __add_peb(self, root, peb):
        self.__add_indexed_node(root, peb, PebParameters.ln_ar)
        self.__add_indexed_node(root, peb, PebParameters.ea)

    def __add_developer(self, root, field):
        """:type field: DeveloperInterface"""
        if isinstance(field, DeveloperExpr):
            for arg, value_object in zip(field.model.args, field.object_values):
                self.__add_indexed_node(root, value_object, DeveloperExprArgValue.value, title=arg.name)
        elif isinstance(field, DeveloperSheet):
            self.__add_header_node(root, "Development model", field.name)

    def __add_resist(self, root, resist):
        """
        :type root: QtGui.QTreeWidgetItem
        :type resist: options.structures.Resist
        """
        node = self.__add_header_node(root, "Resist", resist.name)
        self.__add_exposure(node, resist.exposure)
        self.__add_peb(node, resist.peb)
        self.__add_developer(node, resist.developer)

    def __add_variable(self, root, p_object):
        self.__add_indexed_node(root, p_object)

    def __add_plugin_object(self, root, plugin):
        """
        :type root: QtGui.QTreeWidgetItem
        :type plugin: ConcretePluginCommon
        """
        node = self.__add_header_node(root, str(plugin._base.title), plugin.name)
        for variable in plugin.variables:
            self.__add_variable(node, variable)

    # noinspection PyMethodMayBeStatic
    def __add_db_object(self, root, p_object):
        """:type p_object: orm.Generic or StandardObject"""
        self.__add_header_node(root, p_object.title, p_object.name)

    def __add_composite(self, root, composite):
        """
        :type composite: options.structures.AbstractOptionsBase or
                         orm.Generic or orm.ConcretePluginCommon
        """
        name = composite.identifier if isinstance(composite, AbstractOptionsBase) else composite.name
        node = self.__add_header_node(root, name)
        for name, field in composite.__dict__.iteritems():
            if isinstance(field, Variable):
                self.__add_variable(node, field)
            elif isinstance(field, StandardObject):
                self.__add_db_object(node, field)
            elif isinstance(field, ConcretePluginCommon):
                self.__add_plugin_object(node, field)

    def check_variable(self, item):
        index = item.text(InputVariablesTree.INDEX_COLUMN)
        name = item.text(InputVariablesTree.NAME_COLUMN)
        item.setIcon(InputVariablesTree.NAME_COLUMN, Resources("icons/Ok"))
        self.set_selectable(item, False)
        variable = self.variable_by_indx(index)
        self.clearSelection()
        return name, index, variable

    def uncheck_variable(self, index):
        item = self.item_by_indx(index)
        item.setIcon(InputVariablesTree.NAME_COLUMN, QtGui.QIcon())
        self.set_selectable(item, True)

    # noinspection PyPep8Naming
    def setObject(self, options):
        """:param options.structures.Options options: Program options"""
        self.clear()
        self.__options = options
        self.__add_wafer_process(self.__root, self.__options.wafer_process)
        self.__add_resist(self.__root, self.__options.wafer_process.resist)
        self.__add_composite(self.__root, self.__options.mask)
        self.__add_composite(self.__root, self.__options.imaging_tool)
        self.__add_composite(self.__root, self.__options.exposure_focus)
        self.__add_composite(self.__root, self.__options.peb)
        self.__add_composite(self.__root, self.__options.development)

    def set_expand_collapse_all(self, expand):
        def __recursive(_node):
            for _k in xrange(_node.childCount()):
                _child = _node.child(_k)
                __recursive(_child)
                _child.setExpanded(expand)
            _node.setExpanded(expand)

        for k in xrange(self.__root.childCount()):
            __recursive(self.__root.child(k))


class InputVariablesTable(QtGui.QTableWidget):

    ORD_COLUMN = 0
    NAME_COLUMN = 1
    START_COLUMN = 2
    STOP_COLUMN = 3
    INTERVAL_COLUMN = 4
    INDEX_COLUMN = 5

    CHANGEABLE_COLUMNS = [START_COLUMN, STOP_COLUMN, INTERVAL_COLUMN]

    HEADER = {
        ORD_COLUMN: "#",
        NAME_COLUMN: "Variable name",
        START_COLUMN: "Start",
        STOP_COLUMN: "Stop",
        INTERVAL_COLUMN: "Interval",
        INDEX_COLUMN: "VariableIndex"
    }

    OVERSIZE = 0
    HEIGHT = 20

    ENABLED = QtCore.Qt.ItemIsEnabled
    READONLY = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
    EDITABLE = QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    variablesChanged = Signal(list)
    valuesChanged = Signal(dict)

    def __init__(self, parent):
        """
        :param QtGui.QWidget parent: Widget parent
        """
        super(InputVariablesTable, self).__init__(parent)

        self.setColumnCount(6)
        self.setColumnWidth(InputVariablesTable.ORD_COLUMN, 40)
        self.setColumnWidth(InputVariablesTable.NAME_COLUMN, 200)
        self.setColumnWidth(InputVariablesTable.START_COLUMN, 60)
        self.setColumnWidth(InputVariablesTable.STOP_COLUMN, 60)
        self.setColumnWidth(InputVariablesTable.INTERVAL_COLUMN, 60)
        self.setHorizontalHeaderLabels(listify(InputVariablesTable.HEADER))

        self.setColumnHidden(InputVariablesTable.INDEX_COLUMN, True)

        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.horizontalHeader().setClickable(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(self.HEIGHT)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.setFixedWidth(calculate_table_width(self) + self.OVERSIZE)
        self.setMinimumHeight(_MINIMUM_HEIGHT)

        connect(self.itemChanged, self.onItemChanged)

        self.__variables = list()
        self.__values = dict()

    def clearContents(self, *args, **kwargs):
        super(InputVariablesTable, self).clearContents(*args, **kwargs)
        self.setRowCount(0)
        self.__variables = list()
        self.__values = dict()

    def __reord_rows(self):
        for k in xrange(self.rowCount()):
            ord_item = QtGui.QTableWidgetItem(str(k + 1))
            ord_item.setFlags(InputVariablesTable.READONLY)
            ord_item.setTextAlignment(QtCore.Qt.AlignRight)
            self.setItem(k, InputVariablesTable.ORD_COLUMN, ord_item)

    def add_variable(self, name, index, wrapper):
        row = self.rowCount()

        self.__variables.append(wrapper)
        self.__values[wrapper] = dict()

        self.setRowCount(row + 1)
        name_item = QtGui.QTableWidgetItem(name)
        index_item = QtGui.QTableWidgetItem(str(index))
        for item in (name_item, index_item):
            item.setFlags(InputVariablesTable.READONLY)
        self.setItem(row, InputVariablesTable.NAME_COLUMN, name_item)
        self.setItem(row, InputVariablesTable.START_COLUMN, QtGui.QTableWidgetItem())
        self.setItem(row, InputVariablesTable.STOP_COLUMN, QtGui.QTableWidgetItem())
        self.setItem(row, InputVariablesTable.INTERVAL_COLUMN, QtGui.QTableWidgetItem())
        self.setItem(row, InputVariablesTable.INDEX_COLUMN, index_item)
        self.setRowHeight(row, InputVariablesTable.HEIGHT)
        self.__reord_rows()

        self.variablesChanged.emit(self.__variables)

        return row

    @property
    def variables(self):
        return self.__variables

    @property
    def values(self):
        return self.__values

    def remove_variable(self, row):
        del self.__values[self.__variables[row]]
        self.__variables.remove(self.__variables[row])
        self.removeRow(row)
        self.__reord_rows()
        self.variablesChanged.emit(self.__variables)

    VALUES_DICT_MAP = {
        START_COLUMN: "START",
        STOP_COLUMN: "STOP",
        INTERVAL_COLUMN: "INTERVAL"
    }

    # noinspection PyPep8Naming
    @Slot(QtGui.QTreeWidgetItem)
    def onItemChanged(self, item):
        row = item.row()
        col = item.column()
        # logging.info("Current row/col: %s %s" % (row, col))
        if row != -1 and col in InputVariablesTable.CHANGEABLE_COLUMNS:
            variable = self.__variables[row]
            key = self.VALUES_DICT_MAP[col]
            try:
                self.__values[variable][key] = float(item.text())
                # logging.info("Change [%s, %s]: %s -> %s" % (row, col, self.__values[variable][key], item.text()))
            except ValueError:
                item.setText(str())
                # logging.info("Change [%s, %s]: (rejected)" % (row, col))
            else:
                self.valuesChanged.emit(self.__values)
                # logging.info("Emit value %s" % self.__values)


class InputVariablesBox(AbstractGroupBox):

    MAX_VARIABLES = 2

    variablesChanged = Signal(list)
    valuesChanged = Signal(dict)

    def __init__(self, parent, options):
        """
        :param QtGui.QWidget parent: Parent
        :param options.structures.Options options: Program options
        """
        super(InputVariablesBox, self).__init__("Input variables", parent)
        self.__options = options

        self.__tree_layout = QtGui.QVBoxLayout()
        self.__input_variables_tree = InputVariablesTree(self, self.__options)
        connect(self.__input_variables_tree.itemSelectionChanged, self.onTreeSelectionChanged)

        self.__button_expand_all = QtGui.QPushButton("Expand all", self)
        self.__button_collapse_all = QtGui.QPushButton("Collapse all", self)
        connect(self.__button_expand_all.clicked, self.onExpandAllClicked)
        connect(self.__button_collapse_all.clicked, self.onCollapseAllClicked)
        self.__buttons_colexp_layout = QtGui.QHBoxLayout()
        self.__buttons_colexp_layout.addWidget(self.__button_expand_all)
        self.__buttons_colexp_layout.addWidget(self.__button_collapse_all)

        self.__tree_layout.addWidget(self.__input_variables_tree)
        self.__tree_layout.addLayout(self.__buttons_colexp_layout)

        self.__buttons_addrem_layout = QtGui.QVBoxLayout()
        self.__button_add = QtGui.QPushButton("+", self)
        self.__button_remove = QtGui.QPushButton("-", self)
        self.__button_add.setEnabled(False)
        self.__button_remove.setEnabled(False)
        connect(self.__button_add.clicked, self.onAddVariableButtonClicked)
        connect(self.__button_remove.clicked, self.onRemoveVariableButtonClicked)
        self.__buttons_addrem_layout.addWidget(self.__button_add)
        self.__buttons_addrem_layout.addWidget(self.__button_remove)

        self.__input_variables_table = InputVariablesTable(self)
        connect(self.__input_variables_table.itemSelectionChanged, self.onTableSelectionChanged)
        connect(self.__input_variables_table.variablesChanged, self.onVariablesChanged)
        connect(self.__input_variables_table.valuesChanged, self.onValuesChanged)

        self.__layout = QtGui.QHBoxLayout(self)

        self.__layout.addLayout(self.__tree_layout)
        self.__layout.addLayout(self.__buttons_addrem_layout)
        self.__layout.addWidget(self.__input_variables_table)

    # noinspection PyPep8Naming
    @Slot()
    def onTreeSelectionChanged(self):
        items = self.__input_variables_tree.selectedItems()
        # check whether item has item column (otherwise it's only header not a variable)
        self.__button_add.setEnabled(
            bool(items) and
            bool(items[0].text(InputVariablesTree.INDEX_COLUMN)) and
            self.__input_variables_table.rowCount() < self.MAX_VARIABLES
        )

    # noinspection PyPep8Naming
    @Slot()
    def onTableSelectionChanged(self):
        items = self.__input_variables_table.selectedItems()
        self.__button_remove.setEnabled(bool(items))

    # noinspection PyPep8Naming
    @Slot()
    def onAddVariableButtonClicked(self):
        items = self.__input_variables_tree.selectedItems()
        if items and items[0].text(InputVariablesTree.INDEX_COLUMN):
            name, index, variable = self.__input_variables_tree.check_variable(items[0])
            self.__input_variables_table.add_variable(name, index, variable)

    # noinspection PyPep8Naming
    @Slot()
    def onRemoveVariableButtonClicked(self):
        row = self.__input_variables_table.currentRow()
        index = self.__input_variables_table.item(row, InputVariablesTable.INDEX_COLUMN)
        self.__input_variables_tree.uncheck_variable(index.text())
        self.__input_variables_table.remove_variable(row)

    # noinspection PyPep8Naming
    @Slot()
    def onExpandAllClicked(self):
        self.__input_variables_tree.set_expand_collapse_all(True)

    # noinspection PyPep8Naming
    @Slot()
    def onCollapseAllClicked(self):
        self.__input_variables_tree.set_expand_collapse_all(False)

    # noinspection PyPep8Naming
    @Slot(list)
    def onVariablesChanged(self, data):
        self.variablesChanged.emit(data)

    # noinspection PyPep8Naming
    @Slot(dict)
    def onValuesChanged(self, data):
        self.valuesChanged.emit(data)

    def setObject(self, options):
        self.__options = options
        self.__input_variables_tree.setObject(options)
        selected_items = []
        for variable in self.__input_variables_table.variables:
            indx = self.__input_variables_tree.indx_by_variable(variable)
            if indx is not None:
                item = self.__input_variables_tree.item_by_indx(indx)
                selected_items.append((item, self.__input_variables_table.values[variable]))
        self.__input_variables_table.clearContents()
        for item, values in selected_items:
            name, index, variable = self.__input_variables_tree.check_variable(item)
            row = self.__input_variables_table.add_variable(name, index, variable)
            inv_map = {v: k for k, v in self.__input_variables_table.VALUES_DICT_MAP.items()}
            for key, value in values.iteritems():
                col = inv_map[key]
                self.__input_variables_table.setItem(row, col, QtGui.QTableWidgetItem(str(value)))


class OutputVariableTree(QtGui.QTreeWidget):

    NAME_COLUMN = 0

    HEADER = {
        NAME_COLUMN: "Stage/Metric name",
    }

    def __init__(self, parent, core):
        super(OutputVariableTree, self).__init__(parent)

        self.__core = core

        self.setColumnCount(1)
        self.setColumnWidth(InputVariablesTable.NAME_COLUMN, 200)
        self.setHeaderLabels(listify(OutputVariableTree.HEADER))

        self.setMinimumHeight(_MINIMUM_HEIGHT)
        self.setFixedWidth(400)

        self.__root = self.invisibleRootItem()
        """:type: QtGui.QTreeWidgetItem"""

        self.__stages = dict()

        self.__current_stage = None

        self.__add_stages()

    def __add_stages(self):
        for stage in self.__core:
            self.__stages[stage.name] = stage
            node = QtGui.QTreeWidgetItem([stage.name])
            self.__root.addChild(node)

    def __item_by_name(self, stage_name):
        for k in xrange(self.__root.childCount()):
            node = self.__root.child(k)
            if node.text(OutputVariableTree.NAME_COLUMN) == stage_name:
                return node
        return None

    @property
    def stage(self):
        return self.__current_stage

    @stage.setter
    def stage(self, stage_name):
        if stage_name is not None:
            node = self.__item_by_name(stage_name)
            node.setIcon(OutputVariableTree.NAME_COLUMN, Resources("icons/Ok"))
            self.__current_stage = self.__stages[stage_name]
        elif self.__current_stage is not None:
            node = self.__item_by_name(self.__current_stage.name)
            node.setIcon(OutputVariableTree.NAME_COLUMN, QtGui.QIcon())
            self.__current_stage = None


def make_range(**kwargs):
    return arange(kwargs["START"], kwargs["STOP"] + kwargs["INTERVAL"], kwargs["INTERVAL"])


class SimulationSetsPayload(QtCore.QObject):

    calculationDone = Signal()
    taskStarted = Signal(int)
    taskDone = Signal()

    def __init__(self):
        super(SimulationSetsPayload, self).__init__()
        self.name = None

        self.stage = None
        """:type: core.AbstractStage"""

        self.variables = []
        """:type: list of QObjectNumeric"""
        self.values = dict()

        self.mutex = QtCore.QMutex()
        self.variable_changed = QtCore.QWaitCondition()

        self.calculation_results = None

        self.__aborted = False
        self.__done = False

    @property
    def aborted(self):
        return self.__aborted

    @property
    def done(self):
        return self.__done

    @property
    def is_config_ok(self):
        is_variables = bool(self.variables)
        is_stage = self.stage is not None
        is_values = True

        if len(self.variables) == len(self.values):
            for values in self.values.values():
                # logging.info("Values: %s" % values)
                if set(values.keys()) != {"START", "STOP", "INTERVAL"}:
                    is_values = False
                    break
        else:
            is_values = False

        # logging.info("%s %s %s" % (is_variables, is_stage, is_values))
        return is_variables and is_values and is_stage

    @Slot()
    def start(self):
        # logging.info(
        #     "Starting simulation set in %s with %s to stage: %s" %
        #     (thread_name(), self.variables, self.stage))
        self.name = None
        self.__aborted = False
        self.__done = False

    def __move_to_main_thread(self):
        # noinspection PyArgumentList
        main_thread = QtGui.QApplication.instance().thread()
        self.moveToThread(main_thread)

    def __restore(self, backup):
        for variable in self.variables:
            variable.value = backup[variable]

    @Slot(str)
    def task(self, task_name):

        self.name = task_name

        # logging.info("Preparing calculation in '%s'" % thread_name())
        backup_variables = {}

        arrays = []
        for variable in self.variables:
            # self.mutex.lock()
            # variable.value = None
            backup_variables[variable] = variable.value
            arrays.append(make_range(**self.values[variable]))
            # self.variable_changed.wait(self.mutex)
            # self.mutex.unlock()
        calculation_points = cartesian(*arrays)

        self.taskStarted.emit(len(calculation_points))

        self.calculation_results = list()

        # logging.info("Run calculation of the simulation set in '%s'" % thread_name())
        for calculation_point in calculation_points:

            # logging.debug("Mutex lock")
            self.mutex.lock()

            for variable, value in zip(self.variables, calculation_point):
                # logging.debug("Change variable from thread %s to %s" % (thread_name(), value))
                variable.value = value

            # Workaround for thread not to hangs up, wait no more than one second
            for k in range(100):
                # while self.stage.has_result:
                # logging.info("Waiting for all variables changed and stage invalidated in '%s'" % thread_name())
                # if self.variable_changed.wait(self.mutex, 10):
                #     logging.info("Variables changed done")
                if self.variable_changed.wait(self.mutex, 10) and not self.stage.has_result:
                    break
            else:
                logging.warning("Stop waiting of all variables changed and stage invalidated in '%s'" % thread_name())

            if self.__aborted:
                logging.info("Task abort reported by '%s'" % thread_name())
                self.mutex.unlock()
                self.__restore(backup_variables)
                self.__move_to_main_thread()
                break

            # logging.info("Run stage calculation '%s'" % thread_name())
            try:
                self.calculation_results.append(self.stage.calculate())
            except Exception:
                self.calculation_results.append(None)
                logging.error("Error during calculation")
            # else:
            #     logging.info("Stage calculation done '%s'" % thread_name())
            # self.metrics[] = {metric: SimulationSetsPayload.calc(metric, result) for metric in self.stage.metrics}
            # logging.info("'%s': Result at %s = %s" % (thread_name(), calculation_point, metrics))

            self.calculationDone.emit()

            # logging.debug("Mutex unlock")
            self.mutex.unlock()
        else:
            self.__done = True
            self.taskDone.emit()
            self.__restore(backup_variables)
            self.__move_to_main_thread()

    def abort(self):
        if not self.__done and not self.__aborted:
            # logging.info("Abort calculations signal obtained '%s'" % thread_name())
            self.__aborted = True
            # logging.info("WakeAll threads for aborting calculation")
            self.variable_changed.wakeAll()


class QWorker(QtCore.QThread):

    def __init__(self, payload, *args, **kwargs):
        super(QWorker, self).__init__(*args, **kwargs)
        self.__payload = payload
        self.__payload.moveToThread(self)
        connect(self.started, self.__payload.start)
        connect(self.__payload.taskDone, self.quit)

    @Slot()
    def quit(self):
        self.__payload.abort()
        super(QWorker, self).quit()


class SimulationSetsControl(QtGui.QWidget):

    SET_NAME_PATTERN = "Set #%s"
    RESULT_VALUE_PATTERN = "%s"

    launched = Signal(str)
    finished = Signal(SimulationSetsPayload)

    def __init__(self, parent, core):
        super(SimulationSetsControl, self).__init__(parent)

        self.__core = core

        self.__layout = QtGui.QVBoxLayout(self)

        self.__label_info = QtGui.QLabel(
            "Pressing launch button simulation set will be performed \n"
            "for given input variable till final selected stage not reached.", self)

        self.__label_final_value = QtGui.QLabel("Simulation set result value:")

        self.__edit_final_value = QtGui.QLineEdit(self)
        self.__edit_final_value.setReadOnly(True)
        self.__edit_final_value.setFixedWidth(300)

        self.__layout_control = QtGui.QHBoxLayout()
        self.__button_launch = QtGui.QPushButton("Launch Simulations", self)
        self.__button_launch.setFixedWidth(165)
        self.__button_launch.setEnabled(False)
        self.__edit_set_name = QtGui.QLineEdit(self.SET_NAME_PATTERN % 1, self)
        self.__edit_set_name.setFixedWidth(125)
        self.__layout_control.addWidget(self.__edit_set_name)
        self.__layout_control.addWidget(self.__button_launch)
        self.__layout_control.setAlignment(QtCore.Qt.AlignLeft)

        connect(self.__button_launch.clicked, self.__onLaunchButtonClicked)

        self.__label_progress_info = QtGui.QLabel("Simulation set progress:")
        self.__progress_bar = QtGui.QProgressBar()

        self.__layout.addWidget(self.__label_info)
        self.__layout.addSpacing(20)
        self.__layout.addWidget(self.__label_final_value)
        self.__layout.addWidget(self.__edit_final_value)
        self.__layout.addLayout(self.__layout_control)
        self.__layout.addSpacing(20)
        self.__layout.addWidget(self.__label_progress_info)
        self.__layout.addWidget(self.__progress_bar)

        self.__layout.setAlignment(QtCore.Qt.AlignTop)

        self.wait_box = msgBox(msgBox.NoIcon, "Simulations", "Please, wait...", msgBox.Abort, self)

        self.__payload = SimulationSetsPayload()
        connect(self.launched, self.__payload.task)
        connect(self.__payload.taskStarted, self.__onTaskStarted)
        connect(self.__payload.taskDone, self.__onTaskDone)
        connect(self.__payload.calculationDone, self.__onCalculationDone)

    # noinspection PyPep8Naming
    @Slot()
    def __onLaunchButtonClicked(self):
        connect(self.__payload.stage.invalidated, self.__onStageInvalidated)

        worker = QWorker(self.__payload, objectName="WorkerThread")

        worker.start()

        self.launched.emit(self.__edit_set_name.text())

        self.wait_box.exec_()

        if not self.__payload.done:
            worker.quit()

        worker.wait()

    # noinspection PyPep8Naming
    @Slot(int)
    def __onTaskStarted(self, count):
        # logging.info("Initialize progress bar in '%s'" % thread_name())
        self.__progress_bar.setFormat("%%p%% (%%v/%s)" % count)
        self.__progress_bar.setRange(0, count)
        self.__progress_bar.setValue(0)

    # noinspection PyPep8Naming
    @Slot(bool)
    def __onTaskDone(self):
        # logging.info("Simulation set done '%s'" % thread_name())
        self.wait_box.close()
        self.finished.emit(self.__payload)

    # noinspection PyPep8Naming
    @Slot()
    def __onCalculationDone(self):
        number = self.__progress_bar.value() + 1
        # logging.info("Calculation #%s done reported by '%s'" % (number, thread_name()))
        self.__progress_bar.setValue(number)

    # noinspection PyPep8Naming
    @Slot()
    def __onStageInvalidated(self):
        # logging.info("Wake all waiting variable in '%s'" % thread_name())
        self.__payload.variable_changed.wakeAll()

    @property
    def stage(self):
        return self.__stage

    @stage.setter
    def stage(self, stage):
        if stage is not None:
            text = self.RESULT_VALUE_PATTERN % stage.name
            self.__edit_final_value.setText(text)
        else:
            self.__edit_final_value.setText(str())
        self.__payload.stage = stage
        self.__button_launch.setEnabled(self.__payload.is_config_ok)

    def set_input_variables(self, data):
        self.__payload.variables = data
        self.__button_launch.setEnabled(self.__payload.is_config_ok)

    def set_input_values(self, data):
        self.__payload.values = data
        self.__button_launch.setEnabled(self.__payload.is_config_ok)


class OutputVariableBox(AbstractGroupBox):

    finished = Signal(SimulationSetsPayload)

    def __init__(self, parent, core):
        super(OutputVariableBox, self).__init__("Output variable", parent)

        self.__output_variable_tree = OutputVariableTree(self, core)
        connect(self.__output_variable_tree.itemSelectionChanged, self.onTreeItemSelectionChanged)

        self.__control_widget = SimulationSetsControl(self, core)

        self.__layout_accres = QtGui.QHBoxLayout()
        self.__button_accept = QtGui.QPushButton("Accept", self)
        connect(self.__button_accept.clicked, self.onAcceptButtonClicked)
        self.__button_accept.setEnabled(False)
        self.__button_reset = QtGui.QPushButton("Reset", self)
        connect(self.__button_reset.clicked, self.onResetButtonClicked)
        self.__button_reset.setEnabled(False)
        self.__layout_accres.addWidget(self.__button_accept)
        self.__layout_accres.addWidget(self.__button_reset)

        self.__layout_tree = QtGui.QVBoxLayout()
        self.__layout_tree.addWidget(self.__output_variable_tree)
        self.__layout_tree.addLayout(self.__layout_accres)

        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.addLayout(self.__layout_tree)
        self.__layout.addWidget(self.__control_widget)

        connect(self.__control_widget.finished, self.onFinished)

    # noinspection PyPep8Naming
    @Slot(SimulationSetsPayload)
    def onFinished(self, results):
        self.finished.emit(results)

    # noinspection PyPep8Naming
    @Slot()
    def onTreeItemSelectionChanged(self):
        items = self.__output_variable_tree.selectedItems()
        self.__button_accept.setEnabled(self.__output_variable_tree.stage is None and bool(items))
        self.__button_reset.setEnabled(self.__output_variable_tree.stage is not None)

    # noinspection PyPep8Naming
    @Slot()
    def onAcceptButtonClicked(self):
        items = self.__output_variable_tree.selectedItems()
        self.__output_variable_tree.stage = items[0].text(OutputVariableTree.NAME_COLUMN)
        self.__control_widget.stage = self.__output_variable_tree.stage
        self.__output_variable_tree.clearSelection()

    # noinspection PyPep8Naming
    @Slot()
    def onResetButtonClicked(self):
        self.__output_variable_tree.stage = None
        self.__control_widget.stage = None
        self.__output_variable_tree.clearSelection()

    @Slot(list)
    def set_input_variables(self, data):
        self.__control_widget.set_input_variables(data)

    @Slot(dict)
    def set_input_values(self, data):
        self.__control_widget.set_input_values(data)


class ConfigurationTab(QStackWidgetTab):

    finished = Signal(SimulationSetsPayload)

    def __init__(self, parent, core):
        """
        :param QtGui.QWidget parent: Parent widget
        """
        super(ConfigurationTab, self).__init__(parent)

        self.__core = core

        self.__input_variables_box = InputVariablesBox(self, self.__core.options)
        self.__output_variables_box = OutputVariableBox(self, self.__core)

        connect(self.__input_variables_box.variablesChanged, self.__output_variables_box.set_input_variables)
        connect(self.__input_variables_box.valuesChanged, self.__output_variables_box.set_input_values)

        self.__layout = QtGui.QVBoxLayout(self)
        self.__layout.addWidget(self.__input_variables_box)
        self.__layout.addWidget(self.__output_variables_box)
        # self.__layout.addStretch()

        connect(self.__output_variables_box.finished, self.onFinished)

    # noinspection PyPep8Naming
    @Slot(SimulationSetsPayload)
    def onFinished(self, results):
        self.finished.emit(results)

    def onSetActive(self):
        self.__input_variables_box.setObject(self.__core.options)


class SimulationSetsGraph(QGraphPlot):

    def __init__(self, parent, options):
        super(SimulationSetsGraph, self).__init__(parent)
        self.__options = options
        self.axes = self.add_subplot()

    def _plot_1d(self, results, metric):
        """:type results: SimulationSetsPayload"""
        variable = results.variables[0]
        x = make_range(**results.values[variable])
        values = [metric(calculation_result, **results.stage.metrics_kwargs)
                  for calculation_result in results.calculation_results]
        self.axes.plot(x, values, "o-", linewidth=2.0, color=COMMON_LINES_COLOR)
        self.axes.set_xlabel(variable.object.name)
        self.axes.set_ylabel(metric.caption)

    def _plot_2d(self, results, metric, sequence):
        variable_x = results.variables[sequence[0]]
        variable_p = results.variables[sequence[1]]

        x = make_range(**results.values[variable_x])
        y = make_range(**results.values[variable_p])
        rows, cols = len(y), len(x)

        # 1  2  3  4
        # 5  6  7  8
        # 9 10 11 12

        # 0 4 8
        # 1 5 9

        for k, p in enumerate(y):
            if sequence[0] == 0:
                indexes = range(k, cols*rows + k, rows)
            else:
                indexes = range(k*cols, (k+1)*cols)

            current_results = [r for s, r in enumerate(results.calculation_results) if s in indexes]
            # values = [self.calc(metric, calculation_result) for calculation_result in current_results]
            values = [metric(calculation_result, **results.stage.metrics_kwargs)
                      for calculation_result in current_results]
            self.axes.plot(x, values, marker="o", linewidth=2.0, label=str(p))
        self.axes.set_xlabel(variable_x.object.name)
        self.axes.set_ylabel(metric.caption)
        self.axes.legend()

    # noinspection PyPep8Naming
    def setObject(self, results, metric, sequence=None):
        self.axes.clear()
        if len(results.variables) == 1:
            self._plot_1d(results, metric)
        elif len(results.variables) == 2:
            self._plot_2d(results, metric, sequence)
        self.axes.grid()
        self.redraw()


class SimulationResultsContainer(object):

    def __init__(self, payload):
        """:type payload: SimulationSetsPayload"""
        self.stage = payload.stage
        self.calculation_results = payload.calculation_results
        self.values = payload.values
        self.variables = payload.variables


class SimulationResultsTab(QStackWidgetTab):

    def __init__(self, parent, options):
        super(SimulationResultsTab, self).__init__(parent)

        self.__results = None
        """:type: SimulationSetsPayload"""

        self.__control_layout = QtGui.QHBoxLayout()

        self.__metric_label = QtGui.QLabel("Metric: ", self)
        self.__metric_combobox = QtGui.QComboBox(self)
        self.__metric_combobox.setMaximumWidth(300)
        connect(self.__metric_combobox.currentIndexChanged, self.__onItemChanged)
        self.__button_exchange = QtGui.QPushButton("Exchange", self)
        self.__button_exchange.setEnabled(False)
        connect(self.__button_exchange.clicked, self.__onButtonExchangeClicked)
        self.__button_export = QtGui.QPushButton("Clipboard", self)
        connect(self.__button_export.clicked, self.__onButtonExportClicked)

        self.__sequence = [0, 1]

        self.__control_layout.addWidget(self.__metric_label)
        self.__control_layout.addWidget(self.__metric_combobox)
        self.__control_layout.addSpacing(10)
        self.__control_layout.addWidget(self.__button_exchange)
        self.__control_layout.addWidget(self.__button_export)
        self.__control_layout.setAlignment(QtCore.Qt.AlignLeft)

        self.__graph = SimulationSetsGraph(self, options)
        self.__toolbar = NavigationToolbar(self.__graph, self)

        self.__control_layout.addWidget(self.__toolbar)

        self.__layout = QtGui.QVBoxLayout(self)
        self.__layout.addLayout(self.__control_layout)
        self.__layout.addWidget(self.__graph)

    # noinspection PyPep8Naming
    def setObject(self, results):
        """:type results: SimulationSetsPayload"""

        self.__button_exchange.setEnabled(len(results.variables) > 1)

        self.__results = SimulationResultsContainer(results)

        self.__metric_combobox.clear()
        for metric in results.stage.metrics:
            self.__metric_combobox.addItem(metric.caption)

        if self.__results.stage.metrics:
            self.__graph.setObject(self.__results, self.__results.stage.metrics[0], self.__sequence)

    # noinspection PyPep8Naming
    @Slot()
    def __onButtonExchangeClicked(self):
        self.__sequence[0], self.__sequence[1] = self.__sequence[1], self.__sequence[0]
        index = self.__metric_combobox.currentIndex()
        self.__graph.setObject(self.__results, self.__results.stage.metrics[index], self.__sequence)

    # noinspection PyPep8Naming
    @Slot()
    def __onButtonExportClicked(self):
        lines = self.__graph.axes.get_lines()
        if not lines:
            return
        line0 = lines[0]
        data0 = line0.get_xydata()
        rows = len(lines)
        cols = data0.shape[0]
        result = ndarray(shape=[rows+1, cols+1], dtype=float)
        result[0, 1:] = data0[:, 0]
        for k, line in enumerate(lines):
            try:
                result[k+1, 0] = float(line.get_label())
            except ValueError:
                result[k+1, 0] = NaN
            result[k+1, 1:] = line.get_xydata()[:, 1]
        s = StringIO()
        savetxt(s, result.transpose(), fmt='%.5f', delimiter="\t")
        # noinspection PyArgumentList
        clipboard = QtGui.QApplication.clipboard()
        clipboard.setText(s.getvalue())

    # noinspection PyPep8Naming
    @Slot()
    def __onItemChanged(self, index):
        self.__graph.setObject(self.__results, self.__results.stage.metrics[index], self.__sequence)


class SimulationSets(QStackWidgetTab):

    def __init__(self, parent, core):
        """
        :param QtGui.QWidget parent: Widget parent
        """
        super(SimulationSets, self).__init__(parent)
        self.__tab_widget = QtGui.QTabWidget(self)

        self.__core = core

        self.__configuration_tab = ConfigurationTab(self.__tab_widget, core)
        self.__result_tabs = dict()

        self.__tab_widget.addTab(self.__configuration_tab, "Configuration")

        self.__layout = QtGui.QVBoxLayout()
        self.__layout.addWidget(self.__tab_widget)

        connect(self.__configuration_tab.finished, self.__onFinished)

    # noinspection PyPep8Naming
    @Slot(SimulationSetsPayload)
    def __onFinished(self, results):
        if results.name in self.__result_tabs:
            self.__result_tabs[results.name].setObject(results)
        else:
            self.__result_tabs[results.name] = SimulationResultsTab(self, self.__core.options)
            self.__tab_widget.addTab(self.__result_tabs[results.name], results.name)
            self.__result_tabs[results.name].setObject(results)

    def onSetActive(self):
        self.__configuration_tab.onSetActive()
