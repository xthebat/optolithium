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
import math
import traceback
import logging as module_logging

from qt import QtGui, QtCore, connect, disconnect, Slot, GlobalSignals, backend_name

from metrics import MetricNotImplementedError

from resources import Resources
# from database.base import Float, Integer

from config import APPLICATION_NAME, KILOBYTE, MEGABYTE, GIGABYTE

from numpy import isnan
from matplotlib import rcParams
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.cm import register_cmap

rcParams["backend.qt4"] = backend_name

# CAUTION: That's important not to import matplotlib because it sets up its own gui, mainloop and canvas.
# Backend name PySide or PyQt4 is setup in matplotrc file
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT

import config
import helpers
import options

from options.structures import get_field


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


NavigationToolbar = NavigationToolbar2QT
msgBox = QtGui.QMessageBox


ProlithColormap = LinearSegmentedColormap.from_list("prolith", ["#0000FF", "#00FFFF", "#00FF00", "#FFFF00", "#FF6209"])
register_cmap(cmap=ProlithColormap)


# noinspection PyPep8Naming
def QuestionBox(parent, message, buttons=msgBox.Yes | msgBox.No, default=msgBox.Yes):
    """
    :type parent: QtGui.QWidget
    :type message: str
    :type buttons: int
    :type default: int
    :rtype: int
    """
    # noinspection PyCallByClass,PyTypeChecker
    return msgBox.question(parent, APPLICATION_NAME, message, buttons, default)


# noinspection PyPep8Naming
def WarningBox(parent, message):
    """
    :type parent: QtGui.QWidget
    :type message: str
    :rtype: int
    """
    # noinspection PyCallByClass,PyTypeChecker
    return msgBox.warning(parent, APPLICATION_NAME, message, msgBox.Ok)


# noinspection PyPep8Naming
def ErrorBox(parent, message):
    """
    :type parent: QtGui.QWidget
    :type message: str
    :rtype: int
    """
    # noinspection PyCallByClass,PyTypeChecker
    return msgBox.critical(parent, APPLICATION_NAME, message, msgBox.Ok)


# noinspection PyPep8Naming
def InformationBox(parent, message, buttons=msgBox.Abort, default=msgBox.Abort):
    """
    :type parent: QtGui.QWidget
    :type message: str
    :type buttons: int
    :type default: int
    :rtype: int
    """
    # noinspection PyCallByClass,PyTypeChecker
    return msgBox.information(parent, APPLICATION_NAME, message, buttons, default)


class ExtendedErrorBox(msgBox):
    def __init__(self, title, message, info):
        # noinspection PyCallByClass
        msgBox.__init__(self)
        self.setWindowTitle("%s error" % APPLICATION_NAME)
        self.setText(title)
        self.setInformativeText(message)
        self.setStandardButtons(msgBox.Close | msgBox.Ok)
        self.setDefaultButton(msgBox.Ok)
        self.setIcon(msgBox.Warning)
        self.setWindowIcon(Resources("icons/Logo"))
        # exc_type, exc_value, exc_traceback = sys.exc_info()
        # exc_string = traceback.format_tb(exc_traceback)
        self.setDetailedText(info)


class QTracebackMessageBox(msgBox):
    def __init__(self):
        # noinspection PyCallByClass
        msgBox.__init__(self)
        self.setWindowTitle("%s runtime error" % APPLICATION_NAME)
        self.setText("An error has occurred during perform action!")
        self.setInformativeText(traceback.format_exc(limit=1))
        self.setStandardButtons(msgBox.Close | msgBox.Ok)
        self.setDefaultButton(msgBox.Ok)
        self.setIcon(msgBox.Warning)
        self.setWindowIcon(Resources("icons/Logo"))
        exc_type, exc_value, exc_traceback = sys.exc_info()
        exc_string = traceback.format_tb(exc_traceback)
        self.setDetailedText("\n".join(exc_string))


def show_traceback(function):

    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except:
            msg_box = QTracebackMessageBox()
            reply = msg_box.exec_()
            if reply == msgBox.Close:
                sys.exit(1)
            raise

    return wrapped


def rgbf(color):
    """
    Converts QColor to RGB float.

    :rtype: float, float, float
    """
    return color.red()/255.0, color.green()/255.0, color.blue()/255.0


class QSliderNumeric(QtGui.QSlider):

    def __init__(self, parent, p_object=None, abstract_field=options.Numeric, orientation=QtCore.Qt.Vertical):
        """
        :type parent: QtGui.QWidget
        :type p_object: options.Variable or None
        :type abstract_field: options.Numeric
        """
        QtGui.QSlider.__init__(self, orientation, parent)

        self.__p_object = None
        self.__field = None

        if p_object is not None:
            self.setObject(p_object, abstract_field)

        connect(self.valueChanged, self.__onValueChanged)

    # noinspection PyPep8Naming
    def setObject(self, p_object, abstract_field=options.Numeric):
        self.__p_object = p_object
        self.__field = get_field(p_object, abstract_field)
        """:type: options.Numeric"""

        connect(self.__p_object.signals[self.__field], GlobalSignals.onChanged)

        self.setValue(getattr(p_object, self.__field.key))
        self.setRange(self.__field.min, self.__field.max)

        connect(self.__p_object.signals[self.__field], self.__onValueChanged)

    # noinspection PyPep8Naming
    @Slot()
    @Slot(int)
    def __onValueChanged(self, *args):
        # args is not empty only when event come from Gui
        # if event come from p_object then args is empty and it's only flag
        if self.__p_object is not None:
            if args:
                setattr(self.__p_object, self.__field.key, args[0])
            else:
                self.setValue(getattr(self.__p_object, self.__field.key))


class QLineEditNumeric(QtGui.QLineEdit):

    def __init__(self, parent, p_object=None, abstract_field=options.Numeric):
        """
        :type parent: QtGui.QWidget
        :type p_object: options.Variable or None
        :type abstract_field: options.Numeric or options.AttributedProperty or database.orm.Column
        """
        super(QLineEditNumeric, self).__init__(parent)

        self.__p_object = None
        self.__field = None
        self.__validator = None

        if p_object is not None:
            self.setObject(p_object, abstract_field)

        self.setFixedWidth(config.DEFAULT_EDIT_WIDTH)

        connect(self.editingFinished, self.__onEditingFinished)

    # noinspection PyPep8Naming
    def setObject(self, p_object, abstract_field=options.Numeric):
        """
        :type p_object: options.Variable or options.MaterialLayer
        :type abstract_field: options.Numeric or options.AttributedProperty or database.orm.Column
        """
        if self.__p_object is not None:
            disconnect(self.__p_object.signals[self.__field], self.__changeText)

        self.__p_object = p_object
        self.__field = get_field(p_object, abstract_field)
        """:type: options.Numeric"""

        connect(self.__p_object.signals[self.__field], GlobalSignals.onChanged)

        value = getattr(self.__p_object, self.__field.key)

        if isinstance(value, float):
            self.__validator = QtGui.QDoubleValidator(self)
            self.__validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
            precision = (self.__field.precision
                         if self.__field.precision is not None
                         else config.DEFAULT_DECIMAL_COUNT)
            self.__validator.setDecimals(precision)
        elif isinstance(value, int):
            self.__validator = QtGui.QIntValidator(self)

        self.setText(str(value))

        self.setValidator(self.__validator)

        connect(self.__p_object.signals[self.__field], self.__changeText)

    # noinspection PyPep8Naming
    def unsetObject(self):
        if self.__p_object is not None:
            disconnect(self.__p_object.signals[self.__field], self.__changeText)
            disconnect(self.__p_object.signals[self.__field], GlobalSignals.onChanged)
            self.__p_object = None
            self.__field = None
            self.setText(str())

    # noinspection PyPep8Naming
    @Slot()
    def __changeText(self):
        value = getattr(self.__p_object, self.__field.key)
        self.setText(str(value))

    # noinspection PyPep8Naming
    @Slot()
    def __onEditingFinished(self):
        # logging.info("Value after edit finished: %s" % self.text())
        if self.__p_object is not None:
            try:
                cast_result = self.__field.type.python_type(self.text())
            except ValueError:
                logging.warning("Can't convert value %s to %s" %
                                (self.text(), self.__field.type.python_type.__name__))
            else:
                setattr(self.__p_object, self.__field.key, cast_result)


class QObjectNumeric(QtCore.QObject):

    def __init__(self, parent, p_object=None, abstract_field=options.Numeric, global_signals=False):
        """
        :type parent: QtGui.QWidget
        :type p_object: options.Variable or None
        :type abstract_field: options.Numeric or options.AttributedProperty or database.orm.Column
        :type global_signals: bool
        """
        super(QObjectNumeric, self).__init__(parent)

        self.__global_signals = global_signals

        self.__p_object = None
        self.__field = None
        self.__value = None

        if p_object is not None:
            self.setObject(p_object, abstract_field)

    @property
    def object(self):
        return self.__p_object

    @property
    def field(self):
        return self.__field

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, data):
        if self.__p_object is not None:
            try:
                cast_result = self.__field.type.python_type(data) if data is not None else None
            except ValueError:
                logging.warning("Can't convert value %s to %s" %
                                (self.text(), self.__field.type.python_type.__name__))
            else:
                # v = getattr(self.__p_object, self.__field.key)
                # logging.info(
                #     "Object: %s Field: %s Value: %s -> %s" %
                #     (self.__p_object, self.__field.key, v, cast_result))
                setattr(self.__p_object, self.__field.key, cast_result)
                self.__value = data

    # noinspection PyPep8Naming
    def setObject(self, p_object, abstract_field=options.Numeric):
        """
        :type p_object: options.structures.Variable or options.structures.MaterialLayer
        :type abstract_field: options.Numeric or options.AttributedProperty or database.orm.Column
        """
        if self.__p_object is not None:
            disconnect(self.__p_object.signals[self.__field], self.__field_changed)

        self.__p_object = p_object
        self.__field = get_field(p_object, abstract_field)
        """:type: options.structures.Numeric"""

        if self.__global_signals:
            connect(self.__p_object.signals[self.__field], GlobalSignals.onChanged)

        self.value = getattr(self.__p_object, self.__field.key)

        connect(self.__p_object.signals[self.__field], self.__field_changed)

    # noinspection PyPep8Naming
    def unsetObject(self):
        if self.__p_object is not None:
            disconnect(self.__p_object.signals[self.__field], self.__field_changed)
            if self.__global_signals:
                disconnect(self.__p_object.signals[self.__field], GlobalSignals.onChanged)
            self.__p_object = None
            self.__field = None
            self.__value = None

    # noinspection PyPep8Naming
    @Slot()
    def __field_changed(self):
        self.__value = getattr(self.__p_object, self.__field.key)


class QComboBoxEnum(QtGui.QComboBox):

    def __init__(self, parent, p_object=None, abstract_field=options.Enum):
        """
        :type parent: QtGui.QWidget
        :type p_object: options.Variable or None
        :type abstract_field: options.Enum
        """
        QtGui.QComboBox.__init__(self, parent)

        self.__p_object = None
        self.__field = None

        if p_object is not None:
            self.setObject(p_object, abstract_field)

        connect(self.currentIndexChanged, self.__onIndexChanged)

    # noinspection PyPep8Naming
    def setObject(self, p_object, abstract_field=options.Enum):
        """
        :type p_object: options.Variable or None
        :type abstract_field: options.Enum
        """
        self.__p_object = p_object
        self.__field = get_field(p_object, abstract_field)
        """:type: options.Enum"""

        connect(self.__p_object.signals[self.__field], GlobalSignals.onChanged)

        self.clear()
        self.addItems(self.__field.variants)
        self.setCurrentIndex(self.findText(getattr(self.__p_object, self.__field.key)))

    # noinspection PyPep8Naming
    @Slot(int)
    def __onIndexChanged(self, index):
        if self.__p_object is not None:
            value = str(self.itemText(index))
            setattr(self.__p_object, self.__field.key, value)


class QLabelMulti(QtGui.QLabel):

    class _MemoryFormat(object):
        pass

    memory_format = _MemoryFormat()

    def _enum_items(self):
        for item in self._items:
            obj, abstract_field = item
            field = get_field(obj, abstract_field)
            yield obj, field

    def __init__(self, parent, items=None, frmt=None):
        """
        :type parent: QtGui.QWidget
        :type items: list of (options.Variable,
                              options.Abstract or options.AttributedProperty or database.orm.Column) or None
        :type frmt: str or None
        """
        QtGui.QLabel.__init__(self, parent)

        self._items = None
        self._format = frmt

        if items is not None:
            self.setObject(items)

        self.setAlignment(QtCore.Qt.AlignCenter)

    # noinspection PyPep8Naming
    def setObject(self, items, frmt=None):
        """:type items: list of (options.Variable,
                                 options.Abstract or options.AttributedProperty or database.orm.Column)"""

        if self._items is not None:
            if len(items) != len(self._items) and self._format is not None and frmt is None:
                raise ValueError("Number of objects not equal previous object number but format is not changed!")

            for obj, field in self._enum_items():
                disconnect(obj.signals[field], self.__onTextChanged)

        self._items = items
        for obj, field in self._enum_items():
            connect(obj.signals[field], self.__onTextChanged)

        if frmt is not None:
            self._format = frmt
        elif self._format is None:
            self._format = "%s "*len(self._items)

        self.__onTextChanged()

    # noinspection PyPep8Naming
    @Slot()
    def __onTextChanged(self):
        values = [getattr(obj, field.key) if getattr(obj, field.key) is not None else "- Undefined -"
                  for obj, field in self._enum_items()]

        if self._format is QLabelMulti.memory_format:
            if len(values) != 1:
                raise ValueError("Can't use memory format to more than one item")
            value = float(values[0])
            if value > 10.0*GIGABYTE:
                self.setText("%d GiB" % int(math.ceil(value/10.0/GIGABYTE)))
            elif value > MEGABYTE:
                self.setText("%d MiB" % int(math.ceil(value/MEGABYTE)))
            elif value > KILOBYTE:
                self.setText("%d KiB" % int(math.ceil(value/KILOBYTE)))
            else:
                self.setText("%d Bytes" % int(math.ceil(value)))
        else:
            self.setText(self._format % tuple(values))


class QLabel(QLabelMulti):

    def __init__(self, parent, p_object=None, abstract_field=options.Abstract, frmt=None):
        """
        :type parent: QtGui.QWidget
        :type p_object: options.Variable or None
        :type abstract_field: options.Abstract or options.AttributedProperty or database.orm.Column
        :type frmt: str or None
        """
        # QLabelMulti constructor can't be called because that result in incontinence.
        # QLabelMulti.__init__ call setObject thinking that constructor belongs to QLabelMulti
        # but in really setObject override by QLabel class.
        QtGui.QLabel.__init__(self, parent)

        self._items = None
        self._format = frmt

        if p_object is not None:
            self.setObject(p_object, abstract_field)

        self.setAlignment(QtCore.Qt.AlignRight)

    def setObject(self, p_object, abstract_field=options.Abstract):
        """
        :type p_object: options.Variable or None
        :type abstract_field: options.Abstract or options.AttributedProperty or database.orm.Column
        """
        QLabelMulti.setObject(self, [(p_object, abstract_field)])


class QFramedLabel(QLabel):

    def __init__(self, parent, p_object=None, abstract_field=options.Abstract, frmt=None):
        """
        :type parent: QtGui.QWidget
        :type p_object: options.Variable or None
        :type abstract_field: options.Abstract or options.AttributedProperty or database.orm.Column
        :type frmt: str or None
        """
        QLabel.__init__(self, parent, p_object, abstract_field, frmt)
        self.setAlignment(QtCore.Qt.AlignRight)
        self.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Sunken)
        self.setStyleSheet("QLabel{padding: 3px 3px 3px 3px;}")


class QStackWidgetTab(QtGui.QWidget):

    def __init__(self, parent):
        super(QStackWidgetTab, self).__init__(parent)
        self.__vlayout = None
        self.__hlayout = None

    # noinspection PyPep8Naming
    def onSetActive(self):
        pass

    def reset(self):
        pass

    # noinspection PyPep8Naming
    def setUnstretchable(self, layout):

        self.__vlayout = QtGui.QVBoxLayout()
        self.__vlayout.addLayout(layout)
        self.__vlayout.addStretch(1)

        self.__hlayout = QtGui.QHBoxLayout(self)
        self.__hlayout.addLayout(self.__vlayout)
        self.__hlayout.addStretch(1)


class QStackedWidget(QtGui.QStackedWidget):

    def setCurrentWidget(self, widget):
        if isinstance(widget, QStackWidgetTab):
            widget.onSetActive()
        QtGui.QStackedWidget.setCurrentWidget(self, widget)


class QGraphPlot(FigureCanvas):

    def __init__(self, parent, width=None, height=None, figsize=None):
        """
        :type parent: QtGui.QWidget
        :type width: int
        :type height: int
        """
        self._figure = Figure(dpi=config.Configuration.dpi, figsize=figsize)
        """:type: matplotlib.figure.Figure"""

        super(QGraphPlot, self).__init__(self._figure)
        self.setParent(parent)

        if width is not None and height is not None:
            self.setFixedSize(width, height)

        color = self.palette().color(QtGui.QPalette.Window)
        self._figure.patch.set_facecolor(rgbf(color))

    def add_subplot(self, position=111, **kwargs):
        """:rtype: matplotlib.axes.Axes"""
        return self._figure.add_subplot(position, **kwargs)
        # if aspect is None:
        #     return self._figure.add_subplot(position)
        # else:
        #     return self._figure.add_subplot(position, aspect=aspect)

    def clear(self):
        self._figure.clf()

    def redraw(self):
        if self._figure.get_axes():
            self._figure.tight_layout(pad=0.1)
            self.draw()

    def resizeEvent(self, event=None):
        FigureCanvas.resizeEvent(self, event)
        self.redraw()


class ParameterGroupBox(QtGui.QGroupBox):

    def edit(self, p_object=None):
        result = QLineEditNumeric(self, p_object)
        result.setFixedWidth(config.DEFAULT_EDIT_WIDTH)
        return result

    def framed_label(self, p_object=None):
        result = QFramedLabel(self, p_object)
        result.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        # result.setFixedWidth(config.DEFAULT_EDIT_WIDTH)
        result.setMinimumWidth(80)
        result.setFixedHeight(25)
        return result

    def __init__(self, title, parent):
        super(ParameterGroupBox, self).__init__(title, parent)
        self.__prms = dict()
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Maximum)
        # self.setMinimumWidth(250)
        # self.setFixedWidth(390)

    def _add_plugin_parameters(self, p_object, layout):
        for item in self.__prms.values():
            item["edit"].unsetObject()
            container = item["layout"].takeAt(0)
            while container:
                del container
                container = item["layout"].takeAt(0)
            item["edit"].setParent(None)
            item["label"].setParent(None)
            item["layout"].setParent(None)

        self.__prms.clear()

        for variable in p_object.variables:
            hlayout = QtGui.QHBoxLayout()
            label = QtGui.QLabel(variable.name, self)
            edit = self.edit(variable)
            self.__prms[variable.name] = {"layout": hlayout, "edit": edit, "label": label}
            hlayout.addWidget(label)
            hlayout.addStretch()
            hlayout.addWidget(edit)
            layout.addLayout(hlayout)


# noinspection PyPep8Naming
def QLoadDialogFactory(db_type, plugin_type, plot_type):

    class QLoadDialog(QtGui.QDialog):

        def __init__(self, parent, appdb):
            """
            :type parent: QtGui.QMainWindow
            :type appdb: ApplicationDatabase
            """
            QtGui.QDialog.__init__(self, parent)

            name = db_type.title

            self.setWindowTitle("Load %s" % name)
            self.setWindowIcon(parent.windowIcon())

            self.__appdb = appdb

            self.__db_type = db_type
            self.__plugin_type = plugin_type

            self.__select_group = QtGui.QGroupBox("Select Parametric (Plugin) or Database %s" % name, self)
            self.__select_group_layout = QtGui.QHBoxLayout(self.__select_group)

            self.__parametric_label = QtGui.QLabel("Parametric:")
            self.__parametric_list = QtGui.QListWidget(self.__select_group)
            self.__parametric_layout = QtGui.QVBoxLayout()
            self.__parametric_layout.addWidget(self.__parametric_label)
            self.__parametric_layout.addWidget(self.__parametric_list)
            self.__select_group_layout.addLayout(self.__parametric_layout)

            self.__database_label = QtGui.QLabel("Database:")
            self.__database_list = QtGui.QListWidget(self.__select_group)
            self.__database_layout = QtGui.QVBoxLayout()
            self.__database_layout.addWidget(self.__database_label)
            self.__database_layout.addWidget(self.__database_list)
            self.__select_group_layout.addLayout(self.__database_layout)
            self.__select_group.setFixedHeight(200)

            self.__plot = plot_type(self)
            self.__plot.setEnabled(False)

            self.__plot_hlay = QtGui.QHBoxLayout()
            self.__plot_hlay.addWidget(self.__plot)
            self.__plot_hlay.setAlignment(QtCore.Qt.AlignCenter)

            self.__buttons_layout = QtGui.QHBoxLayout()
            self.__load_button = QtGui.QPushButton("Load", self)
            self.__load_button.setFixedWidth(config.MAXIMUM_DIALOG_BUTTON_WIDTH)
            self.__cancel_button = QtGui.QPushButton("Cancel", self)
            self.__cancel_button.setFixedWidth(config.MAXIMUM_DIALOG_BUTTON_WIDTH)

            self.__buttons_layout.addStretch()
            self.__buttons_layout.addWidget(self.__load_button)
            self.__buttons_layout.addWidget(self.__cancel_button)

            for plugin in self.__appdb[self.__plugin_type]:
                self.__parametric_list.addItem(plugin.name)

            connect(self.__load_button.clicked, self.accept)
            connect(self.__cancel_button.clicked, self.reject)

            connect(self.__parametric_list.itemSelectionChanged, self._accept_state_handler)
            connect(self.__database_list.itemSelectionChanged, self._accept_state_handler)
            connect(self.__parametric_list.itemSelectionChanged, self._change_material)
            connect(self.__database_list.itemSelectionChanged, self._change_material)

            self.__layout = QtGui.QVBoxLayout(self)
            self.__layout.addWidget(self.__select_group)
            self.__layout.addLayout(self.__plot_hlay)
            self.__layout.addLayout(self.__buttons_layout)

            self._accept_state_handler()

        def update_database_list(self):
            self.__database_list.clear()
            for p_object in self.__appdb[self.__db_type]:
                self.__database_list.addItem(p_object.name)

        def showEvent(self, *args, **kwargs):
            self.update_database_list()
            super(QLoadDialog, self).showEvent(*args, **kwargs)

        # noinspection PyUnusedLocal
        def _accept_state_handler(self, *args):
            self.__plot.setEnabled(self.is_item_selected)
            self.__load_button.setEnabled(self.is_item_selected)

        def _change_material(self):
            if self.sender() is self.__parametric_list:
                self.__database_list.clearSelection()
            elif self.sender() is self.__database_list:
                self.__parametric_list.clearSelection()

            if self.object is not None:
                self.__plot.setObject(self.object)

        @property
        def object(self):
            if self.__database_list.selectedItems():
                item = self.__database_list.currentItem()
                return self.__appdb[self.__db_type].filter(self.__db_type.name == item.text()).one()

            elif self.__parametric_list.selectedItems():
                item = self.__parametric_list.currentItem()
                abstract = self.__appdb[self.__plugin_type].\
                    filter(self.__plugin_type.name == item.text()).one()
                return abstract.produce()

        @property
        def is_item_selected(self):
            return bool(self.__parametric_list.selectedItems() or self.__database_list.selectedItems())

    return QLoadDialog


def calculate_table_width(table_widget):
    """
    :type table_widget: QtGui.QTableView
    :rtype: int
    """
    layout = table_widget.layout()
    if layout is not None:
        left, top, right, bottom = table_widget.layout().getContentsMargins()
    else:
        left, top, right, bottom = 0, 0, 0, 0

    extra_left = left + table_widget.frameWidth()
    extra_right = right + table_widget.frameWidth()

    min_width = extra_left + extra_right

    if table_widget.verticalHeader().isVisible():
        min_width += table_widget.verticalHeader().width()

    for k in xrange(table_widget.horizontalHeader().count()):
        min_width += table_widget.columnWidth(k)

    min_width += table_widget.verticalScrollBar().height()/2 + table_widget.frameWidth()

    return min_width


class QMetrologyTable(QtGui.QTableWidget):

    CAPTION_INDEX = 0
    VALUE_INDEX = 1
    HEIGHT = 25
    OVERSIZE = 5

    @staticmethod
    def __create_item(text):
        item = QtGui.QTableWidgetItem(text)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
        return item

    def __init__(self, parent, metrics):
        """
        :type parent: QtGui.QWidget
        :type metrics: list of metrology.MetrologyInterface
        """
        super(QMetrologyTable, self).__init__(parent)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Metric name", "Metric value"])

        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.horizontalHeader().setClickable(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(self.HEIGHT)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.resizeColumnsToContents()

        self.setColumnWidth(self.CAPTION_INDEX, 155)
        self.setColumnWidth(self.VALUE_INDEX, 75)

        self.setFixedWidth(calculate_table_width(self) + self.OVERSIZE)
        self.setMinimumHeight(240)

        self.__p_object = None
        self.__metrics = metrics

    # noinspection PyPep8Naming
    def setObject(self, p_object, **kwargs):
        self.clearContents()
        rows = 0
        self.setRowCount(len(self.__metrics))
        for k, metric in enumerate(self.__metrics):
            try:
                value = metric(p_object, **kwargs)
            except MetricNotImplementedError:
                pass
            else:
                string = metric.format % value if not isnan(value) else "N/A"
                self.setItem(rows, self.CAPTION_INDEX, self.__create_item(metric.caption))
                self.setItem(rows, self.VALUE_INDEX, self.__create_item(string))
                rows += 1

        self.setRowCount(rows)
        self.__p_object = p_object