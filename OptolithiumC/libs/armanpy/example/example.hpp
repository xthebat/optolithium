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

#ifndef _EXAMPLE_HPP_
#define _EXAMPLE_HPP_

/* Cmake will define ${LIBRARY_NAME}_EXPORTS on Windows when it
configures to build a shared library. If you are going to use
another build system on windows or create the visual studio
projects by hand you need to define ${LIBRARY_NAME}_EXPORTS when
building a DLL on windows.
*/
// We are using the Visual Studio Compiler and building Shared libraries

#if defined (_WIN32)
	#if defined(examplelib_EXPORTS)
		#define DLLEXPORT __declspec(dllexport)
	#else
		#define DLLEXPORT __declspec(dllimport)
	#endif
#else
	#define DLLEXPORT
#endif

#if !defined( SWIG )
    // SWIG should not see #inlcude<armadillo> as it can not handle it
	#include <armadillo>
	//#include <boost/shared_ptr.hpp>
#endif

#pragma warning(disable:4251)

class DLLEXPORT Example
 {

public:
    Example( int sz ) {
        m.randn(sz, sz);
    };

    arma::cx_mat get(void) {
        return m;
    };

//    boost::shared_ptr< arma::cx_mat > get_sptr(void) {
//        boost::shared_ptr< arma::cx_mat > p( new arma::cx_mat( m ) );
//        return p;
//    };

    void set( const arma::cx_mat& m ) {
        this->m = m;
    };

    void rnd( unsigned s) {
        this->m.randn(s,s);
    };

    void modify( arma::cx_mat& A, unsigned r, unsigned c ) {
        A.resize( r, c );
        A.randn( r, c );
        for( unsigned i=0; i<r; i++ ) {
            for( unsigned j=0; j<c; j++ ) {
                A(i,j) = 10.0*i+j;
            }
        }
    };

private:
    arma::cx_mat m;
};

#endif
