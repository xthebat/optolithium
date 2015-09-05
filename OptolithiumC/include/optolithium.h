/*
 *
 * This file is part of Optolithium lithography modelling software.
 *
 * Copyright (C) 2015 Alexei Gladkikh
 *
 * This software is dual-licensed: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version only for NON-COMMERCIAL usage.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 *
 * If you are interested in other licensing models, including a commercial-
 * license, please contact the author at gladkikhalexei@gmail.com
 *
 */

#ifndef OPTOLITHIUM_SDK_H_
#define OPTOLITHIUM_SDK_H_

#include <stdlib.h>
#include <math.h>
#include <float.h>
#include <complex.h>


#if defined _WIN32 || defined __CYGWIN__
    #ifdef __GNUC__
        #define DLL_PUBLIC __attribute__ ((dllexport))
    #else
        #define DLL_PUBLIC __declspec(dllexport) // Note: actually gcc seems to also supports this syntax.
    #endif
    #define DLL_LOCAL
#else
    #if __GNUC__ >= 4
        #define DLL_PUBLIC __attribute__ ((visibility ("default")))
        #define DLL_LOCAL  __attribute__ ((visibility ("hidden")))
    #else
        #define DLL_PUBLIC
        #define DLL_LOCAL
    #endif
#endif


#ifdef __cplusplus
extern "C" {
#endif


// Plugin type description
typedef enum {
    PLUGIN_MASK = 0,
    PLUGIN_DEVELOPMENT_MODEL = 1,
    PLUGIN_SOURCE_SHAPE = 2,
    PLUGIN_ILLUMINATION = 3,
    PLUGIN_MATERIAL = 4,
    PLUGIN_PUPIL_FILTER = 5,
} plugin_type_t;


// Plugin entry point type: this structure must export each shared library to being plugin
typedef struct {
    plugin_type_t plugin_type;
    const void* plugin_entry;
} plugin_descriptor_t;


#define INT(value) (int[]){value}
#define DBL(value) (double[]){value}


typedef struct {
    const char *name;
    double defv;
    double *min;
    double *max;
} standard_plugin_arg_t;


// ====================================================================================================================
// Development model plugin descriptions types
// ====================================================================================================================
typedef double (*rate_model_expr_t)(double pac, double depth, const void *args);

typedef standard_plugin_arg_t dev_model_arg_t;

typedef struct {
    const int *prolith_id;
    const char *name;
    const char *desc;
    rate_model_expr_t expression;
    const int args_count;
    const dev_model_arg_t (*args)[];
} dev_model_t;

// ====================================================================================================================
// Mask plugin descriptions types
// ====================================================================================================================
typedef enum {
    MASK_TYPE_1D = 1,
    MASK_TYPE_2D = 2
} mask_type_t;

typedef struct {
    double x;
    double y;
} mask_point_t;

typedef struct {
    double transmittance;
    double phase;
    int length;
    mask_point_t *points;
} mask_region_t;

typedef struct {
    mask_region_t boundary;
    int regions_count;
    mask_region_t *regions;
} mask_t;

typedef int (*mask_create_t)(mask_t *mask, void *parameters);

typedef standard_plugin_arg_t mask_parameter_t;

typedef struct {
    const char *name;
    const char *desc;
    
    const mask_type_t type;
    
    mask_create_t create;
    
    const int parameters_count;
    const mask_parameter_t (*parameters)[];
} mask_plugin_t;


// ====================================================================================================================
// Source shape plugin interface
// ====================================================================================================================
typedef double (*source_shape_expr_t)(double sx, double sy, const void *args);

typedef standard_plugin_arg_t source_shape_arg_t;

typedef struct {
    const char *name;
    const char *desc;
    source_shape_expr_t expression;
    const int args_count;
    const source_shape_arg_t (*args)[];
} source_shape_plugin_t;

// ====================================================================================================================
// Pupil filter plugin interface
// ====================================================================================================================
typedef double _Complex (*pupil_filter_expr_t)(double cx, double cy, const void *args);

typedef standard_plugin_arg_t pupil_filter_arg_t;

typedef struct {
    const char *name;
    const char *desc;
    pupil_filter_expr_t expression;
    const int args_count;
    const pupil_filter_arg_t (*args)[];
} pupil_filter_plugin_t;

#ifdef __cplusplus
}
#endif

#endif /*OPTOLITHIUM_SDK_H_*/
