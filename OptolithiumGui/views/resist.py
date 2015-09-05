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

from qt import QtGui, QtCore, connect, disconnect, Slot
from database import orm
from database.common import ApplicationDatabase
from views.common import QStackWidgetTab, QLineEditNumeric, QGraphPlot, QLabel, QuestionBox, ErrorBox, msgBox
from views.development import DevelopmentGraph
from options import structures

import config
import helpers


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.DEBUG)
helpers.logStreamEnable(logging)


class AbstractResistInfoBox(QtGui.QGroupBox):

    def __init__(self, title, parent):
        QtGui.QGroupBox.__init__(self, title, parent)

    # noinspection PyPep8Naming
    def setObject(self, resist):
        pass


class AbstractResistTab(QStackWidgetTab):

    def __init__(self, parent):
        """:type parent: QtGui.QWidget"""
        # FIXME: Add parent to QStackWidgetTab
        QStackWidgetTab.__init__(self, parent)

    # noinspection PyPep8Naming
    def setObject(self, resist):
        pass

    def update_view(self):
        pass


class AbstractResistInfoTab(AbstractResistTab):

    class General(AbstractResistInfoBox):
        def __init__(self, parent):
            AbstractResistInfoBox.__init__(self, "General", parent)

            self.__general_layout = QtGui.QFormLayout(self)

            self.__name = QLabel(self)
            self.__wavelength = QLabel(self, frmt="%s <i>nm</i>")
            self.__refractive = QLabel(self)

            self.__general_layout.addRow("Name:", self.__name)
            self.__general_layout.addRow("Wavelength:", self.__wavelength)
            self.__general_layout.addRow("Refractive index:", self.__refractive)

        # noinspection PyPep8Naming
        def setObject(self, resist):
            """:type resist: options.structures.Resist"""
            # logging.debug("Set resist: %s" % resist)
            p_object = resist if isinstance(resist, orm.Resist) else resist.db
            self.__name.setObject(p_object, orm.Resist.name)
            self.__wavelength.setObject(resist.exposure, orm.ExposureParameters.wavelength)
            self.__refractive.setObject(resist.exposure, orm.ExposureParameters.n)

    class Exposure(AbstractResistInfoBox):
        def __init__(self, parent):
            AbstractResistInfoBox.__init__(self, "Exposure", parent)

            self.__lnar = QLabel(self, frmt="%s <i>nm2/s</i>")
            self.__ea = QLabel(self, frmt="%s <i>kcal/mole</i>")

            self.__dill_a = QLabel(self, frmt="%s <i>1/um</i>")
            self.__dill_b = QLabel(self, frmt="%s <i>1/um</i>")
            self.__dill_c = QLabel(self, frmt="%s <i>cm2/mJ</i>")

            self.__exposure_layout = QtGui.QFormLayout(self)

            self.__exposure_layout.addRow("Ln(Ar):", self.__lnar)
            self.__exposure_layout.addRow("Ea:", self.__ea)

            self.__exposure_layout.addRow("Dill A:", self.__dill_a)
            self.__exposure_layout.addRow("Dill B:", self.__dill_b)
            self.__exposure_layout.addRow("Dill C:", self.__dill_c)

        # noinspection PyPep8Naming
        def setObject(self, resist):
            """:type resist: options.structures.Resist"""
            # TODO: Add minimum and maximum
            self.__lnar.setObject(resist.peb, orm.PebParameters.ln_ar)
            self.__ea.setObject(resist.peb, orm.PebParameters.ea)

            self.__dill_a.setObject(resist.exposure, orm.ExposureParameters.a)
            self.__dill_b.setObject(resist.exposure, orm.ExposureParameters.b)
            self.__dill_c.setObject(resist.exposure, orm.ExposureParameters.c)

    class Development(AbstractResistInfoBox):
        def __init__(self, parent):
            AbstractResistInfoBox.__init__(self, "Development", parent)

            self.__label_model_name = QLabel(self)
            self.__dev_layout = QtGui.QFormLayout(self)
            self.__dev_layout.addRow("Model:", self.__label_model_name)

        # noinspection PyPep8Naming
        def setObject(self, resist):
            """:type resist: options.structures.Resist"""
            # name = resist.developer.name if resist.developer is not None else str()
            # self.__label_model_name.setText(name)
            p_object = resist if isinstance(resist, orm.Resist) else resist.db
            self.__label_model_name.setObject(p_object, orm.Resist.developer)

    def __init__(self, parent):
        """:type parent: QtGui.QWidget"""
        AbstractResistTab.__init__(self, parent)

        self._hlayout = QtGui.QHBoxLayout()

        self.__info_boxes = dict()
        """:type: dict from str to AbstractResistInfoBox"""

        self.__info_boxes["general"] = AbstractResistInfoTab.General(self)
        self.__info_boxes["exposure"] = AbstractResistInfoTab.Exposure(self)
        self.__info_boxes["development"] = AbstractResistInfoTab.Development(self)

        self.__info_layout = QtGui.QVBoxLayout()
        self.__info_layout.addWidget(self.__info_boxes["general"])
        self.__info_layout.addWidget(self.__info_boxes["exposure"])
        self.__info_layout.addWidget(self.__info_boxes["development"])
        self.__info_layout.addStretch()

        self._hlayout.addLayout(self.__info_layout)

        self.__vlayout = QtGui.QVBoxLayout(self)
        self.__vlayout.addLayout(self._hlayout)
        self.__vlayout.addStretch()

    def setObject(self, resist):
        """:type resist: options.structures.Resist"""
        for info_box in self.__info_boxes.values():
            info_box.setObject(resist)


class ResistInfoTab(AbstractResistInfoTab):
    def __init__(self, parent):
        AbstractResistInfoTab.__init__(self, parent)
        self.__comment_group = QtGui.QGroupBox("Comments", self)
        self.__comment_group_layout = QtGui.QVBoxLayout(self.__comment_group)
        self.__comment_edit = QtGui.QTextEdit(self.__comment_group)
        self.__comment_group_layout.addWidget(self.__comment_edit)
        self.__comment_layout = QtGui.QVBoxLayout()
        self.__comment_layout.addWidget(self.__comment_group)
        self._hlayout.addLayout(self.__comment_layout)


class LoadResistDialog(QtGui.QDialog):

    class ResistInfoLoad(AbstractResistInfoTab):
        def __init__(self, parent):
            AbstractResistInfoTab.__init__(self, parent)

    def __init__(self, parent, appdb):
        """
        :type parent: QtGui.QMainWindow
        :type appdb: ApplicationDatabase
        """
        QtGui.QDialog.__init__(self, parent)

        self.__appdb = appdb

        self.setWindowTitle("Load Resist")
        self.setWindowIcon(parent.windowIcon())

        self.__select_group = QtGui.QGroupBox("Select Resist", self)
        self.__select_group_layout = QtGui.QHBoxLayout(self.__select_group)
        self.__resist_list = QtGui.QListWidget(self.__select_group)
        self.__select_group_layout.addWidget(self.__resist_list)

        for resist in appdb[orm.Resist]:
            self.__resist_list.addItem(resist.name)

        self.__buttons_layout = QtGui.QHBoxLayout()
        self.__load_button = QtGui.QPushButton("Load resist", self)
        self.__load_button.setFixedWidth(config.MAXIMUM_DIALOG_BUTTON_WIDTH)
        self.__cancel_button = QtGui.QPushButton("Cancel", self)
        self.__cancel_button.setFixedWidth(config.MAXIMUM_DIALOG_BUTTON_WIDTH)

        self.__buttons_layout.addStretch()
        self.__buttons_layout.addWidget(self.__load_button)
        self.__buttons_layout.addWidget(self.__cancel_button)

        self.__resist_info = LoadResistDialog.ResistInfoLoad(self)

        connect(self.__load_button.clicked, self.accept)
        connect(self.__cancel_button.clicked, self.reject)
        connect(self.__resist_list.itemSelectionChanged, self._change_resist)

        self.__hlayout = QtGui.QVBoxLayout()
        self.__hlayout.addWidget(self.__select_group)
        self.__hlayout.addWidget(self.__resist_info)

        self.__vlayout = QtGui.QVBoxLayout(self)
        self.__vlayout.addLayout(self.__hlayout)
        self.__vlayout.addLayout(self.__buttons_layout)

    @Slot()
    def _change_resist(self):
        self.__resist_info.setObject(self.dbresist)

    @property
    def dbresist(self):
        """:rtype: orm.Resist"""
        name = str(self.__resist_list.currentItem().text())
        return self.__appdb[orm.Resist].filter(orm.Resist.name == name).one()


class ResistExposureTab(AbstractResistTab):

    class Edit(QLineEditNumeric):
        def __init__(self, *__args):
            QLineEditNumeric.__init__(self, *__args)
            self.setFixedWidth(75)
            self.setAlignment(QtCore.Qt.AlignRight)

    class PebView(AbstractResistInfoBox):

        class Graph(QGraphPlot):
            def __init__(self, parent, temp):
                """
                :type parent: QtGui.QWidget
                :type temp: options.Variable
                """
                QGraphPlot.__init__(self, parent, width=320, height=240)

                self._ax = self.add_subplot()

                self.__resist = None
                """:type: options.structures.Resist"""

                self.__temp = temp

                connect(self.__temp.signals[structures.Abstract], self.__onValueChanged)

            def draw_graph(self, peb, temp):
                """
                :param orm.PebParameters peb: Post exposure bake parameters
                :param float or None temp: Current option temperature (to set graph intervals)
                """
                self._ax.clear()

                if peb is not None and temp is not None:
                    offset = config.PEB_TEMP_GRAPH_RANGE/2.0
                    temp_range = range(int(temp-offset), int(temp+offset))
                    diff_range = peb.diffusivity(temp_range)

                    self._ax.plot(temp_range, diff_range, "r-")

                    self._ax.grid()

                    self._ax.set_xlabel("Temperature (C)")
                    self._ax.set_ylabel("PEB Diffusivity (nm2/s)")

                    self._ax.patch.set_alpha(0.0)

                    self.redraw()

            # noinspection PyPep8Naming
            @Slot()
            def __onValueChanged(self):
                self.draw_graph(self.__resist.peb, self.__temp.value)

            # noinspection PyPep8Naming
            def setObject(self, resist):
                """:type resist: options.structures.Resist"""
                if self.__resist is not None:
                    disconnect(self.__resist.peb.signals[orm.PebParameters.ln_ar], self.__onValueChanged)
                    disconnect(self.__resist.peb.signals[orm.PebParameters.ea], self.__onValueChanged)

                self.__resist = resist

                connect(self.__resist.peb.signals[orm.PebParameters.ln_ar], self.__onValueChanged)
                connect(self.__resist.peb.signals[orm.PebParameters.ea], self.__onValueChanged)

                self.__onValueChanged()

        def __init__(self, parent, temp):
            """
            :type parent: QtGui.QWidget
            :type temp: options.Variable
            """
            QtGui.QGroupBox.__init__(self, "Post Exposure Bake", parent)

            self.__peb_graph = ResistExposureTab.PebView.Graph(self, temp)

            self.__graph_layout = QtGui.QHBoxLayout()
            self.__graph_layout.addWidget(self.__peb_graph)

            self.__ln_ar = ResistExposureTab.Edit(self)
            self.__ea = ResistExposureTab.Edit(self)

            self.__values_layout = QtGui.QHBoxLayout()
            self.__values_layout.addWidget(QtGui.QLabel("Ln(Ar) (nm2/s):"))
            self.__values_layout.addWidget(self.__ln_ar)
            self.__values_layout.addStretch()
            self.__values_layout.addWidget(QtGui.QLabel("Ea (kcal/mole):"))
            self.__values_layout.addWidget(self.__ea)

            self.__layout = QtGui.QVBoxLayout(self)
            self.__layout.addLayout(self.__graph_layout)
            self.__layout.addLayout(self.__values_layout)
            # self.__layout.addStretch()

        def setObject(self, resist):
            """:type resist: options.structures.Resist"""
            self.__ln_ar.setObject(resist.peb, orm.PebParameters.ln_ar)
            self.__ea.setObject(resist.peb, orm.PebParameters.ea)
            self.__peb_graph.setObject(resist)

    class ExposureView(AbstractResistInfoBox):
        def __init__(self, parent):
            QtGui.QGroupBox.__init__(self, "Exposure Dill model", parent)

            # TODO: Fix constraints
            self.__dill_a = ResistExposureTab.Edit(self)
            self.__dill_b = ResistExposureTab.Edit(self)
            self.__dill_c = ResistExposureTab.Edit(self)

            self.__vlayout = QtGui.QFormLayout(self)
            self.__vlayout.addRow("A (1/um):", self.__dill_a)
            self.__vlayout.addRow("B (1/um):", self.__dill_b)
            self.__vlayout.addRow("C (1/um):", self.__dill_c)

        def setObject(self, resist):
            """:type resist: options.structures.Resist"""
            self.__dill_a.setObject(resist.exposure, orm.ExposureParameters.a)
            self.__dill_b.setObject(resist.exposure, orm.ExposureParameters.b)
            self.__dill_c.setObject(resist.exposure, orm.ExposureParameters.c)

    class PropertyView(AbstractResistInfoBox):
        def __init__(self, parent):
            QtGui.QGroupBox.__init__(self, "Exposure Dill model", parent)

            # TODO: Fix constraints
            self.__wavelength = ResistExposureTab.Edit(self)
            self.__refractive_n = ResistExposureTab.Edit(self)

            self.__vlayout = QtGui.QFormLayout(self)
            self.__vlayout.addRow("Wavelength (nm):", self.__wavelength)
            self.__vlayout.addRow("Unexposed refractive:", self.__refractive_n)

        def setObject(self, resist):
            """:type resist: options.structures.Resist"""
            self.__wavelength.setObject(resist.exposure, orm.ExposureParameters.wavelength)
            self.__refractive_n.setObject(resist.exposure, orm.ExposureParameters.n)

    def __init__(self, parent, peb_temp):
        """
        :param QtGui.QWidget parent: Widget parent
        :param options.Variable peb_temp: PEB temperature options field
        """
        AbstractResistTab.__init__(self, parent)

        self.__views = dict()
        """:type: dict from str to AbstractResistInfoBox"""

        self.__views["property"] = ResistExposureTab.PropertyView(self)
        self.__views["exposure"] = ResistExposureTab.ExposureView(self)
        self.__views["peb"] = ResistExposureTab.PebView(self, peb_temp)

        self.__vlayout = QtGui.QVBoxLayout()
        self.__vlayout.addWidget(self.__views["property"])
        self.__vlayout.addWidget(self.__views["exposure"])
        self.__vlayout.addStretch()

        self.__peb_layout = QtGui.QVBoxLayout()
        self.__peb_layout.addWidget(self.__views["peb"])
        self.__peb_layout.addStretch()

        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.addLayout(self.__vlayout)
        self.__layout.addLayout(self.__peb_layout)
        # self.__layout.addStretch()

    def setObject(self, resist):
        """:type resist: options.structures.Resist"""
        for view in self.__views.values():
            view.setObject(resist)


class ResistDevelopmentTab(AbstractResistTab):

    NEW_PLUGIN_RESIST_NAME = "Plugin based developer"
    NEW_PLUGIN_RESIST_TEXT = "Add new plugin development model..."

    class DevRateSheetView(QStackWidgetTab):
        def __init__(self, parent):
            """:type parent: QtGui.QWidget"""
            QStackWidgetTab.__init__(self, parent)
            self.__label = QtGui.QLabel("Parameters of the development rate sheet data can't be changed. "
                                        "Objects of those type can be import at the Database tab.")
            self.__label.setAlignment(QtCore.Qt.AlignLeft)
            self.__label.setWordWrap(True)

            self.__dev_rate_graph = DevelopmentGraph(self)

            self.__layout = QtGui.QHBoxLayout(self)
            self.__layout.addWidget(self.__label)
            self.__layout.addStretch()
            self.__layout.addWidget(self.__dev_rate_graph)

        # noinspection PyPep8Naming
        def setObject(self, resist):
            """:type resist: options.structures.Resist or None"""
            if resist is not None:
                self.__dev_rate_graph.developer = resist.developer
            else:
                self.__dev_rate_graph.developer = None

    class DevRateExprView(QStackWidgetTab):

        class ModelView(QStackWidgetTab):
            def __init__(self, parent, model, graph):
                """
                :type parent: QtGui.QWidget
                :type model: orm.DevelopmentModel
                :type graph: ResistDevelopmentTab.Graph
                """
                QStackWidgetTab.__init__(self, parent)
                self.__layout = QtGui.QVBoxLayout(self)
                self.__graph = graph
                self.__args = dict()
                for arg in model.args:
                    hlayout = QtGui.QHBoxLayout()
                    edit = QLineEditNumeric(self)
                    edit.setFixedWidth(75)
                    edit.setAlignment(QtCore.Qt.AlignRight)
                    self.__args[arg.name] = {"layout": hlayout, "edit": edit}
                    hlayout.addWidget(QtGui.QLabel(arg.name, self))
                    hlayout.addStretch()
                    hlayout.addWidget(edit)
                    self.__layout.addLayout(hlayout)
                self.__layout.addStretch()

            # noinspection PyPep8Naming
            def setObject(self, resist):
                """:type resist: options.structures.Resist or None"""
                if resist is not None:
                    # logging.info("Model view set new resist developer: %s" % resist.developer)

                    developer = resist.developer
                    """:type: orm.DeveloperExpr"""
                    for arg, p_object in zip(developer.model.args, developer.object_values):
                        self.__args[arg.name]["edit"].setObject(p_object, orm.DeveloperExprArgValue.value)
                    self.__graph.developer = developer
                else:
                    self.__graph.developer = None
                    # If resist is None clear resist links with NumericEdit views
                    for item in self.__args.values():
                        item["edit"].unsetObject()

        def __init__(self, parent, appdb):
            """
            :type parent: QtGui.QWidget
            :type appdb: ApplicationDatabase
            """
            QStackWidgetTab.__init__(self, parent)

            self.__appdb = appdb
            self.__resist = None
            """:type: options.structures.Resist"""

            self.__dev_rate_graph = DevelopmentGraph(self)

            self.__group = QtGui.QGroupBox("Parameters", self)

            self.__views = dict()
            self.__parameters_widgets = QtGui.QStackedWidget(self.__group)
            self.__dev_models = QtGui.QComboBox(self.__group)

            for model in self.__appdb[orm.DevelopmentModel]:
                self.__dev_models.addItem(model.name)
                self.__views[model.name] = ResistDevelopmentTab.DevRateExprView.ModelView(
                    self, model, self.__dev_rate_graph)
                self.__parameters_widgets.addWidget(self.__views[model.name])
            self.__dev_models.setFixedWidth(200)
            connect(self.__dev_models.currentIndexChanged, self.__onIndexChanged)

            self.__temporary_check_box = QtGui.QCheckBox("Coupled", self.__group)
            connect(self.__temporary_check_box.stateChanged, self._temporary_box_unchecked)

            self.__group_layout = QtGui.QVBoxLayout(self.__group)
            self.__group_layout.addWidget(self.__dev_models)
            self.__group_layout.addWidget(self.__temporary_check_box)
            self.__group_layout.addWidget(self.__parameters_widgets)
            self.__group_layout.addStretch()

            self.__layout = QtGui.QHBoxLayout(self)
            self.__layout.addWidget(self.__group)
            self.__layout.addStretch()
            self.__layout.addWidget(self.__dev_rate_graph)

        @Slot()
        def _temporary_box_unchecked(self):
            if not self.__temporary_check_box.isChecked():
                replay = QuestionBox(
                    self, "Do you really want to decouple:\n"
                          "Developer \"%s\" from \"%s\" resist?\n"
                          "Note: This action can't be undone, DB resist and developer will be replaced" %
                          (self.__resist.developer.name, self.__resist.name)
                )
                if replay == msgBox.Yes:
                    self.__resist.developer.temporary = False
                    self.__resist.onOptionChanged()
                    self.__appdb.replace(self.__resist)
                    logging.info("Temporary [%s]: %s" % (self.__resist.developer.id, self.__resist.developer.temporary))
                    self.__temporary_check_box.setEnabled(False)
                    self.__temporary_check_box.setText("Coupled")
                else:
                    self.__temporary_check_box.setChecked(True)

        # noinspection PyPep8Naming
        @Slot(int)
        def __onIndexChanged(self, index):
            name = str(self.__dev_models.itemText(index))
            view = self.__views[name]
            # Clear previous links with views
            self.__parameters_widgets.currentWidget().setObject(None)
            self.__parameters_widgets.setCurrentWidget(view)
            self.__temporary_check_box.blockSignals(True)
            self.__temporary_check_box.setChecked(self.__resist.developer.temporary)
            self.__temporary_check_box.setEnabled(self.__resist.developer.temporary)
            self.__temporary_check_box.blockSignals(False)
            text = "Coupled with %s" % self.__resist.name if self.__temporary_check_box.isChecked() else "Coupled"
            self.__temporary_check_box.setText(text)
            db_model = self.__appdb[orm.DevelopmentModel].filter(orm.DevelopmentModel.name == name).one()
            if self.__resist.developer.model is not db_model:
                self.__resist.developer.change_model(db_model)
                self.__resist.onOptionChanged()
            view.setObject(self.__resist)

        # noinspection PyPep8Naming
        def setObject(self, resist):
            """:type resist: options.structures.Resist"""
            self.__resist = resist
            index = self.__dev_models.findText(resist.developer.model.name)
            self.__dev_models.blockSignals(True)
            self.__dev_models.setCurrentIndex(-1)
            self.__dev_models.blockSignals(False)
            self.__dev_models.setCurrentIndex(index)

    class DevRateNone(QStackWidgetTab):

        def __init__(self, parent):
            """:type parent: QtGui.QWidget"""
            QStackWidgetTab.__init__(self, parent)
            self.__label = QtGui.QLabel("Development rate was not set to this resist. "
                                        "To be able to run simulation resist must be set.")
            self.__label.setAlignment(QtCore.Qt.AlignCenter)
            self.__label.setWordWrap(True)

            self.__layout = QtGui.QVBoxLayout(self)
            self.__layout.addWidget(self.__label)

    def __init__(self, parent, appdb):
        """
        Initializer of ResistDevelopmentTab class

        :type parent: QtGui.QWidget
        :type appdb: ApplicationDatabase
        """
        AbstractResistTab.__init__(self, parent)

        self.__appdb = appdb
        self.__resist = None
        """:type: options.structures.Resist"""

        # -- Header --

        self.__dev_name_combobox = QtGui.QComboBox(self)
        self.__dev_name_combobox.setFixedWidth(300)
        connect(self.__dev_name_combobox.currentIndexChanged, self.__onIndexChanged)

        self.__save_button = QtGui.QPushButton("Save Developer")
        self.__save_button.setFixedWidth(120)
        self.__save_button.setEnabled(False)
        connect(self.__save_button.clicked, self._save_developer)

        self.__save_button_as = QtGui.QPushButton("Save Developer As...")
        self.__save_button_as.setFixedWidth(120)
        self.__save_button_as.setEnabled(False)
        connect(self.__save_button_as.clicked, self._save_developer_as)

        self.__header_layout = QtGui.QHBoxLayout()
        self.__header_layout.addWidget(self.__dev_name_combobox)
        self.__header_layout.addStretch()
        self.__header_layout.addWidget(self.__save_button)
        self.__header_layout.addWidget(self.__save_button_as)

        # -- Body --

        self.__parameters_widgets = QtGui.QStackedWidget(self)
        self.__views = {
            orm.DeveloperSheet: ResistDevelopmentTab.DevRateSheetView(self),
            orm.DeveloperExpr: ResistDevelopmentTab.DevRateExprView(self, self.__appdb),
            None: ResistDevelopmentTab.DevRateNone(self)
        }
        for widget in self.__views.values():
            self.__parameters_widgets.addWidget(widget)

        # -- Tab --

        self.__vlayout = QtGui.QVBoxLayout(self)
        self.__vlayout.addLayout(self.__header_layout)
        self.__vlayout.addWidget(self.__parameters_widgets)
        self.__vlayout.addStretch()

    # noinspection PyPep8Naming
    @Slot(int)
    def __onIndexChanged(self, index):
        name = str(self.__dev_name_combobox.itemText(index))
        if not name:
            return

        if name == self.NEW_PLUGIN_RESIST_TEXT:
            dev_model = self.__appdb[orm.DevelopmentModel].first()
            if dev_model is None:
                ErrorBox(self, "Can't create new plugin resist development model because no suitable plugins found")
                return
            developer = orm.DeveloperExpr(self.NEW_PLUGIN_RESIST_NAME, dev_model)
        elif self.__resist.developer is not None and self.__resist.developer.name == name:
            developer = self.__resist.developer
        else:
            db_developer = self.__appdb[orm.DeveloperInterface].filter(orm.Generic.name == name).one()
            developer = db_developer.clone() if isinstance(db_developer, orm.DeveloperExpr) else db_developer

        view = self.__views[type(developer)]
        self.__parameters_widgets.setCurrentWidget(view)
        self.__resist.developer = developer
        view.setObject(self.__resist)

        self.__save_button.setEnabled(isinstance(self.__resist.developer, orm.DeveloperExpr))
        self.__save_button_as.setEnabled(isinstance(self.__resist.developer, orm.DeveloperExpr))

    def _save_developer_payload(self, name):
        """:type name: str"""
        try:
            developer = self.__appdb[orm.DeveloperInterface].filter(orm.DeveloperInterface.name == name).one()
            """:type: orm.DeveloperInterface"""
        except orm.NoResultFound:
            self.__resist.developer.name = name
            self.__appdb.add(self.__resist.developer.clone())
        else:
            replay = QuestionBox(self, "%s \"%s\" already existed, replace it?" %
                                       (developer.identifier, developer.name))
            if replay == msgBox.Yes:
                developer.assign(self.__resist.developer)
                self.__appdb.commit()

    @Slot()
    def _save_developer(self):
        name = str(self.__dev_name_combobox.currentText())
        self._save_developer_payload(name)

    @Slot()
    def _save_developer_as(self):
        name, is_accept = QtGui.QInputDialog.getText(
            self.parent(), "Save developer as...",
            "Specify name of the new developer:",
            QtGui.QLineEdit.Normal,
            str(self.__dev_name_combobox.currentText()))
        if is_accept:
            self._save_developer_payload(str(name))
            self.update_view()

    def update_view(self):
        # Block signals otherwise it automatically change resist
        self.__dev_name_combobox.blockSignals(True)
        self.__dev_name_combobox.clear()

        developers = {self.__resist.developer.name} if self.__resist.developer is not None else set()
        for item in self.__appdb[orm.DeveloperInterface]:
            if isinstance(item, orm.DeveloperSheet) or (isinstance(item, orm.DeveloperExpr) and not item.temporary):
                developers.add(item.name)

        self.__dev_name_combobox.addItems([self.NEW_PLUGIN_RESIST_TEXT] + list(developers))
        self.__dev_name_combobox.setCurrentIndex(-1)

        self.__dev_name_combobox.blockSignals(False)

        if self.__resist.developer is not None:
            index = self.__dev_name_combobox.findText(self.__resist.developer.name)
            self.__dev_name_combobox.setCurrentIndex(index)
        else:
            self.__parameters_widgets.setCurrentWidget(self.__views[None])

    def setObject(self, resist):
        """:type resist: options.structures.Resist"""
        self.__resist = resist
        self.update_view()


class ResistView(QStackWidgetTab):

    def _create_header(self):
        self.__button_load = QtGui.QPushButton("Load Resist")
        self.__button_load.adjustSize()
        self.__button_load.setFixedWidth(self.__button_load.width()+20)
        connect(self.__button_load.clicked, self._load_resist)

        self.__button_save = QtGui.QPushButton("Save Resist to Database")
        self.__button_save.adjustSize()
        self.__button_save.setFixedWidth(self.__button_save.width()+20)
        connect(self.__button_save.clicked, self._save_resist)

        self.__label_name = QtGui.QLabel("Name:")

        self.__edit_name = QtGui.QLineEdit()
        self.__edit_name.setMinimumWidth(100)

        self.__header_layout = QtGui.QHBoxLayout()
        self.__header_layout.addWidget(self.__button_load)
        self.__header_layout.addWidget(self.__button_save)
        self.__header_layout.addSpacing(20)
        self.__header_layout.addWidget(self.__label_name)
        self.__header_layout.addWidget(self.__edit_name)

    @Slot()
    def _load_resist(self):
        load_resist_dlg = LoadResistDialog(self.parent(), self.__appdb)
        if load_resist_dlg.exec_():
            # Make a clone of the resist to avoid undesired changes of it's properties in the database
            db_resist = load_resist_dlg.dbresist.clone()
            logging.info("Load resist: %s" % db_resist.name)
            thickness = self.__wafer_process.resist.thickness
            self.__wafer_process.resist = structures.Resist(db_resist, thickness)
            self.setObject(self.__wafer_process.resist)

    @Slot()
    def _save_resist(self):

        def get_db_developer(_resist):
            """
            Get object from the database (real database id required)

            :type _resist: options.structures.Resist
            :rtype: orm.DeveloperInterface
            """
            try:
                db_developer = self.__appdb[orm.DeveloperInterface].\
                    filter(orm.DeveloperInterface.name == _resist.developer.name).one()
            except orm.NoResultFound:
                db_developer = None

            return db_developer

        name = str(self.__edit_name.text())
        try:
            db_resist = self.__appdb[orm.Resist].filter(orm.Resist.name == name).one()
            """:type: orm.Resist"""
        except orm.NoResultFound:
            self.__wafer_process.resist.name = name
            self.__wafer_process.resist.developer = get_db_developer(self.__wafer_process.resist)
            self.__appdb.add(self.__wafer_process.resist.db.clone())
        else:
            replay = QuestionBox(
                self, "%s \"%s\" already existed, replace it?" %
                (self.__wafer_process.resist.identifier, self.__wafer_process.resist.name))
            if replay == msgBox.Yes:
                db_resist.assign(
                    self.__wafer_process.resist.db,
                    developer=get_db_developer(self.__wafer_process.resist))
                self.__appdb.commit()

    def _create_body(self):
        self.__tab_widget = QtGui.QTabWidget(self)

        self.__tab_widget.addTab(ResistInfoTab(self.__tab_widget), "Information")
        self.__tab_widget.addTab(ResistExposureTab(self.__tab_widget, self.__peb_temp), "Exposure/PEB")
        self.__tab_widget.addTab(ResistDevelopmentTab(self.__tab_widget, self.__appdb), "Development")

        self.__body_layout = QtGui.QHBoxLayout()
        self.__body_layout.addWidget(self.__tab_widget)
        self.__body_layout.addStretch()

        connect(self.__tab_widget.currentChanged, self.__onTabChanged)

    def _enumerate_tabs(self):
        for k in xrange(self.__tab_widget.count()):
            yield self.__tab_widget.widget(k)

    # @property
    # def resist(self):
    #     return self.__resist

    # @resist.setter
    # def resist(self, value):
    #     """:type value: options.structures.Resist"""
    #     self.__resist = value
    #     self.__edit_name.setText(value.name)
    #     for tab in self._enumerate_tabs():
    #         tab.resist = value

    # noinspection PyPep8Naming
    def setObject(self, resist):
        """:type resist: options.structures.Resist"""
        self.__resist = resist
        self.__edit_name.setText(resist.name)
        for tab in self._enumerate_tabs():
            tab.setObject(resist)

    # noinspection PyPep8Naming
    @Slot(int)
    def __onTabChanged(self, *args):
        for tab in self._enumerate_tabs():
            tab.onSetActive()

    def __init__(self, parent, wafer_process, peb_temp, appdb):
        """
        :type parent: QtGui.QWidget
        :param WaferProcess wafer_process: Wafer stack process options
        :param Variable peb_temp: PEB temperature options field
        :type appdb: ApplicationDatabase
        """
        QStackWidgetTab.__init__(self, parent)
        self.setObjectName("ResistView")

        self.__wafer_process = wafer_process
        self.__peb_temp = peb_temp
        self.__appdb = appdb

        self.__resist = None

        # --- Header members ---
        self.__button_load = None
        """:type: QtGui.QPushButton"""
        self.__button_save = None
        """:type: QtGui.QPushButton"""
        self.__label_name = None
        """:type: QtGui.QLabel"""
        self.__edit_name = None
        """:type: QtGui.QLineEdit"""
        self.__header_layout = None
        """:type: QtGui.QHBoxLayout"""

        # --- Body members ---

        self.__tab_widget = None
        """:type: QtGui.QTabWidget"""
        self.__body_layout = None
        """:type: QtGui.QHBoxLayout"""

        # --- Setup ---

        self._create_header()
        self._create_body()

        self.__layout = QtGui.QVBoxLayout()
        self.__layout.addLayout(self.__header_layout)
        self.__layout.addSpacing(20)
        self.__layout.addLayout(self.__body_layout)
        self.__layout.addStretch()

        self.__hlayout = QtGui.QHBoxLayout(self)
        self.__hlayout.addLayout(self.__layout)
        self.__hlayout.addStretch()

        self.setObject(self.__wafer_process.resist)

    def reset(self):
        self.setObject(self.__wafer_process.resist)