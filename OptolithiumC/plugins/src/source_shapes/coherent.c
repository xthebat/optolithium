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

#include <optolithium.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
	double tilt_x;
	double tilt_y;
} args_t;

#define PRECISION 0.001

inline double round_to(double value, double precision) {
    return round(value / precision) * precision;
};

static double coherent_source_shape(double sx, double sy, const void *args) {
    const args_t *prms = (const args_t*) args;
	return (double)(
        round_to(sx, 0.001) == round_to(prms->tilt_x, 0.001) && 
        round_to(sy, 0.001) == round_to(prms->tilt_y, 0.001)
    );
};

static const source_shape_arg_t args[] = {
    {.name = "Tilt X", .min = DBL(-1.0), .max = DBL(1.0), .defv = 0.0},
    {.name = "Tilt Y", .min = DBL(-1.0), .max = DBL(1.0), .defv = 0.0},
};

static const source_shape_plugin_t source_shape_plugin = {
    .name = "Coherent",
    .desc = "Ideal model of fully spatial coherent source shape",
    .expression = coherent_source_shape,
    .args_count = 2,
    .args = &args,
};

DLL_PUBLIC plugin_descriptor_t PluginDescriptor = {
    .plugin_type = PLUGIN_SOURCE_SHAPE,
    .plugin_entry = &source_shape_plugin
};

#ifdef __cplusplus
}
#endif
