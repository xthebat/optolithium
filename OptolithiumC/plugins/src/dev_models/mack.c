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
	double Mth;
	double n;
} args_t;

static double mack_model_expr(double pac, double depth, const void *args)
{
    const args_t *dev = (const args_t*) args;

	double a = (dev->n + 1)/(dev->n - 1) * pow(1 - dev->Mth, dev->n);
	double p = pow(1 - pac, dev->n);
	double rate = dev->Rmax * (a + 1) * p  / (a + p) + dev->Rmin;

	return rate;
};

static const dev_model_arg_t args[] = {
    {.name = "Development Rmax (nm/s)", .min = DBL(0.0), .max = NULL, .defv = 100.0},
    {.name = "Development Rmin (nm/s)", .min = DBL(0.0), .max = NULL, .defv = 0.5},
    {.name = "Development Mth", .min = NULL, .max = DBL(1.0), .defv = 0.5},
    {.name = "Development n", .min = DBL(1.0), .max = NULL, .defv = 2.0},
};

static const dev_model_t development_model = {
    .prolith_id = INT(1),
    .name = "Mack Model",
    .desc = "Resist developing simulates using original Mack's model",
    .expression = mack_model_expr,
    .args_count = 4,
    .args = &args,
};

DLL_PUBLIC plugin_descriptor_t PluginDescriptor = {
    .plugin_type = PLUGIN_DEVELOPMENT_MODEL,
    .plugin_entry = &development_model
};

#ifdef __cplusplus
}
#endif
