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


from ctypes import POINTER, CFUNCTYPE, Structure, cast
from ctypes import c_void_p, c_char_p, c_double, c_int
import inspect


__author__ = 'Alexei Gladkikh'


class PluginCommonError(Exception):
    pass


class PluginNotFoundError(PluginCommonError):
    pass


class PluginRegistry(object):

    def __init__(self):
        self.__container_id = dict()
        self.__container_name = dict()

    def get_by_id(self, plugin_id):
        """:rtype: plugins.Plugin"""
        try:
            return self.__container_id[plugin_id]
        except KeyError:
            raise PluginNotFoundError("Plugin with id %s not found" % plugin_id)

    def get_by_name(self, plugin_name):
        """:rtype: plugins.Plugin"""
        try:
            return self.__container_name[plugin_name]
        except KeyError:
            raise PluginNotFoundError("Plugin with name %s not found" % plugin_name)

    def add_plugin(self, plugin):
        """:type plugin: plugins.Plugin"""
        self.__container_id[plugin.record.id] = plugin
        self.__container_name[plugin.record.name] = plugin


# Plugin registry must be in pcpi module not in plugins module otherwise it result in circular imports
PLUGIN_REGISTRY = PluginRegistry()


class CPluginInterface(Structure):
    plugin_id = None
    """:type: int"""
    name = None
    """:type: str"""
    desc = None
    """:type: str"""


def deref(p):
    return p.contents.value if p else None


def ro_property(attribute):
    return property(fget=lambda self: getattr(self, attribute))


def rw_property(attribute):
    return property(fget=lambda self: getattr(self, attribute),
                    fset=lambda self, value: setattr(self, attribute, value))


# noinspection PyPep8Naming
class _variable_part_t(Structure):
    _fields_ = [
        ("_name", c_char_p),
        ("_defv", c_double),
        ("_min", POINTER(c_double)),
        ("_max", POINTER(c_double))
    ]

    name = property(lambda self: self._name)
    """:type: str"""
    defv = property(lambda self: self._defv)
    """:type: float"""
    min = property(lambda self: deref(self._min))
    """:type: float or None"""
    max = property(lambda self: deref(self._max))
    """:type: float or None"""

    def __str__(self):
        vmin = "Min %.2f, " % self.min if self.min is not None else str()
        vmax = "Max %.2f" % self.max if self.max is not None else str()
        return "Name: \"%s\", %s%s Default: %.2f" % (self.name, vmin, vmax, self.defv)


# ------------------------------------------ Development model Plugin --------------------------------------------------


# noinspection PyPep8Naming
class dev_model_arg_t(_variable_part_t):
    pass


# Return value: double
# Parameters: pac, depth, values
dev_model_expr_t = CFUNCTYPE(c_double, c_double, c_double, POINTER(c_double))


# noinspection PyPep8Naming
class dev_model_t(CPluginInterface):
    plugin_id = 1

    _fields_ = [
        ("_prolith_id", POINTER(c_int)),
        ("_name", c_char_p),
        ("_desc", c_char_p),
        ("_expr", dev_model_expr_t),
        ("_args_count", c_int),
        ("_args", POINTER(dev_model_arg_t))
    ]

    prolith_id = property(lambda self: deref(self._prolith_id))
    """:type: int or None"""
    name = property(lambda self: self._name)
    """:type: str"""
    desc = property(lambda self: self._desc)
    """:type: str"""
    expr = property(lambda self: self._expr)
    """:type: dev_model_expr_t"""
    args_count = property(lambda self: self._args_count)
    """:type: int"""
    args = property(lambda self: self._args)
    """:type: list of dev_model_arg_t"""

    def __str__(self):
        args = "\n".join(["\t%d. %s" % (k, self.args[k]) for k in xrange(self.args_count)])
        return ("Name: \"%s\"\nDesc: %s\nExpr: %s\nCount: %d\nProlith Id: %s\nArgs:\n%s" %
                (self.name, self.desc, self.expr, self.args_count, self.prolith_id, args))


# ------------------------------------------------ Mask Plugin ---------------------------------------------------------


# noinspection PyPep8Naming
class point_t(Structure):

    _fields_ = [
        ("_x", c_double),
        ("_y", c_double)
    ]

    x = rw_property("_x")
    """:type: float"""
    y = rw_property("_y")
    """:type: float"""


# noinspection PyPep8Naming
class mask_region_t(Structure):

    _fields_ = [
        ("_transmittance", c_double),
        ("_phase", c_double),
        ("_length", c_int),
        ("_points", POINTER(point_t))
    ]

    transmittance = rw_property("_transmittance")
    """:type: float"""
    phase = rw_property("_phase")
    """:type: float"""
    length = ro_property("_length")
    """:type: int"""
    points = ro_property("_points")
    """:type: list of point_t"""


# noinspection PyPep8Naming
class mask_parameter_t(_variable_part_t):
    pass


# noinspection PyPep8Naming
class mask_t(Structure):

    _fields_ = [
        ("_boundary", mask_region_t),
        ("_regions_count", c_int),
        ("_regions", POINTER(mask_region_t)),
    ]

    boundary = ro_property("_boundary")
    """:type: mask_region_t"""
    regions_count = ro_property("_regions_count")
    """:type: int"""
    regions = ro_property("_regions")
    """:type: list of mask_region_t"""


# Return value: int - status (0 - Ok)
# Parameters: mask, parameters
mask_create_t = CFUNCTYPE(c_int, POINTER(mask_t), POINTER(c_double))


# noinspection PyPep8Naming
class mask_plugin_t(CPluginInterface):
    plugin_id = 0

    _fields_ = [
        ("_name", c_char_p),
        ("_desc", c_char_p),
        ("_dimensions", c_int),
        ("_create", mask_create_t),
        ("_parameters_count", c_int),
        ("_parameters", POINTER(mask_parameter_t))
    ]

    name = ro_property("_name")
    """:type: str"""
    desc = ro_property("_desc")
    """:type: str"""
    dimensions = ro_property("_dimensions")
    """:type: int"""
    create = ro_property("_create")
    """:type: mask_create_t"""
    parameters_count = ro_property("_parameters_count")
    """:type: int"""
    parameters = ro_property("_parameters")
    """:type: mask_parameter_t"""


# --------------------------------------------- Source Shape Plugin ----------------------------------------------------

# noinspection PyPep8Naming
class source_shape_parameter_t(_variable_part_t):
    pass


# Return value: double - intensity value
# Parameters: direction cosine x, y, and parameters
source_shape_expr_t = CFUNCTYPE(c_double, c_double, c_double, POINTER(c_double))


# noinspection PyPep8Naming
class source_shape_plugin_t(CPluginInterface):
    plugin_id = 2

    _fields_ = [
        ("_name", c_char_p),
        ("_desc", c_char_p),
        ("_expression", source_shape_expr_t),
        ("_parameters_count", c_int),
        ("_parameters", POINTER(source_shape_parameter_t))
    ]

    name = ro_property("_name")
    """:type: str"""
    desc = ro_property("_desc")
    """:type: str"""
    expr = ro_property("_expression")
    """:type: source_shape_expr_t"""
    parameters_count = ro_property("_parameters_count")
    """:type: int"""
    parameters = ro_property("_parameters")
    """:type: source_shape_parameter_t"""


# --------------------------------------------- Pupil Filter Plugin ----------------------------------------------------

# noinspection PyPep8Naming
class pupil_filter_parameter_t(_variable_part_t):
    pass


# noinspection PyPep8Naming
class c_complex(Structure):
    _fields_ = [("_real", c_double), ("_imag", c_double)]
    real = rw_property("_real")
    imag = rw_property("_imag")


# Return value: double - diffraction term coefficient value
# Parameters: direction cosine x, y, and parameters
pupil_filter_expr_t = CFUNCTYPE(c_complex, c_double, c_double, POINTER(c_double))


# noinspection PyPep8Naming
class pupil_filter_plugin_t(CPluginInterface):
    plugin_id = 5

    _fields_ = [
        ("_name", c_char_p),
        ("_desc", c_char_p),
        ("_expression", pupil_filter_expr_t),
        ("_parameters_count", c_int),
        ("_parameters", POINTER(pupil_filter_parameter_t))
    ]

    name = ro_property("_name")
    """:type: str"""
    desc = ro_property("_desc")
    """:type: str"""
    expr = ro_property("_expression")
    """:type: pupil_filter_expr_t"""
    parameters_count = ro_property("_parameters_count")
    """:type: int"""
    parameters = ro_property("_parameters")
    """:type: pupil_filter_parameter_t"""


# ----------------------------------------------------------------------------------------------------------------------


plugin_types = {cls.plugin_id: cls for cls in globals().values()
                if inspect.isclass(cls) and issubclass(cls, CPluginInterface) and cls.plugin_id is not None}


ENTRY_POINT = "PluginDescriptor"


# noinspection PyPep8Naming
class plugin_descriptor_t(Structure):
    _fields_ = [
        ("_plugin_type", c_int),
        ("_plugin_entry", c_void_p)
    ]

    plugin_type = property(lambda self: self._plugin_type)
    """:type: int"""

    @property
    def plugin_entry(self):
        """:rtype: CPluginInterface"""
        return cast(self._plugin_entry, POINTER(plugin_types[self.plugin_type])).contents