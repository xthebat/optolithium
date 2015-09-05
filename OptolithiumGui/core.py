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

import optolithiumc as oplc
import logging as module_logging
import helpers

from numpy import angle
from qt import QtCore, Signal, connect, Slot
from metrics import IMAGE_NEGATIVE, IMAGE_POSITIVE, \
    CONTOUR_METRICS, IMAGE_METRICS, PROFILE_METRICS, STANDING_WAVES_METRICS


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.INFO)
helpers.logStreamEnable(logging)

core_logging = oplc.OptolithiumCoreLog()
core_logging.set_verbose_level(4)

LOG_VERBOSE_0 = 0

# set_printoptions(linewidth=nan, precision=3, threshold=nan)


class CoreSimulationOptions(object):

    def __init__(self, options):
        """:type options: options.structures.Options"""
        self.__options = options

        self.__mask = None
        self.__imaging_tool = None
        self.__wafer_stack = None
        self.__exposure = None
        self.__peb = None
        self.__development = None

    @property
    def options(self):
        return self.__options

    def numerics(self, changed=None):
        if changed is not None:
            changed.append(not self.__options.numerics.is_simulated)
        self.__options.numerics.simulated()
        return self.__options.numerics

    def mask(self, changed=None):
        if not self.__options.mask.is_simulated or self.__mask is None:
            if changed is not None:
                changed.append(True)
            self.__mask = self.__options.mask.convert2core()
            self.__options.mask.simulated()
        elif changed is not None:
            changed.append(False)
        return self.__mask

    def imaging_tool(self, changed=None):
        if not self.__options.imaging_tool.is_simulated or self.__imaging_tool is None:
            if changed is not None:
                changed.append(True)
            self.__imaging_tool = self.__options.imaging_tool.convert2core()
            self.__options.imaging_tool.simulated()
        elif changed is not None:
            changed.append(False)
        return self.__imaging_tool

    def wafer_stack(self, changed=None):
        if not self.__options.wafer_process.is_simulated or self.__wafer_stack is None:
            if changed is not None:
                changed.append(True)
            self.__wafer_stack = self.__options.wafer_process.convert2core()
            self.__options.wafer_process.simulated()
        elif changed is not None:
            changed.append(False)
        return self.__wafer_stack

    def exposure(self, changed=None):
        if not self.__options.exposure_focus.is_simulated or self.__exposure is None:
            if changed is not None:
                changed.append(True)
            self.__exposure = self.__options.exposure_focus.convert2core()
            self.__options.exposure_focus.simulated()
        elif changed is not None:
            changed.append(False)
        return self.__exposure

    def post_exposure_bake(self, changed=None):
        if not self.__options.peb.is_simulated or self.__peb is None:
            if changed is not None:
                changed.append(True)
            self.__peb = self.__options.peb.convert2core()
            self.__options.peb.simulated()
        elif changed is not None:
            changed.append(False)
        return self.__peb

    def development(self, changed=None):
        if not self.__options.development.is_simulated or self.__development is None:
            if changed is not None:
                changed.append(True)
            self.__development = self.__options.development.convert2core()
            self.__options.development.simulated()
        elif changed is not None:
            changed.append(False)
        return self.__development


class AbstractStage(QtCore.QObject):

    invalidated = Signal()

    def __init__(self, core_options, metrics, pre_stage=None):
        """
        :type core_options: CoreSimulationOptions
        :type pre_stage: AbstractStage or None
        """
        super(AbstractStage, self).__init__()

        self.__core_options = core_options

        self.__pre_stage = pre_stage
        """:type: AbstractStage or None"""

        if self.__pre_stage is not None:
            self.__pre_stage.add_post_stage(self)

        self.__post_stages = []
        """:type: list of AbstractStage"""

        self.__result = None

        self.__metrics = [metric_class(self) for metric_class in metrics]

    @property
    def name(self):
        """:rtype: str"""
        raise NotImplementedError

    @property
    def pre_stage(self):
        return self.__pre_stage

    def add_post_stage(self, stage):
        """:type: AbstractStage"""
        self.__post_stages.append(stage)

    @property
    def has_result(self):
        return self.__result is not None

    @Slot()
    def invalidate(self):
        # logging.info("Invalidate: %s" % self.__class__.__name__)
        self.__result = None
        for stage in self.__post_stages:
            # if stage.has_result:
            stage.invalidate()
        self.invalidated.emit()

    @property
    def core_options(self):
        return self.__core_options

    @property
    def options(self):
        return self.core_options.options

    def _payload(self):
        """:rtype: optolithiumc.Diffraction or optolithiumc.ResistVolume"""
        raise NotImplementedError

    @property
    def metrics_kwargs(self):
        """:rtype: dict from str"""
        return dict()

    @property
    def metrics(self):
        """:rtype: list of metrology.MetrologyInterface"""
        return self.__metrics

    def calculate(self):
        logging.debug("Calculate %s" % self.__class__.__name__)
        if not self.has_result:
            self.__result = self._payload()
        else:
            logging.debug("%s not changed" % self.__class__.__name__)
        return self.__result


class DiffractionStage(AbstractStage):

    def __init__(self, core_options):
        super(DiffractionStage, self).__init__(core_options, [])

    @property
    def name(self):
        return "Diffraction"

    def _payload(self, *args):
        mask = self.core_options.mask()
        imaging_tool = self.core_options.imaging_tool()

        diffraction = oplc.diffraction(imaging_tool, mask)

        logging.log(
            LOG_VERBOSE_0,
            "Calculated diffraction pattern data:\n"
            "Diffraction terms numbers belong X-Axis:\n%s\n"
            "Diffraction terms numbers belong Y-Axis:\n%s\n"
            "Diffraction direction cosines belong X-Axis:\n%s\n"
            "Diffraction direction cosines belong Y-Axis:\n%s\n"
            "Diffraction terms direction cosines in polar view:\n%s\n"
            "Diffraction terms values:\n%s\n" % (
                diffraction.kx, diffraction.ky,
                diffraction.cx, diffraction.cy,
                diffraction.cxy, diffraction.values
            )
        )

        return diffraction


class AerialImageStage(AbstractStage):

    def __init__(self, core_options, pre_stage):
        super(AerialImageStage, self).__init__(core_options, metrics=IMAGE_METRICS, pre_stage=pre_stage)

    @property
    def name(self):
        return "Aerial Image"

    def _payload(self):
        diffraction = self.pre_stage.calculate()

        numerics = self.core_options.numerics()
        imaging_tool = self.core_options.imaging_tool()
        exposure_focus = self.core_options.exposure()

        otf = oplc.OpticalTransferFunction(imaging_tool, exposure_focus)
        aerial_image = oplc.aerial_image(diffraction, otf, numerics.grid_xy.value)

        logging.log(
            LOG_VERBOSE_0,
            "Calculated aerial image data [%s]:\n"
            "Aerial image X-Axis data:\n%s\n"
            "Aerial image Y-Axis data:\n%s\n"
            "Aerial image values:\n%s\n" % (
                aerial_image.values.shape,
                aerial_image.x,
                aerial_image.y,
                aerial_image.values
            )
        )

        return aerial_image

    @property
    def metrics_kwargs(self):
        return {
            "level": self.options.metrology.aerial_image_level.value
        }


def _magnitude(v):
    return (v * v.conjugate()).real


def _phase(v):
    return angle(v, deg=True)


class StandingWavesStage(AbstractStage):

    def __init__(self, core_options):
        super(StandingWavesStage, self).__init__(core_options, metrics=STANDING_WAVES_METRICS)

    @property
    def name(self):
        return "Standing Waves"

    def _payload(self):
        wafer_stack = self.core_options.wafer_stack()
        wavelength = self.core_options.imaging_tool().wavelength
        resist_indx = wafer_stack.index_of(wafer_stack.resist())
        resist_reflectivity = wafer_stack.reflectivity(resist_indx, wavelength)
        substrate_reflectivity = wafer_stack.reflectivity(resist_indx+1, wavelength)
        return {
            "resist_reflectivity": _magnitude(resist_reflectivity),
            "resist_phase": _phase(resist_reflectivity),
            "substrate_reflectivity": _magnitude(substrate_reflectivity),
            "substrate_phase": _phase(substrate_reflectivity)
        }


class ImageInResistStage(AbstractStage):

    def __init__(self, core_options, pre_stage):
        super(ImageInResistStage, self).__init__(core_options, metrics=IMAGE_METRICS, pre_stage=pre_stage)

    @property
    def name(self):
        return "Image in Resist"

    def _payload(self):
        diffraction = self.pre_stage.calculate()

        numerics = self.core_options.numerics()
        wafer_stack = self.core_options.wafer_stack()
        imaging_tool = self.core_options.imaging_tool()
        exposure = self.core_options.exposure()

        otf = oplc.OpticalTransferFunction(imaging_tool, exposure, wafer_stack)

        image_in_resist = oplc.image_in_resist(diffraction, otf, numerics.grid_xy.value, numerics.grid_z.value)

        logging.log(
            LOG_VERBOSE_0,
            "Calculated image in resist data [%s]:\n"
            "Image in resist X-Axis data:\n%s\n"
            "Image in resist Y-Axis data:\n%s\n"
            "Image in resist Z-Axis data:\n%s\n"
            "Image in resist values:\n%s\n" % (
                image_in_resist.values.shape,
                image_in_resist.x,
                image_in_resist.y,
                image_in_resist.z,
                image_in_resist.values
            )
        )
        return image_in_resist

    @property
    def metrics_kwargs(self):
        return {
            "title": "Relative Intensity",
            "level": self.options.metrology.image_in_resist_level.value,
            "image_tonality": IMAGE_NEGATIVE,
            "tonality": self.options.metrology.mask_tonality.value,
            "height": self.options.metrology.measurement_height.value,
        }


class LatentImageStage(AbstractStage):

    def __init__(self, core_options, pre_stage):
        super(LatentImageStage, self).__init__(core_options, metrics=IMAGE_METRICS, pre_stage=pre_stage)

    @property
    def name(self):
        return "Exposed Latent Image in Resist"

    def _payload(self):
        image_in_resist = self.pre_stage.calculate()

        resist = oplc.ResistWaferLayer.cast(self.core_options.wafer_stack().resist())
        exposure = self.core_options.exposure()

        latent_image = oplc.latent_image(image_in_resist, resist, exposure)

        logging.log(
            LOG_VERBOSE_0,
            "Calculated image in resist data [%s]:\n"
            "Exposed Latent Image in resist X-Axis data:\n%s\n"
            "Exposed Latent Image in resist Y-Axis data:\n%s\n"
            "Exposed Latent Image in resist Z-Axis data:\n%s\n"
            "Exposed Latent Image in resist values:\n%s\n" % (
                latent_image.values.shape,
                latent_image.x,
                latent_image.y,
                latent_image.z,
                latent_image.values
            )
        )
        return latent_image

    @property
    def metrics_kwargs(self):
        return {
            "title": "Relative PAC Concentration",
            "level": self.options.metrology.latent_image_level.value,
            "image_tonality": IMAGE_POSITIVE,
            "tonality": self.options.metrology.mask_tonality.value,
            "height": self.options.metrology.measurement_height.value,
        }


class PebLatentImageStage(AbstractStage):

    def __init__(self, core_options, pre_stage):
        super(PebLatentImageStage, self).__init__(core_options, metrics=IMAGE_METRICS, pre_stage=pre_stage)

    @property
    def name(self):
        return "Latent Image in Resist after PEB"

    def _payload(self):
        latent_image = self.pre_stage.calculate()

        resist = oplc.ResistWaferLayer.cast(self.core_options.wafer_stack().resist())
        peb = self.core_options.post_exposure_bake()

        peb_latent_image = oplc.peb_latent_image(latent_image, resist, peb)

        logging.log(
            LOG_VERBOSE_0,
            "Calculated image in resist data [%s]:\n"
            "PEB Latent Image in resist X-Axis data:\n%s\n"
            "PEB Latent Image in resist Y-Axis data:\n%s\n"
            "PEB Latent Image in resist Z-Axis data:\n%s\n"
            "PEB Latent Image in resist values:\n%s\n" % (
                peb_latent_image.values.shape,
                peb_latent_image.x,
                peb_latent_image.y,
                peb_latent_image.z,
                peb_latent_image.values
            )
        )
        return peb_latent_image

    @property
    def metrics_kwargs(self):
        return {
            "title": "Relative PAC Concentration",
            "level": self.options.metrology.peb_latent_image_level.value,
            "image_tonality": IMAGE_POSITIVE,
            "tonality": self.options.metrology.mask_tonality.value,
            "height": self.options.metrology.measurement_height.value,
        }


class DevelopContoursStage(AbstractStage):

    def __init__(self, core_options, pre_stage):
        super(DevelopContoursStage, self).__init__(core_options, metrics=CONTOUR_METRICS, pre_stage=pre_stage)

    @property
    def name(self):
        return "Develop Time Contours"

    def _payload(self):
        peb_latent_image = self.pre_stage.calculate()

        resist = oplc.ResistWaferLayer.cast(self.core_options.wafer_stack().resist())

        develop_contours = oplc.develop_time_contours(peb_latent_image, resist)

        logging.log(
            LOG_VERBOSE_0,
            "Calculated develop time contours data [%s]:\n"
            "Develop time contours X-Axis data:\n%s\n"
            "Develop time contours Y-Axis data:\n%s\n"
            "Develop time contours Z-Axis data:\n%s\n"
            "Develop time contours values:\n%s\n" % (
                develop_contours.values.shape,
                develop_contours.x,
                develop_contours.y,
                develop_contours.z,
                develop_contours.values
            )
        )
        return develop_contours

    @property
    def metrics_kwargs(self):
        return {
            "level": self.options.development.develop_time.value,
            "image_tonality": IMAGE_POSITIVE,
            "tonality": self.options.metrology.mask_tonality.value,
            "height": self.options.metrology.measurement_height.value,
            "variate_height": self.options.metrology.variate_meas_height.value,
        }


class ResistProfileStage(AbstractStage):

    def __init__(self, core_options, pre_stage):
        super(ResistProfileStage, self).__init__(core_options, metrics=PROFILE_METRICS, pre_stage=pre_stage)

    @property
    def name(self):
        return "Resist Profile"

    def _payload(self):
        develop_contours = self.pre_stage.calculate()
        develop_time = self.core_options.development()
        resist_profile = oplc.resist_profile(develop_contours, develop_time)
        return resist_profile

    @property
    def metrics_kwargs(self):
        return {
            "tonality": self.options.metrology.mask_tonality.value,
            "height": self.options.metrology.measurement_height.value,
            "variate_height": self.options.metrology.variate_meas_height.value,
        }


class Core(QtCore.QObject):

    def __init__(self, options, *args, **kwargs):
        """:type options: options.structures.Options"""
        super(Core, self).__init__(*args, **kwargs)
        self.__options = options
        core_options = CoreSimulationOptions(options)
        self.__standing_waves_stage = StandingWavesStage(core_options)
        self.__diffraction_stage = DiffractionStage(core_options)
        self.__aerial_image_stage = AerialImageStage(core_options, self.__diffraction_stage)
        self.__image_in_resist_stage = ImageInResistStage(core_options, self.__diffraction_stage)
        self.__latent_image_stage = LatentImageStage(core_options, self.__image_in_resist_stage)
        self.__peb_latent_image_stage = PebLatentImageStage(core_options, self.__latent_image_stage)
        self.__develop_contours_stage = DevelopContoursStage(core_options, self.__peb_latent_image_stage)
        self.__resist_profile_stage = ResistProfileStage(core_options, self.__develop_contours_stage)

        self.__stages = [
            self.standing_waves, self.diffraction,
            self.aerial_image, self.image_in_resist,
            self.latent_image, self.peb_latent_image,
            self.develop_contours, self.resist_profile
        ]

        logging.info("Connect numerics signals to core")
        connect(
            self.__options.numerics.changed,
            self.__standing_waves_stage.invalidate,
            self.__aerial_image_stage.invalidate,
            self.__image_in_resist_stage.invalidate
        )

        logging.info("Connect wafer process signals to core")
        connect(
            self.__options.wafer_process.changed,
            self.__standing_waves_stage.invalidate,
            self.__image_in_resist_stage.invalidate,
        )

        logging.info("Connect resist signals to core")
        connect(
            self.__options.wafer_process.resist.changed,
            self.__standing_waves_stage.invalidate,
            self.__develop_contours_stage.invalidate,
        )

        logging.info("Connect mask signals to core")
        connect(
            self.__options.mask.changed,
            self.__diffraction_stage.invalidate
        )

        logging.info("Connect imaging tool signals to core")
        connect(
            self.__options.imaging_tool.changed,
            self.__standing_waves_stage.invalidate,
            self.__diffraction_stage.invalidate,
        )

        logging.info("Connect exposure focus signals to core")
        connect(
            self.__options.exposure_focus.changed,
            self.__aerial_image_stage.invalidate,
            self.__image_in_resist_stage.invalidate
        )

        logging.info("Connect peb signals to core")
        connect(
            self.__options.peb.changed,
            self.__peb_latent_image_stage.invalidate
        )

        logging.info("Connect development signals to core")
        connect(
            self.__options.development.changed,
            self.__resist_profile_stage.invalidate
        )

    @property
    def options(self):
        return self.__options

    def __iter__(self):
        return self.__stages.__iter__()

    standing_waves = property(lambda self: self.__standing_waves_stage)
    diffraction = property(lambda self: self.__diffraction_stage)
    aerial_image = property(lambda self: self.__aerial_image_stage)
    image_in_resist = property(lambda self: self.__image_in_resist_stage)
    latent_image = property(lambda self: self.__latent_image_stage)
    peb_latent_image = property(lambda self: self.__peb_latent_image_stage)
    develop_contours = property(lambda self: self.__develop_contours_stage)
    resist_profile = property(lambda self: self.__resist_profile_stage)