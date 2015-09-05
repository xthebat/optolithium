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
    double number_of_srafs;
    double sraf_size;
    double sraf_space2main;
    double sraf_space2sraf;
} prms_t;

int get_number_of_regions(int number_of_srafs)
{
    int srafs_regions = (number_of_srafs % 2 == 0) ? number_of_srafs : (number_of_srafs + 1);
    return srafs_regions + 1;
}

void allocate_memory(mask_t* mask, const prms_t* prms)
{
    int k = 0;
    
    int number_of_srafs = (int)prms->number_of_srafs;
    
    for (k = 0; k < mask->regions_count; k++)
        free(mask->regions[k].points);
    free(mask->regions);
    
    mask->regions_count = get_number_of_regions(number_of_srafs);
    mask->regions = calloc(mask->regions_count, sizeof(mask_region_t));
        
    for (k = 0; k < mask->regions_count; k++)
    {
        mask->regions[k].length = 2;
        mask->regions[k].points = calloc(2, sizeof(mask_point_t));
    }
    
    if (mask->boundary.length == 0)
    {
        mask->boundary.length = 2;
        mask->boundary.points = calloc(2, sizeof(mask_point_t));
        
        mask->boundary.transmittance = 1.0;
        mask->boundary.phase = 0.0;
    }
}

void set_pitch(mask_t *mask, const prms_t *prms)
{
    // Boundary half pitch in each direction
    mask->boundary.points[0].x = -prms->pitch/2;
    mask->boundary.points[1].x = prms->pitch/2;
}

void create_primary_line(mask_region_t *region, const prms_t *prms)
{    
    // Feature half width in each direction
    region->points[0].x = -prms->feature_width/2;
    region->points[1].x = prms->feature_width/2;
    
    // Black line
    region->transmittance = 0.0;
    region->phase = 0.0;
}

void create_odd_srafs(mask_region_t *left, mask_region_t *right, const prms_t *prms)
{
    left->points[0].x = -prms->pitch/2;
    left->points[1].x = -prms->pitch/2 + prms->sraf_size/2;
    
    right->points[0].x = prms->pitch/2 - prms->sraf_size/2;
    right->points[1].x = prms->pitch/2;
}

void create_srafs(mask_region_t *regions, const prms_t *prms, int count)
{
    int k = 0;
    
    for (k = 0; k < count/2; k++)
    {
        double x0 = prms->feature_width/2 + prms->sraf_space2main + k * (prms->sraf_size + prms->sraf_space2sraf);
        
        regions[2*k].points[0].x = x0;
        regions[2*k].points[1].x = x0 + prms->sraf_size;
        
        regions[2*k+1].points[0].x = -x0;
        regions[2*k+1].points[1].x = -(x0 + prms->sraf_size);
    }
}

static int create_mask_line_1d_sraf(mask_t *mask, void *parameters)
{
    int k = 0;
    prms_t *prms = (prms_t*) parameters;
    
    allocate_memory(mask, prms);
    
    create_primary_line(&mask->regions[0], prms);
    
    int number_of_srafs = (int) prms->number_of_srafs;
    
    double total_sraf_size = number_of_srafs * prms->sraf_size;
    double total_sraf_space = (number_of_srafs - 1) * prms->sraf_space2sraf + 2 * prms->sraf_space2main;
    
    if (number_of_srafs % 2 != 0)
    {
        prms->pitch = prms->feature_width + total_sraf_size + total_sraf_space;

        create_odd_srafs(&mask->regions[1], &mask->regions[2], prms);
        create_srafs(&mask->regions[3], prms, number_of_srafs - 1);
    }
    else
    {
        //double total_sraf_space = number_of_srafs * prms->sraf_space2sraf + 2 * prms->sraf_space2main;
        double required_pitch = prms->feature_width + total_sraf_space + total_sraf_size;
        
        if (prms->pitch < required_pitch)
            prms->pitch = required_pitch;
        create_srafs(&mask->regions[1], prms, number_of_srafs);
    }
    
    set_pitch(mask, prms);
    
    return 0;
};

static const mask_parameter_t parameters[] = {
    {.name = "Feature Width (nm)", .min = DBL(0.0), .max = NULL, .defv = 250.0},
    {.name = "Pitch (nm)", .min = DBL(0.0), .max = NULL, .defv = 800.0},
    {.name = "Number Of SRAFs", .min = DBL(1), .max = DBL(6), .defv = 2.0},
    {.name = "SRAF Size (nm)", .min = DBL(1.0), .max = NULL, .defv = 80.0},
    {.name = "SRAF Space to Primary (nm)", .min = DBL(1.0), .max = NULL, .defv = 300.0},
    {.name = "Space between SRAF's (nm)", .min = DBL(1.0), .max = NULL, .defv = 100.0}
};

static const mask_plugin_t mask = {
    .name = "1D Binary SRAF - Line",
    .desc = "One dimensional binary line feature with subresolution features",
    .type = MASK_TYPE_1D,
    .create = create_mask_line_1d_sraf,
    .parameters_count = 6,
    .parameters = &parameters,
};

DLL_PUBLIC plugin_descriptor_t PluginDescriptor = {
    .plugin_type = PLUGIN_MASK,
    .plugin_entry = &mask
};

#ifdef __cplusplus
}
#endif
