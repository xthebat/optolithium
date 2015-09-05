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

#ifndef OPTOLITHIUMC_HPP_
#define OPTOLITHIUMC_HPP_

#include <complex>
#include <algorithm>

#if !defined( SWIG )
    // SWIG should not see #include <armadillo> as it can not handle it
	#include <armadillo>
#endif

#include "opl_geometry.h"
#include "opl_interp.h"
#include "opl_contours.h"
#include "opl_physc.h"
#include "opl_misc.h"
#include "optolithium.h"


#define OPTOLITHIUM_CORE_VERSION "0.7a"


namespace oplc {

    using namespace geometry;

    //using namespace std::literals::complex_literals;
    const arma::cx_double j = arma::cx_double(0.0, 1.0);


    inline arma::cx_double _etransmit(double transmit, double phase) {
        return std::sqrt(transmit) * std::exp(j*phase*M_PI/180.0);
    }


    typedef enum {   // z y x
          X_1D = 1,  // 0 0 1
          Y_1D = 2,  // 0 1 0
         XY_2D = 3,  // 0 1 1
         XZ_2D = 5,  // 1 0 1
         YZ_2D = 6,  // 1 1 0
        XYZ_3D = 7,  // 1 1 1
    } resist_volume_type_t;


    typedef enum {
        RESIST_VOLUME = 0,
        RESIST_PROFILE = 1,
    } resist_simulations_t;


    class AbstractResistSimulations {
    protected:
        // Each coordinate values data
        std::shared_ptr<arma::vec> _x;
        std::shared_ptr<arma::vec> _y;
        std::shared_ptr<arma::vec> _z;

        double _stepx;
        double _stepy;
        double _stepz;
    public:
        virtual resist_simulations_t type(void) const = 0;
        virtual ~AbstractResistSimulations(void) { }

        std::shared_ptr<arma::vec> x(void) const;
        std::shared_ptr<arma::vec> y(void) const;
        std::shared_ptr<arma::vec> z(void) const;
        
        double x(uint32_t k) const;
        double y(uint32_t k) const;
        double z(uint32_t k) const;

        bool has_x(void) const;
        bool has_y(void) const;
        bool has_z(void) const;

        double stepx(void) const;
        double stepy(void) const;
        double stepz(void) const;

        resist_volume_type_t axes(void) const;
    };


    typedef std::shared_ptr<AbstractResistSimulations> SharedAbstractResistSimulations;


    class ResistVolume : public AbstractResistSimulations {
    private:
        // Values being calculated
        std::shared_ptr<arma::cube> _values;

        inline static double _calc_lateral_step(double mask_pitch, double desired_step) {
            if (mask_pitch == 0.0 || desired_step == 0.0) {
                return 0.0;
            } else {
                int32_t n = static_cast<int32_t>(ceil(mask_pitch/desired_step));
                if (mask_pitch/static_cast<double>(n-1) > desired_step) {
                    n += (n % 2) ? 2 : 1;
                }
                return mask_pitch/static_cast<double>(n-1);
            }
        }

        inline static double _calc_normal_step(double thickness, double desired_step) {
            if (thickness == 0.0 || desired_step == 0.0) {
                return 0.0;
            } else {
                double tmp = thickness / desired_step;
                if (tmp - round(tmp) != 0.0) {
                    return thickness/ceil(tmp + 1);
                } else {
                    return desired_step;
                }
            }
        }

        // Offset required to make lateral counts odd
        inline static uint32_t _get_count(double size, double step, uint32_t offset=0) {
            if (size == 0.0 || step == 0.0) {
                return 1;
            } else {
                return static_cast<uint32_t>(ceil(size/step)+offset);
            }
        }

        inline static void _init_vector(arma::vec& vec, double start, double step) {
            for (uint32_t k = 0; k < vec.n_elem; k++) {
                vec(k) = k * step + start;
            }
        }
    public:
        // Cached input data
        const RectangleGeometry boundary;
        const double thickness;
        const double desired_stepxy;
        const double desired_stepz;

        // Initialization for 2D/3D cases (e.g. Image in Resist, Latent Image, PAC, Development Rates)
        ResistVolume(const RectangleGeometry& boundary, double thickness, double desired_stepxy, double desired_stepz);
        // Initialization for 1D/2D cases (e.g. for AerialImage)
        ResistVolume(const RectangleGeometry& boundary, double desired_step);
        ResistVolume(const ResistVolume& other, bool copydata=false);
        
        std::shared_ptr<arma::cube> values(void) const;
        double& value(uint32_t u, uint32_t v=0, uint32_t k=0) const;
        resist_simulations_t type(void) const;
    };


    typedef std::shared_ptr<ResistVolume> SharedResistVolume;


    class ResistProfile : public AbstractResistSimulations {
    private:
        ArrayOfSharedPolygons _polygons;
    public:
        ResistProfile(SharedResistVolume volume, double level);
        ArrayOfSharedPolygons polygons(void) const;
        resist_simulations_t type(void) const;
    };


    typedef std::shared_ptr<ResistProfile> SharedResistProfile;


    class AbstractMaskGeometry : public virtual AbstractGeometry {
    protected:
        double _transmittance;
        double _phase;
    public:
        AbstractMaskGeometry(double transmittance, double phase) : _transmittance(transmittance), _phase(phase) { }

        double transmittance(void) const;
        double phase(void) const;
        bool is_mask(void) const;

        // Effective transmittance of the region
        arma::cx_double etransmit(void);

        bool operator==(const AbstractGeometry& other) const;
    };


    class Region : public AbstractMaskGeometry, public PolygonGeometry {
    public:
        Region(const ArrayOfSharedPoints2d &points, double transmittance, double phase) :
            AbstractMaskGeometry(transmittance, phase), PolygonGeometry(points) { }

        Region(const Region& other) : AbstractMaskGeometry(other._transmittance, other._phase), PolygonGeometry(other) { }

        bool operator==(const AbstractGeometry& other) const {
            return AbstractMaskGeometry::operator ==(other) && PolygonGeometry::operator ==(other);
        }
    };


    class Box : public AbstractMaskGeometry, public RectangleGeometry {
    public:
        Box(const Point2d& lb, const Point2d& rt, double transmittance, double phase) :
            AbstractMaskGeometry(transmittance, phase), RectangleGeometry(lb, rt) { }

        Box(ArrayOfSharedPoints2d points, double transmittance, double phase) :
            Box(*points[0], *points[1], transmittance, phase) { }

        Box(const Box& other) : Box(other.left_bottom(), other.right_top(), other._transmittance, other._phase) { }

        bool operator==(const AbstractGeometry& other) const {
            return AbstractMaskGeometry::operator ==(other) && RectangleGeometry::operator ==(other);
        }
    };


    typedef std::shared_ptr<AbstractMaskGeometry> SharedAbstractMaskGeometry;
    typedef std::vector<SharedAbstractMaskGeometry> ArrayOfSharedAbstractMaskGeometry;

    typedef std::shared_ptr<Region> SharedRegion;
    typedef std::shared_ptr<const Region> ConstSharedRegion;
    typedef std::vector<SharedRegion> ArrayOfSharedRegions;
    typedef std::shared_ptr<Box> SharedBox;
    typedef std::shared_ptr<const Box> ConstSharedBox;


    class Mask: public Iterable::Interface<SharedRegion> {
    protected:
        SharedBox _boundary;
        ArrayOfSharedRegions _regions;
        Sizes _sizes;

        // Correct mask region according to diffraction calculation requirements
        static SharedRegion _make_region(ConstSharedRegion region, const Point2d& center_offset);
    public:
        SharedRegion at(uint32_t index) const;
        uint32_t length(void) const;

        Mask(const ArrayOfSharedRegions& regions, SharedBox boundary);
        Mask(const Mask& other);

        SharedBox boundary(void) const;
        Sizes pitch(void) const;
        bool is_opaque(void) const;
        bool is_clear(void) const;
        bool is_bad(void) const;
        bool is_1d(void) const;
        bool operator==(const Mask& other) const;
    };


    typedef std::shared_ptr<Mask> SharedMask;


    typedef enum {
        PLUGIN_MODEL_TYPE = 0,
        SHEET_MODEL_TYPE = 1,
        EMPTY_MODEL_TYPE = 2
    } common_model_type_t;


    class AbstractSourceShapeModel {
    public:
        const common_model_type_t type;

        AbstractSourceShapeModel(common_model_type_t type) : type(type) { }
        virtual ~AbstractSourceShapeModel(void) { };
        virtual double calculate(double sx, double sy) const = 0;
        virtual bool operator==(const AbstractSourceShapeModel& other) const = 0;
    };


    class SourceShapeModelPlugin : public AbstractSourceShapeModel {
    private:
        const source_shape_expr_t _expression;
        const std::vector<double> _args;
        const void *_pargs;
    public:
        SourceShapeModelPlugin(source_shape_expr_t expression, std::vector<double> args);
        double calculate(double sx, double sy) const;
        bool operator==(const AbstractSourceShapeModel& other) const;
    };


    class SourceShapeModelSheet : public AbstractSourceShapeModel {
    private:
        const interp::LinearInterpolation2d _interp;
    public:
        // armanpy not support pass arrays by shared_ptr
        SourceShapeModelSheet(const arma::vec& sx, const arma::vec& sy, const arma::mat& intensity);
        double calculate(double sx, double sy) const;
        bool operator==(const AbstractSourceShapeModel& other) const;
    };


    class AbstractResistRateModel {
    public:
        const common_model_type_t type;

        AbstractResistRateModel(common_model_type_t type) : type(type) { }
        virtual ~AbstractResistRateModel(void) { };
        virtual double calculate(double pac, double depth=0.0) const = 0;
        virtual bool operator==(const AbstractResistRateModel& other) const = 0;
    };


    class ResistRateModelExpression : public AbstractResistRateModel {
    private:
        const rate_model_expr_t _expression;
        const std::vector<double> _args;
        const void *_pargs;
    public:
        ResistRateModelExpression(rate_model_expr_t expression, std::vector<double> args);
        double calculate(double pac, double depth=0.0) const;
        bool operator==(const AbstractResistRateModel& other) const;
    };


    class ResistRateModelDepthSheet : public AbstractResistRateModel {
    private:
        const interp::LinearInterpolation2d _interp;
    public:
    //	armanpy not support pass arrays by shared_ptr
        ResistRateModelDepthSheet(const arma::vec& pac, const arma::vec& depth, const arma::mat& rate);
        double calculate(double pac, double depth=0.0) const;
        bool operator==(const AbstractResistRateModel& other) const;
    };


    class ResistRateModelSheet : public AbstractResistRateModel {
    private:
        const interp::LinearInterpolation1d _interp;
    public:
    //	armanpy not support pass arrays by shared_ptr
        ResistRateModelSheet(const arma::vec& pac, const arma::vec& rate);
        double calculate(double pac, double depth=0.0) const;
        bool operator==(const AbstractResistRateModel& other) const;
    };


    class AbstractPupilFilterModel {
    public:
        const common_model_type_t type;

        AbstractPupilFilterModel(common_model_type_t type) : type(type) { }
        virtual ~AbstractPupilFilterModel(void) { };
        virtual arma::cx_double calculate(double sx, double sy) const = 0;
        virtual bool operator==(const AbstractPupilFilterModel& other) const = 0;
    };


    class PupilFilterModelPlugin : public AbstractPupilFilterModel {
    private:
        const pupil_filter_expr_t _expression;
        const std::vector<double> _args;
        const void *_pargs;
    public:
        PupilFilterModelPlugin(pupil_filter_expr_t expression, std::vector<double> args);
        arma::cx_double calculate(double sx, double sy) const;
        bool operator==(const AbstractPupilFilterModel& other) const;
    };


    class PupilFilterModelSheet : public AbstractPupilFilterModel {
    private:
        interp::LinearInterpolation2d _interp_real;
        interp::LinearInterpolation2d _interp_imag;
    public:
        // armanpy not support pass arrays by shared_ptr
        PupilFilterModelSheet(const arma::vec& sx, const arma::vec& sy, const arma::cx_mat& coef);
        arma::cx_double calculate(double sx, double sy) const;
        bool operator==(const AbstractPupilFilterModel& other) const;
    };


    class PupilFilterModelEmpty : public AbstractPupilFilterModel {
    public:
        PupilFilterModelEmpty(void);
        arma::cx_double calculate(double sx, double sy) const;
        bool operator==(const AbstractPupilFilterModel& other) const;
    };


    typedef std::shared_ptr<AbstractResistRateModel> SharedAbstractResistRateModel;
    typedef std::shared_ptr<const AbstractResistRateModel> ConstSharedAbstractResistRateModel;
    typedef std::shared_ptr<ResistRateModelExpression> SharedResistRateModelExpression;
    typedef std::shared_ptr<ResistRateModelSheet> SharedResistRateModelSheet;

    typedef std::shared_ptr<AbstractSourceShapeModel> SharedAbstractSourceShapeModel;
    typedef std::shared_ptr<const AbstractSourceShapeModel> ConstSharedAbstractSourceShapeModel;
    typedef std::shared_ptr<SourceShapeModelPlugin> SharedSourceShapePlugin;
    typedef std::shared_ptr<SourceShapeModelSheet> SharedSourceShapeSheet;

    typedef std::shared_ptr<AbstractPupilFilterModel> SharedAbstractPupilFilterModel;
    typedef std::shared_ptr<const AbstractPupilFilterModel> ConstSharedAbstractPupilFilterModel;
    typedef std::shared_ptr<PupilFilterModelPlugin> SharedPupilFilterPlugin;
    typedef std::shared_ptr<PupilFilterModelSheet> SharedPupilFilterSheet;


    class SourceShape {
    private:
        // Direction cosine limit in any direction for the source shape
        static constexpr double _clim = 1.0;

        // Simulation's model of the source shape either function or data grid
        SharedAbstractSourceShapeModel _model;

        // Simulation's step by x and y axis
        double _stepx;
        double _stepy;

        std::shared_ptr<arma::mat> _values;

        std::shared_ptr<arma::s32_vec> _kx;
        std::shared_ptr<arma::s32_vec> _ky;

        std::shared_ptr<arma::vec> _cx;
        std::shared_ptr<arma::vec> _cy;

        // Non-zeros item's indexes
        std::shared_ptr<arma::umat> _non_zeros;

        // Non-zeros limits of the source shape
        double _sx_min;
        double _sx_max;
        double _sy_min;
        double _sy_max;

        static void _init_vectors(std::shared_ptr<arma::s32_vec> &k, std::shared_ptr<arma::vec> &dcos, double step);
        static std::shared_ptr<arma::mat> _init_values(
                const arma::vec &cx, const arma::vec &cy, SharedAbstractSourceShapeModel model);
                
        static std::shared_ptr<arma::umat> _get_non_zeros_indexes(const arma::mat &values);

        static void _get_limits(double &sx_min, double &sx_max, double &sy_min, double &sy_max,
                std::shared_ptr<arma::umat> non_zeros, std::shared_ptr<arma::vec> cx, std::shared_ptr<arma::vec> cy);
    public:
        SourceShape(SharedAbstractSourceShapeModel model, double stepx, double stepy);
        
        std::shared_ptr<arma::mat> values(void) const;
        
        double value(uint32_t r, uint32_t c) const;
        
        double cx(uint32_t i) const;
        double cy(uint32_t i) const;
        
        std::shared_ptr<arma::vec> cx(void) const;
        std::shared_ptr<arma::vec> cy(void) const;
        
        std::shared_ptr<arma::umat> non_zeros(void) const;
        
        double sx_min(void) const;
        double sx_max(void) const;
        double sy_min(void) const;
        double sy_max(void) const;
        
        bool operator==(const SourceShape& other) const;
    };


    typedef std::shared_ptr<SourceShape> SharedSourceShape;
    typedef std::shared_ptr<const SourceShape> ConstSharedSourceShape;


    class ImagingTool {
    private:
        SharedSourceShape _source_shape;
        SharedAbstractPupilFilterModel _pupil_filter_model;
        double _reduction_ratio;
        double _squared_reduction_ratio;
        double _flare;
        double _immersion;
    public:
        const double wavelength;
        const double numeric_aperture;

        ImagingTool(SharedSourceShape source_shape, SharedAbstractPupilFilterModel pupil_filter_model, 
                    double wavelength, double numeric_aperture, double reduction_ratio, double flare, double immersion);
        SharedSourceShape source_shape(void) const;
        arma::cx_double filter(double cx, double cy) const;
        double reduction(double cx, double cy, arma::cx_double environment_refraction=physc::air_nk) const;
        void flare(SharedResistVolume intensity) const;
        bool operator==(const ImagingTool& other) const;
    };


    typedef std::shared_ptr<ImagingTool> SharedImagingTool;
    typedef std::shared_ptr<const ImagingTool> ConstSharedImagingTool;


    class Exposure {
    public:
        const double focus;
        const double nominal_dose;
        const double correctable;

        Exposure(double focus, double nominal_dose, double correctable);
        arma::cx_double defocus(double cx, double cy, double wvl) const;
        double dose(void) const;
        bool operator==(const Exposure& other) const;
    };


    typedef std::shared_ptr<Exposure> SharedExposure;
    typedef std::shared_ptr<const Exposure> ConstSharedExposure;


    inline bool within_circle(double dx, double dy, double r) {
        double adx = std::abs(dx);
        double ady = std::abs(dy);
        if (adx + ady <= r) {
            return true;
        } else if (adx > r || ady > r) {
            return false;
        } else if (adx*adx + ady*ady <= r*r) {
            return true;
        } else {
            return false;
        }
    }


    inline bool within_circle(double x, double y, double cx, double cy, double r) {
        return within_circle(x - cx, y - cy, r);
    }


    class Diffraction {
    private:
        // Diffraction orders values
        std::shared_ptr<arma::cx_mat> _values;

        // Diffraction orders spatial frequencies arrays
        std::shared_ptr<arma::vec> _frqx;
        std::shared_ptr<arma::vec> _frqy;

        // Diffraction orders indexes
        std::shared_ptr<arma::s32_vec> _kx;
        std::shared_ptr<arma::s32_vec> _ky;

        // Direction cosines matrix and vectors
        std::shared_ptr<arma::mat> _cxy;
        std::shared_ptr<arma::vec> _cx;
        std::shared_ptr<arma::vec> _cy;

        inline static void _init_vectors(arma::s32_vec& k, arma::vec& frq, arma::vec& dcos,
                double pitch, double wavelength, std::pair<int32_t, int32_t> limits) {
            if (pitch == 0.0) {
                k(0) = 0;
                frq(0) = 0.0;
                dcos(0) = 0.0;
            } else {
                int32_t k_min = limits.first;
                // int32_t k_max = limits.second;
                // int32_t median = static_cast<int32_t>(round(static_cast<double>(k_max - k_min)/2.0));
                // VLOG(4) << "k_min = " << k_min << " k_max = " << k_max << " median = " << median;
                for (uint32_t i = 0; i < k.n_elem; i++) {
                    k(i) = k_min + i;
                    frq(i) = k(i) / pitch;
                    dcos(i) = frq(i) * wavelength;
                }
            }
        }

        inline static void _init_cosines(arma::mat& cxy, arma::vec& cx, arma::vec& cy) {
            for (uint32_t c = 0; c < cx.n_elem; c++) {
                for (uint32_t r = 0; r < cy.n_elem; r++) {
                    cxy(r, c) = sqrt(cx(c)*cx(c) + cy(r)*cy(r));
                }
            }
        }

        // Calculate total size of the diffraction array taking account source shape tilt
        // median - center point of the diffraction pattern belong axis
        // na - numeric aperture
        // wvl - wavelength
        // pitch - mask pitch for specified direction
        // cs_min/cx_max - minimum/maximum value of direction cosine in source shape
        //                 coordinate system where intensity is not zero
        inline static std::pair<int32_t, int32_t> _calc_size(
                double na, double wvl, double pitch, double cs_min, double cs_max) {
            if (cs_min > cs_max) {
                std::ostringstream error_msg;
                error_msg << "Maximum direction cosine of source shape must be greater than minimum value: "
                        << "Max = " << cs_max << " Min = " << cs_min;
                throw std::invalid_argument(error_msg.str());
            }
            int32_t k_min = static_cast<int32_t>(-floor(na*(1.0-cs_min)/wvl*pitch));
            int32_t k_max = static_cast<int32_t>(floor(na*(1.0+cs_max)/wvl*pitch));
            return std::pair<int32_t, int32_t>(k_min, k_max);
        }

        template <typename T>
        inline static std::shared_ptr<T> _select_axis(uint32_t axis, std::shared_ptr<T> x, std::shared_ptr<T> y) {
            if (axis == DIM_1D_X) {
                return x;
            } else if (axis == DIM_1D_Y) {
                return y;
            } else {
                throw std::runtime_error("Can't get using axis from non-1D storage");
            }
        }

        void _add_1d_region(SharedAbstractMaskGeometry region, arma::cx_double factor);
        static arma::cx_double _calc_2d_region(SharedAbstractMaskGeometry region,
                int32_t kx, int32_t ky, double frqx, double frqy);
        void _add_2d_region(SharedAbstractMaskGeometry region, arma::cx_double factor);

    public:
        // Corresponding source shape data
        ConstSharedSourceShape source_shape;

        // Corresponding mask pitch (it's hard linked with spatial frequencies step = 1/pitch)
        const Sizes pitch;
        const Box boundary;

        // Required to pass diffraction points over the objective lens at the corners
        const double numeric_aperture;
        const double wavelength;


        Diffraction(SharedMask mask, SharedImagingTool imaging_tool);

        // Return direction cosines for given axis
        std::shared_ptr<arma::vec> c(uint32_t axis) const;
        // Return diffraction terms order number for given axis
        std::shared_ptr<arma::s32_vec> k(uint32_t axis) const;
        // Return spatial frequencies for given axis
        std::shared_ptr<arma::vec> frq(uint32_t axis) const;
        // Return plane waves of diffraction pattern values
        std::shared_ptr<arma::cx_mat> values(void) const;
        arma::cx_double value(uint32_t r, uint32_t c) const;
        
        // Return absolute value of direction cosines
        std::shared_ptr<arma::mat> cxy(void) const;
        // Return direction cosine belong to x-axis
        std::shared_ptr<arma::vec> cx(void) const;
        double cx(uint32_t i) const;
        
        // Return direction cosine belong to y-axis
        std::shared_ptr<arma::vec> cy(void) const;
        double cy(uint32_t i) const;

        // Return spatial frequencies belong to x-axis
        std::shared_ptr<arma::vec> frqx(void) const;
        // Return spatial frequencies belong to y-axis
        std::shared_ptr<arma::vec> frqy(void) const;
        // Return diffraction terms order numbers belong x-axis
        std::shared_ptr<arma::s32_vec> kx(void) const;
        int32_t kx(uint32_t i) const;

        // Return diffraction terms order numbers belong y-axis
        std::shared_ptr<arma::s32_vec> ky(void) const;
        int32_t ky(uint32_t i) const;

        void add_region(SharedAbstractMaskGeometry region, arma::cx_double factor);
    };


    typedef std::shared_ptr<Diffraction> SharedDiffraction;
    typedef std::shared_ptr<const Diffraction> ConstSharedDiffraction;


    typedef enum {
        ENVIRONMENT_LAYER = 0,
        RESIST_LAYER = 1,
        MATERIAL_LAYER = 2,
        SUBSTRATE_LAYER = 3
    } layer_type_t;


    class AbstractWaferLayer {
    public:
        const layer_type_t type;
        const double thickness;

        AbstractWaferLayer(layer_type_t layer_type, double thickness) : type(layer_type), thickness(thickness) { }

        virtual ~AbstractWaferLayer(void) { };
        // 0 < m < 1 - for resist layer current PAC value, for others layer should be ignored
        virtual arma::cx_double refraction(double wavelength, double m=1.0) const = 0;

        bool is_environment(void) const;
        bool is_resist(void) const;
        bool is_material(void) const;
        bool is_substrate(void) const;
        
        arma::cx_double effective_refraction(arma::cx_double incident_angle, double wavelength) const;

        // WARNING: valid only for zero order
        arma::cx_double internal_transmit(double wavelength, double power=1.0) const;
        
        // Can be used for others d.ords
        arma::cx_double internal_transmit(arma::cx_double incident_angle, double dz, double wavelength) const;

        std::string str(void) const;

        virtual bool operator==(const AbstractWaferLayer& other) const = 0;
    };


    class StandardWaferLayer : public AbstractWaferLayer {
    private:
        interp::LinearInterpolation1d _refraction_real;
        interp::LinearInterpolation1d _refraction_imag;
    public:
        StandardWaferLayer(layer_type_t layer_type, double thickness, const arma::vec& wavelength,
                const arma::vec& refraction_real, const arma::vec& refraction_imag);
                    
        StandardWaferLayer(layer_type_t layer_type, const arma::vec& wavelength,
                const arma::vec& refraction_real, const arma::vec& refraction_imag) :
                StandardWaferLayer(layer_type, NAN, wavelength, refraction_real, refraction_imag) { };

        arma::cx_double refraction(double wavelength, double m=1.0) const;
        bool operator==(const AbstractWaferLayer& other) const;
    };


    class ConstantWaferLayer : public AbstractWaferLayer {
    private:
        arma::cx_double _refraction;
    public:
        ConstantWaferLayer(layer_type_t layer_type, double thickness, double real, double imag);
        
        ConstantWaferLayer(layer_type_t layer_type, double real, double imag) :
            ConstantWaferLayer(layer_type, NAN, real, imag) { }

        arma::cx_double refraction(double wavelength=0.0, double m=1.0) const;
        bool operator==(const AbstractWaferLayer& other) const;
    };


    class ExposureResistModel {
    public:
        const double wavelength;
        // Dill model constants
        const double a;
        const double b;
        const double c;
        // Real refractive index
        const double n;

        ExposureResistModel(double wavelength, double a, double b, double c, double n) :
            wavelength(wavelength), a(a), b(b), c(c), n(n) { }

        arma::cx_double refraction(double m=1.0) const;
        bool operator==(const ExposureResistModel& other) const;
    };


    typedef std::shared_ptr<ExposureResistModel> SharedExposureResistModel;
    typedef std::shared_ptr<const ExposureResistModel> ConstSharedExposureResistModel;


    class PostExposureBake {
    public:
        const double time;
        const double temp;
        PostExposureBake(double time, double temp) : time(time), temp(temp) { }
    };


    typedef std::shared_ptr<PostExposureBake> SharedPostExposureBake;
    typedef std::shared_ptr<const PostExposureBake> ConstSharedPostExposureBake;


    class PebResistModel {
    public:
        const double ea;
        const double ln_ar;

        PebResistModel(double ea, double ln_ar) : ea(ea), ln_ar(ln_ar) { }

        double diffusivity(double temp) const;
        double diffusion_length(double temp, double time) const;
        arma::vec kernel(SharedPostExposureBake peb, double step) const;
        bool operator==(const PebResistModel& other) const;
    };


    typedef std::shared_ptr<PebResistModel> SharedPebResistModel;
    typedef std::shared_ptr<const PebResistModel> ConstSharedPebResistModel;


    class ResistWaferLayer : public AbstractWaferLayer {
    public:
        const ConstSharedExposureResistModel exposure;
        const ConstSharedPebResistModel peb;
        const ConstSharedAbstractResistRateModel rate;

        ResistWaferLayer(double thickness, SharedExposureResistModel exposure_model,
                SharedPebResistModel peb_model, SharedAbstractResistRateModel rate_model) :
                AbstractWaferLayer(RESIST_LAYER, thickness),
                exposure(exposure_model), peb(peb_model), rate(rate_model) { }

        arma::cx_double refraction(double wavelength, double m=1.0) const;
        bool operator==(const AbstractWaferLayer& other) const;
    };


    typedef std::shared_ptr<AbstractWaferLayer> SharedAbstractWaferLayer;
    typedef std::shared_ptr<StandardWaferLayer> SharedStandardWaferLayer;
    typedef std::shared_ptr<ResistWaferLayer> SharedResistWaferLayer;
    typedef std::shared_ptr<ConstantWaferLayer> SharedConstantWaferLayer;
    typedef std::vector<SharedAbstractWaferLayer> ArrayOfSharedAbstractWaferLayers;


    class WaferStack {
    private:
        ArrayOfSharedAbstractWaferLayers _layers;
        SharedAbstractWaferLayer _resist;
        SharedAbstractWaferLayer _substrate;
        SharedAbstractWaferLayer _environment;

        std::map<std::pair<double, double>, std::shared_ptr<arma::cx_vec>> _cached_top_reflections;
        std::map<std::pair<double, double>, std::shared_ptr<arma::cx_vec>> _cached_bottom_reflections;
        double _cached_wavelength;

        static inline arma::cx_double _angle(arma::cx_double incident_angle,
                arma::cx_double top_refraction, arma::cx_double bottom_refraction) {
            return std::asin(top_refraction / bottom_refraction * std::sin(incident_angle));
        }

        static inline arma::cx_double _reflection(arma::cx_double top_refraction, arma::cx_double bottom_refraction) {
            return (top_refraction - bottom_refraction) / (top_refraction + bottom_refraction);
        }

        static inline arma::cx_double _transmittance(arma::cx_double top_refraction, arma::cx_double bottom_refraction) {
            return 2.0 * top_refraction / (top_refraction + bottom_refraction);
        }

        // Calculate refractive indexes between layers (for all layers in the stack)
        arma::cx_vec _calc_refractive_indexes(double cxy, double wavelength);

        // Calculate effective reflection for all stack from top to bottom
        // (reflection with taking account of all top layers)
        std::shared_ptr<arma::cx_vec> _calc_effective_top_reflections(double cxy, double wavelength);

        // Return cached value or calculate
        std::shared_ptr<arma::cx_vec> effective_top_reflection(double cx, double cy, double wavelength);

        // Calculate effective reflection for all stack from bottom to top
        // (reflection with taking account of all bottom layers)
        std::shared_ptr<arma::cx_vec> _calc_effective_bottom_reflections(double cxy, double wavelength);

        // Return cached value or calculate
        std::shared_ptr<arma::cx_vec> effective_bottom_reflection(double cx, double cy, double wavelength);

    public:
        WaferStack(void);
        WaferStack(ArrayOfSharedAbstractWaferLayers layers);

        void push(SharedAbstractWaferLayer layer);

        bool is_ok(void);

        SharedAbstractWaferLayer operator[](int32_t i) const;
        SharedAbstractWaferLayer environment(void) const;
        SharedAbstractWaferLayer resist(void) const;
        SharedAbstractWaferLayer substrate(void) const;
        uint32_t index_of(SharedAbstractWaferLayer layer) const;
        std::complex<double> reflectivity(uint32_t indx, double wavelength);

        // This routine only suitable for the stack where resist is the SECOND layer!
        std::complex<double> standing_waves(double cx, double cy, double dz, double wavelength);

        bool operator==(const WaferStack& other) const;
    };


    typedef std::shared_ptr<WaferStack> SharedWaferStack;
    typedef std::shared_ptr<const WaferStack> ConstSharedWaferStack;


    class Development {
    public:
        const double time;
        Development(double time) : time(time) { }
    };


    typedef std::shared_ptr<Development> SharedDevelopment;
    typedef std::shared_ptr<const Development> ConstSharedDevelopment;


    class OpticalTransferFunction {
    private:
        ConstSharedImagingTool _imaging_tool;
        ConstSharedExposure _exposure;

        // This object is not constant because when calculating it change it internal precalculated values
        SharedWaferStack _wafer_stack;

        const double _wavelength;
        const double _numeric_aperture;

    //	std::map<std::pair<double, double>, arma::cx_double> _cached_data;
    public:
        OpticalTransferFunction(SharedImagingTool imaging_tool, 
            SharedExposure exposure=nullptr, SharedWaferStack wafer_stack=nullptr) :
            _imaging_tool(imaging_tool), _exposure(exposure), _wafer_stack(wafer_stack),
            _wavelength(imaging_tool->wavelength), _numeric_aperture(imaging_tool->numeric_aperture) { }

        // Calculate optical transfer function value for given direction cosines values cx, cy
        // and given offset from the resist top dz.
        arma::cx_double calc(double cx, double cy, double dz=0.0);

        ConstSharedImagingTool imaging_tool(void) const;
        ConstSharedExposure exposure(void) const;
        ConstSharedWaferStack wafer_stack(void) const;
    };


    typedef std::shared_ptr<OpticalTransferFunction> SharedOpticalTransferFunction;


    // WARNING: !!! REQUIRED OTHERWISE SWIG NOT INCLUDE ARMANPY.I !!!
    class  Example
    {
    private:
        arma::imat m;
    public:
        Example(int rows, int cols) {
            m = arma::randi(rows, cols, arma::distr_param(0, 100));
        };

        arma::imat get(void) {
            return m;
        };

        // THIS METHOD MUST EXISTS
        void set(const arma::imat& m) {
            this->m = m;
        };

        void set(int v, int r, int c) {
            this->m(r, c) = v;
        }

        void rnd(unsigned s) {
            this->m.randn(s,s);
        };

        std::shared_ptr<arma::imat> get_sptr(void) {
            std::shared_ptr<arma::imat> p(new arma::imat(m));
            return p;
        };

        void modify(arma::imat& A, unsigned rows, unsigned cols) {
            A.resize( rows, cols );
            A.randn( rows, cols );
            for( unsigned r = 0; r < rows; r++) {
                for( unsigned c = 0; c < cols; c++) {
                    A(r, c) = 10.0*r+c;
                }
            }
        };

        arma::imat reshape(int rows, int cols) const {
            return arma::reshape(this->m, rows, cols);
        }

        arma::imat rot90(void) const {
            return misc::rot90(this->m);
        }
    };

}  // namespace oplc

#endif /* OPTOLITHIUMC_HPP_ */
