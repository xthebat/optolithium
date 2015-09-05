/*
 * Benchmark and test the Fourier library for Optolithium software
 *
 * Copyright (C) 2015 Alexei Gladkikh
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
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
 */

#include <fftw3.h>
#include <fourier.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>
#include <sys/time.h>


#define MEASURE_START() { \
    struct timeval tval_before, tval_after, tval_result; \
    gettimeofday(&tval_before, NULL);


#define MEASURE_FINISH(result) \
    gettimeofday(&tval_after, NULL); \
    timersub(&tval_after, &tval_before, &tval_result); \
    result = (double) (tval_result.tv_sec) + (double)(tval_result.tv_usec)/1.0E6; \
}

#define FFT_DIRECTION FFT_LITHO_FORWARD
//#define FFT_DIRECTION FFT_LITHO_BACKWARD

#define N_START 1

#define N_STOP 1024
//#define N_STOP 5

#define HOW_MANY 128
#define ERROR_THRESHOLD 1.0
#define PRINT_EVERY_NTEST 512

#define USE_FFTW_ONE_EXECUTE

//#define ONLY_POWER_OF_2


int main(int argc, char* argv[]) {
    unsigned int n_test, s = 0;
    double sum_coef = 0.0;
    double sum_fourier_time = 0.0;
    double sum_fftw_time = 0.0;
    unsigned int count = 0;
    unsigned int total_prime = 0;
    unsigned int total_radix2 = 0;
    unsigned int total_mixed = 0;

    double ft_rate = 0.0;
    double fftw_rate = 0.0;

    double mean_ft_rate = 0.0;
    double mean_fftw_rate = 0.0;

    double prime_time_fftw = 0.0;
    double radix2_time_fftw = 0.0;
    double mixed_time_fftw = 0.0;

    double prime_time_ft = 0.0;
    double radix2_time_ft = 0.0;
    double mixed_time_ft = 0.0;

    time_t current_time;
    time(&current_time);
    srand((unsigned int) current_time);

    double fftw_time, fourier_time;

    fft_initialize_radix_2();

    for (n_test = N_START; n_test <= N_STOP; n_test++) {
#ifdef ONLY_POWER_OF_2
        if (is_power2(n_test)) {
#endif
            unsigned int total = HOW_MANY * n_test;

            fft_complex_t *in_buf = (fft_complex_t *) malloc(total * sizeof(fft_complex_t));
            fft_complex_t *opl_buf = (fft_complex_t *) malloc(total * sizeof(fft_complex_t));
        #ifdef USE_FFTW_ONE_EXECUTE
            fftw_complex *fftw_buf_in = (fftw_complex *) malloc(total * sizeof(fftw_complex));
            fftw_complex *fftw_buf_out = (fftw_complex *) malloc(total * sizeof(fftw_complex));

            for (s = 0; s < total; s++) {
                in_buf[s].r = opl_buf[s].r = fftw_buf_in[s][0] = (double) (rand() % 32768) / 512.0;
                in_buf[s].i = opl_buf[s].i = fftw_buf_in[s][1] = (double) (rand() % 32768) / 512.0;
            }
        #else
            fftw_complex *fftw_buf = (fftw_complex *) malloc(total * sizeof(fftw_complex));

            for (s = 0; s < total; s++) {
                in_buf[s].r = opl_buf[s].r = fftw_buf[s][0] = (double) (rand() % 32768) / 512.0;
                in_buf[s].i = opl_buf[s].i = fftw_buf[s][1] = (double) (rand() % 32768) / 512.0;
            }
        #endif

//            for (s = 0; s < total; s++) {
//                in_buf[s].r = opl_buf[s].r = fftw_buf[s][0] = 10.0*(s+1);
//                in_buf[s].i = opl_buf[s].i = fftw_buf[s][1] = 4.0*(s+1);
//            }

            MEASURE_START()
#ifdef USE_FFTW_ONE_EXECUTE
                int dims[1] = { n_test };
                fftw_plan fftw_pln = fftw_plan_many_dft(
                        1, dims, HOW_MANY,
                        fftw_buf_in, dims, 1, n_test,
                        fftw_buf_out, dims, 1, n_test,
                        FFT_DIRECTION, FFTW_ESTIMATE);
                fftw_execute(fftw_pln);
#else
                fftw_complex *tmp = fftw_buf;
                unsigned int k = 0;
                for (k = 0; k < HOW_MANY; k++) {
                    fftw_plan fftw_pln = fftw_plan_dft_1d(n_test, tmp, tmp, FFT_DIRECTION, FFTW_ESTIMATE);
                    fftw_execute(fftw_pln);
                    tmp += n_test;
                }
#endif
            MEASURE_FINISH(fftw_time)

            MEASURE_START()
//                struct fft_plan_t* opl_plan = fft_plan_create_many_1d(n_test, HOW_MANY, opl_buf, opl_buf, FFT_DIRECTION, FFT_NO_FLAGS);
//                struct fft_plan_t* opl_plan = fft_plan_create_many_1d(n_test, HOW_MANY, opl_buf, opl_buf, FFT_DIRECTION, FFT_USE_RADIX2_TABLE);
//                struct fft_plan_t* opl_plan = fft_plan_create_many_1d(n_test, HOW_MANY, opl_buf, opl_buf, FFT_DIRECTION, FFT_USE_CACHE);
                struct fft_plan_t *opl_plan = fft_plan_create_many_1d(
                        n_test, HOW_MANY, opl_buf, opl_buf, FFT_DIRECTION, FFT_USE_CACHE | FFT_USE_RADIX2_TABLE);
                fft_execute(opl_plan);
            MEASURE_FINISH(fourier_time)

            double std = 0.0, error = 0.0;
            for (s = 0; s < total; s++) {
#ifdef USE_FFTW_ONE_EXECUTE
                double dr = fabs(opl_buf[s].r - fftw_buf_out[s][0]);
                double di = fabs(opl_buf[s].i - fftw_buf_out[s][1]);
#else
                double dr = fabs(opl_buf[s].r - fftw_buf[s][0]);
                double di = fabs(opl_buf[s].i - fftw_buf[s][1]);
#endif
                std += sqrt(dr * dr + di * di);
            }

            ft_rate += 5 * n_test * log2(n_test) / (fourier_time * 1E6 / (double) HOW_MANY);
            fftw_rate += 5 * n_test * log2(n_test) / (fftw_time * 1E6 / (double) HOW_MANY);

            mean_ft_rate += ft_rate;
            mean_fftw_rate += fftw_rate;

            fftw_time /= (double) HOW_MANY;
            fourier_time /= (double) HOW_MANY;

            std /= (double) (total);
            sum_fftw_time += fftw_time;
            sum_fourier_time += fourier_time;
            sum_coef += (fourier_time / fftw_time);
            count++;

            if (is_prime(n_test)) {
                prime_time_fftw += fftw_time;
                prime_time_ft += fourier_time;
                total_prime++;
            } else if (is_power2(n_test)) {
                radix2_time_fftw += fftw_time;
                radix2_time_ft += fourier_time;
                total_radix2++;
            } else {
                mixed_time_fftw += fftw_time;
                mixed_time_ft += fourier_time;
                total_mixed++;
            }

#ifdef ONLY_POWER_OF_2
            if (is_power2(n_test) || std > ERROR_THRESHOLD) {
#else
            if (n_test % PRINT_EVERY_NTEST == 0 || std > ERROR_THRESHOLD) {
#endif
                printf("---- [%6d] Results Fourier/FFTW -> cur: |%6d|%.6f|%.6f| = %7.2f total: |%.6f|%.6f| mean = %5.2f Rate: |%5.0f|%5.0f| ----\n",
                       n_test, n_test,
                       fourier_time, fftw_time, fourier_time / fftw_time,
                       sum_fourier_time, sum_fftw_time,
                       sum_coef / (double) count,
                       ft_rate/(double)count, fftw_rate/(double)count);
                fflush(stdout);
                sum_fftw_time = 0;
                sum_fourier_time = 0;
                sum_coef = 0;
                count = 0;
                ft_rate = 0;
                fftw_rate = 0;
            }

            if (std > ERROR_THRESHOLD) {
                for (s = 0; s < total; s++) {
#ifdef USE_FFTW_ONE_EXECUTE
                    printf("values[%3d] = (%.3f, %.3fi) -> fftw = (%.3f, %.3fi) opl = (%.3f, %.3fi)\n",
                           s, in_buf[s].r, in_buf[s].i, fftw_buf_out[s][0], fftw_buf_out[s][1], opl_buf[s].r, opl_buf[s].i);
#else
                    printf("values[%3d] = (%.3f, %.3fi) -> fftw = (%.3f, %.3fi) opl = (%.3f, %.3fi)\n",
                           s, in_buf[s].r, in_buf[s].i, fftw_buf[s][0], fftw_buf[s][1], opl_buf[s].r, opl_buf[s].i);
#endif
                }
                printf("ERROR: TEST WAS NOT PASSED! -> TOO BIG ERROR\n");
                return -1;
            }

            free(in_buf);
            free(opl_buf);
#ifdef USE_FFTW_ONE_EXECUTE
            free(fftw_buf_out);
            free(fftw_buf_in);
#else
            free(fftw_buf);
#endif
#ifdef ONLY_POWER_OF_2
        }
#endif
    }

    const unsigned int total = total_mixed+total_prime+total_radix2;
    printf("Total count: %d\n", total);
    printf("Fourier/FFTW total -> prime %d radix-2 %d mixed %d\n", total_prime, total_radix2, total_mixed);
    printf("Fourier/FFTW total -> prime |%.6f|%.6f| radix-2 |%.6f|%.6f| mixed |%.6f|%.6f|\n",
           prime_time_ft, prime_time_fftw, radix2_time_ft, radix2_time_fftw, mixed_time_ft, mixed_time_fftw);
    printf("Fourier/FFTW mean  -> prime |%.6f|%.6f| radix-2 |%.6f|%.6f| mixed |%.6f|%.6f|\n",
            prime_time_ft/(double)total_prime,
            prime_time_fftw/(double)total_prime,
            radix2_time_ft/(double)total_radix2,
            radix2_time_fftw/(double)total_radix2,
            mixed_time_ft/(double)total_mixed,
            mixed_time_fftw/(double)total_mixed);
    printf("Mean rate Fourier/FFTW: |%5.0f|%5.0f|\n", mean_ft_rate/(double) total, mean_fftw_rate/(double) total);

    return 0;
}