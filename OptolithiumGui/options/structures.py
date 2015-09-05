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

import bson
import os
import numpy
import logging as module_logging

from pcpi import PluginNotFoundError
from resources import Resources
from options.common import Abstract, Variable, Numeric, Enum, ReportTemplates, AttributedProperty
from qt import QtCore, connect, Slot, disconnect, Signal, GlobalSignals
from database import orm
from metrics import VARIATE_HEIGHT_FALSE, VARIATE_HEIGHT_TRUE, MASK_CLEAR, MASK_OPAQUE

import config
import helpers

import optolithiumc as oplc


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.DEBUG)
helpers.logStreamEnable(logging)


PARAMETRIC_NAME = "Parametric"
RESIST_TYPE = "Resist"
LAYER_TYPE = "Layer"
SUBSTRATE_TYPE = "Substrate"


def get_field(p_object, abstract_field):
    if hasattr(abstract_field, "get_concrete"):
        return abstract_field.get_concrete(p_object)
    else:
        return abstract_field


class OptionsLoadErrors(Exception):

    def __init__(self, errors, p_object):
        self.errors = errors
        self.p_object = p_object

    def __iter__(self):
        return self.errors.__iter__()


class OptionsParseError(Exception):
    pass


class AbstractReportOption(object):

    icon = None

    @property
    def identifier(self):
        return self.__class__.__name__

    def report_header(self):
        return ReportTemplates.header % {"icon": Resources(self.icon, "url"), "name": self.identifier, "body": "%s"}

    def report(self):
        raise NotImplementedError


class AbstractOptionsBase(QtCore.QObject, AbstractReportOption):

    changed = Signal()

    def __init__(self, *args, **kwargs):
        super(AbstractOptionsBase, self).__init__(*args, **kwargs)
        self.__saved = True
        self.__simulated = True

    def _connect_signals(self):
        for var in self.__dict__.values():
            if isinstance(var, Variable):
                connect(var.signals[Abstract], self.onOptionChanged)
        connect(self.changed, GlobalSignals.onChanged)

    def _set_composite_variable(self, name, value):
        vname = "_%s__%s" % (self.__class__.__name__, name)
        if getattr(self, vname) is not None:
            for variable in getattr(self, vname).variables:
                # print(variable.signals[Abstract])
                disconnect(variable.signals[Abstract], self.onOptionChanged)

        setattr(self, vname, value)

        if value is not None:
            for variable in getattr(self, vname).variables:
                connect(variable.signals[Abstract], self.onOptionChanged)

        self.onOptionChanged()

    # noinspection PyPep8Naming
    @Slot()
    def onOptionChanged(self):
        # emit_required = self.__saved or self.__simulated
        # sender_str = " by %s" % self.sender() if self.sender() else ""
        # logging.info("Options <%s> has been changed (saved = %s simulated = %s)%s" %
        #              (self.identifier, self.__saved, self.__simulated, sender_str))
        self.__saved = False
        self.__simulated = False
        # if emit_required:
        self.changed.emit()

    @property
    def is_saved(self):
        return self.__saved

    @property
    def is_simulated(self):
        return self.__simulated

    def saved(self, emit=True):
        # logging.info("Save options, emit = %s" % emit)
        self.__saved = True
        if emit:
            self.changed.emit()

    def simulated(self):
        self.__simulated = True
        # if emit:
        #     self.changed.emit()

    @classmethod
    def default(cls):
        raise NotImplementedError

    @classmethod
    def empty(cls):
        raise NotImplementedError

    @classmethod
    def load(cls, data):
        raise NotImplementedError

    def assign(self, other):
        """:type other: AbstractOptionsBase"""
        self.__saved = other.__saved
        self.__simulated = other.__simulated

    def export(self):
        raise NotImplementedError


class Numerics(AbstractOptionsBase):

    icon = "icons/Numerics"

    scalar = "Scalar"
    vector = "Vector"

    def __init__(self, model, speed, grid_xy, grid_z):
        super(Numerics, self).__init__()

        self.calculation_model = Variable(
            Enum(variants=[Numerics.scalar, Numerics.vector]),
            value=model, name="Model")

        self.speed_factor = Variable(
            Numeric(vmin=0, vmax=10, dtype=int),
            value=speed, name="SpeedFactor")

        self.grid_xy = Variable(
            Numeric(vmin=1.0, vmax=50.0, dtype=float, precision=1),
            value=grid_xy, name="GridXY")

        self.grid_z = Variable(
            Numeric(vmin=1.0, vmax=50.0, dtype=float, precision=1),
            value=grid_z, name="GridZ")

        self._connect_signals()

    @property
    def source_stepxy(self):
        return config.SOURCE_SHAPE_STEP_MAP[self.speed_factor.value]

    def assign(self, other):
        """:type other: Numerics"""
        self.calculation_model.value = other.calculation_model.value
        self.speed_factor.value = other.speed_factor.value
        self.grid_xy.value = other.grid_xy.value
        self.grid_z.value = other.grid_z.value

    @classmethod
    def default(cls):
        return cls(model=Numerics.scalar, speed=5, grid_xy=5.0, grid_z=5.0)

    @classmethod
    def empty(cls):
        return cls(model=None, speed=None, grid_xy=None, grid_z=None)

    @classmethod
    def load(cls, data):
        return cls.empty().parse(data)

    def report(self):
        template = self.report_header()
        body = "\n".join([
            self.calculation_model.report(),
            self.speed_factor.report(),
            self.grid_xy.report(),
            self.grid_z.report()
        ])
        return template % body

    def export(self):
        return {
            self.calculation_model.name: self.calculation_model.value,
            self.speed_factor.name: self.speed_factor.value,
            self.grid_xy.name: self.grid_xy.value,
            self.grid_z.name: self.grid_z.value
        }

    def parse(self, data):
        """:type data: dict"""
        self.calculation_model.value = data[self.calculation_model.name]
        self.speed_factor.value = data[self.speed_factor.name]
        self.grid_xy.value = data[self.grid_xy.name]
        self.grid_z.value = data[self.grid_z.name]
        return self


class WaferStackLayer(AbstractReportOption):

    def __init__(self, material, is_parametric=False):
        """
        :type material: orm.Generic
        :type is_parametric: bool
        """
        self._material = material
        self._is_parametric = is_parametric

    def connect_with(self, slot):
        raise NotImplementedError

    def disconnect_from(self, slot):
        raise NotImplementedError

    @property
    def is_parametric(self):
        return self._is_parametric

    @staticmethod
    def _create_parametric_material(wavelength, real, imag):
        """
        :type wavelength: float
        :type real: float
        :type imag: float
        """
        material = orm.Material(
            name=PARAMETRIC_NAME,
            data=[orm.MaterialData(wavelength=wavelength, real=real, imag=imag)],
            desc="Parametric material n=%.2f k=+%.2fi @ %.0f nm" % (real, imag, wavelength))
        return material

    @classmethod
    def default_parametric(cls, wavelength):
        """:rtype: WaferStackLayer"""
        raise NotImplementedError

    @classmethod
    def db_stored(cls, material, *args):
        """
        :type material: orm.Material
        :rtype: WaferStackLayer
        """
        raise NotImplementedError

    @property
    def wavelength(self):
        """:rtype: list of float"""
        raise NotImplementedError

    @property
    def refraction(self):
        """
        :return: Refractive index real, image lists
        :rtype: list of float, list of float
        """
        raise NotImplementedError

    @property
    def type(self):
        """:rtype: str"""
        raise NotImplementedError

    def refraction_at(self, wavelength):
        wvl = self.wavelength
        real, imag = self.refraction
        re = numpy.interp(wavelength, wvl, real)
        im = numpy.interp(wavelength, wvl, imag)
        return re, im

    def export(self):
        raise NotImplementedError

    @classmethod
    def load(cls, data):
        raise NotImplementedError

    def convert2core(self):
        raise NotImplementedError


class MaterialLayer(WaferStackLayer):
    """Class describe wafer stack layer which has predefined material data (for example Substrate)"""

    icon = "icons/Material"

    SignalsClass = orm.SignalsMeta.CreateSignalsClass("MaterialLayer", ["real", "imag"], db_columns=False)

    def __init__(self, material, is_parametric=False):
        """
        :type material: orm.Material
        :type is_parametric: bool
        """
        self.__signals = self.__class__.SignalsClass(self)
        WaferStackLayer.__init__(self, material, is_parametric)

    def connect_with(self, slot):
        if self.is_parametric:
            connect(self.signals[MaterialLayer.real], slot)
            connect(self.signals[MaterialLayer.imag], slot)

    def disconnect_from(self, slot):
        if self.is_parametric:
            disconnect(self.signals[MaterialLayer.real], slot)
            disconnect(self.signals[MaterialLayer.imag], slot)

    @property
    def signals(self):
        return self.__signals

    @property
    def name(self):
        return self._material.name

    @property
    def wavelength(self):
        """:rtype: list of float"""
        return [d.wavelength for d in self._material.data]

    @property
    def refraction(self):
        """
        :return: Refractive index real, image lists
        :rtype: list of float, list of float
        """
        return zip(*self._material.data)

    # ------------------------------------------------------------------------------------------------------------------
    # These refraction properties are only appropriate for parametric object
    # where only one material data item is contained in the material data list.

    _real_error_string = "Property 'real' is only available for parametric object"

    def _get_real(self):
        if not self.is_parametric:
            raise NotImplementedError(self._real_error_string)
        return self._material.data[0].real

    def _set_real(self, value):
        if not self.is_parametric:
            raise NotImplementedError(self._real_error_string)
        if self._material.data[0].real != value:
            self._material.data[0].real = value
            self.signals[MaterialLayer.real].emit()

    real = AttributedProperty(
        _get_real, _set_real,
        key="real", dtype=orm.Float,
        precision=orm.MaterialData.real.precision)

    _imag_error_string = "Property 'imag' is only available for parametric object"

    def _get_imag(self):
        if not self.is_parametric:
            raise NotImplementedError(self._imag_error_string)
        return self._material.data[0].imag

    def _set_imag(self, value):
        if not self.is_parametric:
            raise NotImplementedError(self._imag_error_string)
        if self._material.data[0].imag != value:
            self._material.data[0].imag = value
            self.signals[MaterialLayer.imag].emit()

    imag = AttributedProperty(
        _get_imag, _set_imag,
        key="imag", dtype=orm.Float,
        precision=orm.MaterialData.imag.precision)

    def export(self):
        return {
            "Type": self.type,
            "Parametric": self.is_parametric,
            "Material": self._material.export()
        }

    @classmethod
    def load(cls, data):
        """:type data: dict"""
        return cls(orm.Material.load(data["Material"]), data["Parametric"])


class Substrate(MaterialLayer):

    @classmethod
    def parametric(cls, wavelength, real, imag):
        """
        :type wavelength: float
        :type real: float
        :type imag: float
        """
        material = MaterialLayer._create_parametric_material(wavelength, real,  imag)
        return cls(material, is_parametric=True)

    @classmethod
    def default_parametric(cls, wavelength):
        """
        :type wavelength: float
        :rtype: Substrate
        """
        return cls.parametric(
            wavelength,
            config.DEFAULT_LAYER_REAL_INDEX,
            config.DEFAULT_LAYER_IMAG_INDEX)

    @classmethod
    def db_stored(cls, material, *args):
        """
        :type material: orm.Material
        :rtype: Substrate
        """
        return cls(material)

    @property
    def type(self):
        return SUBSTRATE_TYPE

    def report(self):
        body = [
            ReportTemplates.value % {"name": "Name", "value": "%(order)d:" + self._material.name},
            ReportTemplates.value % {"name": "Refractive", "value": "%(index)s"},
        ]
        template = self.report_header()
        return template % "\n".join(body)

    def convert2core(self):
        real, imag = self.refraction[0], self.refraction[1]
        if len(self.wavelength) > 1:
            return oplc.StandardWaferLayer(
                oplc.SUBSTRATE_LAYER, numpy.asfortranarray(self.wavelength),
                numpy.asfortranarray(real), numpy.asfortranarray(imag))
        else:
            return oplc.ConstantWaferLayer(oplc.SUBSTRATE_LAYER, real[0], imag[0])


class StandardLayer(MaterialLayer):
    """Class describe wafer stack layer that has both a predefined material and thickness"""

    SignalsClass = orm.SignalsMeta.CreateSignalsClass("StandardLayer", ["real", "imag", "thickness"], db_columns=False)

    def __init__(self, material, thickness, is_parametric=False):
        """
        :type material: orm.Material
        :type thickness: float
        :type is_parametric: bool
        """
        MaterialLayer.__init__(self, material, is_parametric)
        self._thickness = Variable(Numeric(vmin=0.0, vmax=10000.0, precision=1), value=thickness, name="Thickness")

    def connect_with(self, slot):
        super(StandardLayer, self).connect_with(slot)
        connect(self.signals[StandardLayer.thickness], slot)

    def disconnect_from(self, slot):
        super(StandardLayer, self).disconnect_from(slot)
        disconnect(self.signals[StandardLayer.thickness], slot)

    @classmethod
    def parametric(cls, wavelength, real, imag, thickness):
        """
        :type wavelength: float
        :type real: float
        :type imag: float
        :type thickness: float
        """
        material = MaterialLayer._create_parametric_material(wavelength, real,  imag)
        return cls(material, thickness, is_parametric=True)

    @classmethod
    def default_parametric(cls, wavelength):
        """
        :type wavelength: float
        :rtype: StandardLayer
        """
        return cls.parametric(
            wavelength,
            config.DEFAULT_LAYER_REAL_INDEX,
            config.DEFAULT_LAYER_IMAG_INDEX,
            config.DEFAULT_LAYER_THICKNESS)

    @classmethod
    def db_stored(cls, material, *args):
        """
        :type material: orm.Material
        :rtype: StandardLayer
        """
        thickness = args[0]
        return cls(material, thickness)

    def _get_thickness(self):
        return self._thickness.value

    def _set_thickness(self, value):
        if self._thickness.value != value:
            self._thickness.value = value
            self.signals[StandardLayer.thickness].emit()

    thickness = AttributedProperty(_get_thickness, _set_thickness, key="thickness", dtype=orm.Float)

    @property
    def type(self):
        return LAYER_TYPE

    def export(self):
        result = super(StandardLayer, self).export()
        result.update({"Thickness": self.thickness})
        return result

    @classmethod
    def load(cls, data):
        """:type data: dict"""
        return cls(
            material=orm.Material.load(data["Material"]),
            thickness=data["Thickness"],
            is_parametric=data["Parametric"])

    def report(self):
        body = [
            ReportTemplates.value % {"name": "Name", "value": "%(order)d:" + self._material.name},
            ReportTemplates.value % {"name": "Thickness", "value": self.thickness},
            ReportTemplates.value % {"name": "Refractive", "value": "%(index)s"},
        ]
        template = self.report_header()
        return template % "\n".join(body)

    def convert2core(self):
        real, imag = self.refraction[0], self.refraction[1]
        if len(self.wavelength) > 1:
            return oplc.StandardWaferLayer(
                oplc.SUBSTRATE_LAYER, self.thickness, numpy.asfortranarray(self.wavelength),
                numpy.asfortranarray(real), numpy.asfortranarray(imag))
        else:
            return oplc.ConstantWaferLayer(oplc.SUBSTRATE_LAYER, self.thickness, real[0], imag[0])


class Resist(AbstractOptionsBase, StandardLayer):
    """Class redefined from database material to resist"""

    icon = "icons/Resist"

    def __init__(self, material, thickness):
        """
        :type material: orm.Resist
        :type thickness: float
        """
        AbstractOptionsBase.__init__(self)
        StandardLayer.__init__(self, material, thickness)

    def connect_with(self, slot):
        super(Resist, self).connect_with(slot)
        connect(self._material.peb.signals[orm.PebParameters.ea], slot)
        connect(self._material.peb.signals[orm.PebParameters.ln_ar], slot)

        connect(self._material.exposure.signals[orm.ExposureParameters.wavelength], slot)
        connect(self._material.exposure.signals[orm.ExposureParameters.a], slot)
        connect(self._material.exposure.signals[orm.ExposureParameters.b], slot)
        connect(self._material.exposure.signals[orm.ExposureParameters.c], slot)
        connect(self._material.exposure.signals[orm.ExposureParameters.n], slot)

        if isinstance(self._material.developer, orm.DeveloperExpr):
            for obj in self._material.developer.object_values:
                connect(obj.signals[orm.DeveloperExprArgValue.value], slot)

    def disconnect_from(self, slot):
        super(Resist, self).disconnect_from(slot)
        disconnect(self._material.peb.signals[orm.PebParameters.ea], slot)
        disconnect(self._material.peb.signals[orm.PebParameters.ln_ar], slot)

        disconnect(self._material.exposure.signals[orm.ExposureParameters.wavelength], slot)
        disconnect(self._material.exposure.signals[orm.ExposureParameters.a], slot)
        disconnect(self._material.exposure.signals[orm.ExposureParameters.b], slot)
        disconnect(self._material.exposure.signals[orm.ExposureParameters.c], slot)
        disconnect(self._material.exposure.signals[orm.ExposureParameters.n], slot)

        if isinstance(self._material.developer, orm.DeveloperExpr):
            for obj in self._material.developer.object_values:
                disconnect(obj.signals[orm.DeveloperExprArgValue.value], slot)

    @classmethod
    def default_parametric(cls, wavelength):
        raise NotImplementedError

    @classmethod
    def db_stored(cls, material, *args):
        raise NotImplementedError

    @property
    def db(self):
        """:rtype: orm.Resist"""
        return self._material

    @property
    def name(self):
        return self._material.name

    @name.setter
    def name(self, value):
        self._material.name = value
        self.onOptionChanged()

    @property
    def exposure(self):
        """:rtype: orm.ExposureParameters"""
        return self._material.exposure

    @property
    def peb(self):
        """:rtype: orm.PebParameters"""
        return self._material.peb

    @property
    def developer(self):
        """:rtype: orm.DeveloperInterface"""
        return self._material.developer

    @developer.setter
    def developer(self, value):
        """:type value: orm.DeveloperInterface"""
        if self._material.developer is not value:
            self._material.developer = value
            self.onOptionChanged()

    @property
    def wavelength(self):
        """:rtype: list of float"""
        # Because refraction of the resist changes linear depend on wavelength so list of refractions and
        # wavelengths return to refraction_at method automatically calculate it.
        return [0.0, self._material.exposure.wavelength]

    @property
    def refraction(self):
        """
        :return: Refractive index real, image lists
        :rtype: list of float, list of float
        """
        re = self._material.exposure.n
        # k = w/4/pi*(A+B)/1000
        ab = (self._material.exposure.a + self._material.exposure.b)*1e-3
        im = self._material.exposure.wavelength/4.0/numpy.pi * ab
        return [re, re], [0.0, im]

    @property
    def type(self):
        return RESIST_TYPE

    def report(self):
        body = [
            ReportTemplates.value % {"name": "Name", "value": self._material.name},
            ReportTemplates.value % {"name": "Thickness", "value": self.thickness},
            ReportTemplates.value % {"name": "<i>Exposure</i>", "value": ""},
            ReportTemplates.subvalue % {"name": "Wavelength", "value": self._material.exposure.wavelength},
            ReportTemplates.subvalue % {"name": "Refractive", "value": self._material.exposure.n},
            ReportTemplates.subvalue % {"name": "Dill A", "value": self._material.exposure.a},
            ReportTemplates.subvalue % {"name": "Dill B", "value": self._material.exposure.b},
            ReportTemplates.subvalue % {"name": "Dill C", "value": self._material.exposure.c},
            ReportTemplates.value % {"name": "<i>Post Exposure Bake</i>", "value": ""},
            ReportTemplates.subvalue % {"name": "Ln(Ar)", "value": self._material.peb.ln_ar},
            ReportTemplates.subvalue % {"name": "Ea", "value": self._material.peb.ea},
            ReportTemplates.value % {"name": "<i>Development</i>", "value": ""},
        ]

        if isinstance(self._material.developer, orm.DeveloperExpr):
            body.append(ReportTemplates.subvalue % {"name": "Developer", "value": self._material.developer.name})
            for arg, value in zip(self._material.developer.model.args, self._material.developer.values):
                body.append(ReportTemplates.subvalue % {"name": arg.name, "value": value})
        elif isinstance(self._material.developer, orm.DeveloperSheet):
            body.append(ReportTemplates.subvalue % {"name": "Developer", "value": self._material.developer.name})
        else:
            body.append(ReportTemplates.subvalue % {"name": "Developer", "value": "Undefined"})

        template = self.report_header()
        return template % "\n".join(body)

    def assign(self, other):
        """:type other: Resist"""
        self.thickness = other.thickness
        self._material.assign(other._material)
        self.onOptionChanged()

    def export(self):
        return {
            "Type": self.type,
            "Thickness": self.thickness,
            "Material": self._material.export()
        }

    @classmethod
    def load(cls, data):
        """:type data: dict"""
        return cls(material=orm.Resist.load(data["Material"]), thickness=data["Thickness"])

    def parse(self, data):
        """:type data: dict"""
        self._material.parse(data["Material"])
        self.thickness = data["Thickness"]

    def convert2core(self):
        exposure = self._material.exposure.convert2core()
        peb = self._material.peb.convert2core()
        developer = self._material.developer.convert2core()
        return oplc.ResistWaferLayer(self.thickness, exposure, peb, developer)


class WaferProcess(AbstractOptionsBase):

    icon = "icons/WaferStack"

    _resist_key = 0
    _substrate_key = -1

    def __init__(self, stack_layers=None):
        """
        :type stack_layers: list of WaferStackLayer or None
        """
        super(WaferProcess, self).__init__()

        self._stack = list()
        """:type: list of WaferStackLayer"""

        if stack_layers is not None:
            for layer in stack_layers:
                if not isinstance(layer, WaferStackLayer):
                    raise TypeError("Value must be WaferStackLayer")
                layer.connect_with(self.onOptionChanged)
                self._stack.append(layer)

        self.imaging_tool = None
        """:type: ImagingTool"""

        connect(self.changed, GlobalSignals.onChanged)

    def insert(self, index, stack_layer):
        """
        :type index: int
        :type stack_layer: WaferStackLayer
        """
        if not isinstance(stack_layer, WaferStackLayer):
            raise TypeError("Value must be WaferStackLayer")

        stack_layer.connect_with(self.onOptionChanged)
        self._stack.insert(index, stack_layer)
        self.onOptionChanged()

    def remove(self, index):
        """:type index: int"""
        self._stack[index].disconnect_from(self.onOptionChanged)
        del self._stack[index]
        self.onOptionChanged()

    def __iter__(self):
        return self._stack.__iter__()

    def __setitem__(self, key, value):
        """
        :type key: int
        :type value: WaferStackLayer
        """
        if not isinstance(value, WaferStackLayer):
            raise TypeError("Value must be WaferStackLayer")
        # if key in self._stack:
        #     self._link_layer(self._stack[key], action=disconnect)
        # self._stack[key] = value
        if key == WaferProcess._resist_key:
            self._stack[key] = value
        else:
            self.remove(key)
            self.insert(key, value)
            self.onOptionChanged()

    def __getitem__(self, item):
        """
        :type item: int
        :rtype: WaferStackLayer
        """
        return self._stack[item]

    def __len__(self):
        """:rtype: int"""
        return len(self._stack)

    @property
    def resist(self):
        """:rtype: Resist"""
        return self[WaferProcess._resist_key]

    @resist.setter
    def resist(self, value):
        """:type value: Resist"""
        if self.resist is not value:
            self.resist.disconnect_from(self.onOptionChanged)
            if WaferProcess._resist_key in self:
                # noinspection PyUnresolvedReferences
                disconnect(self[WaferProcess._resist_key].changed, self.onOptionChanged)
            self[WaferProcess._resist_key] = value
            # noinspection PyUnresolvedReferences
            connect(self[WaferProcess._resist_key].changed, self.onOptionChanged)
            self.resist.connect_with(self.onOptionChanged)

    @property
    def substrate(self):
        """:rtype: Substrate"""
        return self[WaferProcess._substrate_key]

    @staticmethod
    def _create_default_substrate():
        substrate = orm.Material(
            name=config.DEFAULT_SUBSTRATE_MATERIAL_NAME,
            data=[orm.MaterialData(wavelength=362.5, real=6.308, imag=2.88)],
            desc="Default substrate material, n=6.308+2.88i @ 362.5 nm")
        return substrate

    @staticmethod
    def _create_default_devrate():
        dev_rate = orm.DeveloperSheet(
            name=config.DEFAULT_DEV_RATE_NAME,
            is_depth=False,
            data=[orm.DeveloperSheetData(pac=0.0, rate=100.0),
                  orm.DeveloperSheetData(pac=0.3, rate=90.0),
                  orm.DeveloperSheetData(pac=0.7, rate=10.0),
                  orm.DeveloperSheetData(pac=1.0, rate=0.1)],
            desc="Default development rate data")
        return dev_rate

    @staticmethod
    def _create_default_resist():
        exposure = orm.ExposureParameters(wavelength=365.0, a=0.5, b=0.5, c=0.01, n=1.5)
        peb = orm.PebParameters(ea=30.0, ln_ar=40.0)
        dev_rate = WaferProcess._create_default_devrate()

        resist = orm.Resist(
            name=config.DEFAULT_RESIST_NAME, comment="Default resist data",
            exposure=exposure, peb=peb, developer=dev_rate)

        return resist

    # noinspection PyMethodOverriding
    @classmethod
    def default(cls):
        """:rtype: WaferProcess"""
        resist = Resist(WaferProcess._create_default_resist(), config.DEFAULT_LAYER_THICKNESS)
        substrate = Substrate(WaferProcess._create_default_substrate())
        return cls([resist, substrate])

    @classmethod
    def empty(cls):
        return cls()

    @classmethod
    def load(cls, data):
        stack_layers = []
        for layer_data in data:
            if layer_data["Type"] == RESIST_TYPE:
                layer = Resist.load(layer_data)
            elif layer_data["Type"] == LAYER_TYPE:
                layer = StandardLayer.load(layer_data)
            elif layer_data["Type"] == SUBSTRATE_TYPE:
                layer = Substrate.load(layer_data)
            else:
                raise KeyError("Unknown layer type: %s" % layer_data["Type"])
            stack_layers.append(layer)
        return cls(stack_layers=stack_layers)

    def __del__(self):
        # FIXME: This is workaround for strange error when exit: _stack not found in wafer_process
        pass

    def saved(self, emit=True):
        self.resist.saved(emit=False)
        super(WaferProcess, self).saved(emit)

    def report(self):
        template = self.report_header()
        body = "\n".join(
            [ReportTemplates.composite % layer.report() %
             {
                 "order": len(self._stack)-order-1,
                 # "index": "%.2f%+.2fi" % layer.refraction_at(self.resist.material.exposure.wavelength)
                 "index": "%.2f%+.2fi" % layer.refraction_at(self.resist.exposure.wavelength)
             }
             for order, layer in enumerate(self._stack)
             if not isinstance(layer, Resist)])
        return template % body

    def export(self):
        return [layer.export() for layer in self._stack]

    def assign(self, other):
        """:type other: WaferProcess"""
        # Delete all layers except the resist (first layer)
        while len(self) != 1:
            self.remove(-1)

        for layer in other:
            if isinstance(layer, Resist):
                self.resist.assign(layer)
            else:
                layer.connect_with(self.onOptionChanged)
                self._stack.append(layer)

    def parse(self, data):
        """:type data: dict"""
        stack_layers = []

        # Delete all layers except the resist (first layer)
        while len(self) != 1:
            self.remove(-1)

        for layer_data in data:
            if layer_data["Type"] == RESIST_TYPE:
                # self.resist.parse(layer_data)
                self.resist = Resist.load(layer_data)
            elif layer_data["Type"] == LAYER_TYPE:
                stack_layers.append(StandardLayer.load(layer_data))
            elif layer_data["Type"] == SUBSTRATE_TYPE:
                stack_layers.append(Substrate.load(layer_data))

        # self._stack[WaferProcess._resist_key+1:] = stack_layers
        for layer in stack_layers:
            layer.connect_with(self.onOptionChanged)
            self._stack.append(layer)

    def convert2core(self):
        result = oplc.WaferStack()

        for wafer_layer in reversed(self):
            result.push(wafer_layer.convert2core())

        nenv = self.imaging_tool.immersion.value if self.imaging_tool.immersion_enabled else oplc.air_nk.real
        core_env_layer = oplc.ConstantWaferLayer(oplc.ENVIRONMENT_LAYER, nenv, 0.0)
        result.push(core_env_layer)

        return result


class Mask(AbstractOptionsBase):

    icon = "icons/Mask"

    mask_type_map = {0: "1D", 1: "2D"}

    def __init__(self, container):
        """:type container: orm.Mask | orm.ConcretePluginMask"""
        super(Mask, self).__init__()
        self.__container = None
        self.container = container
        self._connect_signals()

    @property
    def container(self):
        return self.__container

    @container.setter
    def container(self, value):
        if self.__container is not value:
            if self.__container is not None:
                disconnect(self.__container.signals[orm.Mask.background], self.onOptionChanged)
                disconnect(self.__container.signals[orm.Mask.phase], self.onOptionChanged)
            self._set_composite_variable("container", value)
            connect(self.__container.signals[orm.Mask.background], self.onOptionChanged)
            connect(self.__container.signals[orm.Mask.phase], self.onOptionChanged)

    def report(self):
        body = [
            ReportTemplates.value % {"name": "Name", "value": self.container.name},
            ReportTemplates.value % {"name": "Dimensions", "value": "%sD" % self.container.dimensions},
        ]
        if isinstance(self.container, orm.ConcretePluginMask):
            body.append(ReportTemplates.value % {"name": "Type", "value": "Plugin"})
            for arg, value in zip(self.container.variables, self.container.values):
                body.append(ReportTemplates.subvalue % {"name": arg.name, "value": value})
        elif isinstance(self.container, orm.Mask):
            body.append(ReportTemplates.value % {"name": "Type", "value": "Database"})

        template = self.report_header()
        return template % "\n".join(body)

    @staticmethod
    def default_container():
        region_transmit = 1.0
        bg_transmit = 0.0

        feature = 250.0
        pitch = 800.0
        height = 800.0

        name = "Line %s/%s" % (feature, pitch)
        description = "Binary dense line mask with feature = %s and pitch = %s size" % (feature, pitch)
        boundary = orm.Geometry.rectangle(-pitch/2.0, -height/2.0, pitch/2.0, height/2.0)
        sim_region = boundary.clone()
        points = [orm.Point(-feature/2.0, -height/2.0), orm.Point(-feature/2.0, height/2.0),
                  orm.Point(feature/2.0, height/2.0), orm.Point(feature/2.0, -height/2.0)]
        regions = [orm.Region(region_transmit, 0.0, orm.GeometryShape.Polygon, points)]
        return orm.Mask(name, bg_transmit, 0.0, boundary, sim_region, regions, desc=description)

    @classmethod
    def default(cls):
        return cls(container=Mask.default_container())

    @classmethod
    def empty(cls):
        return cls(container=None)

    @classmethod
    def load(cls, data):
        """:type data: dict"""
        return cls.empty().parse(data)

    def assign(self, other):
        """:type other: Mask"""
        self.container = other.container.clone()

    def export(self):
        return self.container.export()

    def parse(self, data):
        """:type data: dict"""
        if data[orm.Generic.type.key] == str(orm.GenericType.Mask):
            self.container = orm.Mask.load(data)
        elif data[orm.Generic.type.key] == str(orm.GenericType.AbstractPluginMask):
            self.container = orm.ConcretePluginMask.load(data)
        else:
            raise orm.UnknownObjectTypeError(data[orm.Generic.type.key])
        return self

    def convert2core(self):
        container = self.container
        points = oplc.Points2dArray([oplc.Point2d(*p) for p in container.boundary.points])
        boundary = oplc.Box(points, container.background, container.phase)
        regions = oplc.RegionsArray()
        for region in container.regions:
            points = oplc.Points2dArray([oplc.Point2d(p.x, p.y) for p in region.points])
            regions.append(oplc.Region(points, region.transmittance, region.phase))
        return oplc.Mask(regions, boundary)


class ImagingTool(AbstractOptionsBase):

    icon = "icons/ImagingTool"

    pupil_filter_key = "PupilFilter"
    source_shape_key = "SourceShape"

    def __init__(self, wavelength, numerical_aperture, reduction_ratio, flare,
                 immersion, immersion_enabled, source_shape, pupil_filter):
        """
        :param float wavelength: Imaging tool nominal wavelength
        :param float numerical_aperture: Imaging tool projection lenses nominal numerical aperture
        :param float reduction_ratio: Imaging tool projection lenses reduction ratio
        :param float flare: Imaging tool parasitic flare (empirical parameter)
        :param float or None immersion: Refraction index of immersion layer above resist (None if not applicable)
        :param bool immersion_enabled: If True immersion data is valid and enabled
        :param orm.SourceShape or orm.ConcretePluginSourceShape source_shape: Source shape of the imaging tool
        :param orm.PupilFilter or orm.ConcretePluginPupilFilter or None pupil_filter: Projection lenses pupil filter
            of the imaging tool (None - no)
        """
        super(ImagingTool, self).__init__()
        self.__source_shape = source_shape
        self.__pupil_filter = pupil_filter

        self.wavelength = Variable(
            Numeric(vmin=0.0001, vmax=1000.0, dtype=float),
            value=wavelength, name="Wavelength")
        self.numerical_aperture = Variable(
            Numeric(vmin=0.0001, vmax=1.0, dtype=float),
            value=numerical_aperture, name="Numerical Aperture")
        self.reduction_ratio = Variable(
            Numeric(vmin=1.0, vmax=10.0, dtype=float),
            value=reduction_ratio, name="Reduction Ratio")
        self.flare = Variable(
            Numeric(vmin=0.0, vmax=1.0, dtype=float),
            value=flare, name="Flare")

        immersion = 1.44 if immersion is None else immersion

        self.immersion = Variable(
            Numeric(vmin=1.0, vmax=3.0, dtype=float),
            value=immersion, name="Immersion")

        self.__immersion_enabled = immersion_enabled

        self.numerics = None
        """:type: Numerics"""

        self._connect_signals()

    @property
    def source_shape(self):
        return self.__source_shape

    @source_shape.setter
    def source_shape(self, value):
        """:type value: orm.SourceShape or orm.ConcretePluginSourceShape"""
        if self.__source_shape is not value:
            self._set_composite_variable("source_shape", value)
            self.__source_shape.numerics = self.numerics

    @property
    def pupil_filter(self):
        return self.__pupil_filter

    @pupil_filter.setter
    def pupil_filter(self, value):
        if self.__pupil_filter is not value:
            self._set_composite_variable("pupil_filter", value)

    @property
    def immersion_enabled(self):
        return self.__immersion_enabled

    @immersion_enabled.setter
    def immersion_enabled(self, value):
        if self.__immersion_enabled != value:
            self.__immersion_enabled = value
            self.onOptionChanged()

    def report(self):
        body = [
            self.wavelength.report(),
            self.numerical_aperture.report(),
            self.reduction_ratio.report(),
            self.flare.report()
        ]
        if self.immersion_enabled:
            body.append(self.immersion.report())

        body.append(ReportTemplates.value % {"name": "Source Shape", "value": self.source_shape.name})
        if isinstance(self.source_shape, orm.ConcretePluginSourceShape):
            body.append(ReportTemplates.subvalue % {"name": "Type", "value": "Plugin"})
            for arg, value in zip(self.source_shape.variables, self.source_shape.values):
                body.append(ReportTemplates.subvalue % {"name": arg.name, "value": value})
        elif isinstance(self.source_shape, orm.SourceShape):
            body.append(ReportTemplates.subvalue % {"name": "Type", "value": "Database"})

        if self.pupil_filter is not None:
            body.append(ReportTemplates.value % {"name": "Pupil Filter", "value": self.pupil_filter.name})
            if isinstance(self.pupil_filter, orm.ConcretePluginPupilFilter):
                body.append(ReportTemplates.subvalue % {"name": "Type", "value": "Plugin"})
                for arg, value in zip(self.pupil_filter.variables, self.pupil_filter.values):
                    body.append(ReportTemplates.subvalue % {"name": arg.name, "value": value})
            elif isinstance(self.pupil_filter, orm.PupilFilter):
                body.append(ReportTemplates.subvalue % {"name": "Type", "value": "Database"})

        template = self.report_header()
        return template % "\n".join(body)

    @classmethod
    def default(cls):
        default_source_shape = orm.SourceShape(
            name="CoherentDefault",
            data=[orm.SourceShapeData(x=0.0, y=0.0, intensity=1.0)],
            desc="Default ideal conventional coherent source shape")
        return cls(
            wavelength=365.0,
            numerical_aperture=0.51,
            reduction_ratio=1.0,
            flare=0.0,
            immersion=None,
            immersion_enabled=False,
            source_shape=default_source_shape,
            pupil_filter=None)

    @classmethod
    def empty(cls):
        return cls(
            wavelength=None,
            numerical_aperture=None,
            reduction_ratio=None,
            flare=None,
            immersion=None,
            immersion_enabled=False,
            source_shape=None,
            pupil_filter=None
        )

    def export(self):
        if self.pupil_filter is not None:
            pupil_filter = {ImagingTool.pupil_filter_key: self.pupil_filter.export()}
        else:
            pupil_filter = {}

        if self.immersion_enabled:
            immersion = {self.immersion.name: self.immersion.value}
        else:
            immersion = {}

        result = {
            self.wavelength.name: self.wavelength.value,
            self.numerical_aperture.name: self.numerical_aperture.value,
            self.reduction_ratio.name: self.reduction_ratio.value,
            self.flare.name: self.flare.value,
            ImagingTool.source_shape_key: self.source_shape.export(),
        }

        result.update(pupil_filter)
        result.update(immersion)

        return result

    def assign(self, other):
        """:type other: ImagingTool"""
        self.wavelength.value = other.wavelength.value
        self.numerical_aperture.value = other.numerical_aperture.value
        self.reduction_ratio.value = other.reduction_ratio.value
        self.flare.value = other.flare.value
        self.immersion.value = other.immersion.value
        self.immersion_enabled = other.immersion_enabled
        self.source_shape = other.source_shape.clone()
        self.pupil_filter = other.pupil_filter.clone() if other.pupil_filter is not None else None

    def parse(self, data):
        """:type data: dict"""
        self.wavelength.value = float(data[self.wavelength.name])
        self.numerical_aperture.value = float(data[self.numerical_aperture.name])
        self.reduction_ratio.value = float(data[self.reduction_ratio.name])
        self.flare.value = float(data[self.flare.name])

        source_shape_data = data[ImagingTool.source_shape_key]
        typename = source_shape_data[orm.Generic.type.key]
        if typename == str(orm.GenericType.SourceShape):
            self.source_shape = orm.SourceShape.load(source_shape_data)
        elif typename == str(orm.GenericType.AbstractPluginSourceShape):
            self.source_shape = orm.ConcretePluginSourceShape.load(source_shape_data)
        else:
            raise orm.UnknownObjectTypeError(typename)

        try:
            immersion = float(data[self.immersion.name])
        except KeyError:
            self.immersion_enabled = False
        else:
            self.immersion.value = immersion
            self.immersion_enabled = True

        try:
            pupil_filter_data = data[ImagingTool.pupil_filter_key]
        except KeyError:
            self.pupil_filter = None
        else:
            typename = pupil_filter_data[orm.Generic.type.key]
            if typename == str(orm.GenericType.PupilFilter):
                self.pupil_filter = orm.PupilFilter.load(pupil_filter_data)
            elif typename == str(orm.GenericType.AbstractPluginPupilFilter):
                self.pupil_filter = orm.ConcretePluginPupilFilter.load(pupil_filter_data)
            else:
                raise orm.UnknownObjectTypeError(typename)

        return self

    @classmethod
    def load(cls, data):
        return cls.empty().parse(data)

    def convert2core(self):
        stepx = stepy = self.numerics.source_stepxy
        model = self.source_shape.convert2core()
        source_shape = oplc.SourceShape(model, stepx, stepy)
        pupil_filter = self.pupil_filter.convert2core() \
            if self.pupil_filter is not None else oplc.PupilFilterModelEmpty()
        immersion = self.immersion.value if self.immersion_enabled else oplc.air_nk.real
        return oplc.ImagingTool(
            source_shape, pupil_filter,
            self.wavelength.value, self.numerical_aperture.value,
            self.reduction_ratio.value, self.flare.value, immersion)


class ExposureFocus(AbstractOptionsBase):

    icon = "icons/ExposureAndFocus"

    top = "Top"
    middle = "Middle"
    bottom = "Bottom"

    up = "Up"
    down = "Down"

    _dir_ = {up: -1.0, down: 1.0}

    def __init__(self, exposure, focus, correctable, relative_to, direction):
        """
        :param float exposure: Exposure value
        :param float focus: Focus value
        :param float correctable: Dose correctable coefficient
        :param str relative_to: Focal position relative to
        :param str direction: Positive direction of focal position
        """
        super(ExposureFocus, self).__init__()

        self.exposure = Variable(
            Numeric(vmin=0.0, vmax=1000.0, dtype=float),
            value=exposure, name="Exposure")

        self.focus = Variable(
            Numeric(vmin=-10.0, vmax=10.0, dtype=float),
            value=focus, name="Focus")

        self.dose_correctable = Variable(
            Numeric(vmin=0.0, vmax=100.0, dtype=float),
            value=correctable, name="DoseCorrectable")

        self.focal_relative_to = Variable(
            Enum(variants=[ExposureFocus.top, ExposureFocus.middle, ExposureFocus.bottom]),
            value=relative_to, name="FocalRelativeTo")

        self.focal_direction = Variable(
            Enum(variants=[ExposureFocus.up, ExposureFocus.down]),
            value=direction, name="FocalDirection")

        # Link to the wafer process (simplify the calculation)
        self.wafer_process = None
        """:type: WaferProcess"""

        self._connect_signals()

    _rel_ = {
        top: lambda v: 0.0,
        middle: lambda v: float(v)/2.0,
        bottom: lambda v: float(v)
    }

    def assign(self, other):
        """:type other: ExposureFocus"""
        self.exposure.value = other.exposure.value
        self.focus.value = other.focus.value
        self.dose_correctable.value = other.dose_correctable.value
        self.focal_relative_to.value = other.focal_relative_to.value
        self.focal_direction.value = other.focal_direction.value

    @property
    def focal_plane(self):
        """
        Calculate focus relative to the top of Resist
        :rtype: float
        """
        # noinspection PyCallingNonCallable
        base = ExposureFocus._rel_[self.focal_relative_to.value](self.wafer_process.resist.thickness)
        direction = ExposureFocus._dir_[self.focal_direction.value]
        return direction * 1E3*self.focus.value + base

    @classmethod
    def default(cls):
        return cls(
            exposure=50.0,
            focus=0.0,
            correctable=1.0,
            relative_to=ExposureFocus.top,
            direction=ExposureFocus.up
        )

    @classmethod
    def empty(cls):
        return cls(
            exposure=None,
            focus=None,
            correctable=None,
            relative_to=None,
            direction=None
        )

    @classmethod
    def load(cls, data):
        return cls.empty().parse(data)

    def report(self):
        template = self.report_header()
        body = "\n".join([
            self.exposure.report(),
            self.focus.report(),
            self.dose_correctable.report(),
            self.focal_relative_to.report(),
            self.focal_direction.report(),
        ])
        return template % body

    def export(self):
        return {
            self.exposure.name: self.exposure.value,
            self.focus.name: self.focus.value,
            self.dose_correctable.name: self.dose_correctable.value,
            self.focal_relative_to.name: self.focal_relative_to.value,
            self.focal_direction.name: self.focal_direction.value
        }

    def parse(self, data):
        """:type data: dict"""
        self.exposure.value = data[self.exposure.name]
        self.focus.value = data[self.focus.name]
        self.dose_correctable.value = data[self.dose_correctable.name]
        self.focal_relative_to.value = data[self.focal_relative_to.name]
        self.focal_direction.value = data[self.focal_direction.name]
        return self

    def convert2core(self):
        focus_top = self.focal_plane
        exposure = self.exposure.value
        correctable = self.dose_correctable.value
        return oplc.Exposure(focus_top, exposure, correctable)


class PostExposureBake(AbstractOptionsBase):

    icon = "icons/PEB"

    def __init__(self, time, temp):
        super(PostExposureBake, self).__init__()
        self.time = Variable(Numeric(vmin=0.0, vmax=500.0, precision=1), value=time, name="PebTime")
        self.temp = Variable(Numeric(vmin=0.0, vmax=300.0, precision=1), value=temp, name="PebTemp")
        self._connect_signals()

    def assign(self, other):
        """:type other: PostExposureBake"""
        self.time.value = other.time.value
        self.temp.value = other.temp.value

    def parse(self, data):
        """
        :type data: dict
        :rtype: PostExposureBake
        """
        self.time.value = data[self.time.name]
        self.temp.value = data[self.temp.name]
        return self

    @classmethod
    def default(cls):
        return cls(time=50.0, temp=115.0)

    @classmethod
    def empty(cls):
        return cls(time=None, temp=None)

    @classmethod
    def load(cls, data):
        return cls.empty().parse(data)

    def report(self):
        template = self.report_header()
        body = "\n".join([
            self.time.report(),
            self.temp.report(),
        ])
        return template % body

    def export(self):
        return {
            self.time.name: self.time.value,
            self.temp.name: self.temp.value
        }

    def convert2core(self):
        return oplc.PostExposureBake(self.time.value, self.temp.value)


class Development(AbstractOptionsBase):

    icon = "icons/Development"

    def __init__(self, time):
        super(Development, self).__init__()
        self.develop_time = Variable(
            Numeric(vmin=0.0, vmax=5000.0, precision=1),
            value=time, name="DevelopmentTime")
        self._connect_signals()

    def assign(self, other):
        """:type other: Development"""
        self.develop_time.value = other.develop_time.value

    @classmethod
    def default(cls):
        return cls(time=60.0)

    @classmethod
    def empty(cls):
        return cls(time=None)

    @classmethod
    def load(cls, data):
        return cls.empty().parse(data)

    def report(self):
        template = self.report_header()
        return template % self.develop_time.report()

    def export(self):
        return {self.develop_time.name: self.develop_time.value}

    def parse(self, data):
        """:type data: dict"""
        self.develop_time.value = data[self.develop_time.name]
        return self

    def convert2core(self):
        return oplc.Development(self.develop_time.value)


class Metrology(AbstractOptionsBase):

    icon = "icons/Metrology"

    def __init__(self, measurement_height, var_meas_height, aerial_image_level, image_in_resist_level,
                 latent_image_level, peb_latent_image_level, mask_tonality, cd_bias):
        super(Metrology, self).__init__()

        self.measurement_height = Variable(
            Numeric(vmin=0.0, vmax=100.0, precision=2),
            value=measurement_height, name="Measurement Height")

        self.variate_meas_height = Variable(
            Enum(variants=[VARIATE_HEIGHT_FALSE, VARIATE_HEIGHT_TRUE]),
            value=var_meas_height, name="Variate measurement height")

        self.aerial_image_level = Variable(
            Numeric(vmin=0.0, precision=3),
            value=aerial_image_level, name="Aerial Image Intensity Level")

        self.image_in_resist_level = Variable(
            Numeric(vmin=0.0, precision=3),
            value=image_in_resist_level, name="Image In Resist Intensity Level")

        self.latent_image_level = Variable(
            Numeric(vmin=0.0, precision=3),
            value=latent_image_level, name="Exposed Latent Image PAC Level")

        self.peb_latent_image_level = Variable(
            Numeric(vmin=0.0, precision=3),
            value=peb_latent_image_level, name="PEB Latent Image PAC Level")

        self.mask_tonality = Variable(
            Enum(variants=[MASK_CLEAR, MASK_OPAQUE]),
            value=mask_tonality, name="Mask tonality")

        self.cd_bias = Variable(
            Numeric(vmin=0.0, precision=3),
            value=cd_bias, name="Resist Profile Bias")

    def assign(self, other):
        """:type other: Metrology"""
        self.measurement_height.value = other.measurement_height.value
        self.variate_meas_height.value = other.variate_meas_height.value
        self.aerial_image_level.value = other.aerial_image_level.value
        self.image_in_resist_level.value = other.image_in_resist_level.value
        self.latent_image_level.value = other.latent_image_level.value
        self.peb_latent_image_level.value = other.peb_latent_image_level.value
        self.mask_tonality.value = other.mask_tonality.value
        self.cd_bias.value = other.cd_bias.value

    @classmethod
    def default(cls):
        return cls(
            measurement_height=5.0,
            var_meas_height=VARIATE_HEIGHT_FALSE,
            aerial_image_level=0.3,
            image_in_resist_level=0.3,
            latent_image_level=0.5,
            peb_latent_image_level=0.5,
            mask_tonality=MASK_OPAQUE,
            cd_bias=0.0,
        )

    @classmethod
    def empty(cls):
        return cls(
            measurement_height=None,
            var_meas_height=None,
            aerial_image_level=None,
            image_in_resist_level=None,
            latent_image_level=None,
            peb_latent_image_level=None,
            mask_tonality=None,
            cd_bias=None,
        )

    @classmethod
    def load(cls, data):
        return cls.empty().parse(data)

    def report(self):
        template = self.report_header()
        body = "\n".join([
            self.measurement_height.report(),
            self.variate_meas_height.report(),
            self.aerial_image_level.report(),
            self.image_in_resist_level.report(),
            self.latent_image_level.report(),
            self.peb_latent_image_level.report(),
            self.mask_tonality.report(),
            self.cd_bias.report(),
        ])
        return template % body

    def export(self):
        return {
            self.measurement_height.name: self.measurement_height.value,
            self.variate_meas_height.name: self.variate_meas_height.value,
            self.aerial_image_level.name: self.aerial_image_level.value,
            self.image_in_resist_level.name: self.image_in_resist_level.value,
            self.latent_image_level.name: self.latent_image_level.value,
            self.peb_latent_image_level.name: self.peb_latent_image_level.value,
            self.mask_tonality.name: self.mask_tonality.value,
            self.cd_bias.name: self.cd_bias.value,
        }

    def parse(self, data):
        """:type data: dict"""
        self.measurement_height.value = data[self.measurement_height.name]
        self.variate_meas_height.value = data[self.variate_meas_height.name]
        self.aerial_image_level.value = data[self.aerial_image_level.name]
        self.image_in_resist_level.value = data[self.image_in_resist_level.name]
        self.latent_image_level.value = data[self.latent_image_level.name]
        self.peb_latent_image_level.value = data[self.peb_latent_image_level.name]
        self.mask_tonality.value = data[self.mask_tonality.name]
        self.cd_bias.value = data[self.cd_bias.name]
        return self


class Options(AbstractOptionsBase):

    def __init__(self, numerics, wafer_process, mask, imaging_tool,
                 exposure_focus, peb, development, metrology, path=None, coupled=False):
        """
        :type numerics: Numerics
        :type wafer_process: WaferProcess
        :type mask: Mask
        :type imaging_tool: ImagingTool
        :type exposure_focus: ExposureFocus
        :type peb: PostExposureBake
        :type development: Development
        :type metrology: Metrology
        :type path: str or None
        :param bool coupled: If true then Options coupled with file on disk
        """
        super(Options, self).__init__()

        self._folder = None
        """:type: str"""

        self._filename = None
        """:type: str"""

        self.numerics = numerics
        """:type: Numerics"""
        self.wafer_process = wafer_process
        """:type: WaferProcess"""
        self.mask = mask
        """:type: Mask"""
        self.imaging_tool = imaging_tool
        """:type: ImagingTool"""
        self.exposure_focus = exposure_focus
        """:type: ExposureFocus"""
        self.peb = peb
        """:type: PostExposureBake"""
        self.development = development
        """:type: Development"""
        self.metrology = metrology
        """:type: Metrology"""

        self.imaging_tool.numerics = self.numerics
        self.wafer_process.imaging_tool = self.imaging_tool
        self.exposure_focus.wafer_process = self.wafer_process

        self.__groups = [
            self.numerics, self.wafer_process, self.mask,
            self.imaging_tool, self.exposure_focus,
            self.peb, self.development, self.metrology]
        """:type: list of AbstractOptionsBase"""

        self.__coupled = coupled
        self.path = path

        connect(GlobalSignals.changed, self.onOptionChanged)

    def assign(self, other):
        """:type other: Options"""
        super(Options, self).assign(other)
        disconnect(GlobalSignals.changed, other.onOptionChanged)
        for group in self.__groups:
            other_group = filter(lambda g: isinstance(g, type(group)), other.groups)[0]
            group.assign(other_group)
        self.path = other.path
        self.__coupled = other.coupled
        connect(GlobalSignals.changed, other.onOptionChanged)
        self.changed.emit()

    @property
    def groups(self):
        return self.__groups

    @property
    def path(self):
        return os.path.join(self._folder, self._filename)

    @path.setter
    def path(self, value):
        if value is not None:
            folder, filename = os.path.split(value)
            self._folder = folder
            self._filename = filename
        else:
            self._folder = os.path.expanduser("~")
            self._filename = config.DEFAULT_OPTIONS_NAME

    @property
    def filename(self):
        return self._filename

    @property
    def folder(self):
        return self._folder

    @property
    def coupled(self):
        """
        :return: True if options has been already coupled with the file on disk
        :rtype: bool
        """
        return self.__coupled

    def couple_with(self, path):
        # logging.info("Couple with: %s" % path)
        self.path = path
        self.__coupled = True
        for group in self.__groups:
            group.saved(emit=False)
        self.saved()

    @classmethod
    def default(cls):
        """:rtype: Options"""
        default_options = cls(
            numerics=Numerics.default(),
            wafer_process=WaferProcess.default(),
            mask=Mask.default(),
            imaging_tool=ImagingTool.default(),
            exposure_focus=ExposureFocus.default(),
            peb=PostExposureBake.default(),
            development=Development.default(),
            metrology=Metrology.default(),
        )
        return default_options

    @classmethod
    def empty(cls):
        return cls(
            numerics=Numerics.empty(),
            wafer_process=WaferProcess.empty(),
            mask=Mask.empty(),
            imaging_tool=ImagingTool.empty(),
            exposure_focus=ExposureFocus.empty(),
            peb=PostExposureBake.empty(),
            development=Development.empty(),
            metrology=Metrology.empty(),
        )

    def report(self):
        return ("""<table border="0">
            <tr>
                <td valign="top">%(numerics)s</td>
                <td valign="top">%(exposure_focus)s</td>
            </tr>
            <tr>

                <td valign="top">%(wafer_process)s</td>
                <td valign="top">%(resist)s</td>
            </tr>
            <tr>
                <td valign="top">%(mask)s</td>
                <td valign="top">%(imaging_tool)s</td>
            </tr>
            <tr>
                <td valign="top">%(development)s</td>
                <td valign="top">%(peb)s</td>
            </tr>
            <tr>
                <td valign="top">%(metrology)s</td>
            </tr>
        </table>""" % {
            "numerics": self.numerics.report(),
            "wafer_process": self.wafer_process.report(),
            "resist": self.wafer_process.resist.report(),
            "mask": self.mask.report(),
            "imaging_tool": self.imaging_tool.report(),
            "exposure_focus": self.exposure_focus.report(),
            "peb": self.peb.report(),
            "development": self.development.report(),
            "metrology": self.metrology.report(),
        })

    def export(self):
        return {group.identifier: group.export() for group in self.groups}

    def save(self, path):
        if not path:
            return

        data = self.export()

        # import json
        # logging.info("Save data:\n%s" % json.dumps(data, indent=4))
        # import time
        # time.sleep(0.1)

        with open(path, "wb") as options_file:
            options_file.write(bson.dumps(data))

        self.couple_with(path)

    def open(self, path):
        if not path:
            return

        with open(path, "rb") as options_file:
            data = bson.loads(options_file.read())

        # import json
        # logging.info("Parse data:\n%s" % json.dumps(data, indent=4))
        # import time
        # time.sleep(0.1)

        errors = []

        for group in self.__groups:
            try:
                # logging.debug("Load options group %s" % group.name)
                group_data = data[group.identifier]
                try:
                    group.parse(group_data)
                except PluginNotFoundError as error:
                    group.assign(type(group).default())
                    errors.append(OptionsParseError(error.message))
                except orm.UnknownObjectTypeError as error:
                    group.assign(type(group).default())
                    errors.append(OptionsParseError(error.message))
            except KeyError:
                group.assign(type(group).default())
                errors.append(OptionsParseError("%s data not found in file" % group.identifier))

        self.couple_with(path)

        if errors:
            raise OptionsLoadErrors(errors, self)

    @classmethod
    def load(cls, path):
        """
        :rtype: Options
        """
        with open(path, "rb") as options_file:
            data = bson.loads(options_file.read())

        # import json
        # logging.info("Load data:\n%s" % json.dumps(data, indent=4))
        # import time
        # time.sleep(0.1)

        errors = []
        kwargs = dict()

        for group_class in [Numerics, WaferProcess, Mask, ImagingTool, ExposureFocus, PostExposureBake, Development]:
            try:
                logging.debug("Load options group %s" % group_class.name)
                group_data = data[group_class.name]
                try:
                    kwargs[group_class.name] = group_class.load(group_data)
                except PluginNotFoundError as error:
                    kwargs[group_class.name] = group_class.default()
                    errors.append(OptionsParseError(error.message))
                except orm.UnknownObjectTypeError as error:
                    kwargs[group_class.name] = group_class.default()
                    errors.append(OptionsParseError(error.message))
            except KeyError:
                kwargs[group_class.name] = group_class.default()
                errors.append(OptionsParseError("%s data not found in file" % group_class.name))

        result = cls(
            numerics=kwargs[Numerics.identifier], wafer_process=kwargs[WaferProcess.identifier], mask=kwargs[Mask.identifier],
            imaging_tool=kwargs[ImagingTool.identifier], exposure_focus=kwargs[ExposureFocus.identifier],
            peb=kwargs[PostExposureBake.identifier], development=kwargs[Development.identifier])

        result.couple_with(path)

        if errors:
            raise OptionsLoadErrors(errors, result)

        return result