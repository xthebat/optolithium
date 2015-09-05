/*
 *
 * This file is part of Optolithium lithography modelling software.
 *
 * Copyright (C) 2015 Alexei Gladkikh
 *
 * This software is dual-licensed: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version only for non-commercial usage.
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

#ifndef OPL_CONV_H_
#define OPL_CONV_H_


#if !defined( SWIG )
    // SWIG should not see #include <armadillo> as it can not handle it
	#include <armadillo>
#endif


namespace conv {

	typedef enum {
		SYMMETRIC = 0,
		CIRCULAR = 1
	} conv1d_type_t;


	template <typename _ArrayType>
	inline void _symmetric_conv1d(_ArrayType& result, const _ArrayType& array, const arma::vec& kernel) {
		// Symmetric convolution help
		//	                  |     |
		//        0  1  2  1  0  1  2  1  0
		//	      0  1  2  3  4  3  2  1  0
		//	     -4 -3 -2 -1  0  1  2  3  4
		if (array.n_elem > 1) {
			const double n_elem = static_cast<double>(kernel.n_elem);
			const int32_t kmin = -static_cast<int32_t>(std::floor(n_elem/2.0));
//			LOG(INFO) << "Array size = " << array.n_elem << " Centered kernel min index = " << kmin;

			// Make symmetric convolution. Indexes reflected from boundary
			for (int32_t i = 0; i < static_cast<int32_t>(array.n_elem); i++) {
				double sum = 0;
				for (int32_t s = kmin, k = 0; k < static_cast<int32_t>(kernel.n_elem); s++, k++) {
					uint32_t v;
					const int32_t w = abs(i + s), c = array.n_elem;
					if (w >= c) {
						const uint8_t is_fall = (w/(c-1))%2;
						if (is_fall) {
							v = (c-1) - w % (c-1);
						} else {
							v = w % (c-1);
						}
					} else {
						v = w;
					}
//					LOG(INFO) << "i = " << i << " s = " << s <<
//							" array(" << v << ") = " << array(v) <<
//							" kernel(" << k << ") = " << kernel(k);
					sum += array(v) * kernel(k);
				}
				result(i) = sum;
			}
		} else if (array.n_elem == 1) {
			result(0) = array(0);
//			LOG(INFO) << "Array size = 1 -> input: " << array(0) << " result: " << result(0);
		}
	}


	template <typename _ArrayType>
	inline void _circular_conv1d(_ArrayType& result, const _ArrayType& array, const arma::vec& kernel) {
		// Circular convolution help for vertical stage
		//	                  |     |
		//	0  1  2  0  1  2  0  1  2  0  1  2  0  1  2
		//	      0  1  2  3  4  3  2  1  0
		//	     -4 -3 -2 -1  0  1  2  3  4
		if (array.n_elem > 1) {
			const double n_elem = static_cast<double>(kernel.n_elem);
			const int32_t kmin = -static_cast<int32_t>(std::floor(n_elem/2.0));
//			LOG(INFO) << "Array size = " << array.n_elem << " Centered kernel min index = " << kmin;

			// Make circular convolution
			for (int32_t i = 0; i < static_cast<int32_t>(array.n_elem); i++) {
				double sum = 0;
				for (int32_t s = kmin, k = 0; k < static_cast<int32_t>(kernel.n_elem); s++, k++) {
					const uint32_t v = (array.n_elem + i + s) % array.n_elem;
//					LOG(INFO) << "i = " << i << " s = " << s <<
//							" array(" << v << ") = " << array(v) <<
//							" kernel(" << k << ") = " << kernel(k);
					sum += array(v) * kernel(k);
				}
				result(i) = sum;
			}
		} else if (array.n_elem == 1) {
			result(0) = array(0);
//			LOG(INFO) << "Array size = 1 -> input: " << array(0) << " result: " << result(0);
		}
	}


	inline arma::rowvec conv1d(const arma::rowvec& array, const arma::vec& kernel, conv1d_type_t type) {
		arma::rowvec result = arma::rowvec(array.n_elem);
		if (type == CIRCULAR) {
			_circular_conv1d(result, array, kernel);
		} else if (type == SYMMETRIC) {
			_symmetric_conv1d(result, array, kernel);
		} else {
			throw std::invalid_argument("Convolution type can be only SYMMETRIC or CIRCULAR");
		}
		return result;
	}


	inline arma::colvec conv1d(const arma::colvec& array, const arma::vec& kernel, conv1d_type_t type) {
		arma::colvec result = arma::colvec(array.n_elem);
		if (type == CIRCULAR) {
			_circular_conv1d(result, array, kernel);
		} else if (type == SYMMETRIC) {
			_symmetric_conv1d(result, array, kernel);
		} else {
			throw std::invalid_argument("Convolution type can be only SYMMETRIC or CIRCULAR");
		}
		return result;
	}


	inline arma::cube conv1d(const arma::cube& array, const arma::vec& kernel, conv1d_type_t type) {
		if ((array.n_rows == 1 && array.n_cols == 1) ||
			(array.n_rows == 1 && array.n_slices == 1) ||
			(array.n_cols == 1 && array.n_slices == 1))
		{
			arma::cube result = arma::cube(array.n_rows, array.n_cols, array.n_slices);
			if (type == CIRCULAR) {
				_circular_conv1d(result, array, kernel);
			} else if (type == SYMMETRIC) {
				_symmetric_conv1d(result, array, kernel);
			} else {
				throw std::invalid_argument("Convolution type can be only SYMMETRIC or CIRCULAR");
			}
			return result;
		} else {
			throw std::invalid_argument("One dimension circular convolution can be performed only on vectors");
		}
	}

}

#endif /* OPL_CONV_H_ */
