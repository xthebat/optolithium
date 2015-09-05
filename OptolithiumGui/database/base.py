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

import sqlalchemy
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.ext.declarative import DeclarativeMeta

import logging as module_logging
import settings
import helpers


Integer = sqlalchemy.Integer
String = sqlalchemy.String
Float = sqlalchemy.Float
Boolean = sqlalchemy.Boolean
DateTime = sqlalchemy.DateTime
Enum = sqlalchemy.Enum


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


class Column(sqlalchemy.Column):

    def __init__(self, *args, **kwargs):
        self.precision = kwargs.pop("precision", None)
        super(Column, self).__init__(*args, **kwargs)


class SignalsMeta(DeclarativeMeta):

    ID_NAME = "id"

    SIGNAL_CLASS_SUFFIX = "SignalsClass"

    GuiObjectClass = settings.get_gui_provider_object()
    GuiSignalClass = settings.get_gui_provider_signal()

    ClassAttributes = dict()

    # noinspection PyPep8Naming
    @staticmethod
    def SignalsAttrName(arg):
        classname = arg if isinstance(arg, basestring) else arg.__class__.__name__
        return "%s.%s" % (classname, SignalsMeta.SIGNAL_CLASS_SUFFIX)

    class AbstractSignalsClass(GuiObjectClass):
        def __init__(self, container):
            SignalsMeta.GuiObjectClass.__init__(self)
            # logging.info("%s: %s" % (self.__class__.__name__, container))
            self.__container = container

        def __getitem__(self, column):
            """
            :type column: Column | RelationshipProperty |
                options.structures.AttributedProperty | options.structures.Abstract
            :rtype: GuiSignalClass
            """
            return getattr(self, column.key)

        # def __iter__(self):
        #     for field in self.__container.__dict__.values():
        #         # if isinstance(field, (Column, RelationshipProperty, AttributedProperty, Abstract)):
        #         # FIXME: This is wrench and very danger
        #         logging.info("Self: %s (%s)" % (field, field.__class__.__name__))
        #         if isinstance(field, (Column, RelationshipProperty)) or \
        #            field.__class__.__name__ == "AttributedProperty" or \
        #            field.__class__.__name__ == "Abstract":
        #             yield self[field]

        def container(self):
            return self.__container

    # noinspection PyPep8Naming
    @staticmethod
    def CreateSignalsClass(class_name, items, db_columns=False):
        """
        :type class_name: str
        :type items: list of str or list of Column
        :type db_columns: bool
        """
        signal_class_name = SignalsMeta.SignalsAttrName(class_name)
        if db_columns:
            signal_class_dict = dict()
            for item in items:
                # logging.info("Item: %s [%s]" % (item, type(item)))

                # "key" property used here because "name" property has only Column
                # object but RelationshipProperty hasn't. While "key" is equal to "name"
                # and both objects have this property.
                if isinstance(item, (Column, RelationshipProperty)) and \
                   item.key not in signal_class_dict and \
                   item.key != SignalsMeta.ID_NAME:
                    # logging.info("Add signal: %s.%s" % (class_name, item.key))
                    signal_class_dict[item.key] = SignalsMeta.GuiSignalClass(name=item.key)
        else:
            signal_class_dict = {item: SignalsMeta.GuiSignalClass(name=item) for item in items}

        return type(signal_class_name, (SignalsMeta.AbstractSignalsClass, ), signal_class_dict)

    def __init__(cls, class_name, bases, dict_):
        # logging.info("Current class: %s" % cls.__name__)

        super(SignalsMeta, cls).__init__(class_name, bases, dict_)

        check_attrs = []
        for parent in cls.mro():
            check_attrs.extend(SignalsMeta.ClassAttributes.get(parent, []))
        check_attrs.extend(dict_.values())

        SignalsMeta.ClassAttributes[cls] = dict_.values()

        signal_class = SignalsMeta.CreateSignalsClass(class_name, check_attrs, db_columns=True)
        setattr(cls, signal_class.__name__, signal_class)