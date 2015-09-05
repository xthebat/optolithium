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

import ctypes
import datetime
import logging as module_logging
import gdsii.library
import gdsii.structure
import gdsii.elements

import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.orm.query
import sqlalchemy.orm.exc
import sqlalchemy.orm.session
import sqlalchemy.engine.reflection
import sqlalchemy.sql.schema
from sqlalchemy import and_
from sqlalchemy import ForeignKey, event
from sqlalchemy.orm import relationship, backref, RelationshipProperty, ColumnProperty
from sqlalchemy.schema import CheckConstraint, UniqueConstraint, DDL
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property

from database.base import Column, SignalsMeta, Integer, Float, String, DateTime, Boolean

import numpy as np
from scipy.interpolate import interp1d, griddata
from collections import OrderedDict
from config import DATETIME_FORMAT

from options.common import Variable, Numeric, AttributedProperty
from auxmath import cartesian, point_inside_polygon

import optolithiumc as oplc

import config
import Enum
import helpers
import pcpi
import physc


__author__ = 'Alexei Gladkikh'


Connection = sqlalchemy.create_engine
Inspector = sqlalchemy.engine.reflection.Inspector
Table = sqlalchemy.sql.schema.Table
Query = sqlalchemy.orm.query.Query

NoResultFound = sqlalchemy.orm.exc.NoResultFound
MultipleResultsFound = sqlalchemy.orm.exc.MultipleResultsFound
IntegrityError = sqlalchemy.exc.IntegrityError
OperationalError = sqlalchemy.exc.OperationalError

logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)

APPLICATION_NAME = "Optolithium"

METHOD_NONE_IMPLEMENTED = "This method must be redefined in the inherited class"


class Precision(object):
    refractive_index = 3
    wavelength = 3
    dill = 3


class DeleteHook(object):

    def on_delete(self, session):
        """
        :type: Session
        :return: Query of the objects to being delete
        :rtype: Query
        """
        pass


class UnknownObjectTypeError(Exception):
    def __init__(self, typename):
        super(UnknownObjectTypeError, self).__init__("Unknown object type: %s" % typename)


class GenericType(Enum.DeclarativeEnum):

    # Standard object's types
    Material = "Ma", "Materials"
    """:type: str"""
    SourceShape = "So", "Source Shapes"
    """:type: str"""
    PupilFilter = "Pf", "Pupil Filters"
    """:type: str"""
    Illumination = "Il", "Illuminations"
    """:type: str"""
    Polarization = "Po", "Polarizations"
    """:type: str"""
    TemperatureProfile = "Tp", "Temperature Profiles"
    """:type: str"""
    Mask = "Mk", "Database Masks"
    """:type: str"""
    DeveloperSheet = "DSh", "Development Rates"
    """:type: str"""
    DeveloperExpr = "DEx", "Development Rates"
    """:type: str"""
    Resist = "Re", "Resists"
    """:type: str"""

    # Plugin object's types
    DevelopmentModel = "DmD", "Development Models"
    """:type: str"""
    AbstractPluginMask = "MkP", "Mask's Plugins"
    """:type: str"""
    AbstractPluginSourceShape = "SoP", "Source Shape's Plugins"
    """:type: str"""
    AbstractPluginPupilFilter = "PfP", "Pupil Filter's Plugins"
    """:type: str"""


class GeometryShape(Enum.DeclarativeEnum):

    Rectangle = "R", "Rectangle"
    """:type: str"""
    Polygon = "P", "Polygon"
    """:type: str"""


class GeometryObjectType(Enum.DeclarativeEnum):

    Geometry = "Ge", "Geometry"
    """:type: str"""
    Region = "Re", "Region"
    """:type: str"""


class BaseTemplate(object):

    id = Column(Integer, primary_key=True)
    __tablename__ = declared_attr(lambda cls: cls.__name__)
    identifier = hybrid_property(lambda cls: cls.__tablename__)

    # CAUTION: Using lazy initialization because "@reconstructor" decorator not working under Cython

    @property
    def dirty(self):
        if not hasattr(self, "_dirty"):
            # noinspection PyAttributeOutsideInit
            self._dirty = False
        return self._dirty

    @property
    def signals(self):
        """:rtype: AbstractSignalsClass"""
        if not hasattr(self, "_signals"):
            # logging.info("Create signals for %s of %s" % (self, self.__class__.__name__))
            signal_class = getattr(self.__class__, SignalsMeta.SignalsAttrName(self))
            # noinspection PyAttributeOutsideInit
            self._signals = signal_class(self)
        return self._signals


Base = declarative_base(cls=BaseTemplate, name=BaseTemplate.__name__, metaclass=SignalsMeta, constructor=None)


# noinspection PyUnusedLocal
@event.listens_for(Base, 'attribute_instrument')
def configure_listener(class_, key, inst):
    """This event is called whenever an attribute on a class is instrumented"""

    # logging.info("Configure listener for: %s, %s, %s" % (inst, hasattr(inst.property, 'columns'), type(inst)))

    if isinstance(inst.property, ColumnProperty):
        # noinspection PyUnusedLocal
        @event.listens_for(inst, "set", retval=True)
        def set_column(instance, value, oldvalue, initiator):
            """This event is called whenever a "set" occurs on that instrumented attribute"""
            column = inst.property.columns[0]
            if column.key == SignalsMeta.ID_NAME:
                return value

            round_value = round(value, column.precision) if column.precision is not None else value
            # logging.info("%s: %s -> %s (%s) [%s]" % (column.key, oldvalue, value, round_value, column.precision))

            if column.key not in instance.__dict__ or instance.__dict__[column.key] != round_value:
                # Oh... it's a black magic change value before some ORM action's how it affect on db
                instance.__dict__[column.key] = round_value

                # Workaround of SQLAlchemy strange behaviour, it set attribute
                # before call constructor or reconstructor for parametric material
                if hasattr(instance, "signals"):
                    instance.signals[column].emit()

                instance._dirty = True

            return round_value

    elif isinstance(inst.property, RelationshipProperty):
        # noinspection PyUnusedLocal
        @event.listens_for(inst, "set", retval=True)
        def set_relationship(instance, value, oldvalue, initiator):
            """This event is called whenever a "set" occurs on that instrumented attribute"""
            # logging.info("%s: %s -> %s" % (inst.property.key, oldvalue, value))
            if inst.property.key not in instance.__dict__ or instance.__dict__[inst.property.key] != value:
                instance.__dict__[inst.property.key] = value

                if hasattr(instance, "signals"):
                    instance.signals[inst.property].emit()

                instance._dirty = True

            return value


class Generic(Base):

    @staticmethod
    def const_polymorphic():
        query = """
            CREATE TRIGGER ConstantGenericInheritance
                UPDATE OF type ON Generic
            BEGIN
                SELECT RAISE (ABORT, 'Changing of objects polymorphic type is forbidden!');
            END;"""
        return DDL(query)

    @staticmethod
    def inheritance_trigger(child_class):
        """:type child_class: type"""
        symbol = getattr(GenericType, child_class.__name__)
        query = """
            CREATE TRIGGER Check%(child_name)sInheritance
                BEFORE INSERT ON %(child_name)s
                WHEN EXISTS (
                    SELECT NULL FROM Generic
                    WHERE Generic.id == new.id AND Generic.type != "%(type_name)s"
                )
            BEGIN
                SELECT RAISE (ABORT, 'Inheritance violated on Generic->%(child_name)s');
            END;""" % {'child_name': symbol.name, 'type_name': symbol.value}
        return DDL(query)

    # noinspection PyPropertyDefinition,PyMethodParameters
    @hybrid_property
    def icon(cls):
        raise NotImplementedError(METHOD_NONE_IMPLEMENTED)

    # noinspection PyPropertyDefinition,PyMethodParameters
    @hybrid_property
    def title(cls):
        # This hack is required because cls can be as a instance and object
        # Class always must has __name__ attribute that determine its name
        name = getattr(cls, "__name__", cls.__class__.__name__)
        enum_symbol = getattr(GenericType, name)
        """:type: Enum.EnumSymbol"""
        return enum_symbol.description

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    desc = Column(String, nullable=False)
    created = Column(DateTime, nullable=False)
    type = Column(GenericType.db_type(), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": None,
        "polymorphic_on": type
    }

    def __init__(self, name, desc):
        super(Generic, self).__init__()
        self.name = name
        self.desc = desc if desc is not None else str()
        self.created = datetime.datetime.now()

    def assign(self, other):
        """:type other: Generic"""
        if self.type != other.type:
            raise RuntimeError("Assign of Generics objects (%s, %s) with different types (%s, %s)" %
                               (self.name, other.name, self.type, other.type))
        self.name = other.name
        self.desc = other.desc
        self.created = other.created
        self.type = other.type

    def clone(self, name=None):
        """
        :type name: str or None
        :rtype: Generic
        """
        return Generic(self.name if name is None else name, self.desc)

    def __str__(self):
        return "%s \"%s\"" % (self.__tablename__, self.name)

    def export(self):
        """:rtype: dict"""
        return {
            Generic.name.key: self.name,
            Generic.desc.key: self.desc,
            Generic.created.key: self.created.strftime(DATETIME_FORMAT),
            Generic.type.key: str(self.type)
        }

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        raise NotImplementedError(METHOD_NONE_IMPLEMENTED)

    def parse(self, p_object):
        """:type p_object: dict"""
        raise NotImplementedError(METHOD_NONE_IMPLEMENTED)


event.listen(Generic.__table__, "after_create", Generic.const_polymorphic())


class Session(sqlalchemy.orm.session.Session):

    def delete(self, instance):
        logging.debug("Session.delete(%s)" % instance)
        deleted = [instance]
        if isinstance(instance, Generic) and isinstance(instance, DeleteHook):
            deleted.extend(instance.on_delete(self))
        self.autoflush = False
        for p_object in deleted:
            super(Session, self).delete(p_object)
        self.autoflush = True


class StandardObject(object):
    pass


class PluginObject(object):

    cpi = None
    """
    :param: C plugin interface structure
    :type: pcpi.CPluginInterface
    """


class AbstractPluginParameter(object):

    def __init__(self, name, order, defv, vmin=None, vmax=None):
        """
        :type name: str
        :type order: int
        :type defv: float
        :type vmin: float
        :type vmax: float
        """
        super(AbstractPluginParameter, self).__init__()
        self.name = name
        self.ord = order
        self.defv = defv
        self.min = vmin
        self.max = vmax

    @property
    def default(self):
        return self.defv

    def clone(self):
        """:rtype: AbstractPluginParameter"""
        return self.__class__(self.name, self.ord, self.defv, self.min, self.max)


def _create_backref(name, order_by="id", suffix="Data"):
    """:type name: str"""
    data_table = name + suffix
    return backref(data_table, order_by="%s.%s" % (data_table, order_by))


def _create_relationship(name, order_by="id", suffix="Data", cascade="all, delete, delete-orphan"):
    """:type name: str"""
    data_table = name + suffix
    return relationship(data_table, order_by="%s.%s" % (data_table, order_by), cascade=cascade)


class Material(Generic, StandardObject):

    icon = hybrid_property(lambda cls: "icons/Material")

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)
    data = _create_relationship("Material")

    __mapper_args__ = {"polymorphic_identity": GenericType.Material}

    def __init__(self, name, data, desc=None):
        """:type data: list of MaterialData"""
        super(Material, self).__init__(name, desc)
        self.data = data

    def assign(self, other):
        """:type other: Material"""
        super(Material, self).assign(other)
        self.data = [v.clone() for v in other.data]

    def clone(self, name=None):
        """
        :type name: str or None
        :rtype: Material
        """
        data = [v.clone() for v in self.data]
        return Material(self.name if name is None else name, data, self.desc)

    def export(self):
        """:rtype: dict"""
        result = super(Material, self).export()
        result.update({Material.data.key: [data.export() for data in self.data]})
        return result

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        data = [MaterialData.load(data) for data in p_object[Material.data.key]]
        return cls(
            name=str(p_object[Material.name.key]),
            desc=str(p_object[Material.desc.key]),
            data=data)

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(Material.load(p_object))


event.listen(Material.__table__, "after_create", Generic.inheritance_trigger(Material))


class MaterialData(Base):

    wavelength = Column(Float, nullable=False, precision=Precision.wavelength)
    real = Column(Float, nullable=False, precision=Precision.refractive_index)
    imag = Column(Float, nullable=False, precision=Precision.refractive_index)
    material_id = Column(Integer, ForeignKey(Material.id), nullable=False)

    material = relationship(Material, backref=_create_backref("Material"))

    __table_args__ = (
        UniqueConstraint(wavelength, material_id, name="duplicate wavelength values"),
        # -------------------------------------------------
        CheckConstraint(wavelength > 0.0, name="wavelength must be > 0.0"),
        # -------------------------------------------------
        CheckConstraint(real >= 0.0, name="real part must be >= 0.0"),
        CheckConstraint(imag >= 0.0, name="imag part must be >= 0.0")
    )

    def __init__(self, wavelength, real, imag):
        """
        :type wavelength: float
        :type real: float
        :type imag: float
        """
        super(MaterialData, self).__init__()
        self.wavelength = wavelength
        self.real = real
        self.imag = imag

    def clone(self):
        """:rtype: MaterialData"""
        return MaterialData(self.wavelength, self.real, self.imag)

    def __iter__(self):
        return (v for v in [self.real, self.imag])

    def export(self):
        return {
            MaterialData.wavelength.key: self.wavelength,
            MaterialData.real.key: self.real,
            MaterialData.imag.key: self.imag
        }

    def assign(self, other):
        """:type other: MaterialData"""
        self.wavelength = other.wavelength
        self.real = other.real
        self.imag = other.imag

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        return cls(
            wavelength=float(p_object[MaterialData.wavelength.key]),
            real=float(p_object[MaterialData.real.key]),
            imag=float(p_object[MaterialData.imag.key]))

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(MaterialData.load(p_object))


class SourceShape(Generic, StandardObject):

    icon = hybrid_property(lambda cls: "icons/SourceShape")

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)
    data = _create_relationship("SourceShape")

    __mapper_args__ = {"polymorphic_identity": GenericType.SourceShape}

    def __init__(self, name, data, desc=None):
        """:type data: list of SourceShapeData"""
        super(SourceShape, self).__init__(name, desc)
        self.data = data

    def assign(self, other):
        """:type other: SourceShape"""
        super(SourceShape, self).assign(other)
        self.data = [v.clone() for v in other.data]

    def clone(self, name=None):
        """
        :type name: str or None
        :rtype: SourceShape
        """
        data = [v.clone() for v in self.data]
        return SourceShape(self.name if name is None else name, data, self.desc)

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        data = [SourceShapeData.load(data) for data in p_object[SourceShape.data.key]]
        return cls(
            name=str(p_object[SourceShape.name.key]),
            desc=str(p_object[SourceShape.desc.key]),
            data=data)

    def export(self):
        result = super(SourceShape, self).export()
        result.update({SourceShape.data.key: [data.export() for data in self.data]})
        return result

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(SourceShape.load(p_object))

    def intensity(self, x=None, y=None):
        """
        Return intensity of the source shape.
        If x or y is None then native coordinates (as in input data) are used.

        :param list of float x or None: x-coordinates at which intensity must be calculated
        :param list of float y or None: y-coordinates at which intensity must be calculated
        :return: Native x, y if x or y is None and intensity else only intensity
        :rtype: (np.array, np.array, np.array) or np.array
        """
        def find_nearest(value, array):
            return (np.abs(array - value)).argmin()

        native_xy = False

        if x is None or y is None:
            native_xy = True
            vx, vy, vz = [], [], []
            for item in self.data:
                vx.append(item.x)
                vy.append(item.y)
                vz.append(item.intensity)

            x = np.unique(np.array(vx))
            y = np.unique(np.array(vy))

        if len(self.data) == 1:
            result = np.ndarray([len(y), len(x)])
            r = find_nearest(self.data[0].y, y)
            c = find_nearest(self.data[0].x, x)
            result[r, c] = self.data[0].intensity
        else:
            vx, vy, vz = [], [], []
            for item in self.data:
                vx.append(item.x)
                vy.append(item.y)
                vz.append(item.intensity)

            vx = np.array(vx)
            vy = np.array(vy)
            vz = np.array(vz)

            # This shit: y[:, None] - is transpose
            result = griddata((vy, vx), vz, (y[None, :], x[:, None]), method='linear', fill_value=0.0)

        if native_xy:
            return x, y, result

        return result

    # Compatibility with ConcretePluginSourceShape
    @property
    def variables(self):
        return []

    def convert2core(self):
        x, y, values = self.intensity()
        return oplc.SourceShapeModelSheet(x, y, np.asfortranarray(values))


event.listen(SourceShape.__table__, "after_create", Generic.inheritance_trigger(SourceShape))


class SourceShapeData(Base):

    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    intensity = Column(Float, nullable=False)
    source_shape_id = Column(Integer, ForeignKey(SourceShape.id), nullable=False)

    source_shape = relationship(SourceShape, backref=_create_backref("SourceShape"))

    __table_args__ = (
        UniqueConstraint(x, y, source_shape_id, name="duplicate x, y values"),
        # -------------------------------------------------
        CheckConstraint(intensity >= 0.0, name="intensity must >= 0.0"),
        CheckConstraint(intensity <= 1.0, name="intensity must <= 1.0"),
        # -------------------------------------------------
        CheckConstraint(x >= -1.0, name="x must be >= -1.0"),
        CheckConstraint(x <= 1.0, name="x must be <= 1.0"),
        # -------------------------------------------------
        CheckConstraint(y >= -1.0, name="y must be >= -1.0"),
        CheckConstraint(y <= 1.0, name="y must be <= 1.0")
    )

    def __init__(self, x, y, intensity):
        """
        :type x: float
        :type y: float
        :type intensity: float
        """
        super(SourceShapeData, self).__init__()
        self.x = x
        self.y = y
        self.intensity = intensity

    def clone(self):
        """:rtype: SourceShapeData"""
        return SourceShapeData(self.x, self.y, self.intensity)

    def assign(self, other):
        """:type other: SourceShapeData"""
        self.x = other.x
        self.y = other.y
        self.intensity = other.intensity

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        return cls(
            x=p_object[SourceShapeData.x.key],
            y=p_object[SourceShapeData.y.key],
            intensity=p_object[SourceShapeData.intensity.key])

    def export(self):
        return {
            SourceShapeData.x.key: self.x,
            SourceShapeData.y.key: self.y,
            SourceShapeData.intensity.key: self.intensity
        }

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(SourceShapeData.load(p_object))


class ConcretePluginCommon(object):

    SignalsClass = None

    def __init__(self, abstract, values):
        self.__abstract = abstract

        self.__signals = self.__class__.SignalsClass(self)

        self.__vars_dict = OrderedDict()

        values = [parameter.default for parameter in self._base.prms] if values is None else values

        for parameter, value in zip(self._base.prms, values):
            variable = Variable(
                ftype=Numeric(vmin=parameter.min, vmax=parameter.max, dtype=float),
                value=value, name=parameter.name)
            self.__vars_dict[variable.name] = variable

    signals = property(lambda self: self.__signals)
    name = property(lambda self: self.__abstract.name)
    desc = property(lambda self: self.__abstract.desc)
    variables = property(lambda self: self.__vars_dict.values())
    values = property(lambda self: [variable.value for variable in self.__vars_dict.values()])

    _base = property(lambda self: self.__abstract)

    def export(self):
        return {variable.name: variable.value for variable in self.variables}

    @classmethod
    def load(cls, p_object, abstract):
        values = [float(p_object[parameter.name]) for parameter in abstract.prms]
        return cls(abstract, values)

    def clone(self):
        return self.__class__(self._base, self.values)


class ConcretePluginSourceShape(ConcretePluginCommon):

    SignalsClass = SignalsMeta.CreateSignalsClass("ConcretePluginSourceShape", [], db_columns=False)

    def __init__(self, abstract, values=None):
        """
        :type abstract: orm.AbstractPluginSourceShape
        :type values: list of float
        """
        super(ConcretePluginSourceShape, self).__init__(abstract, values)
        self.__source_shape_struct = pcpi.source_shape_plugin_t()

    def intensity(self, x, y):
        """
        Return intensity of the source shape.
        If x or y is None then native coordinates (as in input data) are used.

        :param list of float x: x-coordinates at which intensity must be calculated
        :param list of float y: y-coordinates at which intensity must be calculated
        :return: intensity on x-y grid
        :rtype: np.array
        """
        result = np.ndarray([len(y), len(x)], dtype=float)
        xy = cartesian(y, x)
        rows = range(len(y))
        cols = range(len(x))
        rc = cartesian(rows, cols)
        for (r, c), (y, x) in zip(rc, xy):
            result[r, c] = self._base.calculate(x, y, *self.values)
        return result

    expr = property(lambda self: self._base.entry.expr)

    def export(self):
        result = self._base.export()
        result.update(super(ConcretePluginSourceShape, self).export())
        return result

    @classmethod
    def load(cls, p_object, abstract=None):
        """:type p_object: dict"""
        abstract_base = AbstractPluginSourceShape.load(p_object)
        return super(ConcretePluginSourceShape, cls).load(p_object, abstract_base)

    def convert2core(self):
        return oplc.SourceShapeModelPlugin(self.expr, self.values)


class AbstractPluginSourceShape(Generic, PluginObject):

    icon = hybrid_property(lambda cls: "icons/Numerics")

    cpi = pcpi.source_shape_plugin_t

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)
    prms = relationship(
        "AbstractPluginSourceShapePrm",
        order_by="AbstractPluginSourceShapePrm.ord",
        cascade="all, delete, delete-orphan")

    __mapper_args__ = {"polymorphic_identity": GenericType.AbstractPluginSourceShape}

    def __init__(self, name, prms, desc=None):
        """
        :param str name: Source Shape plugin name
        :param list of AbstractPluginSourceShapePrm prms: Parameters descriptors of the source shape plugin
        :param str or None desc: Description of the plugin
        """
        super(AbstractPluginSourceShape, self).__init__(name, desc)
        self.prms = prms
        self._source_shape_entry = None
        """:type: pcpi.source_shape_plugin_t"""

    def produce(self, values=None):
        """
        :type values: list of float
        :rtype: ConcretePluginSourceShape
        """
        return ConcretePluginSourceShape(self, values)

    @property
    def entry(self):
        """:rtype: pcpi.source_shape_plugin_t"""
        if not hasattr(self, "_source_shape_entry") or self._source_shape_entry is None:
            self._source_shape_entry = pcpi.PLUGIN_REGISTRY.get_by_id(self.id).entry
        return self._source_shape_entry

    def calculate(self, cx, cy, *values):
        array = ctypes.c_double * len(self.prms)
        # noinspection PyCallingNonCallable
        return self.entry.expr(cx, cy, array(*values))

    def assign(self, other):
        raise NotImplementedError(METHOD_NONE_IMPLEMENTED)

    def clone(self, name=None):
        """
        :type name: str or None
        :rtype: AbstractPluginSourceShape
        """
        if name is not None:
            raise NotImplementedError(METHOD_NONE_IMPLEMENTED)

        prms = [v.clone() for v in self.prms]
        return AbstractPluginSourceShape(self.name, prms, self.desc)

    @classmethod
    def load(cls, p_object):
        return pcpi.PLUGIN_REGISTRY.get_by_name(p_object[Generic.name.key]).record


class AbstractPluginSourceShapePrm(AbstractPluginParameter, Base):

    name = Column(String, nullable=False)
    ord = Column(Integer, nullable=False)
    defv = Column(Float)
    max = Column(Float)
    min = Column(Float)
    plugin_source_shape_id = Column(Integer, ForeignKey(AbstractPluginSourceShape.id, ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint(ord, plugin_source_shape_id, name="duplicate order arguments number"),
        # -------------------------------------------------
        # TODO: Check parameters
        # CheckConstraint(defv > min, "default value must greater than min values"),
        # CheckConstraint(defv < max, "default value must lower than max values"),
        # CheckConstraint(max > min, name="max must be > min argument value"),
    )


class PupilFilter(Generic, StandardObject):

    icon = hybrid_property(lambda cls: "icons/PupilFilter")

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)
    data = _create_relationship("PupilFilter")

    __mapper_args__ = {"polymorphic_identity": GenericType.PupilFilter}

    def __init__(self, name, data, desc=None):
        """:type data: list of PupilFilterData"""
        super(PupilFilter, self).__init__(name, desc)
        self.data = data

    def assign(self, other):
        """:type other: PupilFilter"""
        super(PupilFilter, self).assign(other)
        self.data = [v.clone() for v in other.data]

    def clone(self, name=None):
        """
        :type name: str or None
        :rtype: PupilFilter
        """
        data = [v.clone() for v in self.data]
        return PupilFilter(self.name if name is None else name, data, self.desc)

    def export(self):
        result = super(PupilFilter, self).export()
        result.update({PupilFilter.data.key: [data.export() for data in self.data]})
        return result

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        data = [PupilFilterData.load(data) for data in p_object[PupilFilter.data.key]]
        return cls(
            name=str(p_object[PupilFilter.name.key]),
            desc=str(p_object[PupilFilter.desc.key]),
            data=data)

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(PupilFilter.load(p_object))

    def coefficients(self, xdata=None, ydata=None):
        native_xy = False
        if xdata is None or ydata is None:
            step_rad = 1.0/float(len(self.data))
            xdata = np.arange(-1.0, 1.0 + step_rad, step_rad)
            ydata = np.arange(-1.0, 1.0 + step_rad, step_rad)
            native_xy = True

        rows = len(ydata)
        cols = len(xdata)
        result = np.ndarray([rows, cols], dtype=complex)
        xp = []
        fp_real = []
        fp_imag = []
        for item in self.data:
            xp.append(item.radius)
            rad = np.deg2rad(item.phase)
            fp_real.append(item.amplitude * np.cos(rad))
            fp_imag.append(item.amplitude * np.sin(rad))
        real = interp1d(xp, fp_real, bounds_error=False, fill_value=0.0)
        imag = interp1d(xp, fp_imag, bounds_error=False, fill_value=0.0)
        rc = cartesian(range(rows), range(cols))
        xy = cartesian(xdata, ydata)
        for (r, c), (x, y) in zip(rc, xy):
            radius = np.sqrt(x**2 + y**2)
            result[r, c] = complex(real(radius), imag(radius))

        if native_xy:
            return xdata, ydata, result

        return result

    # Compatibility with ConcretePluginPupilFilter
    @property
    def variables(self):
        return []

    def convert2core(self):
        x, y, values = self.coefficients()
        return oplc.PupilFilterModelSheet(x, y, np.asfortranarray(values))


event.listen(PupilFilter.__table__, "after_create", Generic.inheritance_trigger(PupilFilter))


class PupilFilterData(Base):

    radius = Column(Float, nullable=False)
    phase = Column(Float, nullable=False)  # in degrees
    amplitude = Column(Float, nullable=False)
    pupil_filter_id = Column(Integer, ForeignKey(PupilFilter.id), nullable=False)

    pupil_filter = relationship(PupilFilter, backref=_create_backref("PupilFilter"))

    __table_args__ = (
        UniqueConstraint(radius, pupil_filter_id, name="duplicate radius values"),
        # -------------------------------------------------
        CheckConstraint(phase >= -180.0, name="phase must be >= -180.0"),
        CheckConstraint(phase <= 180.0, name="phase must be <= 180.0"),
        # -------------------------------------------------
        CheckConstraint(amplitude >= 0.0, name="amplitude >= 0.0"),
        CheckConstraint(amplitude <= 1.0, name="amplitude <= 1.0")
    )

    def __init__(self, radius, phase, amplitude):
        """
        :type radius: float
        :type phase: float
        :type amplitude: float
        """
        super(PupilFilterData, self).__init__()
        self.radius = radius
        self.phase = phase
        self.amplitude = amplitude

    def clone(self):
        """:rtype: PupilFilterData"""
        return PupilFilterData(self.radius, self.phase, self.amplitude)

    def assign(self, other):
        """:type other: PupilFilterData"""
        self.radius = other.radius
        self.phase = other.phase
        self.amplitude = other.amplitude

    def export(self):
        return {
            PupilFilterData.radius.key: self.radius,
            PupilFilterData.phase.key: self.phase,
            PupilFilterData.amplitude.key: self.amplitude
        }

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        return cls(
            radius=p_object[PupilFilterData.radius.key],
            phase=p_object[PupilFilterData.phase.key],
            amplitude=p_object[PupilFilterData.amplitude.key])

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(PupilFilterData.load(p_object))


class ConcretePluginPupilFilter(ConcretePluginCommon):

    SignalsClass = SignalsMeta.CreateSignalsClass("ConcretePluginPupilFilter", [], db_columns=False)

    def __init__(self, abstract, values=None):
        """
        :type abstract: orm.AbstractPluginPupilFilter
        :type values: list of float
        """
        super(ConcretePluginPupilFilter, self).__init__(abstract, values)
        self.__pupil_filter_struct = pcpi.pupil_filter_plugin_t()

    def coefficients(self, x, y):
        """
        Return coefficients of the pupil filter.
        If x or y is None then native coordinates (as in input data) are used.

        :param list of float x: x-coordinates at which intensity must be calculated
        :param list of float y: y-coordinates at which intensity must be calculated
        :return: intensity on x-y grid
        :rtype: np.array
        """
        result = np.ndarray([len(y), len(x)], dtype=complex)
        xy = cartesian(y, x)
        rows = range(len(y))
        cols = range(len(x))
        rc = cartesian(rows, cols)
        for (r, c), (y, x) in zip(rc, xy):
            result[r, c] = self._base.calculate(x, y, *self.values)
        return result

    expr = property(lambda self: self._base.entry.expr)

    def export(self):
        result = self._base.export()
        result.update(super(ConcretePluginPupilFilter, self).export())
        return result

    @classmethod
    def load(cls, p_object, abstract=None):
        """:type p_object: dict"""
        abstract_base = AbstractPluginPupilFilter.load(p_object)
        return super(ConcretePluginPupilFilter, cls).load(p_object, abstract_base)

    def convert2core(self):
        return oplc.PupilFilterModelPlugin(self.expr, self.values)


class AbstractPluginPupilFilter(Generic, PluginObject):

    icon = hybrid_property(lambda cls: "icons/Numerics")

    cpi = pcpi.pupil_filter_plugin_t

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)
    prms = relationship(
        "AbstractPluginPupilFilterPrm",
        order_by="AbstractPluginPupilFilterPrm.ord",
        cascade="all, delete, delete-orphan")

    __mapper_args__ = {"polymorphic_identity": GenericType.AbstractPluginPupilFilter}

    def __init__(self, name, prms, desc=None):
        """
        :param str name: Pupil filter plugin name
        :param list of AbstractPluginPupilFilterPrm prms: Parameters descriptors of the pupil filter plugin
        :param str or None desc: Description of the plugin
        """
        super(AbstractPluginPupilFilter, self).__init__(name, desc)
        self.prms = prms
        self._pupil_filter_entry = None
        """:type: pcpi.pupil_filter_plugin_t"""

    def produce(self, values=None):
        """
        :type values: list of float
        :rtype: ConcretePluginPupilFilter
        """
        return ConcretePluginPupilFilter(self, values)

    @property
    def entry(self):
        """:rtype: pcpi.pupil_filter_plugin_t"""
        if not hasattr(self, "_pupil_filter_entry") or self._pupil_filter_entry is None:
            self._pupil_filter_entry = pcpi.PLUGIN_REGISTRY.get_by_id(self.id).entry
        return self._pupil_filter_entry

    def calculate(self, cx, cy, *values):
        array = ctypes.c_double * len(self.prms)
        # noinspection PyCallingNonCallable
        value = self.entry.expr(cx, cy, array(*values))
        return complex(value.real, value.imag)

    def assign(self, other):
        raise NotImplementedError(METHOD_NONE_IMPLEMENTED)

    def clone(self, name=None):
        """
        :type name: str or None
        :rtype: AbstractPluginPupilFilter
        """
        if name is not None:
            raise NotImplementedError(METHOD_NONE_IMPLEMENTED)

        prms = [v.clone() for v in self.prms]
        return AbstractPluginPupilFilter(self.name, prms, self.desc)

    @classmethod
    def load(cls, p_object):
        return pcpi.PLUGIN_REGISTRY.get_by_name(p_object[Generic.name.key]).record


class AbstractPluginPupilFilterPrm(AbstractPluginParameter, Base):

    name = Column(String, nullable=False)
    ord = Column(Integer, nullable=False)
    defv = Column(Float)
    max = Column(Float)
    min = Column(Float)
    plugin_pupil_filter_id = Column(Integer, ForeignKey(AbstractPluginPupilFilter.id, ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint(ord, plugin_pupil_filter_id, name="duplicate order arguments number"),
        # -------------------------------------------------
        # TODO: Check parameters
        # CheckConstraint(defv > min, "default value must greater than min values"),
        # CheckConstraint(defv < max, "default value must lower than max values"),
        # CheckConstraint(max > min, name="max must be > min argument value"),
    )


class Illumination(Generic, StandardObject):

    icon = hybrid_property(lambda cls: "icons/Material")

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)
    data = _create_relationship("Illumination")

    __mapper_args__ = {"polymorphic_identity": GenericType.Illumination}

    def __init__(self, name, data, desc=None):
        """:type data: list of IlluminationData"""
        super(Illumination, self).__init__(name, desc)
        self.data = data

    def assign(self, other):
        """:type other: Illumination"""
        super(Illumination, self).assign(other)
        self.data = [v.clone() for v in other.data]

    def clone(self, name=None):
        """
        :type name: str or None
        :rtype: Illumination
        """
        data = [v.clone() for v in self.data]
        return Illumination(self.name if name is None else name, data, self.desc)

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        data = [IlluminationData.load(data) for data in p_object[Illumination.data.key]]
        return cls(p_object[Illumination.name.key, data, p_object[Illumination.desc.key]])

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(Illumination.load(p_object))


event.listen(Illumination.__table__, "after_create", Generic.inheritance_trigger(Illumination))


class IlluminationData(Base):

    wavelength = Column(Float, nullable=False, precision=Precision.wavelength)
    intensity = Column(Float, nullable=False)
    illumination_id = Column(Integer, ForeignKey(Illumination.id), nullable=False)

    illumination = relationship(Illumination, backref=_create_backref("Illumination"))

    __table_args__ = (
        UniqueConstraint(wavelength, illumination_id, name="duplicate wavelength values"),
        # -------------------------------------------------
        CheckConstraint(intensity >= 0.0, name="intensity >= 0.0"),
        CheckConstraint(intensity <= 1.0, name="intensity <= 1.0")
    )

    def __init__(self, wavelength, intensity):
        """
        :type wavelength: float
        :type intensity: float
        """
        super(IlluminationData, self).__init__()
        self.wavelength = wavelength
        self.intensity = intensity

    def clone(self):
        """:rtype: IlluminationData"""
        return IlluminationData(self.wavelength, self.intensity)

    def assign(self, other):
        """:type other: IlluminationData"""
        self.wavelength = other.wavelength
        self.intensity = other.intensity

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        return cls(
            wavelength=p_object[IlluminationData.wavelength.key],
            intensity=p_object[IlluminationData.intensity.key])

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(IlluminationData.load(p_object))


class Polarization(Generic, StandardObject):

    icon = hybrid_property(lambda cls: "icons/Material")

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)
    data = _create_relationship("Polarization")

    __mapper_args__ = {"polymorphic_identity": GenericType.Polarization}

    def __init__(self, name, data, desc=None):
        """:type data: list of PolarizationData"""
        super(Polarization, self).__init__(name, desc)
        self.data = data

    def assign(self, other):
        """:type other: Polarization"""
        super(Polarization, self).assign(other)
        self.data = [v.clone() for v in other.data]

    def clone(self, name=None):
        """
        :type name: str or None
        :rtype: Polarization
        """
        data = [v.clone() for v in self.data]
        return Polarization(self.name if name is None else name, data, self.desc)

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        data = [PolarizationData.load(data) for data in p_object[Polarization.data.key]]
        return cls(p_object[Polarization.name.key, data, p_object[Polarization.desc.key]])

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(Polarization.load(p_object))


event.listen(Polarization.__table__, "after_create", Generic.inheritance_trigger(Polarization))


class PolarizationData(Base):

    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    degree = Column(Float, nullable=False)
    angle = Column(Float, nullable=False)
    ellipticity = Column(Float, nullable=False)
    polarization_id = Column(Integer, ForeignKey(Polarization.id), nullable=False)

    polarization = relationship(Polarization, backref=_create_backref("Polarization"))

    __table_args__ = (
        UniqueConstraint(x, y, polarization_id, name="duplicate x, y values"),
        # -------------------------------------------------
        CheckConstraint(x >= -1.0, name="x must be >= -1.0"),
        CheckConstraint(x <= 1.0, name="x must be <= 1.0"),
        # -------------------------------------------------
        CheckConstraint(y >= -1.0, name="y must be >= -1.0"),
        CheckConstraint(y <= 1.0, name="y must be <= 1.0"),
        # -------------------------------------------------
        CheckConstraint(degree >= 0.0, name="degree must be >= -1.0"),
        CheckConstraint(degree <= 1.0, name="degree must be <= 1.0"),
        # -------------------------------------------------
        CheckConstraint(angle >= -180.0, name="angle must be >= -180.0"),
        CheckConstraint(angle <= 180.0, name="angle must be <= 180.0"),
        # -------------------------------------------------
        CheckConstraint(ellipticity >= -1.0, name="ellipticity must be >= -1.0"),
        CheckConstraint(ellipticity <= 1.0, name="ellipticity must be <= 1.0"),
    )

    def __init__(self, x, y, degree, angle, ellipticity):
        """
        :type x: float
        :type y: float
        :type degree: float
        :type angle: float
        :type ellipticity: float
        """
        super(PolarizationData, self).__init__()
        self.x = x
        self.y = y
        self.degree = degree
        self.angle = angle
        self.ellipticity = ellipticity

    def clone(self):
        """:rtype: PolarizationData"""
        return PolarizationData(self.x, self.y, self.degree, self.angle, self.ellipticity)

    def assign(self, other):
        """:type other: PolarizationData"""
        self.x = other.x
        self.y = other.y
        self.degree = other.degree
        self.angle = other.angle
        self.ellipticity = other.ellipticity

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        return cls(
            x=p_object[PolarizationData.x.key],
            y=p_object[PolarizationData.y.key],
            degree=p_object[PolarizationData.degree.key],
            angle=p_object[PolarizationData.angle.key],
            ellipticity=p_object[PolarizationData.ellipticity.key])

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(PolarizationData.load(p_object))


class TemperatureProfile(Generic, StandardObject):

    icon = hybrid_property(lambda cls: "icons/Material")

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)
    data = _create_relationship("TemperatureProfile")

    __mapper_args__ = {"polymorphic_identity": GenericType.TemperatureProfile}

    def __init__(self, name, data, desc=None):
        """:type data: list of TemperatureProfileData"""
        super(TemperatureProfile, self).__init__(name, desc)
        self.data = data

    def assign(self, other):
        """:type other: TemperatureProfile"""
        super(TemperatureProfile, self).assign(other)
        self.data = [v.clone() for v in other.data]

    def clone(self, name=None):
        """
        :type name: str or None
        :rtype: TemperatureProfile
        """
        data = [v.clone() for v in self.data]
        return TemperatureProfile(self.name if name is None else name, data, self.desc)

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        data = [TemperatureProfileData.load(data) for data in p_object[TemperatureProfile.data.key]]
        return cls(p_object[TemperatureProfile.name.key, data, p_object[TemperatureProfile.desc.key]])

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(TemperatureProfile.load(p_object))


event.listen(TemperatureProfile.__table__, "after_create", Generic.inheritance_trigger(TemperatureProfile))


class TemperatureProfileData(Base):

    time = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    temperature_profile_id = Column(Integer, ForeignKey(TemperatureProfile.id), nullable=False)

    temperature_profile = relationship(TemperatureProfile, backref=_create_backref("TemperatureProfile"))

    __table_args__ = (
        # UniqueConstraint(time, temperature_profile_id, name="duplicate time values"),
        CheckConstraint(temperature >= physc.T0, name="temperature must be >= %s C" % physc.T0),
    )

    def __init__(self, time, temperature):
        """
        :type time: float
        :type temperature: float
        """
        super(TemperatureProfileData, self).__init__()
        self.time = time
        self.temperature = temperature

    def clone(self):
        """:rtype: TemperatureProfileData"""
        return TemperatureProfileData(self.time, self.temperature)

    def assign(self, other):
        """:type other: TemperatureProfileData"""
        self.time = other.time
        self.temperature = other.temperature

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        return cls(
            time=p_object[TemperatureProfileData.time.key],
            temperature=p_object[TemperatureProfileData.temperature.key])

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(TemperatureProfileData.load(p_object))


class Geometry(Base):

    shape = Column(GeometryShape.db_type(), nullable=False)
    type = Column(GeometryObjectType.db_type(), nullable=False)

    points = relationship("Point", order_by="Point.ord", cascade="all, delete, delete-orphan")

    __mapper_args__ = {
        "polymorphic_identity": GeometryObjectType.Geometry,
        "polymorphic_on": type
    }

    def __init__(self, shape, points):
        """
        :type shape: str
        :type points: list of Point
        """
        super(Geometry, self).__init__()
        self.shape = shape
        if points is not None:
            self.points = points
            for k, point in enumerate(self.points):
                point.ord = k

    def clone(self):
        """:rtype: Geometry"""
        return Geometry(shape=self.shape, points=[p.clone() for p in self.points])

    def add(self, point):
        """:type point: Point"""
        point.ord = len(self.points)
        self.points.append(point)

    def __sub__(self, other):
        if isinstance(other, Point):
            return Geometry(shape=self.shape, points=[p - other for p in self.points])
        return NotImplemented

    def __len__(self):
        return len(self.points)

    def __getitem__(self, item):
        return self.points[item]

    def __iter__(self):
        for point in self.points:
            yield point

    def convert2rect(self):
        """:rtype: Geometry or None"""

        if self.shape == GeometryShape.Rectangle:
            return self.clone()

        point_count = len(self.points)

        if point_count != 4:
            return None

        min_x = min(self.points, key=lambda p: p.x).x
        max_x = max(self.points, key=lambda p: p.x).x
        min_y = min(self.points, key=lambda p: p.y).y
        max_y = max(self.points, key=lambda p: p.y).y

        try:
            lb = filter(lambda p: p.x == min_x and p.y == min_y, self.points)[0]
            rt = filter(lambda p: p.x == max_x and p.y == max_y, self.points)[0]
            lt = filter(lambda p: p.x == min_x and p.y == max_y, self.points)[0]
            rb = filter(lambda p: p.x == max_x and p.y == min_y, self.points)[0]
        except IndexError:
            return None

        if lb.x == lt.x and rt.x == rb.x and lb.y == rb.y and lt.y == rt.y:
            return Geometry(shape=GeometryShape.Rectangle, points=[lb, rt])

        return None

    def convert2poly(self):
        if self.shape == GeometryShape.Polygon:
            return self.clone()
        elif self.shape == GeometryShape.Rectangle:
            lb = self.points[0]
            rt = self.points[1]
            # Check if one dimension region
            if lb.x == rt.x or lb.y == rt.y:
                return self.clone()
            points = [Point(lb.x, lb.y), Point(rt.x, lb.y), Point(rt.x, rt.y), Point(lb.x, rt.y)]
            return Geometry(shape=GeometryShape.Polygon, points=points)
        else:
            raise RuntimeError("Unknown geometry type")

    def is_rect(self):
        return self.convert2rect() is not None

    @classmethod
    def load(cls, p_object):
        shape = getattr(GeometryShape, str(p_object[Geometry.shape.key]))
        points = [Point.load(point_data) for point_data in p_object[Geometry.points.key]]
        return cls(shape, points)

    def assign(self, other):
        """:type other: Geometry"""
        if self.type != other.type:
            raise RuntimeError("Assign of Geometry objects with different types (%s, %s)" % (self.type, other.type))
        self.shape = other.shape
        self.points = [point.clone() for point in other.points]

    def export(self):
        return {
            Geometry.shape.key: str(self.shape),
            Geometry.points.key: [point.export() for point in self.points]
        }

    @classmethod
    def rectangle(cls, left, bottom, right, top):
        """
        :type left: float
        :type bottom: float
        :type right: float
        :type top: float
        """
        return cls(GeometryShape.Rectangle, [Point(left, bottom), Point(right, top)])

    @classmethod
    def polygon(cls, points):
        """
        :type points: list[tuple[float]]
        """
        return cls(GeometryShape.Polygon, [Point(*coords) for k, coords in enumerate(points)])


class Point(Base):

    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    ord = Column(Integer, nullable=False)
    geometry_id = Column(Integer, ForeignKey(Geometry.id), nullable=False)

    def __init__(self, x, y):
        """
        :type x: float
        :type y: float
        """
        super(Point, self).__init__()
        self.x = x
        self.y = y

    def __add__(self, other):
        if isinstance(other, float) or isinstance(other, int):
            return Point(self.x + other, self.y + other)
        elif isinstance(other, Point):
            return Point(self.x + other.x, self.y + other.y)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, float) or isinstance(other, int):
            return Point(self.x - other, self.y - other)
        elif isinstance(other, Point):
            return Point(self.x - other.x, self.y - other.y)
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, float) or isinstance(other, int):
            return Point(self.x * other, self.y * other)
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, float) or isinstance(other, int):
            return Point(other * self.x, other * self.y)
        return NotImplemented

    def __div__(self, other):
        if isinstance(other, float) or isinstance(other, int):
            return Point(self.x / other, self.y / other)
        return NotImplemented

    def __str__(self):
        return "Point(%f, %f)" % (self.x, self.y)

    def __iter__(self):
        return iter([self.x, self.y])

    def inside(self, polygon):
        if polygon.type == GeometryShape.Polygon:
            return point_inside_polygon(self, polygon)
        elif polygon.type == GeometryShape.Rectangle:
            return polygon.points[0].x <= self.x <= polygon.points[1].x and \
                polygon.points[0].y <= self.y <= polygon.points[1].y
        else:
            raise RuntimeError("Unknown polygon shape type")

    @classmethod
    def load(cls, p_object):
        return cls(float(p_object[Point.x.key]), float(p_object[Point.y.key]))

    def export(self):
        return {Point.x.key: self.x, Point.y.key: self.y}

    def clone(self):
        """:rtype: Point"""
        return Point(self.x, self.y)


class Mask(Generic, StandardObject):

    DB_MASK_DIMENSIONS_COUNT = 2

    icon = hybrid_property(lambda cls: "icons/Mask")

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)

    boundary_id = Column(Integer, ForeignKey(Geometry.id), nullable=False, unique=True)
    boundary = relationship(Geometry, foreign_keys=[boundary_id])

    sim_region_id = Column(Integer, ForeignKey(Geometry.id), nullable=False, unique=True)
    sim_region = relationship(Geometry, foreign_keys=[sim_region_id])

    regions = relationship(
        "Region", order_by="Region.id",
        cascade="all, delete, delete-orphan",
        foreign_keys="[Region.mask_id]")

    background = Column(Float, nullable=False)
    phase = Column(Float, nullable=False)
    clean = Column(Boolean, nullable=False)

    __mapper_args__ = {"polymorphic_identity": GenericType.Mask}

    __table_args__ = (
        CheckConstraint(background >= 0.0, name="background transmittance must be >= 0.0"),
        CheckConstraint(background <= 1.0, name="background transmittance must be <= 1.0"),
        # -------------------------------------------------
        CheckConstraint(phase >= -180.0, name="phase must be >= -180.0"),
        CheckConstraint(phase <= 180.0, name="phase must be <= 180.0")
    )

    def __init__(self, name, background, phase, boundary, sim_region, regions=None, clean=True, desc=None):
        """
        :type name: str
        :type background: float
        :type phase: float
        :type boundary: Geometry
        :type sim_region: Geometry
        :type regions: list of Region
        :type clean: bool
        :type desc: str
        """
        super(Mask, self).__init__(name, desc)
        self.background = background
        self.phase = phase
        self.boundary = boundary
        self.sim_region = sim_region
        self.clean = clean
        if regions is not None:
            self.regions = regions

    def add_region(self, region):
        """:type region: Region"""
        self.regions.append(region)
        self.clean = False

    def clone(self, name=None):
        """:rtype: MaskDatabase"""
        return Mask(
            name=self.name if name is None else name,
            desc=self.desc,
            background=self.background,
            phase=self.phase,
            boundary=self.boundary.clone(),
            sim_region=self.sim_region.clone(),
            regions=[v.clone() for v in self.regions],
            clean=self.clean)

    @property
    def dimensions(self):
        return Mask.DB_MASK_DIMENSIONS_COUNT

    # Compatibility with ConcretePluginMask
    @property
    def variables(self):
        return []

    def gds(self, stream):
        gds_lib = gdsii.library.Library(version=600, physical_unit=1.0E-9, logical_unit=0.001, name="DB")

        top_cell = gdsii.structure.Structure(self.name)

        for region in self.regions:
            try:
                layer, datatype = config.GdsLayerMapping.get_layer(region.transmittance, region.phase)
            except (KeyError, ValueError):
                return False
            points = [np.array([p.x, p.y]) for p in region.points]
            polygon = gdsii.elements.Boundary(xy=points, layer=layer, data_type=datatype)
            top_cell.append(polygon)

        bnd = self.boundary
        points = [np.array([bnd[0].x, bnd[0].y]), np.array([bnd[0].x, bnd[1].y]),
                  np.array([bnd[1].x, bnd[1].y]), np.array([bnd[1].x, bnd[0].y])]
        layer, datatype = config.GdsLayerMapping.boundary_layer()
        boundary = gdsii.elements.Boundary(xy=points, layer=layer, data_type=datatype)
        top_cell.append(boundary)

        gds_lib.append(top_cell)
        gds_lib.save(stream)

        return True

    def export(self):
        """:rtype: dict"""
        result = super(Mask, self).export()
        result.update({
            Mask.background.key: self.background,
            Mask.phase.key: self.phase,
            Mask.boundary.key: self.boundary.export(),
            Mask.sim_region.key: self.sim_region.export(),
            Mask.clean.key: self.clean,
            Mask.regions.key: [region.export() for region in self.regions]
        })
        return result

    def assign(self, other):
        """:type other: Mask"""
        super(Mask, self).assign(other)
        self.background = other.background
        self.phase = other.phase
        self.sim_region.assign(other.sim_region)
        self.boundary.assign(other.boundary)
        self.clean = other.clean
        self.regions = [region.clone() for region in other.regions]

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        return cls(
            name=str(p_object[Mask.name.key]),
            desc=str(p_object[Mask.desc.key]),
            background=float(p_object[Mask.background.key]),
            phase=float(p_object[Mask.phase.key]),
            boundary=Geometry.load(p_object[Mask.boundary.key]),
            sim_region=Geometry.load(p_object[Mask.sim_region.key]),
            clean=bool(p_object[Mask.clean.key]),
            regions=[Region.load(region_data) for region_data in p_object[Mask.regions.key]],
        )

    def parse(self, p_object):
        self.assign(Mask.load(p_object))


event.listen(Mask.__table__, "after_create", Generic.inheritance_trigger(Mask))


class Region(Geometry):

    id = Column(Integer, ForeignKey(Geometry.id), primary_key=True)

    # Self fields
    transmittance = Column(Float, nullable=False)
    phase = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint(transmittance >= 0.0), CheckConstraint(transmittance <= 1.0),
        CheckConstraint(phase >= -180.0), CheckConstraint(phase <= 180.0)
    )

    __mapper_args__ = {"polymorphic_identity": GeometryObjectType.Region}

    # Reference to the mask data
    mask_id = Column(Integer, ForeignKey(Mask.id), nullable=False)

    def __init__(self, transmittance, phase, shape, points=None):
        """
        :type transmittance: float
        :type phase: float
        :type shape: str
        :type points: list of Point or None
        """
        super(Region, self).__init__(shape, points)
        self.transmittance = transmittance
        self.phase = phase

    def export(self):
        result = super(Region, self).export()
        result.update({
            Region.transmittance.key: self.transmittance,
            Region.phase.key: self.phase,
        })
        return result

    @classmethod
    def load(cls, p_object):
        transmittance = float(p_object[Region.transmittance.key])
        phase = float(p_object[Region.phase.key])
        shape = getattr(GeometryShape, str(p_object[Geometry.shape.key]))
        points = [Point.load(point_data) for point_data in p_object[Geometry.points.key]]
        return cls(transmittance, phase, shape, points)

    def clone(self):
        """:rtype: Region"""
        points = [v.clone() for v in self.points]
        return Region(self.transmittance, self.phase, self.shape, points)


class ConcretePluginMask(ConcretePluginCommon):

    SignalsClass = SignalsMeta.CreateSignalsClass("ConcretePluginMask", ["background", "phase"], db_columns=False)

    def __init__(self, abstract, values=None):
        """
        :type abstract: orm.AbstractPluginMask
        :type values: list of float
        """
        super(ConcretePluginMask, self).__init__(abstract, values)
        self.__mask_struct = pcpi.mask_t()
        self._base.regenerate(self.__mask_struct, *self.values)
        self.__transmittance = self.__mask_struct.boundary.transmittance
        self.__phase = self.__mask_struct.boundary.phase

    dimensions = property(lambda self: self._base.dims)

    @property
    def boundary(self):
        self._base.regenerate(self.__mask_struct, *self.values)
        self.__mask_struct.boundary.transmittance = self.__transmittance
        self.__mask_struct.boundary.phase = self.__phase
        points = self.__mask_struct.boundary.points
        if self._base.dims == 1:
            boundary = Geometry.rectangle(points[0].x, points[0].y, points[1].x, points[1].y)
        else:
            boundary = Geometry.rectangle(points[0].x, points[0].y, points[2].x, points[2].y)
        return boundary

    @property
    def regions(self):
        self._base.regenerate(self.__mask_struct, *self.values)
        self.__mask_struct.boundary.transmittance = self.__transmittance
        self.__mask_struct.boundary.phase = self.__phase
        # Returns regions generator
        for k in xrange(self.__mask_struct.regions_count):
            r = self.__mask_struct.regions[k]
            yield Region(
                transmittance=r.transmittance, phase=r.phase, shape=GeometryShape.Polygon,
                points=[Point(r.points[k].x, r.points[k].y) for k in xrange(r.length)])

    def _get_background(self):
        return self.__mask_struct.boundary.transmittance

    def _set_background(self, value):
        if self.__mask_struct.boundary.transmittance != value:
            self.__mask_struct.boundary.transmittance = self.__transmittance = value
            self.signals[ConcretePluginMask.background].emit()

    def _get_phase(self):
        return self.__mask_struct.boundary.phase

    def _set_phase(self, value):
        if self.__mask_struct.boundary.phase != value:
            self.__mask_struct.boundary.phase = self.__phase = value
            self.signals[ConcretePluginMask.phase].emit()

    background = AttributedProperty(_get_background, _set_background, key="background", dtype=Float)
    phase = AttributedProperty(_get_phase, _set_phase, key="phase", dtype=Float)

    def export(self):
        result = self._base.export()
        result.update(super(ConcretePluginMask, self).export())
        result.update({
            ConcretePluginMask.background.key: self.background,
            ConcretePluginMask.phase.key: self.phase,
        })
        return result

    @classmethod
    def load(cls, p_object, abstract=None):
        """:type p_object: dict"""
        abstract_base = AbstractPluginMask.load(p_object)
        result = super(ConcretePluginMask, cls).load(p_object, abstract_base)
        result.background = p_object[ConcretePluginMask.background.key]
        result.phase = p_object[ConcretePluginMask.phase.key]
        return result

    def clone(self):
        result = super(ConcretePluginMask, self).clone()
        result.background = self.background
        result.phase = self.phase
        return result


class AbstractPluginMask(Generic, PluginObject):

    icon = hybrid_property(lambda cls: "icons/Numerics")

    cpi = pcpi.mask_plugin_t

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)
    dims = Column(Integer, nullable=False)
    prms = relationship(
        "AbstractPluginMaskPrm",
        order_by="AbstractPluginMaskPrm.ord",
        cascade="all, delete, delete-orphan")

    __mapper_args__ = {"polymorphic_identity": GenericType.AbstractPluginMask}

    def __init__(self, name, prms, dims, desc=None):
        """
        :param str name: Mask plugin name
        :param list of AbstractPluginMaskPrm prms: Parameters descriptors of the mask plugin
        :param int dims: 1 or 2 dimensions mask
        :param str or None desc: Description of the plugin
        """
        super(AbstractPluginMask, self).__init__(name, desc)
        self.prms = prms
        self.dims = dims
        self._mask_entry = None
        """:type: mask_plugin_t"""

    def produce(self, values=None):
        """
        :type values: list of float
        :rtype: ConcretePluginMask
        """
        return ConcretePluginMask(self, values)

    @property
    def entry(self):
        """:rtype: mask_t"""
        if not hasattr(self, "_mask_entry") or self._mask_entry is None:
            self._mask_entry = pcpi.PLUGIN_REGISTRY.get_by_id(self.id).entry
        return self._mask_entry

    def regenerate(self, mask_struct, *values):
        """:type mask_struct: pcpi.mask_t"""
        array = ctypes.c_double * len(self.prms)
        # noinspection PyCallingNonCallable
        if self.entry.create(ctypes.byref(mask_struct), array(*values)):
            raise RuntimeError("Error during plugin mask regeneration")

    def assign(self, other):
        raise NotImplementedError(METHOD_NONE_IMPLEMENTED)

    def clone(self, name=None):
        """
        :type name: str or None
        :rtype: AbstractPluginMask
        """
        if name is not None:
            raise NotImplementedError(METHOD_NONE_IMPLEMENTED)

        prms = [v.clone() for v in self.prms]
        return AbstractPluginMask(self.name, prms, self.mask_type, self.desc)

    @classmethod
    def load(cls, p_object):
        return pcpi.PLUGIN_REGISTRY.get_by_name(p_object[Generic.name.key]).record


class AbstractPluginMaskPrm(AbstractPluginParameter, Base):

    name = Column(String, nullable=False)
    ord = Column(Integer, nullable=False)
    defv = Column(Float)
    max = Column(Float)
    min = Column(Float)
    plugin_mask_id = Column(Integer, ForeignKey(AbstractPluginMask.id, ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint(ord, plugin_mask_id, name="duplicate order arguments number"),
        # -------------------------------------------------
        # TODO: Check parameters
        # CheckConstraint(defv > min, "default value must greater than min values"),
        # CheckConstraint(defv < max, "default value must lower than max values"),
        # CheckConstraint(max > min, name="max must be > min argument value"),
    )


class DeveloperInterface(Generic):

    icon = hybrid_property(lambda cls: "icons/Development")
    __text_type__ = "Abstract"

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)

    __mapper_args__ = {"polymorphic_identity": None}

    def __init__(self, name, desc):
        super(DeveloperInterface, self).__init__(name, desc)

    def rate(self, pac, depth):
        """
        :type pac: numpy.ndarray or list of float
        :type depth: numpy.ndarray or list of float
        :rtype: numpy.ndarray
        """
        raise NotImplementedError(METHOD_NONE_IMPLEMENTED)

    def assign(self, other):
        """:type other: DeveloperInterface"""
        if not DeveloperInterface in self.__class__.mro():
            raise NotImplementedError(METHOD_NONE_IMPLEMENTED)
        super(DeveloperInterface, self).assign(other)

    def clone(self, name=None):
        """
        :type name: str
        :rtype: DeveloperInterface
        """
        if not DeveloperInterface in self.__class__.mro():
            raise NotImplementedError(METHOD_NONE_IMPLEMENTED)
        return super(DeveloperInterface, self).clone()

    def __str__(self):
        return "%s [%s]" % (self.name, self.__text_type__)

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        if p_object[DeveloperInterface.type.key] == str(GenericType.DeveloperExpr):
            return DeveloperExpr.load(p_object)
        elif p_object[DeveloperInterface.type.key] == str(GenericType.DeveloperSheet):
            return DeveloperSheet.load(p_object)
        else:
            raise UnknownObjectTypeError(p_object[DeveloperInterface.type.key])

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(type(self).load(p_object))

    def convert2core(self):
        raise NotImplementedError(METHOD_NONE_IMPLEMENTED)


class Resist(Generic, StandardObject, DeleteHook):

    icon = hybrid_property(lambda cls: "icons/Resist")

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)

    # Compare with ExposureParameter and PebParameters where foreign keys not in resist table developer must be in
    # resist table because for one developer several resist may exists. But for Exposure and PEB connection is one-one.
    # Also it's simpler to delete orphan exposure and peb parameter only using DB level (ON DELETE CASCADE)
    developer_id = Column(Integer, ForeignKey(DeveloperInterface.id))
    developer = relationship(DeveloperInterface, foreign_keys=[developer_id])
    """:type: DeveloperInterface"""

    exposure = relationship("ExposureParameters", cascade="all, delete-orphan", uselist=False)
    """:type: ExposureParameters"""
    peb = relationship("PebParameters", cascade="all, delete-orphan", uselist=False)
    """:type: PebParameters"""

    __mapper_args__ = {"polymorphic_identity": GenericType.Resist}

    def __init__(self, name, comment, exposure, peb, developer):
        """
        :type name: str
        :type comment: str
        :type exposure: ExposureParameters
        :type peb: PebParameters
        :type developer: DeveloperInterface
        """
        super(Resist, self).__init__(name, comment)
        self.exposure = exposure
        self.peb = peb
        self.developer = developer

    def on_delete(self, session):
        """
        :type session: Session
        :return: Query of the objects to being delete
        :rtype: Query
        """
        # Select only deleted and temporary development expression
        condition = and_(DeveloperExpr.id == self.developer_id, DeveloperExpr.temporary == 1)
        return session.query(DeveloperExpr).filter(condition)

    def assign(self, other, developer=None):
        """
        :type other: Resist
        :type developer: DeveloperInterface
        """
        super(Resist, self).assign(other)
        self.developer = other.developer if developer is None else developer
        self.exposure.assign(other.exposure)
        self.peb.assign(other.peb)

    def clone(self, name=None, developer=None):
        """
        :type name: str
        :type developer: DeveloperInterface
        :rtype: Resist
        """
        exposure = self.exposure.clone()
        peb = self.peb.clone()

        if developer is None:
            if isinstance(self.developer, DeveloperExpr):
                developer = self.developer.clone()
            elif isinstance(self.developer, DeveloperSheet):
                developer = self.developer
            elif self.developer is None:
                developer = None
            else:
                raise TypeError("Unknown developer %s type: %s" % (self.developer.name, type(self.developer).__name__))

        name = self.name if name is None else name

        return Resist(name, self.desc, exposure, peb, developer)

    def export(self):
        result = super(Resist, self).export()
        result.update({
            Resist.exposure.key: self.exposure.export(),
            Resist.peb.key: self.peb.export(),
            Resist.developer.key: self.developer.export()
        })
        return result

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        return cls(
            name=p_object[Resist.name.key],
            comment=p_object[Resist.desc.key],
            exposure=ExposureParameters.load(p_object[Resist.exposure.key]),
            peb=PebParameters.load(p_object[Resist.peb.key]),
            developer=DeveloperInterface.load(p_object[Resist.developer.key]))

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(Resist.load(p_object))


event.listen(Resist.__table__, "after_create", Generic.inheritance_trigger(Resist))


class ExposureParameters(Base):

    name = "Exposure Parameters"

    resist_id = Column(Integer, ForeignKey(Resist.id, ondelete="CASCADE"), unique=True, nullable=False)

    wavelength = Column(Float, nullable=False, precision=Precision.wavelength)
    a = Column(Float, nullable=False, precision=Precision.dill)
    b = Column(Float, nullable=False, precision=Precision.dill)
    c = Column(Float, nullable=False, precision=Precision.dill)
    n = Column(Float, nullable=False, precision=Precision.refractive_index)

    __table_args__ = (
        CheckConstraint(wavelength >= 0.0, name="Wavelength must be >= 0.0"),
        CheckConstraint(a >= 0.0, name="Dill A must be >= 0.0"),
        CheckConstraint(b >= 0.0, name="Dill B must be >= 0.0"),
        CheckConstraint(c >= 0.0, name="Dill C must be >= 0.0"),
        CheckConstraint(n >= 0.0, name="Unexposed n must be >= 0.0"),
    )

    def __init__(self, wavelength, a, b, c, n):
        """
        :param float wavelength: Wavelength at which resist was calibrated
        :param float a: Exposure Dill ABC model parameter A
        :param float b: Exposure Dill ABC model parameter B
        :param float c: Exposure Dill ABC model parameter C
        :param float n: Real part of refractive index of unexposed resist
        """
        super(ExposureParameters, self).__init__()
        self.wavelength = wavelength
        self.a = a
        self.b = b
        self.c = c
        self.n = n

    def assign(self, other):
        """:type other: ExposureParameters"""
        self.wavelength = other.wavelength
        self.a = other.a
        self.b = other.b
        self.c = other.c
        self.n = other.n

    def clone(self):
        """:rtype: ExposureParameters"""
        return ExposureParameters(self.wavelength, self.a, self.b, self.c, self.n)

    def export(self):
        return {
            ExposureParameters.wavelength.key: self.wavelength,
            ExposureParameters.a.key: self.a,
            ExposureParameters.b.key: self.b,
            ExposureParameters.c.key: self.c,
            ExposureParameters.n.key: self.n
        }

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        return cls(
            wavelength=p_object[ExposureParameters.wavelength.key],
            a=p_object[ExposureParameters.a.key],
            b=p_object[ExposureParameters.b.key],
            c=p_object[ExposureParameters.c.key],
            n=p_object[ExposureParameters.n.key])

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(ExposureParameters.load(p_object))

    def convert2core(self):
        return oplc.ExposureResistModel(self.wavelength, self.a, self.b, self.c, self.n)


class PebParameters(Base):

    name = "PEB Parameters"

    resist_id = Column(Integer, ForeignKey(Resist.id, ondelete="CASCADE"), unique=True, nullable=False)

    ea = Column(Float, nullable=False, precision=3)
    ln_ar = Column(Float, nullable=False, precision=3)

    def __init__(self, ea, ln_ar):
        """
        :type ea: float
        :type ln_ar: float
        """
        super(PebParameters, self).__init__()
        self.ea = ea
        self.ln_ar = ln_ar

    def diffusivity(self, temp):
        """
        Calculate diffusivity for graph display.
        Note: Real sigma to PEB convolution should be calculated using:
        sqrt(2*kt*time), where kt is the result of this function.

        :param float or list of float or numpy.ndarray temp: Temperature in C
        :rtype: float
        """
        if isinstance(temp, list):
            temp = np.array(temp, dtype=float)
        tempk = temp - physc.T0
        return np.exp(self.ln_ar - self.ea/(physc.R*tempk))

    def diffusion_length(self, temp, time):
        """
        :type temp: float
        :type time: float
        """
        return np.sqrt(2*self.diffusivity(temp)*time)

    def assign(self, other):
        """:type other: PebParameters"""
        self.ln_ar = other.ln_ar
        self.ea = other.ea

    def clone(self):
        """:rtype: PebParameters"""
        return PebParameters(self.ea, self.ln_ar)

    def export(self):
        return {
            PebParameters.ea.key: self.ea,
            PebParameters.ln_ar.key: self.ln_ar
        }

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        return cls(
            ea=p_object[PebParameters.ea.key],
            ln_ar=p_object[PebParameters.ln_ar.key])

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(ExposureParameters.load(p_object))

    def convert2core(self):
        return oplc.PebResistModel(self.ea, self.ln_ar)


class DeveloperSheet(DeveloperInterface, StandardObject):

    id = Column(Integer, ForeignKey(DeveloperInterface.id), primary_key=True)
    is_depth = Column(Boolean, nullable=False)
    data = relationship("DeveloperSheetData", order_by="DeveloperSheetData.pac", cascade="all, delete-orphan")

    __text_type__ = "Sheet"

    __mapper_args__ = {"polymorphic_identity": GenericType.DeveloperSheet}

    def __init__(self, name, is_depth, data, desc=None):
        """
        :type name: str
        :type is_depth: bool
        :type data: list of DeveloperSheetData
        """
        super(DeveloperSheet, self).__init__(name, desc)
        self.is_depth = is_depth
        self.data = data

    def rate(self, pac=None, depth=None):
        """
        :type pac: numpy.ndarray or list of float or None
        :type depth: numpy.ndarray or list of float or None
        :rtype: numpy.ndarray
        """

        native_xy = True

        pacs, depths, rates = [], [], []
        for item in self.data:
            pacs.append(item.pac)
            depths.append(item.depth if self.is_depth else 0.0)
            rates.append(item.rate)

        if pac is None or depth is None:
            pac = np.unique(np.array(pacs))
            depth = np.unique(np.array(depths))
        else:
            native_xy = False
            if not self.is_depth:
                if callable(depth) and (depth is max or depth is min):
                    depth = np.zeros([1, 1])
                else:
                    depth = np.zeros(len(depth))
            else:
                if callable(depth) and (depth is max or depth is min):
                    depth = np.array(depth(self.data, key=lambda v: v.depth).depth)
                else:
                    depth = np.array(depth)
            pac = np.array(pac)

        if len(depth) > 1:
            # This shit: y[:, None] - is transpose
            result = griddata((pacs, depths), rates, (pac[None, :], depth[:, None]), method='linear', fill_value=0.0)
        else:
            depth_cond = np.where(np.asarray(depths) == depth[0])
            pacs = np.asarray(pacs)[depth_cond]
            rates = np.asarray(rates)[depth_cond]
            result = np.ndarray([len(pac), 1])
            result[:, 0] = interp1d(pacs, rates)(pac)

        if native_xy:
            return pac, depth, result

        return result

    def assign(self, other):
        """:type other: DeveloperSheet"""
        super(DeveloperSheet, self).assign(other)
        self.is_depth = other.is_depth
        self.data = [v.clone() for v in other.data]

    def clone(self, name=None):
        """:rtype: DeveloperSheet"""
        name = self.name if name is None else name
        data = [v.clone() for v in self.data]
        return DeveloperSheet(name, self.is_depth, data, self.desc)

    def export(self):
        result = super(DeveloperSheet, self).export()
        result.update({
            DeveloperSheet.is_depth.key: self.is_depth,
            DeveloperSheet.data.key: [data.export() for data in self.data]
        })
        return result

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        data = [DeveloperSheetData.load(data) for data in p_object[DeveloperSheet.data.key]]
        return cls(
            name=p_object[DeveloperSheet.name.key],
            desc=p_object[DeveloperSheet.desc.key],
            is_depth=p_object[DeveloperSheet.is_depth.key],
            data=data)

    def convert2core(self):
        if self.is_depth:
            pac, depth, values = self.rate()
            return oplc.ResistRateModelDepthSheet(pac, depth, np.asfortranarray(values))
        else:
            pac, _, values = self.rate()
            return oplc.ResistRateModelSheet(pac, values[:, 0])


event.listen(DeveloperSheet.__table__, "after_create", Generic.inheritance_trigger(DeveloperSheet))


_dev_rate_depth_dependency = DDL("""
CREATE TRIGGER dev_rate_depth_dependency
BEFORE INSERT ON DeveloperSheetData
FOR EACH ROW
WHEN (
  CASE
    EXISTS (
      SELECT NULL FROM DeveloperSheet
      WHERE DeveloperSheet.id == new.developer_sheet_id
            AND DeveloperSheet.is_depth == 1
    )
  WHEN 1 THEN
    new.depth IS NULL
  ELSE
    new.depth IS NOT NULL
  END
)
BEGIN
  SELECT RAISE( ABORT, 'Development rate depth dependency failed' );
END;""")


class DeveloperSheetData(Base):

    pac = Column(Float, nullable=False)
    rate = Column(Float, nullable=False)  # in nm/s
    depth = Column(Float)

    developer_sheet_id = Column(Integer, ForeignKey(DeveloperSheet.id, ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint(pac, depth, developer_sheet_id, name="duplicate PAC, depth values"),
        # -------------------------------------------------
        CheckConstraint(pac >= 0.0, name="PAC must be >= 0.0"),
        CheckConstraint(pac <= 1.0, name="PAC must be <= 1.0"),
        # -------------------------------------------------
        CheckConstraint(rate >= 0.0, name="developer rate must be >= 0.0"),
    )

    def __init__(self, pac, rate, depth=None):
        super(DeveloperSheetData, self).__init__()
        self.pac = float(pac)
        self.rate = float(rate)
        self.depth = float(depth) if depth is not None else None

    def clone(self):
        """:rtype: DeveloperSheetData"""
        return DeveloperSheetData(self.pac, self.rate, self.depth)

    def export(self):
        return {
            DeveloperSheetData.pac.key: self.pac,
            DeveloperSheetData.rate.key: self.rate,
            DeveloperSheetData.depth.key: self.depth
        }

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        return cls(
            pac=p_object[DeveloperSheetData.pac.key],
            rate=p_object[DeveloperSheetData.rate.key],
            depth=p_object[DeveloperSheetData.depth.key])

    def parse(self, p_object):
        """:type p_object: dict"""
        self.assign(DeveloperSheetData.load(p_object))


# CREATE TRIGGER dev_rate_depth_dependency
event.listen(DeveloperSheetData.__table__, "after_create", _dev_rate_depth_dependency)


class DevelopmentModel(Generic, PluginObject):

    icon = hybrid_property(lambda cls: "icons/Numerics")

    cpi = pcpi.dev_model_t

    id = Column(Integer, ForeignKey(Generic.id), primary_key=True)
    prolith_id = Column(Integer, unique=True)
    args = relationship("DevelopmentModelArg", order_by="DevelopmentModelArg.ord")

    __mapper_args__ = {"polymorphic_identity": GenericType.DevelopmentModel}

    def __init__(self, name, args, desc=None, prolith_id=None):
        """
        :param str name: Development model name
        :param list of DevelopmentModelArg args: Arguments descriptors of the model
        :param str or None desc: Description of the model
        :param int or None prolith_id: Prolith development model identifier (to link model with it's standard models)
        """
        super(DevelopmentModel, self).__init__(name, desc)
        self.args = args
        self.prolith_id = prolith_id
        self._rate_entry = None

    @property
    def entry(self):
        if not hasattr(self, "_rate_entry") or self._rate_entry is None:
            self._rate_entry = pcpi.PLUGIN_REGISTRY.get_by_id(self.id).entry
        return self._rate_entry

    def calc(self, pac, depth, *values):
        array = ctypes.c_double * len(self.args)
        # noinspection PyTypeChecker,PyCallingNonCallable
        return self.entry.expr(pac, depth, array(*values))

    def assign(self, other):
        raise NotImplementedError(METHOD_NONE_IMPLEMENTED)

    def clone(self, name=None):
        """
        :type name: str or None
        :rtype: DevelopmentModel
        """
        if name is not None:
            raise NotImplementedError(METHOD_NONE_IMPLEMENTED)

        args = [v.clone() for v in self.args]
        return DevelopmentModel(self.name, args, self.desc, self.prolith_id)


class DevelopmentModelArg(AbstractPluginParameter, Base):

    name = Column(String, nullable=False)
    ord = Column(Integer, nullable=False)
    defv = Column(Float)
    max = Column(Float)
    min = Column(Float)
    development_model_id = Column(Integer, ForeignKey(DevelopmentModel.id, ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint(ord, development_model_id, name="duplicate order arguments number"),
        # -------------------------------------------------
        # TODO: Check parameters
        # CheckConstraint(defv > min, "default value must greater than min values"),
        # CheckConstraint(defv < max, "default value must lower than max values"),
        # CheckConstraint(max > min, name="max must be > min argument value"),
    )


class DeveloperExpr(DeveloperInterface, StandardObject):

    id = Column(Integer, ForeignKey(DeveloperInterface.id), primary_key=True)
    model_id = Column(Integer, ForeignKey(DevelopmentModel.id, ondelete="CASCADE"))

    __text_type__ = "Expression"

    model = relationship(DevelopmentModel, foreign_keys=[model_id])

    surface_rate = Column(Float, nullable=False)
    inhibition_depth = Column(Float, nullable=False)

    #TODO: Create trigger or other controller on this column (see description in __init__)
    temporary = Column(Boolean, nullable=False)

    #TODO: order_by
    object_values = relationship("DeveloperExprArgValue", cascade="all, delete-orphan")
    """:type: list of DeveloperExprArgValue"""

    values = association_proxy("object_values", "value")

    __mapper_args__ = {"polymorphic_identity": GenericType.DeveloperExpr}

    def __init__(self, name, model, values=None, surface_rate=1.0, inhibition_depth=10.0, desc=None, temporary=False):
        """
        :param str name: Name of the developer model
        :param DevelopmentModel model: Definition of the model
        :param list of float values or None: Model argument values (if None then default will be used)
        :param float surface_rate: Relative surface rate
        :param float inhibition_depth: Inhibition depth (nm)
        :param str desc: Description of the model
        :param bool temporary: If this parameter is True - then Developer will be deleted as soon as according
                               resist removed. Also in this case only one resist can be linked with this Developer
        """
        super(DeveloperExpr, self).__init__(name, desc)
        self.model = model
        if values is None:
            values = [arg.default for arg in model.args]
        self.values = values
        self.surface_rate = surface_rate
        self.inhibition_depth = inhibition_depth
        self.temporary = temporary

    def rate(self, pac, depth):
        """
        Return rates of the development model

        :param numpy.ndarray or list of float pac: Photo-active component concentration
        :param numpy.ndarray or list of float depth: Depth into resist
        :return: rate on pac-depth grid
        :rtype: numpy.ndarray
        """
        result = np.ndarray([len(pac), len(depth)])
        pac_depth = cartesian(pac, depth)
        rows = range(len(pac))
        cols = range(len(depth))
        rc = cartesian(rows, cols)
        for (r, c), (pac, depth) in zip(rc, pac_depth):
            result[r, c] = self.model.calc(pac, depth, *self.values)
        return result

    def change_model(self, model):
        """:type model: DevelopmentModel"""
        if self.model != model:
            self.model = model
            self.values = [arg.default for arg in model.args]
            logging.info("Set model %s to %s: %s" % (self.model, self.name, self.values))

    def assign(self, other):
        """:type other: DeveloperExpr"""
        super(DeveloperExpr, self).assign(other)
        self.model = other.model
        self.surface_rate = other.surface_rate
        self.inhibition_depth = other.inhibition_depth
        self.temporary = other.temporary
        self.values = [float(v) for v in other.values]

    def clone(self, name=None):
        """:rtype: DeveloperExpr"""
        name = self.name if name is None else name
        values = [float(v) for v in self.values]
        return DeveloperExpr(name, self.model, values, self.surface_rate,
                             self.inhibition_depth, self.desc, self.temporary)

    def export(self):
        result = super(DeveloperExpr, self).export()
        # noinspection PyUnresolvedReferences
        result.update({
            DeveloperExpr.model.key: self.model.name,
            DeveloperExpr.surface_rate.key: self.surface_rate,
            DeveloperExpr.inhibition_depth.key: self.inhibition_depth,
            DeveloperExpr.temporary.key: self.temporary,
            DeveloperExpr.object_values.key: [float(v) for v in self.values]
        })
        return result

    @classmethod
    def load(cls, p_object):
        """:type p_object: dict"""
        model = pcpi.PLUGIN_REGISTRY.get_by_name(p_object[DeveloperExpr.model.key]).record
        # noinspection PyUnresolvedReferences
        return cls(
            name=p_object[DeveloperExpr.name.key],
            desc=p_object[DeveloperExpr.desc.key],
            model=model,
            temporary=p_object[DeveloperExpr.temporary.key],
            surface_rate=p_object[DeveloperExpr.surface_rate.key],
            inhibition_depth=p_object[DeveloperExpr.inhibition_depth.key],
            values=p_object[DeveloperExpr.object_values.key])

    def convert2core(self):
        return oplc.ResistRateModelExpression(self.model.entry.expr, self.values)


event.listen(DeveloperExpr.__table__, "after_create", Generic.inheritance_trigger(DeveloperExpr))


class DeveloperExprArgValue(Base):

    value = Column(Float, nullable=False)

    development_model_arg_id = Column(Integer, ForeignKey(DevelopmentModelArg.id, ondelete="CASCADE"), unique=True)
    developer_expr_id = Column(Integer, ForeignKey(DeveloperExpr.id, ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint(development_model_arg_id, developer_expr_id, name="duplicate developer expression arguments"),
    )

    def __init__(self, value):
        """:type value: float"""
        super(DeveloperExprArgValue, self).__init__()
        # TODO: development_model_arg_id is not fill because association_proxy field
        # (check whether this link is really required)
        self.value = value

    def clone(self):
        """:rtype: DeveloperExprArgValue"""
        return DeveloperExprArgValue(self.value)

    def assign(self, other):
        """:type other: DeveloperExprArgValue"""
        self.value = other.value

    @classmethod
    def load(cls, p_object):
        """:type p_object: float"""
        return cls(p_object)

    def parse(self, p_object):
        """:type p_object: float"""
        self.value = p_object


class Info(Base):

    version = Column(Integer, nullable=False)
    appname = Column(String, nullable=False)
    created = Column(DateTime, nullable=False)

    def __init__(self, version):
        super(Info, self).__init__()
        self.version = version
        self.appname = APPLICATION_NAME
        self.created = datetime.datetime.now()

    def __str__(self):
        print self.appname, self.version, self.created
        return "%s DB v.%d created %s" % (self.appname, self.version, self.created)


tables = Base.metadata.tables
""":type: dict from str to Table"""


def _enum_tables_of(base):
    """:rtype: __generator[Generic]"""
    for table_name in tables.keys():
        table_class = globals().get(table_name, None)
        if table_class is not None and issubclass(table_class, base):
            yield table_class


standard_tables = list(_enum_tables_of(StandardObject))
plugin_tables = list(_enum_tables_of(PluginObject))


def get_table_by_plugin(plugin):
    # noinspection PyUnresolvedReferences
    _tables = [table for table in plugin_tables if table.cpi.plugin_id == plugin.type]
    if not _tables:
        raise KeyError("Plugin table not found")
    elif len(_tables) > 1:
        raise RuntimeError("Tables count to one plugin must be == 1")
    return _tables[0]