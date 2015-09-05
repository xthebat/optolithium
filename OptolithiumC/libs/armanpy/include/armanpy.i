// -*- mode: c++; fill-column: 80 -*-

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

// Typemaps for converting between armadillo and numpy arrays.

// numpy.i is from https://github.com/numpy/numpy/tree/master/doc/swig
%include "numpy.i"

%fragment("ArmaNumPy_Backward_Compatibility", "header")
{
%#if NPY_API_VERSION < 0x00000007
%#define NPY_ARRAY_OWNDATA               NPY_OWNDATA
%#define array_set_base_object(arr, obj) ( PyArray_BASE(arr) = (PyObject *)obj )
%#define array_set_data( arr, mem )      ( ((PyArrayObject*)arr)->data = (char*)mem )
%#define array_clear_flags( arr, flg )   (((PyArrayObject*)arr)->flags) = ( (((PyArrayObject*)arr)->flags) & ~( flg ) )
%#define array_free_data( arr )          PyArray_free( arr )
%#else
%#define array_set_base_object(arr, obj) PyArray_SetBaseObject(arr, (PyObject *)obj )
%#define array_set_data( arr, mem )      ( ((PyArrayObject_fields*)arr)->data = (char*)mem )
%#define array_clear_flags( arr, flg )   PyArray_CLEARFLAGS( arr, flg )
%#define array_free_data( arr )          PyArray_free( arr )
%#endif
}

%fragment( "armanpy_typemaps", "header", fragment="NumPy_Fragments", fragment="ArmaNumPy_Backward_Compatibility" )
{

    template< typename ArmaT >
    bool armanpy_basic_typecheck( PyObject* input, bool raise, bool check_own_data = false )
    {
        /***/
        if( armanpy_allow_conversion_flag ) {
            PyErr_SetString( PyExc_TypeError, "Conversion not supported anymore. Please wrap your data using numpy.array( ... ) and call armanpy_conversion( false )." );
            return false;
        } else {
            const int req_type = ArmaTypeInfo<ArmaT>::type;
            if( ! is_array( input ) ) {
                const char * required = typecode_string( req_type );
                const char * actual   = pytype_string( input );
                if( raise ) PyErr_Format( PyExc_TypeError, "Array of type '%s' required. A '%s' was given.", required, actual );
                return false;
            }
            PyArrayObject* array = (PyArrayObject*)input;
            if( ! PyArray_EquivTypenums( array_type( array ), req_type ) ) {
                const char * required = typecode_string( req_type );
                const char * actual   = typecode_string( array_type(array) );
                if( raise ) PyErr_Format( PyExc_TypeError, "Array of type '%s' required. Array of type '%s' was given.", required, actual );
                return false;                
            }
            if( ! require_dimensions( array, ArmaTypeInfo<ArmaT>::numdim ) ) {
                if( raise ) PyErr_Format( PyExc_TypeError, "Array with %i dimension required. A %i-dimensional array was given.", ArmaTypeInfo<ArmaT>::numdim, array_numdims( array ) );
                return false;
            }
            if( ArmaTypeInfo<ArmaT>::numdim < 2 ) {
                if( ! ( array_is_fortran(array) || array_is_contiguous(array) ) ) {
                    if( raise ) PyErr_SetString( PyExc_TypeError, "Array must be contiguous. A non-contiguous array was given." );
                    return false;
                }
            } else {
                if( ! array_is_fortran(array) ) {
                    if( raise ) PyErr_SetString( PyExc_TypeError, "Array must be FORTRAN contiguous. A non-FORTRAN-contiguous array was given." );
                    return false;
                }
            }
            if( check_own_data && ( ! ( PyArray_FLAGS(array) & NPY_ARRAY_OWNDATA ) ) ) {
                if( raise ) PyErr_SetString( PyExc_TypeError, "Array must own its data. Please wrap your data using numpy.array( ... ).");
                return false;
            }
            if( sizeof(npy_intp) > sizeof(arma::uword) ) {
                npy_intp  ndim = array_numdims(array);
                npy_intp *dims = array_dimensions(array);
                npy_intp max_arma_uword = npy_intp( std::numeric_limits< arma::uword >::max() ); // As there are more byte for npy_intp this is no problem
                for( npy_intp i=0; i < ndim; i++ ) {
                    if( dims[i] > max_arma_uword ) {
                        if( raise ) PyErr_Format( PyExc_TypeError, "Dimension %li of array to large (%li). Only %li elements per dimension supported.", i, dims[i], max_arma_uword );
                        return false;
                    };
                }
            }
            return true;
        }
    }
}

#define ARMANPY_SHARED_PTR

%header %{
    #include <algorithm>
    #include <armadillo>
    #include <iostream>
    #include <stdio.h>
    #include <string.h>
    #include <complex>
%}

#if defined( ARMANPY_SHARED_PTR )
    %header %{
        #include <memory>
        #define ARMANPY_SHARED_PTR
    %}
#else
    %header %{
        #undef ARMANPY_SHARED_PTR
    %}
#endif

%header %{
    #include "armanpy.hpp"
%}

%init %{

// This must be called at the start of each module to import numpy.
import_array();

INIT_ARMA_CAPSULE( arma::Col< double >      )
INIT_ARMA_CAPSULE( arma::Col< float >       )
INIT_ARMA_CAPSULE( arma::Col< int >         )
INIT_ARMA_CAPSULE( arma::Col< unsigned >    )
#if defined(ARMA_64BIT_WORD)
    INIT_ARMA_CAPSULE( arma::Col< arma::sword > )
    INIT_ARMA_CAPSULE( arma::Col< arma::uword > )
#endif
INIT_ARMA_CAPSULE( arma::Col< std::complex< double > > )
INIT_ARMA_CAPSULE( arma::Col< std::complex< float > >  )


INIT_ARMA_CAPSULE( arma::Row< double >      )
INIT_ARMA_CAPSULE( arma::Row< float >       )
INIT_ARMA_CAPSULE( arma::Row< int >         )
INIT_ARMA_CAPSULE( arma::Row< unsigned >    )
#if defined(ARMA_64BIT_WORD)
    INIT_ARMA_CAPSULE( arma::Row< arma::sword > )
    INIT_ARMA_CAPSULE( arma::Row< arma::uword > )
#endif
INIT_ARMA_CAPSULE( arma::Row< std::complex< double > > )
INIT_ARMA_CAPSULE( arma::Row< std::complex< float > >  )


INIT_ARMA_CAPSULE( arma::Mat< double >      )
INIT_ARMA_CAPSULE( arma::Mat< float >       )
INIT_ARMA_CAPSULE( arma::Mat< int >         )
INIT_ARMA_CAPSULE( arma::Mat< unsigned >    )
#if defined(ARMA_64BIT_WORD)
    INIT_ARMA_CAPSULE( arma::Mat< arma::sword > )
    INIT_ARMA_CAPSULE( arma::Mat< arma::uword > )
#endif
INIT_ARMA_CAPSULE( arma::Mat< std::complex< double > > )
INIT_ARMA_CAPSULE( arma::Mat< std::complex< float > >  )

INIT_ARMA_CAPSULE( arma::Cube< double >      )
INIT_ARMA_CAPSULE( arma::Cube< float >       )
INIT_ARMA_CAPSULE( arma::Cube< int >         )
INIT_ARMA_CAPSULE( arma::Cube< unsigned >    )
#if defined(ARMA_64BIT_WORD)
    INIT_ARMA_CAPSULE( arma::Cube< arma::sword > )
    INIT_ARMA_CAPSULE( arma::Cube< arma::uword > )
#endif
INIT_ARMA_CAPSULE( arma::Cube< std::complex< double > > )
INIT_ARMA_CAPSULE( arma::Cube< std::complex< float > >  )

/////////////////////////////////////////////////////////////

#if defined( ARMANPY_SHARED_PTR )

INIT_ARMA_BSPTR_CAPSULE( arma::Col< double >      )
INIT_ARMA_BSPTR_CAPSULE( arma::Col< float >       )
INIT_ARMA_BSPTR_CAPSULE( arma::Col< int >         )
INIT_ARMA_BSPTR_CAPSULE( arma::Col< unsigned >    )
#if defined(ARMA_64BIT_WORD)
    INIT_ARMA_BSPTR_CAPSULE( arma::Col< arma::sword > )
    INIT_ARMA_BSPTR_CAPSULE( arma::Col< arma::uword > )
#endif
INIT_ARMA_BSPTR_CAPSULE( arma::Col< std::complex< double > > )
INIT_ARMA_BSPTR_CAPSULE( arma::Col< std::complex< float > >  )


INIT_ARMA_BSPTR_CAPSULE( arma::Row< double >      )
INIT_ARMA_BSPTR_CAPSULE( arma::Row< float >       )
INIT_ARMA_BSPTR_CAPSULE( arma::Row< int >         )
INIT_ARMA_BSPTR_CAPSULE( arma::Row< unsigned >    )
#if defined(ARMA_64BIT_WORD)
    INIT_ARMA_BSPTR_CAPSULE( arma::Row< arma::sword > )
    INIT_ARMA_BSPTR_CAPSULE( arma::Row< arma::uword > )
#endif
INIT_ARMA_BSPTR_CAPSULE( arma::Row< std::complex< double > > )
INIT_ARMA_BSPTR_CAPSULE( arma::Row< std::complex< float > >  )


INIT_ARMA_BSPTR_CAPSULE( arma::Mat< double >      )
INIT_ARMA_BSPTR_CAPSULE( arma::Mat< float >       )
INIT_ARMA_BSPTR_CAPSULE( arma::Mat< int >         )
INIT_ARMA_BSPTR_CAPSULE( arma::Mat< unsigned >    )
#if defined(ARMA_64BIT_WORD)
    INIT_ARMA_BSPTR_CAPSULE( arma::Mat< arma::sword > )
    INIT_ARMA_BSPTR_CAPSULE( arma::Mat< arma::uword > )
#endif
INIT_ARMA_BSPTR_CAPSULE( arma::Mat< std::complex< double > > )
INIT_ARMA_BSPTR_CAPSULE( arma::Mat< std::complex< float > >  )

INIT_ARMA_BSPTR_CAPSULE( arma::Cube< double >      )
INIT_ARMA_BSPTR_CAPSULE( arma::Cube< float >       )
INIT_ARMA_BSPTR_CAPSULE( arma::Cube< int >         )
INIT_ARMA_BSPTR_CAPSULE( arma::Cube< unsigned >    )
#if defined(ARMA_64BIT_WORD)
    INIT_ARMA_BSPTR_CAPSULE( arma::Cube< arma::sword > )
    INIT_ARMA_BSPTR_CAPSULE( arma::Cube< arma::uword > )
#endif
INIT_ARMA_BSPTR_CAPSULE( arma::Cube< std::complex< double > > )
INIT_ARMA_BSPTR_CAPSULE( arma::Cube< std::complex< float > >  )

#endif

%}

%include "armanpy_1d.i"
%include "armanpy_2d.i"
%include "armanpy_3d.i"





