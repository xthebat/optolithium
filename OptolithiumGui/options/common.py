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
from database.base import SignalsMeta, Float, Integer, String
import helpers

__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


class ReportTemplates(object):

    header = (
        """<table border="0">
            <tr class="report">
                <td class="report-icon"><img src="%(icon)s"/></td>
                <td class="report-name">%(name)s</td>
                <td class="report-value"></td>
            </tr>
            %(body)s
        </table>"""
    )

    value = (
        """<tr class="report">
                <td class="report-icon"></td>
                <td class="report-name">%(name)s</td>
                <td class="report-value">%(value)s</td>
        </tr>"""
    )

    subvalue = (
        """<tr class="report">
                <td class="report-icon"></td>
                <td class="report-name"><div class="report-subvalue">%(name)s</div></td>
                <td class="report-value">%(value)s</td>
        </tr>"""
    )

    composite = (
        """<tr>
            <td colspan="3">%s</td>
        </tr>"""
    )


class Abstract(object):

    key = "value"

    def __init__(self, dtype):
        self.__dtype = dtype()
        self.__values = {None: self}

    def __get__(self, instance, owner):
        if instance not in self.__values:
            raise KeyError("Value of %s [%s] hasn't set yet" % (instance.name, owner))

        return self.__values[instance]

    def __set__(self, instance, value):
        real_type = self.__dtype.python_type
        if not isinstance(value, real_type):
            raise TypeError("Option value of %s can be assigned only to %s type value (input is %s)" %
                            (instance.name, real_type.__name__, type(value).__name__))
        if instance not in self.__values or self.__values[instance] != value:
            # previous = "Undefined" if instance not in self.__values else self.__values[instance]
            # logging.info("%s.%s: %s -> %s" % (instance.name, self.key, previous, value))
            self.__values[instance] = value
            instance.signals[Abstract].emit()

    @staticmethod
    def get_concrete(instance):
        """:rtype: Abstract"""
        return getattr(instance.__class__, Abstract.key)

    @property
    def type(self):
        return self.__dtype


class Enum(Abstract):

    def __init__(self, variants, raise_constraint=True):
        """
        :param list of string variants: List of the possible value for enumeration
        :param bool raise_constraint: If True - then exception will be raised if try to set value not from variants
        """
        super(Enum, self).__init__(dtype=String)

        if not isinstance(variants, list):
            raise TypeError("Variants input parameter must be list of the acceptable values")

        if not all([isinstance(v, basestring) for v in variants]):
            raise TypeError("Each variants member must be string type")

        self.__raise_constraint = raise_constraint
        self.__variants = variants

    def __set__(self, instance, value):
        if not isinstance(value, basestring):
            raise TypeError("Value input parameter must be string")

        if value not in self.__variants:
            if self.__raise_constraint:
                raise ValueError("Enumeration of %s set to value not in possible list: %s" % (instance.name, value))

        super(Enum, self).__set__(instance, value)

    @property
    def variants(self):
        return self.__variants


class Numeric(Abstract):

    orm_cast = {
        float: Float,
        int: Integer,
        long: Integer
    }

    def __init__(self, vmin=None, vmax=None, dtype=float, precision=None, raise_constraint=False):

        if dtype not in Numeric.orm_cast:
            raise TypeError("Numeric class only support the next types: int, float! Input value is %s" % dtype.__name__)

        super(Numeric, self).__init__(dtype=Numeric.orm_cast[dtype])

        self.__raise_constraint = raise_constraint
        self.__precision = precision

        if vmin is not None:
            if type(vmin) != dtype:
                raise TypeError("Minimum value type must be identical to value type")
            self.__min_value = vmin
        else:
            self.__min_value = None

        if vmax is not None:
            if type(vmax) != dtype:
                raise TypeError("Maximum value type must be identical to value type")
            self.__max_value = vmax
        else:
            self.__max_value = None

    @property
    def min(self):
        return self.__min_value

    @property
    def max(self):
        return self.__max_value

    @property
    def precision(self):
        return self.__precision

    def higher_max(self, value):
        return self.max is not None and value > self.max

    def lower_min(self, value):
        return self.min is not None and value < self.min

    def within_constraint(self, value):
        return not self.higher_max(value) and not self.lower_min(value)

    def __set__(self, instance, value):
        if self.__raise_constraint and not self.within_constraint(value):
            raise ValueError("Numeric of %s set to the outside constraint value: %s" % (instance.name, value))

        if self.higher_max(value):
            value = self.max
        elif self.lower_min(value):
            value = self.min

        if type(value) == float and self.__precision is not None:
            value = round(value, self.__precision)

        super(Numeric, self).__set__(instance, value)


class AttributedProperty(property):

    def __init__(self, fget=None, fset=None, fdel=None, doc=None, **kwargs):

        super(AttributedProperty, self).__init__(fget, fset, fdel, doc)
        self.key = kwargs.pop("key")
        self.type = kwargs.pop("dtype")()
        self.precision = kwargs.pop("precision", None)
        if kwargs:
            raise NotImplementedError("The next attributes is unimplemented: %s" % kwargs)


class Variable(object):

    SignalsClass = SignalsMeta.CreateSignalsClass("SignalsClass", [Abstract.key])

    value = None
    count = 0

    def __init__(self, ftype, value=None, name=None):
        """
        :param str or None name: Object name
        :param value: Initial options value
        :param name: Option name
        """
        self.__name = "%s_%d" % (Variable.__name__, Variable.count) if name is None else name
        self.__signals = Variable.SignalsClass(self)
        if value is not None:
            self.value = value
        Variable.count += 1

    @property
    def name(self):
        return self.__name

    @property
    def signals(self):
        return self.__signals

    def __new__(cls, ftype, *args, **kwargs):
        class_ = type(cls.__name__, (cls, ), {"value": ftype})
        return object.__new__(class_)

    def report(self):
        return ReportTemplates.value % {"name": self.name, "value": self.value}