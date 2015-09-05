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

%fragment( "armanpy_vec_typemaps", "header", fragment="armanpy_typemaps" )
{

    ///////////////////////////////////////// numpy -> arma ////////////////////////////////////////

    template< typename VecT >
    bool armanpy_numpy_as_vec_with_shared_memory( PyObject* input, VecT **m )
    {
        typedef typename VecT::elem_type eT;
        PyArrayObject* array = obj_to_array_no_conversion( input, NumpyType<eT>::val );
        if ( !array || !require_dimensions(array, 1) ) return false;
        if( ! ( PyArray_FLAGS(array) & NPY_ARRAY_OWNDATA ) ) {
            PyErr_SetString(PyExc_TypeError, "Array must own its data.");
            return false;
        }
        if ( !array_is_contiguous(array) ) {
            PyErr_SetString(PyExc_TypeError,
                "Array must be FORTRAN contiguous.  A non-FORTRAN-contiguous array was given");
            return false;
        }
        arma::uword p = arma::uword( array_dimensions(array)[0] );
        *m = new VecT( (eT *)array_data(array), p, false, false );
        return true;
    }

    /////////////////////////////////////// arma -> numpy ////////////////////////////////////////////

    template< typename VecT >
    void armanpy_vec_as_numpy_with_shared_memory( VecT *m, PyObject* input )
    {
        typedef typename VecT::elem_type eT;
        PyArrayObject* ary= (PyArrayObject*)input;
        array_dimensions(ary)[0] = m->n_elem;
        array_strides(ary)[0]    = sizeof(eT);
        if(  m->mem != ( eT *)array_data(ary) ) {
            // if( ! m->uses_local_mem() ) {
                // 1. We do not need the memory at array_data(ary) anymore
                //    This can be simply removed by PyArray_free( array_data(ary) );
                array_free_data( array_data(ary) );

                // 2. We should "implant" the m->mem into array_data(ary)
                //    Here we use the trick from http://blog.enthought.com/?p=62
                array_clear_flags( ary, NPY_ARRAY_OWNDATA );
                ArmaCapsule< VecT > *capsule;
                capsule      = PyObject_New( ArmaCapsule< VecT >, &ArmaCapsulePyType< VecT >::object );
                capsule->mat = m;
                array_set_data( ary, capsule->mat->mem );
                array_set_base_object( ary, capsule );
            //} else {
                // Here we just copy a few bytes, as local memory of arma is typically small
            //    memcpy ( array_data(ary), m->mem, sizeof( eT ) * m->n_elem );
            //    delete m;
            //}
        } else {
            // Memory was not changed at all; i.e. all modifications were done on the original
            // memory brought by the input numpy array. So we just delete the arma array
            // which does not free the memory as it was constructed with the aux memory constructor
            delete m;
        }
    }

    template< typename VecT >
    PyObject* armanpy_vec_copy_to_numpy( VecT * m )
    {
        typedef typename VecT::elem_type eT;
        npy_intp dims[1] = { npy_intp(m->n_elem) };
        PyObject* array = PyArray_EMPTY( ArmaTypeInfo< VecT >::numdim, dims, ArmaTypeInfo< VecT >::type, true);
        if ( !array || !array_is_contiguous( array ) ) {
            PyErr_SetString( PyExc_TypeError, "Creation of 1-dimensional return array failed" );
            return NULL;
        }
        std::copy( m->begin(), m->end(), reinterpret_cast< eT *>(array_data(array)) );
        return array;
     }

#if defined(ARMANPY_SHARED_PTR)

    template< typename VecT >
    PyObject* armanpy_vec_bsptr_as_numpy_with_shared_memory( std::shared_ptr< VecT > m )
    { 
        typedef typename VecT::elem_type eT;
        npy_intp dims[1] = { 1 };
        PyArrayObject* ary = (PyArrayObject*)PyArray_EMPTY(1, dims, NumpyType< eT >::val, true);
        if ( !ary || !array_is_contiguous(ary) ) { return NULL; }

        array_dimensions(ary)[0] = m->n_elem;
        array_strides(ary)[0]    = sizeof(  eT  );

        // 1. We do not need the memory at array_data(ary) anymore
        //    This can be simply removed by PyArray_free( array_data(ary) );
        array_free_data( array_data(ary) );

        // 2. We should "implant" the m->mem into array_data(ary)
        //    Here we use the trick from http://blog.enthought.com/?p=62
        array_clear_flags( ary, NPY_ARRAY_OWNDATA );
        ArmaBsptrCapsule< VecT > *capsule;
        capsule      = PyObject_New( ArmaBsptrCapsule< VecT >, &ArmaBsptrCapsulePyType< VecT >::object );
        capsule->mat = new std::shared_ptr< VecT >();
        array_set_data( ary, m->mem );
        (*(capsule->mat)) = m;
        array_set_base_object( ary, capsule );
        return (PyObject*)ary;
    }

#endif

}
//////////////////////////////////////////////////////////////////////////
// BY VALUE ARGs for 1D arrays
//////////////////////////////////////////////////////////////////////////

%define %armanpy_vec_byvalue_typemaps( ARMA_MAT_TYPE )

    %typemap( typecheck, precedence=SWIG_TYPECHECK_FLOAT_ARRAY )
        ( const ARMA_MAT_TYPE   ),
        (       ARMA_MAT_TYPE   )
    {
        $1 = armanpy_basic_typecheck< ARMA_MAT_TYPE >( $input, false );
    }

    %typemap( in, fragment="armanpy_vec_typemaps" )
        ( const ARMA_MAT_TYPE   ) ( PyArrayObject* array=NULL ),
        (       ARMA_MAT_TYPE   ) ( PyArrayObject* array=NULL )
    {
        if( ! armanpy_basic_typecheck< ARMA_MAT_TYPE >( $input, true ) ) SWIG_fail;
        array = obj_to_array_no_conversion( $input, ArmaTypeInfo< ARMA_MAT_TYPE >::type );
        if( !array ) SWIG_fail;
        $1 = ARMA_MAT_TYPE( ( ARMA_MAT_TYPE::elem_type *)array_data(array), arma::uword( array_dimensions(array)[0] ), false );
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

%armanpy_vec_byvalue_typemaps( arma::Col< double > )
%armanpy_vec_byvalue_typemaps( arma::Col< float >  )
%armanpy_vec_byvalue_typemaps( arma::Col< int > )
%armanpy_vec_byvalue_typemaps( arma::Col< unsigned >  )
%armanpy_vec_byvalue_typemaps( arma::Col< arma::sword >  )
%armanpy_vec_byvalue_typemaps( arma::Col< arma::uword >  )
%armanpy_vec_byvalue_typemaps( arma::Col< arma::cx_double >  )
%armanpy_vec_byvalue_typemaps( arma::Col< arma::cx_float >  )
%armanpy_vec_byvalue_typemaps( arma::Col< std::complex< double > > )
%armanpy_vec_byvalue_typemaps( arma::Col< std::complex< float > > )
%armanpy_vec_byvalue_typemaps( arma::vec )
%armanpy_vec_byvalue_typemaps( arma::fvec )
%armanpy_vec_byvalue_typemaps( arma::ivec )
%armanpy_vec_byvalue_typemaps( arma::uvec )
%armanpy_vec_byvalue_typemaps( arma::uchar_vec )
%armanpy_vec_byvalue_typemaps( arma::u32_vec )
%armanpy_vec_byvalue_typemaps( arma::s32_vec )
%armanpy_vec_byvalue_typemaps( arma::cx_vec )
%armanpy_vec_byvalue_typemaps( arma::cx_fvec )
%armanpy_vec_byvalue_typemaps( arma::colvec )
%armanpy_vec_byvalue_typemaps( arma::fcolvec )
%armanpy_vec_byvalue_typemaps( arma::icolvec )
%armanpy_vec_byvalue_typemaps( arma::ucolvec )
%armanpy_vec_byvalue_typemaps( arma::uchar_colvec )
%armanpy_vec_byvalue_typemaps( arma::u32_colvec )
%armanpy_vec_byvalue_typemaps( arma::s32_colvec )
%armanpy_vec_byvalue_typemaps( arma::cx_colvec )
%armanpy_vec_byvalue_typemaps( arma::cx_fcolvec )

%armanpy_vec_byvalue_typemaps( arma::Row< double > )
%armanpy_vec_byvalue_typemaps( arma::Row< float >  )
%armanpy_vec_byvalue_typemaps( arma::Row< int > )
%armanpy_vec_byvalue_typemaps( arma::Row< unsigned >  )
%armanpy_vec_byvalue_typemaps( arma::Row< arma::sword >  )
%armanpy_vec_byvalue_typemaps( arma::Row< arma::uword >  )
%armanpy_vec_byvalue_typemaps( arma::Row< std::complex< double > > )
%armanpy_vec_byvalue_typemaps( arma::Row< std::complex< float > > )
%armanpy_vec_byvalue_typemaps( arma::Row< arma::cx_double >  )
%armanpy_vec_byvalue_typemaps( arma::Row< arma::cx_float >  )
%armanpy_vec_byvalue_typemaps( arma::rowvec )
%armanpy_vec_byvalue_typemaps( arma::frowvec )
%armanpy_vec_byvalue_typemaps( arma::irowvec )
%armanpy_vec_byvalue_typemaps( arma::urowvec )
%armanpy_vec_byvalue_typemaps( arma::uchar_rowvec )
%armanpy_vec_byvalue_typemaps( arma::u32_rowvec )
%armanpy_vec_byvalue_typemaps( arma::s32_rowvec )
%armanpy_vec_byvalue_typemaps( arma::cx_rowvec )
%armanpy_vec_byvalue_typemaps( arma::cx_frowvec )

//////////////////////////////////////////////////////////////////////////
// CONST REF/PTR ARGs for 1D arrays
//////////////////////////////////////////////////////////////////////////

%define %armanpy_vec_const_ref_typemaps( ARMA_MAT_TYPE )

    %typemap( typecheck, precedence=SWIG_TYPECHECK_FLOAT_ARRAY )
        ( const ARMA_MAT_TYPE & ) ( PyArrayObject* array=NULL ),
        ( const ARMA_MAT_TYPE * ) ( PyArrayObject* array=NULL )
    {
        $1 = armanpy_basic_typecheck< ARMA_MAT_TYPE >( $input, false );
    }

    %typemap( in, fragment="armanpy_vec_typemaps" )
        ( const ARMA_MAT_TYPE & ) ( PyArrayObject* array=NULL ),
        ( const ARMA_MAT_TYPE * ) ( PyArrayObject* array=NULL )
    {
        if( ! armanpy_basic_typecheck< ARMA_MAT_TYPE >( $input, true ) ) SWIG_fail;
        array = obj_to_array_no_conversion( $input, ArmaTypeInfo< ARMA_MAT_TYPE >::type );
        if( !array ) SWIG_fail;
        $1 = new ARMA_MAT_TYPE( ( ARMA_MAT_TYPE::elem_type *)array_data(array),
                                arma::uword( array_dimensions(array)[0] ), false );
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

%armanpy_vec_const_ref_typemaps( arma::Col< double > )
%armanpy_vec_const_ref_typemaps( arma::Col< float >  )
%armanpy_vec_const_ref_typemaps( arma::Col< int > )
%armanpy_vec_const_ref_typemaps( arma::Col< unsigned >  )
%armanpy_vec_const_ref_typemaps( arma::Col< arma::sword >  )
%armanpy_vec_const_ref_typemaps( arma::Col< arma::uword >  )
%armanpy_vec_const_ref_typemaps( arma::Col< arma::cx_double >  )
%armanpy_vec_const_ref_typemaps( arma::Col< arma::cx_float >  )
%armanpy_vec_const_ref_typemaps( arma::Col< std::complex< double > > )
%armanpy_vec_const_ref_typemaps( arma::Col< std::complex< float > > )
%armanpy_vec_const_ref_typemaps( arma::vec )
%armanpy_vec_const_ref_typemaps( arma::fvec )
%armanpy_vec_const_ref_typemaps( arma::ivec )
%armanpy_vec_const_ref_typemaps( arma::uvec )
%armanpy_vec_const_ref_typemaps( arma::uchar_vec )
%armanpy_vec_const_ref_typemaps( arma::u32_vec )
%armanpy_vec_const_ref_typemaps( arma::s32_vec )
%armanpy_vec_const_ref_typemaps( arma::cx_vec )
%armanpy_vec_const_ref_typemaps( arma::cx_fvec )
%armanpy_vec_const_ref_typemaps( arma::colvec )
%armanpy_vec_const_ref_typemaps( arma::fcolvec )
%armanpy_vec_const_ref_typemaps( arma::icolvec )
%armanpy_vec_const_ref_typemaps( arma::ucolvec )
%armanpy_vec_const_ref_typemaps( arma::uchar_colvec )
%armanpy_vec_const_ref_typemaps( arma::u32_colvec )
%armanpy_vec_const_ref_typemaps( arma::s32_colvec )
%armanpy_vec_const_ref_typemaps( arma::cx_colvec )
%armanpy_vec_const_ref_typemaps( arma::cx_fcolvec )

%armanpy_vec_const_ref_typemaps( arma::Row< double > )
%armanpy_vec_const_ref_typemaps( arma::Row< float >  )
%armanpy_vec_const_ref_typemaps( arma::Row< int > )
%armanpy_vec_const_ref_typemaps( arma::Row< unsigned >  )
%armanpy_vec_const_ref_typemaps( arma::Row< arma::sword >  )
%armanpy_vec_const_ref_typemaps( arma::Row< arma::uword >  )
%armanpy_vec_const_ref_typemaps( arma::Row< std::complex< double > > )
%armanpy_vec_const_ref_typemaps( arma::Row< std::complex< float > > )
%armanpy_vec_const_ref_typemaps( arma::Row< arma::cx_double >  )
%armanpy_vec_const_ref_typemaps( arma::Row< arma::cx_float >  )
%armanpy_vec_const_ref_typemaps( arma::rowvec )
%armanpy_vec_const_ref_typemaps( arma::frowvec )
%armanpy_vec_const_ref_typemaps( arma::irowvec )
%armanpy_vec_const_ref_typemaps( arma::urowvec )
%armanpy_vec_const_ref_typemaps( arma::uchar_rowvec )
%armanpy_vec_const_ref_typemaps( arma::u32_rowvec )
%armanpy_vec_const_ref_typemaps( arma::s32_rowvec )
%armanpy_vec_const_ref_typemaps( arma::cx_rowvec )
%armanpy_vec_const_ref_typemaps( arma::cx_frowvec )

//////////////////////////////////////////////////////////////////////////
// Typemaps for input-output arguments. That is for arguments which are
// potentialliy modified in place.
//////////////////////////////////////////////////////////////////////////

// A macor for generating the typemaps for one matrix type
%define %armanpy_vec_ref_typemaps( ARMA_MAT_TYPE )

    %typemap( typecheck, precedence=SWIG_TYPECHECK_FLOAT_ARRAY )
        ( ARMA_MAT_TYPE &)
    {
        $1 = armanpy_basic_typecheck< ARMA_MAT_TYPE >( $input, false, true );
    }

    %typemap( in, fragment="armanpy_vec_typemaps" )
        ( ARMA_MAT_TYPE &)
    {
        if( ! armanpy_basic_typecheck< ARMA_MAT_TYPE >( $input, true, true )            ) SWIG_fail;
        if( ! armanpy_numpy_as_vec_with_shared_memory< ARMA_MAT_TYPE >( $input, &($1) ) ) SWIG_fail;
    }

    %typemap( argout, fragment="armanpy_vec_typemaps" )
        ( ARMA_MAT_TYPE & )
    {
        armanpy_vec_as_numpy_with_shared_memory( $1, $input );
    }

    %typemap( freearg )
        ( ARMA_MAT_TYPE & )
    {
       // NOOP
    }

%enddef

%armanpy_vec_ref_typemaps( arma::Col< double > )
%armanpy_vec_ref_typemaps( arma::Col< float >  )
%armanpy_vec_ref_typemaps( arma::Col< int > )
%armanpy_vec_ref_typemaps( arma::Col< unsigned >  )
%armanpy_vec_ref_typemaps( arma::Col< arma::sword >  )
%armanpy_vec_ref_typemaps( arma::Col< arma::uword >  )
%armanpy_vec_ref_typemaps( arma::Col< arma::cx_double >  )
%armanpy_vec_ref_typemaps( arma::Col< arma::cx_float >  )
%armanpy_vec_ref_typemaps( arma::Col< std::complex< double > > )
%armanpy_vec_ref_typemaps( arma::Col< std::complex< float > > )
%armanpy_vec_ref_typemaps( arma::vec )
%armanpy_vec_ref_typemaps( arma::fvec )
%armanpy_vec_ref_typemaps( arma::ivec )
%armanpy_vec_ref_typemaps( arma::uvec )
%armanpy_vec_ref_typemaps( arma::uchar_vec )
%armanpy_vec_ref_typemaps( arma::u32_vec )
%armanpy_vec_ref_typemaps( arma::s32_vec )
%armanpy_vec_ref_typemaps( arma::cx_vec )
%armanpy_vec_ref_typemaps( arma::cx_fvec )
%armanpy_vec_ref_typemaps( arma::colvec )
%armanpy_vec_ref_typemaps( arma::fcolvec )
%armanpy_vec_ref_typemaps( arma::icolvec )
%armanpy_vec_ref_typemaps( arma::ucolvec )
%armanpy_vec_ref_typemaps( arma::uchar_colvec )
%armanpy_vec_ref_typemaps( arma::u32_colvec )
%armanpy_vec_ref_typemaps( arma::s32_colvec )
%armanpy_vec_ref_typemaps( arma::cx_colvec )
%armanpy_vec_ref_typemaps( arma::cx_fcolvec )


%armanpy_vec_ref_typemaps( arma::Row< double > )
%armanpy_vec_ref_typemaps( arma::Row< float >  )
%armanpy_vec_ref_typemaps( arma::Row< int > )
%armanpy_vec_ref_typemaps( arma::Row< unsigned >  )
%armanpy_vec_ref_typemaps( arma::Row< arma::sword >  )
%armanpy_vec_ref_typemaps( arma::Row< arma::uword >  )
%armanpy_vec_ref_typemaps( arma::Row< arma::cx_double >  )
%armanpy_vec_ref_typemaps( arma::Row< arma::cx_float >  )
%armanpy_vec_ref_typemaps( arma::Row< std::complex< double > > )
%armanpy_vec_ref_typemaps( arma::Row< std::complex< float > > )
%armanpy_vec_ref_typemaps( arma::rowvec )
%armanpy_vec_ref_typemaps( arma::frowvec )
%armanpy_vec_ref_typemaps( arma::irowvec )
%armanpy_vec_ref_typemaps( arma::urowvec )
%armanpy_vec_ref_typemaps( arma::uchar_rowvec )
%armanpy_vec_ref_typemaps( arma::u32_rowvec )
%armanpy_vec_ref_typemaps( arma::s32_rowvec )
%armanpy_vec_ref_typemaps( arma::cx_rowvec )
%armanpy_vec_ref_typemaps( arma::cx_frowvec )

//////////////////////////////////////////////////////////////////////////
// Typemaps for return by value functions/methods
//////////////////////////////////////////////////////////////////////////

%define %armanpy_vec_return_by_value_typemaps( ARMA_MAT_TYPE )
    %typemap( out )
        ( ARMA_MAT_TYPE )
    {
      PyObject* array = armanpy_vec_copy_to_numpy< ARMA_MAT_TYPE >( &$1 );
      if ( !array ) SWIG_fail;
      $result = SWIG_Python_AppendOutput($result, array);
    }
%enddef

%armanpy_vec_return_by_value_typemaps( arma::Col< double > )
%armanpy_vec_return_by_value_typemaps( arma::Col< float >  )
%armanpy_vec_return_by_value_typemaps( arma::Col< int > )
%armanpy_vec_return_by_value_typemaps( arma::Col< unsigned >  )
%armanpy_vec_return_by_value_typemaps( arma::Col< arma::sword >  )
%armanpy_vec_return_by_value_typemaps( arma::Col< arma::uword >  )
%armanpy_vec_return_by_value_typemaps( arma::Col< arma::cx_double >  )
%armanpy_vec_return_by_value_typemaps( arma::Col< arma::cx_float >  )
%armanpy_vec_return_by_value_typemaps( arma::Col< std::complex< double > > )
%armanpy_vec_return_by_value_typemaps( arma::Col< std::complex< float > > )
%armanpy_vec_return_by_value_typemaps( arma::vec )
%armanpy_vec_return_by_value_typemaps( arma::fvec )
%armanpy_vec_return_by_value_typemaps( arma::ivec )
%armanpy_vec_return_by_value_typemaps( arma::uvec )
%armanpy_vec_return_by_value_typemaps( arma::uchar_vec )
%armanpy_vec_return_by_value_typemaps( arma::u32_vec )
%armanpy_vec_return_by_value_typemaps( arma::s32_vec )
%armanpy_vec_return_by_value_typemaps( arma::cx_vec )
%armanpy_vec_return_by_value_typemaps( arma::cx_fvec )
%armanpy_vec_return_by_value_typemaps( arma::colvec )
%armanpy_vec_return_by_value_typemaps( arma::fcolvec )
%armanpy_vec_return_by_value_typemaps( arma::icolvec )
%armanpy_vec_return_by_value_typemaps( arma::ucolvec )
%armanpy_vec_return_by_value_typemaps( arma::uchar_colvec )
%armanpy_vec_return_by_value_typemaps( arma::u32_colvec )
%armanpy_vec_return_by_value_typemaps( arma::s32_colvec )
%armanpy_vec_return_by_value_typemaps( arma::cx_colvec )
%armanpy_vec_return_by_value_typemaps( arma::cx_fcolvec )

%armanpy_vec_return_by_value_typemaps( arma::Row< double > )
%armanpy_vec_return_by_value_typemaps( arma::Row< float >  )
%armanpy_vec_return_by_value_typemaps( arma::Row< int > )
%armanpy_vec_return_by_value_typemaps( arma::Row< unsigned >  )
%armanpy_vec_return_by_value_typemaps( arma::Row< arma::sword >  )
%armanpy_vec_return_by_value_typemaps( arma::Row< arma::uword >  )
%armanpy_vec_return_by_value_typemaps( arma::Row< arma::cx_double >  )
%armanpy_vec_return_by_value_typemaps( arma::Row< arma::cx_float >  )
%armanpy_vec_return_by_value_typemaps( arma::Row< std::complex< double > > )
%armanpy_vec_return_by_value_typemaps( arma::Row< std::complex< float > > )
%armanpy_vec_return_by_value_typemaps( arma::rowvec )
%armanpy_vec_return_by_value_typemaps( arma::frowvec )
%armanpy_vec_return_by_value_typemaps( arma::irowvec )
%armanpy_vec_return_by_value_typemaps( arma::urowvec )
%armanpy_vec_return_by_value_typemaps( arma::uchar_rowvec )
%armanpy_vec_return_by_value_typemaps( arma::u32_rowvec )
%armanpy_vec_return_by_value_typemaps( arma::s32_rowvec )
%armanpy_vec_return_by_value_typemaps( arma::cx_rowvec )
%armanpy_vec_return_by_value_typemaps( arma::cx_frowvec )

%define %armanpy_vec_return_by_reference_typemaps( ARMA_MAT_TYPE )
    %typemap( out )
        ( const ARMA_MAT_TYPE & ),
        (       ARMA_MAT_TYPE & )
    {
      PyObject* array = armanpy_vec_copy_to_numpy< ARMA_MAT_TYPE >( $1 );
      if ( !array ) SWIG_fail;
      $result = SWIG_Python_AppendOutput($result, array);
    }
%enddef

%armanpy_vec_return_by_reference_typemaps( arma::Col< double > )
%armanpy_vec_return_by_reference_typemaps( arma::Col< float >  )
%armanpy_vec_return_by_reference_typemaps( arma::Col< int > )
%armanpy_vec_return_by_reference_typemaps( arma::Col< unsigned >  )
%armanpy_vec_return_by_reference_typemaps( arma::Col< arma::sword >  )
%armanpy_vec_return_by_reference_typemaps( arma::Col< arma::uword >  )
%armanpy_vec_return_by_reference_typemaps( arma::Col< arma::cx_double >  )
%armanpy_vec_return_by_reference_typemaps( arma::Col< arma::cx_float >  )
%armanpy_vec_return_by_reference_typemaps( arma::Col< std::complex< double > > )
%armanpy_vec_return_by_reference_typemaps( arma::Col< std::complex< float > > )
%armanpy_vec_return_by_reference_typemaps( arma::vec )
%armanpy_vec_return_by_reference_typemaps( arma::fvec )
%armanpy_vec_return_by_reference_typemaps( arma::ivec )
%armanpy_vec_return_by_reference_typemaps( arma::uvec )
%armanpy_vec_return_by_reference_typemaps( arma::uchar_vec )
%armanpy_vec_return_by_reference_typemaps( arma::u32_vec )
%armanpy_vec_return_by_reference_typemaps( arma::s32_vec )
%armanpy_vec_return_by_reference_typemaps( arma::cx_vec )
%armanpy_vec_return_by_reference_typemaps( arma::cx_fvec )
%armanpy_vec_return_by_reference_typemaps( arma::colvec )
%armanpy_vec_return_by_reference_typemaps( arma::fcolvec )
%armanpy_vec_return_by_reference_typemaps( arma::icolvec )
%armanpy_vec_return_by_reference_typemaps( arma::ucolvec )
%armanpy_vec_return_by_reference_typemaps( arma::uchar_colvec )
%armanpy_vec_return_by_reference_typemaps( arma::u32_colvec )
%armanpy_vec_return_by_reference_typemaps( arma::s32_colvec )
%armanpy_vec_return_by_reference_typemaps( arma::cx_colvec )
%armanpy_vec_return_by_reference_typemaps( arma::cx_fcolvec )

%armanpy_vec_return_by_reference_typemaps( arma::Row< double > )
%armanpy_vec_return_by_reference_typemaps( arma::Row< float >  )
%armanpy_vec_return_by_reference_typemaps( arma::Row< int > )
%armanpy_vec_return_by_reference_typemaps( arma::Row< unsigned >  )
%armanpy_vec_return_by_reference_typemaps( arma::Row< arma::sword >  )
%armanpy_vec_return_by_reference_typemaps( arma::Row< arma::uword >  )
%armanpy_vec_return_by_reference_typemaps( arma::Row< arma::cx_double >  )
%armanpy_vec_return_by_reference_typemaps( arma::Row< arma::cx_float >  )
%armanpy_vec_return_by_reference_typemaps( arma::Row< std::complex< double > > )
%armanpy_vec_return_by_reference_typemaps( arma::Row< std::complex< float > > )
%armanpy_vec_return_by_reference_typemaps( arma::rowvec )
%armanpy_vec_return_by_reference_typemaps( arma::frowvec )
%armanpy_vec_return_by_reference_typemaps( arma::irowvec )
%armanpy_vec_return_by_reference_typemaps( arma::urowvec )
%armanpy_vec_return_by_reference_typemaps( arma::uchar_rowvec )
%armanpy_vec_return_by_reference_typemaps( arma::u32_rowvec )
%armanpy_vec_return_by_reference_typemaps( arma::s32_rowvec )
%armanpy_vec_return_by_reference_typemaps( arma::cx_rowvec )
%armanpy_vec_return_by_reference_typemaps( arma::cx_frowvec )

//////////////////////////////////////////////////////////////////////////
// Typemaps for return by std::shared_ptr< ... > functions/methods
//////////////////////////////////////////////////////////////////////////

#if defined(ARMANPY_SHARED_PTR)

%define %armanpy_vec_return_by_bsptr_typemaps( ARMA_MAT_TYPE )
    %typemap( out , fragment="armanpy_vec_typemaps" )
        ( std::shared_ptr< ARMA_MAT_TYPE > )
    {
      PyObject* array = armanpy_vec_bsptr_as_numpy_with_shared_memory< ARMA_MAT_TYPE >( $1 );
      if ( !array ) SWIG_fail;
      $result = SWIG_Python_AppendOutput($result, array);
    }
%enddef

%armanpy_vec_return_by_bsptr_typemaps( arma::Col< double > )
%armanpy_vec_return_by_bsptr_typemaps( arma::Col< float >  )
%armanpy_vec_return_by_bsptr_typemaps( arma::Col< int > )
%armanpy_vec_return_by_bsptr_typemaps( arma::Col< unsigned >  )
%armanpy_vec_return_by_bsptr_typemaps( arma::Col< arma::sword >  )
%armanpy_vec_return_by_bsptr_typemaps( arma::Col< arma::uword >  )
%armanpy_vec_return_by_bsptr_typemaps( arma::Col< arma::cx_double >  )
%armanpy_vec_return_by_bsptr_typemaps( arma::Col< arma::cx_float >  )
%armanpy_vec_return_by_bsptr_typemaps( arma::Col< std::complex< double > > )
%armanpy_vec_return_by_bsptr_typemaps( arma::Col< std::complex< float > > )
%armanpy_vec_return_by_bsptr_typemaps( arma::vec )
%armanpy_vec_return_by_bsptr_typemaps( arma::fvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::ivec )
%armanpy_vec_return_by_bsptr_typemaps( arma::uvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::uchar_vec )
%armanpy_vec_return_by_bsptr_typemaps( arma::u32_vec )
%armanpy_vec_return_by_bsptr_typemaps( arma::s32_vec )
%armanpy_vec_return_by_bsptr_typemaps( arma::cx_vec )
%armanpy_vec_return_by_bsptr_typemaps( arma::cx_fvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::colvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::fcolvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::icolvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::ucolvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::uchar_colvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::u32_colvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::s32_colvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::cx_colvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::cx_fcolvec )

%armanpy_vec_return_by_bsptr_typemaps( arma::Row< double > )
%armanpy_vec_return_by_bsptr_typemaps( arma::Row< float >  )
%armanpy_vec_return_by_bsptr_typemaps( arma::Row< int > )
%armanpy_vec_return_by_bsptr_typemaps( arma::Row< unsigned >  )
%armanpy_vec_return_by_bsptr_typemaps( arma::Row< arma::sword >  )
%armanpy_vec_return_by_bsptr_typemaps( arma::Row< arma::uword >  )
%armanpy_vec_return_by_bsptr_typemaps( arma::Row< arma::cx_double >  )
%armanpy_vec_return_by_bsptr_typemaps( arma::Row< arma::cx_float >  )
%armanpy_vec_return_by_bsptr_typemaps( arma::Row< std::complex< double > > )
%armanpy_vec_return_by_bsptr_typemaps( arma::Row< std::complex< float > > )
%armanpy_vec_return_by_bsptr_typemaps( arma::rowvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::frowvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::irowvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::urowvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::uchar_rowvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::u32_rowvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::s32_rowvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::cx_rowvec )
%armanpy_vec_return_by_bsptr_typemaps( arma::cx_frowvec )

#endif
