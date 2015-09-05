/*
 * File:        FMM_API.h
 * Copyrights:  (c) 2005 The Trustees of Princeton University and Board of
 *                  Regents of the University of Texas.  All rights reserved.
 *              (c) 2009 Kevin T. Chu.  All rights reserved.
 * Revision:    $Revision: 149 $
 * Modified:    $Date: 2009-01-18 00:31:09 -0800 (Sun, 18 Jan 2009) $
 * Description: Header file for 2D and 3D Fast Marching Method Algorithms
 */
 
#ifndef FMM_API_H_
#define FMM_API_H_

//#include "FMM_Real.h"


/* Debugging macro */
#ifndef LSMLIB_DEBUG_NO_INLINE
/* #undef LSMLIB_DEBUG_NO_INLINE  */
#endif

/* Macro defined if double precision library is being built. */
#ifndef LSMLIB_DOUBLE_PRECISION
#define LSMLIB_DOUBLE_PRECISION 1
#endif

/* Floating-point precision for LSMLIB_REAL */
#ifndef LSMLIB_REAL
#define LSMLIB_REAL double
#endif

/* Zero tolerance */
#ifndef LSMLIB_ZERO_TOL
#define LSMLIB_ZERO_TOL 1.e-11
#endif

/* Maximum value for LSMLIB_REAL */
#ifndef LSMLIB_REAL_MAX
#define LSMLIB_REAL_MAX DBL_MAX
#endif

/* Minimum value for LSMLIB_REAL */
#ifndef LSMLIB_REAL_MIN
#define LSMLIB_REAL_MIN DBL_MIN
#endif

/* Machine epsilon value for LSMLIB_REAL */
#ifndef LSMLIB_REAL_EPSILON
#define LSMLIB_REAL_EPSILON DBL_EPSILON
#endif



/*============================= Constants ===========================*/
#define LSM_FMM_TRUE                   (1)
#define LSM_FMM_FALSE                  (0)
#define LSM_FMM_DEFAULT_UPDATE_VALUE   (-1)


/*========================== Error Codes ============================*/
#define LSM_FMM_ERR_SUCCESS                                 (0)
#define LSM_FMM_ERR_FMM_DATA_CREATION_ERROR                 (1)
#define LSM_FMM_ERR_INVALID_SPATIAL_DISCRETIZATION_ORDER    (2)


#ifdef __cplusplus
extern "C" {
#endif

/*! \file FMM_API.h
 * 
 * \brief 
 * @ref lsm_fast_marching_method.h provides support for basic fast 
 * marching method calculations:  computing distance functions, 
 * extensions of field variables (e.g. extension velocities, etc.) 
 * off of the zero contour of a level set function, and solving the
 * Eikonal equation.
 *
 * The algorithm (and naming) closely follows the description in 
 * "Level Set Methods and Fast Marching Methods" by J.A. Sethian
 * and "The Fast Construction of Extension Velocities in Level Set
 * Methods" by D. Adalsteinsson and J.A. Sethian (J. Comp. Phys, 
 * vol 148, p 2-22, 1999).
 * 
 * 
 * <h3> NOTES </h3>
 * - The fast marching method library assumes that the field data
 *   are stored in Fortran order (i.e. column-major order).
 *
 * - Error Codes:  0 - successful computation,
 *                 1 - FMM_Data creation error,
 *                 2 - invalid spatial discretization order
 *
 * - While @ref lsm_fast_marching_method.h only provides functions 
 *   for 2D and 3D FMM calculations, LSMLIB is capable of supporting higher 
 *   dimensional calculations (currently as high as 8, set by 
 *   FMM_HEAP_MAX_NDIM in @ref FMM_Heap.h).  To use LSMLIB to do 
 *   higher dimensional fast marching method calculations, just modify 
 *   lsm_FMM_field_extension*d.c and/or lsm_FMM_eikonal*d.c so that
 *   the data array sizes and index calculations are appropriate
 *   for the dimensionality of the problem of interest.
 *
 */


/*!
 * computeExtensionFields2d uses the FMM algorithm to compute the 
 * distance function and extension fields from the original level set
 * function, phi, and the specified source fields.  
 *
 * Arguments:
 *  - distance_function (out):            updated distance function
 *  - extension_fields (out):             extension fields
 *  - phi (in):                           original level set function
 *  - mask (in):                          mask for domain of problem;
 *                                        grid points outside of the domain
 *                                        of the problem should be set to a 
 *                                        negative value.  
 *  - source_fields(in):                  source fields used to compute 
 *                                        extension fields
 *  - num_extension_fields (in):          number of extension fields to compute
 *  - spatial_discretization_order (in):  order of finite differences used 
 *                                        to compute spatial derivatives
 *  - grid_dims (in):                     array of index space extents for all 
 *                                        fields 
 *  - dx (in):                            array of grid cell sizes in each 
 *                                        coordinate direction
 *
 * Return value:                          error code (see NOTES for translation)
 *
 *
 * NOTES:
 *  - When the second-order spatial discretization is requested, only
 *    the distance function is computed using the second-order scheme.
 *    The extension fields are computed using a first-order 
 *    discretization of the gradient for the extension field and a 
 *    second-order accurate discretization of the gradient for the 
 *    distance function.  We use a first-order discretization when
 *    computing extension fields because the second-order 
 *    discretization is "unstable" and leads to amplification of the
 *    errors introduced when initializing the extension fields in 
 *    the region around the zero level set.
 *
 *  - The distance function computed when using a second-order spatial 
 *    discretization are approximately second-order accurate in the 
 *    L2 norm but are only first-order accurate in the L-infinity norm.  
 *    The reason for this behavior is that the current implementation 
 *    uses only a first-order accurate scheme for initializing the grid 
 *    points around the zero-level set.
 *
 *  - For grid points that are masked out, the distance function and
 *    extension fields are set to 0.
 *
 *  - It is assumed that the user has allocated the memory for the
 *    distance function, extension fields, phi, and source fields.
 *
 *  - It is assumed that the phi and mask data arrays are both of 
 *    the same size.  That is, all data fields are assumed to have 
 *    the same index space extents.
 *
 *  - If mask is set to a NULL pointer, then all grid points are treated
 *    as being in the interior of the domain.
 *
 *  - The number of extension fields is assumed to be equal to the
 *    number of source fields.
 *
 */
int computeExtensionFields2d(
  LSMLIB_REAL *distance_function,
  LSMLIB_REAL **extension_fields,
  LSMLIB_REAL *phi,
  LSMLIB_REAL *mark,
  LSMLIB_REAL **source_fields,
  int num_extension_fields,
  int spatial_discretization_order,
  int *grid_dims,
  LSMLIB_REAL *dx);

/*!
 * computeDistanceFunction2d uses the FMM algorithm to compute the 
 * a distance function from the original level set function, phi.
 *
 * Arguments:
 *  - distance_function (out):            updated distance function
 *  - phi (in):                           original level set function
 *  - mask (in):                          mask for domain of problem;
 *                                        grid points outside of the domain
 *                                        of the problem should be set to a 
 *                                        negative value.
 *  - spatial_discretization_order (in):  order of finite differences used 
 *                                        to compute spatial derivatives
 *  - grid_dims (in):                     array of index space extents for all 
 *                                        fields 
 *  - dx (in):                            array of grid cell sizes in each 
 *                                        coordinate direction
 *
 * Return value:                          error code (see NOTES for translation)
 *
 *
 * NOTES:
 *  - The distance function computed when using a second-order spatial 
 *    discretization are approximately second-order accurate in the 
 *    L2 norm but are only first-order accurate in the L-infinity norm.  
 *    The reason for this behavior is that the current implementation 
 *    uses only a first-order accurate scheme for initializing the grid 
 *    points around the zero-level set.
 *
 *  - For grid points that are masked out, the distance function is
 *    set to 0.
 *
 *  - It is assumed that the user has allocated the memory for the
 *    distance function and phi fields.
 *
 *  - If mask is set to a NULL pointer, then all grid points are treated
 *    as being in the interior of the domain.
 *
 *  - It is assumed that the phi and mask data arrays are both of 
 *    the same size.  That is, all data fields are assumed to have 
 *    the same index space extents.
 *
 */
int computeDistanceFunction2d(
  LSMLIB_REAL *distance_function,
  LSMLIB_REAL *phi,
  LSMLIB_REAL *mark,
  int spatial_discretization_order,
  int *grid_dims,
  LSMLIB_REAL *dx);

/*!
 * solveEikonalEquation2d uses the FMM algorithm to solve the Eikonal
 * equation 
 *
 *   |grad(phi)| = 1/speed(x,y)
 *
 * in two space dimensions with the specified boundary data and
 * speed function.  
 *
 * This function assumes that the solution phi is assumed to be 
 * strictly non-negative with values in the interior of the domain 
 * greater than the values on the boundaries.  For problems where 
 * phi takes on negative values with interior values greater than 
 * boundary values, this function can be used to solve for 
 * psi = phi + C, where C is a constant offset that ensures that psi 
 * is strictly non-negative.  For problems where interior values are 
 * less than boundary values, this function can be used to solve for
 * psi = -phi.
 *
 *
 * Arguments:
 *  - phi (in/out):                       pointer to solution to Eikonal 
 *                                        equation phi must be initialized as 
 *                                        specified in the NOTES below. 
 *  - speed (in):                         pointer to speed field
 *  - mask (in):                          mask for domain of problem;
 *                                        grid points outside of the domain
 *                                        of the problem should be set to a 
 *                                        negative value.
 *  - spatial_discretization_order (in):  order of finite differences used 
 *                                        to compute spatial derivatives
 *  - grid_dims (in):                     array of index space extents for all 
 *                                        fields 
 *  - dx (in):                            array of grid cell sizes in each 
 *                                        coordinate direction
 *
 * Return value:                          error code (see NOTES for translation)
 *
 * 
 * NOTES:
 *  - When using the second-order spatial discretization, the solution
 *    phi is second-order accurate in the L-infinity norm only if the 
 *    "boundary values" of phi are specified in a layer of grid cells at 
 *    least two deep near the mathematical/physical domain boundary.  
 *    Otherwise, the values of the solution near the boundary will only 
 *    be first-order accurate.  Close to second-order convergence in the 
 *    L2 norm is achieved using the second-order scheme even if only one 
 *    layer of boundary values is specified.
 *
 *  - phi MUST be initialized so that the values for phi at grid points on 
 *    or adjacent to the boundary of the domain for the Eikonal equation 
 *    are correctly set.  All other grid points should be set to have
 *    negative values for phi.
 *
 *  - For grid points that are masked out or have speed equal to zero, phi 
 *    is set to LSMLIB_REAL_MAX.
 *
 *  - It is assumed that the phi, speed, and mask data arrays are all of 
 *    the same size.  That is, all data fields are assumed to have the 
 *    same index space extents.
 *
 *  - Both phi and the speed function MUST be strictly non-negative.
 *
 *  - It is the user's responsibility to set the speed function.
 *
 *  - If mask is set to a NULL pointer, then all grid points are treated
 *    as being in the interior of the domain.
 *
 */
int solveEikonalEquation2d(
  LSMLIB_REAL *phi,
  const LSMLIB_REAL *speed,
  LSMLIB_REAL *mask,
  const int spatial_discretization_order,
  const int *grid_dims,
  const LSMLIB_REAL *dx);

/*!
 * computeExtensionFields3d uses the FMM algorithm to compute the 
 * distance function and extension fields from the original level set
 * function, phi, and the specified source fields.  
 *
 * Arguments:
 *  - distance_function (out):            updated distance function
 *  - extension_fields (out):             extension fields
 *  - phi (in):                           original level set function
 *  - mask (in):                          mask for domain of problem;
 *                                        grid points outside of the domain
 *                                        of the problem should be set to a 
 *                                        negative value.
 *  - source_fields(in):                  source fields used to compute 
 *                                        extension fields
 *  - num_extension_fields (in):          number of extension fields to compute
 *  - spatial_discretization_order (in):  order of finite differences used 
 *                                        to compute spatial derivatives
 *  - grid_dims (in):                     array of index space extents for all 
 *                                        fields 
 *  - dx (in):                            array of grid cell sizes in each 
 *                                        coordinate direction
 *
 * Return value:                          error code (see NOTES for translation)
 *
 *
 * NOTES:
 *  - When the second-order spatial discretization is requested, only
 *    the distance function is computed using the second-order scheme.
 *    The extension fields are computed using a first-order 
 *    discretization of the gradient for the extension field and a 
 *    second-order accurate discretization of the gradient for the 
 *    distance function.  We use a first-order discretization when
 *    computing extension fields because the second-order 
 *    discretization is "unstable" and leads to amplification of the
 *    errors introduced when initializing the extension fields in 
 *    the region around the zero level set.
 *
 * -  The distance function computed when using a second-order spatial 
 *    discretization are approximately second-order accurate in the 
 *    L2 norm but are only first-order accurate in the L-infinity norm.  
 *    The reason for this behavior is that the current implementation 
 *    uses only a first-order accurate scheme for initializing the grid 
 *    points around the zero-level set.
 *
 *  - For grid points that are masked out, the distance function and
 *    extension fields are set to 0.
 *
 *  - It is assumed that the user has allocated the memory for the
 *    distance function, extension fields, phi, and source fields.
 *
 *  - It is assumed that the phi and mask data arrays are both of 
 *    the same size.  That is, all data fields are assumed to have 
 *    the same index space extents.
 *
 *  - If mask is set to a NULL pointer, then all grid points are treated
 *    as being in the interior of the domain.
 *
 *  - The number of extension fields is assumed to be equal to the
 *    number of source fields.
 *
 */
int computeExtensionFields3d(
  LSMLIB_REAL *distance_function,
  LSMLIB_REAL **extension_fields,
  LSMLIB_REAL *phi,
  LSMLIB_REAL *mask,
  LSMLIB_REAL **source_fields,
  int num_extension_fields,
  int spatial_discretization_order,
  int *grid_dims,
  LSMLIB_REAL *dx);

/*!
 * computeDistanceFunction3d uses the FMM algorithm to compute the 
 * a distance function from the original level set function, phi.
 *
 * Arguments:
 *  - distance_function (out):            updated distance function
 *  - phi (in):                           original level set function
 *  - mask (in):                          mask for domain of problem;
 *                                        grid points outside of the domain
 *                                        of the problem should be set to a 
 *                                        negative value.
 *  - spatial_discretization_order (in):  order of finite differences used 
 *                                        to compute spatial derivatives
 *  - grid_dims (in):                     array of index space extents for all 
 *                                        fields 
 *  - dx (in):                            array of grid cell sizes in each 
 *                                        coordinate direction
 *
 * Return value:                          error code (see NOTES for translation)
 *
 *
 * NOTES:
 *  - The distance function computed when using a second-order spatial 
 *    discretization are approximately second-order accurate in the 
 *    L2 norm but are only first-order accurate in the L-infinity norm.  
 *    The reason for this behavior is that the current implementation 
 *    uses only a first-order accurate scheme for initializing the grid 
 *    points around the zero-level set.
 *
 *  - For grid points that are masked out, the distance function is
 *    set to 0.
 *
 *  - It is assumed that the user has allocated the memory for the
 *    distance function and phi fields.
 *
 *  - If mask is set to a NULL pointer, then all grid points are treated
 *    as being in the interior of the domain.
 *
 *  - It is assumed that the phi and mask data arrays are both of 
 *    the same size.  That is, all data fields are assumed to have 
 *    the same index space extents.
 *
 */
int computeDistanceFunction3d(
  LSMLIB_REAL *distance_function,
  LSMLIB_REAL *phi,
  LSMLIB_REAL *mask,
  int spatial_discretization_order,
  int *grid_dims,
  LSMLIB_REAL *dx);

/*!
 * solveEikonalEquation3d uses the FMM algorithm to solve the Eikonal
 * equation 
 *
 *   |grad(phi)| = 1/speed(x,y,z)
 *
 * in three space dimensions with the specified boundary data 
 * and speed function. 
 *
 * This function assumes that the solution phi is assumed to be 
 * strictly non-negative with values in the interior of the domain 
 * greater than the values on the boundaries.  For problems where 
 * phi takes on negative values with interior values greater than 
 * boundary values, this function can be used to solve for 
 * psi = phi + C, where C is a constant offset that ensures that psi 
 * is strictly non-negative.  For problems where interior values are 
 * less than boundary values, this function can be used to solve for
 * psi = -phi.
 *
 *
 * Arguments:
 *  - phi (in/out):                       pointer to solution to Eikonal 
 *                                        equation phi must be initialized as
 *                                        specified in the NOTES below. 
 *  - speed (in):                         pointer to speed field
 *  - mask (in):                          mask for domain of problem;
 *                                        grid points outside of the domain
 *                                        of the problem should be set to a 
 *                                        negative value.
 *  - spatial_discretization_order (in):  order of finite differences used 
 *                                        to compute spatial derivatives
 *  - grid_dims (in):                     array of index space extents for all 
 *                                        fields 
 *  - dx (in):                            array of grid cell sizes in each 
 *                                        coordinate direction
 *
 * Return value:                          error code (see NOTES for translation)
 *
 *
 * NOTES:
 *  - When using the second-order spatial discretization, the solution
 *    phi is second-order accurate in the L-infinity norm only if the 
 *    "boundary values" of phi are specified in a layer of grid cells at 
 *    least two deep near the mathematical/physical domain boundary.  
 *    Otherwise, the values of the solution near the boundary will only 
 *    be first-order accurate.  Close to second-order convergence in the 
 *    L2 norm is achieved using the second-order scheme even if only one 
 *    layer of boundary values is specified.
 *
 *  - phi MUST be initialized so that the values for phi at grid points on 
 *    or adjacent to the boundary of the domain for the Eikonal equation 
 *    are correctly set.  All other grid points should be set to have
 *    negative values for phi.
 *
 *  - For grid points that are masked out or have speed equal to zero, phi 
 *    is set to LSMLIB_REAL_MAX.
 *
 *  - It is assumed that the phi, speed, and mask data arrays are all of 
 *    the same size.  That is, all data fields are assumed to have the 
 *    same index space extents.
 *
 *  - Both phi and the speed function MUST be strictly non-negative.
 *
 *  - It is the user's responsibility to set the speed function.
 *
 *  - If mask is set to a NULL pointer, then all grid points are treated
 *    as being in the interior of the domain.
 *
 */
int solveEikonalEquation3d(
  LSMLIB_REAL *phi,
  const LSMLIB_REAL *speed,
  LSMLIB_REAL *mask,
  const int spatial_discretization_order,
  const int *grid_dims,
  const LSMLIB_REAL *dx);

#ifdef __cplusplus
}
#endif

#endif
