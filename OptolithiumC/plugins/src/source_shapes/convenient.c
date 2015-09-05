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
	double sigma;
} args_t;

#define PRECISION 0.001

inline double round_to(double value, double precision) {
    return round(value / precision) * precision;
};

inline double squared_distance(double x, double y) {
    return round_to(x, PRECISION) * round_to(x, PRECISION) + round_to(y, PRECISION) * round_to(y, PRECISION);
}

static double convenient_source_shape(double sx, double sy, const void *args) {
    const args_t *prms = (const args_t*) args;
    double sxy = squared_distance(sx, sy);
    double squared_sigma = prms->sigma * prms->sigma;
	return (double)(sxy <= squared_sigma);
};

static const source_shape_arg_t args[] = {
    {.name = "Sigma", .min = DBL(0.0), .max = DBL(1.0), .defv = 0.5},
};

static const source_shape_plugin_t source_shape_plugin = {
    .name = "Convenient",
    .desc = "Ideal convenient source shape",
    .expression = convenient_source_shape,
    .args_count = 1,
    .args = &args,
};

DLL_PUBLIC plugin_descriptor_t PluginDescriptor = {
    .plugin_type = PLUGIN_SOURCE_SHAPE,
    .plugin_entry = &source_shape_plugin
};

#ifdef __cplusplus
}
#endif
