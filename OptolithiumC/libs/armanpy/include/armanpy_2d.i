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

%fragment( "armanpy_mat_typemaps", "header", fragment="armanpy_typemaps" )
{
    template< typename MatT >
    bool armanpy_typecheck_mat_with_conversion( PyObject* input , int nd )
    {
        typedef typename MatT::elem_type eT;
        PyArrayObject* array=NULL;
        int is_new_object=0;
        if( armanpy_allow_conversion_flag ) {
            array = obj_to_array_fortran_allow_conversion( input, NumpyType<eT>::val, &is_new_object );
            if ( !array || !require_dimensions( array, nd ) ) return false;
            return true;
        } else {
            array = obj_to_array_no_conversion( input, NumpyType<eT>::val );
            if( !array )                           return false;
            if( !require_dimensions( array, nd ) ) return false;
            if( !array_is_fortran(array) )         return false;
            return true;
        }
    }

    template< typename MatT >
    PyArrayObject* armanpy_to_mat_with_conversion( PyObject* input , int nd )
    {
        typedef typename MatT::elem_type eT;
        PyArrayObject* array=NULL;
        int is_new_object=0;
        if( armanpy_allow_conversion_flag ) {
            array = obj_to_array_fortran_allow_conversion( input, NumpyType<eT>::val, &is_new_object );
            if ( !array || !require_dimensions( array, nd ) ) return NULL;
            if( armanpy_warn_on_conversion_flag && is_new_object ) {
                PyErr_WarnEx( PyExc_RuntimeWarning,
                    "Argument converted (copied) to FORTRAN-contiguous array.", 1 );
            }
            return array;
        } else {
            array = obj_to_array_no_conversion( input, NumpyType<eT>::val );
            if ( !array || !require_dimensions( array, nd ) )return NULL;
                if( !array_is_fortran(array) ) {
                    PyErr_SetString(PyExc_TypeError,
                        "Array must be FORTRAN contiguous."\
                        "  A non-FORTRAN-contiguous array was given");
                    return NULL;
               }
            return array;
        }
    }

    template< typename MatT >
    void armanpy_mat_as_numpy_with_shared_memory( MatT *m, PyObject* input )
    {
        typedef typename MatT::elem_type eT;
        PyArrayObject* ary= (PyArrayObject*)input;
        array_dimensions(ary)[0] = m->n_rows;
        array_dimensions(ary)[1] = m->n_cols;
        array_strides(ary)[0]    = sizeof( eT );
        array_strides(ary)[1]    = sizeof( eT ) * m->n_rows;
        if(  m->mem != (eT*)array_data(ary) ) {
            // if( ! m->uses_local_mem() ) {
                // 1. We do not need the memory at array_data(ary) anymore
                //    This can be simply removed by PyArray_free( array_data(ary) );
                array_free_data( array_data(ary) );

                // 2. We should "implant" the m->mem into array_data(ary)
                //    Here we use the trick from http://blog.enthought.com/?p=62
                // array_flags(ary) = array_flags(ary) & ~( NPY_ARRAY_OWNDATA );
                array_clear_flags( ary, NPY_ARRAY_OWNDATA );
                ArmaCapsule< MatT > *capsule;
                capsule      = PyObject_New( ArmaCapsule< MatT >, &ArmaCapsulePyType< MatT >::object );
                capsule->mat = m;
                //ary->data = (char *)capsule->mat->mem;
                array_set_data( ary, capsule->mat->mem );
                array_set_base_object( ary, capsule );
            //} else {
                // Here we just copy a few bytes, as local memory of arma is typically small
            //    memcpy ( array_data(ary), m->mem, sizeof(eT) * m->n_elem );
            //    delete m;
            //}
        } else {
            // Memory was not changed at all; i.e. all modifications were done on the original
            // memory brought by the input numpy array. So we just delete the arma array
            // which does not free the memory as it was constructed with the aux memory constructor
            delete m;
        }
    }

    template< typename MatT >
    bool armanpy_numpy_as_mat_with_shared_memory( PyObject* input, MatT **m )
    {
        typedef typename MatT::elem_type eT;
        PyArrayObject* array = obj_to_array_no_conversion( input, NumpyType<eT>::val );
        if ( !array || !require_dimensions(array, 2) ) return false;
        if( ! ( PyArray_FLAGS(array) & NPY_ARRAY_OWNDATA ) ) {
            PyErr_SetString(PyExc_TypeError, "Array must own its data.");
            return false;
        }
        if ( !array_is_fortran(array) ) {
            PyErr_SetString(PyExc_TypeError,
                "Array must be FORTRAN contiguous.  A non-FORTRAN-contiguous array was given");
            return false;
        }
        arma::uword r = arma::uword( array_dimensions(array)[0] );
        arma::uword c = arma::uword( array_dimensions(array)[1] );
        *m = new MatT( (eT*)array_data(array), r, c, false, false );
        return true;
    }

    template< typename MatT >
    PyObject* armanpy_mat_copy_to_numpy( MatT * m )
    {
        typedef typename MatT::elem_type eT;
        npy_intp dims[2] = { npy_intp(m->n_rows), npy_intp(m->n_cols) };
        PyObject* array = PyArray_EMPTY( ArmaTypeInfo< MatT >::numdim, dims, ArmaTypeInfo< MatT >::type, true);
        if ( !array || !array_is_fortran( array ) ) {
            PyErr_SetString( PyExc_TypeError, "Creation of 2-dimensional return array failed" );
            return NULL;
        }
        std::copy( m->begin(), m->end(), reinterpret_cast<eT*>(array_data(array)) );
        return array;
     }

#if defined(ARMANPY_SHARED_PTR)

    template< typename MatT >
    PyObject* armanpy_mat_bsptr_as_numpy_with_shared_memory( std::shared_ptr< MatT > m )
    {
        typedef typename MatT::elem_type eT;
        npy_intp dims[2] = { 1, 1 };
        PyArrayObject* ary = (PyArrayObject*)PyArray_EMPTY(2, dims, NumpyType<eT>::val, true);
        if ( !ary || !array_is_fortran(ary) ) { return NULL; }

        array_dimensions(ary)[0] = m->n_rows;
        array_dimensions(ary)[1] = m->n_cols;
        array_strides(ary)[0]    = sizeof(eT);
        array_strides(ary)[1]    = sizeof(eT) * m->n_rows;

        // 1. We do not need the memory at array_data(ary) anymore
        //    This can be simply removed by PyArray_free( array_data(ary) );
        array_free_data( array_data(ary) );

        // 2. We should "implant" the m->mem into array_data(ary)
        //    Here we use the trick from http://blog.enthought.com/?p=62
        // array_flags(ary) = array_flags(ary) & ~( NPY_ARRAY_OWNDATA );
        array_clear_flags( ary, NPY_ARRAY_OWNDATA );

        ArmaBsptrCapsule< MatT > *capsule;
        capsule      = PyObject_New( ArmaBsptrCapsule< MatT >, &ArmaBsptrCapsulePyType< MatT >::object );
        capsule->mat = new std::shared_ptr< MatT >();
        // This currently works, but this may break with future versions of numpy
        // ary->data = (char *)( m->mem );
        array_set_data( ary, m->mem );
        (*(capsule->mat)) = m;
        array_set_base_object( ary, capsule );
        return (PyObject*)ary;
    }

#endif

}

//////////////////////////////////////////////////////////////////////////
// BY VALUE ARGs for 2D arrays
//////////////////////////////////////////////////////////////////////////

%define %armanpy_mat_byvalue_typemaps( ARMA_MAT_TYPE )

    %typemap( typecheck, precedence=SWIG_TYPECHECK_FLOAT_ARRAY )
        ( const ARMA_MAT_TYPE   ) ( PyArrayObject* array=NULL ),
        (       ARMA_MAT_TYPE   ) ( PyArrayObject* array=NULL )
    {
        $1 = armanpy_basic_typecheck< ARMA_MAT_TYPE >( $input, false );
    }

    %typemap( in, fragment="armanpy_mat_typemaps" )
        ( const ARMA_MAT_TYPE   ) ( PyArrayObject* array=NULL ),
        (       ARMA_MAT_TYPE   ) ( PyArrayObject* array=NULL )
    {
        if( ! armanpy_basic_typecheck< ARMA_MAT_TYPE >( $input, true ) ) SWIG_fail;
        array = obj_to_array_no_conversion( $input, ArmaTypeInfo< ARMA_MAT_TYPE >::type );
        if( !array ) SWIG_fail;
        $1 = ARMA_MAT_TYPE( ( ARMA_MAT_TYPE::elem_type *)array_data(array), array_dimensions(array)[0], array_dimensions(array)[1], false );
    }

    %typemap( argout )
        ( const ARMA_MAT_TYPE   ),
        (       ARMA_MAT_TYPE   )
    {
    }

    %typemap( freearg )
        ( const ARMA_MAT_TYPE   ),
        (       ARMA_MAT_TYPE   )
    {
    }

%enddef

%armanpy_mat_byvalue_typemaps( arma::Mat< double > )
%armanpy_mat_byvalue_typemaps( arma::Mat< float >  )
%armanpy_mat_byvalue_typemaps( arma::Mat< int > )
%armanpy_mat_byvalue_typemaps( arma::Mat< unsigned >  )
%armanpy_mat_byvalue_typemaps( arma::Mat< arma::sword >  )
%armanpy_mat_byvalue_typemaps( arma::Mat< arma::uword >  )
%armanpy_mat_byvalue_typemaps( arma::Mat< arma::cx_double >  )
%armanpy_mat_byvalue_typemaps( arma::Mat< arma::cx_float >  )
%armanpy_mat_byvalue_typemaps( arma::Mat< std::complex< double > >  )
%armanpy_mat_byvalue_typemaps( arma::Mat< std::complex< float > >  )
%armanpy_mat_byvalue_typemaps( arma::mat )
%armanpy_mat_byvalue_typemaps( arma::fmat )
%armanpy_mat_byvalue_typemaps( arma::imat )
%armanpy_mat_byvalue_typemaps( arma::umat )
%armanpy_mat_byvalue_typemaps( arma::uchar_mat )
%armanpy_mat_byvalue_typemaps( arma::u32_mat )
%armanpy_mat_byvalue_typemaps( arma::s32_mat )
%armanpy_mat_byvalue_typemaps( arma::cx_mat )
%armanpy_mat_byvalue_typemaps( arma::cx_fmat )

//////////////////////////////////////////////////////////////////////////
// CONST REF/PTR ARGs for 2D arrays
//////////////////////////////////////////////////////////////////////////

%define %armanpy_mat_const_ref_typemaps( ARMA_MAT_TYPE )

    %typemap( typecheck, precedence=SWIG_TYPECHECK_FLOAT_ARRAY )
        ( const ARMA_MAT_TYPE & ) ( PyArrayObject* array=NULL ),
        ( const ARMA_MAT_TYPE * ) ( PyArrayObject* array=NULL )
    {
        $1 = armanpy_basic_typecheck< ARMA_MAT_TYPE >( $input, false );
    }

    %typemap( in, fragment="armanpy_mat_typemaps" )
        ( const ARMA_MAT_TYPE & ) ( PyArrayObject* array=NULL ),
        ( const ARMA_MAT_TYPE * ) ( PyArrayObject* array=NULL )
    {
        if( ! armanpy_basic_typecheck< ARMA_MAT_TYPE >( $input, true ) ) SWIG_fail;
        array = obj_to_array_no_conversion( $input, ArmaTypeInfo< ARMA_MAT_TYPE >::type );
        if( !array ) SWIG_fail;
        $1 = new ARMA_MAT_TYPE( ( ARMA_MAT_TYPE::elem_type *)array_data(array),
                                arma::uword( array_dimensions(array)[0] ), arma::uword( array_dimensions(array)[1] ), false );
    }

    %typemap( argout )
        ( const ARMA_MAT_TYPE & ),
        ( const ARMA_MAT_TYPE * )
    {
    // NOOP
    }

    %typemap( freearg )
        ( const ARMA_MAT_TYPE & ),
        ( const ARMA_MAT_TYPE * )
    {
        if( array$argnum ) {
            delete $1;
        }
    }

%enddef

%armanpy_mat_const_ref_typemaps( arma::Mat< double > )
%armanpy_mat_const_ref_typemaps( arma::Mat< float >  )
%armanpy_mat_const_ref_typemaps( arma::Mat< int > )
%armanpy_mat_const_ref_typemaps( arma::Mat< unsigned >  )
%armanpy_mat_const_ref_typemaps( arma::Mat< arma::sword >  )
%armanpy_mat_const_ref_typemaps( arma::Mat< arma::uword >  )
%armanpy_mat_const_ref_typemaps( arma::Mat< arma::cx_double >  )
%armanpy_mat_const_ref_typemaps( arma::Mat< arma::cx_float >  )
%armanpy_mat_const_ref_typemaps( arma::Mat< std::complex< double > >  )
%armanpy_mat_const_ref_typemaps( arma::Mat< std::complex< float > >  )
%armanpy_mat_const_ref_typemaps( arma::mat )
%armanpy_mat_const_ref_typemaps( arma::fmat )
%armanpy_mat_const_ref_typemaps( arma::imat )
%armanpy_mat_const_ref_typemaps( arma::umat )
%armanpy_mat_const_ref_typemaps( arma::uchar_mat )
%armanpy_mat_const_ref_typemaps( arma::u32_mat )
%armanpy_mat_const_ref_typemaps( arma::s32_mat )
%armanpy_mat_const_ref_typemaps( arma::cx_mat )
%armanpy_mat_const_ref_typemaps( arma::cx_fmat )

//////////////////////////////////////////////////////////////////////////
// Typemaps for input-output arguments. That is for arguments which are
// potentialliy modified in place.
//////////////////////////////////////////////////////////////////////////

// A macor for generating the typemaps for one matrix type
%define %armanpy_mat_ref_typemaps( ARMA_MAT_TYPE )

    %typemap( typecheck, precedence=SWIG_TYPECHECK_FLOAT_ARRAY )
        ( ARMA_MAT_TYPE &)
    {
        $1 = armanpy_basic_typecheck< ARMA_MAT_TYPE >( $input, false, true );
    }

    %typemap( in, fragment="armanpy_mat_typemaps" )
        ( ARMA_MAT_TYPE &)
    {
        if( ! armanpy_basic_typecheck< ARMA_MAT_TYPE >( $input, true, true )            ) SWIG_fail;
        if( ! armanpy_numpy_as_mat_with_shared_memory< ARMA_MAT_TYPE >( $input, &($1) ) ) SWIG_fail;
    }

    %typemap( argout, fragment="armanpy_mat_typemaps" )
        ( ARMA_MAT_TYPE & )
    {
        armanpy_mat_as_numpy_with_shared_memory( $1, $input );
    }

    %typemap( freearg )
        ( ARMA_MAT_TYPE & )
    {
       // NOOP
    }

%enddef

%armanpy_mat_ref_typemaps( arma::Mat< double > )
%armanpy_mat_ref_typemaps( arma::Mat< float >  )
%armanpy_mat_ref_typemaps( arma::Mat< int > )
%armanpy_mat_ref_typemaps( arma::Mat< unsigned >  )
%armanpy_mat_ref_typemaps( arma::Mat< arma::sword >  )
%armanpy_mat_ref_typemaps( arma::Mat< arma::uword >  )
%armanpy_mat_ref_typemaps( arma::Mat< arma::cx_double >  )
%armanpy_mat_ref_typemaps( arma::Mat< arma::cx_float >  )
%armanpy_mat_ref_typemaps( arma::Mat< std::complex< double > >  )
%armanpy_mat_ref_typemaps( arma::Mat< std::complex< float > >  )
%armanpy_mat_ref_typemaps( arma::mat )
%armanpy_mat_ref_typemaps( arma::fmat )
%armanpy_mat_ref_typemaps( arma::imat )
%armanpy_mat_ref_typemaps( arma::umat )
%armanpy_mat_ref_typemaps( arma::uchar_mat )
%armanpy_mat_ref_typemaps( arma::u32_mat )
%armanpy_mat_ref_typemaps( arma::s32_mat )
%armanpy_mat_ref_typemaps( arma::cx_mat )
%armanpy_mat_ref_typemaps( arma::cx_fmat )

//////////////////////////////////////////////////////////////////////////
// Typemaps for return by value functions/methods
//////////////////////////////////////////////////////////////////////////

%define %armanpy_mat_return_by_value_typemaps( ARMA_MAT_TYPE )
    %typemap( out )
        ( ARMA_MAT_TYPE )
    {
      PyObject* array = armanpy_mat_copy_to_numpy< ARMA_MAT_TYPE >( &$1 );
      if ( !array ) SWIG_fail;
      $result = SWIG_Python_AppendOutput($result, array);
    }
%enddef

%armanpy_mat_return_by_value_typemaps( arma::Mat< double > )
%armanpy_mat_return_by_value_typemaps( arma::Mat< float >  )
%armanpy_mat_return_by_value_typemaps( arma::Mat< int > )
%armanpy_mat_return_by_value_typemaps( arma::Mat< unsigned >  )
%armanpy_mat_return_by_value_typemaps( arma::Mat< arma::sword >  )
%armanpy_mat_return_by_value_typemaps( arma::Mat< arma::uword >  )
%armanpy_mat_return_by_value_typemaps( arma::Mat< arma::cx_double >  )
%armanpy_mat_return_by_value_typemaps( arma::Mat< arma::cx_float >  )
%armanpy_mat_return_by_value_typemaps( arma::Mat< std::complex< double > >  )
%armanpy_mat_return_by_value_typemaps( arma::Mat< std::complex< float > >  )
%armanpy_mat_return_by_value_typemaps( arma::mat )
%armanpy_mat_return_by_value_typemaps( arma::fmat )
%armanpy_mat_return_by_value_typemaps( arma::imat )
%armanpy_mat_return_by_value_typemaps( arma::umat )
%armanpy_mat_return_by_value_typemaps( arma::uchar_mat )
%armanpy_mat_return_by_value_typemaps( arma::u32_mat )
%armanpy_mat_return_by_value_typemaps( arma::s32_mat )
%armanpy_mat_return_by_value_typemaps( arma::cx_mat )
%armanpy_mat_return_by_value_typemaps( arma::cx_fmat )

%define %armanpy_mat_return_by_reference_typemaps( ARMA_MAT_TYPE )
    %typemap( out )
        ( const ARMA_MAT_TYPE & ),
        (       ARMA_MAT_TYPE & )
    {
      PyObject* array = armanpy_mat_copy_to_numpy< ARMA_MAT_TYPE >( $1 );
      if ( !array ) SWIG_fail;
      $result = SWIG_Python_AppendOutput($result, array);
    }
%enddef

%armanpy_mat_return_by_reference_typemaps( arma::Mat< double > )
%armanpy_mat_return_by_reference_typemaps( arma::Mat< float >  )
%armanpy_mat_return_by_reference_typemaps( arma::Mat< int > )
%armanpy_mat_return_by_reference_typemaps( arma::Mat< unsigned >  )
%armanpy_mat_return_by_reference_typemaps( arma::Mat< arma::sword >  )
%armanpy_mat_return_by_reference_typemaps( arma::Mat< arma::uword >  )
%armanpy_mat_return_by_reference_typemaps( arma::Mat< arma::cx_double >  )
%armanpy_mat_return_by_reference_typemaps( arma::Mat< arma::cx_float >  )
%armanpy_mat_return_by_reference_typemaps( arma::Mat< std::complex< double > >  )
%armanpy_mat_return_by_reference_typemaps( arma::Mat< std::complex< float > >  )
%armanpy_mat_return_by_reference_typemaps( arma::mat )
%armanpy_mat_return_by_reference_typemaps( arma::fmat )
%armanpy_mat_return_by_reference_typemaps( arma::imat )
%armanpy_mat_return_by_reference_typemaps( arma::umat )
%armanpy_mat_return_by_reference_typemaps( arma::uchar_mat )
%armanpy_mat_return_by_reference_typemaps( arma::u32_mat )
%armanpy_mat_return_by_reference_typemaps( arma::s32_mat )
%armanpy_mat_return_by_reference_typemaps( arma::cx_mat )
%armanpy_mat_return_by_reference_typemaps( arma::cx_fmat )

//////////////////////////////////////////////////////////////////////////
// Typemaps for return by std::shared_ptr< ... > functions/methods
//////////////////////////////////////////////////////////////////////////

#if defined(ARMANPY_SHARED_PTR)

%define %armanpy_mat_return_by_bsptr_typemaps( ARMA_MAT_TYPE )
    %typemap( out , fragment="armanpy_mat_typemaps" )
        ( std::shared_ptr< ARMA_MAT_TYPE > )
    {
      PyObject* array = armanpy_mat_bsptr_as_numpy_with_shared_memory< ARMA_MAT_TYPE >( $1 );
      if ( !array ) { SWIG_fail; }
      $result = SWIG_Python_AppendOutput($result, array);
    }
%enddef

%armanpy_mat_return_by_bsptr_typemaps( arma::Mat< double > )
%armanpy_mat_return_by_bsptr_typemaps( arma::Mat< float >  )
%armanpy_mat_return_by_bsptr_typemaps( arma::Mat< int > )
%armanpy_mat_return_by_bsptr_typemaps( arma::Mat< unsigned >  )
%armanpy_mat_return_by_bsptr_typemaps( arma::Mat< arma::sword >  )
%armanpy_mat_return_by_bsptr_typemaps( arma::Mat< arma::uword >  )
%armanpy_mat_return_by_bsptr_typemaps( arma::Mat< arma::cx_double >  )
%armanpy_mat_return_by_bsptr_typemaps( arma::Mat< arma::cx_float >  )
%armanpy_mat_return_by_bsptr_typemaps( arma::Mat< std::complex< double > >  )
%armanpy_mat_return_by_bsptr_typemaps( arma::Mat< std::complex< float > >  )
%armanpy_mat_return_by_bsptr_typemaps( arma::mat )
%armanpy_mat_return_by_bsptr_typemaps( arma::fmat )
%armanpy_mat_return_by_bsptr_typemaps( arma::imat )
%armanpy_mat_return_by_bsptr_typemaps( arma::umat )
%armanpy_mat_return_by_bsptr_typemaps( arma::uchar_mat )
%armanpy_mat_return_by_bsptr_typemaps( arma::u32_mat )
%armanpy_mat_return_by_bsptr_typemaps( arma::s32_mat )
%armanpy_mat_return_by_bsptr_typemaps( arma::cx_mat )
%armanpy_mat_return_by_bsptr_typemaps( arma::cx_fmat )

#endif
