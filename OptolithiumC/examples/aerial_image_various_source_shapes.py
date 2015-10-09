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
    cond2 = np.abs(yv) >= stripe_width/2.
    cond3 = np.abs(xv) >= stripe_width/2.
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


class AerialImage(object):
    def __init__(self):
        # setting pattern properties:
        # example: pattern with 1 feature _I_

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

        self.sourceStep = 0.01
        self.maskStep = 5.

        self.sourceShapeType = 6
        # 1  - conventional coherent
        # 3  - conventional partially coherent
        # 4  - dipole
        # 5  - monopole
        # 6  - quadrupole
        # 7  - quasar
        # 8  - shrinc
        # 9  - square
        # 10 - annular
        self.aerial_image_formation()

    def source_shape_model_choice(self, x, y):
        if self.sourceShapeType == 1:
            return get_conventional_coherent_source_shape_model(self.sourceStep, x, y)
        elif self.sourceShapeType == 3:
            return get_conventional_partially_coherent_source_shape_model(x, y, sigma=0.5)
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

    def aerial_image_formation(self):
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
        x = np.round(x/self.sourceStep)*self.sourceStep
        y = np.round(y/self.sourceStep)*self.sourceStep
        values = self.source_shape_model_choice(x, y)

        source_shape_model_sheet = oplc.SourceShapeModelSheet(x, y, values)
        source_shape = oplc.SourceShape(source_shape_model_sheet, self.sourceStep, self.sourceStep)

        pupil_filter_model = oplc.PupilFilterModelEmpty()
        imaging_tool = oplc.ImagingTool(source_shape, pupil_filter_model, self.wavelength, self.numericalAperture,
                                        self.reductionRatio, self.flare, self.immersion)

        diffraction = oplc.diffraction(imaging_tool, mask)

        exposure = oplc.Exposure(self.focus, self.nominalDose, self.correctable)

        optical_transfer_function = oplc.OpticalTransferFunction(imaging_tool, exposure, None)

        aerial_image = oplc.aerial_image(diffraction, optical_transfer_function, self.maskStep)

        plt.plot(aerial_image.x, aerial_image.values[0])
        plt.show()
        with open("results.txt", 'w') as f:
            for i in range(len(aerial_image.x)):
                f.write('%f' % aerial_image.x[i])
                f.write("\t")
                f.write('%f' % aerial_image.values[0][i])
                f.write("\n")


def main():
    AerialImage()


if __name__ == "__main__":
    main()