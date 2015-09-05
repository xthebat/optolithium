# -*- coding: utf-8 -*-
# The Enum Recipe by zzzeek
# http://techspot.zzzeek.org/2011/01/14/the-enum-recipe/
import re
from sqlalchemy.types import SchemaType, TypeDecorator
from database.base import Enum


class EnumSymbol(object):
    """Define a fixed symbol tied to a parent class."""

    def __init__(self, cls_, name, value, description):
        self.cls_ = cls_
        """:type: type"""
        self.name = name
        """:type: str"""
        self.value = value
        """:type: str"""
        self.description = description
        """:type: str"""

    def __reduce__(self):
        """Allow unpickling to return the symbol linked to the DeclarativeEnum class."""
        return getattr, (self.cls_, self.name)

    def __iter__(self):
        return iter([self.value, self.description])

    def __repr__(self):
        return "%s" % self.name


class EnumMeta(type):
    """Generate new DeclarativeEnum classes."""

    def __init__(cls, classname, bases, dict_):
        cls._reg = reg = cls._reg.copy()
        for k, v in dict_.items():
            if isinstance(v, tuple):
                sym = reg[v[0]] = EnumSymbol(cls, k, *v)
                setattr(cls, k, sym)
        # noinspection PyReturnFromInit
        return type.__init__(cls, classname, bases, dict_)

    def __iter__(cls):
        # noinspection PyUnresolvedReferences
        return iter(cls._reg.values())


class DeclarativeEnum(object):
    """Declarative enumeration."""

    __metaclass__ = EnumMeta
    _reg = {}

    @classmethod
    def from_string(cls, value):
        try:
            return cls._reg[value]
        except KeyError:
            raise ValueError("Invalid value for %r: %r" % (cls.__name__, value))

    @classmethod
    def values(cls):
        return cls._reg.keys()

    @classmethod
    def db_type(cls):
        return DeclarativeEnumType(cls)


class DeclarativeEnumType(SchemaType, TypeDecorator):
    # noinspection PyMissingConstructor
    def __init__(self, enum):
        self.enum = enum
        sub = re.sub('([A-Z])', lambda m: "_" + m.group(1).lower(), enum.__name__)
        self.impl = Enum(*enum.values(), name="ck%s" % sub)

    def _set_table(self, table, column):
        # noinspection PyProtectedMember
        self.impl._set_table(table, column)

    def copy(self):
        return DeclarativeEnumType(self.enum)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value.value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum.from_string(value.strip())