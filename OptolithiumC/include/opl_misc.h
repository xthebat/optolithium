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

#ifndef OPL_MISC_H_
#define OPL_MISC_H_

#if !defined(SWIG)
namespace misc {
	inline void swap(double& a, double& b) {
		double tmp = b;
		b = a;
		a = tmp;
	}

	inline double round_to(double value, double precision) {
		return round(value / precision) * precision;
	}

	template <class cls>
	inline bool safe_vector_equal(
			const std::vector<std::shared_ptr<cls>>& v1,
			const std::vector<std::shared_ptr<cls>>& v2) {
		return v1.size() == v2.size() && std::equal(v1.begin(), v1.end(), v2.begin(),
			[] (const std::shared_ptr<cls>& a, const std::shared_ptr<cls>& b) -> bool {return *a == *b;});
	}

	// Rotate arma::mat counter-clockwise
	template <class cls>
	inline cls rot90(cls array) {
		cls result = cls(array.n_cols, array.n_rows);
		for (uint32_t r = 0; r < array.n_rows; r++) {
			for (uint32_t c = 0; c < array.n_cols; c++) {
				result(array.n_cols - c - 1, r) = array(r, c);
			}
		}
		return result;
	}
}
#endif



#endif /* OPL_MISC_H_ */
