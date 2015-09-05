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

#ifndef OPL_PHYSC_H_
#define OPL_PHYSC_H_

#include <complex>

namespace physc {

	// Ideal gas constant (kcal/K/mol)
	constexpr double R = 1.987204118e-3;

	// Absolute zero temperature (C)
	constexpr double T0 = -273.15;

	// Refractive index in air
	constexpr std::complex<double> air_nk = std::complex<double>(1.0002926, 0.0);

	// Speed of Light (m/s)
	constexpr double c = 299792458;
}


#endif /* OPL_PHYSC_H_ */
