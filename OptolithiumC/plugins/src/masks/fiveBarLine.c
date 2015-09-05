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
    double feature_space;
    double pitch_x;
    double pitch_y;
} prms_t;


#define REGION_COUNT 5
#define POINTS_COUNT 4

#define X_OFFSET 100.0
#define Y_OFFSET 500.0


void allocate_memory(mask_t *mask, const prms_t *prms)
{
    int k = 0;
    
    if (mask->regions_count == 0)
    {
        mask->regions_count = REGION_COUNT;
        mask->regions = calloc(mask->regions_count, sizeof(mask_region_t));
        
        for (k = 0; k < REGION_COUNT; k++)
        {
            mask->regions[k].length = POINTS_COUNT;
            mask->regions[k].points = calloc(mask->regions[k].length, sizeof(mask_point_t));
        }
    }
    
    if (mask->boundary.length == 0)
    {
        mask->boundary.length = 4;
        mask->boundary.points = calloc(4, sizeof(mask_point_t));
        
        mask->boundary.transmittance = 1.0;
        mask->boundary.phase = 0.0;
    }   
}

void create_rectangle(mask_point_t *points, double x, double y, double width, double height)
{
    points[0].x = x;
    points[0].y = y;
    
    points[1].x = x;
    points[1].y = y + height;
    
    points[2].x = x + width;
    points[2].y = y + height;
    
    points[3].x = x + width;
    points[3].y = y;
}

void create_centered_rectangle(mask_point_t *points, double cx, double cy, double width, double height)
{
    create_rectangle(points, cx - width/2, cy - height/2, width, height);
}

void set_pitch(mask_t *mask, prms_t *prms)
{
    double total_x = REGION_COUNT * (prms->feature_width + prms->feature_space) + X_OFFSET;
    
    if (prms->pitch_x < total_x)
        prms->pitch_x = total_x;
        
    create_centered_rectangle(mask->boundary.points, 0.0, 0.0, prms->pitch_x, prms->pitch_y);
}

void create_primary_line(mask_region_t *region, const prms_t *prms)
{
    double y0 = Y_OFFSET - prms->pitch_y/2;
    double y1 = prms->pitch_y/2 - Y_OFFSET;
    double height = y1 - y0;
    create_rectangle(region->points, -prms->feature_width/2, y0, prms->feature_width, height);
}

void create_secondary_lines(mask_region_t *regions, const prms_t *prms)
{
    int k = 0;
    
    double y0 = Y_OFFSET - prms->pitch_y/2;
    double y1 = 0.0;
    double height = y1 - y0;
    
    double dx = prms->feature_width/2 + prms->feature_space;
    
    for (k = 0; k < (REGION_COUNT - 1)/2; k++)
    {
        double x0 = dx + k * (prms->feature_width + prms->feature_space);
        create_rectangle(regions[2*k].points, x0, y0, prms->feature_width, height);
        create_rectangle(regions[2*k+1].points, -x0 - prms->feature_width, y0, prms->feature_width, height);
    }
}

static int create_mask(mask_t *mask, void *parameters)
{
    prms_t *prms = (prms_t*) parameters;
    
    allocate_memory(mask, prms);
    set_pitch(mask, prms);
    create_primary_line(&mask->regions[0], prms);
    create_secondary_lines(&mask->regions[1], prms);
    
    return 0;
};

static const mask_parameter_t parameters[] = {
    {.name = "Feature Width (nm)", .min = DBL(0.0), .max = NULL, .defv = 250.0},
    {.name = "Feature Space (nm)", .min = DBL(0.0), .max = NULL, .defv = 500.0},
    {.name = "Pitch X (nm)", .min = DBL(0.0), .max = NULL, .defv = 2000.0},
    {.name = "Pitch Y (nm)", .min = DBL(0.0), .max = NULL, .defv = 8000.0},
};

static const mask_plugin_t mask_plugin = {
    .name = "2D Five Bar Lines",
    .desc = "Two dimensions five bar lines features",
    .type = MASK_TYPE_2D,
    .create = create_mask,
    .parameters_count = 4,
    .parameters = &parameters,
};

DLL_PUBLIC plugin_descriptor_t PluginDescriptor = {
    .plugin_type = PLUGIN_MASK,
    .plugin_entry = &mask_plugin
};

#ifdef __cplusplus
}
#endif
