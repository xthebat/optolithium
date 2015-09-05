/*
 * Fourier Transform library for Optolithium lithography modelling software
 *
 * Copyright (C) 2015 Alexei Gladkikh
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without modification, are permitted provided that
 * the following conditions are met:
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the
 *    documentation  and/or other materials provided with the distribution.
 * 3. Neither the names of the copyright holders nor the names of any
 *    contributors may be used to endorse or promote products derived from this
 *    software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
 * INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, ORCONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 */

#ifndef BASICS_H_
#define BASICS_H_

#ifdef __cplusplus
extern "C" {
#endif

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#include <mm_malloc.h>
#include <xmmintrin.h>
#include <pmmintrin.h>

#include "fourier.h"


#define FORCE_INLINE __attribute__((always_inline))


#if FOURIER_LOG_VERBOSE_LEVEL <= 50
extern unsigned int RECURSION_DEPTH;
#define INCREASE_RECURSION_DEPTH() RECURSION_DEPTH++;
#define DECREASE_RECURSION_DEPTH() \
    if (FOURIER_LOG_VERBOSE_LEVEL <= 50) { \
        FOURIER_LOG(50, "<--- Recursion depth: %d", RECURSION_DEPTH); \
        RECURSION_DEPTH--; \
    }

static inline void _print_log_recursion_tabs(void) {
    unsigned int k = 0;
    if (RECURSION_DEPTH > 0) {
        for (k = 0; k < RECURSION_DEPTH-1; k++) {
            fprintf(stdout, "\t");
        }
    }
}
#else
// When heavy logging disabled then remove recursion depth follow for multithreading
extern unsigned int RECURSION_DEPTH;
#define INCREASE_RECURSION_DEPTH()
#define DECREASE_RECURSION_DEPTH()
static inline void _print_log_recursion_tabs(void) { }
#endif


static char *ECHO_NAME_MAP[] = {"DEBUG", "VERBOSE", "CRITICAL"};


#define FOURIER_ASSERT(condition, level, message, ...) \
    /* This code will be optimized out if current level unsatisfied */ \
    if (level >= FOURIER_ASSERT_VERBOSE_LEVEL) { \
        if (!(condition)) { \
            fflush(stdout); \
            fprintf(stderr, "[%s] Fourier library assertion in [%s:%4d]:\n\t"message, \
                    ECHO_NAME_MAP[level], __func__, __LINE__, ##__VA_ARGS__); \
            exit(-1); \
        } \
    }


#define FOURIER_LOG(level, message, ...) \
    /* This code will be optimized out if current level unsatisfied */ \
    if (level >= FOURIER_LOG_VERBOSE_LEVEL) { \
        fprintf(stdout, "[%2d] Fourier log [%18s:%4d]: ", level, __func__, __LINE__); \
        _print_log_recursion_tabs(); \
        fprintf(stdout, message"\n", ##__VA_ARGS__); \
        fflush(stdout); \
    }


#if FOURIER_LOG_VERBOSE_LEVEL <= 50
#define INCREASE_CALCULATED_TWIDDLES(_plan) _plan->calculated_twiddles++;
#define INIT_CALCULATED_TWIDDLES(_plan) _plan->calculated_twiddles = 0;
#define PRINT_CALCULATED_TWIDDLES(_plan) \
        FOURIER_LOG(50, "Total calculated twiddles = %d", plan->calculated_twiddles);
#else
#define INCREASE_CALCULATED_TWIDDLES(_plan)
#define INIT_CALCULATED_TWIDDLES(_plan)
#define PRINT_CALCULATED_TWIDDLES(_plan)
#endif


static FORCE_INLINE void* wmalloc(size_t n_bytes) {
    void* result = _mm_malloc(n_bytes, 16);
    if (FOURIER_LOG_VERBOSE_LEVEL >= 30) {
        memset(result, 0, n_bytes);
    }
    FOURIER_LOG(30, "Allocated %d bytes of memory at %p", (unsigned int) n_bytes, result);
    return result;
}


static FORCE_INLINE void wfree(void* ptr) {
    FOURIER_LOG(30, "Memory at pointer %p has been freed", ptr);
    _mm_free(ptr);
}


#define MALLOC(count, type) (type*) wmalloc(count*sizeof(type))
#define MEMCPY(dst, src, count, type) memcpy(dst, src, count*sizeof(type))
#define FREE(ptr) \
    if (ptr != NULL) { \
        wfree(ptr); \
        ptr = NULL; \
    }


#define SWAP(type, v1, v2) \
{ \
    type tmp = v1; \
    v1 = v2; \
    v2 = tmp; \
}


#define FOURIER_ALGORITHM_STD_ASSERTS(_level, _plan, _min_samples) \
    FOURIER_ASSERT(_plan->count >= _min_samples, _level, \
        "FFT algorithm implemented only for more than %d samples in the input sequence: %d\n", \
        _min_samples, _plan->count); \
    FOURIER_ASSERT(_plan->howMany > 0, _level, "Plan howMany must be greater than zero: %d\n", _plan->howMany); \
    FOURIER_ASSERT(_plan->in != NULL, _level, "Plan input array must be allocated: %p\n", _plan->in); \
    FOURIER_ASSERT(_plan->out != NULL, _level, "Plan output array must be allocated: %p\n", _plan->out); \
    FOURIER_ASSERT(_plan->direction == FFT_LITHO_BACKWARD || _plan->direction == FFT_LITHO_FORWARD, \
                   FOURIER_ECHO_DEBUG, "Direction of FFT can be -1 or 1 but specified: %d\n", _plan->direction);


#define FOURIER_ALGORITHM_STD_LOG(_level, _plan, _name) \
    FOURIER_LOG(_level, "---> [%2d] FFT ALGORITHM: '"_name \
                "' count=%d  howMany=%d  iodist=%d/%d  iostride=%d/%d  dir=%d", \
                RECURSION_DEPTH, _plan->count, _plan->howMany, _plan->idist, _plan->odist, \
                _plan->istride, _plan->ostride, _plan->direction);


#define USE_FFT_SSE3


#ifdef USE_FFT_SSE3
static FORCE_INLINE fft_complex_t c_add(const fft_complex_t a, const fft_complex_t b) {
    __m128d x = _mm_load_pd(&a.r);
    __m128d y = _mm_load_pd(&b.r);
    __m128d z = _mm_add_pd(x, y);

    fft_complex_t result;
    _mm_store_pd((double *)&result, z);
    return result;
}
#else
static FORCE_INLINE fft_complex_t c_add(const fft_complex_t a, const fft_complex_t b) {
    fft_complex_t result = {
            .r = a.r + b.r,
            .i = a.i + b.i
    };
    return result;
}
#endif

#ifdef USE_FFT_SSE3
static FORCE_INLINE fft_complex_t c_sub(const fft_complex_t a, const fft_complex_t b) {
    __m128d x = _mm_load_pd(&a.r);
    __m128d y = _mm_load_pd(&b.r);
    __m128d z = _mm_sub_pd(x, y);

    fft_complex_t result;
    _mm_store_pd((double *)&result, z);
    return result;
}
#else
static FORCE_INLINE fft_complex_t c_sub(const fft_complex_t a, const fft_complex_t b) {
    fft_complex_t result = {
            .r = a.r - b.r,
            .i = a.i - b.i
    };
    return result;
}
#endif


#ifdef USE_FFT_SSE3
static FORCE_INLINE fft_complex_t c_mul(const fft_complex_t a, const fft_complex_t b) {
    // Duplicates lower vector element into upper vector element.
    //   num1: [x.real, x.real]
    __m128d x = _mm_loaddup_pd(&a.r);

    // Move y elements into a vector
    //   num2: [y.img, y.real]
    __m128d y = _mm_set_pd(b.i, b.r);

    // Multiplies vector elements
    //   num3: [(x.real*y.img), (x.real*y.real)]
    __m128d z = _mm_mul_pd(y, x);

    //   num1: [x.img, x.img]
    x = _mm_loaddup_pd(&a.i);

    // Swaps the vector elements
    //   num2: [y.real, y.img]
    y = _mm_shuffle_pd(y, y, 1);

    //   num2: [(x.img*y.real), (x.img*y.img)]
    y = _mm_mul_pd(y, x);

    // Adds upper vector element while subtracting lower vector element
    //   num3: [((x.real *y.img)+(x.img*y.real)),
    //          ((x.real*y.real)-(x.img*y.img))]
    z = _mm_addsub_pd(z, y);

    fft_complex_t result;
    _mm_store_pd((double *)&result, z);
    return result;
}
#else
#define C_MUL_RE(a, b) a.r * b.r - a.i * b.i
#define C_MUL_IM(a, b) a.r * b.i + a.i * b.r

static FORCE_INLINE fft_complex_t c_mul(const fft_complex_t a, const fft_complex_t b) {
    fft_complex_t result = {
            .r = C_MUL_RE(a, b),
            .i = C_MUL_IM(a, b)
    };
    return result;
}
#endif


static FORCE_INLINE fft_complex_t* c_divbyv(fft_complex_t* a, const double v) {
    a->r /= v;
    a->i /= v;
    return a;
}


static FORCE_INLINE fft_complex_t c_divv(fft_complex_t a, const double v) {
    fft_complex_t result = {
            .r = a.r / v,
            .i = a.i / v
    };
    return result;
}


static FORCE_INLINE fft_complex_t* c_addto(fft_complex_t *a, const fft_complex_t b) {
    a->r += b.r;
    a->i += b.i;
    return a;
}


static FORCE_INLINE fft_complex_t* c_subfrom(fft_complex_t *a, const fft_complex_t b) {
    a->r -= b.r;
    a->i -= b.i;
    return a;
}


static FORCE_INLINE fft_complex_t* c_mulby(fft_complex_t *a, const fft_complex_t b) {
    *a = c_mul(*a, b);
    return a;
}


static FORCE_INLINE fft_complex_t c_exp(fft_complex_t a) {
    fft_complex_t result = {
            .r = exp(a.r) * cos(a.i),
            .i = exp(a.r) * sin(a.i)
    };
    return result;
};


static FORCE_INLINE fft_complex_t c_expi(double imag) {
    fft_complex_t result = {
            .r = cos(imag),
            .i = sin(imag)
    };
    return result;
};


static FORCE_INLINE fft_complex_t c_rone(void) {
    fft_complex_t result = {
            .r = 1.0,
            .i = 0.0
    };
    return result;
}


static FORCE_INLINE fft_complex_t c_ione(void) {
    fft_complex_t result = {
            .r = 0.0,
            .i = 1.0
    };
    return result;
}


static FORCE_INLINE fft_complex_t c_zero(void) {
    fft_complex_t result = {
            .r = 0.0,
            .i = 0.0
    };
    return result;
}


static FORCE_INLINE fft_complex_t* c_clear(fft_complex_t* a) {
    a->r = 0.0;
    a->i = 0.0;
    return a;
};


static FORCE_INLINE fft_complex_t c_neg(const fft_complex_t a) {
    fft_complex_t result = {
            .r = -a.r,
            .i = -a.i
    };
    return result;
};


static FORCE_INLINE fft_complex_t c_mulpj(const fft_complex_t a) {
    fft_complex_t result = {
            .r = -a.i,
            .i = a.r
    };
    return result;
};


static FORCE_INLINE fft_complex_t c_mulnj(const fft_complex_t a) {
    fft_complex_t result = {
            .r = a.i,
            .i = -a.r
    };
    return result;
};


static FORCE_INLINE fft_complex_t c_mulj(const fft_complex_t a, const int sign) {
    FOURIER_ASSERT(sign > 0 || sign < 0, FOURIER_ECHO_DEBUG, "Sign must be > 0 or < 0");
    return (sign < 0) ? c_mulpj(a) : c_mulnj(a);
};


/*
 *  WARNING: This function can't be inlined
 */
static FORCE_INLINE fft_complex_t* c_sumto(fft_complex_t* result, const unsigned int count, ...) {
    va_list args;
    va_start(args, count);
    unsigned int k = 0;
    for (k = 0; k < count; k++) {
        fft_complex_t value = va_arg(args, fft_complex_t);
        c_addto(result, value);
    }
    va_end(args);
    return result;
}

/*
 *  WARNING: This function can't be inlined
 */
static FORCE_INLINE fft_complex_t c_sum(const unsigned int count, ...) {
    va_list args;
    va_start(args, count);
    fft_complex_t result = c_zero();
    c_sumto(&result, count, args);
    va_end(args);
    return result;
}


static FORCE_INLINE fft_complex_t* ivp(const struct fft_plan_t* plan, unsigned int s, unsigned int k) {
    fft_complex_t* result = plan->in + s * plan->istride + k * plan->idist;

    FOURIER_ASSERT(s < plan->howMany, FOURIER_ECHO_DEBUG, "Signal number (s) must be lower than plan->howMany");
    FOURIER_ASSERT(k < plan->count, FOURIER_ECHO_DEBUG, "Item number (k) must be lower than plan->count");
    FOURIER_ASSERT(s == 0 || plan->istride != 0, FOURIER_ECHO_DEBUG,
                   "s != 0 and plan->istride == 0: s = %d of %d with istride %d and k = %d of %d with idist %d",
                   s, plan->howMany, plan->istride, k, plan->count, plan->idist);
    FOURIER_ASSERT(k == 0 || plan->idist != 0, FOURIER_ECHO_DEBUG,
                   "k != 0 and plan->idist == 0: s = %d of %d with istride %d and k = %d of %d with idist %d",
                   s, plan->howMany, plan->istride, k, plan->count, plan->idist);

    FOURIER_LOG(40, "s = %d of %d with istride %d and k = %d of %d with idist %d -> (%.4f, %.4f)",
                s, plan->howMany, plan->istride, k, plan->count, plan->idist, result->r, result->i);

    return result;
}


static FORCE_INLINE fft_complex_t iv(const struct fft_plan_t* plan, unsigned int s, unsigned int k) {
    return *ivp(plan, s, k);
}


static FORCE_INLINE fft_complex_t* ovp(const struct fft_plan_t* plan, unsigned int s, unsigned int k) {
    fft_complex_t* result = plan->out + s * plan->ostride + k * plan->odist;

    FOURIER_ASSERT(s < plan->howMany, FOURIER_ECHO_DEBUG, "Signal number (s) must be lower than plan->howMany");
    FOURIER_ASSERT(k < plan->count, FOURIER_ECHO_DEBUG, "Item number (k) must be lower than plan->count");
    FOURIER_ASSERT(s == 0 || plan->ostride != 0, FOURIER_ECHO_DEBUG,
                   "s != 0 and plan->istride == 0: s = %d of %d with ostride %d and k = %d of %d with odist %d",
                   s, plan->howMany, plan->ostride, k, plan->count, plan->odist);
    FOURIER_ASSERT(k == 0 || plan->odist != 0, FOURIER_ECHO_DEBUG,
                   "k != 0 and plan->idist == 0: s = %d of %d with ostride %d and k = %d of %d with odist %d",
                   s, plan->howMany, plan->ostride, k, plan->count, plan->odist);

    FOURIER_LOG(40, "s = %d of %d with ostride %d and k = %d of %d with odist %d -> (%.4f, %.4f)",
                s, plan->howMany, plan->ostride, k, plan->count, plan->odist, result->r, result->i);

    return result;
}


static FORCE_INLINE fft_complex_t ov(const struct fft_plan_t* plan, unsigned int s, unsigned int k) {
    return *ovp(plan, s, k);
}


// Normalize array if backward transform (according to Matlab)
#if FOURIER_NORMALIZATION_TYPE != FOURIER_DISABLE_NORMALIZATION
#define FOURIER_NORMALIZE(_plan, _s, _k) \
    if (_plan->direction == FOURIER_NORMALIZATION_TYPE) { \
        for (_k = 0; _k < _plan->count; _k++) { \
            c_divbyv(ovp(_plan, _s, _k), _plan->count); \
        } \
    }
#else
#define FOURIER_NORMALIZE(_plan, _s, _k)
#endif


// This macros should be used for "manual" implementation of FFT for some samples count
// routine that specified in fft_handlers array. Each function that included in fft_handlers
// should be started with FFT_IMPLEMENTATION_BEGIN macro and finished with
// FFT_IMPLEMENTATION_END macro. In this macros defined next variables that required to
// implement FFT:
// complex iv[] - array of input values
// complex *ovp[] - array of pointers to output values
// complex w[] - array of twiddles, w[1] = twiddle(1,N)
// Between this macros code for calculation each output value of FFT should be placed.
// Begin and end macros calculate required twiddles factors, normalization (for backward
// transform), input value (according to idist, istride, inext) and output values places.
// !!! NOTE !!! Loop that used in the macros optimized by compiler to linear code execution.
#define FFT_IMPLEMENTATION_BEGIN(_plan, _length) \
        INCREASE_RECURSION_DEPTH(); \
        FOURIER_ALGORITHM_STD_LOG(50, _plan, "Butterfly"); \
        FOURIER_ALGORITHM_STD_ASSERTS(FOURIER_ECHO_DEBUG, _plan, _length) \
        FOURIER_ASSERT(_plan->count == _length, FOURIER_ECHO_DEBUG, "Samples count must be equal to %d\n", _length); \
        unsigned int k = 0, s = 0; \
        const int len = _length; \
        for (s = 0; s < _plan->howMany; s++) { \

#if FOURIER_NORMALIZATION_TYPE != FOURIER_DISABLE_NORMALIZATION
#define FFT_IMPLEMENTATION_END(_plan) \
            if (_plan->direction == FOURIER_NORMALIZATION_TYPE) { \
                for (k = 0; k < len; k++) { \
                    c_divbyv(ovp(_plan,s,k), len); \
                } \
            } \
        } \
        DECREASE_RECURSION_DEPTH();
#else
#define FFT_IMPLEMENTATION_END(_plan) } DECREASE_RECURSION_DEPTH();
#endif

#define X(k) iv(plan, s, k)

#ifdef __cplusplus
}
#endif

#endif