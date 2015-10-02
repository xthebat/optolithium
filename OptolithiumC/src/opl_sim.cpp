/*
 *
 * This file is part of Optolithium lithography modelling software.
 *
 * Copyright (C) 2015 Alexei Gladkikh
 *
 * This software is dual-licensed: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version only for NON-COMMERCIAL usage.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 *
 * If you are interested in other licensing models, including a commercial-
 * license, please contact the author at gladkikhalexei@gmail.com
 *
 */

#include "opl_sim.h"
#include "opl_physc.h"
#include "opl_conv.h"
#include "opl_eikonal.h"
#include "opl_contours.h"
#include "opl_fft.h"


SharedDiffraction diffraction(SharedImagingTool imaging_tool, SharedMask mask)
{
	LOG(INFO) << "Optolithium Core: Calculate diffraction pattern for given mask, pitch = " << mask->pitch().str();
	TIMED_FUNC(diffraction_timer);

	if (mask->is_bad()) {
		throw std::invalid_argument("Wrong mask bounding box size! "
				"Diffraction 1D can only be calculation for one-dimensional mask.");
	}

	SharedDiffraction diffraction = std::make_shared<Diffraction>(mask, imaging_tool);

	for (auto region : *mask) {
		arma::cx_double factor = region->etransmit() - mask->boundary()->etransmit();
		diffraction->add_region(region, factor);
	}

	if (!mask->is_opaque()) {
		arma::cx_double factor = mask->boundary()->etransmit();
		diffraction->values()->elem(arma::find(*diffraction->cxy() == 0.0)) += factor;
	}

	return diffraction;
}


void _calc_aerial_image(SharedResistVolume result, SharedDiffraction diffraction,
		SharedOpticalTransferFunction otf, double refractive_index, double stepxy, double stepz=0.0) {
	TIMED_FUNC(aerial_image_timer);

	const uint32_t n_rows = result->values()->n_rows != 1 ? result->values()->n_rows - 1 : result->values()->n_rows;
	const uint32_t n_cols = result->values()->n_cols != 1 ? result->values()->n_cols - 1 : result->values()->n_cols;
	const uint32_t n_slices = result->values()->n_slices;

	const uint32_t midcol = static_cast<uint32_t>(static_cast<double>(n_cols)/2.0);
	const uint32_t midrow = static_cast<uint32_t>(static_cast<double>(n_rows)/2.0);

	const uint32_t n_source_points = diffraction->source_shape->non_zeros()->n_rows;

	const double na = diffraction->numeric_aperture;

	if (n_rows != 1 && n_rows % 2 != 0) {
		throw std::invalid_argument("The result rows count must be even");
	} else if (n_cols != 1 && n_cols % 2 != 0) {
		throw std::invalid_argument("The result columns count must be even");
	}

	arma::cx_mat efield = arma::cx_mat(n_rows, n_cols);

    fft::FFT2d fft(efield, fft::FFT_BACKWARD, n_source_points*n_slices);

	for (uint32_t s = 0; s < n_slices; s++) {
		const double thickness = result->z(s);

		arma::mat intensity = arma::mat(n_rows, n_cols, arma::fill::zeros);

		for (uint32_t k = 0; k < diffraction->source_shape->non_zeros()->n_rows; k++) {
			// Get non-zeros intensity source shape point indexes
			auto src_row_col = diffraction->source_shape->non_zeros()->row(k);

			const double source_irradiance = diffraction->source_shape->value(src_row_col(0), src_row_col(1));
			const double scx = na * diffraction->source_shape->cx(src_row_col(1));
			const double scy = na * diffraction->source_shape->cy(src_row_col(0));

			// Clear temporary array of current source shape electric field
			efield.zeros();

			{TIMED_SCOPE(aerial_image_diffraction, "Diffraction pattern generation done");
				// Get non-zeros elements (according to current source shape point) and
				// copy it to Fourier backward transform temporary matrix
				for (uint32_t r = 0; r < diffraction->values()->n_rows; r++) {
					for (uint32_t c = 0; c < diffraction->values()->n_cols; c++) {
						double dcy = diffraction->cy(r);
						double dcx = diffraction->cx(c);
						uint32_t e_row = (n_rows + diffraction->ky(r) - 1) % n_rows;
						uint32_t e_col = (n_cols + diffraction->kx(c) - 1) % n_cols;
						efield(e_row, e_col) = otf->calc(dcx - scx, dcy - scy, thickness) * diffraction->value(r, c);
					}
				}
			}

            fft.execute();

			{TIMED_SCOPE(aerial_image_timer_intensity, "Intensity for given source shape point done");
				// Calculate intensity for given source point and sum if with previous result
				intensity += source_irradiance * arma::real(efield % arma::conj(efield));
			}
		}

		intensity *= (refractive_index / arma::accu(*diffraction->source_shape->values()));

		// Save results to the output array and make fftshift and copy last point (Prolith symmetry)
		arma::mat& layer = result->values()->slice(s);
		if (n_cols != 1 && n_rows == 1) {
			for (uint32_t c = 0; c < midcol; c++) {
				layer(0, c + midcol) = intensity(0, c);
				layer(0, c) = intensity(0, c + midcol);
			}
			layer(0, n_cols) = layer(0, 0);
		} else if (n_rows != 1 && n_cols == 1) {
			for (uint32_t r = 0; r < midrow; r++) {
				layer(r + midrow, 0) = intensity(r, 0);
				layer(r, 0) = intensity(r + midrow, 0);
			}
			layer(n_rows, 0) = layer(0, 0);
		} else if (n_rows != 1 && n_cols != 1) {
			for (uint32_t r = 0; r < midrow; r++) {
				for (uint32_t c = 0; c < midcol; c++) {
					layer(r + midrow, c + midcol) = intensity(r, c);
					layer(r, c) = intensity(r + midrow, c + midcol);
					layer(r, c + midcol) = intensity(r + midrow, c);
					layer(r + midrow, c) = intensity(r, c + midcol);

					layer(n_rows, c) = layer(0, c);
					layer(n_rows, c + midcol) = layer(0, c + midcol);
				}
				layer(r, n_cols) = layer(r, 0);
				layer(r + midrow, n_cols) = layer(r + midrow, 0);
			}
			layer(n_rows, n_cols) = layer(0, 0);
		}
	}
}


SharedResistVolume aerial_image(SharedDiffraction diffraction, SharedOpticalTransferFunction otf, double stepxy) {
	LOG(INFO) << "Optolithium Core: Calculate aerial image";
	double refractive_index = physc::air_nk.real();
	if (otf->wafer_stack()) {
		if (!otf->wafer_stack()->environment()) {
			throw std::invalid_argument("Environment was not specified");
		}
		double wavelength = diffraction->wavelength;
		refractive_index = otf->wafer_stack()->environment()->refraction(wavelength).real();
	}
	SharedResistVolume result = std::make_shared<ResistVolume>(diffraction->boundary, stepxy);
	_calc_aerial_image(result, diffraction, otf, refractive_index, stepxy);
	otf->imaging_tool()->flare(result);
	return result;
}


SharedResistVolume image_in_resist(SharedDiffraction diffraction,
		SharedOpticalTransferFunction otf, double stepxy, double stepz) {
	LOG(INFO) << "Optolithium Core: Calculate image in resist";
	double wavelength = diffraction->wavelength;
	double refractive_index = otf->wafer_stack()->resist()->refraction(wavelength).real();
	double thickness = otf->wafer_stack()->resist()->thickness;
	SharedResistVolume result = std::make_shared<ResistVolume>(diffraction->boundary, thickness, stepxy, stepz);
	_calc_aerial_image(result, diffraction, otf, refractive_index, stepxy, stepz);
	otf->imaging_tool()->flare(result);
	return result;
}


SharedResistVolume latent_image(SharedResistVolume image_in_resist,
		SharedResistWaferLayer resist, SharedExposure exposure) {
	LOG(INFO) << "Optolithium Core: Calculate exposed latent image";
	const arma::cube& values = *image_in_resist->values();
	// Create new resist volume object without coping data from it.
	SharedResistVolume result = std::make_shared<ResistVolume>(*image_in_resist, false);
//	LOG(INFO) << "Dose = " << exposure->dose() << " C = " << resist->exposure->c;
	*result->values() = arma::exp(-values*exposure->dose()*resist->exposure->c);
	return result;
}


SharedResistVolume peb_latent_image(SharedResistVolume latent_image,
		SharedResistWaferLayer resist, SharedPostExposureBake peb) {
	LOG(INFO) << "Optolithium Core: Calculate PEB latent image";
	SharedResistVolume result = std::make_shared<ResistVolume>(*latent_image, false);

	arma::vec kernelx = resist->peb->kernel(peb, latent_image->stepx());
	arma::vec kernely = resist->peb->kernel(peb, latent_image->stepy());
	arma::vec kernelz = resist->peb->kernel(peb, latent_image->stepz());

	// Perform separable convolution

	const arma::cube& input = *latent_image->values();
	arma::cube& output = *result->values();

	for (uint32_t s = 0; s < input.n_slices; s++) {
		const arma::mat& input_slice = input.slice(s);
		arma::mat output_slice = arma::mat(input_slice.n_rows, input_slice.n_cols);

//		LOG(INFO) << "Slice #" << s << " kernelx = " << kernelx.n_elem << " kernely = " << kernely.n_elem;

		// Because when slice the cube matrix is transpose then y->cols and x->rows

		for (uint32_t r = 0; r < input.n_rows; r++) {
			const arma::rowvec& row = input_slice.row(r);
			output_slice.row(r) = conv::conv1d(row, kernelx, conv::CIRCULAR);
		}

		for (uint32_t c = 0; c < input.n_cols; c++) {
			const arma::colvec& col = output_slice.col(c);
			arma::vec tmp = conv::conv1d(col, kernely, conv::CIRCULAR);
			output_slice.col(c) = tmp;
		}

		output.slice(s) = output_slice;
	}

	for (uint32_t r = 0; r < input.n_rows; r++) {
		for (uint32_t c = 0; c < input.n_cols; c++) {
			const arma::cube& tube = output.tube(r, c);
			auto tmp = conv::conv1d(tube, kernelz, conv::SYMMETRIC);
			output.tube(r, c) = tmp;
		}
	}

	return result;
}


//#define ENABLE_DEBUG_RATES


SharedResistVolume develop_time_contours(SharedResistVolume peb_latent_image, SharedResistWaferLayer resist) {
	LOG(INFO) << "Optolithium Core: Calculate develop time contours";
	SharedResistVolume result = std::make_shared<ResistVolume>(*peb_latent_image, false);

	const arma::cube& values = *peb_latent_image->values();

	arma::cube rates = arma::cube(values.n_rows, values.n_cols, values.n_slices);

//	LOG(INFO) << "Calculate development rates";
	for (uint32_t s = 0; s < rates.n_slices; s++) {
		double depth = peb_latent_image->z(s);
//		LOG(INFO) << "s = " << s << " depth = " << depth;
		for (uint32_t r = 0; r < rates.n_rows; r++) {
			for (uint32_t c = 0; c < rates.n_cols; c++) {
				double pac = values(r, c, s);
				rates(r, c, s) = resist->rate->calculate(pac, depth);
			}
		}
	}

#ifndef ENABLE_DEBUG_RATES
	arma::cube& develop = *result->values();

//	LOG(INFO) << "Create initial resist profile contour";
	develop.fill(-1.0);
	develop.slice(develop.n_slices-1).fill(arma::fill::zeros);

//	LOG(INFO) << "Calculate resist profile development";
	eikonal::solve3d(develop, rates, result->stepy(), result->stepx(), result->stepz());
#else
	*result->values() = rates;
#endif

	return result;
}


SharedResistProfile resist_profile(SharedResistVolume develop_times, SharedDevelopment development) {
	return std::make_shared<ResistProfile>(develop_times, development->time);
}
