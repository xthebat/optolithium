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
import subprocess
import sys
import helpers
import config
import logging as module_logging
from qt import QtGui, QtCore, connect, Slot
from views.common import WarningBox
from config import Configuration, MEGABYTE, MAXIMUM_DIALOG_BUTTON_WIDTH


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.DEBUG)
helpers.logStreamEnable(logging)


class AppConfigurationView(QtGui.QDialog):

    def int_edit(self):
        edit = QtGui.QLineEdit(self)
        edit.setMaximumWidth(50)
        edit.setValidator(QtGui.QIntValidator(self))
        return edit

    def button(self, name, callback):
        btn = QtGui.QPushButton(name, self)
        btn.setFixedWidth(60)
        connect(btn.clicked, callback)
        return btn

    def __init__(self, parent):
        """
        :param QtGui.QWidget parent: Exposure and focus view widget parent
        """
        super(AppConfigurationView, self).__init__(parent)

        self.setWindowTitle(config.APPLICATION_NAME + " Application Configuration Data")

        self.grid_lay = QtGui.QGridLayout()

        cell_size = 75

        self.grid_lay.setColumnMinimumWidth(1, cell_size)
        self.grid_lay.setColumnMinimumWidth(2, cell_size)
        self.grid_lay.setColumnMinimumWidth(3, cell_size)
        self.grid_lay.setColumnMinimumWidth(4, cell_size)

        self.map_path_label = QtGui.QLabel("GDSII layer map path:", self)
        self.map_path_edit = QtGui.QLineEdit(self)
        self.map_path_edit.setMinimumWidth(4*cell_size)
        self.map_path_btn_browse = self.button("Browse", self.onBrowseLayerMapPath)
        self.map_path_btn_edit = self.button("Edit", self.onLayerMapEdit)

        self.grid_lay.addWidget(self.map_path_label, 0, 0)
        self.grid_lay.addWidget(self.map_path_edit, 0, 1, 1, 4)
        self.grid_lay.addWidget(self.map_path_btn_browse, 0, 5)
        self.grid_lay.addWidget(self.map_path_btn_edit, 0, 6)

        self.db_path_label = QtGui.QLabel("Application database path:", self)
        self.db_path_edit = QtGui.QLineEdit(self)
        self.db_path_edit.setMinimumWidth(4*cell_size)
        self.db_path_btn_browse = self.button("Browse", self.onBrowseApplicationDatabase)

        self.grid_lay.addWidget(self.db_path_label, 1, 0)
        self.grid_lay.addWidget(self.db_path_edit, 1, 1, 1, 4)
        self.grid_lay.addWidget(self.db_path_btn_browse, 1, 5)

        self.plugin_paths_label = QtGui.QLabel("Plugins paths:", self)
        self.plugin_paths_edit = QtGui.QLineEdit(self)
        self.plugin_paths_edit.setMinimumWidth(4*cell_size)
        self.plugin_paths_btn_add = self.button("Add", self.onPluginPathAdd)

        self.grid_lay.addWidget(self.plugin_paths_label, 2, 0)
        self.grid_lay.addWidget(self.plugin_paths_edit, 2, 1, 1, 4)
        self.grid_lay.addWidget(self.plugin_paths_btn_add, 2, 5)

        self.memory_update_label = QtGui.QLabel("Memory update interval (ms):", self)
        self.memory_update_edit = self.int_edit()

        self.grid_lay.addWidget(self.memory_update_label, 3, 0)
        self.grid_lay.addWidget(self.memory_update_edit, 3, 1)

        self.dpi_label = QtGui.QLabel("Graphics DPI:", self)
        self.dpi_edit = self.int_edit()

        self.grid_lay.addWidget(self.dpi_label, 4, 0)
        self.grid_lay.addWidget(self.dpi_edit, 4, 1)

        self.gds_size_label = QtGui.QLabel("Maximum size of GDSII file (MiB):", self)
        self.gds_size_edit = self.int_edit()

        self.grid_lay.addWidget(self.gds_size_label, 3, 2)
        self.grid_lay.addWidget(self.gds_size_edit, 3, 3)

        self.thread_count_label = QtGui.QLabel("Maximum thread count:", self)
        self.thread_count_edit = self.int_edit()

        self.grid_lay.addWidget(self.thread_count_label, 4, 2)
        self.grid_lay.addWidget(self.thread_count_edit, 4, 3)

        self.buttons_hlay = QtGui.QHBoxLayout()

        self.button_ok = self.button("Ok", self.accept)
        self.button_ok.setFixedWidth(MAXIMUM_DIALOG_BUTTON_WIDTH)
        self.button_cancel = self.button("Cancel", self.reject)
        self.button_cancel.setFixedWidth(MAXIMUM_DIALOG_BUTTON_WIDTH)
        self.button_ok.setDefault(True)

        self.buttons_hlay.addWidget(self.button_cancel)
        self.buttons_hlay.addWidget(self.button_ok)
        self.buttons_hlay.setAlignment(QtCore.Qt.AlignRight)

        self.vlay = QtGui.QVBoxLayout(self)
        self.vlay.addLayout(self.grid_lay)
        self.vlay.addLayout(self.buttons_hlay)

    def _set_config_values(self):
        self.map_path_edit.setText(Configuration.layer_map_path)
        self.db_path_edit.setText(Configuration.db_path)
        self.plugin_paths_edit.setText(Configuration.PLUGIN_PATHS_SEPARATOR.join(Configuration.plugin_paths))
        self.memory_update_edit.setText(str(Configuration.memory_update_interval))
        self.dpi_edit.setText(str(Configuration.dpi))
        self.gds_size_edit.setText(str(Configuration.maximum_gds_size/MEGABYTE))
        self.thread_count_edit.setText(str(Configuration.thread_count))

    def showEvent(self, *args, **kwargs):
        self._set_config_values()
        super(AppConfigurationView, self).showEvent(*args, **kwargs)

    # noinspection PyPep8Naming
    @Slot()
    def onLayerMapEdit(self):
        filepath = self.map_path_edit.text()
        if os.path.isfile(filepath) and os.access(filepath, os.W_OK) or \
           os.access(os.path.dirname(filepath), os.W_OK):
            if sys.platform.startswith(config.darwin):
                subprocess.call(("open", filepath))
            elif os.name == config.nt:
                subprocess.call(("notepad", filepath))
            elif os.name == config.posix:
                subprocess.call(("xdg-open", filepath))
        else:
            WarningBox(self, "Selected file %s can't be written" % filepath)

    # noinspection PyPep8Naming
    @Slot()
    def onBrowseLayerMapPath(self):
        file_path, _ = QtGui.QFileDialog.getOpenFileName(
            self, "Choose GDSII Layer Map File",
            self.map_path_edit.text(), "JavaScript Object Notation files (*.json)")

        if file_path:
            self.map_path_edit.setText(file_path)

    # noinspection PyPep8Naming
    @Slot()
    def onBrowseApplicationDatabase(self):
        file_path, _ = QtGui.QFileDialog.getOpenFileName(
            self, "Choose Application Database File",
            self.db_path_edit.text(), "SQLite Database (*.db)")

        if file_path:
            self.db_path_edit.setText(file_path)

    # noinspection PyPep8Naming
    @Slot()
    def onPluginPathAdd(self):
        plugin_path = QtGui.QFileDialog.getExistingDirectory(
            self, "Choose Additional Plugins Directory",
            Configuration.SYSTEM_PLUGINS_PATH,
            QtGui.QFileDialog.ShowDirsOnly | QtGui.QFileDialog.DontResolveSymlinks)

        if plugin_path and os.access(plugin_path, os.R_OK) and \
           plugin_path not in self.plugin_paths_edit.text().split(Configuration.PLUGIN_PATHS_SEPARATOR):
            path = self.plugin_paths_edit.text() + Configuration.PLUGIN_PATHS_SEPARATOR + os.path.abspath(plugin_path)
            self.plugin_paths_edit.setText(path)

    def accept(self, *args, **kwargs):
        Configuration.layer_map_path = self.map_path_edit.text()
        Configuration.db_path = self.db_path_edit.text()
        Configuration.plugin_paths = self.plugin_paths_edit.text()
        logging.info("%s" % Configuration.plugin_paths)

        Configuration.dpi = self.dpi_edit.text()
        Configuration.thread_count = self.thread_count_edit.text()
        Configuration.maximum_gds_size = int(self.gds_size_edit.text()) * MEGABYTE
        Configuration.memory_update_interval = self.memory_update_edit.text()
        Configuration.save()
        return super(AppConfigurationView, self).accept(*args, **kwargs)