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

%module optolithiumc
%{
    #define SWIG_FILE_WITH_INIT

    /* Includes the header in the wrapper code */
    #include "opl_contours.h"
    #include "opl_geometry.h"
    #include "opl_iter.h"
    #include "opl_capi.h"
    #include "opl_sim.h"

    static PyObject* ctypes_module;
    static PyObject* ctypes_module_cast;
    static PyObject* ctypes_module_c_void_p;

    int load_ctypes_module(void) {
        ctypes_module = PyImport_ImportModule("ctypes");
        if (!ctypes_module) {
            PyErr_SetString(PyExc_RuntimeError, "Can't load ctypes module!");
            return -1;
        }

        ctypes_module_cast = PyObject_GetAttrString(ctypes_module, "cast");
        if (!ctypes_module_cast) {
            PyErr_SetString(PyExc_RuntimeError, "ctypes.cast function not found in ctypes module!");
            return -1;
        }

        ctypes_module_c_void_p = PyObject_GetAttrString(ctypes_module, "c_void_p");
        if (!ctypes_module_c_void_p) {
            PyErr_SetString(PyExc_RuntimeError, "ctypes.c_void_p class not found in ctypes module!");
            return -1;
        }
        return 0;
    }

%}

%init {
    if (load_ctypes_module() == -1) {
        # if PY_VERSION_HEX >= 0x03000000
            return NULL;
        # else
            return;
        # endif
    }
}

/* ---------------------------------------------------------------------------- */

%define %ctypes_callback(typename)
    %typemap(in) typename {
        PyObject* args = Py_BuildValue("(OO)", $input, ctypes_module_c_void_p);
        if (!args) {
            SWIG_exception_fail(SWIG_ERROR, "Py_BuildValue: can't create input args tuple!");
        }
        PyObject* pointer = PyObject_CallObject(ctypes_module_cast, args);
        if (!pointer) {
            SWIG_exception_fail(SWIG_ERROR, "PyObject_CallObject: convert function to c_void_p failed!");
        }
        PyObject* address = PyObject_GetAttrString(pointer, "value");
        if (!address) {
            SWIG_exception_fail(SWIG_ERROR, "PyObject_GetAttrString: get address from c_void_p failed!");
        }
        uint64_t address_value = PyInt_AsUnsignedLongLongMask(address);
        //printf("Address is %016llX\n", address_value);
        //PyObject_Print(address,stdout,Py_PRINT_RAW);
        if (address_value == (uint64_t)-1) {
            if (PyErr_Occurred()) {
                PyObject *errtype, *errvalue, *traceback;
                PyErr_Fetch(&errtype, &errvalue, &traceback);
                if (errvalue != nullptr) {
                    PyObject *str = PyObject_Str(errvalue);
                    std::string header_string("PyLong_AsUnsignedLongLong: ");
                    std::string message_string(PyString_AsString(str));
                    SWIG_exception_fail(SWIG_ERROR, (header_string + message_string).c_str());
                    Py_DECREF(str);
                }
                Py_XDECREF(errvalue);
                Py_XDECREF(errtype);
                Py_XDECREF(traceback);
            }
        }
        $1 = reinterpret_cast<typename>(address_value);
    }
%enddef

/* ---------------------------------------------------------------------------- */

%include <typemaps.i>
%include <stdint.i>
%include <complex.i>
%include <std_shared_ptr.i>
%include <std_vector.i>
%include <std_string.i>
%include <armanpy.i>

/* ---------------------------------------------------------------------------- */

%ctypes_callback(source_shape_expr_t)
%ctypes_callback(rate_model_expr_t)
%ctypes_callback(pupil_filter_expr_t)

/* ---------------------------------------------------------------------------- */

%shared_ptr(geometry::Point2d)
%shared_ptr(geometry::Edge2d)

%shared_ptr(geometry::Point3d)
%shared_ptr(geometry::Edge3d)

%shared_ptr(geometry::Triangle3d)
%shared_ptr(geometry::Surface3d)

%shared_ptr(geometry::AbstractGeometry)
%shared_ptr(geometry::PolygonGeometry)
%shared_ptr(geometry::RectangleGeometry)

%shared_ptr(oplc::AbstractMaskGeometry)
%shared_ptr(oplc::Region)
%shared_ptr(oplc::Box)

%shared_ptr(oplc::AbstractResistRateModel)
%shared_ptr(oplc::ResistRateModelExpression)
%shared_ptr(oplc::ResistRateModelSheet)
%shared_ptr(oplc::ResistRateModelDepthSheet)

%shared_ptr(oplc::AbstractSourceShapeModel)
%shared_ptr(oplc::SourceShapeModelPlugin)
%shared_ptr(oplc::SourceShapeModelSheet)

%shared_ptr(oplc::AbstractPupilFilterModel)
%shared_ptr(oplc::PupilFilterModelPlugin)
%shared_ptr(oplc::PupilFilterModelSheet)
%shared_ptr(oplc::PupilFilterModelEmpty)

%shared_ptr(oplc::ExposureResistModel)
%shared_ptr(oplc::PebResistModel)

%shared_ptr(oplc::AbstractWaferLayer)
%shared_ptr(oplc::StandardWaferLayer)
%shared_ptr(oplc::ResistWaferLayer)
%shared_ptr(oplc::ConstantWaferLayer)
%shared_ptr(oplc::WaferStack)

%shared_ptr(oplc::Mask)
%shared_ptr(oplc::ImagingTool)
%shared_ptr(oplc::Diffraction)
%shared_ptr(oplc::SourceShape)
%shared_ptr(oplc::Exposure)
%shared_ptr(oplc::PostExposureBake)
%shared_ptr(oplc::Development)
%shared_ptr(oplc::OpticalTransferFunction)

%shared_ptr(oplc::AbstractResistSimulations)
%shared_ptr(oplc::ResistVolume)
%shared_ptr(oplc::ResistProfile)

/* ---------------------------------------------------------------------------- */

%template(Triangle3dArray) std::vector<std::shared_ptr<geometry::Triangle3d> >;
%template(PolygonsArray) std::vector<std::shared_ptr<geometry::PolygonGeometry> >;
%template(Points2dArray) std::vector<std::shared_ptr<geometry::Point2d> >;
%template(Points3dArray) std::vector<std::shared_ptr<geometry::Point3d> >;
%template(RegionsArray) std::vector<std::shared_ptr<Region> >;
%template(DoubleArray) std::vector<double>;

/* ---------------------------------------------------------------------------- */

%exception {
    try {
        $action
    } catch (std::length_error error) {
        PyErr_SetString(PyExc_IndexError, error.what());
        SWIG_fail;
    } catch (std::out_of_range error) {
        PyErr_SetString(PyExc_IndexError, error.what());
        SWIG_fail;
    } catch (std::invalid_argument error) {
        PyErr_SetString(PyExc_ValueError, error.what());
        SWIG_fail;
    } catch (std::range_error error) {
        PyErr_SetString(PyExc_IndexError, error.what());
        SWIG_fail;
    } catch (std::runtime_error error) {
        PyErr_SetString(PyExc_RuntimeError, error.what());
        SWIG_fail;
    } catch (std::exception error) {
        PyErr_SetString(PyExc_Exception, error.what());
        SWIG_fail;    
    }
}

/* ---------------------------------------------------------------------------- */

namespace geometry {

    %extend Point2d {
        %rename(__getitem__) operator[];
        %rename(__len__) length;
        %rename(__repr__) str;

        %pythoncode %{
            def round(self, ndigits):
                return self.__class__(round(self.x, ndigits), round(self.y, ndigits))

            def __hash__(self):
                return hash((self.x, self.y))
        %}
    }

    %ignore operator *;
    %ignore operator /;

    %extend Edge2d {
        %rename(__str__) str;
    }

    %extend Point3d {
        %rename(__getitem__) operator[];
        %rename(__len__) length;
        %rename(__repr__) str;
    }

    %extend Edge3d {
        %rename(__str__) str;
    }

    %extend Triangle3d {
        %rename(__getitem__) operator[];
        %rename(__len__) length;
        %rename(__repr__) str;

        %rename(_get_a) a() const;
        %rename(_get_b) b() const;
        %rename(_get_c) c() const;

        %pythoncode %{
            __swig_getmethods__["a"] = _get_a
            __swig_getmethods__["b"] = _get_b
            __swig_getmethods__["c"] = _get_c

            if _newclass: 
                a = property(_get_a)
                b = property(_get_b)
                c = property(_get_c)
        %}
    }

    %extend Surface3d {
        %rename(_get_points) points() const;
        %rename(_get_triangles) triangles() const;

        %rename(_get_x) x() const;
        %rename(_get_y) y() const;
        %rename(_get_z) z() const;

        %pythoncode %{
            __swig_getmethods__["points"] = _get_points
            __swig_getmethods__["triangles"] = _get_triangles

            __swig_getmethods__["x"] = _get_x
            __swig_getmethods__["y"] = _get_y
            __swig_getmethods__["z"] = _get_z

            if _newclass: 
                points = property(_get_points)
                triangles = property(_get_triangles)

                x = property(_get_x)
                y = property(_get_y)
                z = property(_get_z)
        %}
    }

    // ArrayOfSharedPoints2d
    %extend std::vector<std::shared_ptr<Point2d> > {
        std::string __str__() {
            std::ostringstream result;
            for (auto item : *$self) {
                result << " " << item->str() << ", " << std::endl;
            }
            return result.str();
        }
    }

    // ArrayOfSharedPoints3d
    %extend std::vector<std::shared_ptr<Point3d> > {
        std::string __str__() {
            std::ostringstream result;
            for (auto item : *$self) {
                result << " " << item->str() << ", " << std::endl;
            }
            return result.str();
        }
    }

    %extend AbstractGeometry {
        %rename(__getitem__) at;
        %rename(__len__) length;
        %rename(__str__) str;

        %pythoncode %{
            def __iter__(self):
                for k in xrange(len(self)):
                    yield self[k]
        %}
    }


    // ArrayOfSharedPolygons
    %extend std::vector<std::shared_ptr<PolygonGeometry> > {
        std::string __str__() {
            std::ostringstream result;
            for (auto item : *$self) {
                result << " " << item->str() << ", " << std::endl;
            }
            return result.str();
        }
    }
}  // namespace geometry


namespace interp {
    %extend LinearInterpolation1d {
        LinearInterpolation1d(const arma::vec& x, const arma::vec& y, double fill=0.0) {
            return new interp::LinearInterpolation1d(
                std::make_shared<const arma::vec>(x), 
                std::make_shared<const arma::vec>(y), 
                fill);
        }
    }

    %extend LinearInterpolation2d {
        LinearInterpolation2d(const arma::vec& x, const arma::vec& y, const arma::mat& values, double fill=0.0) {
            return new interp::LinearInterpolation2d(
                std::make_shared<const arma::vec>(x), 
                std::make_shared<const arma::vec>(y), 
                std::make_shared<const arma::mat>(values), 
                fill);
        }
    }
}  // namespace interp

namespace oplc {

    %extend Diffraction {
        %ignore c(uint32_t) const;
        %ignore k(uint32_t) const;
        %ignore frq(uint32_t) const;
        %ignore value(uint32_t, uint32_t) const;
        %ignore cx(uint32_t) const;
        %ignore cy(uint32_t) const;
        %ignore kx(uint32_t) const;
        %ignore ky(uint32_t) const;

        %rename(_get_values) values() const;
        %rename(_get_cxy) cxy() const;
        
        %rename(_get_cx) cx() const;
        %rename(_get_cy) cy() const;

        %rename(_get_frqx) frqx() const;
        %rename(_get_frqy) frqy() const;
        
        %rename(_get_kx) kx() const;
        %rename(_get_ky) ky() const;
        
        %pythoncode %{
            __swig_getmethods__["values"] = _get_values
            __swig_getmethods__["cxy"] = _get_cxy
            
            __swig_getmethods__["cx"] = _get_cx
            __swig_getmethods__["cy"] = _get_cy

            __swig_getmethods__["frqx"] = _get_frqx
            __swig_getmethods__["frqy"] = _get_frqy
            
            __swig_getmethods__["kx"] = _get_kx
            __swig_getmethods__["ky"] = _get_ky
            if _newclass: 
                values = property(_get_values)
                cxy = property(_get_cxy)

                cx = property(_get_cx)
                cy = property(_get_cy)
                
                frqx = property(_get_frqx)
                frqy = property(_get_frqy)
                
                kx = property(_get_kx)
                ky = property(_get_ky)
        %}
    }


    %extend AbstractResistSimulations {    
        %ignore x(uint32_t) const;
        %ignore y(uint32_t) const;
        %ignore z(uint32_t) const;

        %rename(_get_type) type() const;
        %rename(_get_x) x() const;
        %rename(_get_y) y() const;
        %rename(_get_z) z() const;
        %rename(_has_x) has_x() const;
        %rename(_has_y) has_y() const;
        %rename(_has_z) has_z() const;
        %rename(_axes) axes() const;

        %pythoncode %{
            __swig_getmethods__["type"] = _get_type
            __swig_getmethods__["x"] = _get_x
            __swig_getmethods__["y"] = _get_y
            __swig_getmethods__["z"] = _get_z
            __swig_getmethods__["has_x"] = _has_x
            __swig_getmethods__["has_y"] = _has_y
            __swig_getmethods__["has_z"] = _has_z
            __swig_getmethods__["axes"] = _axes;
            if _newclass:
                type = property(_get_type)
                x = property(_get_x)
                y = property(_get_y)
                z = property(_get_z)
                has_x = property(_has_x)
                has_y = property(_has_y)
                has_z = property(_has_z)
                axes = property(_axes)
        %}
    }


    %extend ResistVolume {
        %ignore value(uint32_t, uint32_t, uint32_t) const;
        %rename(_get_values) values() const;
        %pythoncode %{
            __swig_getmethods__["values"] = _get_values
            if _newclass:
                values = property(_get_values)
        %}
    }


    %extend ResistProfile {
        %rename(_get_polygons) polygons() const;
        %pythoncode %{
            __swig_getmethods__["values"] = _get_polygons
            if _newclass:
                polygons = property(_get_polygons)
        %}
    }

    %extend Mask {
        %rename(__getitem__) at;
        %rename(__len__) length;
    };


    %extend AbstractWaferLayer {
        %rename(__str__) str;
    };


    %extend ResistWaferLayer {
        static std::shared_ptr<ResistWaferLayer> cast(std::shared_ptr<AbstractWaferLayer> base) {
            return std::dynamic_pointer_cast<ResistWaferLayer>(base);
        }
    }


    %extend WaferStack {
        %rename(__getitem__) operator[];
    };
    
}  // namespace oplc


%ignore _ContourBuilderIterator;
%ignore _ContourEngine;


/* Parse the header file to generate wrappers */
%include "opl_physc.h"
%include "opl_interp.h"
%include "opl_geometry.h"
%include "opl_contours.h"
%include "opl_capi.h"
%include "opl_sim.h"
%include "opl_log.h"
