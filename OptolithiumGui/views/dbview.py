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

import os
import logging as module_logging

from resources import Resources
from database import orm
from database.common import ApplicationDatabase
from qt import QtGui, QtCore, connect, Signal
from views.common import QStackWidgetTab, QuestionBox, WarningBox, msgBox, show_traceback
import helpers


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


class QTreeWidgetDrag(QtGui.QTreeWidget):

    dropped = Signal(str)

    class QSizeDelegate(QtGui.QItemDelegate):
        def __init__(self):
            QtGui.QItemDelegate.__init__(self)

        def sizeHint(self, option, index):
            return QtCore.QSize(18, 18)

    def __init__(self, parent):
        QtGui.QTreeWidget.__init__(self, parent)
        self.setAcceptDrops(True)
        delegate = QTreeWidgetDrag.QSizeDelegate()
        self.setItemDelegate(delegate)

    # noinspection PyPep8Naming
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    # noinspection PyPep8Naming
    def dropEvent(self, event):
        file_list = list()
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                file_list.append(path)

        if len(file_list) == 1:
            self.dropped.emit(str(file_list[0]))

        elif len(file_list) > 1:
            label_pattern = "Loading file \'%s\' into database"
            progress = QtGui.QProgressDialog(str(), "Abort", 0, len(file_list), self)
            progress.setWindowTitle("Import Objects")
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.show()

            for k, path in enumerate(file_list):
                progress.setLabelText(label_pattern % helpers.GetFilename(path))
                self.dropped.emit(str(path))
                progress.setValue(k)
                if progress.wasCanceled():
                    break

            progress.setValue(len(file_list))
            progress.close()


class QDatabaseTreeWidget(QTreeWidgetDrag):

    NAME_COLUMN = 0
    COUNT_COLUMN = 1
    TIME_COLUMN = 2
    DESC_COLUMN = 3

    HEADER = {
        NAME_COLUMN: "Name",
        COUNT_COLUMN: "#",
        TIME_COLUMN: "Timestamp",
        DESC_COLUMN: "Description"
    }

    @staticmethod
    def listify(data):
        return [value for index, value in sorted(data.iteritems())]

    def __init__(self, parent, database):
        """
        :param parent: QtGui.QWidget
        :type database: database.ApplicationDatabase
        """
        QTreeWidgetDrag.__init__(self, parent)

        self.__root = None
        """:type: QtGui.QTreeWidgetItem"""

        self.__standard_root = None
        """:type: QtGui.QTreeWidgetItem"""

        self.__plugin_root = None
        """:type: QtGui.QTreeWidgetItem"""

        self.__nodes = dict()
        """:type: dict from str to QtGui.QTreeWidgetItem"""

        self.__database = database
        """:type: database.ApplicationDatabase"""

        logging.info("Configure database view")

        self.setColumnCount(4)
        self.setColumnWidth(QDatabaseTreeWidget.NAME_COLUMN, 300)
        self.setColumnWidth(QDatabaseTreeWidget.COUNT_COLUMN, 40)
        self.setColumnWidth(QDatabaseTreeWidget.TIME_COLUMN, 140)
        self.setHeaderLabels(self.listify(QDatabaseTreeWidget.HEADER))
        self.sortItems(QDatabaseTreeWidget.NAME_COLUMN, QtCore.Qt.AscendingOrder)
        self.setSortingEnabled(True)

        logging.info("Reload database objects")
        self.reload()

        self.__undeleteable_items = {self.__root, self.__standard_root, self.__plugin_root}

        logging.info("Configure actions")
        # Add item to database action
        connect(self.dropped, self.__onFileDropped)
        # Remove item from database action
        self.installEventFilter(self)

    def reload(self):
        self.clear()
        self.__nodes.clear()
        self.__configure_root()
        self.__load_content()

    def __configure_root(self):
        self.__root = QtGui.QTreeWidgetItem([os.path.abspath(self.__database.path)])
        self.__root.setIcon(0, Resources("icons/Folder"))
        self.addTopLevelItem(self.__root)
        self.__root.setFirstColumnSpanned(True)

        self.__standard_root = QtGui.QTreeWidgetItem(["Standard objects"])
        self.__standard_root.setIcon(0, Resources("icons/Folder"))
        self.__standard_root.setFirstColumnSpanned(True)

        self.__plugin_root = QtGui.QTreeWidgetItem(["Plugins"])
        self.__plugin_root.setIcon(0, Resources("icons/Folder"))
        self.__plugin_root.setFirstColumnSpanned(True)

        self.__root.addChildren([self.__standard_root, self.__plugin_root])

    @staticmethod
    def __align_text_bottom(item):
        """:type item: QtGui.QTreeWidgetItem"""
        for k in xrange(len(QDatabaseTreeWidget.HEADER)):
            alignment = item.textAlignment(k) | QtCore.Qt.AlignBottom
            item.setTextAlignment(k, alignment)

    def __load_table(self, table):
        table_data = self.__database[table]
        if table.title not in self.__nodes:
            node = QtGui.QTreeWidgetItem()
            node.setText(QDatabaseTreeWidget.NAME_COLUMN, table.title)
            node.setText(QDatabaseTreeWidget.COUNT_COLUMN, str(table_data.count()))
            node.setIcon(QDatabaseTreeWidget.NAME_COLUMN, Resources("icons/Folder"))
            self.__align_text_bottom(node)
            self.__nodes[table.title] = node
        for p_object in table_data:
            self.__add_item(p_object)
        return self.__nodes[table.title]

    def __load_content(self):
        for table in self.__database.standard_tables:
            node = self.__load_table(table)
            self.__standard_root.addChild(node)
        self.__standard_root.setExpanded(True)

        for table in self.__database.plugin_tables:
            node = self.__load_table(table)
            self.__plugin_root.addChild(node)
        self.__plugin_root.setExpanded(True)

        self.__root.setExpanded(True)

    def __add_item(self, p_object):
        """:type p_object: orm.Generic"""
        node = self.__nodes[p_object.title]
        data = {
            QDatabaseTreeWidget.NAME_COLUMN: p_object.name,
            QDatabaseTreeWidget.COUNT_COLUMN: str(),
            QDatabaseTreeWidget.TIME_COLUMN: p_object.created.strftime("%d.%m.%y %H:%M:%S"),
            QDatabaseTreeWidget.DESC_COLUMN: p_object.desc
        }
        result = self.listify(data)
        item = QtGui.QTreeWidgetItem(result)
        item.setIcon(QDatabaseTreeWidget.NAME_COLUMN, Resources(p_object.icon))
        item.setTextAlignment(QDatabaseTreeWidget.TIME_COLUMN, QtCore.Qt.AlignRight)
        self.__align_text_bottom(item)
        node.addChild(item)
        node.setText(QDatabaseTreeWidget.COUNT_COLUMN, str(node.childCount()))

    def __get_item(self, p_object):
        """:type p_object: orm.Generic"""
        node = self.__nodes[p_object.title]
        for k in xrange(node.childCount()):
            item = node.child(k)
            if str(item.text(QDatabaseTreeWidget.NAME_COLUMN)) == p_object.name:
                return item
        return None

    def __remove_item(self, p_object):
        """:type p_object: orm.Generic or QtGui.QTreeWidgetItem"""
        if isinstance(p_object, orm.Generic):
            node = self.__nodes[p_object.title]
            item = self.__get_item(p_object)
            node.removeChild(item)
        elif isinstance(p_object, QtGui.QTreeWidgetItem):
            node = p_object.parent()
            node.removeChild(p_object)
        else:
            raise TypeError("Only Generic or QTreeWidgetItem types are possible")
        node.setText(QDatabaseTreeWidget.COUNT_COLUMN, str(node.childCount()))

    def __replace_item(self, p_object):
        """:type p_object: orm.Generic"""
        self.__remove_item(p_object)
        self.__add_item(p_object)

    # noinspection PyPep8Naming
    @show_traceback
    def __onFileDropped(self, path):
        """:type path: str"""
        logging.debug("File \"%s\" dropped" % str(path))
        try:
            new_objects = self.__database.import_object(str(path))
        except ApplicationDatabase.ObjectExisted as existed:
            replay = QuestionBox(self, "%s \"%s\" already existed, replace it?" %
                                       (existed.object.identifier, existed.object.name))
            if replay == msgBox.Yes:
                self.__database.replace(existed.object)
                self.__replace_item(existed.object)
        except ApplicationDatabase.ImportError as error:
            WarningBox(self, error.message)
        else:
            for obj in new_objects:
                logging.info("%s added to database" % obj)
                self.__add_item(obj)

    def eventFilter(self, p_object, event=None):
        """
        This event filter required to detect when "Delete" key press then confirmation dialog appeared
        to delete the object selected under mouse.

        :type p_object: QtCore.QObject
        :type event: QtCore.QEvent
        """
        # noinspection PyUnresolvedReferences
        if p_object is self and event.type() == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_Delete:
            item = self.currentItem()
            if item not in self.__undeleteable_items and item not in set(self.__nodes.values()):
                name = unicode(item.text(QDatabaseTreeWidget.NAME_COLUMN))
                reply = QuestionBox(self, "Do you really want to delete it?")
                if reply == msgBox.Yes:
                    for obj in self.__database.remove(name=name):
                        self.__remove_item(obj)
                return True
        return QTreeWidgetDrag.eventFilter(self, p_object, event)


class DatabaseView(QStackWidgetTab):
    def __init__(self, parent, database):
        """
        :type parent: QtGui.QWidget
        :type database: database.ApplicationDatabase
        """
        QStackWidgetTab.__init__(self, parent)
        self.__data_tree = QDatabaseTreeWidget(self, database)

        # Create widget layout
        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.addWidget(self.__data_tree)

    def onSetActive(self):
        self.__data_tree.reload()
