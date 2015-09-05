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
import sys
import webbrowser
import psutil

from qt import QtCore, QtGui, connect, Slot, backend_name
from qt import core_version as QtCoreVersion
from qt import version as QtBackendVersion

os.environ["MATPLOTLIBDATA"] = os.path.join(os.path.abspath(os.curdir), "mpl-data")
from matplotlib import __version__ as matplotlib_version

from views.controls import ControlBar, ControlsView
from views.common import QStackedWidget, QuestionBox, ErrorBox, ExtendedErrorBox, msgBox
from views.dbview import DatabaseView
from views.summary import SummaryView
from views.numerics import NumericsView
from views.wafer import WaferProcessView
from views.resist import ResistView
from views.mask import MaskView
from views.imaging import ImagingView
from views.exposure import ExposureFocusView
from views.peb import PostExposureBakeView
from views.development import DevelopmentView
from views.metrology import MetrologyView
from views.diffraction import DiffractionPatternView
from views.simulations import AerialImageView, ImageInResistView, LatentImageView, \
    PebLatentImageView, DevelopContoursView, ResistProfileView
from views.sets import SimulationSets
from views.appconfig import AppConfigurationView

from resources import Resources
from database.common import ApplicationDatabase
from database.dbparser import GenericParser, GenericParserError
from config import MEGABYTE
from optolithiumc import OPTOLITHIUM_CORE_VERSION

import config
import helpers
import options
import plugins

import core


__author__ = 'Alexei Gladkikh'
from info import __version__


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


class AboutWindow(QtGui.QDialog):

    def __init__(self, parent):
        """:type parent: QtGui.QMainWindow"""
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle("About")
        self.setWindowIcon(parent.windowIcon())

        logo_banner = os.path.join(os.getcwd(), "icons/Banner.png")
        self.__program_banner = QtGui.QLabel(self)
        self.__program_banner.setPixmap(QtGui.QPixmap(logo_banner))
        self.__program_banner.setAlignment(QtCore.Qt.AlignCenter)

        self.__close_button = QtGui.QPushButton("Close", self)
        self.__close_button.setMaximumWidth(config.MAXIMUM_DIALOG_BUTTON_WIDTH)
        connect(self.__close_button.clicked, self.close)
        self.__info_box = QtGui.QGroupBox("Information", self)
        self.__info_layout = QtGui.QFormLayout(self.__info_box)
        widget_t = QtGui.QLabel
        self.__info_layout.addRow("Application:", widget_t(config.APPLICATION_NAME + " " + __version__))
        self.__info_layout.addRow("Author:", widget_t(__author__))
        self.__info_layout.addRow("Core version:", widget_t(OPTOLITHIUM_CORE_VERSION))
        self.__info_layout.addRow("Python version:", widget_t(sys.version))
        self.__info_layout.addRow("%s version:" % backend_name, widget_t(QtBackendVersion))
        self.__info_layout.addRow("Qt4 version:", widget_t(QtCoreVersion))
        self.__info_layout.addRow("Matplotlib version:", widget_t(matplotlib_version))

        self.__layout = QtGui.QGridLayout(self)
        self.__layout.addWidget(self.__program_banner, 0, 0, 1, 2)
        self.__layout.addWidget(self.__info_box, 1, 0, 1, 2)
        self.__layout.addWidget(self.__close_button, 2, 1)


class MemoryUsageView(QtGui.QProgressBar):
    STYLE = """
    QProgressBar{
        text-align: center
    }

    QProgressBar::chunk {
        width: 10px;
        margin: 0px;
    }
    """

    def __init__(self, parent, pid):
        QtGui.QProgressBar.__init__(self, parent)
        self.__process = psutil.Process(pid)
        self.setStyleSheet(MemoryUsageView.STYLE)
        self.setFormat("%v MiB")
        self.update_memory()

    def update_memory(self):
        usage = psutil.virtual_memory()
        meminfo = self.__process.get_memory_info()
        total = int(usage.total/MEGABYTE)
        free = int(usage.available/MEGABYTE)
        required = int(meminfo.rss/MEGABYTE)
        self.setMaximum(free + required)
        self.setValue(required)
        self.setToolTip("Available: %d MiB\nTotal: %d MiB" % (free, total))


class StatusBar(QtGui.QStatusBar):

    def __init__(self, parent):
        QtGui.QStatusBar.__init__(self, parent)
        self.setObjectName("StatusBar")
        self.__mem_usage = MemoryUsageView(self, os.getpid())
        self.__mem_usage.setMaximumWidth(200)
        self.addPermanentWidget(self.__mem_usage)
        self.__mem_update_timer = QtCore.QTimer(self)
        connect(self.__mem_update_timer.timeout, self.__mem_usage.update_memory)
        self.__mem_update_timer.start(config.Configuration.memory_update_interval)


class MainWindow(QtGui.QMainWindow):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        
        Resources.load(os.getcwd(), ["icons", "xhtml"], icon_driver=QtGui.QIcon)

        self.tabs = dict()
        """:type: dict from str to QtGui.QWidget"""

        self.tabs_stack = None
        """:type: QStackedWidget"""

        self.window_layout = None
        """:type: QtGui.QLayout"""

        self.controls_view = None
        """:type: ControlsView"""

        self.about_window = None
        """:type: AboutWindow"""

        self.dbparser = None
        """:type: GenericParser"""

        self.appdb = None
        """:type: database.ApplicationDatabase"""

        self.plugins = None
        """:type: plugins.Container"""

        self.my_state = None
        self.my_geometry = None

        self.resize(1080, 760)
        self.center()

        try:
            config.openLayerMapConfig(config.Configuration.layer_map_path)
        except config.LayerMapConfig.ParseError:
            ErrorBox(self, "Can't parse '%s' GDSII layer mapping file!" % config.Configuration.layer_map_path)
            sys.exit(-1)

        self.configure_dbparser()
        self.configure_database()
        self.configure_plugins()
        self.configure_windows()

        self.appconfig = AppConfigurationView(self)

        # Create initial options object
        self.options = options.Options.default()

        self.core = core.Core(self.options)

        connect(self.options.changed, self.setApplicationTitle)
        self.setApplicationTitle()
        self.setWindowIcon(QtGui.QIcon("icons/Logo.png"))

        self.configure_controls()
        self.configure_window_state()

        logging.info("Configure status bar")
        self.status_bar = StatusBar(self)
        self.setStatusBar(self.status_bar)
        self.statusBar().showMessage("Ready")

        self.state_changed = False

        logging.info("Configuration done")

        logging.info("Loading options")
        if len(sys.argv) > 1:
            path = sys.argv[1]
            self._open_options(path)

        self.show()

    # noinspection PyPep8Naming
    @Slot()
    def setApplicationTitle(self):
        self.setWindowTitle("%s - [%s]%s" % (
            config.APPLICATION_NAME,
            self.options.filename,
            " *" if not self.options.is_saved else ""))

    # noinspection PyArgumentList
    def center(self):
        frame = self.frameGeometry()
        screen = QtGui.QApplication.desktop().screenNumber(QtGui.QApplication.desktop().cursor().pos())
        center = QtGui.QApplication.desktop().screenGeometry(screen).center()
        frame.moveCenter(center)
        self.move(frame.topLeft())

    def configure_dbparser(self):
        try:
            self.dbparser = GenericParser()

        except GenericParserError as error:
            ErrorBox(self, "Critical error in database parser: %s" % error.message)
            sys.exit(-1)

    def configure_database(self):
        logging.info("Configure application database")

        try:
            self.appdb = ApplicationDatabase.open(config.Configuration.db_path, create=True)

        except ApplicationDatabase.DefaultObjectsError as missing_defaults:
            reply = QuestionBox(self, "Default objects %s not found in the database.\n"
                                      "Do you want to create these objects?\n"
                                      "Note: otherwise program will be closed." % missing_defaults.message,
                                msgBox.Yes | msgBox.No, msgBox.Yes)
            if reply == msgBox.Yes:
                self.appdb = missing_defaults.fix()
            else:
                sys.exit(0)

        except ApplicationDatabase.OperationError as error:
            reply = QuestionBox(self,
                                "Application database can't be opened:\n%s\n"
                                "Do you want to replace it with the empty compatible database?\n"
                                "Note: if you select Yes all previous data will be erased!" % error.message,
                                msgBox.Yes | msgBox.No, msgBox.No)
            if reply == msgBox.Yes:
                self.appdb = ApplicationDatabase.create(config.Configuration.db_path, rewrite=True)
            else:
                sys.exit(0)

        self.appdb.parser = self.dbparser

        # FIXME: Handle case when database can't be created for specified path

    def configure_plugins(self):
        logging.info("Configure application plugins")
        self.plugins = plugins.Container.load(*config.Configuration.plugin_paths)
        inspector = plugins.Inspector(self.appdb)
        for plugin in self.plugins:
            try:
                inspector.verify(plugin)
            except ApplicationDatabase.SqlError as error:
                logging.info("Can't acquire plugin '%s': %s" % (plugin.entry.name, error.message))
            except plugins.Inspector.CommonError as error:
                logging.info("Verification plugin error '%s': %s" % (plugin.entry.name, error.message))

        dll_plugin_names = {plugin.entry.name for plugin in self.plugins}
        db_plugin_names = set()
        for table in self.appdb.plugin_tables:
            db_plugin_names.update([str(p_object.name) for p_object in self.appdb[table]])

        missed_plugins = db_plugin_names - dll_plugin_names
        for plugin_name in missed_plugins:
            reply = QuestionBox(self, "Plugin %s wasn't loaded and must be removed from the application database. "
                                      "Do you want continue? If canceled you can try to fix missed dynamic library. "
                                      "Note: if you continue all dependent objects also will be deleted." % plugin_name,
                                msgBox.Yes | msgBox.Cancel, msgBox.Cancel)

            if reply == msgBox.Cancel:
                sys.exit(0)

            self.appdb.remove(plugin_name)

    def configure_windows(self):
        logging.info("Configure application windows")
        self.about_window = AboutWindow(self)

    def configure_window_state(self):
        self.controls_view["Parameters"]["Numerics"].trigger()
        # self.controls_view["Parameters"]["Summary"].trigger()

    def save_state(self):
        self.my_state = self.saveState()
        self.my_geometry = self.saveGeometry()

    def load_state(self):
        self.restoreState(self.my_state)
        self.restoreGeometry(self.my_geometry)

    def options_modified_handler(self):
        """
        Check whether options has been modified and ask user to save it before reset options.

        :return: True - if action accepted and False if rejected
        :rtype: bool
        """
        if not self.options.is_saved:
            reply = QuestionBox(
                self, "Options data had been changed but not saved.\n"
                      "Do you want save it to %s?" % self.options.filename,
                msgBox.Cancel | msgBox.No | msgBox.Yes)
            if reply == msgBox.Yes:
                self.save_options()
                return True
            elif reply == msgBox.No:
                return True
            else:
                return False
        else:
            return True

    def closeEvent(self, event):
        if self.options_modified_handler():
            event.accept()
        else:
            event.ignore()

    @Slot()
    def new_options(self):
        if self.options_modified_handler():
            default_options = self.options.default()
            self.options.assign(default_options)
            for tab in self.tabs.values():
                tab.reset()

    @Slot()
    def save_options(self):
        if not self.options.coupled:
            path, _ = QtGui.QFileDialog.getSaveFileName(
                self.centralWidget(), "Save Options As...", self.options.path, config.OPTIONS_EXTENSION)
        else:
            path = self.options.path

        self.options.save(path)
        self.statusBar().showMessage("Options has been successfully saved to %s" % path,
                                     config.STATUS_BAR_MESSAGE_DURATION)

    @Slot()
    def save_options_as(self):
        path, _ = QtGui.QFileDialog.getSaveFileName(
            self.centralWidget(), "Save Options As...", self.options.path, config.OPTIONS_EXTENSION)

        self.options.save(path)
        self.statusBar().showMessage("Options has been successfully saved to %s" % path,
                                     config.STATUS_BAR_MESSAGE_DURATION)

    def _open_options(self, path):
        try:
            self.options.open(path)
        except options.OptionsLoadErrors as errors:
            error_box = ExtendedErrorBox(
                "Options load errors occurred",
                "During loading given option file %s the errors occurred; default values will be loaded" % path,
                str("\n").join([error.message for error in errors]))
            reply = error_box.exec_()
            if reply == error_box.Close:
                sys.exit(-1)

        for tab in self.tabs.values():
            tab.reset()

        self.statusBar().showMessage("Options has been successfully loaded from %s" % path,
                                     config.STATUS_BAR_MESSAGE_DURATION)

        logging.info("Options has been successfully loaded from %s" % path)

    @Slot()
    def load_options(self):
        if self.options_modified_handler():
            path, _ = QtGui.QFileDialog.getOpenFileName(
                self.centralWidget(), "Open Options", self.options.path, config.OPTIONS_EXTENSION)
            self._open_options(path)

    # noinspection PyPep8Naming
    def changeStackView(self):
        sender_name = str(self.sender().objectName())
        widget = self.tabs[sender_name]
        self.tabs_stack.setCurrentWidget(widget)

    # noinspection PyPep8Naming,PyMethodMayBeStatic
    def onWebsiteOpen(self):
        webbrowser.open(config.APPLICATION_WEBSITE)

    # noinspection PyPep8Naming
    def onPrint(self):
        dialog = QtGui.QPrintDialog()
        if dialog.exec_() == QtGui.QDialog.Accepted:
            self.tabs["Parameters.Summary"].print_(dialog.printer())

    # noinspection PyPep8Naming
    def onPrintPreview(self):
        dialog = QtGui.QPrintPreviewDialog()
        connect(dialog.paintRequested, self.tabs["Parameters.Summary"].print_)
        dialog.exec_()

    # noinspection PyPep8Naming,PyMethodMayBeStatic
    def onPageSetup(self):
        dialog = QtGui.QPageSetupDialog()
        dialog.exec_()

    def configure_controls(self):
        logging.info("Configure window controls")
        controls_data = [
            ControlsView.ControlData(name="File", text="&File", actions=[
                ControlBar.ActionData(
                    name="New",
                    text="&New",
                    icon=Resources("icons/NewFile"),
                    callback=self.new_options,
                    status_tip="Create a new document",
                    shortcut="Ctrl+N"),
                ControlBar.ActionData(
                    name="Open",
                    text="&Open",
                    icon=Resources("icons/Open"),
                    callback=self.load_options,
                    status_tip="Open an existing document",
                    shortcut="Ctrl+O"),
                ControlBar.ActionData(
                    name="Save",
                    text="&Save",
                    icon=Resources("icons/Save"),
                    callback=self.save_options,
                    status_tip="Save the active document"),
                ControlBar.ActionData(
                    name="SaveAs",
                    text="Save As ...",
                    callback=self.save_options_as,
                    status_tip="Save the active document with a new name"),
                None,
                ControlBar.ActionData(
                    name="Preferences",
                    text="&Preferences",
                    callback=self.appconfig.exec_,
                    icon=Resources("icons/Preferences"),
                    status_tip="Edit preferences settings"),
                None,
                ControlBar.ActionData(
                    name="Print",
                    text="Print...",
                    callback=self.onPrint,
                    status_tip="Print the active document",
                    shortcut="Ctrl+P"),
                ControlBar.ActionData(
                    name="PrintPreview",
                    text="Print Preview",
                    callback=self.onPrintPreview,
                    status_tip="Display a preview of the report"),
                ControlBar.ActionData(
                    name="PrintSetup",
                    text="Print Setup...",
                    # callback=self.onPageSetup,
                    status_tip="Change the printer and printing options"),
                None,
                ControlBar.ActionData(
                    name="Exit",
                    text="&Exit",
                    icon=Resources("icons/Exit"),
                    callback=self.close,
                    status_tip="Quit the application; prompts to save document",
                    shortcut="Ctrl+Q")
            ]),
            ControlsView.ControlData(name="View", text="&View", actions=[
                ControlBar.ActionData(
                    name="Database",
                    text="&Database",
                    icon=Resources("icons/Database"),
                    callback=self.changeStackView,
                    status_tip="%s database storage" % config.APPLICATION_NAME),
                ControlBar.ActionData(
                    name="Queue",
                    text="&Queue",
                    icon=Resources("icons/Queue"),
                    status_tip="Show the sim_region queue window"),
                ControlBar.ActionData(
                    name="Warnings",
                    text="&Warnings",
                    status_tip="Show the warning list window")
            ]),
            ControlsView.ControlData(name="Parameters", text="&Parameters", actions=[
                ControlBar.ActionData(
                    name="Numerics",
                    text="&Numerics",
                    icon=Resources("icons/Numerics"),
                    callback=self.changeStackView,
                    status_tip="Numerics"),
                ControlBar.ActionData(
                    name="WaferProcesses",
                    text="&Wafer Processes",
                    icon=Resources("icons/WaferStack"),
                    callback=self.changeStackView,
                    status_tip="Wafer Processes"),
                ControlBar.ActionData(
                    name="Resist",
                    text="&Resist",
                    icon=Resources("icons/Resist"),
                    callback=self.changeStackView,
                    status_tip="Resist"),
                ControlBar.ActionData(
                    name="CoatAndPrebake",
                    text="&Coat and prebake",
                    callback=self.changeStackView,
                    status_tip="Coat and prebake"),
                ControlBar.ActionData(
                    name="Mask",
                    text="&Mask",
                    icon=Resources("icons/Mask"),
                    callback=self.changeStackView,
                    status_tip="Mask"),
                ControlBar.ActionData(
                    name="ImagingTool",
                    text="&Imaging Tool",
                    icon=Resources("icons/ImagingTool"),
                    callback=self.changeStackView,
                    status_tip="Imaging Tool"),
                ControlBar.ActionData(
                    name="ExposureAndFocus",
                    text="&Exposure and Focus",
                    icon=Resources("icons/ExposureAndFocus"),
                    callback=self.changeStackView,
                    status_tip="Exposure and Focus"),
                ControlBar.ActionData(
                    name="PostExposureBake",
                    text="&Post Exposure Bake",
                    icon=Resources("icons/PEB"),
                    callback=self.changeStackView,
                    status_tip="Post Exposure Bake"),
                ControlBar.ActionData(
                    name="Development",
                    text="&Development",
                    icon=Resources("icons/Development"),
                    callback=self.changeStackView,
                    status_tip="Development"),
                ControlBar.ActionData(
                    name="Metrology",
                    text="M&etrology",
                    icon=Resources("icons/Metrology"),
                    callback=self.changeStackView,
                    status_tip="Metrology"),
                ControlBar.ActionData(
                    name="Summary",
                    text="&Summary",
                    icon=Resources("icons/Summary"),
                    callback=self.changeStackView,
                    status_tip="Summary")
            ]),
            ControlsView.ControlData(name="Simulation", text="&Simulations", actions=[
                ControlBar.ActionData(
                    name="DiffractionPattern",
                    text="&Diffraction Pattern",
                    icon=Resources("icons/DiffractionPattern"),
                    callback=self.changeStackView,
                    status_tip="Diffraction Pattern"),
                ControlBar.ActionData(
                    name="AerialImage",
                    text="&Aerial Image",
                    icon=Resources("icons/AerialImage"),
                    callback=self.changeStackView,
                    status_tip="Aerial Image"),
                ControlBar.ActionData(
                    name="ImageInResist",
                    text="&Image in Resist",
                    icon=Resources("icons/ImageInResist"),
                    callback=self.changeStackView,
                    status_tip="Image in Resist"),
                ControlBar.ActionData(
                    name="ExposedLatentImage",
                    text="&Exposed Latent Image",
                    icon=Resources("icons/LatentImage"),
                    callback=self.changeStackView,
                    status_tip="Exposed Latent Image"),
                ControlBar.ActionData(
                    name="PEBLatentImage",
                    text="&PEB Latent Image",
                    icon=Resources("icons/PostBakeImage"),
                    callback=self.changeStackView,
                    status_tip="PEB Latent Image"),
                ControlBar.ActionData(
                    name="DevelopTimeContours",
                    text="&Develop Time Contours",
                    icon=Resources("icons/DevelopTimeContours"),
                    callback=self.changeStackView,
                    status_tip="Develop Time Contours"),
                ControlBar.ActionData(
                    name="ResistProfile",
                    text="&Resist Profile",
                    icon=Resources("icons/ResistProfile"),
                    callback=self.changeStackView,
                    status_tip="Resist Profile"),
                None,
                ControlBar.ActionData(
                    name="SimulationSets",
                    text="&Simulation Sets",
                    icon=Resources("icons/SimulationSets"),
                    callback=self.changeStackView,
                    status_tip="Simulation Sets")
            ]),
            ControlsView.ControlData(name="Help", text="&Help", actions=[
                ControlBar.ActionData(
                    name="Manual",
                    text="&Manual",
                    icon=Resources("icons/Help"),
                    status_tip="Application manual of %s" % config.APPLICATION_NAME),
                ControlBar.ActionData(
                    name="About",
                    text="&About %s" % config.APPLICATION_NAME,
                    icon=Resources("icons/About"),
                    callback=self.about_window.show,
                    status_tip="Display program information, version, copyright and etc"),
                ControlBar.ActionData(
                    name="Warnings",
                    text="%s website" % config.APPLICATION_NAME,
                    icon=Resources("icons/Website"),
                    callback=self.onWebsiteOpen,
                    status_tip="Launch browser to %s project website" % config.APPLICATION_NAME)
            ]),
        ]

        controls_group = [("View", "Parameters", "Simulation")]

        logging.info("Create controls view")
        self.controls_view = ControlsView(self, controls_data, controls_group)

        logging.info("Create database view")
        self.tabs["View.Database"] = DatabaseView(self, self.appdb)
        
        logging.info("Create numerics view")
        self.tabs["Parameters.Numerics"] = NumericsView(self, self.options)

        logging.info("Create wafer processes view")
        self.tabs["Parameters.WaferProcesses"] = WaferProcessView(
            self, self.options.wafer_process, self.appdb)

        logging.info("Create resist view")
        self.tabs["Parameters.Resist"] = ResistView(
            self, self.options.wafer_process, self.options.peb.temp, self.appdb)

        logging.info("Create mask view")
        self.tabs["Parameters.Mask"] = MaskView(self, self.options, self.appdb)

        logging.info("Create imaging tool view")
        self.tabs["Parameters.ImagingTool"] = ImagingView(self, self.options, self.appdb)

        logging.info("Create exposure and focus view")
        self.tabs["Parameters.ExposureAndFocus"] = ExposureFocusView(
            self, self.options.exposure_focus, self.options.wafer_process)

        logging.info("Create post exposure bake view")
        self.tabs["Parameters.PostExposureBake"] = PostExposureBakeView(self, self.options)

        logging.info("Create development view")
        self.tabs["Parameters.Development"] = DevelopmentView(
            self, self.options.development, self.options.wafer_process)

        logging.info("Create metrology view")
        self.tabs["Parameters.Metrology"] = MetrologyView(self, self.options)

        logging.info("Create summary view")
        self.tabs["Parameters.Summary"] = SummaryView(self, self.options)

        logging.info("Create diffraction pattern simulation view")
        self.tabs["Simulation.DiffractionPattern"] = DiffractionPatternView(self, self.core)

        logging.info("Create aerial image simulation view")
        self.tabs["Simulation.AerialImage"] = AerialImageView(self, self.core.aerial_image, self.options)

        logging.info("Create image in resist simulation view")
        self.tabs["Simulation.ImageInResist"] = ImageInResistView(self, self.core.image_in_resist, self.options)

        logging.info("Create exposed latent image simulation view")
        self.tabs["Simulation.ExposedLatentImage"] = LatentImageView(self, self.core.latent_image, self.options)

        logging.info("Create peb latent image simulation view")
        self.tabs["Simulation.PEBLatentImage"] = PebLatentImageView(self, self.core.peb_latent_image, self.options)

        logging.info("Create develop time contours simulation view")
        self.tabs["Simulation.DevelopTimeContours"] = \
            DevelopContoursView(self, self.core.develop_contours, self.options)

        logging.info("Create resist profile simulation view")
        self.tabs["Simulation.ResistProfile"] = ResistProfileView(self, self.core.resist_profile, self.options)

        logging.info("Create simulation sets view")
        self.tabs["Simulation.SimulationSets"] = SimulationSets(self, self.core)

        logging.info("Configure stack widget")
        window = QtGui.QWidget()
        self.setCentralWidget(window)
        self.tabs_stack = QStackedWidget(window)

        self.window_layout = QtGui.QHBoxLayout(window)
        self.window_layout.addWidget(self.tabs_stack)

        # self.scroll_widget = QtGui.QScrollArea()
        # self.scroll_widget.setWidget(window)
        # self.scroll_widget.setWidgetResizable(True)

        for control in self.tabs.values():
            self.tabs_stack.addWidget(control)
