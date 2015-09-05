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
    double feature_width;
    double pitch;
} prms_t;

int set_mask_parameters(mask_t *mask, const void *parameters)
{
    const prms_t *prms = (const prms_t*) parameters;
    
    // Boundary half pitch in each direction
    mask->boundary.points[0].x = -prms->pitch/2;
    mask->boundary.points[1].x = prms->pitch/2;
    
    // Feature half width in each direction
    mask->regions[0].points[0].x = -prms->feature_width/2;
    mask->regions[0].points[1].x = prms->feature_width/2;
    
    // Black line
    mask->regions[0].transmittance = 0.0;
    mask->regions[0].phase = 0.0;
    
    return 0;
}

static int create_mask_line_1d(mask_t *mask, void *parameters)
{
    if (mask->regions_count == 0)
    {
        mask->regions_count = 1;
        mask->regions = calloc(mask->regions_count, sizeof(mask_region_t));
        
        mask->regions[0].length = 2;
        mask->regions[0].points = calloc(2, sizeof(mask_point_t));
    }
    
    if (mask->boundary.length == 0)
    {
        mask->boundary.length = 2;
        mask->boundary.points = calloc(2, sizeof(mask_point_t));
        
        mask->boundary.transmittance = 1.0;
        mask->boundary.phase = 0.0;
    }
    
    return set_mask_parameters(mask, parameters);
};

static const mask_parameter_t parameters[] = {
    {.name = "Feature Width (nm)", .min = DBL(0.0), .max = NULL, .defv = 250.0},
    {.name = "Pitch (nm)", .min = DBL(0.0), .max = NULL, .defv = 800.0}
};

static const mask_plugin_t mask = {
    .name = "1D Binary - Line",
    .desc = "One dimensional binary line feature",
    .type = MASK_TYPE_1D,
    .create = create_mask_line_1d,
    .parameters_count = 2,
    .parameters = &parameters,
};

DLL_PUBLIC plugin_descriptor_t PluginDescriptor = {
    .plugin_type = PLUGIN_MASK,
    .plugin_entry = &mask
};

#ifdef __cplusplus
}
#endif
