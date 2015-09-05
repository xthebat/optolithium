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

#ifndef OPL_SIM_H_
#define OPL_SIM_H_

#include "opl_capi.h"

using namespace oplc;

SharedDiffraction diffraction(SharedImagingTool imaging_tools, SharedMask mask);
SharedResistVolume aerial_image(SharedDiffraction diffraction, SharedOpticalTransferFunction otf, double stepxy);
SharedResistVolume image_in_resist(SharedDiffraction diffraction,
		SharedOpticalTransferFunction otf, double stepxy, double stepz);
SharedResistVolume latent_image(SharedResistVolume image_in_resist,
		SharedResistWaferLayer resist, SharedExposure exposure);
SharedResistVolume peb_latent_image(SharedResistVolume latent_image,
		SharedResistWaferLayer resist, SharedPostExposureBake peb);
SharedResistVolume develop_time_contours(SharedResistVolume peb_latent_image, SharedResistWaferLayer resist);
SharedResistProfile resist_profile(SharedResistVolume develop_times, SharedDevelopment development);

#endif /* OPL_SIM_H_ */
