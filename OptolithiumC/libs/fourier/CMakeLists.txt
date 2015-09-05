CMAKE_MINIMUM_REQUIRED(VERSION 2.6.0)
PROJECT(fourier)

SET(CMAKE_USE_RELATIVE_PATHS ON)
SET(CMAKE_SKIP_RPATH TRUE)

SET(CMAKE_BUILD_TYPE "Release")

SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Ofast -fmerge-all-constants -funroll-loops")
# SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fassociative-math -ffinite-math-only -freciprocal-math" )

INCLUDE_DIRECTORIES("${CMAKE_CURRENT_SOURCE_DIR}/include")

ADD_LIBRARY(fourier STATIC
    "src/fourier.c"
    "src/primes.c")


FIND_PACKAGE(FFTW REQUIRED)
INCLUDE_DIRECTORIES("${FFTW_INCLUDES}")
ADD_EXECUTABLE(check "src/check.c")
TARGET_LINK_LIBRARIES(check ${FFTW_LIBRARIES})
TARGET_LINK_LIBRARIES(check fourier)
