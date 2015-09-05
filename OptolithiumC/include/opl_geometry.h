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

#ifndef OPL_GEOMETRY_H_
#define OPL_GEOMETRY_H_

#include <stdlib.h>
#include <cmath>
#include <vector>
#include <list>
#include <memory>

#include "opl_log.h"
#include "opl_iter.h"


#if !defined( SWIG )
    // SWIG should not see #include <armadillo> as it can not handle it
	#include <armadillo>
#endif


#if !defined(M_PI) && !defined(SWIG)
	// Shit C++11 standard where not defined in math but this constant defined
	#define M_E			2.7182818284590452354
	#define M_LOG2E		1.4426950408889634074
	#define M_LOG10E	0.43429448190325182765
	#define M_LN2		0.69314718055994530942
	#define M_LN10		2.30258509299404568402
	#define M_PI		3.14159265358979323846
	#define M_PI_2		1.57079632679489661923
	#define M_PI_4		0.78539816339744830962
	#define M_1_PI		0.31830988618379067154
	#define M_2_PI		0.63661977236758134308
	#define M_2_SQRTPI	1.12837916709551257390
	#define M_SQRT2		1.41421356237309504880
	#define M_SQRT1_2	0.70710678118654752440
#endif


namespace geometry {

	typedef enum {
		LEFT = 0,
		RIGHT = 1,
		BEYOND = 2,
		BEHIND = 3,
		BETWEEN = 4,
		ORIGIN = 5,
		DESTINATION = 6,
	} classify_type_t;


	typedef enum {
		COLLINEAR = 0,
		PARALLEL = 1,
		SKEW = 2,
		SKEW_NO_CROSS = 3,
		SKEW_CROSS =4,
	} cross_type_t;


	typedef enum {
		CW = 1,
		CCW = -1,
	} rotation_type_t;


	typedef enum {
		DIM_1D_X = 0,
		DIM_1D_Y = 1,
		DIM_2D = 2
	} dimension_t;


	typedef enum {
		GEOMETRY_POLYGON = 0,
		GEOMETRY_BOX = 1
	} geometry_t;


	#define DEFAULT_CLASSIFY_PRECISION 1e-2


	class Edge2d;


	class Point2d {
	public:
		double x;
		double y;

		Point2d(double x=0.0, double y=0.0) : x(x), y(y) { }

		Point2d(const Point2d& other) : x(other.x), y(other.y) { }

		Point2d operator+(const Point2d& p) const;
		Point2d operator+(double s) const;
		Point2d operator-(const Point2d& p) const;
		Point2d operator-(double s) const;

		double& operator[](uint32_t i);
		double operator[](uint32_t i) const;
		bool operator==(const Point2d& p) const;
		bool operator!=(const Point2d& p) const;
		bool operator<(const Point2d& p) const;
		bool operator>(const Point2d& p) const;

		Point2d& operator+=(const Point2d& rhs);
		Point2d& operator-=(const Point2d& rhs);
		Point2d& abs(void);
		classify_type_t classify(const Point2d& p0, const Point2d& p1,
				double precision=DEFAULT_CLASSIFY_PRECISION) const;
		classify_type_t classify(const Edge2d&, double precision=DEFAULT_CLASSIFY_PRECISION) const;
		double polar_angle(void) const;
		double length(void) const;
		Point2d normal_intersect(const Edge2d&) const;
		double distance(const Edge2d&) const;
		void transform(int32_t sign, double mag, double angle);
		std::string str(void) const;
	};

	Point2d operator* (double s, const Point2d& p);
	Point2d operator/ (const Point2d& p, double s);
	double dot(const Point2d& p, const Point2d& q);


	typedef Point2d Sizes;


	class Edge2d {
	public:
		Point2d org;
		Point2d dst;

		Edge2d(double org_x, double org_y, double dst_x, double dst_y) :
			org(Point2d(org_x, org_y)), dst(Point2d(dst_x, dst_y)) { }

		Edge2d(const Point2d& org, const Point2d& dst) : org(org), dst(dst) { }

		Edge2d& rot(rotation_type_t dir=CCW);
		Edge2d& flip(void);
		cross_type_t intersect(const Edge2d& e, double &t) const;

		// Return intersection point between 'this' edge and edge represented as 't' value (line direction)
		Point2d point(double t) const;

		// Return intersection point between 'this' edge and given edge 'e'
		Point2d point(const Edge2d& e) const;

		cross_type_t cross_type(const Edge2d& e) const;
		bool is_vertical(void) const;
		bool is_horizontal(void) const;
		double dx(void) const;
		double dy(void) const;
		Sizes sizes(void) const;
		double length(void) const;
		double slope(void) const;
		double y(double x) const;

		// Calculate the area of trapezoid between this edge, y-axis and two horizontal lines.
		double area(void) const;

		std::string str(void) const;
		bool operator==(const Edge2d& other) const;
	};


	typedef std::shared_ptr<Point2d> SharedPoint2d;
	typedef std::vector<SharedPoint2d> ArrayOfSharedPoints2d;

	typedef std::shared_ptr<Edge2d> SharedEdge2d;
	typedef std::shared_ptr<const Edge2d> ConstSharedEdge2d;
	typedef std::vector<SharedEdge2d> ArrayOfSharedEdges2d;


	class AbstractGeometry : public Iterable::Interface<SharedEdge2d> {
	protected:
		ArrayOfSharedEdges2d _edges;
		dimension_t _axis;
	public:
		virtual geometry_t type(void) const = 0;
		virtual bool operator==(const AbstractGeometry &other) const = 0;
		virtual std::string str(void) const = 0;

		virtual bool is_mask(void) const {
			return false;
		}

		SharedEdge2d at(uint32_t index) const;
		uint32_t length(void) const;

		double signed_area(void) const;
		virtual bool set_bypass(rotation_type_t direction);
		dimension_t axis(void) const;
	};


	typedef std::shared_ptr<AbstractGeometry> SharedAbstractGeomtery;
	typedef std::vector<SharedAbstractGeomtery> ArrayOfSharedAbstractGeomtery;


	class PolygonGeometry : public virtual AbstractGeometry {
	public:
		// Check whether input points represent one dimensional polygon
		static bool is_1d_possible(const ArrayOfSharedPoints2d &points);
		static bool is_2d_possible(const ArrayOfSharedPoints2d &points);

		PolygonGeometry(const ArrayOfSharedPoints2d &points);
		PolygonGeometry(const PolygonGeometry& other);

		bool clean(void);

		geometry_t type(void) const;
		bool operator==(const AbstractGeometry &other) const;
		std::string str(void) const;
	};


	typedef std::shared_ptr<PolygonGeometry> SharedPolygon;
	typedef std::vector<SharedPolygon> ArrayOfSharedPolygons;


	class RectangleGeometry : public virtual AbstractGeometry {
	private:
		Edge2d _diag;
		Sizes _sizes;
	public:
		RectangleGeometry(const Point2d& lb, const Point2d& rt);
		RectangleGeometry(ArrayOfSharedPoints2d points);
		RectangleGeometry(const RectangleGeometry& other);

		Point2d left_bottom(void) const;
		Point2d right_top(void) const;
		Edge2d diag(void) const;
		Sizes sizes(void) const;
		bool set_bypass(rotation_type_t direction);

		geometry_t type(void) const;
		bool operator==(const AbstractGeometry& other) const;
		std::string str(void) const;
	};


	class Point3d {
	public:
		double x;
		double y;
		double z;

		Point3d(double x=0.0, double y=0.0, double z=0.0) : x(x), y(y), z(z) { }

		Point3d(const Point3d& other) : x(other.x), y(other.y), z(other.z) { }

		Point3d operator+(const Point3d& p) const;
		Point3d operator+(double s) const;
		Point3d operator-(const Point3d& p) const;
		Point3d operator-(double s) const;

		double& operator[](uint32_t i);
		double operator[](uint32_t i) const;
		bool operator==(const Point3d& p) const;
		bool operator!=(const Point3d& p) const;
		bool operator<(const Point3d& p) const;
		bool operator>(const Point3d& p) const;

		Point3d& operator+=(const Point3d& rhs);
		Point3d& operator-=(const Point3d& rhs);
		Point3d& abs(void);

		double length(void) const;

		std::string str(void) const;
	};

	Point3d operator* (double s, const Point3d& p);
	Point3d operator/ (const Point3d& p, double s);
	double dot(const Point3d& p, const Point3d& q);


	typedef std::shared_ptr<Point3d> SharedPoint3d;
	typedef std::shared_ptr<const Point3d> ConstSharedPoint3d;
	typedef std::vector<SharedPoint3d> ArrayOfSharedPoints3d;


	class Edge3d {
	public:
		Point3d org;
		Point3d dst;

		Edge3d(double org_x, double org_y, double org_z, double dst_x, double dst_y, double dst_z) :
			org(Point3d(org_x, org_y, org_z)), dst(Point3d(dst_x, dst_y, dst_z)) { }

		Edge3d(const Point3d& org, const Point3d& dst) : org(org), dst(dst) { }

		double length(void) const;

		std::string str(void) const;
		bool operator==(const Edge3d& other) const;
	};

	double dot(const Edge3d& p, const Edge3d& q);
	Point3d cross(const Edge3d& p, const Edge3d& q);

	typedef std::shared_ptr<Edge3d> SharedEdge3d;
	typedef std::vector<SharedEdge3d> ArrayOfSharedEdges3d;


	class Triangle3d : public Iterable::Interface<SharedPoint3d> {
	private:
		SharedPoint3d _a, _b, _c;
	public:
		Triangle3d(SharedPoint3d a, SharedPoint3d b, SharedPoint3d c) : _a(a), _b(b), _c(c) { }
		Triangle3d(const Point3d& a, const Point3d& b, const Point3d& c);

		uint32_t length(void) const {
			return 3;
		}

		bool operator==(const Triangle3d &other) const;
		std::string str(void) const;

		SharedPoint3d at(uint32_t index) const;
		Point3d& operator[](uint32_t i);
		Point3d operator[](uint32_t i) const;

		SharedPoint3d normal(void) const;

		SharedPoint3d a(void) const {
			return this->_a;
		}

		SharedPoint3d b(void) const {
			return this->_b;
		}

		SharedPoint3d c(void) const {
			return this->_c;
		}
	};


	typedef std::shared_ptr<Triangle3d> SharedTriangle3d;
	typedef std::vector<SharedTriangle3d> ArrayOfSharedTriangles3d;


	class Surface3d {
	private:
		bool _is_finalized;

		ArrayOfSharedPoints3d _points;
		ArrayOfSharedTriangles3d _triangles;

		std::shared_ptr<arma::vec> _x;
		std::shared_ptr<arma::vec> _y;
		std::shared_ptr<arma::vec> _z;
	public:
		Surface3d() {
			this->_is_finalized = false;
		};

		Surface3d(ArrayOfSharedPoints3d points, ArrayOfSharedTriangles3d triangles);

		bool add_point(SharedPoint3d point) {
			if (!this->_is_finalized) {
				this->_points.push_back(point);
				return true;
			} else {
				return false;
			}
		}

		bool add_triangle(SharedTriangle3d triangle) {
			if (!this->_is_finalized) {
				this->_triangles.push_back(triangle);
				return true;
			} else {
				return false;
			}
		}

		void generate_xyz(void);

		ArrayOfSharedPoints3d points(void) const;
		ArrayOfSharedTriangles3d triangles(void) const;
		std::shared_ptr<arma::vec> x(void) const;
		std::shared_ptr<arma::vec> y(void) const;
		std::shared_ptr<arma::vec> z(void) const;
	};

	typedef std::shared_ptr<Surface3d> SharedSurface3d;
}

#endif /* OPL_GEOMETRY_H_ */
