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

#include "opl_log.h"
#include <stdint.h>

#if !defined(SWIG)
// SWIG should not see #include <armadillo> as it can not handle it
    #include <armadillo>
#endif


#if defined(OPTOLITHIUMC_USE_FFTW_LIBRARY)
#include <fftw3.h>
#elif defined(OPTOLITHIUMC_USE_KISSFFT_LIBRARY)
#include <kiss_fftnd.h>
#include <kiss_fft.h>
#elif defined(OPTOLITHIUMC_USE_FOURIER_LIBRARY)
#include <fourier.h>
#else
#error "OPTOLITHIUMC_USE_KISSFFT_LIBRARY or OPTOLITHIUMC_USE_FFTW_LIBRARY must be set!"
#endif


namespace fft {

    enum direction_t {FFT_BACKWARD, FFT_FORWARD};

    class TransformInterface2d {
    public:
        // TransformInterface2d(arma::cx_mat &array, direction_t dir, int32_t n_times=-1) { }
        virtual void execute(void) = 0;
        virtual ~TransformInterface2d() { };
    };

#if defined(OPTOLITHIUMC_USE_FFTW_LIBRARY)
    #define FFTW_METHOD_THRESHOLD 100

    typedef fftw_plan fft_plan_t;

    class FFTW2d {
    private:
        fft_plan_t _plan;
        fftw_complex *_raw_ptr;
    public:
        FFTW2d(arma::cx_mat &array, direction_t dir, int32_t n_times = -1) {
            int fftw_dir = (dir == FFT_FORWARD) ? FFTW_FORWARD : FFTW_BACKWARD;
            this->_raw_ptr = reinterpret_cast<fftw_complex *>(&array(0, 0));

            {TIMED_SCOPE(aerial_image_fftw_plan, "Create fftw transform plan");
                const uint32_t method = (uint32_t) (n_times > FFTW_METHOD_THRESHOLD ? FFTW_MEASURE : FFTW_ESTIMATE);
                this->_plan = fftw_plan_dft_2d(array.n_cols, array.n_rows, this->_raw_ptr, this->_raw_ptr, fftw_dir, method);
            }
        }

        ~FFTW2d() {
            fftw_destroy_plan(this->_plan);
        }

        void execute(void) {
            {TIMED_SCOPE(aerial_image_timer_fftw, "FFTW calculation done");
				fftw_execute(this->_plan);
			}
        }
    };

    typedef FFTW2d FFT2d;
#elif defined(OPTOLITHIUMC_USE_KISSFFT_LIBRARY)
    class KissFFT2d : public TransformInterface2d {
    private:
        kiss_fftnd_cfg _cfg;
        kiss_fft_cpx *_out_buf;
        kiss_fft_cpx *_raw_ptr;
        uint32_t _buf_size;
        uint32_t _n_elem;
    public:
        KissFFT2d(arma::cx_mat &array, direction_t dir, int32_t n_times = -1) {
            printf("n_cols = %d, n_rows = %d\n", array.n_cols, array.n_rows);
            const int ndims = 2;
            const int dims[2] = {static_cast<int>(array.n_cols), static_cast<int>(array.n_rows)};
//            const int dims[2] = {static_cast<int>(array.n_rows), static_cast<int>(array.n_cols)};
            int is_inverse = (dir == FFT_BACKWARD) ? 1 : 0;
            this->_raw_ptr = reinterpret_cast<kiss_fft_cpx*>(&array(0, 0));
//            this->_n_elem = array.n_cols * array.n_rows;
//            this->_buf_size = static_cast<uint32_t>(this->_n_elem*sizeof(kiss_fft_cpx));
//            this->_out_buf = static_cast<kiss_fft_cpx*>(malloc(this->_buf_size));
            this->_cfg = kiss_fftnd_alloc(dims, ndims, is_inverse, NULL, NULL);
        }

        ~KissFFT2d() {
            kiss_fft_free(this->_cfg);
            free(this->_out_buf);
        }

        void execute(void) {
            {TIMED_SCOPE(aerial_image_timer_fftw, "KissFFT calculation done");
//                printf("================================================================\n");

//                kiss_fft_cpx zero;
//                zero.r = 0.0;
//                zero.i = 0.0;
//                kiss_fft_cpx tmp = this->_raw_ptr[0];
//                this->_raw_ptr[0] = this->_raw_ptr[159];
//                this->_raw_ptr[1] = tmp;
//                this->_raw_ptr[159] = tmp;
//                this->_raw_ptr[158] = zero;

//                memcpy(this->_out_buf, this->_raw_ptr, this->_buf_size);
//                for (uint32_t k = 0; k < this->_n_elem; k++) {
//                    printf("v[%d] = %.5f %.5fi\n", k, this->_out_buf[k].r, this->_out_buf[k].i);
//                }
//                memset(this->_out_buf, 0, this->_buf_size);

                kiss_fftnd(this->_cfg, this->_raw_ptr, this->_raw_ptr);

//                for (uint32_t k = 0; k < this->_n_elem; k++) {
//                    this->_out_buf[k].r /= this->_n_elem;
//                    this->_out_buf[k].i /= this->_n_elem;
//                }

//                printf("--------------------------------------------------------------\n");
//
//                for (uint32_t k = 0; k < this->_n_elem; k++) {
//                    printf("v[%d] = %.5f %.5fi\n", k, this->_out_buf[k].r, this->_out_buf[k].i);
//                }
//                memcpy(this->_raw_ptr, this->_out_buf, this->_buf_size);
            }
        }
    };

    typedef KissFFT2d FFT2d;
#elif defined(OPTOLITHIUMC_USE_FOURIER_LIBRARY)
    class Fourier2d {
    private:
        fft_plan_t* _plan;
        fft_complex_t * _raw_ptr;
    public:
        Fourier2d(arma::cx_mat &array, direction_t dir, int32_t n_times = -1) {
            int fft_dir = (dir == FFT_FORWARD) ? FFT_LITHO_FORWARD : FFT_LITHO_BACKWARD;
            this->_raw_ptr = reinterpret_cast<fft_complex_t *>(&array(0, 0));
            this->_plan = fft_plan_create_2d(
                    array.n_rows, array.n_cols, this->_raw_ptr, this->_raw_ptr,
                    fft_dir, FFT_USE_CACHE | FFT_USE_RADIX2_TABLE);
        }

        ~Fourier2d() {
            fft_plan_destroy(this->_plan);
        }

        void execute(void) {
            {TIMED_SCOPE(aerial_image_timer_fftw, "FFT calculation done");
                fft_execute_2d(this->_plan);
            }
        }
    };

    typedef Fourier2d FFT2d;
#endif

}
