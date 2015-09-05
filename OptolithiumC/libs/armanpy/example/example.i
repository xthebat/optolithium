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

%module armanpyexample
%{
#define SWIG_FILE_WITH_INIT

/* Includes the header in the wrapper code */
#include "example.hpp"
%}

/* We need this for boost_shared::ptr support */
%include <boost_shared_ptr.i>

/* Now include ArmaNpy typemaps */
%include "armanpy.i"

/* Some minimal excpetion handling */
%exception {
    try {
        $action
    } catch( char * str ) {
        PyErr_SetString( PyExc_IndexError, str );
        SWIG_fail;
    } 
}

/* Parse the header file to generate wrappers */
%include "example.hpp"
