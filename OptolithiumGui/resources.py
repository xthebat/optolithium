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
import sys

if os.name == "nt":
    basis = sys.executable if hasattr(sys, 'frozen') else sys.argv[0]
    basepath = os.path.split(basis)[0]
    os.environ['PATH'] = basepath + os.pathsep + os.environ['PATH']

import magic
from magic.api import MagicError
import helpers
import logging as module_logging


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


class Resource(object):

    # In windows platform prefix must be file:\\ and in linux file:/
    html_prefix = {
        "nt": "file:\\",
        "posix": "file:"
    }

    def __init__(self, path):
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        logging.debug("Loading resources %s" % path)
        self.__path = path
        self.__url = Resource.html_prefix[os.name] + path

    @property
    def path(self):
        return self.__path

    @property
    def url(self):
        return self.__url


class PlainText(Resource):
    def __init__(self, *args):
        path = args[0]
        super(PlainText, self).__init__(path)
        with open(path) as data_file:
            self.__data = data_file.read()

    @property
    def data(self):
        return self.__data


class Icon(Resource):
    def __init__(self, *args):
        path, icon_driver = args[0], args[1]
        super(Icon, self).__init__(path)
        self.__data = icon_driver(path)

    @property
    def data(self):
        return self.__data


_ResourceFactory = {
    "text": PlainText,
    "application": PlainText,
    "image": Icon
}


class DummyIcon(object):
    def __init__(self, path):
        self.__path = path


class Resources(object):

    _instance = None

    # FIXME: Quirk to load magic library (must be fixed by mean of the recompiling of libmagic1 library)
    try:
        _magic = magic.Magic(flags=magic.MAGIC_MIME_TYPE)
    except MagicError:
        _magic = magic.Magic(paths=["share/misc/magic"], flags=magic.MAGIC_MIME_TYPE)

    def __new__(cls, resource=None, attribute=None, data=None):
        if not cls._instance:
            cls._instance = super(Resources, cls).__new__(cls)
            return cls._instance
        else:
            return cls._instance.get_item_attribute(resource, attribute)

    # noinspection PyUnusedLocal
    def __init__(self, resource=None, data=None):
        if isinstance(self, Resources):
            self.__data = data

    @classmethod
    def load(cls, basepath, directories, icon_driver=None):
        if icon_driver is None:
            logging.warning("Icons driver was not set!")
            icon_driver = DummyIcon

        data = dict()
        for directory in directories:
            data[directory] = dict()
            resource_directory = os.path.join(basepath, directory)
            for filename in os.listdir(resource_directory):
                path = os.path.join(resource_directory, filename)
                mime_type = cls._magic.id_filename(path)
                if mime_type is not None:
                    mime = mime_type.split('/')[0]
                    try:
                        resource_class = _ResourceFactory[mime]
                    except KeyError:
                        logging.warning("Can't load resource (unknown mime %s): %s" % (mime, path))
                    else:
                        resource_name = helpers.GetFilename(filename).split('.')[0]
                        data[directory][resource_name] = resource_class(path, icon_driver)
                else:
                    logging.warning("Can't load resource (mime not determined): %s" % path)

        return cls(data=data)

    def get_item_attribute(self, item, attribute=None):
        attribute = "data" if attribute is None else attribute

        if '/' not in item:
            return [getattr(v, attribute) for v in self.__data[item].values()]
        else:
            directory, name = item.split('/')
            return getattr(self.__data[directory][name], attribute)


if __name__ == "__main__":
    import PyQt4.QtGui as QtGui
    app = QtGui.QApplication(sys.argv)
    Resources.load(os.getcwd(), ["icons", "ddl"],  QtGui.QIcon)
    print Resources("icons/No")
    print Resources("icons/Resist", "url")
    print Resources("ddl")
    main_window = QtGui.QMainWindow()
    main_window.show()
    sys.exit(app.exec_())