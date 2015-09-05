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
import re
import StringIO
import numpy
import logging as module_logging

import config
import clipper
import gdsii.library
import gdsii.elements

import orm
import helpers


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)


def unique_rows(array):
    ncols = array.shape[1]
    dtype = array.dtype.descr * ncols
    struct = array.view(dtype)
    unique = numpy.unique(struct)
    return unique.view(array.dtype).reshape(-1, ncols)


def txt2array(text, ndmin=1):
    """
    :type text: str
    :rtype: numpy.ndarray
    """
    # noinspection PyTypeChecker
    return numpy.loadtxt(StringIO.StringIO(text), ndmin=ndmin)


class GenericParserError(Exception):
    pass


class UnableParseError(GenericParserError):
    pass


class WrongParserError(GenericParserError):
    pass


class ParserInterface(object):

    __meta_class__ = abc.ABCMeta

    def __init__(self, extension_map=None):
        self.extension_map = extension_map if extension_map is not None else dict()

    @abc.abstractmethod
    def name(self):
        """:rtype: str"""
        pass

    @abc.abstractmethod
    def parse(self, path):
        """
        :param str path: Path to the file object
        :rtype: orm.GenericObject
        """
        pass

    def __getitem__(self, item):
        """
        :param str item: Path to Prolith file being parsed
        """
        _, ext = os.path.splitext(item)

        try:
            return self.extension_map[ext.lower()]
        except KeyError:
            raise UnableParseError("Unknown file extension %s" % ext)


class Version(object):

    class ParseError(UnableParseError):
        pass

    @staticmethod
    def _normalize(v):
        return [int(x) for x in re.sub(r'(\.0+)*$', '', v).split(".")]

    def __init__(self, value):
        """:type value: str"""
        self.__value = value
        try:
            self.__version = self._normalize(value)
        except (KeyError, ValueError):
            raise Version.ParseError("Version number can't be parsed")

    def __cmp__(self, other):
        return cmp(self.__version, other.__version)

    def __str__(self):
        return self.__value


class ProlithFormat(object):

    PUPIL_FILTER_TYPE_RADIUS = 0
    PUPIL_FILTER_TYPE_GRID = 1

    DEV_RATE_TYPE_PAC = 0
    DEV_RATE_TYPE_EXPOSURE = 1

    RESIST_NEGATIVE = 0
    RESIST_POSITIVE = 1

    RESIST_CONVENTIONAL = 0
    RESIST_CHEMICAL_AMPLIFIED = 1

    RESIST_EXPOSURE_MODEL_TYPE = 1

    RESIST_PEB_DIFFUSION_MODEL = 1
    RESIST_PEB_RXD_MODEL = 2


class ProlithParser(ParserInterface):

    COMMENT_CHAR = ";"

    SUPPORTED_VERSIONS = [Version("1.2.3.4")]

    JUNK_PATTERN = re.compile(r"""^\s*$|\s*;.*$""", re.MULTILINE)

    # It's a witchcraft be carefully... I was near to tear it into shreds...
    SECTIONS_PATTERN = re.compile(r"""\[Version](?:\r\n?|\n)(?P<Version>[^\[]*)
\[Parameters](?:\r\n?|\n)(?P<Parameters>[^\[]*)
(?:\[(?i)Data](?:\r\n?|\n)(?P<Data>[^\[]*))?
(?:\[Comments](?:\r\n?|\n)(?P<Comments>[^\[]*))?
(?:\[Develop\sParameters](?:\r\n?|\n)(?P<Develop>[^\[]*))?
(?:\[PAB\sParameters](?:\r\n?|\n)(?P<PAB>[^\[]*))?
(?:\[PEB\sParameters](?:\r\n?|\n)(?P<PEB>[^\[]*))?
(?:\[Exposure\sParameters](?:\r\n?|\n)(?P<Exposure>[^\[]*))?""", re.DOTALL | re.VERBOSE)

    # This regex return list of dictionary with next keys:
    # transmittance, phase, group, points
    POLYGON_PATTERN = re.compile(r"""Polygon\(
                    (?P<transmittance>[-+]?[0-9]*\.?[0-9]+),\ *
                    (?P<phase>[-+]?[0-9]*\.?[0-9]+),\ *
                    (?P<group>[-+]?[0-9]*\.?[0-9]+)\ *\)
                    (?:\r\n?|\n)\{(?:\r\n?|\n)
                    (?P<points>(?:\ *[-+]?[0-9]*\.?[0-9]+,\ [-+]?[0-9]*\.?[0-9]+(?:\r\n?|\n))+)
                    }""", re.VERBOSE)

    # ------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def dictify(separated, names):
        """
        Created dictionary from list of values and names for keys and also clean all comment started with
        ProlithParser.COMMENT_CHAR if any occurred. Moreover control if next value is not empty or not equal to the
        new Prolith format section.

        :param list of str separated: Separated values to generate dictionary
        :param list of str names: Name for result dictionary
        :rtype: dict from str to str
        """
        results = dict.fromkeys(names, None)

        for line, name in zip(separated, names):
            value = line.split(ProlithParser.COMMENT_CHAR)[0].strip()
            """:type: str"""
            if not value or value.startswith('[') and value.endswith(']'):
                break
            results[name] = value

        return results

    @staticmethod
    def get_parameters(sections, names, directory="Parameters"):
        """
        :param dict from str to str sections: Input data
        :param list of str names: Name for result dictionary
        :param str directory: Determine from which directory parameter will be extracted
        :rtype: dict from str to str
        """
        return ProlithParser.dictify(sections[directory].splitlines(), names)

    # ------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def load_data_array(model, sections):
        """
        :type model: type
        :type sections: dict from str to str
        :rtype: list of orm.Generic
        """
        array = txt2array(sections["Data"].strip(), ndmin=2)
        return [model(*args) for args in unique_rows(array)]

    def load_generic_object(self, object_model, data_model, sections):
        """
        :type object_model: type
        :type data_model: type
        :type sections: dict from str to str
        :rtype: orm.Generic
        """
        name = self.get_parameters(sections, ["name"])["name"]
        array = self.load_data_array(data_model, sections)
        return object_model(name, array)

    # ------------------------------------------------------------------------------------------------------------------

    def load_material(self, sections):
        """:rtype: orm.Material, list of orm.Generic"""
        logging.debug("Load material data")
        return self.load_generic_object(orm.Material, orm.MaterialData, sections)

    def load_source_shape(self, sections):
        """:rtype: orm.SourceShape, list of orm.Generic"""
        logging.debug("Load source shape data")
        return self.load_generic_object(orm.SourceShape, orm.SourceShapeData, sections)

    def load_pupil_filter(self, sections):
        """
        :type sections: dict from str to str
        :rtype: orm.PupilFilter
        """
        logging.debug("Load pupil filter data")
        prms = self.get_parameters(sections, ["name", "type", "step"])
        if int(prms["type"]) != ProlithFormat.PUPIL_FILTER_TYPE_RADIUS:
            raise UnableParseError("Only radius format data supported")
        array = self.load_data_array(orm.PupilFilterData, sections)
        """:type: list of PupilFilterData"""
        return orm.PupilFilter(prms["name"], array)

    def load_development_rate(self, sections):
        """
        :type sections: dict from str to str
        :rtype: orm.DeveloperSheet
        """
        logging.debug("Load developer rate data")
        prms = self.get_parameters(sections, ["name", "type", "is_depth", "steps"])
        if int(prms["type"]) != ProlithFormat.DEV_RATE_TYPE_PAC:
            raise UnableParseError("Only R(m) developer rate dependence supported")

        is_depth = int(prms["is_depth"])

        if is_depth:
            steps = int(prms["steps"])
            data_section = sections["Data"].splitlines()
            depth_array = txt2array(data_section[0])
            data_array = txt2array("\n".join(data_section[1:]))
            if len(depth_array) != steps or data_array.shape[1] != steps+1:
                raise UnableParseError("Number of columns %s not equals to number of steps %s" %
                                       (data_array.shape[1], steps))

            data = list()
            for k, depth in enumerate(depth_array):
                for s, rate in enumerate(data_array[:, k+1]):
                    pac = data_array[s, 0]
                    data.append(orm.DeveloperSheetData(pac, rate, depth))
        else:
            data = self.load_data_array(orm.DeveloperSheetData, sections)

        return orm.DeveloperSheet(prms["name"], bool(is_depth), data)

    # noinspection PyMethodMayBeStatic
    def load_illumination(self, sections):
        """:rtype: orm.Illumination, list of orm.Generic"""
        logging.debug("Load illumination data")
        return self.load_generic_object(orm.Illumination, orm.IlluminationData, sections)

    def load_polarization(self, sections):
        """:rtype: orm.Polarization, list of orm.Generic"""
        logging.debug("Load polarization data")
        return self.load_generic_object(orm.Polarization, orm.PolarizationData, sections)

    def load_temperature_profile(self, sections):
        """:rtype: orm.TemperatureProfile, list of orm.Generic"""
        logging.debug("Load temperature profile data")
        return self.load_generic_object(orm.TemperatureProfile, orm.TemperatureProfileData, sections)

    @staticmethod
    def parse_mask_region(data):
        """
        Generate new regions using string of floating-point values array specified in the next format:
            x1,y1
            x2,y2
            :
            xn,yn

        :param data: Geometry data of region specified as string contained points array
        """
        region = orm.Region(float(data["transmittance"]), float(data["phase"]), orm.GeometryShape.Polygon)
        for line in data["points"].strip().splitlines():
            p = line.strip().split(",")
            region.add(orm.Point(float(p[0]), float(p[1])))
        return region

    @staticmethod
    def str2bbox(value):
        """
        Convert string of four floating-point value represent bounding box to polygon

        :param str value: Prolith bounding box string representation
        :rtype: orm.Geometry
        """
        return orm.Geometry.rectangle(*reversed([float(v) for v in value.split(",")]))

    # noinspection PyMethodMayBeStatic
    def load_mask(self, sections):
        """
        :type sections: dict from str to str
        :rtype: orm.Mask
        """
        logging.debug("Load mask 2D data")

        # Section parameters contain fixed data. Values saved with the next order.
        prms = self.get_parameters(sections, ["name", "boundary", "sim_region", "background",
                                              "phase", "critical_shape_step", "generate_cse", "clean"])

        # Create mask base object
        mask = orm.Mask(
            name=prms["name"],
            background=float(prms["background"]),
            phase=float(prms["phase"]),
            boundary=ProlithParser.str2bbox(prms["boundary"]),
            sim_region=ProlithParser.str2bbox(prms["sim_region"]))

        # Parsing polygons data sections
        for match in self.POLYGON_PATTERN.finditer(sections["Data"]):
            region = ProlithParser.parse_mask_region(match.groupdict())
            # TODO: Consider about polygon clipping by dimensions
            mask.add_region(region)

        return mask

    def _parse_developer(self, sections, resist_name):
        header = ["number_of_developers", "model", "developer_used"]

        prms = self.get_parameters(sections, header, directory="Develop")

        if int(prms["number_of_developers"]) != 1:
            raise UnableParseError("Only one developer supported")

        # Development rate in sheet data (Prolith not store which of rate are used)
        if prms["developer_used"] == "0":
            return None

        # If User Defined then used parameters otherwise bad format
        if prms["developer_used"] != "User Defined":
            raise UnableParseError("Bad developer used")

        try:
            model = (self.select(orm.DevelopmentModel).
                     filter(orm.DevelopmentModel.prolith_id == int(prms["model"])).one())
            """:type: orm.DevelopmentModel"""
        except orm.NoResultFound:
            raise UnableParseError("Not supported Prolith resist development model")

        header.extend([arg.name for arg in model.args])
        header.extend(["Surface Rate", "Inhibition"])

        prms = self.get_parameters(sections, header, directory="Develop")

        values = [float(prms[arg.name]) for arg in model.args]

        return orm.DeveloperExpr(name="Dev%s" % resist_name,
                                 model=model, values=values,
                                 surface_rate=float(prms["Surface Rate"]), inhibition_depth=float(prms["Inhibition"]),
                                 desc="Development model expression for %s resist" % resist_name, temporary=True)

    def _parse_exposure(self, sections):
        prms = self.get_parameters(sections, ["model_type", "values"], directory="Exposure")

        if int(prms["model_type"]) != ProlithFormat.RESIST_EXPOSURE_MODEL_TYPE:
            raise UnableParseError("Unsupported Prolith exposure model type")

        prms = self.dictify(prms["values"].split(), ["wavelength", "A", "B", "C", "n_unexposed", "n_exposed"])

        if float(prms["n_unexposed"]) != float(prms["n_exposed"]):
            raise UnableParseError("Real part of the refractive index changing during exposure process unsupported")

        return orm.ExposureParameters(float(prms["wavelength"]), float(prms["A"]), float(prms["B"]),
                                      float(prms["C"]), float(prms["n_unexposed"]))

    def _parse_peb(self, sections):
        prms = self.get_parameters(sections, ["model_type", "Ea", "LnAr"], directory="PEB")

        if int(prms["model_type"]) != ProlithFormat.RESIST_PEB_DIFFUSION_MODEL:
            raise UnableParseError("Only Diffusion PEB model supported")

        return orm.PebParameters(float(prms["Ea"]), float(prms["LnAr"]))

    # noinspection PyMethodMayBeStatic
    def load_resist(self, sections):
        """
        :type sections: dict from str to str
        :rtype: orm.Resist
        """
        logging.debug("Load resist")

        prms = self.get_parameters(sections, ["name", "vendor", "read_only", "tone", "type"])

        if int(prms["tone"]) != ProlithFormat.RESIST_POSITIVE:
            raise UnableParseError("Only positive resist tone is supported")

        if int(prms["type"]) != ProlithFormat.RESIST_CONVENTIONAL:
            raise UnableParseError("Only conventional resist types are supported")

        exposure_prms = self._parse_exposure(sections)
        peb_prms = self._parse_peb(sections)
        develop_prms = self._parse_developer(sections, prms["name"])
        resist = orm.Resist(prms["name"], sections["Comments"], exposure_prms, peb_prms, develop_prms)

        return resist

    # ------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def _parse_sections(data):
        """:type data: str"""
        # Clean all the comments
        data = ProlithParser.JUNK_PATTERN.sub('', data) + "\n"

        try:
            # noinspection PyTypeChecker
            sections = next(ProlithParser.SECTIONS_PATTERN.finditer(data)).groupdict()
        except StopIteration:
            raise WrongParserError

        for key, value in sections.iteritems():
            if value is not None:
                sections[key] = value.strip()

        return sections

    def __init__(self):
        super(ProlithParser, self).__init__(
            extension_map={
                ".mat": self.load_material,
                ".src": self.load_source_shape,
                ".fil": self.load_pupil_filter,
                ".dev": self.load_development_rate,
                ".ill": self.load_illumination,
                ".pol": self.load_polarization,
                ".tpr": self.load_temperature_profile,
                ".msk": self.load_mask,
                ".res": self.load_resist})

        self.select = None
        """:type: (sqlalchemy.orm.session.Session, tuple, dict) -> sqlalchemy.orm.Query or None"""

    def parse(self, path):
        """
        :param str path: Path to the file object
        :rtype: orm.Generic
        """
        with open(path) as datafile:
            data = datafile.read()

        sections = self._parse_sections(data)
        version = Version(sections["Version"])

        # if version not in ProlithParser.SUPPORTED_VERSIONS:
        #     raise UnableParseError("Unsupported format version %s" % version)

        try:
            return self[path](sections)
        except ValueError as error:
            raise UnableParseError("Prolith parsing error:\nStandardError: %s" % error.message)

    def name(self):
        return "Prolith"


class LayoutParser(ParserInterface):

    @staticmethod
    def merge(polygons):
        paths = clipper.Paths()
        for polygon in polygons:
            xy = polygon.xy if polygon.xy[0] != polygon.xy[-1] else polygon.xy[:-1]
            path = clipper.Path([clipper.IntPoint(*p) for p in xy])
            paths.append(path)
        clipper.SimplifyPolygons(paths, clipper.pftNonZero | clipper.pftEvenOdd | clipper.pftPositive)
        paths = clipper.CutHoles(clipper.Paths(paths))
        # print paths
        return paths

    @staticmethod
    def load_gds(path):
        with open(path, "r") as gds_stream:
            gds_lib = gdsii.library.Library.load(gds_stream)

        # Coordinates factor to set all coordinates in nanometers
        factor = gds_lib.physical_unit / 1.0E-9

        if len(gds_lib) != 1:
            raise UnableParseError("GDSII file should contains one cell only")

        cell = gds_lib[0]
        """:type: gdsii.elements.Cell"""

        polygons = filter(lambda item: isinstance(item, gdsii.elements.Boundary), cell)
        """:type: list[gdsii.elements.Boundary]"""

        # Get boundary polygon
        bnd_num, bnd_dt = config.GdsLayerMapping.boundary_layer()
        boundary_polygons = filter(lambda item: item.layer == bnd_num and item.data_type == bnd_dt, polygons)

        if len(boundary_polygons) != 1:
            raise UnableParseError("Boundary layer should contains only one polygon")

        if boundary_polygons[0].xy[0] == boundary_polygons[0].xy[-1]:
            boundary_xy = boundary_polygons[0].xy[:-1]
        else:
            boundary_xy = boundary_polygons[0].xy

        # GDSII format first and last point of the polygon must be matched.
        # So run over all point except the last
        boundary = orm.Geometry(
            shape=orm.GeometryShape.Polygon,
            points=[orm.Point(*p)*factor for p in boundary_xy]).convert2rect()

        if boundary is None:
            raise UnableParseError("Boundary polygon is not rectangle: %s" % boundary_xy)

        # Parse polygons
        not_mapped = dict()
        mapped_polygons = dict()

        regions = []
        for polygon in polygons:

            if polygon == boundary_polygons[0]:
                continue

            layer_number = "%s.%s" % (polygon.layer, polygon.data_type)
            try:
                config.GdsLayerMapping[layer_number]
            except KeyError:
                if layer_number not in not_mapped:
                    not_mapped[layer_number] = 1
                else:
                    not_mapped[layer_number] += 1
            else:
                if layer_number not in mapped_polygons:
                    mapped_polygons[layer_number] = list()
                mapped_polygons[layer_number].append(polygon)

        for layer_number in not_mapped:
            logging.warning("Loaded %s object from GDS layer %s not mapped!" % (not_mapped[layer_number], layer_number))

        offset = boundary[0] + (boundary[1] - boundary[0]) / 2.0

        for layer_number, polygons_list in mapped_polygons.items():
            polygons = LayoutParser.merge(polygons_list)
            for polygon in polygons:
                layer_property = config.GdsLayerMapping[layer_number]
                # Move origin of layout to boundary left-bottom point, and polygon now is numpy array
                # noinspection PyTypeChecker
                regions.append(orm.Region(
                    transmittance=layer_property["transmittance"],
                    phase=layer_property["phase"],
                    shape=orm.GeometryShape.Polygon,
                    points=[(orm.Point(p.X, p.Y)*factor - offset) for p in polygon]))

        # Move boundary to origin
        boundary -= offset

        return orm.Mask(
            name=cell.name,
            background=float(config.GdsLayerMapping["background"]["transmittance"]),
            phase=float(config.GdsLayerMapping["background"]["phase"]),
            boundary=boundary,
            sim_region=boundary.clone(),
            regions=regions)

    def __init__(self):
        super(LayoutParser, self).__init__(
            extension_map={
                ".gdsii": LayoutParser.load_gds,
                ".gds2": LayoutParser.load_gds,
                ".gds": LayoutParser.load_gds})
        self.select = None
        """:type: (sqlalchemy.orm.session.Session, tuple, dict) -> sqlalchemy.orm.Query or None"""

    def parse(self, path):
        """
        :param str path: Path to the file object
        :rtype: orm.Generic
        """
        if os.path.getsize(path) > config.Configuration.maximum_gds_size:
            raise UnableParseError("Layout file is too large!")

        return self[path](path)

    def name(self):
        return "LayoutParser"


class GenericParser(ParserInterface):

    __available_drivers__ = [ProlithParser, LayoutParser]
    """:type: list of type"""

    def __init__(self):
        super(GenericParser, self).__init__()
        self.__drivers = [cls() for cls in GenericParser.__available_drivers__]
        """:type: list of ParserInterface"""
        self.__select = None
        """:type: (sqlalchemy.orm.session.Session, tuple, dict) -> sqlalchemy.orm.Query or None"""

    @property
    def selector(self):
        """:rtype: (sqlalchemy.orm.session.Session, tuple, dict) -> sqlalchemy.orm.Query or None"""
        return self.__select

    @selector.setter
    def selector(self, value):
        """:type value: (sqlalchemy.orm.session.Session, tuple, dict) -> sqlalchemy.orm.Query or None"""
        self.__select = value
        for driver in self.__drivers:
            driver.select = self.__select

    def parse(self, path):
        """
        :param str path: Path to the file object
        :rtype: orm.Generic
        """
        if not os.path.isfile(path):
            raise GenericParserError("File can't be opened")

        for driver in self.__drivers:
            try:
                return driver.parse(path)
            except UnableParseError as error:
                error.message = "%s: %s" % (driver.name(), error.message)
                raise error
            except WrongParserError:
                continue

        raise GenericParserError("File format was not understood, no appropriate driver found")

    def name(self):
        return "Generic"