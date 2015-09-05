# cmake -G "MSYS Makefiles" 
#       -DCMAKE_BUILD_TYPE=Release 
#       -DARMADILLO_INCLUDE_DIR=d:\Gladkikh\Python\Lithography\ThirdParty\armadillo\include\ 
#       -DARMANPY_INCLUDE_DIR=d:\Gladkikh\temp\armanpy-0.1.3\include\ 
#       CMakeLists.txt 
# cmake --build . --config Release

SET( CMAKE_CXX_FLAGS "-D__NO_MINGW_LFS -include cmath -std=c++11 ${CMAKE_CXX_FLAGS}" )

cmake_minimum_required(VERSION 3.0)

SET( CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR} )
SET( THIRDPARTY_DIR "d:/Gladkikh/Python/Lithography/ThirdParty/" )
SET( ARMADILLO_INCLUDE_DIR "${THIRDPARTY_DIR}/armadillo/include/" )
SET( ARMANPY_INCLUDE_DIR "${THIRDPARTY_DIR}/armanpy/include" )

FIND_PACKAGE(SWIG REQUIRED)
FIND_PACKAGE(PythonLibs REQUIRED)
FIND_PACKAGE(NumPy REQUIRED)

INCLUDE(${SWIG_USE_FILE})
INCLUDE_DIRECTORIES("${PYTHON_INCLUDE_DIR}")
INCLUDE_DIRECTORIES("${ARMADILLO_INCLUDE_DIR}")
INCLUDE_DIRECTORIES("${ARMANPY_INCLUDE_DIR}")
INCLUDE_DIRECTORIES("${PROJECT_BINARY_DIR}")
INCLUDE_DIRECTORIES("${NUMPY_INCLUDE_DIRS}")

# INCLUDE_DIRECTORIES("C:\\Python27\\lib\\site-packages\\numpy\\core\\include")

# build the example library
add_library( examplelib SHARED example.cpp example.hpp )

##
## Set up the swig wrapper
##

# Swig shall but all stuff to the same directory where the *.so or *.pyd are placed
SET( CMAKE_SWIG_OUTDIR "${PROJECT_BINARY_DIR}/bin" )

# We need to say that we deal with C++ and do not care about missing include files and declarations
set_source_files_properties( example.i PROPERTIES CPLUSPLUS ON)
set_source_files_properties( example.i PROPERTIES SWIG_FLAGS "-ignoremissing;-w509" )

SWIG_ADD_MODULE    ( armanpyexample python example.i )
SWIG_LINK_LIBRARIES( armanpyexample examplelib ${PYTHON_LIBRARIES} )

configure_file( example.py "${CMAKE_SWIG_OUTDIR}/example.py" COPYONLY )

add_test( NAME example COMMAND ${PYTHON_EXECUTABLE} example.py WORKING_DIRECTORY ${CMAKE_SWIG_OUTDIR} )
