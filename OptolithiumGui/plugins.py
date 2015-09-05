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
import ctypes
import sys

from database import orm

import config
import helpers
import pcpi


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.DEBUG)
helpers.logStreamEnable(logging)


class System(object):

    def _darwin_free_lib(self, handle):
        self._dylib.dlclose(handle)

    def _linux_free_lib(self, handle):
        self._libdl.dlclose(handle)

    def _windows_free_lib(self, handle):
        self._windll.kernel32.FreeLibrary(handle)

    def __init__(self):
        if sys.platform.startswith(config.darwin):
            self._dylib = ctypes.cdll.LoadLibrary("libdl.dylib")
        elif os.name == config.posix:
            self._libdl = ctypes.cdll.LoadLibrary("libdl.so")
        elif os.name == config.nt:
            self._windll = ctypes.windll

        self._free_library = {
            config.darwin: self._darwin_free_lib,
            config.nt: self._windows_free_lib,
            config.posix: self._linux_free_lib
        }

    # noinspection PyProtectedMember
    def free_library(self, library):
        handle = library._handle
        # noinspection PyCallingNonCallable
        return self._free_library[os.name](handle)

    # noinspection PyMethodMayBeStatic,PyPep8Naming
    @property
    def SharedLibraryLoadError(self):
        # noinspection PyUnresolvedReferences
        return WindowsError


system = System()


class Plugin(object):

    class LoadError(Exception):
        def __init__(self, *args, **kwargs):
            super(Plugin.LoadError, self).__init__(*args, **kwargs)

    def __init__(self, library_path, library, plugin_desc):
        """
        :param str library_path: Path to the library
        :param library: Module handle of the plugin library
        :param plugin_descriptor_t plugin_desc: C plugin descriptor
        """
        self._library_path = library_path
        self._library = library
        self._plugin_desc = plugin_desc

        self.record = None
        """:type: orm.Generic or None"""

    @property
    def type(self):
        """:rtype: int"""
        return self._plugin_desc.plugin_type

    @property
    def entry(self):
        """:rtype: CPluginInterface"""
        return self._plugin_desc.plugin_entry

    @property
    def path(self):
        """:rtype: str"""
        return self._library_path

    @classmethod
    def load(cls, library_path):
        """
        :param str library_path: Path to the file of plugin shared library
        """
        try:
            library = ctypes.cdll.LoadLibrary(library_path)
        except system.SharedLibraryLoadError:
            raise Plugin.LoadError("File \"%s\" is not valid shared object and can't be loaded" % library_path)

        try:
            plugin_desc = pcpi.plugin_descriptor_t.in_dll(library, pcpi.ENTRY_POINT)
        except ValueError:
            system.free_library(library)
            raise Plugin.LoadError("Plugin entry point not found: \"%s\"" % library_path)

        if plugin_desc.plugin_type not in pcpi.plugin_types:
            plugin_type = plugin_desc.plugin_type
            system.free_library(library)
            raise Plugin.LoadError("Unsupported plugin type \"%s\" of \"%s\"" % (plugin_type, library_path))

        return cls(library_path, library, plugin_desc)

    def unload(self):
        system.free_library(self._library)
        self._library_path = None
        self._library = None
        self._plugin_desc = None


class Container(object):

    @staticmethod
    def _clean_plugins_dict():
        """:rtype: dict[int, list[Plugin]]"""
        return {possible_type: list() for possible_type in pcpi.plugin_types}

    def __init__(self):
        self._plugins_directory = self._clean_plugins_dict()

    def load_path(self, *plugins_path):
        """
        Enumerate plugin file in directories. Structure of the one directory is follow:
        + plugins:
          + masks:
            - line.dll
            - space.dll
          + dev_models:
            - mack.dll
            - enhanced.dll
            - notch.dll
          + source_shapes:
            - conventional.dll
            - annular.dll
            - coherent.dll

        :param tuple[str] plugins_path: List of of root directories for plugins
        """
        if not plugins_path:
            plugins_path = [config.Configuration.SYSTEM_PLUGINS_PATH]

        for path in plugins_path:
            if not os.path.isdir(path):
                logging.warning("Plugin path '%s' not existed or not is directory omitted" % path)
                continue

            for dir_name in os.listdir(path):
                dir_path = os.path.join(path, dir_name)

                if not os.path.isdir(dir_path):
                    continue

                for filename in os.listdir(dir_path):
                    _, ext = os.path.splitext(filename)
                    if ext != config.shared_ext:
                        continue

                    filepath = os.path.join(dir_path, filename)

                    if self.is_loaded(filepath):
                        logging.info("Plugin already loaded \"%s\"" % filepath)
                        continue

                    try:
                        plugin = Plugin.load(filepath)
                    except Plugin.LoadError as error:
                        logging.warning(error.message)
                    else:
                        self._plugins_directory[plugin.type].append(plugin)
                        logging.info("Plugin library load: \"%s\"" % filepath)

    def __iter__(self):
        """:rtype: __generator[Plugin]"""
        for plugins in self._plugins_directory.values():
            for plugin in plugins:
                yield plugin

    def next(self):
        """:rtype: Plugin"""
        return next(self)

    def is_loaded(self, filepath):
        """
        :param str filepath: Plugin file path
        :rtype: bool
        """
        for plugin in self:
            if plugin.path == filepath:
                return True
        return False

    @classmethod
    def load(cls, *plugins_path):
        container = cls()
        container.load_path(*plugins_path)
        return container

    def unload(self):
        for plugin in self:
            plugin.unload()
            del plugin
        self._plugins_directory = self._clean_plugins_dict()


class Inspector(object):

    Load = 0
    Verify = 1

    class CommonError(Exception):
        def __init__(self, *args, **kwargs):
            super(Inspector.CommonError, self).__init__(*args, **kwargs)

    class VerifyError(CommonError):
        def __init__(self, *args, **kwargs):
            super(Inspector.VerifyError, self).__init__(*args, **kwargs)
            self.message = "Verify of %s" % self.message

    class DevelopmentModelVerifyError(VerifyError):
        def __init__(self, *args, **kwargs):
            super(Inspector.DevelopmentModelVerifyError, self).__init__(*args, **kwargs)
            self.message = "Development model: %s" % self.message

    class PluginMaskVerifyError(VerifyError):
        def __init__(self, *args, **kwargs):
            super(Inspector.PluginMaskVerifyError, self).__init__(*args, **kwargs)
            self.message = "Plugin mask: %s" % self.message

    class PluginSourceShapeVerifyError(VerifyError):
        def __init__(self, *args, **kwargs):
            super(Inspector.PluginSourceShapeVerifyError, self).__init__(*args, **kwargs)
            self.message = "Source shape: %s" % self.message

    class PluginPupilFilterVerifyError(VerifyError):
        def __init__(self, *args, **kwargs):
            super(Inspector.PluginPupilFilterVerifyError, self).__init__(*args, **kwargs)
            self.message = "Pupil filter: %s" % self.message

    @staticmethod
    def _load_development_model(plugin):
        """:type plugin: Plugin"""
        entry = plugin.entry
        """:type: dev_model_t"""
        args = [orm.DevelopmentModelArg(entry.args[k].name, k, entry.args[k].defv, entry.args[k].min, entry.args[k].max)
                for k in xrange(entry.args_count)]
        return orm.DevelopmentModel(name=entry.name, args=args, desc=entry.desc, prolith_id=entry.prolith_id)

    @staticmethod
    def _verify_development_model(plugin, record):
        """
        :param Plugin plugin: Descriptor of the loaded plugin
        :param orm.DevelopmentModel record: Database record of this plugin
        """
        entry = plugin.entry
        """:type: pcpi.dev_model_t"""

        if record.name != entry.name:
            raise Inspector.DevelopmentModelVerifyError("Names not equals: %s != %s" % (record.name, entry.name))

        if len(record.args) != entry.args_count:
            raise Inspector.DevelopmentModelVerifyError(
                "Plugin expression arguments not equal to saved: %d != %d" %
                (len(record.args), entry.args_count))

        for rarg in record.args:
            earg = entry.args[rarg.ord]
            if rarg.name != earg.name:
                raise Inspector.DevelopmentModelVerifyError(
                    "Argument names not equals: %s != %s" % (rarg.name, earg.name))
            if rarg.max != earg.max:
                raise Inspector.DevelopmentModelVerifyError(
                    "Maximum values not equals: %s != %s" % (rarg.max, earg.max))
            if rarg.min != earg.min:
                raise Inspector.DevelopmentModelVerifyError(
                    "Minimum values not equals: %s != %s" % (rarg.min, earg.min))

    @staticmethod
    def _load_standard_plugin(plugin, plg_type, prm_type):
        entry = plugin.entry
        prms = [prm_type(
            entry.parameters[k].name, k, entry.parameters[k].defv,
            entry.parameters[k].min, entry.parameters[k].max) for k in xrange(entry.parameters_count)]
        return plg_type(name=entry.name, prms=prms, desc=entry.desc)

    @staticmethod
    def _verify_standard_plugin(plugin, record, err_type):
        """
        :param Plugin plugin: Descriptor of the loaded plugin
        :param record: Database record of this plugin
        :param type err_type: Error type to raise if necessary
        """
        entry = plugin.entry
        """:type: pcpi.mask_t"""

        if record.name != entry.name:
            raise err_type("Names not equals: %s != %s" % (record.name, entry.name))

        if len(record.prms) != entry.parameters_count:
            raise err_type("Plugin parameters not equal to saved: %d != %d" % (len(record.prms), entry.parameters_count))

        for rprm in record.prms:
            eprm = entry.parameters[rprm.ord]
            if rprm.name != eprm.name:
                raise err_type("Parameters names not equals: %s != %s" % (rprm.name, eprm.name))
            if rprm.max != eprm.max:
                raise err_type("Maximum values not equals: %s != %s" % (rprm.max, eprm.max))
            if rprm.min != eprm.min:
                raise err_type("Minimum values not equals: %s != %s" % (rprm.min, eprm.min))

    @staticmethod
    def _load_mask_plugin(plugin):
        """:type plugin: Plugin"""
        entry = plugin.entry
        prms = [orm.AbstractPluginMaskPrm(
            entry.parameters[k].name, k, entry.parameters[k].defv,
            entry.parameters[k].min, entry.parameters[k].max) for k in xrange(entry.parameters_count)]
        return orm.AbstractPluginMask(name=entry.name, prms=prms, desc=entry.desc, dims=entry.dimensions)

    @staticmethod
    def _verify_mask_plugin(plugin, record):
        """
        :param Plugin plugin: Descriptor of the loaded plugin
        :param orm.AbstractPluginMask record: Database record of this plugin
        """
        Inspector._verify_standard_plugin(plugin, record, Inspector.PluginMaskVerifyError)

    @staticmethod
    def _load_source_shape_plugin(plugin):
        """:type plugin: Plugin"""
        return Inspector._load_standard_plugin(plugin, orm.AbstractPluginSourceShape, orm.AbstractPluginSourceShapePrm)

    @staticmethod
    def _verify_source_shape_plugin(plugin, record):
        """
        :param Plugin plugin: Descriptor of the loaded plugin
        :param orm.AbstractPluginSourceShape record: Database record of this plugin
        """
        Inspector._verify_standard_plugin(plugin, record, Inspector.PluginSourceShapeVerifyError)

    @staticmethod
    def _load_pupil_filter_plugin(plugin):
        """:type plugin: Plugin"""
        return Inspector._load_standard_plugin(plugin, orm.AbstractPluginPupilFilter, orm.AbstractPluginPupilFilterPrm)

    @staticmethod
    def _verify_pupil_filter_plugin(plugin, record):
        """
        :param Plugin plugin: Descriptor of the loaded plugin
        :param orm.AbstractPluginPupilFilter record: Database record of this plugin
        """
        Inspector._verify_standard_plugin(plugin, record, Inspector.PluginPupilFilterVerifyError)

    def __init__(self, database):
        """
        :type database: database.ApplicationDatabase
        """
        self._plugin_map = {
            orm.AbstractPluginMask.cpi.plugin_id: (self._load_mask_plugin, self._verify_mask_plugin),
            orm.AbstractPluginSourceShape.cpi.plugin_id:
                (self._load_source_shape_plugin, self._verify_source_shape_plugin),
            orm.AbstractPluginPupilFilter.cpi.plugin_id:
                (self._load_pupil_filter_plugin, self._verify_pupil_filter_plugin),
            orm.DevelopmentModel.cpi.plugin_id: (self._load_development_model, self._verify_development_model),
        }

        self._database = database

    def verify(self, plugin):
        """:type plugin: Plugin"""
        table = orm.get_table_by_plugin(plugin)

        try:
            routines = self._plugin_map[plugin.type]
        except KeyError:
            raise Inspector.CommonError(
                "Plugin verification routines not found! "
                "Plugin type with index '%d' is not supported now." % plugin.type)

        try:
            record = self._database[table].filter(table.name == plugin.entry.name).one()
        except orm.NoResultFound:
            record = routines[Inspector.Load](plugin)
            self._database.add(record)
        else:
            routines[Inspector.Verify](plugin, record)

        plugin.record = record

        # Save plugin expression in the registry
        pcpi.PLUGIN_REGISTRY.add_plugin(plugin)