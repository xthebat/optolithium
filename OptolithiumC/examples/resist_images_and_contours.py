__author__ = 'OlaPsema'

import optolithiumc as oplc
import numpy as np
import matplotlib.pyplot as plt


def get_quasar_source_shape_model(x, y, sigma_in, sigma_out, blade_angle):
    xv, yv = np.meshgrid(x, y)
    if blade_angle <= 90.:
        blade_angle = (90. + blade_angle) / 2.
        cond3 = np.abs(yv) <= np.abs(np.tan(np.deg2rad(blade_angle)) * x)
        cond4 = np.abs(xv) <= np.abs(np.tan(np.deg2rad(blade_angle)) * np.transpose(np.array([y])))
    else:
        cond3 = cond4 = 1
    cond1 = ((xv - 0.) ** 2 + (yv - 0.) ** 2) <= sigma_out ** 2
    cond2 = ((xv - 0.) ** 2 + (yv - 0.) ** 2) >= sigma_in ** 2
    val = np.array(cond1 & cond2 & cond3 & cond4, dtype=float)
    plt.imshow(val)
    plt.show()
    val = np.asfortranarray(val / np.sum(val))
    return val


def get_conventional_coherent_source_shape_model(step, x, y):
    xv, yv = np.meshgrid(x, y)
    val = np.array(((xv - 0.) ** 2 + (yv - 0.) ** 2) <= (step / 10.) ** 2, dtype=float)
    plt.imshow(val)
    plt.show()
    return np.asfortranarray(val)


def get_conventional_partially_coherent_source_shape_model(x, y, sigma):
    xv, yv = np.meshgrid(x, y)
    cond = ((xv - 0.) ** 2 + (yv - 0.) ** 2) <= sigma ** 2
    val = np.array(cond, dtype=float)
    plt.imshow(val)
    plt.show()
    val = np.asfortranarray(val / np.sum(val))
    return val


def get_annular_source_shape_model(x, y, sigma_in, sigma_out):
    xv, yv = np.meshgrid(x, y)
    cond1 = ((xv - 0.) ** 2 + (yv - 0.) ** 2) <= sigma_out ** 2
    cond2 = ((xv - 0.) ** 2 + (yv - 0.) ** 2) >= sigma_in ** 2
    val = np.array(cond1 & cond2, dtype=float)
    plt.imshow(val)
    plt.show()
    val = np.asfortranarray(val / np.sum(val))
    return val


def get_dipole_source_shape_model(x, y, center_sigma, radius_sigma):
    xv, yv = np.meshgrid(x, y)
    cond1 = ((xv - center_sigma) ** 2 + (yv - 0.) ** 2) <= radius_sigma ** 2
    cond2 = ((xv + center_sigma) ** 2 + (yv - 0.) ** 2) <= radius_sigma ** 2
    val = np.array(cond1 | cond2, dtype=float)
    plt.imshow(val)
    plt.show()
    val = np.asfortranarray(val / np.sum(val))
    return val


def get_monopole_source_shape_model(x, y, center_x, center_y, radius_sigma):
    xv, yv = np.meshgrid(x, y)
    cond1 = ((xv - center_x) ** 2 + (yv + center_y) ** 2) <= radius_sigma ** 2
    val = np.array(cond1, dtype=float)
    plt.imshow(val)
    plt.show()
    val = np.asfortranarray(val / np.sum(val))
    return val


def get_quadrupole_source_shape_model(x, y, center_sigma, radius_sigma, geometry_type):
    xv, yv = np.meshgrid(x, y)
    if geometry_type == 1:
        center_sigma = center_sigma * np.sqrt(1. / 2.)
        cond1 = ((xv - center_sigma) ** 2 + (yv - center_sigma) ** 2) <= radius_sigma ** 2
        cond2 = ((xv - center_sigma) ** 2 + (yv + center_sigma) ** 2) <= radius_sigma ** 2
        cond3 = ((xv + center_sigma) ** 2 + (yv - center_sigma) ** 2) <= radius_sigma ** 2
        cond4 = ((xv + center_sigma) ** 2 + (yv + center_sigma) ** 2) <= radius_sigma ** 2
    else:
        cond1 = ((xv - center_sigma) ** 2 + (yv - 0.) ** 2) <= radius_sigma ** 2
        cond2 = ((xv + center_sigma) ** 2 + (yv + 0.) ** 2) <= radius_sigma ** 2
        cond3 = ((xv - 0.) ** 2 + (yv - center_sigma) ** 2) <= radius_sigma ** 2
        cond4 = ((xv - 0.) ** 2 + (yv + center_sigma) ** 2) <= radius_sigma ** 2
    val = np.array(cond1 | cond2 | cond3 | cond4, dtype=float)
    plt.imshow(val)
    plt.show()
    val = np.asfortranarray(val / np.sum(val))
    return val


def get_shrinc_source_shape_model(x, y, sigma_out, stripe_width):
    xv, yv = np.meshgrid(x, y)
    cond1 = ((xv - 0.) ** 2 + (yv - 0.) ** 2) <= sigma_out ** 2
    cond2 = np.abs(yv) >= stripe_width / 2.
    cond3 = np.abs(xv) >= stripe_width / 2.
    val = np.array(cond1 & cond2 & cond3, dtype=float)
    plt.imshow(val)
    plt.show()
    val = np.asfortranarray(val / np.sum(val))
    return val


def get_square_source_shape_model(x, y, half_width_sigma):
    xv, yv = np.meshgrid(x, y)
    cond1 = np.abs(yv) <= half_width_sigma
    cond2 = np.abs(xv) <= half_width_sigma
    val = np.array(cond1 & cond2, dtype=float)
    plt.imshow(val)
    plt.show()
    val = np.asfortranarray(val / np.sum(val))
    return val


class ResistImagesAndContours(object):
    def __init__(self):
        self.featureWidth = 240.  # nm
        self.pitch = 600.  # nm
        self.featureTransmittance = 0.  # from 0. to 1.
        self.maskTransmittance = 1.  # from 0. to 1.
        self.featurePhase = 0.
        self.maskPhase = 0.

        self.wavelength = 365.0  # nanometers
        self.numericalAperture = 0.9
        self.reductionRatio = 1.0
        self.flare = 0.
        self.immersion = 0.
        self.focus = 0.
        self.nominalDose = 145  # mJ/cm^2
        self.correctable = 0.5
        self.resistThickness = 600.

        self.stepZ = 5.
        self.sourceStep = 0.05
        self.maskStep = 5.

        self.a = 0.  # exposure-dependent absorption of resist
        self.b = 0.81  # exposure-independent absorption of resist
        self.c = 0.008  # rate of absorption change or bleaching rate
        self.n = 1.835  # refractive index (exposed and unexposed)

        self.ea = 33.5  # PEB acid diffusivity activation energy
        self.ln_ar = 45.  # PEB acid diffusivity Ln(Ar)

        self.substrateRefractiveIndexReal = 6.49
        self.substrateRefractiveIndexImage = 2.6
        self.barcThickness = 172.
        self.barcRefractiveIndexReal = 1.81
        self.barcRefractiveIndexImage = 0.34
        self.environmentRefractiveIndexReal = 1.
        self.environmentRefractiveIndexImage = 0.

        self.pac = np.linspace(0., 1., np.int(self.pitch / self.maskStep))
        # relative inhibitor concentration = (inhibitor concentration)/(initial inhibitor concentration)
        self.pn = 2
        max_development_rate = 100  # nm/s
        min_development_rate = 0.1  # nm/s
        self.rate = max_development_rate * np.power((1 - self.pac), self.pn) + min_development_rate
        # development rate
        self.sourceShapeType = 3
        # 1  - conventional coherent
        # 3  - conventional partially coherent
        # 4  - dipole
        # 5  - monopole
        # 6  - quadrupole
        # 7  - quasar
        # 8  - shrinc
        # 9  - square
        # 10 - annular
        self.image_formation()

    def source_shape_model_choice(self, x, y):
        if self.sourceShapeType == 1:
            return get_conventional_coherent_source_shape_model(self.sourceStep, x, y)
        elif self.sourceShapeType == 3:
            return get_conventional_partially_coherent_source_shape_model(x, y, sigma=0.9)
        elif self.sourceShapeType == 4:
            return get_dipole_source_shape_model(x, y, center_sigma=0.5, radius_sigma=0.3)
        elif self.sourceShapeType == 5:
            return get_monopole_source_shape_model(x, y, center_x=0.5, center_y=0.3, radius_sigma=0.2)
        elif self.sourceShapeType == 6:
            # types:
            # 1 - Normal (90deg)
            # 2 - Cross  (45deg)
            return get_quadrupole_source_shape_model(x, y, center_sigma=0.5, radius_sigma=0.2, geometry_type=1)
        elif self.sourceShapeType == 7:
            return get_quasar_source_shape_model(x, y, sigma_in=0.4, sigma_out=0.8, blade_angle=60.)
        elif self.sourceShapeType == 8:
            return get_shrinc_source_shape_model(x, y, sigma_out=0.8, stripe_width=0.2)
        elif self.sourceShapeType == 9:
            return get_square_source_shape_model(x, y, half_width_sigma=0.5)
        elif self.sourceShapeType == 10:
            return get_annular_source_shape_model(x, y, sigma_in=0.4, sigma_out=0.8)
        else:
            raise ValueError("Wrong source shape id")

    def image_formation(self):
        core_logging = oplc.OptolithiumCoreLog()
        core_logging.set_verbose_level(0)

        # feature formation
        point1 = oplc.Point2d(-self.featureWidth / 2., 0.)
        point2 = oplc.Point2d(self.featureWidth / 2., 0.)
        points_array = oplc.Points2dArray((point1, point2))
        region = oplc.Region(points_array, self.featureTransmittance, self.featurePhase)
        region_array = (region, )

        # repeatable part formation
        point1 = oplc.Point2d(-self.pitch / 2., 0.)
        point2 = oplc.Point2d(self.pitch / 2., 0.)
        box = oplc.Box(point1, point2, self.maskTransmittance, self.maskPhase)

        # mask formation
        mask = oplc.Mask(region_array, box)

        # source calculation
        points_count = int(2 / self.sourceStep) + 1
        nx, ny = (points_count, points_count)
        x = np.linspace(-1, 1, nx)
        y = np.linspace(-1, 1, ny)
        x = np.round(x / self.sourceStep) * self.sourceStep
        y = np.round(y / self.sourceStep) * self.sourceStep
        values = self.source_shape_model_choice(x, y)

        source_shape_model_sheet = oplc.SourceShapeModelSheet(x, y, values)
        source_shape = oplc.SourceShape(source_shape_model_sheet, self.sourceStep, self.sourceStep)

        pupil_filter_model = oplc.PupilFilterModelEmpty()
        imaging_tool = oplc.ImagingTool(source_shape, pupil_filter_model, self.wavelength, self.numericalAperture,
                                        self.reductionRatio, self.flare, self.immersion)

        diffraction = oplc.diffraction(imaging_tool, mask)

        exposure = oplc.Exposure(self.focus, self.nominalDose, self.correctable)

        exposure_resist_model = oplc.ExposureResistModel(self.wavelength, self.a, self.b, self.c, self.n)

        peb_resist_model = oplc.PebResistModel(self.ea, self.ln_ar)

        rate_model = oplc.ResistRateModelSheet(self.pac, self.rate)

        plt.plot(self.pac, self.rate)
        plt.show()

        # wafer stack formation
        substrate_layer = oplc.ConstantWaferLayer(oplc.SUBSTRATE_LAYER, self.substrateRefractiveIndexReal,
                                                  self.substrateRefractiveIndexImage)
        resist_layer = oplc.ResistWaferLayer(self.resistThickness, exposure_resist_model, peb_resist_model, rate_model)
        barc_layer = oplc.ConstantWaferLayer(oplc.MATERIAL_LAYER, self.barcThickness, self.barcRefractiveIndexReal,
                                             self.barcRefractiveIndexImage)
        environment_layer = oplc.ConstantWaferLayer(oplc.ENVIRONMENT_LAYER, self.environmentRefractiveIndexReal,
                                                    self.environmentRefractiveIndexImage)

        wafer_stack = oplc.WaferStack()
        wafer_stack.push(substrate_layer)
        wafer_stack.push(barc_layer)
        wafer_stack.push(resist_layer)
        wafer_stack.push(environment_layer)

        optical_transfer_function = oplc.OpticalTransferFunction(imaging_tool, exposure, wafer_stack)

        image_in_resist = oplc.image_in_resist(diffraction, optical_transfer_function, self.maskStep, self.stepZ)

        fig, ax = plt.subplots(figsize=(6, 6))
        tmp = np.rot90(image_in_resist.values[0])
        with open("resultsImageInResist.txt", 'w') as f:
            for i in range(len(tmp)):
                for j in range(len(tmp[i])):
                    f.write('%f\t' % tmp[i][j])
                f.write("\n")
        ax.imshow(tmp, interpolation='none', extent=[-self.pitch / 2, self.pitch / 2., 0, self.resistThickness])
        ax.set_aspect("equal")
        plt.show()

        latent_image = oplc.latent_image(image_in_resist, resist_layer, exposure)
        fig, ax = plt.subplots(figsize=(6, 6))
        tmp = np.rot90((latent_image.values[0]))
        with open("resultsLatentImage.txt", 'w') as f:
            for i in range(len(tmp)):
                for j in range(len(tmp[i])):
                    f.write('%f\t' % tmp[i][j])
                f.write("\n")
        ax.imshow(tmp, interpolation='none', extent=[-self.pitch / 2, self.pitch / 2., 0, self.resistThickness])
        ax.set_aspect("equal")
        plt.show()

        time_contours = oplc.develop_time_contours(latent_image, resist_layer)

        tmp = np.rot90((time_contours.values[0]))
        with open("resultsTimeContours.txt", 'w') as f:
            for i in range(len(tmp)):
                for j in range(len(tmp[i])):
                    f.write('%f\t' % tmp[i][j])
                f.write("\n")
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.imshow(tmp, interpolation='none', extent=[-self.pitch / 2., self.pitch / 2., 0, self.resistThickness])
        ax.set_aspect("equal")
        plt.show()


def main():
    ResistImagesAndContours()


if __name__ == "__main__":
    main()