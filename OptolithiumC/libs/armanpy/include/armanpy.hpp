// Copyright (C) 2012 thomas.natschlaeger@gmail.com
// 
// This file is part of the ArmaNpy library.
// It is provided without any warranty of fitness
// for any purpose. You can redistribute this file
// and/or modify it under the terms of the GNU
// Lesser General Public License (LGPL) as published
// by the Free Software Foundation, either version 3
// of the License or (at your option) any later version.
// (see http://www.opensource.org/licenses for more info)

///////////////////////////////////////////////////////////////////////////////
// Define types (templated) to allow wrapping of armadillo types as Python
// objects such that they can be used as base objects of numpy arrays
//

#define INIT_ARMA_CAPSULE( MatT )  \
    ArmaCapsulePyType< MatT >::object.tp_new = PyType_GenericNew; \
    if (PyType_Ready(&ArmaCapsulePyType< MatT >::object) < 0) return;

template< typename MatT >
struct ArmaCapsule {
    PyObject_HEAD
    MatT *mat;
} ;

template< typename MatT >
static void ArmaMat_dealloc( PyObject *self )
{
    //std::cerr << "ArmaMat_dealloc( " << self << " )"<< std::endl;
    //((ArmaMat_Capsule *)self)->mat->print("mat");
    delete ((ArmaCapsule<MatT> *)self)->mat;
    self->ob_type->tp_free( self );
};

template<typename MatT >
class ArmaCapsulePyType {
public:
    static PyTypeObject object;
private:
    MatT _dummy;
};


template< typename MatT > PyTypeObject ArmaCapsulePyType<MatT>::object = { \
    PyObject_HEAD_INIT(NULL)   \
    0, /*ob_size*/             \
    "ArmaCapsule", /*tp_name*/ \
    sizeof( ArmaCapsule< MatT > ), /*tp_basicsize*/ \
    0, /*tp_itemsize*/ \
    ArmaMat_dealloc< MatT >, /*tp_dealloc*/ \
    0, /*tp_print*/ \
    0, /*tp_getattr*/ \
    0, /*tp_setattr*/ \
    0, /*tp_compare*/ \
    0, /*tp_repr*/ \
    0, /*tp_as_number*/ \
    0, /*tp_as_sequence*/ \
    0, /*tp_as_mapping*/ \
    0, /*tp_hash */ \
    0, /*tp_call*/ \
    0, /*tp_str*/ \
    0, /*tp_getattro*/ \
    0, /*tp_setattro*/ \
    0, /*tp_as_buffer*/ \
    Py_TPFLAGS_DEFAULT, /*tp_flags*/ \
    "Internal armadillo capsulation object", /* tp_doc */ \
    };

///////////////////////////////////////////////////////////////////////////////
// Define types (templated) to allow wrapping of std::shared_ptr< arma::... >
// types as Python objects such that they can be used as base objects of numpy
// arrays.
// This is mainly used for return values of the type std::shared_ptr< arma::... >
//

#if defined( ARMANPY_SHARED_PTR )

#define INIT_ARMA_BSPTR_CAPSULE( MatT )  \
    ArmaBsptrCapsulePyType< MatT >::object.tp_new = PyType_GenericNew; \
    if (PyType_Ready(&ArmaBsptrCapsulePyType< MatT >::object) < 0) return;

template< typename MatT >
struct ArmaBsptrCapsule {
    PyObject_HEAD
    std::shared_ptr< MatT > *mat;
} ;

template< typename MatT >
static void ArmaBsptrMat_dealloc( PyObject *self )
{
    //std::cerr << "ArmaBsptrMat_dealloc( " << self << " )"<< std::endl;
    //(*(((ArmaBsptrCapsule<MatT> *)self)->mat))->print("mat");
    delete ((ArmaBsptrCapsule<MatT> *)self)->mat;
    self->ob_type->tp_free( self );
};

template<typename MatT >
class ArmaBsptrCapsulePyType {
public:
    static PyTypeObject object;
private:
    MatT _dummy;
};


template< typename MatT > PyTypeObject ArmaBsptrCapsulePyType<MatT>::object = { \
    PyObject_HEAD_INIT(NULL)   \
    0, /*ob_size*/             \
    "ArmaBsptrCapsule", /*tp_name*/ \
    sizeof( ArmaBsptrCapsule< MatT > ), /*tp_basicsize*/ \
    0, /*tp_itemsize*/ \
    ArmaBsptrMat_dealloc< MatT >, /*tp_dealloc*/ \
    0, /*tp_print*/ \
    0, /*tp_getattr*/ \
    0, /*tp_setattr*/ \
    0, /*tp_compare*/ \
    0, /*tp_repr*/ \
    0, /*tp_as_number*/ \
    0, /*tp_as_sequence*/ \
    0, /*tp_as_mapping*/ \
    0, /*tp_hash */ \
    0, /*tp_call*/ \
    0, /*tp_str*/ \
    0, /*tp_getattro*/ \
    0, /*tp_setattro*/ \
    0, /*tp_as_buffer*/ \
    Py_TPFLAGS_DEFAULT, /*tp_flags*/ \
    "Internal armadillo capsulation object", /* tp_doc */ \
    };

#endif

///////////////////////////////////////////////////////////////////////////////
// Define a template NumpyType which associates the element types like double,
// float, int, etc. with the accoring numpy enums NPY_DOUBLE, NPY_FLOAT and so
// on.
//
// #include <numpy/ndarraytypes.h>
#include <numpy/arrayobject.h>

template< typename elem_type > struct NumpyType { private: elem_type _d; };

#define ASSOCIATE_NUMPY_TYPE( elem_type, npy ) \
    template<> struct NumpyType< elem_type > { static int val; }; \
    int NumpyType< elem_type >::val=npy;

ASSOCIATE_NUMPY_TYPE( double,   NPY_DOUBLE )
ASSOCIATE_NUMPY_TYPE( float,    NPY_FLOAT )
ASSOCIATE_NUMPY_TYPE( int,      NPY_INT )
ASSOCIATE_NUMPY_TYPE( unsigned, NPY_UINT )
ASSOCIATE_NUMPY_TYPE( unsigned char, NPY_UBYTE )
#if defined(ARMA_64BIT_WORD)
ASSOCIATE_NUMPY_TYPE( arma::sword, NPY_INT64 )
ASSOCIATE_NUMPY_TYPE( arma::uword, NPY_UINT64 )
#endif
ASSOCIATE_NUMPY_TYPE( std::complex< double >, NPY_COMPLEX128 )
ASSOCIATE_NUMPY_TYPE( std::complex< float >,  NPY_COMPLEX64 )

template< typename MatT > struct ArmaTypeInfo { private: MatT _d; };
#define ARMA_TYPE_INFO( MatT, nd ) \
    template<> struct ArmaTypeInfo< MatT > { static int type; static int numdim; }; \
    int ArmaTypeInfo< MatT >::type=NumpyType< MatT::elem_type >::val; \
    int ArmaTypeInfo< MatT >::numdim=nd;

ARMA_TYPE_INFO( arma::vec,          1 )
ARMA_TYPE_INFO( arma::fvec,         1 )
ARMA_TYPE_INFO( arma::ivec,         1 )
ARMA_TYPE_INFO( arma::uvec,         1 )
ARMA_TYPE_INFO( arma::uchar_vec,    1 )
#if defined(ARMA_64BIT_WORD)
ARMA_TYPE_INFO( arma::u32_vec,      1 )
ARMA_TYPE_INFO( arma::s32_vec,      1 )
#endif
ARMA_TYPE_INFO( arma::cx_vec,       1 )
ARMA_TYPE_INFO( arma::cx_fvec,      1 )

ARMA_TYPE_INFO( arma::rowvec,       1 )
ARMA_TYPE_INFO( arma::frowvec,      1 )
ARMA_TYPE_INFO( arma::irowvec,      1 )
ARMA_TYPE_INFO( arma::urowvec,      1 )
ARMA_TYPE_INFO( arma::uchar_rowvec, 1 )
#if defined(ARMA_64BIT_WORD)
ARMA_TYPE_INFO( arma::u32_rowvec,   1 )
ARMA_TYPE_INFO( arma::s32_rowvec,   1 )
#endif
ARMA_TYPE_INFO( arma::cx_rowvec,    1 )
ARMA_TYPE_INFO( arma::cx_frowvec,   1 )

ARMA_TYPE_INFO( arma::mat,       2 )
ARMA_TYPE_INFO( arma::fmat,      2 )
ARMA_TYPE_INFO( arma::imat,      2 )
ARMA_TYPE_INFO( arma::umat,      2 )
ARMA_TYPE_INFO( arma::uchar_mat, 2 )
#if defined(ARMA_64BIT_WORD)
ARMA_TYPE_INFO( arma::u32_mat,   2 )
ARMA_TYPE_INFO( arma::s32_mat,   2 )
#endif
ARMA_TYPE_INFO( arma::cx_mat,    2 )
ARMA_TYPE_INFO( arma::cx_fmat,   2 )

ARMA_TYPE_INFO( arma::cube,       3 )
ARMA_TYPE_INFO( arma::fcube,      3 )
ARMA_TYPE_INFO( arma::icube,      3 )
ARMA_TYPE_INFO( arma::ucube,      3 )
ARMA_TYPE_INFO( arma::uchar_cube, 3 )
#if defined(ARMA_64BIT_WORD)
ARMA_TYPE_INFO( arma::u32_cube,   3 )
ARMA_TYPE_INFO( arma::s32_cube,   3 )
#endif
ARMA_TYPE_INFO( arma::cx_cube,    3 )
ARMA_TYPE_INFO( arma::cx_fcube,   3 )

///////////////////////////////////////////////////////////////////////////////
// Function to modify conversion and warning behaviour.
//

static bool armanpy_allow_conversion_flag   = false;
static bool armanpy_warn_on_conversion_flag = true;

/*
void armanpy_conversion( bool allowed =false, bool warnings = true ) {
    armanpy_allow_conversion_flag   = allowed;
    armanpy_warn_on_conversion_flag = warnings;
};
*/

///////////////////////////////////////////////////////////////////////////////
// Code for typechecks, typemaps etc.
//

//#include "armanpy_1d.hpp"
