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

#ifndef OPL_EIKONAL_H_
#define OPL_EIKONAL_H_


#if !defined( SWIG )
    // SWIG should not see #include <armadillo> as it can not handle it
	#include <armadillo>
	#include <FMM_API.h>
#endif

namespace eikonal {

	void _chk_eikonal_status(int status) {
		if (status != LSM_FMM_ERR_SUCCESS) {
			std::string error_string;
			if (status == LSM_FMM_ERR_FMM_DATA_CREATION_ERROR) {
				error_string = "Data creation error";
			} else if (status == LSM_FMM_ERR_INVALID_SPATIAL_DISCRETIZATION_ORDER) {
				error_string = "Invalid spatial discretization order";
			} else {
				error_string = "General error";
			}
			throw std::runtime_error("Solving eikonal failed: " + error_string);
		}
	}

	// result must contain initial state
	void solve2d(arma::mat& result, const arma::mat& rates, double row_step, double col_step) {
		const int sizes[2] = { static_cast<int>(rates.n_rows), static_cast<int>(rates.n_cols) };
		const double grid[2] = { col_step, row_step };

		const int derivative_order = 2;

		double *mask = nullptr;
		double *phi = reinterpret_cast<LSMLIB_REAL*>(&result(0, 0));
		const double *speed = reinterpret_cast<const LSMLIB_REAL*>(&rates(0, 0));

		int status = solveEikonalEquation2d(phi, speed, mask, derivative_order, sizes, grid);

		_chk_eikonal_status(status);
	}

	// result must contain initial state
	void solve3d(arma::cube& result, const arma::cube& rates, double row_step, double col_step, double slice_step) {
		int sizes[3] = { static_cast<int>(rates.n_rows),
				static_cast<int>(rates.n_cols), static_cast<int>(rates.n_slices) };
		double grid[3] = { row_step, col_step, slice_step };

		int derivative_order = 2;

		double *mask = nullptr;
		double *phi = reinterpret_cast<LSMLIB_REAL*>(&result(0, 0, 0));
		const double *speed = reinterpret_cast<const LSMLIB_REAL*>(&rates(0, 0, 0));

		int status = solveEikonalEquation3d(phi, speed, mask, derivative_order, sizes, grid);

		_chk_eikonal_status(status);
	}

}


#endif /* OPL_EIKONAL_H_ */
