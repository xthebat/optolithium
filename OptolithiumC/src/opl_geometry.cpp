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

#include "opl_geometry.h"
#include "opl_misc.h"

namespace geometry {

	/* ==================================== Point ==================================== */

	Point2d Point2d::operator+(const Point2d& p) const {
		return Point2d(this->x + p.x, this->y + p.y);
	}

	Point2d Point2d::operator+(double s) const {
		return Point2d(this->x + s, this->y + s);
	}

	Point2d Point2d::operator-(const Point2d& p) const {
		return Point2d(this->x - p.x, this->y - p.y);
	}

	Point2d Point2d::operator-(double s) const {
		return Point2d(this->x - s, this->y - s);
	}

	Point2d operator* (double s, const Point2d& p) {
		return Point2d(s * p.x, s * p.y);
	}

	Point2d operator/ (const Point2d& p, double s) {
		return Point2d(p.x/s, p.y/s);
	}

	double dot(const Point2d& p, const Point2d& q) {
		return p.x*q.x + p.y*q.y;
	}

	double& Point2d::operator[](uint32_t i) {
		return (i == 0) ? this->x : this->y;
	}

	double Point2d::operator[](uint32_t i) const {
		return (i == 0) ? this->x : this->y;
	}

	bool Point2d::operator==(const Point2d& p) const {
		return (this->x == p.x) && (this->y == p.y);
	}

	bool Point2d::operator!=(const Point2d& p) const {
		return (this->x != p.x) || (this->y != p.y);
	}

	bool Point2d::operator<(const Point2d& p) const {
		return ((this->x < p.x) || ((this->x == p.x) && (this->y < p.y)));
	}

	bool Point2d::operator>(const Point2d& p) const {
		return ((this->x > p.x) || ((this->x == p.x) && (this->y > p.y)));
	}

	Point2d& Point2d::operator+=(const Point2d& rhs) {
		this->x += rhs.x;
		this->y += rhs.y;
		return *this;
	}

	Point2d& Point2d::operator-=(const Point2d& rhs) {
		this->x -= rhs.x;
		this->y -= rhs.y;
		return *this;
	}

	Point2d& Point2d::abs(void) {
		this->x = (this->x >= 0) ? this->x : -this->x;
		this->y = (this->y >= 0) ? this->y : -this->y;
		return *this;
	}

	classify_type_t Point2d::classify(const Point2d& p0, const Point2d& p1, double precision) const {
		Point2d p2 = *this;
		Point2d a = p1 - p0;
		Point2d b = p2 - p0;
		double sa = a.x*b.y - b.x*a.y;

		if (sa > precision) {
			return LEFT;
		} else if (sa < -precision) {
			return RIGHT;
		} else if (a.x*b.x < 0 || a.y*b.y < 0) {
			return BEHIND;
		} else if (a.length() < b.length()) {
			return BEYOND;
		} else if (p0 == p2) {
			return ORIGIN;
		} else if (p1 == p2) {
			return DESTINATION;
		} else {
			return BETWEEN;
		}
	}

	classify_type_t Point2d::classify(const Edge2d& e, double precision) const {
		return this->classify(e.org, e.dst, precision);
	}

	double Point2d::polar_angle(void) const {
		if (this->x == 0 && this->y == 0) {
			return -1;
		} else if (this->x == 0) {
			return ((this->y > 0.0) ? 90.0 : 270.0);
		}

		double theta = atan(this->y/this->x);
		theta *= 360/(2*M_PI);

		if (x > 0)
			return ((y >= 0) ? theta : 360.0 + theta);
		else
			return	180.0 + theta;
	}

	double Point2d::length(void) const {
		return sqrt(this->x*this->x + this->y*this->y);
	}

	Point2d Point2d::normal_intersect(const Edge2d& e) const {
		Edge2d ab = e;
		ab.rot(CCW);
		Point2d n(ab.dst - ab.org);
		Edge2d normal(*this, *this + n);
		return e.point(normal);
	}

	double Point2d::distance(const Edge2d& e) const {
		Point2d s = this->normal_intersect(e);
		return Edge2d(*this, s).length();
	}

	void Point2d::transform(int32_t sign, double mag, double angle) {
		double xp = this->x, yp = this->y;
		double cos_ang = cos(angle), sin_ang = sin(angle);

		this->x = mag * (xp * cos_ang - sign * yp * sin_ang);
		this->y = mag * (xp * sin_ang + sign * yp * cos_ang);
	}

	std::string Point2d::str(void) const {
		std::ostringstream result;
		result << "(" << this->x << ", " << this->y << ")";
		return result.str();
	}

	/* ==================================== Edge ==================================== */

	Edge2d& Edge2d::rot(rotation_type_t dir) {
		int32_t sign = (dir == CW) ? -1 : 1;
		Point2d m = 0.5 * (this->org + this->dst);
		Point2d v = this->dst - this->org;
		Point2d n(v.y, -v.x);
		this->org = m + sign * 0.5 * n;
		this->dst = m - sign * 0.5 * n;
		return *this;
	}

	Edge2d& Edge2d::flip(void) {
		misc::swap(this->dst.x, this->org.x);
		misc::swap(this->dst.y, this->org.y);
		return *this;
	}

	cross_type_t Edge2d::intersect(const Edge2d& e, double &t) const {
		Point2d a = this->org;
		Point2d b = this->dst;
		Point2d c = e.org;
		Point2d d = e.dst;
		Point2d n = Point2d((d - c).y, (c - d).x);
		double denom = dot(n, b-a);

		if (denom == 0)
		{
			if (this->org.classify(e) == LEFT || this->org.classify(e) == RIGHT) {
				return PARALLEL;
			} else {
				return COLLINEAR;
			}
		}
		double num = dot(n, a-c);
		t = -num/denom;
		return SKEW;
	}

	// Return intersection point between 'this' edge and edge represented as 't' value (line direction)
	Point2d Edge2d::point(double t) const {
		return Point2d(this->org + t*(this->dst - this->org));
	}

	// Return intersection point between 'this' edge and given edge 'e'
	Point2d Edge2d::point(const Edge2d& e) const {
		double t = 0.0;
		this->intersect(e, t);
		return this->point(t);
	}

	cross_type_t Edge2d::cross_type(const Edge2d& e) const {
		double s = 0.0, t = 0.0;

		cross_type_t cross = e.intersect(*this, s);
		if (cross == COLLINEAR || cross == PARALLEL)
			return cross;

		if (s < 0.0 || s > 1.0)
			return SKEW_NO_CROSS;

		// Calculate t-value
		this->intersect(e, t);

		if (0.0 <= t || t <= 1.0) {
			return SKEW_CROSS;
		} else {
			return SKEW_NO_CROSS;
		}
	}

	bool Edge2d::is_vertical(void) const {
		return this->org.x == this->dst.x;
	}

	bool Edge2d::is_horizontal(void) const {
		return this->org.y == this->dst.y;
	}

	double Edge2d::dx(void) const {
		return this->dst.x - this->org.x;
	}

	double Edge2d::dy(void) const {
		return this->dst.y - this->org.y;
	}

	Sizes Edge2d::sizes(void) const {
		return this->dst - this->org;
	}

	double Edge2d::length(void) const {
		return this->sizes().length();
	}

	double Edge2d::slope(void) const {
		if (this->dx() != 0.0) {
			return this->dy()/this->dx();
		} else {
			// Infinity slope
			return this->dy() * INFINITY;
		}
	}

	double Edge2d::y(double x) const {
		return this->slope()*(x - this->org.x) + this->org.y;
	}

	// Calculate the area of trapezoid between this edge, y-axis and two horizontal lines.
	double Edge2d::area(void) const {
		return this->dx() * (this->dst.y + this->org.y) / 2.0;
	}

	std::string Edge2d::str(void) const {
		std::ostringstream result;
		result << "[" << this->org.str() << " -> " << this->dst.str() << "]";
		return result.str();
	}

	bool Edge2d::operator==(const Edge2d& other) const {
		return this->org == other.org && this->dst == other.dst;
	}

	/* ==================================== AbstractGeometry ==================================== */

	SharedEdge2d AbstractGeometry::at(uint32_t index) const {
		return this->_edges.at(index);
	}

	uint32_t AbstractGeometry::length(void) const {
		return static_cast<uint32_t>(this->_edges.size());
	}

	double AbstractGeometry::signed_area(void) const {
		double result = 0.0;
		if (this->_axis == DIM_2D) {
			for (auto edge : this->_edges) {
				result += edge->area();
			}
		} else {
			SharedEdge2d e = this->front();
			uint32_t axis = this->_axis;
			result = e->dst[axis] - e->org[axis];
		}
		return result;
	}

	bool AbstractGeometry::set_bypass(rotation_type_t direction) {
		bool corrected = false;
		double area = this->signed_area();
		if (direction*area < 0) {
			corrected = true;
			std::reverse(this->_edges.begin(), this->_edges.end());
			for (auto edge : this->_edges) {
				edge->flip();
			}
		}
		return corrected;
	}

	dimension_t AbstractGeometry::axis(void) const {
		return this->_axis;
	}

	/* ==================================== PolygonGeometry ==================================== */

	geometry_t PolygonGeometry::type(void) const {
		return GEOMETRY_POLYGON;
	}

	// Check whether input points represent one dimensional polygon
	bool PolygonGeometry::is_1d_possible(const ArrayOfSharedPoints2d &points) {
		if (points.size() == 2) {
			const Edge2d edge = Edge2d(*points[0], *points[1]);
			if (edge.is_vertical() || edge.is_horizontal()) {
				return true;
			}
		}
		return false;
	}

	bool PolygonGeometry::is_2d_possible(const ArrayOfSharedPoints2d &points) {
		return points.size() >= 3;
	}

	PolygonGeometry::PolygonGeometry(const ArrayOfSharedPoints2d &points) {
		if (PolygonGeometry::is_1d_possible(points)) {
			SharedEdge2d edge = std::make_shared<Edge2d>(*points.back(), *points.front());
			this->_edges.push_back(edge);
			this->_axis = edge->is_horizontal() ? DIM_1D_X : DIM_1D_Y;
		} else if (PolygonGeometry::is_2d_possible(points)) {
			auto start = points.begin();
			SharedPoint2d previous_point = *start;
			for (auto it = ++start; it != points.end(); ++it) {
				SharedPoint2d current_point = *it;
				this->_edges.push_back(std::make_shared<Edge2d>(*previous_point, *current_point));
				previous_point = current_point;
			}
			this->_edges.push_back(std::make_shared<Edge2d>(*points.back(), *points.front()));
			this->_axis = DIM_2D;
		} else {
			throw std::invalid_argument("Can't create region from passed points sequence!");
		}
	}

	PolygonGeometry::PolygonGeometry(const PolygonGeometry& other) {
		this->_axis = other._axis;
		for (auto edge : other) {
			this->_edges.push_back(std::make_shared<Edge2d>(*edge));
		}
	}

	bool PolygonGeometry::clean(void) {
		if (this->_axis == DIM_2D) {
//			LOG(INFO) << "Clean polygon with " << this->length() << " edges";
			bool deleted = false;
			auto it = this->begin();
			while (this->length() && it != this->end()) {
//				SharedEdge prev_edge = *it.prev();
//				bool is_end = !(it.prev() != this->end());
//				LOG(INFO) << "[" << is_end << "] Prev Edge[" << it.prev().pos() << "/"
//						<< this->length() << "] = " << prev_edge->str();

				SharedEdge2d cur_edge = *it;
//				is_end = !(it != this->end());
//				LOG(INFO) << "[" << is_end << "] Cur  Edge[" << it.pos() << "/"
//						<< this->length() << "] = " << cur_edge->str();

				SharedEdge2d next_edge = *it.next();
//				is_end = !(it.next() != this->end());
//				LOG(INFO) << "[" << is_end << "] Next Edge[" << it.next().pos() << "/"
//						<< this->length() << "] = " << next_edge->str();

				bool remove_required = false;
				if (cur_edge->length() == 0.0) {
					remove_required = true;
				} else {
					double tmp = 0.0;
					if (cur_edge->intersect(*next_edge, tmp) == COLLINEAR) {
						remove_required = true;
					}
				}

				if (remove_required) {
//					LOG(INFO) << "---> Erase edge: " << (*it)->str();
					this->_edges.erase(this->_edges.begin() + it.pos());
					(*it)->org = (*it.prev())->dst;
					deleted = true;
				} else {
					++it;
				}
			}

			this->_edges.shrink_to_fit();

//			LOG(INFO) << "Cleaned polygon[" << deleted << "] " << this->str();

			return deleted;
		} else {
			return false;
		}
	}

	std::string PolygonGeometry::str(void) const {
		std::ostringstream result;
		result << "PolygonGeometry {";
		for (auto edge : this->_edges) {
			result << std::endl << "\t" << edge->str();
		}
		result << "};";
		return result.str();
	}

	bool PolygonGeometry::operator==(const AbstractGeometry& other) const {
		return this->type() == other.type() && misc::safe_vector_equal(this->_edges,
				dynamic_cast<const PolygonGeometry*>(&other)->_edges);
	}

	/* ==================================== RectangleGeometry ==================================== */

	geometry_t RectangleGeometry::type(void) const {
		return GEOMETRY_BOX;
	}

	RectangleGeometry::RectangleGeometry(const Point2d& lb, const Point2d& rt) : _diag(Edge2d(lb, rt)) {
		this->_sizes = this->_diag.sizes();

		if (this->_sizes.x != 0.0 && this->_sizes.y != 0.0) {
			this->_axis = DIM_2D;

			this->_edges = {
				std::make_shared<Edge2d>(lb.x, lb.y, rt.x, lb.y),
				std::make_shared<Edge2d>(rt.x, lb.y, rt.x, rt.y),
				std::make_shared<Edge2d>(rt.x, rt.y, lb.x, rt.y),
				std::make_shared<Edge2d>(lb.x, rt.y, lb.x, lb.y)
			};
		} else if (this->_sizes.x != 0.0) {
			this->_axis = DIM_1D_X;
			this->_edges = { std::make_shared<Edge2d>(this->_diag) };
		} else {
			this->_axis = DIM_1D_Y;
			this->_edges = { std::make_shared<Edge2d>(this->_diag) };
		}
	}

	RectangleGeometry::RectangleGeometry(ArrayOfSharedPoints2d points) : RectangleGeometry(*points[0], *points[1]) { }

	RectangleGeometry::RectangleGeometry(const RectangleGeometry& other) :
		RectangleGeometry(other.left_bottom(), other.right_top()) { }

	Point2d RectangleGeometry::left_bottom(void) const {
		return this->_diag.org;
	}

	Point2d RectangleGeometry::right_top(void) const {
		return this->_diag.dst;
	}

	Edge2d RectangleGeometry::diag(void) const {
		return this->_diag;
	}

	Sizes RectangleGeometry::sizes(void) const {
		return this->_sizes;
	}

	bool RectangleGeometry::set_bypass(rotation_type_t direction) {
		bool corrected = false;
		if (AbstractGeometry::set_bypass(direction)) {
			this->_diag.flip();
			corrected = true;
		}
		return corrected;
	}

	bool RectangleGeometry::operator==(const AbstractGeometry& other) const {
		return this->type() == other.type() && this->_diag == dynamic_cast<const RectangleGeometry*>(&other)->_diag;
	}

	std::string RectangleGeometry::str(void) const {
		std::ostringstream result;
		result << "RectangleGeometry {";
		result << std::endl << "\t" << this->_diag.org.str();
		result << std::endl << "\t" << this->_diag.dst.str();
		result << "};";
		return result.str();
	}

	/* ==================================== Point 3d ==================================== */

	Point3d Point3d::operator+(const Point3d& p) const {
		return Point3d(this->x + p.x, this->y + p.y, p.z + this->z);
	}

	Point3d Point3d::operator+(double s) const {
		return Point3d(this->x + s, this->y + s, this->z + s);
	}

	Point3d Point3d::operator-(const Point3d& p) const {
		return Point3d(this->x - p.x, this->y - p.y, this->z - p.z);
	}

	Point3d Point3d::operator-(double s) const {
		return Point3d(this->x - s, this->y - s, this->z - s);
	}

	Point3d operator* (double s, const Point3d& p) {
		return Point3d(s * p.x, s * p.y, s * p.z);
	}

	Point3d operator/ (const Point3d& p, double s) {
		return Point3d(p.x/s, p.y/s, p.z/s);
	}

	double dot(const Point3d& p, const Point3d& q) {
		return p.x*q.x + p.y*q.y + p.z*q.z;
	}

	double& Point3d::operator[](uint32_t i) {
		if (i == 0) {
			return this->x;
		} else if (i == 1) {
			return this->y;
		} else if (i == 2) {
			return this->z;
		} else {
			throw std::out_of_range("The index of dimensions is out of range");
		}
	}

	double Point3d::operator[](uint32_t i) const {
		if (i == 0) {
			return this->x;
		} else if (i == 1) {
			return this->y;
		} else if (i == 2) {
			return this->z;
		} else {
			throw std::out_of_range("The index of dimensions is out of range");
		}
	}

	bool Point3d::operator==(const Point3d& p) const {
		return (this->x == p.x) && (this->y == p.y);
	}

	bool Point3d::operator!=(const Point3d& p) const {
		return (this->x != p.x) || (this->y != p.y);
	}

	bool Point3d::operator<(const Point3d& p) const {
		if (this->x < p.x) {
			return true;
		} else if (this->x == p.x) {
			if (this->y < p.y) {
				return true;
			} else if (this->y == p.y) {
				return this->z < p.z;
			} else {
				return false;
			}
		} else {
			return false;
		}
	}

	bool Point3d::operator>(const Point3d& p) const {
		if (this->x > p.x) {
			return true;
		} else if (this->x == p.x) {
			if (this->y > p.y) {
				return true;
			} else if (this->y == p.y) {
				return this->z > p.z;
			} else {
				return false;
			}
		} else {
			return false;
		}
	}

	Point3d& Point3d::operator+=(const Point3d& rhs) {
		this->x += rhs.x;
		this->y += rhs.y;
		this->z += rhs.z;
		return *this;
	}

	Point3d& Point3d::operator-=(const Point3d& rhs) {
		this->x -= rhs.x;
		this->y -= rhs.y;
		this->z -= rhs.z;
		return *this;
	}

	Point3d& Point3d::abs(void) {
		this->x = fabs(this->x);
		this->y = fabs(this->y);
		this->z = fabs(this->z);
		return *this;
	}

	double Point3d::length(void) const {
		return sqrt(this->x*this->x + this->y*this->y + this->z*this->z);
	}

	std::string Point3d::str(void) const {
		std::ostringstream result;
		result << "(" << this->x << ", " << this->y << ", " << this->z << ")";
		return result.str();
	}

	/* ==================================== Edge 3d ==================================== */

	double Edge3d::length(void) const {
		Point3d v = (this->dst - this->org);
		return sqrt(dot(v, v));
	}

	std::string Edge3d::str(void) const {
		std::ostringstream result;
		result << "[" << this->org.str() << " -> " << this->dst.str() << "]";
		return result.str();
	}

	bool Edge3d::operator==(const Edge3d& other) const {
		return this->org == other.org && this->dst == other.dst;
	}

	double dot(const Edge3d& p, const Edge3d& q) {
		return dot(p.dst - p.org, q.dst - q.org);
	}

	Point3d cross(const Edge3d& p, const Edge3d& q) {
		Point3d a = p.dst - p.org;
		Point3d b = q.dst - q.org;
		return Point3d(
				a.y * b.z - a.z * b.y,
				a.z * b.x - a.x * b.z,
				a.x * b.y - a.y * b.z);
	}

	/* ==================================== Triangle 3d ==================================== */

	Triangle3d::Triangle3d(const Point3d& a, const Point3d& b, const Point3d& c) {
		// TODO: Check that points can create triangle
		this->_a = std::make_shared<Point3d>(a);
		this->_b = std::make_shared<Point3d>(b);
		this->_c = std::make_shared<Point3d>(c);
	}

	bool Triangle3d::operator==(const Triangle3d &other) const {
		return *this->_a == other[0] && *this->_b == other[1] && *this->_c == other[2];
	}

	std::string Triangle3d::str(void) const {
		std::ostringstream result;
		result << "{" << this->_a->str() << ", " << this->_b->str() << ", " << this->_c->str() << "}";
		return result.str();
	}

	SharedPoint3d Triangle3d::at(uint32_t index) const {
		if (index == 0) {
			return this->_a;
		} else if (index == 1) {
			return this->_b;
		} else if (index == 2) {
			return this->_c;
		} else {
			throw std::out_of_range("The index of dimensions is out of range");
		}
	}

	Point3d& Triangle3d::operator[](uint32_t i){
		if (i == 0) {
			return *this->_a;
		} else if (i == 1) {
			return *this->_b;
		} else if (i == 2) {
			return *this->_c;
		} else {
			throw std::out_of_range("The index of dimensions is out of range");
		}
	}

	Point3d Triangle3d::operator[](uint32_t i) const {
		if (i == 0) {
			return *this->_a;
		} else if (i == 1) {
			return *this->_b;
		} else if (i == 2) {
			return *this->_c;
		} else {
			throw std::out_of_range("The index of dimensions is out of range");
		}
	}

	SharedPoint3d Triangle3d::normal(void) const {
		Point3d n = cross(Edge3d(*this->_a, *this->_b), Edge3d(*this->_b, *this->_c));
		return std::make_shared<Point3d>(n/n.length());
	}

	/* ==================================== Surface 3d ==================================== */

	Surface3d::Surface3d(ArrayOfSharedPoints3d points, ArrayOfSharedTriangles3d triangles) : Surface3d() {
		this->_points = points;
		this->_triangles = triangles;
		this->generate_xyz();
	}

	void Surface3d::generate_xyz(void) {
		if (!this->_is_finalized) {
			uint32_t length = this->_points.size();
			this->_x = std::make_shared<arma::vec>(length);
			this->_y = std::make_shared<arma::vec>(length);
			this->_z = std::make_shared<arma::vec>(length);
			for (uint32_t k = 0; k < this->_points.size(); k++) {
				(*this->_x)(k) = this->_points[k]->x;
				(*this->_y)(k) = this->_points[k]->y;
				(*this->_z)(k) = this->_points[k]->z;
			}
			this->_is_finalized = true;
		}
	}

	ArrayOfSharedPoints3d Surface3d::points(void) const {
		return this->_points;
	}

	ArrayOfSharedTriangles3d Surface3d::triangles(void) const {
		return this->_triangles;
	}

	std::shared_ptr<arma::vec> Surface3d::x(void) const {
		return this->_x;
	}

	std::shared_ptr<arma::vec> Surface3d::y(void) const {
		return this->_y;
	}

	std::shared_ptr<arma::vec> Surface3d::z(void) const {
		return this->_z;
	}
}
