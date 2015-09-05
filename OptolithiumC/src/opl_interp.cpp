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

#include <float.h>
#include <stdint.h>
#include "opl_interp.h"
#include "opl_log.h"


namespace interp {
	uint32_t _get_base_index(const arma::vec& x, double xi) {
		uint32_t result = 0;

//		if (xi < x(0) || xi > x(x.n_elem-1)) {
//			std::ostringstream result;
//			result << "Wrong base index interval during interpolation: "
//					<< "xi = " << xi << " x(0) = " << x(0) << " x(-1) = " << x(x.n_elem-1);
//			throw std::range_error(result.str());
//		}

		const int32_t sdx = (x(x.n_elem-1) - x(0)) > 0 ? 1 : -1;
		for (uint32_t k = 0; k < x.n_elem-1; k++) {
			if (sdx*xi >= sdx*x(k) && sdx*xi <= sdx*x(k+1)) {
				result = k;
				break;
			}
		}

		return result;
	}

	inline double _interp1(double xi, double x0, double x1, double v0, double v1) {
		return ((x1 - xi)*v0 + (xi - x0)*v1)/(x1 - x0);
	}

	LinearInterpolation1d::LinearInterpolation1d(ConstVector px, ConstVector py, double fill) : _px(px), _py(py) {
		this->_fill = fill;
		const arma::vec &x = *this->_px, &y = *this->_py;
		this->_s = std::make_shared<arma::vec>(x.n_elem);
		this->_b = std::make_shared<arma::vec>(x.n_elem);
		arma::vec& s = *this->_s;
		arma::vec& b = *this->_b;
//		LOG(INFO) << "size(y) = " << y.n_elem << " size(x) = " << x.n_elem;
		for (uint32_t k = 0; k < x.n_elem-1; k++) {
//			LOG(INFO) << "k = " << k << " y(k) = " << y(k) << " x(k) = " << x(k);
			s(k) = (y(k+1) - y(k)) / (x(k+1) - x(k));
			b(k) = (x(k+1)*y(k) - x(k)*y(k+1)) / (x(k+1) - x(k));
		}
	}

	double LinearInterpolation1d::interpolate(double xi) const {
		const arma::vec &x = *this->_px, &y = *this->_py;
//		LOG(INFO) << "xi = " << xi << " x(0) = " << x(0) << " x(-1) = " << x(x.n_elem-1);
		const int32_t sdx = (x(x.n_elem-1) - x(0)) > 0 ? 1 : -1;
		if (sdx*xi < sdx*x(0) || sdx*xi > sdx*x(x.n_elem-1)) {
			return this->_fill;
		} else if (xi == x(0)) {
//			LOG(INFO) << "return y(0) = " << y(0);
			return y(0);
		} else if (xi == x(x.n_elem-1)) {
//			LOG(INFO) << "return y(-1) = " << y(y.n_elem-1);
			return y(y.n_elem-1);
		} else {
			const uint32_t k = _get_base_index(x, xi);
			const arma::vec &s = *this->_s, &b = *this->_b;
			const double result = s(k)*xi + b(k);
//			LOG(INFO) << "interpolate 1d s = " << s(k) << " b = " << b(k) << " v = " << result;
			return result;
		}
	}

	std::shared_ptr<arma::vec> LinearInterpolation1d::interpolate(const arma::vec& xi) const {
		std::shared_ptr<arma::vec> result = std::make_shared<arma::vec>(xi.n_elem);
		for (uint32_t k = 0; k < xi.n_elem; k++) {
			(*result)(k) = this->interpolate(xi(k));
		}
		return result;
	}

	bool LinearInterpolation1d::operator==(const LinearInterpolation1d& other) const {
		return arma::as_scalar(*this->_px == *other._px) && arma::as_scalar(*this->_py == *other._py) &&
				this->_fill == other._fill;
	}

	LinearInterpolation2d::LinearInterpolation2d(ConstVector px, ConstVector py, ConstMatrix values, double fill) {
		this->_px = px;
		this->_py = py;
		this->_values = values;
		this->_fill = fill;

//		LOG(INFO) << "px.n_elem = " << px->n_elem << " py.n_elem = " << py->n_elem;
//		LOG(INFO) << "INPUT MATRIX: r = " << values->n_rows << " c = " << values->n_cols;

		this->_yinterp1.resize(py->n_elem);
		for (uint32_t r = 0; r < py->n_elem; r++) {
			ConstVector row = std::make_shared<arma::vec>(arma::trans(values->row(r)));
			this->_yinterp1[r] = std::make_shared<LinearInterpolation1d>(px, row);
		}

		ConstVector last_col = std::make_shared<arma::vec>(values->col(px->n_elem-1));
		this->_xlastinterp1 = std::make_shared<LinearInterpolation1d>(py, last_col);
	}

	double LinearInterpolation2d::interpolate(double xi, double yi) const {
		const arma::mat &f = *this->_values;
		const arma::vec &x = *this->_px, &y = *this->_py;
		const int32_t sdx = (x(x.n_elem-1) - x(0)) > 0 ? 1 : -1;
		const int32_t sdy = (y(y.n_elem-1) - y(0)) > 0 ? 1 : -1;
//		LOG(INFO) << "xi = " << xi << " x(0) = " << x(0) << " x(-1) = " << x(x.n_elem-1) << " sdx = " << sdx
//				<< " yi = " << yi << " y(0) = " << y(0) << " y(-1) = " << y(y.n_elem-1) << " sdy = " << sdy;
		if (sdx*xi < sdx*x(0) || sdx*xi > sdx*x(x.n_elem-1) ||
			sdy*yi < sdy*y(0) || sdy*yi > sdy*y(y.n_elem-1)) {
//			LOG(INFO) << "return filler " << (sdx*xi < sdx*x(0)) << " " << (sdx*xi > sdx*x(x.n_elem-1)) << " "
//					<< (sdy*yi < sdy*y(0)) << " " << (sdy*yi > sdy*y(y.n_elem-1));
			return this->_fill;
		} else if (xi == x(x.n_elem-1) && yi == y(y.n_elem-1)) {
//			LOG(INFO) << "return f(-1, -1)";
			return f(y.n_elem-1, x.n_elem-1);
		} else if (yi == y(y.n_elem-1)) {
//			LOG(INFO) << "interpolate last row";
			return this->_yinterp1[y.n_elem-1]->interpolate(xi);
		} else if (xi == x(x.n_elem-1)) {
//			LOG(INFO) << "interpolate last col";
			return this->_xlastinterp1->interpolate(yi);
		} else {
//			LOG(INFO) << "interpolate 2d";
			const uint32_t r = _get_base_index(y, yi);
//			LOG(INFO) << "BASE INDEX = " << r << "/" << this->_yinterp1.size();
			double v0 = this->_yinterp1[r]->interpolate(xi);
			double v1 = this->_yinterp1[r+1]->interpolate(xi);
			return _interp1(yi, y(r), y(r+1), v0, v1);
		}
	}

	std::shared_ptr<arma::mat> LinearInterpolation2d::interpolate(const arma::vec& xi, const arma::vec& yi) const {
		std::shared_ptr<arma::mat> result = std::make_shared<arma::mat>(yi.n_elem, xi.n_elem);
		for (uint32_t r = 0; r < yi.n_elem; r++) {
			for (uint32_t c = 0; c < xi.n_elem; c++) {
				(*result)(r, c) = this->interpolate(xi(c), yi(r));
			}
		}
		return result;
	}


	bool LinearInterpolation2d::operator==(const LinearInterpolation2d& other) const {
		return arma::as_scalar(*this->_px == *other._px) && arma::as_scalar(*this->_py == *other._py) &&
				arma::as_scalar(*this->_values == *other._values) && this->_fill == other._fill;
	}
}
