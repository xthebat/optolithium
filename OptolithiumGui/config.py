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
import psutil
import json
import logging as module_logging
import sys
import helpers
import ctypes


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


darwin = "darwin"
nt = "win32"
posix = "linux2"


_shared_ext = {
    darwin: ".dylib",
    nt: ".dll",
    posix: ".so"
}


shared_ext = _shared_ext[sys.platform]


_plot_bottom_adjust = {
    darwin: 0.15,
    nt: 0.15,
    posix: 0.15
}

plot_bottom_adjust = _plot_bottom_adjust[sys.platform]


_application_styles = {
    darwin: u"Plastique",
    nt: u"Windows",
    posix: u"Windows"
}


application_style = _application_styles[sys.platform]

RESIST_FILL_COLOR = "purple"
RESIST_LINES_COLOR = "black"
RESIST_CONTOUR_COLOR = "grey"
COMMON_LINES_COLOR = "crimson"

KILOBYTE = 1024
MEGABYTE = KILOBYTE * KILOBYTE
GIGABYTE = KILOBYTE * MEGABYTE

STATUS_BAR_MESSAGE_DURATION = 2000

MAXIMUM_DIALOG_BUTTON_WIDTH = 100
DEFAULT_EDIT_WIDTH = 60

APPLICATION_NAME = "Optolithium"
APPLICATION_WEBSITE = "https://bitbucket.org/gladkikhalexei/lithography"

LOG_DATABASE_QUERIES = False
RESOURCES = ["icons"]

DATETIME_FORMAT = "%d.%m.%Y %H:%M:%S"

DEFAULT_DECIMAL_COUNT = 3

DEFAULT_LAYER_THICKNESS = 100.0
DEFAULT_LAYER_REAL_INDEX = 1.0
DEFAULT_LAYER_IMAG_INDEX = 0.0

PEB_TEMP_GRAPH_RANGE = 20
DEV_RATE_PAC_STEP = 0.01

DEFAULT_RESIST_NAME = "ResistDefault"
DEFAULT_SUBSTRATE_MATERIAL_NAME = "SubstrateMaterial"
DEFAULT_DEV_RATE_NAME = "DevRateDefault"
DEFAULT_SOURCE_SHAPE_NAME = "Coherent"
DEFAULT_AIR_VACUUM_NAME = "Air-Vacuum"

DEFAULT_OPTIONS_NAME = "Untitled.opl"
OPTIONS_EXTENSION = "Optolithium options (*.opl)"

KLAYOUT_PATH = "klayout"

if sys.platform == nt:
    buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.kernel32.GetEnvironmentVariableW(u"USERPROFILE", buf, 1024)
    HOME_PATH = buf.value
else:
    HOME_PATH = os.path.expanduser("~")

APPLICATION_DIRECTORY = "." + APPLICATION_NAME
CONFIG_NAME = "config.json"

CONFIG_PATH = os.path.join(HOME_PATH, APPLICATION_DIRECTORY, CONFIG_NAME)

DEFAULT_DATABASE_NAME = "OptolithiumDatabase.db"
DEFAULT_MAP_FILE_NAME = "map.json"
DEFAULT_MEMORY_USAGE_UPDATE = 1000  # ms
DEFAULT_GRAPH_DPI = 60
DEFAULT_MAX_GDSII_FILE_SIZE = 5 * MEGABYTE

SOURCE_SHAPE_STEP_MAP = [0.007, 0.010, 0.020, 0.032, 0.040, 0.050, 0.059, 0.067, 0.083, 0.125, 0.250]


class LayerMapConfig(object):

    BOUNDARY_LAYER_VALUE = "boundary"
    BACKGROUND_LAYER_KEY = "background"
    TRANSMITTANCE_MAP_KEY = "transmittance"
    PHASE_MAP_KEY = "phase"

    __instance__ = None

    class ParseError(Exception):
        pass

    @staticmethod
    def _default_data():
        return {
            "8.0": {"transmittance": 0.0, "phase": 0.0},
            "63.0": "boundary",
            "background": {"transmittance": 1.0, "phase": 0.0}
        }

    def _verify(self):
        if LayerMapConfig.BACKGROUND_LAYER_KEY not in self.__data:
            raise LayerMapConfig.ParseError("Background parameters not found")

        if LayerMapConfig.BOUNDARY_LAYER_VALUE not in self.__data.values():
            raise LayerMapConfig.ParseError("Boundary layer not found")

        for key, value in self.__data.items():
            if key != LayerMapConfig.BACKGROUND_LAYER_KEY:

                num_type = key.split(".")
                if len(num_type) != 2:
                    raise LayerMapConfig.ParseError("Wrong layer number: %s" % key)

                number, datatype = num_type

                try:
                    int(number)
                    int(datatype)
                except ValueError:
                    LayerMapConfig.ParseError("Wrong layer number or datatype: %s" % key)

                if value != LayerMapConfig.BOUNDARY_LAYER_VALUE:
                    try:
                        float(value[LayerMapConfig.TRANSMITTANCE_MAP_KEY])
                    except ValueError or KeyError:
                        raise LayerMapConfig.ParseError("Wrong map record %s: %s" % (key, value))

    def save(self, path):
        map_dir = os.path.dirname(os.path.abspath(path))

        if not os.path.exists(map_dir):
            os.makedirs(map_dir)

        with open(path, "w") as map_file:
            map_file.write(json.dumps(self.__data, indent=4))

    def __init__(self, path):

        if LayerMapConfig.__instance__ is not None:
            raise RuntimeError("Layers map configuration has been already initialized!")

        self.__data = dict()

        try:
            with open(path) as map_file:
                self.__data.update(json.loads(map_file.read()))
        except IOError as error:
            if error.errno == 2:
                logging.error("GDS map file was not found using default")
                self.__data = LayerMapConfig._default_data()
                self.save(path)
            else:
                raise
        else:
            self._verify()

        self.__path = path

        LayerMapConfig.__instance__ = self

    @property
    def path(self):
        return self.__path

    def boundary_layer(self):
        """:rtype: (int, int)"""
        return [map(int, k.split(".")) for k, v in self.__data.iteritems()
                if v == LayerMapConfig.BOUNDARY_LAYER_VALUE][0]

    def __getitem__(self, item):
        return self.__data[item]

    def get_layer(self, transmittance, phase):
        """:rtype: (int, int)"""
        layers = [k for k, v in self.__data.iteritems()
                  if isinstance(v, dict) and
                  v[LayerMapConfig.TRANSMITTANCE_MAP_KEY] == transmittance and
                  v[LayerMapConfig.PHASE_MAP_KEY] == phase]
        if not layers:
            raise KeyError
        if layers[0] == LayerMapConfig.BACKGROUND_LAYER_KEY:
            raise ValueError
        return map(int, layers[0].split("."))


GdsLayerMapping = None
""":type: LayerMapConfig"""


# noinspection PyPep8Naming
def openLayerMapConfig(path):
    global GdsLayerMapping
    GdsLayerMapping = LayerMapConfig(path)


class _Configuration(object):

    SYSTEM_PLUGINS_PATH = "plugins"
    PLUGIN_PATHS_SEPARATOR = ";"

    __ERROR_CONFIG_NOT_INIT_MSG__ = "Configuration was not initialized"

    __instance__ = None

    def __init__(self, **kwargs):
        """
        :param str map_path: Path to gds map file
        :param str db_path: Application Database path
        :param str plugin_paths: User plugin directory
        :param str __memory_update:
        :param int dpi: Dots-per-Inch for all graphs
        :param int gds_size: Maximum Gds size in megabytes
        :param int thread_count: Count of the threads
        """
        if _Configuration.__instance__ is not None:
            raise RuntimeError("Global application configuration settings has been already initialized!")

        self.__data = dict()

        try:
            self.__data["map_path"] = kwargs["map_path"]
        except KeyError:
            self.__data["map_path"] = os.path.join(HOME_PATH, APPLICATION_DIRECTORY, DEFAULT_MAP_FILE_NAME)
            logging.warning("GDSII map file path was not set using default path: %s" % self.layer_map_path)

        try:
            self.__data["db_path"] = kwargs["db_path"]
        except KeyError:
            self.__data["db_path"] = os.path.join(HOME_PATH, APPLICATION_DIRECTORY, DEFAULT_DATABASE_NAME)
            logging.warning("Database file path was not set using default path: %s" % self.db_path)

        try:
            if kwargs["plugin_paths"]:
                self.__data["plugin_paths"] = \
                    kwargs["plugin_paths"].split(_Configuration.PLUGIN_PATHS_SEPARATOR) + \
                    [_Configuration.SYSTEM_PLUGINS_PATH]
            else:
                self.__data["plugin_paths"] = [_Configuration.SYSTEM_PLUGINS_PATH]
        except KeyError:
            self.__data["plugin_paths"] = [_Configuration.SYSTEM_PLUGINS_PATH]
            logging.warning("Additional plugin directories was not set using system path only: %s" % self.plugin_paths)

        try:
            self.__data["memory_update"] = int(kwargs["memory_update"])
        except KeyError or ValueError:
            self.__data["memory_update"] = DEFAULT_MEMORY_USAGE_UPDATE
            logging.warning("Memory usage update interval was not set "
                            "to properly value using default: %s" % self.memory_update_interval)

        try:
            self.__data["dpi"] = int(kwargs["dpi"])
        except KeyError or ValueError:
            self.__data["dpi"] = DEFAULT_GRAPH_DPI
            logging.warning("Graphs DPI was not set to properly value using default: %s" % self.dpi)

        try:
            self.__data["gds_size"] = int(kwargs["gds_size"])
        except KeyError or ValueError:
            self.__data["gds_size"] = DEFAULT_MAX_GDSII_FILE_SIZE
            logging.warning("Max GDSII file size was not set "
                            "to properly value using default: %s" % self.maximum_gds_size)

        try:
            self.__data["thread_count"] = int(kwargs["thread_count"])
        except KeyError or ValueError:
            self.__data["thread_count"] = psutil.cpu_count()
            logging.warning("Max threads count was not set "
                            "to properly value using CPU cores count: %s" % self.thread_count)

        self.path = None

        _Configuration.__instance__ = self

    def serialize(self):
        result = self.__data
        filtered = filter(lambda v: v != _Configuration.SYSTEM_PLUGINS_PATH, self.__data["plugin_paths"])
        logging.info("%s" % filtered)
        result["plugin_paths"] = _Configuration.PLUGIN_PATHS_SEPARATOR.join(filtered)
        return result

    def _get_data(self, key):
        try:
            return self.__data[key]
        except KeyError:
            raise RuntimeError(_Configuration.__ERROR_CONFIG_NOT_INIT_MSG__)

    @property
    def layer_map_path(self):
        return self._get_data("map_path")

    @layer_map_path.setter
    def layer_map_path(self, value):
        self.__data["map_path"] = value

    @property
    def db_path(self):
        return self._get_data("db_path")

    @db_path.setter
    def db_path(self, value):
        self.__data["db_path"] = value

    @property
    def plugin_paths(self):
        return self._get_data("plugin_paths")

    @plugin_paths.setter
    def plugin_paths(self, value):
        self.__data["plugin_paths"] = value.split(_Configuration.PLUGIN_PATHS_SEPARATOR)

    @property
    def memory_update_interval(self):
        return self._get_data("memory_update")

    @memory_update_interval.setter
    def memory_update_interval(self, value):
        interval = int(value)
        if interval < 100:
            interval = 100
        self.__data["memory_update"] = interval

    @property
    def dpi(self):
        return self._get_data("dpi")

    @dpi.setter
    def dpi(self, value):
        dpi = int(value)
        if dpi < 40:
            dpi = 40
        elif dpi > 100:
            dpi = 100
        self.__data["dpi"] = dpi

    @property
    def maximum_gds_size(self):
        return self._get_data("gds_size")

    @maximum_gds_size.setter
    def maximum_gds_size(self, value):
        size = int(value)
        if size < MEGABYTE:
            size = MEGABYTE
        self.__data["gds_size"] = size

    @property
    def thread_count(self):
        return self._get_data("thread_count")

    @thread_count.setter
    def thread_count(self, value):
        thread_count = int(value)
        if thread_count > psutil.cpu_count():
            thread_count = psutil.cpu_count()
        elif thread_count < 1:
            thread_count = 1
        self.__data["thread_count"] = thread_count

    @classmethod
    def open(cls, path=CONFIG_PATH):

        save_required = False

        try:
            with open(path, "r") as config_file:
                kwargs = json.loads(config_file.read())
        except IOError as error:
            if error.errno == 2:
                logging.error("Can't open configuration file using default values")
                save_required = True
                kwargs = {}
            else:
                raise
        except ValueError:
            logging.error("Can't parse configuration file using default values")
            save_required = True
            kwargs = {}

        config = cls(**kwargs)
        config.path = path

        if save_required:
            config.save(path)

        return config

    def save(self, path=CONFIG_PATH):
        config_dir = os.path.dirname(os.path.abspath(path))

        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        with open(path, "w") as config_file:
            config_file.write(json.dumps(self.serialize(), indent=4))


Configuration = _Configuration.open()
""":type: _Configuration"""
