/*
 * FMM_Config2d.h
 *
 *  Created on: Aug 16, 2014
 *      Author: batman
 */

#ifndef FMM_CONFIG2D_H_
#define FMM_CONFIG2D_H_


/* Define required macros */
#define FMM_NDIM                               2
#define FMM_EIKONAL_SOLVE_EIKONAL_EQUATION     solveEikonalEquation2d
#define FMM_EIKONAL_INITIALIZE_FRONT           FMM_initializeFront_Eikonal2d
#define FMM_EIKONAL_UPDATE_GRID_POINT_ORDER1                              \
        FMM_updateGridPoint_Eikonal2d_Order1
#define FMM_EIKONAL_UPDATE_GRID_POINT_ORDER2                              \
        FMM_updateGridPoint_Eikonal2d_Order2


#endif /* FMM_CONFIG2D_H_ */
