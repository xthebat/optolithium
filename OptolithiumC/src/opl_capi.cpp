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

#include "opl_capi.h"

namespace oplc {

    // ========================================= AbstractResistSimulations ========================================== //

    std::shared_ptr<arma::vec> AbstractResistSimulations::x(void) const {
        return this->_x;
    }

    std::shared_ptr<arma::vec> AbstractResistSimulations::y(void) const {
        return this->_y;
    }

    std::shared_ptr<arma::vec> AbstractResistSimulations::z(void) const {
        return this->_z;
    }

    double AbstractResistSimulations::x(uint32_t k) const {
        return (*this->_x)(k);
    }

    double AbstractResistSimulations::y(uint32_t k) const {
        return (*this->_y)(k);
    }

    double AbstractResistSimulations::z(uint32_t k) const {
        return (*this->_z)(k);
    }

    bool AbstractResistSimulations::has_x(void) const {
        return this->_x->n_elem > 1;
    }

    bool AbstractResistSimulations::has_y(void) const {
        return this->_y->n_elem > 1;
    }

    bool AbstractResistSimulations::has_z(void) const {
        return this->_z->n_elem > 1;
    }

    double AbstractResistSimulations::stepx(void) const {
        return this->_stepx;
    }

    double AbstractResistSimulations::stepy(void) const {
        return this->_stepy;
    }

    double AbstractResistSimulations::stepz(void) const {
        return this->_stepz;
    }

    resist_volume_type_t AbstractResistSimulations::axes(void) const {
        uint8_t has_z = static_cast<uint8_t>(this->has_z()) << 2;
        uint8_t has_y = static_cast<uint8_t>(this->has_y()) << 1;
        uint8_t has_x = static_cast<uint8_t>(this->has_x());
        return static_cast<resist_volume_type_t>(has_z | has_y | has_x);
    }


    // ================================================ ResistVolume ================================================ //


    // Initialization for 2D/3D cases (e.g. Image in Resist, Latent Image, PAC, Development Rates)
    ResistVolume::ResistVolume(
        const RectangleGeometry& boundary, double thickness, double desired_stepxy, double desired_stepz) :
        boundary(boundary), thickness(thickness), desired_stepxy(desired_stepxy), desired_stepz(desired_stepz) {

        Sizes sizes = this->boundary.sizes();

        this->_stepx = ResistVolume::_calc_lateral_step(sizes.x, desired_stepxy);
        this->_stepy = ResistVolume::_calc_lateral_step(sizes.y, desired_stepxy);
        this->_stepz = ResistVolume::_calc_normal_step(thickness, desired_stepz);

        // VLOG(4) << "Step X = " << this->_stepx << " Step Y = " << this->_stepy << " Step Z = " << this->_stepz;

        uint32_t row = ResistVolume::_get_count(sizes.y, this->_stepy, 1);
        uint32_t col = ResistVolume::_get_count(sizes.x, this->_stepx, 1);
        uint32_t slices =  ResistVolume::_get_count(thickness, this->_stepz);

        if (slices != 1) {
            slices++;
        }

        // VLOG(4) << "row = " << row << " col = " << col << " slices = " << slices;

        this->_values = std::make_shared<arma::cube>(row, col, slices);
        this->_x = std::make_shared<arma::vec>(col);
        this->_y = std::make_shared<arma::vec>(row);
        this->_z = std::make_shared<arma::vec>(slices);

        const Point2d& left_bottom = this->boundary.left_bottom();

        ResistVolume::_init_vector(*this->_x, left_bottom.x, this->_stepx);
        ResistVolume::_init_vector(*this->_y, left_bottom.y, this->_stepy);
        ResistVolume::_init_vector(*this->_z, thickness, -this->_stepz);
    }

    // Initialization for 1D/2D cases (e.g. for AerialImage)
    ResistVolume::ResistVolume(const RectangleGeometry& boundary, double desired_step) : 
        ResistVolume(boundary, 0.0, desired_step, 0.0) { }

    ResistVolume::ResistVolume(const ResistVolume& other, bool copydata) :
        boundary(other.boundary), thickness(other.thickness),
        desired_stepxy(other.desired_stepxy), desired_stepz(other.desired_stepz) {
        this->_stepx = other._stepx;
        this->_stepy = other._stepy;
        this->_stepz = other._stepz;
        this->_x = std::make_shared<arma::vec>(*other._x);
        this->_y = std::make_shared<arma::vec>(*other._y);
        this->_z = std::make_shared<arma::vec>(*other._z);
        if (copydata) {
            this->_values = std::make_shared<arma::cube>(
                    other._values->n_rows, other._values->n_cols, other._values->n_slices);
        } else {
            this->_values = std::make_shared<arma::cube>(*other._values);
        }
    }

    std::shared_ptr<arma::cube> ResistVolume::values(void) const {
        return this->_values;
    }

    double& ResistVolume::value(uint32_t u, uint32_t v, uint32_t k) const {
        return (*this->_values)(u, v, k);
    }

    resist_simulations_t ResistVolume::type(void) const {
        return RESIST_VOLUME;
    }


    // ================================================ ResistProfile =============================================== //


    ResistProfile::ResistProfile(SharedResistVolume volume, double level) {
        this->_stepx = volume->stepx();
        this->_stepy = volume->stepy();
        this->_stepz = volume->stepz();
        this->_x = std::make_shared<arma::vec>(*volume->x());
        this->_y = std::make_shared<arma::vec>(*volume->y());
        this->_z = std::make_shared<arma::vec>(*volume->z());

        if (this->has_x() && this->has_y()) {
            throw std::invalid_argument("Can't create resist profile from 3D resist volume data");
        } else if (this->has_x()) {
            const arma::mat& values = volume->values()->tube(arma::span(0, 0), arma::span::all);
            this->_polygons = contours::contours(*this->_x, *this->_z, misc::rot90(values), level, true);
        } else if (this->has_y()) {
            const arma::mat& values = volume->values()->tube(arma::span::all, arma::span(0, 0));
            this->_polygons = contours::contours(*this->_y, *this->_z, misc::rot90(values), level, true);
        } else {
            throw std::invalid_argument("Can't create resist profile from empty resist volume data");
        }
    }

    ArrayOfSharedPolygons ResistProfile::polygons(void) const {
        return this->_polygons;
    }

    resist_simulations_t ResistProfile::type(void) const {
        return RESIST_PROFILE;
    }


    // ============================================== AbstractGeometry ============================================== //


    double AbstractMaskGeometry::transmittance(void) const {
        return this->_transmittance;
    }

    double AbstractMaskGeometry::phase(void) const {
        return this->_phase;
    }

    bool AbstractMaskGeometry::is_mask(void) const {
        return true;
    }

    // Effective transmittance of the region
    arma::cx_double AbstractMaskGeometry::etransmit(void) {
        return _etransmit(this->_transmittance, this->_phase);
    }

    bool AbstractMaskGeometry::operator==(const AbstractGeometry& other) const {
        if (!other.is_mask()) {
            return false;
        } else {
            const AbstractMaskGeometry* p = dynamic_cast<const AbstractMaskGeometry*>(&other);
            return this->_transmittance == p->_transmittance && this->_phase == p->_phase;
        }
    }


    // ==================================================== Mask ==================================================== //


    // Correct mask region according to diffraction calculation requirements
    SharedRegion Mask::_make_region(ConstSharedRegion region, const Point2d& center_offset) {
        auto result = std::make_shared<Region>(*region);
        result->set_bypass(CW);
        for (auto edge : *result) {
            edge->org -= center_offset;
            edge->dst -= center_offset;
        }
        return result;
    }

    Mask::Mask(const ArrayOfSharedRegions& regions, SharedBox boundary) {
        const Point2d center_offset = boundary->left_bottom() + (boundary->right_top() - boundary->left_bottom()) / 2.0;
        for (auto region : regions) {
            this->_regions.push_back(Mask::_make_region(region, center_offset));
        }
        auto lb = boundary->left_bottom() - center_offset;
        auto rt = boundary->right_top() - center_offset;
        this->_boundary = std::make_shared<Box>(lb, rt, boundary->transmittance(), boundary->phase());
        this->_sizes = this->_boundary->sizes();
    }

    Mask::Mask(const Mask& other) {
        for (auto region : other) {
            this->_regions.push_back(std::make_shared<Region>(*region));
        }
        this->_boundary = std::make_shared<Box>(*other._boundary);
        this->_sizes = this->_boundary->sizes();
    }

    SharedBox Mask::boundary(void) const {
        return this->_boundary;
    }

    Sizes Mask::pitch(void) const {
        return this->_sizes;
    }

    bool Mask::is_opaque(void) const {
        return this->_boundary->transmittance() == 0.0;
    }

    bool Mask::is_clear(void) const {
        return !this->is_opaque();
    }

    bool Mask::is_bad(void) const {
        return this->_sizes.x == 0.0 && this->_sizes.y == 0.0;
    }

    bool Mask::is_1d(void) const {
        return this->_sizes.x == 0.0 || this->_sizes.y == 0.0;
    }

    bool Mask::operator==(const Mask& other) const {
        return *this->_boundary == *other._boundary && misc::safe_vector_equal(this->_regions, other._regions);
    }


    SharedRegion Mask::at(uint32_t index) const
    {
        return this->_regions.at(index);
    }

    uint32_t Mask::length(void) const {
        return static_cast<uint32_t>(this->_regions.size());
    }


    // =========================================== SourceShapeModelPlugin =========================================== //


    SourceShapeModelPlugin::SourceShapeModelPlugin(source_shape_expr_t expression, std::vector<double> args) :
        AbstractSourceShapeModel(PLUGIN_MODEL_TYPE), _expression(expression), _args(args),
        _pargs(static_cast<const void*>(this->_args.data())) {
        VLOG(6) << "Plugin source shape model core object created";
    };

    double SourceShapeModelPlugin::calculate(double sx, double sy) const {
        return this->_expression(sx, sy, this->_pargs);
    }

    bool SourceShapeModelPlugin::operator==(const AbstractSourceShapeModel& other) const {
        if (this->type != other.type) {
            return false;
        } else {
            const SourceShapeModelPlugin *p = dynamic_cast<const SourceShapeModelPlugin*>(&other);
            return this->_args == p->_args && this->_expression == p->_expression;
        }
    }


    // ============================================ SourceShapeModelSheet =========================================== //


    //	armanpy not support pass arrays by shared_ptr
    SourceShapeModelSheet::SourceShapeModelSheet(const arma::vec& sx, const arma::vec& sy, const arma::mat& intensity) :
        AbstractSourceShapeModel(SHEET_MODEL_TYPE), _interp(interp::LinearInterpolation2d(
                std::make_shared<arma::vec>(sx), std::make_shared<arma::vec>(sy),
                std::make_shared<arma::mat>(intensity))) {
        VLOG(6) << "Sheet source shape model core object created";
    };

    double SourceShapeModelSheet::calculate(double sx, double sy) const {
        return this->_interp.interpolate(sx, sy);
    }

    bool SourceShapeModelSheet::operator==(const AbstractSourceShapeModel& other) const {
        if (this->type != other.type) {
            return false;
        } else {
            const SourceShapeModelSheet *p = dynamic_cast<const SourceShapeModelSheet*>(&other);
            return this->_interp == p->_interp;
        }
    }


    // ========================================== ResistRateModelExpression ========================================= //


    ResistRateModelExpression::ResistRateModelExpression(rate_model_expr_t expression, std::vector<double> args) :
        AbstractResistRateModel(PLUGIN_MODEL_TYPE), _expression(expression), _args(args),
        _pargs(static_cast<const void*>(this->_args.data())) {
        VLOG(6) << "Plugin resist development rate model core object created";
    };

    double ResistRateModelExpression::calculate(double pac, double depth) const {
        return this->_expression(pac, depth, this->_pargs);
    }

    bool ResistRateModelExpression::operator==(const AbstractResistRateModel& other) const {
        if (this->type != other.type) {
            return false;
        } else {
            const ResistRateModelExpression *p = dynamic_cast<const ResistRateModelExpression*>(&other);
            return this->_args == p->_args && this->_expression == p->_expression;
        }
    }


    // ========================================== ResistRateModelDepthSheet ========================================= //


    //	armanpy not support pass arrays by shared_ptr
    ResistRateModelDepthSheet::ResistRateModelDepthSheet(
        const arma::vec& pac, const arma::vec& depth, const arma::mat& rate) :
        AbstractResistRateModel(SHEET_MODEL_TYPE), _interp(interp::LinearInterpolation2d(
                std::make_shared<arma::vec>(pac), std::make_shared<arma::vec>(depth),
                std::make_shared<arma::mat>(rate))) {
        VLOG(6) << "Sheet with depth dependence resist development rate model core object created";
    }

    double ResistRateModelDepthSheet::calculate(double pac, double depth) const {
        return this->_interp.interpolate(pac, depth);
    }

    bool ResistRateModelDepthSheet::operator==(const AbstractResistRateModel& other) const {
        if (this->type != other.type) {
            return false;
        } else {
            const ResistRateModelDepthSheet *p = dynamic_cast<const ResistRateModelDepthSheet*>(&other);
            return this->_interp == p->_interp;
        }
    }


    // ============================================ ResistRateModelSheet =========================================== //


    //	armanpy not support pass arrays by shared_ptr
    ResistRateModelSheet::ResistRateModelSheet(const arma::vec& pac, const arma::vec& rate) :
        AbstractResistRateModel(SHEET_MODEL_TYPE), _interp(interp::LinearInterpolation1d(
                std::make_shared<arma::vec>(pac), std::make_shared<arma::vec>(rate))) {
        VLOG(6) << "Sheet resist development rate model core object created";
    }

    double ResistRateModelSheet::calculate(double pac, double depth) const {
        return this->_interp.interpolate(pac);
    }

    bool ResistRateModelSheet::operator==(const AbstractResistRateModel& other) const {
        if (this->type != other.type) {
            return false;
        } else {
            const ResistRateModelSheet *p = dynamic_cast<const ResistRateModelSheet*>(&other);
            return this->_interp == p->_interp;
        }
    }


    // ============================================ PupilFilterModelPlugin ========================================== //


    PupilFilterModelPlugin::PupilFilterModelPlugin(pupil_filter_expr_t expression, std::vector<double> args) :
        AbstractPupilFilterModel(PLUGIN_MODEL_TYPE), _expression(expression), _args(args),
        _pargs(static_cast<const void*>(this->_args.data())) {
        VLOG(6) << "Plugin pupil filter model core object created";
    };

    arma::cx_double PupilFilterModelPlugin::calculate(double sx, double sy) const {
        return static_cast<arma::cx_double>(this->_expression(sx, sy, this->_pargs));
    }

    bool PupilFilterModelPlugin::operator==(const AbstractPupilFilterModel& other) const {
        if (this->type != other.type) {
            return false;
        } else {
            const PupilFilterModelPlugin *p = dynamic_cast<const PupilFilterModelPlugin*>(&other);
            return this->_args == p->_args && this->_expression == p->_expression;
        }
    }


    // ============================================= PupilFilterModelSheet ========================================== //


    //	armanpy not support pass arrays by shared_ptr
    PupilFilterModelSheet::PupilFilterModelSheet(const arma::vec& sx, const arma::vec& sy, const arma::cx_mat& coef) :
        AbstractPupilFilterModel(SHEET_MODEL_TYPE) {
        auto reals = std::make_shared<arma::mat>(coef.n_rows, coef.n_cols);
        auto imags = std::make_shared<arma::mat>(coef.n_rows, coef.n_cols);
        for (uint32_t r = 0; r < coef.n_rows; r++) {
            for (uint32_t c = 0; c < coef.n_cols; c++) {
                (*reals)(r, c) = coef(r, c).real();
                (*imags)(r, c) = coef(r, c).imag();
            }
        }

        std::shared_ptr<arma::vec> p_sx = std::make_shared<arma::vec>(sx);
        std::shared_ptr<arma::vec> p_sy = std::make_shared<arma::vec>(sy);

        this->_interp_real = interp::LinearInterpolation2d(p_sx, p_sy, reals);
        this->_interp_imag = interp::LinearInterpolation2d(p_sx, p_sy, imags);

        VLOG(6) << "Sheet pupil filter model core object created";
    }

    arma::cx_double PupilFilterModelSheet::calculate(double sx, double sy) const {
        double real = this->_interp_real.interpolate(sx, sy);
        double imag = this->_interp_imag.interpolate(sx, sy);
        return arma::cx_double(real, imag);
    }

    bool PupilFilterModelSheet::operator==(const AbstractPupilFilterModel& other) const {
        if (this->type != other.type) {
            return false;
        } else {
            const PupilFilterModelSheet *p = dynamic_cast<const PupilFilterModelSheet*>(&other);
            return this->_interp_real == p->_interp_real && this->_interp_imag == this->_interp_imag;
        }
    }


    // ============================================= PupilFilterModelEmpty ========================================== //


    PupilFilterModelEmpty::PupilFilterModelEmpty(void) : AbstractPupilFilterModel(EMPTY_MODEL_TYPE) {
        VLOG(6) << "Empty pupil filter model core object created";
    }

    arma::cx_double PupilFilterModelEmpty::calculate(double sx, double sy) const {
        return arma::cx_double(1.0, 0.0);
    }

    bool PupilFilterModelEmpty::operator==(const AbstractPupilFilterModel& other) const {
        return this->type == other.type;
    }


    // ================================================= SourceShape ================================================ //


    void SourceShape::_init_vectors(std::shared_ptr<arma::s32_vec> &k, std::shared_ptr<arma::vec> &dcos, double step) {
        // Cut value above 1.0 because max direction cosine in source shape grid must be lower 1.0
        double count = static_cast<uint32_t>(2*SourceShape::_clim/step+1);

        k = std::make_shared<arma::s32_vec>(count);
        dcos = std::make_shared<arma::vec>(count);

        uint32_t median = static_cast<uint32_t>(floor(static_cast<double>(count)/2.0));
        for (uint32_t i = 0; i < count; i++) {
            (*k)(i) = i - median;
            (*dcos)(i) = (*k)(i) * step;
        }
    }

    std::shared_ptr<arma::mat> SourceShape::_init_values(const arma::vec &cx, const arma::vec &cy,
            SharedAbstractSourceShapeModel model) {
        std::shared_ptr<arma::mat> result = std::make_shared<arma::mat>(cy.n_elem, cx.n_elem);
        for (uint32_t c = 0; c < cx.n_elem; c++) {
            for (uint32_t r = 0; r < cy.n_elem; r++) {
                (*result)(r, c) = model->calculate(cx(c), cy(r));
            }
        }
        return result;
    }

    std::shared_ptr<arma::umat> SourceShape::_get_non_zeros_indexes(const arma::mat &values) {
        arma::uvec indexes = arma::find(values != 0.0);
        auto result = std::make_shared<arma::umat>(indexes.n_elem, 2);
        for (int32_t k = 0; k < static_cast<int32_t>(indexes.n_elem); k++) {
            (*result)(k, 0) = indexes(k) % values.n_rows;  // row index
            (*result)(k, 1) = indexes(k) / values.n_rows;  // column index
        }
        return result;
    }

    void SourceShape::_get_limits(double &sx_min, double &sx_max, double &sy_min, double &sy_max, 
            std::shared_ptr<arma::umat> non_zeros, std::shared_ptr<arma::vec> cx, std::shared_ptr<arma::vec> cy) {

        auto rows_indx = non_zeros->col(0);
        uint32_t r_min = arma::min(rows_indx);
        uint32_t r_max = arma::max(rows_indx);

        auto cols_indx = non_zeros->col(1);
        uint32_t c_min = arma::min(cols_indx);
        uint32_t c_max = arma::max(cols_indx);

        sx_min = (*cx)(c_min);
        sx_max = (*cx)(c_max);

        sy_min = (*cy)(r_min);
        sy_max = (*cy)(r_max);
    }

    SourceShape::SourceShape(SharedAbstractSourceShapeModel model, double stepx, double stepy) {
        this->_model = model;
        this->_stepx = stepx;
        this->_stepy = stepy;

        SourceShape::_init_vectors(this->_kx, this->_cx, stepx);
        SourceShape::_init_vectors(this->_ky, this->_cy, stepy);

    //	VLOG(4) << "Calculate source shape values in simulation grid";
        this->_values = SourceShape::_init_values(*this->_cx, *this->_cy, this->_model);

    //	VLOG(4) << "Get indexes of the non-zeros items";
        this->_non_zeros = SourceShape::_get_non_zeros_indexes(*this->_values);

    //  VLOG(4) << "Get source shape direction cosine limits";
        this->_get_limits(this->_sx_min, this->_sx_max, this->_sy_min, this->_sy_max,
                this->_non_zeros, this->_cx, this->_cy);
    //	VLOG(4) << "SX = " << this->_sx_min << " " << this->_sx_max <<
    //			" SY = " << this->_sy_min << " " << this->_sy_max;
    }

    std::shared_ptr<arma::mat> SourceShape::values(void) const {
        return this->_values;
    }

    double SourceShape::value(uint32_t r, uint32_t c) const {
        return (*this->_values)(r, c);
    }

    std::shared_ptr<arma::vec> SourceShape::cx(void) const {
        return this->_cx;
    }

    double SourceShape::cx(uint32_t i) const {
        return (*this->_cx)(i);
    }

    std::shared_ptr<arma::vec> SourceShape::cy(void) const {
        return this->_cy;
    }

    double SourceShape::cy(uint32_t i) const {
        return (*this->_cy)(i);
    }

    std::shared_ptr<arma::umat> SourceShape::non_zeros(void) const {
        return this->_non_zeros;
    }

    double SourceShape::sx_min(void) const {
        return this->_sx_min;
    }

    double SourceShape::sx_max(void) const {
        return this->_sx_max;
    }

    double SourceShape::sy_min(void) const {
        return this->_sy_min;
    }

    double SourceShape::sy_max(void) const {
        return this->_sy_max;
    }

    bool SourceShape::operator==(const SourceShape& other) const {
        return *this->_model == *other._model && this->_stepx == other._stepx && this->_stepy == other._stepy;
    }


    // ================================================= ImagingTool ================================================ //


    ImagingTool::ImagingTool(SharedSourceShape source_shape, SharedAbstractPupilFilterModel pupil_filter_model,
            double wavelength, double numeric_aperture, double reduction_ratio, double flare, double immersion) :
        wavelength(wavelength), numeric_aperture(numeric_aperture) {
        this->_source_shape = source_shape;
        this->_pupil_filter_model = pupil_filter_model;
        this->_reduction_ratio = reduction_ratio;
        this->_squared_reduction_ratio = reduction_ratio * reduction_ratio;
        this->_flare = flare;
        this->_immersion = immersion;
    }

    SharedSourceShape ImagingTool::source_shape(void) const {
        return this->_source_shape;
    }

    arma::cx_double ImagingTool::filter(double cx, double cy) const {
        return this->_pupil_filter_model->calculate(cx, cy);
    }

    double ImagingTool::reduction(double cx, double cy, arma::cx_double environment_refraction) const {
        // TODO: Added immersion calculation
        double cxy2 = cx * cx + cy * cy;
        double n_env2 = std::abs(environment_refraction) * std::abs(environment_refraction);
    //	LOG(INFO) << "Environment refractive index = " << std::abs(environment_refraction);
        return std::pow((1 - cxy2/this->_squared_reduction_ratio) / (1 - cxy2/n_env2), 0.25);
    }

    void ImagingTool::flare(SharedResistVolume intensity) const {
        if (this->_flare != 0.0) {
            arma::cube& values = *intensity->values();
            for (arma::cube::iterator it = values.begin(); it != values.end(); it++) {
                *it = this->_flare + (1 - this->_flare) * (*it);
            }
        }
    }

    bool ImagingTool::operator==(const ImagingTool& other) const {
        return *this->_source_shape == *other._source_shape &&
                *this->_pupil_filter_model == *other._pupil_filter_model &&
                this->wavelength == other.wavelength &&
                this->numeric_aperture == other.numeric_aperture &&
                this->_reduction_ratio == other._reduction_ratio &&
                this->_flare == other._flare &&
                this->_immersion == other._immersion;
    }


    // ================================================== Exposure ================================================== //


    Exposure::Exposure(double focus, double nominal_dose, double correctable) :
        focus(focus), nominal_dose(nominal_dose), correctable(correctable) { }

    arma::cx_double Exposure::defocus(double cx, double cy, double wvl) const {
        if (this->focus != 0.0) {
            double cxy2 = cx * cx + cy * cy;
            double opd = this->focus*(1 - sqrt(1 - cxy2));
            return std::exp(2*M_PI*j*opd/wvl);
        } else {
            return arma::cx_double(1.0, 0.0);
        }
    }

    double Exposure::dose(void) const {
        return this->nominal_dose * this->correctable;
    }

    bool Exposure::operator==(const Exposure& other) const {
        return this->focus == other.focus &&
                this->nominal_dose == other.nominal_dose &&
                this->correctable == other.correctable;
    }


    // ================================================= Diffraction ================================================ //


    void Diffraction::_add_1d_region(SharedAbstractMaskGeometry region, arma::cx_double factor)
    {
        // Corrected during mask converting
        // region->set_bypass(CW);

        // In one-dimensional mask only one region exist
        SharedEdge2d r = region->front();

        // Simplifier access to required member fields
        uint32_t axis = region->axis();
        double dst = r->dst[axis];
        double org = r->org[axis];
        arma::cx_mat& values = *this->_values;
        arma::s32_vec& k = *this->k(axis);
        arma::vec& frq = *this->frq(axis);

        arma::cx_double value;
        for (uint32_t i = 0; i < k.n_elem; i++) {
            if (k(i) == 0) {
                value = (dst - org);
    //			VLOG(4) << "i = " << i << " k = " << i << "/" << k.n_elem << " v = " << value;
            } else {
                arma::cx_double w = 2*M_PI*j*frq(i);
                value = -(std::exp(-w*dst) - std::exp(-w*org)) / w;
    //			VLOG(4) << "i = " << i << " k = " << i << "/" << k.n_elem << " f = " << frq(i)
    //					<< " w = " << w << " e^w1 = " << exp(-w*dst) << " e^w2 = " << exp(-w*org)
    //					<< " v = " << value;
            }
            values(i) += factor*value;
        }
    }

    arma::cx_double Diffraction::_calc_2d_region(SharedAbstractMaskGeometry region, 
            int32_t kx, int32_t ky, double frqx, double frqy) {
        arma::cx_double result = 0.0;

        for (auto e : *region) {
            arma::cx_double value;
            const double dx = e->dx();

            if (dx == 0.0) {
                value = 0.0;
            } else {
                const double dy = e->dy();
                const double s = e->slope();
                const double b = e->dst.y - s*e->dst.x;

                if (kx == 0 && ky == 0) { // diffraction for zero order
                    value = e->area();
                } else if (kx == 0 && ky != 0) { // diffraction for orders if FX = 0
                    const arma::cx_double wy = 2*M_PI*j*frqy;
                    if (dy == 0) {
                        value = dx/wy*(1.0 - std::exp(-wy*b));
                    } else { //dX && dY != 0
                        value = dx/wy + (std::exp(-wy*b)/s/wy/wy)*(std::exp(-s*wy*e->dst.x) - std::exp(-s*wy*e->org.x));
                    }
                } else if (kx != 0 && ky == 0) { // diffraction for orders if FY = 0
                    const arma::cx_double wx = 2*M_PI*j*frqx;
                    if (dy == 0) {
                        value = b/wx*(std::exp(-wx*e->org.x) - std::exp(-wx*e->dst.x));
                    } else { //dX && dY != 0
                        const arma::cx_double ex0 = std::exp(-wx * e->org.x);
                        const arma::cx_double ex1 = std::exp(-wx * e->dst.x);
                        value = (s+wx*b)*(ex0-ex1)/wx/wx + s*(ex0*e->org.x - ex1*e->dst.x)/wx;
                    }
                } else { // other cases
                    const arma::cx_double wx = 2*M_PI*j*frqx;
                    const arma::cx_double wy = 2*M_PI*j*frqy;
                    if (dy == 0) {
                        value = (1.0 - std::exp(-wy*b))*(std::exp(-wx*e->org.x)-std::exp(-wx*e->dst.x))/wx/wy;
                    } else if (wx + s*wy == 0.0) {
                        value = (std::exp(-wx*e->org.x)-std::exp(-wx*e->dst.x))/wx/wy - dx*std::exp(-wy*b)/wy;
                    } else {
                        const arma::cx_double coef = wx + s*wy;
                        const arma::cx_double dexp = std::exp(-wx*e->org.x) - std::exp(-wx*e->dst.x);
                        value = dexp/wx/wy + std::exp(-wy*b)/wy*(std::exp(-coef*e->dst.x)-std::exp(-coef*e->org.x))/coef;
                    }
                }
            }
            result += value;
        }
        return result;
    }

    void Diffraction::_add_2d_region(SharedAbstractMaskGeometry region, arma::cx_double factor) {
        arma::cx_mat& values = *this->values();
        arma::mat& cxy = *this->cxy();

        // Corrected during mask converting
        // We should make positive area of polygon
        // region->set_bypass(CW);

        double na = this->numeric_aperture;

        // Flag that diffraction term at kx, ky has been calculated
        auto calculated = arma::uchar_mat(values.n_rows, values.n_cols, arma::fill::zeros);

        for (uint32_t k = 0; k < this->source_shape->non_zeros()->n_rows; k++) {
            auto rc = this->source_shape->non_zeros()->row(k);
            double scx = na * this->source_shape->cx(rc(1));
            double scy = na * this->source_shape->cy(rc(0));

            for (uint32_t c = 0;  c < this->_kx->n_elem; c++) {
                int32_t kx = (*this->_kx)(c);
                double cx = (*this->_cx)(c);
                double frqx = (*this->_frqx)(c);
                for (uint32_t r = 0; r < this->_ky->n_elem; r++) {
                    int32_t ky = (*this->_ky)(r);
                    double cy = (*this->_cy)(r);
                    double frqy = (*this->_frqy)(r);
                    // Diffraction term not being calculated if it has already been calculated and
                    // it in aperture or in aperture + offset from source
                    // Additional check cxy <= na required for the reason diffraction orders should
                    // not been removed for central order especially for displaying.
                    if (!calculated(r, c) && (cxy(r, c) <= na || within_circle(cx, cy, scx, scy, na))) {
                        values(r, c) += factor*Diffraction::_calc_2d_region(region, kx, ky, frqx, frqy);
                        calculated(r, c) = true;
                    }
                } // end ky for-loop
            }  // end kx for-loop
        }  // end source shape for-loop
    }

    Diffraction::Diffraction(SharedMask mask, SharedImagingTool imaging_tool) :
            source_shape(imaging_tool->source_shape()),
            pitch(mask->pitch()),
            boundary(*mask->boundary()),
            numeric_aperture(imaging_tool->numeric_aperture),
            wavelength(imaging_tool->wavelength)
    {
        const double na = this->numeric_aperture;
        const double wvl = this->wavelength;
        const double scx_min = this->source_shape->sx_min();
        const double scx_max = this->source_shape->sx_max();
        const double scy_min = this->source_shape->sy_min();
        const double scy_max = this->source_shape->sy_max();

        // Attention: rows is y-axis and cols is x-axis
        auto lim_cols = Diffraction::_calc_size(na, wvl, this->pitch.x, scx_min, scx_max);
        auto lim_rows = Diffraction::_calc_size(na, wvl, this->pitch.y, scy_min, scy_max);

        uint32_t cols = lim_cols.second - lim_cols.first + 1;
        uint32_t rows = lim_rows.second - lim_rows.first + 1;

    //	VLOG(4) << "Cols = " << cols << " Rows = " << rows;

    //	VLOG(4) << "Allocate memory for arrays and vectors";
        this->_values = std::make_shared<arma::cx_mat>(rows, cols, arma::fill::zeros);

        this->_frqx = std::make_shared<arma::vec>(cols, arma::fill::zeros);
        this->_frqy = std::make_shared<arma::vec>(rows, arma::fill::zeros);

        this->_cx = std::make_shared<arma::vec>(cols, arma::fill::zeros);
        this->_cy = std::make_shared<arma::vec>(rows, arma::fill::zeros);

        this->_kx = std::make_shared<arma::s32_vec>(cols, arma::fill::zeros);
        this->_ky = std::make_shared<arma::s32_vec>(rows, arma::fill::zeros);

    //	VLOG(4) << "Initialize diffraction cosine and terms vectors";
        Diffraction::_init_vectors(*this->_kx, *this->_frqx, *this->_cx, this->pitch.x, this->wavelength, lim_cols);
        Diffraction::_init_vectors(*this->_ky, *this->_frqy, *this->_cy, this->pitch.y, this->wavelength, lim_rows);

        this->_cxy = std::make_shared<arma::mat>(rows, cols, arma::fill::zeros);
        Diffraction::_init_cosines(*this->_cxy, *this->_cx, *this->_cy);
    }

    // Return direction cosines for given axis
    std::shared_ptr<arma::vec> Diffraction::c(uint32_t axis) const {
        return Diffraction::_select_axis(axis, this->_cx, this->_cy);
    }

    // Return diffraction terms order number for given axis
    std::shared_ptr<arma::s32_vec> Diffraction::k(uint32_t axis) const {
        return Diffraction::_select_axis(axis, this->_kx, this->_ky);
    }

    // Return spatial frequencies for given axis
    std::shared_ptr<arma::vec> Diffraction::frq(uint32_t axis) const {
        return Diffraction::_select_axis(axis, this->_frqx, this->_frqy);
    }

    // Return plane waves of diffraction pattern values
    std::shared_ptr<arma::cx_mat> Diffraction::values(void) const {
        return this->_values;
    }

    arma::cx_double Diffraction::value(uint32_t r, uint32_t c) const {
        return (*this->_values)(r, c);
    }

    // Return absolute value of direction cosines
    std::shared_ptr<arma::mat> Diffraction::cxy(void) const {
        return this->_cxy;
    }

    // Return direction cosine belong to x-axis
    std::shared_ptr<arma::vec> Diffraction::cx(void) const {
        return this->_cx;
    }

    double Diffraction::cx(uint32_t i) const {
        return (*this->_cx)(i);
    }

    // Return direction cosine belong to y-axis
    std::shared_ptr<arma::vec> Diffraction::cy(void) const {
        return this->_cy;
    }

    double Diffraction::cy(uint32_t i) const {
        return (*this->_cy)(i);
    }

    // Return spatial frequencies belong to x-axis
    std::shared_ptr<arma::vec> Diffraction::frqx(void) const {
        return this->_frqx;
    }

    // Return spatial frequencies belong to y-axis
    std::shared_ptr<arma::vec> Diffraction::frqy(void) const {
        return this->_frqy;
    }

    // Return diffraction terms order numbers belong x-axis
    std::shared_ptr<arma::s32_vec> Diffraction::kx(void) const {
        return this->_kx;
    }

    int32_t Diffraction::kx(uint32_t i) const {
        return (*this->_kx)(i);
    }

    // Return diffraction terms order numbers belong y-axis
    std::shared_ptr<arma::s32_vec> Diffraction::ky(void) const {
        return this->_ky;
    }

    int32_t Diffraction::ky(uint32_t i) const {
        return (*this->_ky)(i);
    }

    void Diffraction::add_region(SharedAbstractMaskGeometry region, arma::cx_double factor) {
        if (region->axis() == DIM_1D_X || region->axis() == DIM_1D_Y) {
            this->_add_1d_region(region, factor/this->pitch[region->axis()]);
        } else if (region->axis() == DIM_2D) {
            this->_add_2d_region(region, factor/this->pitch.x/this->pitch.y);
        } else {
            throw std::invalid_argument("Can't process region while diffraction calculate: region type is unknown");
        }
    }


    // ============================================= AbstractWaferLayer ============================================= //


    bool AbstractWaferLayer::is_environment(void) const {
        return this->type == ENVIRONMENT_LAYER;
    }

    bool AbstractWaferLayer::is_resist(void) const {
        return this->type == RESIST_LAYER;
    }

    bool AbstractWaferLayer::is_material(void) const {
        return this->type == MATERIAL_LAYER;
    }

    bool AbstractWaferLayer::is_substrate(void) const {
        return this->type == SUBSTRATE_LAYER;
    }

    arma::cx_double AbstractWaferLayer::effective_refraction(arma::cx_double incident_angle, double wavelength) const {
        return std::cos(incident_angle) * this->refraction(wavelength);
    }

    // Attention: valid only for zero order
    arma::cx_double AbstractWaferLayer::internal_transmit(double wavelength, double power) const {
        return std::exp(2.0*M_PI*j*this->refraction(wavelength)*this->thickness/wavelength*power);
    }

    arma::cx_double AbstractWaferLayer::internal_transmit(
        arma::cx_double incident_angle, double dz, double wavelength) const {
        return std::exp(2.0*M_PI*j*this->effective_refraction(incident_angle, wavelength)*dz/wavelength);
    }

    std::string AbstractWaferLayer::str(void) const {
        std::ostringstream result;
        result << "WaferLayer: ";
        if (this->is_environment()) {
            result << "environment";
        } else if (this->is_resist()) {
            result << "resist";
        } else if (this->is_material()) {
            result << "material";
        } else if (this->is_substrate()) {
            result << "substrate";
        } else {
            result << "unknown type";
        }
        result << "; thickness: " << this->thickness;
        return result.str();
    }


    // ============================================= StandardWaferLayer ============================================= //


    StandardWaferLayer::StandardWaferLayer(layer_type_t layer_type, double thickness, const arma::vec& wavelength,
            const arma::vec& refraction_real, const arma::vec& refraction_imag) :
                AbstractWaferLayer(layer_type, thickness) {
        auto wvl = std::make_shared<arma::vec>(wavelength);
        auto real = std::make_shared<arma::vec>(refraction_real);
        auto imag = std::make_shared<arma::vec>(refraction_imag);
        this->_refraction_real = interp::LinearInterpolation1d(wvl, real, NAN);
        this->_refraction_imag = interp::LinearInterpolation1d(wvl, imag, NAN);
    }

    arma::cx_double StandardWaferLayer::refraction(double wavelength, double m) const {
        double real = this->_refraction_real.interpolate(wavelength);
        double imag = this->_refraction_imag.interpolate(wavelength);
    //	LOG(INFO) << "REFRACTION(" << wavelength << ") = " << real << " " << imag;
        return arma::cx_double(real, imag);
    }

    bool StandardWaferLayer::operator==(const AbstractWaferLayer& other) const {
        if (this->type != other.type) {
            return false;
        } else {
            const StandardWaferLayer *p = dynamic_cast<const StandardWaferLayer*>(&other);
            return this->_refraction_real == p->_refraction_real && this->_refraction_imag == p->_refraction_imag;
        }
    }


    // ============================================= ConstantWaferLayer ============================================= //


    ConstantWaferLayer::ConstantWaferLayer(layer_type_t layer_type, double thickness, double real, double imag) :
        AbstractWaferLayer(layer_type, thickness) {
        this->_refraction = arma::cx_double(real, imag);
    }

    arma::cx_double ConstantWaferLayer::refraction(double wavelength, double m) const {
    //	LOG(INFO) << "CONST REFRACTION: " << this->_refraction.real() << " " << this->_refraction.imag();
        return this->_refraction;
    }

    bool ConstantWaferLayer::operator==(const AbstractWaferLayer& other) const {
        if (this->type != other.type) {
            return false;
        } else {
            const ConstantWaferLayer *p = dynamic_cast<const ConstantWaferLayer*>(&other);
            return this->_refraction == p->_refraction;
        }
    }


    // ============================================ ExposureResistModel ============================================= //


    arma::cx_double ExposureResistModel::refraction(double m) const {
        double im = this->wavelength / 4.0 / M_PI * (this->a * m + this->b) * 1e-3;
        return arma::cx_double(this->n, im);
    }

    bool ExposureResistModel::operator==(const ExposureResistModel& other) const {
        return this->wavelength == other.wavelength &&
                this->a == other.a && this->b == other.b &&
                this->c == other.c && this->n == other.n;
    }


    // ============================================== PebResistModel ================================================ //


    double PebResistModel::diffusivity(double temp) const {
        double tempk = temp - physc::T0;
        return std::exp(this->ln_ar - this->ea/(physc::R*tempk));
    }

    double PebResistModel::diffusion_length(double temp, double time) const {
        return std::sqrt(2.0 * this->diffusivity(temp) * time);
    }

    arma::vec PebResistModel::kernel(SharedPostExposureBake peb, double step) const {
        if (step != 0.0) {
            double sigma = this->diffusion_length(peb->temp, peb->time);

    //		LOG(INFO) << "Create PEB kernel for temp = " << peb->temp <<
    //				" time = " << peb->time << " with Sigma = " << sigma;

            // Convert result sigma value to input grid value
            double sigma_on_grid = std::ceil(3.0*sigma) - std::fmod(std::ceil(3.0*sigma), step) + step;
            uint32_t count = (uint32_t) (2*sigma_on_grid/step) + 1;

    //		LOG(INFO) << "Kernel size = " << count << " SigmaGrid = " << sigma_on_grid;

            arma::vec kernel = arma::vec(count);

            for (uint32_t k = 0; k < count; k++) {
                double x = k*step - sigma_on_grid;
                kernel[k] = step/sigma/std::sqrt(2*M_PI)*std::exp(-x*x/2/sigma/sigma);
            }

            // Convolution kernel must be normalized because three sigma interval is not equal to full intergral value
            // of the kernel. So this can result in PAC after PEB will exceed max possible value 1.0. In turn development
            // rates will be calculated with NaN values
            return kernel / arma::accu(kernel);
        } else {
    //		LOG(INFO) << "Create empty PEB kernel (step = 0.0)";
            return arma::vec(1, arma::fill::ones);
        }
    }

    bool PebResistModel::operator==(const PebResistModel& other) const {
        return this->ea == other.ea && this->ln_ar == other.ln_ar;
    }


    // ============================================= ResistWaferLayer =============================================== //


    arma::cx_double ResistWaferLayer::refraction(double wavelength, double m) const {
        return this->exposure->refraction(m);
    }

    bool ResistWaferLayer::operator==(const AbstractWaferLayer& other) const {
        if (this->type != other.type) {
            return false;
        } else {
            const ResistWaferLayer *p = dynamic_cast<const ResistWaferLayer*>(&other);
            return this->exposure == p->exposure && this->peb == p->peb && this->rate == p->rate;
        }
    }


    // ================================================ WaferStack ================================================== //


    // Calculate refractive indexes between layers (for all layers in the stack)
    arma::cx_vec WaferStack::_calc_refractive_indexes(double cxy, double wavelength) {
        arma::cx_vec refractive_indexes = arma::cx_vec(this->_layers.size());

        arma::cx_double angle = std::asin(cxy);
        refractive_indexes(0) = this->_layers[0]->effective_refraction(angle, wavelength);
        for (uint32_t k = 1; k < this->_layers.size(); k++) {
            arma::cx_double rtop = this->_layers[k-1]->refraction(wavelength);
            arma::cx_double rbot = this->_layers[k]->refraction(wavelength);
            angle = WaferStack::_angle(angle, rtop, rbot);
            refractive_indexes(k) = this->_layers[k]->effective_refraction(angle, wavelength);
        }

        return refractive_indexes;
    }

    // Calculate effective reflection for all stack from top to bottom
    // (reflection with taking account of all top layers)
    std::shared_ptr<arma::cx_vec> WaferStack::_calc_effective_top_reflections(double cxy, double wavelength) {
        arma::cx_vec refractive_indexes = this->_calc_refractive_indexes(cxy, wavelength);

        std::shared_ptr<arma::cx_vec> result = std::make_shared<arma::cx_vec>(this->_layers.size());
        arma::cx_vec& reflections = *result;

        reflections(0) = WaferStack::_reflection(refractive_indexes(0), refractive_indexes(1));

        for (uint32_t k = 1; k < this->_layers.size()-1; k++) {
            arma::cx_double v = reflections(k-1) * this->_layers[k]->internal_transmit(wavelength, 2.0);
            arma::cx_double y = (1.0 + v) / (1.0 - v);
            reflections(k) = (refractive_indexes(k)*y - refractive_indexes(k+1)) /
                    (refractive_indexes(k)*y + refractive_indexes(k+1));
        }

        return result;
    }

    // Return cached value or calculate
    std::shared_ptr<arma::cx_vec> WaferStack::effective_top_reflection(double cx, double cy, double wavelength) {
        if (this->_cached_wavelength != wavelength) {
            this->_cached_top_reflections.clear();
            this->_cached_wavelength = wavelength;
        }
        auto cx_cy = std::make_pair(cx, cy);
        auto cached = this->_cached_top_reflections.find(cx_cy);
        if (cached != this->_cached_top_reflections.end()) {
             return cached->second;
        } else {
            double cxy = sqrt(cx*cx + cy*cy);
            std::shared_ptr<arma::cx_vec> reflections = this->_calc_effective_top_reflections(cxy, wavelength);
            this->_cached_top_reflections[cx_cy] = reflections;
            return reflections;
        }
    }

    // Calculate effective reflection for all stack from bottom to top
    // (reflection with taking account of all bottom layers)
    std::shared_ptr<arma::cx_vec> WaferStack::_calc_effective_bottom_reflections(double cxy, double wavelength) {
        arma::cx_vec refractive_indexes = this->_calc_refractive_indexes(cxy, wavelength);
        std::shared_ptr<arma::cx_vec> result = std::make_shared<arma::cx_vec>(this->_layers.size());
        arma::cx_vec& reflections = *result;

        uint32_t bottom = this->_layers.size() - 1;
        reflections(bottom-1) = WaferStack::_reflection(refractive_indexes(bottom-1), refractive_indexes(bottom));

        for (uint32_t k = bottom-2; k >= 1; k--) {
            arma::cx_double v = reflections(k+1) * this->_layers[k+1]->internal_transmit(wavelength, 2.0);
            arma::cx_double x = (1.0 - v) / (1.0 + v);
            reflections(k) = (refractive_indexes(k) - x*refractive_indexes(k+1)) /
                    (refractive_indexes(k) + x*refractive_indexes(k+1));
        }

        reflections(0) = WaferStack::_reflection(refractive_indexes(0), refractive_indexes(1));

        return result;
    }

    // Return cached value or calculate
    std::shared_ptr<arma::cx_vec> WaferStack::effective_bottom_reflection(double cx, double cy, double wavelength) {
        if (this->_cached_wavelength != wavelength) {
            this->_cached_bottom_reflections.clear();
            this->_cached_wavelength = wavelength;
        }
        auto cx_cy = std::make_pair(cx, cy);
        auto cached = this->_cached_bottom_reflections.find(cx_cy);
        if (cached != this->_cached_bottom_reflections.end()) {
             return cached->second;
        } else {
            double cxy = sqrt(cx*cx + cy*cy);
            std::shared_ptr<arma::cx_vec> reflections = this->_calc_effective_bottom_reflections(cxy, wavelength);
            this->_cached_bottom_reflections[cx_cy] = reflections;
            return reflections;
        }
    }

    WaferStack::WaferStack(void) {
        this->_resist = nullptr;
        this->_substrate = nullptr;
        this->_environment = nullptr;
        this->_cached_wavelength = -1.0;
    }

    WaferStack::WaferStack(ArrayOfSharedAbstractWaferLayers layers) : WaferStack() {
        for (auto layer : layers) {
            this->push(layer);
        }
    }

    void WaferStack::push(SharedAbstractWaferLayer layer) {
        if (this->_environment) {
            throw std::invalid_argument("Layer of any type can't be added after the environment layer set");
        }

        if (this->_resist) {
            if (layer->is_resist()) {
                throw std::invalid_argument("Can't push the second resist layer into the wafer stack");
            } else if (!layer->is_environment()) {
                throw std::invalid_argument("Material layer on the resist layer not allowed");
            }
        }

        if (this->_layers.empty() && !layer->is_substrate()) {
            throw std::invalid_argument("First layer must be substrate layer");
        }

        if (layer->is_environment()) {
            this->_environment = layer;
        } else if (layer->is_resist()) {
            this->_resist = layer;
        } else if (layer->is_substrate()) {
            this->_substrate = layer;
        }

        this->_layers.insert(this->_layers.begin(), layer);
    }

    bool WaferStack::is_ok(void) {
        return this->_environment && this->_resist && this->_substrate;
    }

    SharedAbstractWaferLayer WaferStack::operator[](int32_t i) const {
        // Make available circular indexing and negative indexing, e.g. -1 => last item
        return this->_layers[(this->_layers.size() + i) % this->_layers.size()];
    }

    SharedAbstractWaferLayer WaferStack::environment(void) const {
        return this->_environment;
    }

    SharedAbstractWaferLayer WaferStack::resist(void) const {
        return this->_resist;
    }

    SharedAbstractWaferLayer WaferStack::substrate(void) const {
        return this->_substrate;
    }

    uint32_t WaferStack::index_of(SharedAbstractWaferLayer layer) const {
        return std::find(this->_layers.begin(), this->_layers.end(), layer) - this->_layers.begin();
    }

    std::complex<double> WaferStack::reflectivity(uint32_t indx, double wavelength) {
        if (indx == 0 || indx > this->_layers.size()-1) {
            throw std::out_of_range("Can't calculate reflectivity for "
                    "environment layer or layer that isn't in list");
        }

        arma::cx_double ro12 = WaferStack::_reflection(
                this->_layers[indx-1]->effective_refraction(0.0, wavelength),
                this->_layers[indx]->effective_refraction(0.0, wavelength));

        arma::cx_vec bottom_reflections = *this->effective_bottom_reflection(0.0, 0.0, wavelength);

        arma::cx_double ro23e = bottom_reflections(indx);
        arma::cx_double tau2d = this->_layers[indx]->internal_transmit(wavelength, 2.0);

        arma::cx_double v = (ro12 + ro23e * tau2d) / (1.0 + ro12*ro23e * tau2d);

    //	LOG(INFO) << "indx = " << indx << "ro12 = " << ro12 << " ro23e = "
    //			<< ro23e << " tau2d = " << tau2d << " v = " << v;

        return v;
    }

    // This routine only suitable for the stack where resist is the SECOND layer!
    std::complex<double> WaferStack::standing_waves(double cx, double cy, double dz, double wavelength) {
        arma::cx_vec reflections = *this->effective_bottom_reflection(cx, cy, wavelength);
        double cxy = sqrt(cx*cx + cy*cy);

        arma::cx_double env_angle = std::asin(cxy);
        arma::cx_double resist_angle = WaferStack::_angle(env_angle,
                this->environment()->refraction(wavelength), this->resist()->refraction(wavelength));

        arma::cx_double reffenv = this->environment()->effective_refraction(env_angle, wavelength);
        arma::cx_double reffres = this->resist()->effective_refraction(resist_angle, wavelength);

        arma::cx_double tau12 = WaferStack::_transmittance(reffenv, reffres);
        arma::cx_double ro12 = reflections(0);
        arma::cx_double ro23e = reflections(1);
        arma::cx_double dtau = this->resist()->internal_transmit(resist_angle, this->resist()->thickness, wavelength);
        arma::cx_double tau2d = dtau * dtau;
        arma::cx_double ztau = this->resist()->internal_transmit(resist_angle, dz, wavelength);
        arma::cx_double num = tau12 * (ztau + ro23e*tau2d/ztau);
        arma::cx_double den = 1.0 + ro12*ro23e*tau2d;
        arma::cx_double standing_wave = num / den;
    //	LOG(INFO) << "cx = " << cx << " cy = " << cy << " dz = " << dz << " wvl = " << wavelength << std::endl
    //			<< " angle env = " << env_angle << " angl res = " << resist_angle << std::endl
    //			<< " reffenv = " << reffenv << " reffres = " << reffres << " tau12 = " << tau12 << std::endl
    //			<< " coef = " << ztau << " ro12 = " << reflections(0) << " ro23e = " << reflections(1) << std::endl
    //			<< " standing wave = " << standing_wave;
        return standing_wave;
    }

    bool WaferStack::operator==(const WaferStack& other) const {
        return this->_layers == other._layers;
    }


    // =========================================== OpticalTransferFunction ========================================== //


    // Calculate optical transfer function value for given direction cosines values cx, cy
    // and given offset from the resist top dz.
    arma::cx_double OpticalTransferFunction::calc(double cx, double cy, double dz) {
        arma::cx_double otf = 1.0;
        if (within_circle(cx, cy, this->_numeric_aperture)) {
            otf *= this->_imaging_tool->filter(cx, cy);
            otf *= this->_imaging_tool->reduction(cx, cy);
            if (this->_exposure) {
                otf *= this->_exposure->defocus(cx, cy, this->_wavelength);
            }
            if (this->_wafer_stack) {
                otf *= this->_wafer_stack->standing_waves(cx, cy, dz, this->_wavelength);
            }
        } else {
            otf = 0.0;
        }
        return otf;
    }

    ConstSharedImagingTool OpticalTransferFunction::imaging_tool(void) const {
        return this->_imaging_tool;
    }

    ConstSharedExposure OpticalTransferFunction::exposure(void) const {
        return this->_exposure;
    }

    ConstSharedWaferStack OpticalTransferFunction::wafer_stack(void) const {
        return this->_wafer_stack;
    }
    
}  // namespace oplc
