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

import abc
import os
import subprocess
import threading
import traceback
import functools
from Queue import Queue as StandardQueue
from Queue import Empty as QueueEmpty
import logging as module_logging
import sys
import itertools


__author__ = 'Alexei Gladkikh'


# noinspection PyPep8Naming
def enableLoggersForHelperModule():
    """
    This function will be called after definition of enableStreamLogHandler and
    enableFileLogHandler. Use it to enable required logger handlers.
    """
    logStreamEnable(logging)


# --------------------------------------------------------------------------------------------------


# noinspection PyPep8Naming
def GetFilename(path):
    """
    Return file name without extension from input path

    :type path: str
    """
    basename = os.path.basename(path)
    return os.path.splitext(basename)[0]


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
fdevnull = open(os.devnull, 'w')


# noinspection PyPep8Naming
def Cast(value, type, default=None):
    """
    Cast(value, type[, default]) -> value

    Try to cast value to specified type. If conversion can't be performed return default value.
    """
    try:
        return type(value)
    except ValueError:
        if default is None:
            return default
        return type(default)


# noinspection PyPep8Naming
def StaticVariable(varname, value):
    def decorate(func):
        setattr(func, varname, value)
        return func
    return decorate


# noinspection PyPep8Naming
def Singleton(cls):
    """
    Decorate specified class to make it correspond to singleton pattern.

    WARNING: In inheritance a class that also decorated by mean of this Singleton decorator
    you have to use old-style parent constructor, for example threading.Thread.__init__(self),
    otherwise TypeError exception occurred.

    :param cls: Decorated as singleton class
    :type cls: class
    :return: types.FunctionType
    """

    # Static variable
    instances = {}

    def getInstance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return getInstance


# noinspection PyPep8Naming
@StaticVariable("handler", None)
@StaticVariable("loggers", [])
def logStreamEnable(logger):
    """
    Set format and enable stream logging for specified logger.

    :type logger: logging.Logger
    """

    if logger not in logStreamEnable.loggers:
        # Lazy handler initialization
        if logStreamEnable.handler is None:
            log_hdlr = module_logging.StreamHandler(sys.stdout)
            formatter = module_logging.Formatter("%(levelname)-8s %(module)-12s"
                                                 "[%(funcName)-18s:%(lineno)-4d]# %(message)s")
            log_hdlr.setFormatter(formatter)
            logStreamEnable.handler = log_hdlr

        logger.addHandler(logStreamEnable.handler)
        logStreamEnable.loggers.append(logger)
        logging.debug("Stream log handler enabled for logger %s" % logger.name)
    else:
        logging.warning("Stream log handler already enabled for logger %s" % logger.name)


# This function must be defined at the head of helper module
# where required logger must be initialized by mean of
# enableStreamLogHandler and/or enableFileLogHandler
enableLoggersForHelperModule()


# noinspection PyPep8Naming
class classproperty(property):
    # noinspection PyMethodOverriding
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()


# --------------------------------------------------------------------------------------------------


def enum(*sequential, **named):
    """
    Create enumeration object with reverse dictionary property.

    Python 2.7 enumeration support (PEP 435).

    E = enum("ONE", "TWO")
    print(E.ONE, E.TWO)
    -> 0, 1
    E.reverse_mapping[0] => "ONE"
    E.reverse_mapping[1] => "TWO"
    """
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)


# --------------------------------------------------------------------------------------------------


def pairwise_shift(iterable):
    """s -> (s0,s1), (s2,s3), (s4, s5), ..."""
    a = iter(iterable)
    return itertools.izip(a, a)


def pairwise_all(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)


# --------------------------------------------------------------------------------------------------


class DisposableInterface(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def dispose(self):
        pass


class DisposableList(list, DisposableInterface):

    # Caution: type(self) for purposes to use it in the IDAPython. When IDA reload context (after script restart)
    # ID of previous superclass and current superclass is different, but types are equals.

    # noinspection PyMissingConstructor
    def __init__(self, *args):
        super(type(self), self).__init__()
        for item in args:
            self.append(item)

    def append(self, p_object):
        if not isinstance(p_object, DisposableInterface):
            raise ValueError("Item must be inherited from DisposableInterface")
        super(type(self), self).append(p_object)

    def extend(self, iterable):
        if not all([isinstance(item, DisposableInterface) for item in iterable]):
            raise ValueError("All items must be inherited from DisposableInterface")
        super(type(self), self).extend(iterable)

    def insert(self, index, p_object):
        if not isinstance(p_object, DisposableInterface):
            raise ValueError("Item must be inherited from DisposableInterface")
        super(type(self), self).insert(index, p_object)

    def pop(self, index=None):
        value = super(type(self), self).pop(index) if index is not None else super(type(self), self).pop()
        value.dispose()
        return value

    def remove(self, value):
        super(type(self), self).remove(value)
        value.dispose()

    def dispose(self):
        while self:
            self.pop()