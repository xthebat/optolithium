# Copyright (C) 2012 thomas.natschlaeger@gmail.com
# 
# This file is part of the ArmaNpy library.
# It is provided without any warranty of fitness
# for any purpose. You can redistribute this file
# and/or modify it under the terms of the GNU
# Lesser General Public License (LGPL) as published
# by the Free Software Foundation, either version 3
# of the License or (at your option) any later version.
# (see http://www.opensource.org/licenses for more info)

import os, sys, warnings
import numpy as N

sys.path.append( "./build/bin" )
from armanpyexample import *

def example_usage():

    # New instance of class using arma::mat
    ex = Example( 5 )

    
    # return values with and without boost:shared_ptr
    m1 = ex.get()
    print m1
        
    m2 = ex.get_sptr()
    print N.all( N.all( m1 == m2 ) )

    # Input arguments must have FORTRAN odering: i.e. order="F"
    ex.set( N.array( [ [1.,2.,3.], [4.,5.,0.6] ], order="F" ) )
    print ex.get()
    

    
    # The following would cause an exception
    # ex.set_m( N.array( [ [1.,2.,3.], [4.,5.,.6] ], order="C" ) )
    # --> TypeError: Array must be FORTRAN contiguous. A non-FORTRAN-contiguous array was given.
    
    # In the following the size and content of a matrix is modified
    m = N.array( [ [1.,2.,3.], [4.,5.,0.6] ], order="F" )
    ex.modify( m, 9, 9 )
    print m
    
    # Note that after the matrix was modifed by this function it does not
    # own its memory. So one can e.g. not resize it
    # m.resize( 81, 1 ) ---> ValueError: cannot resize this array: it does not own its data
    # But it is easy to copy it and work with it
    m = N.array( m )
    m.resize(81,1)
    print m.shape
    
    
if __name__ == '__main__':
    example_usage()
