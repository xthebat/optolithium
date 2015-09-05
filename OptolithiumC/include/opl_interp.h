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

#ifndef OPL_INTERP_H_
#define OPL_INTERP_H_


#include <memory>

#if !defined( SWIG )
    // SWIG should not see #include <armadillo> as it can not handle it
	#include <armadillo>
#endif


namespace interp {

	typedef std::shared_ptr<const arma::vec> ConstVector;
	typedef std::shared_ptr<const arma::mat> ConstMatrix;
	typedef std::shared_ptr<arma::vec> Vector;


	class LinearInterpolation1d {
	private:
		ConstVector _px;  // Input array x
		ConstVector _py;  // Input array y - values

		Vector _b;  // Additive coefficient of line
		Vector _s;  // Slope of line

		double _fill;
	public:
		LinearInterpolation1d(void) : _fill(0.0) { };
		LinearInterpolation1d(ConstVector px, ConstVector py, double fill=0.0);
		double interpolate(double xi) const;
		std::shared_ptr<arma::vec> interpolate(const arma::vec& xi) const;

		std::shared_ptr<const arma::vec> x(void) const {
			return this->_px;
		}

		std::shared_ptr<const arma::vec> y(void) const {
			return this->_py;
		}

		bool operator==(const LinearInterpolation1d& other) const;
	};

	typedef std::shared_ptr<LinearInterpolation1d> SharedLinearInterpolation1d;

	class LinearInterpolation2d {
	private:
		ConstVector _px;
		ConstVector _py;
		ConstMatrix _values;
		double _fill;

		SharedLinearInterpolation1d _xlastinterp1;
		std::vector<SharedLinearInterpolation1d> _yinterp1;
	public:
		LinearInterpolation2d(void) : _fill(0.0) { };
		LinearInterpolation2d(ConstVector px, ConstVector py, ConstMatrix values, double fill=0.0);
		double interpolate(double xi, double yi) const;
		std::shared_ptr<arma::mat> interpolate(const arma::vec& xi, const arma::vec& yi) const;

		std::shared_ptr<const arma::vec> x(void) const {
			return this->_px;
		}

		std::shared_ptr<const arma::vec> y(void) const {
			return this->_py;
		}

		std::shared_ptr<const arma::mat> values(void) const {
			return this->_values;
		}

		bool operator==(const LinearInterpolation2d& other) const;
	};

	typedef std::shared_ptr<LinearInterpolation2d> SharedLinearInterpolation2d;
}

#endif /* OPL_INTERP_H_ */
