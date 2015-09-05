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
	double Rmax;
	double Rmin;
	double Rresin;
	double n;
	double l;
} args_t;

static double enhanced_model_expr(double pac, double depth, const void *args)
{
    const args_t *dev = (const args_t*) args;

    double ki = dev->Rresin/dev->Rmin - 1;
    double ke = dev->Rmax/dev->Rresin - 1;
    double rate = dev->Rresin * (1 + ke * pow(1 - pac, dev->n)) / (1 + ki * pow(pac, dev->l));

	return rate;
};

static const dev_model_arg_t args[] = {
    {.name = "Development Rmax (nm/s)", .min = DBL(0.0), .max = NULL, .defv = 100.0},
    {.name = "Development Rmin (nm/s)", .min = DBL(0.0), .max = NULL, .defv = 0.5},
    {.name = "Development Rresin (nm/s)", .min = DBL(0.0), .max = NULL, .defv = 10.0},
    {.name = "Development n", .min = DBL(1.0), .max = NULL, .defv = 4.0},
    {.name = "Development l", .min = DBL(0.0), .max = NULL, .defv = 20.0},
};

static const dev_model_t development_model = {
    .prolith_id = INT(2),
    .name = "Enhanced Model",
    .desc = "Resist developing simulates using enhanced Mack's model",
    .expression = enhanced_model_expr,
    .args_count = 5,
    .args = &args,
};

DLL_PUBLIC plugin_descriptor_t PluginDescriptor = {
    .plugin_type = PLUGIN_DEVELOPMENT_MODEL,
    .plugin_entry = &development_model
};

#ifdef __cplusplus
}
#endif
