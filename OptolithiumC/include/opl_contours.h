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

#ifndef OPL_CONTOURS_H_
#define OPL_CONTOURS_H_


#if !defined( SWIG )
    // SWIG should not see #include <armadillo> as it can not handle it
	#include <armadillo>
#endif

#include "opl_log.h"
#include "opl_geometry.h"
#include "opl_interp.h"

namespace contours {

	using namespace geometry;

	typedef std::shared_ptr<ArrayOfSharedPoints2d> SharedArrayOfSharedPoints;

	class _ContourEngine {
	private:
		typedef arma::Mat<char> CharMat;

		std::shared_ptr<const arma::vec> _x;
		std::shared_ptr<const arma::vec> _y;
		std::shared_ptr<const arma::mat> _values;

		CharMat _marks;
		std::list<SharedArrayOfSharedPoints> _contours_list;
		ArrayOfSharedPolygons _polygons;

		void _mark_facets(double lvl, int32_t sign);
		void _drawcn(double lvl, int32_t r, int32_t c, Point2d ct, uint8_t start_edge, bool first);
		void _calculate_level_lines(double level);
		void _erase_contour(SharedArrayOfSharedPoints contour);
		void _extract_polygons(void);
	public:
		_ContourEngine(const arma::vec& x, const arma::vec& y,
				const arma::mat& values, double level, bool negative=false);
		ArrayOfSharedPolygons polygons(void) const;
	};

	class _SurfaceCell;

	class _SurfaceEngine {
	private:
		friend class _SurfaceCell;

		const arma::vec& _x;
		const arma::vec& _y;
		const arma::vec& _z;
		const arma::cube& _values;

		const double _level;

		const int32_t _negative;

		ArrayOfSharedTriangles3d _triangles;
		ArrayOfSharedPoints3d _verteces;

		// Lookup tables used in the construction of the isosurface.
		static const uint32_t edgeTable[256];
		static const int32_t triTable[256][16];

		static const uint32_t indexes_p[12];
		static const uint32_t indexes_q[12];

		// Calculate table lookup index from those vertices which are below the isolevel.
		static uint32_t _calculate_table_index(const _SurfaceCell& cell, double level, int32_t negative);
		static ArrayOfSharedPoints3d _calculate_vertices(const _SurfaceCell& cell, uint32_t edge_code, double level);

		void _process_verteces(ArrayOfSharedPoints3d verteces, const int32_t tri_codes[]);

		static inline Point3d _linear_interp3d(double lvl,
				const Point3d& p, const Point3d& q, double v1, double v2) {
			double k = (lvl - v1) / (v2 - v1);
			return p + k * (q - p);
		}
	public:
		_SurfaceEngine(const arma::vec& x, const arma::vec& y, const arma::vec& z,
				const arma::cube& values, const double level, const int32_t negative);
		SharedSurface3d surface(void) const;
	};

	class _SurfaceCell {
	public:
		std::vector<Point3d> points;
		std::vector<double> values;

		inline void _get_level(const _SurfaceEngine* se, Point3d& p, double& v, uint32_t r, uint32_t c, uint32_t s) {
			if (r >= se->_y.n_elem || c >= se->_x.n_elem || s >= se->_z.n_elem) {
				p = Point3d();
				v = -1.0;
			} else {
				p = Point3d(se->_x(c), se->_y(r), se->_z(s));
				v = se->_values(r, c, s);
			}
		}

		_SurfaceCell(const _SurfaceEngine* se, uint32_t r, uint32_t c, uint32_t s) {
			this->points.resize(8);
			this->values.resize(8);

			_get_level(se, this->points[0], this->values[0], r  , c  , s);
			_get_level(se, this->points[1], this->values[1], r+1, c  , s);
			_get_level(se, this->points[2], this->values[2], r+1, c+1, s);
			_get_level(se, this->points[3], this->values[3], r  , c+1, s);
			_get_level(se, this->points[4], this->values[4], r  , c  , s+1);
			_get_level(se, this->points[5], this->values[5], r+1, c  , s+1);
			_get_level(se, this->points[6], this->values[6], r+1, c+1, s+1);
			_get_level(se, this->points[7], this->values[7], r  , c+1, s+1);
		}

		std::string str(void) const {
			std::ostringstream result;
			result << "{\n";
			for (uint32_t k = 0; k < 8; k++) {
				result << "\t" << this->points[k].str() << " -> " << this->values[k] << "\n";
			}
			result << "}";
			return result.str();
		}
	};


	ArrayOfSharedPolygons contours(const arma::vec& x, const arma::vec& y,
			const arma::mat& values, double level, bool negative=false);

	SharedSurface3d isosurface(const arma::vec& x, const arma::vec& y, const arma::vec& z,
				const arma::cube& values, double level, bool negative);
}

#endif /* OPL_CONTOURS_H_ */
