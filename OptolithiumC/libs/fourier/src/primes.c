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

#include "primes.h"


void fft_litho_c2(struct fft_plan_t *plan) {
    FFT_IMPLEMENTATION_BEGIN(plan, 2);

        *ovp(plan, s, 0) = c_add(X(0), X(1));
        *ovp(plan, s, 1) = c_sub(X(0), X(1));

    FFT_IMPLEMENTATION_END(plan);
}


const static fft_complex_t TWIDDLE_ARRAY_R3[2][3] = {
        {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r = -0.4999999999999998, .i = -0.8660254037844388},
                { .r = -0.5000000000000004, .i =  0.8660254037844384},
        }, {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r = -0.4999999999999998, .i =  0.8660254037844388},
                { .r = -0.5000000000000004, .i = -0.8660254037844384},
        }
};


FORCE_INLINE fft_complex_t c_add3(const fft_complex_t a, const fft_complex_t b, const fft_complex_t c) {
    fft_complex_t result = {
            .r = a.r + b.r + c.r,
            .i = a.i + b.i + c.i
    };
    return result;
}


#define CALC_S3(k1, k2) c_add3(X(0), c_mul(w[k1], X(1)), c_mul(w[k2], X(2)))


void fft_litho_c3(struct fft_plan_t *plan) {
    FFT_IMPLEMENTATION_BEGIN(plan, 3);

        const fft_complex_t *w = TWIDDLE_ARRAY_R3[plan->direction == FFT_LITHO_BACKWARD];
        *ovp(plan, s, 0) = c_add3(X(0), X(1), X(2));
        *ovp(plan, s, 1) = CALC_S3(1, 2);
        *ovp(plan, s, 2) = CALC_S3(2, 1);

    FFT_IMPLEMENTATION_END(plan);
}


FORCE_INLINE fft_complex_t c_add4(const fft_complex_t a, const fft_complex_t b, const fft_complex_t c, const fft_complex_t d) {
    fft_complex_t result = {
            .r = a.r + b.r + c.r + d.r,
            .i = a.i + b.i + c.i + d.i
    };
    return result;
}


void fft_litho_c4(struct fft_plan_t *plan) {
    FFT_IMPLEMENTATION_BEGIN(plan, 4);

        const int d = plan->direction;

        *ovp(plan, s, 0) = c_add4(X(0),        X(1),            X(2),         X(3));
        *ovp(plan, s, 1) = c_add4(X(0), c_mulj(X(1), -d), c_neg(X(2)), c_mulj(X(3),  d));
        *ovp(plan, s, 2) = c_add4(X(0),  c_neg(X(1)),           X(2),   c_neg(X(3)));
        *ovp(plan, s, 3) = c_add4(X(0), c_mulj(X(1),  d), c_neg(X(2)), c_mulj(X(3), -d));

    FFT_IMPLEMENTATION_END(plan);
}


const static fft_complex_t TWIDDLE_ARRAY_R5[2][5] = {
        {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.3090169943749475, .i = -0.9510565162951535},
                { .r = -0.8090169943749473, .i = -0.5877852522924732},
                { .r = -0.8090169943749475, .i =  0.5877852522924730},
                { .r =  0.3090169943749472, .i =  0.9510565162951536},
        }, {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.3090169943749475, .i =  0.9510565162951535},
                { .r = -0.8090169943749473, .i =  0.5877852522924732},
                { .r = -0.8090169943749475, .i = -0.5877852522924730},
                { .r =  0.3090169943749472, .i = -0.9510565162951536},
        }
};


FORCE_INLINE fft_complex_t c_add5(
        const fft_complex_t x0, const fft_complex_t x1, const fft_complex_t x2,
        const fft_complex_t x3, const fft_complex_t x4) {
    fft_complex_t result = {
            .r = x0.r + x1.r + x2.r + x3.r + x4.r,
            .i = x0.i + x1.i + x2.i + x3.i + x4.i
    };
    return result;
}


#define CALC_S5(k1, k2, k3, k4) \
    c_add5(X(0), \
        c_mul(w[k1], X(1)), c_mul(w[k2], X(2)), c_mul(w[k3], X(3)), c_mul(w[k4], X(4)))


void fft_litho_c5(struct fft_plan_t *plan) {
    FFT_IMPLEMENTATION_BEGIN(plan, 5);

        const fft_complex_t *w = TWIDDLE_ARRAY_R5[plan->direction == FFT_LITHO_BACKWARD];

        *ovp(plan, s, 0) = c_add5(X(0), X(1), X(2), X(3), X(4));
        *ovp(plan, s, 1) = CALC_S5(1, 2, 3, 4);
        *ovp(plan, s, 2) = CALC_S5(2, 4, 1, 3);
        *ovp(plan, s, 3) = CALC_S5(3, 1, 4, 2);
        *ovp(plan, s, 4) = CALC_S5(4, 3, 2, 1);

    FFT_IMPLEMENTATION_END(plan);
}


const static fft_complex_t TWIDDLE_ARRAY_R6[2][6] = {
        {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.5000000000000001, .i = -0.8660254037844386},
                { .r = -0.4999999999999998, .i = -0.8660254037844388},
                { .r = -1.0000000000000000, .i = -0.0000000000000001},
                { .r = -0.5000000000000004, .i =  0.8660254037844384},
                { .r =  0.4999999999999993, .i =  0.8660254037844390},
        }, {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.5000000000000001, .i =  0.8660254037844386},
                { .r = -0.4999999999999998, .i =  0.8660254037844388},
                { .r = -1.0000000000000000, .i =  0.0000000000000001},
                { .r = -0.5000000000000004, .i = -0.8660254037844384},
                { .r =  0.4999999999999993, .i = -0.8660254037844390},

        }
};


void fft_litho_c6(struct fft_plan_t *plan) {
    FFT_IMPLEMENTATION_BEGIN(plan, 6);

        const fft_complex_t *w3 = TWIDDLE_ARRAY_R3[plan->direction == FFT_LITHO_BACKWARD];
        const fft_complex_t *w6 = TWIDDLE_ARRAY_R6[plan->direction == FFT_LITHO_BACKWARD];

        const fft_complex_t e[3] = {
                c_add3(X(0), X(2), X(4)),
                c_add3(X(0), c_mul(w3[1], X(2)), c_mul(w3[2], X(4))),
                c_add3(X(0), c_mul(w3[2], X(2)), c_mul(w3[1], X(4))),
        };

        const fft_complex_t o[3] = {
                c_add3(X(1), X(3), X(5)),
                c_mul(w6[1], c_add3(X(1), c_mul(w3[1], X(3)), c_mul(w3[2], X(5)))),
                c_mul(w6[2], c_add3(X(1), c_mul(w3[2], X(3)), c_mul(w3[1], X(5)))),
        };

        *ovp(plan, s, 0) = c_add(e[0], o[0]);
        *ovp(plan, s, 1) = c_add(e[1], o[1]);
        *ovp(plan, s, 2) = c_add(e[2], o[2]);
        *ovp(plan, s, 3) = c_sub(e[0], o[0]);
        *ovp(plan, s, 4) = c_sub(e[1], o[1]);
        *ovp(plan, s, 5) = c_sub(e[2], o[2]);

    FFT_IMPLEMENTATION_END(plan);
}


const static fft_complex_t TWIDDLE_ARRAY_R7[2][7] __attribute__ ((aligned (16))) = {
        {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.6234898018587336, .i = -0.7818314824680297},
                { .r = -0.2225209339563143, .i = -0.9749279121818236},
                { .r = -0.9009688679024190, .i = -0.4338837391175582},
                { .r = -0.9009688679024191, .i =  0.4338837391175580},
                { .r = -0.2225209339563146, .i =  0.9749279121818235},
                { .r =  0.6234898018587334, .i =  0.7818314824680299},
        }, {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.6234898018587336, .i =  0.7818314824680297},
                { .r = -0.2225209339563143, .i =  0.9749279121818236},
                { .r = -0.9009688679024190, .i =  0.4338837391175582},
                { .r = -0.9009688679024191, .i = -0.4338837391175580},
                { .r = -0.2225209339563146, .i = -0.9749279121818235},
                { .r =  0.6234898018587334, .i = -0.7818314824680299},
        }
};


FORCE_INLINE fft_complex_t c_add7(
        const fft_complex_t x0, const fft_complex_t x1, const fft_complex_t x2, const fft_complex_t x3,
        const fft_complex_t x4, const fft_complex_t x5, const fft_complex_t x6) {
    fft_complex_t result = {
            .r = x0.r + x1.r + x2.r + x3.r + x4.r + x5.r + x6.r,
            .i = x0.i + x1.i + x2.i + x3.i + x4.i + x5.i + x6.i
    };
    return result;
}


#define CALC_S7(k1, k2, k3, k4, k5, k6) \
    c_add7(X(0), \
        c_mul(w[k1], X(1)), c_mul(w[k2], X(2)), c_mul(w[k3], X(3)), \
        c_mul(w[k4], X(4)), c_mul(w[k5], X(5)), c_mul(w[k6], X(6)))


void fft_litho_c7(struct fft_plan_t *plan) {
    FFT_IMPLEMENTATION_BEGIN(plan, 7);

        const fft_complex_t *w = TWIDDLE_ARRAY_R7[plan->direction == FFT_LITHO_BACKWARD];
        *ovp(plan, s, 0) = c_add7(X(0), X(1), X(2), X(3), X(4), X(5), X(6));
        *ovp(plan, s, 1) = CALC_S7(1, 2, 3, 4, 5, 6);
        *ovp(plan, s, 2) = CALC_S7(2, 4, 6, 1, 3, 5);
        *ovp(plan, s, 3) = CALC_S7(3, 6, 2, 5, 1, 4);
        *ovp(plan, s, 4) = CALC_S7(4, 1, 5, 2, 6, 3);
        *ovp(plan, s, 5) = CALC_S7(5, 3, 1, 6, 4, 2);
        *ovp(plan, s, 6) = CALC_S7(6, 5, 4, 3, 2, 1);

    FFT_IMPLEMENTATION_END(plan);
}


const static fft_complex_t TWIDDLE_ARRAY_R11[2][11] = {
        {
                {.r =  1.0000000000000000, .i =  0.0000000000000000 },
                {.r =  0.8412535328311812, .i = -0.5406408174555976 },
                {.r =  0.4154150130018864, .i = -0.9096319953545183 },
                {.r = -0.1423148382732852, .i = -0.9898214418809327 },
                {.r = -0.6548607339452850, .i = -0.7557495743542584 },
                {.r = -0.9594929736144974, .i = -0.2817325568414296 },
                {.r = -0.9594929736144974, .i =  0.2817325568414298 },
                {.r = -0.6548607339452852, .i =  0.7557495743542582 },
                {.r = -0.1423148382732853, .i =  0.9898214418809327 },
                {.r =  0.4154150130018860, .i =  0.9096319953545186 },
                {.r =  0.8412535328311812, .i =  0.5406408174555974 },
        }, {
                {.r =  1.0000000000000000, .i =  0.0000000000000000 },
                {.r =  0.8412535328311812, .i =  0.5406408174555976 },
                {.r =  0.4154150130018864, .i =  0.9096319953545183 },
                {.r = -0.1423148382732852, .i =  0.9898214418809327 },
                {.r = -0.6548607339452850, .i =  0.7557495743542584 },
                {.r = -0.9594929736144974, .i =  0.2817325568414296 },
                {.r = -0.9594929736144974, .i = -0.2817325568414298 },
                {.r = -0.6548607339452852, .i = -0.7557495743542582 },
                {.r = -0.1423148382732853, .i = -0.9898214418809327 },
                {.r =  0.4154150130018860, .i = -0.9096319953545186 },
                {.r =  0.8412535328311812, .i = -0.5406408174555974 },
        }
};


FORCE_INLINE fft_complex_t c_add11(
        const fft_complex_t x0, const fft_complex_t x1, const fft_complex_t x2, const fft_complex_t x3,
        const fft_complex_t x4, const fft_complex_t x5, const fft_complex_t x6, const fft_complex_t x7,
        const fft_complex_t x8, const fft_complex_t x9, const fft_complex_t x10) {
    fft_complex_t result = {
            .r = x0.r + x1.r + x2.r + x3.r + x4.r + x5.r + x6.r + x7.r + x8.r + x9.r + x10.r,
            .i = x0.i + x1.i + x2.i + x3.i + x4.i + x5.i + x6.i + x7.i + x8.i + x9.i + x10.i
    };
    return result;
}


#define CALC_S11(k1, k2, k3, k4, k5, k6, k7, k8, k9, k10) \
    c_add11(X(0), \
        c_mul(w[k1], X(1)), c_mul(w[k2], X(2)), c_mul(w[k3], X(3)), c_mul(w[k4], X(4)),  c_mul(w[k5],  X(5)), \
        c_mul(w[k6], X(6)), c_mul(w[k7], X(7)), c_mul(w[k8], X(8)), c_mul(w[k9], X(9)), c_mul(w[k10], X(10)));


void fft_litho_c11(struct fft_plan_t *plan) {
    FFT_IMPLEMENTATION_BEGIN(plan, 11);

        const fft_complex_t *w = TWIDDLE_ARRAY_R11[plan->direction == FFT_LITHO_BACKWARD];

        *ovp(plan, s,  0) = c_add11(X(0), X(1), X(2), X(3), X(4), X(5), X(6), X(7), X(8), X(9), X(10));
        *ovp(plan, s,  1) = CALC_S11( 1,  2,  3,  4,  5,  6,  7,  8,  9, 10);
        *ovp(plan, s,  2) = CALC_S11( 2,  4,  6,  8, 10,  1,  3,  5,  7,  9);
        *ovp(plan, s,  3) = CALC_S11( 3,  6,  9,  1,  4,  7, 10,  2,  5,  8);
        *ovp(plan, s,  4) = CALC_S11( 4,  8,  1,  5,  9,  2,  6, 10,  3,  7);
        *ovp(plan, s,  5) = CALC_S11( 5, 10,  4,  9,  3,  8,  2,  7,  1,  6);
        *ovp(plan, s,  6) = CALC_S11( 6,  1,  7,  2,  8,  3,  9,  4, 10,  5);
        *ovp(plan, s,  7) = CALC_S11( 7,  3, 10,  6,  2,  9,  5,  1,  8,  4);
        *ovp(plan, s,  8) = CALC_S11( 8,  5,  2, 10,  7,  4,  1,  9,  6,  3);
        *ovp(plan, s,  9) = CALC_S11( 9,  7,  5,  3,  1, 10,  8,  6,  4,  2);
        *ovp(plan, s, 10) = CALC_S11(10,  9,  8,  7,  6,  5,  4,  3,  2,  1);

    FFT_IMPLEMENTATION_END(plan);
}


const static fft_complex_t TWIDDLE_ARRAY_R13[2][13] = {
        {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.8854560256532099, .i = -0.4647231720437686},
                { .r =  0.5680647467311558, .i = -0.8229838658936564},
                { .r =  0.1205366802553230, .i = -0.9927088740980540},
                { .r = -0.3546048870425357, .i = -0.9350162426854148},
                { .r = -0.7485107481711012, .i = -0.6631226582407952},
                { .r = -0.9709418174260520, .i = -0.2393156642875577},
                { .r = -0.9709418174260520, .i =  0.2393156642875579},
                { .r = -0.7485107481711011, .i =  0.6631226582407953},
                { .r = -0.3546048870425359, .i =  0.9350162426854147},
                { .r =  0.1205366802553232, .i =  0.9927088740980540},
                { .r =  0.5680647467311556, .i =  0.8229838658936566},
                { .r =  0.8854560256532100, .i =  0.4647231720437683},
        }, {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.8854560256532099, .i =  0.4647231720437686},
                { .r =  0.5680647467311558, .i =  0.8229838658936564},
                { .r =  0.1205366802553230, .i =  0.9927088740980540},
                { .r = -0.3546048870425357, .i =  0.9350162426854148},
                { .r = -0.7485107481711012, .i =  0.6631226582407952},
                { .r = -0.9709418174260520, .i =  0.2393156642875577},
                { .r = -0.9709418174260520, .i = -0.2393156642875579},
                { .r = -0.7485107481711011, .i = -0.6631226582407953},
                { .r = -0.3546048870425359, .i = -0.9350162426854147},
                { .r =  0.1205366802553232, .i = -0.9927088740980540},
                { .r =  0.5680647467311556, .i = -0.8229838658936566},
                { .r =  0.8854560256532100, .i = -0.4647231720437683},
        }
};


FORCE_INLINE fft_complex_t c_add13(
        const fft_complex_t x0, const fft_complex_t x1, const fft_complex_t x2, const fft_complex_t x3,
        const fft_complex_t x4, const fft_complex_t x5, const fft_complex_t x6, const fft_complex_t x7,
        const fft_complex_t x8, const fft_complex_t x9, const fft_complex_t x10, const fft_complex_t x11,
        const fft_complex_t x12) {
    fft_complex_t result = {
            .r = x0.r + x1.r + x2.r + x3.r + x4.r + x5.r + x6.r + x7.r + x8.r + x9.r + x10.r + x11.r + x12.r,
            .i = x0.i + x1.i + x2.i + x3.i + x4.i + x5.i + x6.i + x7.i + x8.i + x9.i + x10.i + x11.i + x12.i
    };
    return result;
}


#define CALC_S13(k1, k2, k3, k4, k5, k6, k7, k8, k9, k10, k11, k12) \
    c_add13(X(0), \
        c_mul(w[k1], X(1)), c_mul(w[k2], X(2)), c_mul(w[k3], X(3)), c_mul(w[k4], X(4)),  c_mul(w[k5],  X(5)), \
        c_mul(w[k6], X(6)), c_mul(w[k7], X(7)), c_mul(w[k8], X(8)), c_mul(w[k9], X(9)), c_mul(w[k10], X(10)), \
        c_mul(w[k11], X(11)), c_mul(w[k12], X(12)))


void fft_litho_c13(struct fft_plan_t *plan) {
    FFT_IMPLEMENTATION_BEGIN(plan, 13);

        const fft_complex_t *w = TWIDDLE_ARRAY_R13[plan->direction == FFT_LITHO_BACKWARD];

        *ovp(plan, s,  0) = c_add13(X(0), X(1), X(2), X(3), X(4), X(5), X(6), X(7), X(8), X(9), X(10), X(11), X(12));
        *ovp(plan, s,  1) = CALC_S13( 1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12);
        *ovp(plan, s,  2) = CALC_S13( 2,  4,  6,  8, 10, 12,  1,  3,  5,  7,  9, 11);
        *ovp(plan, s,  3) = CALC_S13( 3,  6,  9, 12,  2,  5,  8, 11,  1,  4,  7, 10);
        *ovp(plan, s,  4) = CALC_S13( 4,  8, 12,  3,  7, 11,  2,  6, 10,  1,  5,  9);
        *ovp(plan, s,  5) = CALC_S13( 5, 10,  2,  7, 12,  4,  9,  1,  6, 11,  3,  8);
        *ovp(plan, s,  6) = CALC_S13( 6, 12,  5, 11,  4, 10,  3,  9,  2,  8,  1,  7);
        *ovp(plan, s,  7) = CALC_S13( 7,  1,  8,  2,  9,  3, 10,  4, 11,  5, 12,  6);
        *ovp(plan, s,  8) = CALC_S13( 8,  3, 11,  6,  1,  9,  4, 12,  7,  2, 10,  5);
        *ovp(plan, s,  9) = CALC_S13( 9,  5,  1, 10,  6,  2, 11,  7,  3, 12,  8,  4);
        *ovp(plan, s, 10) = CALC_S13(10,  7,  4,  1, 11,  8,  5,  2, 12,  9,  6,  3);
        *ovp(plan, s, 11) = CALC_S13(11,  9,  7,  5,  3,  1, 12, 10,  8,  6,  4,  2);
        *ovp(plan, s, 12) = CALC_S13(12, 11, 10,  9,  8,  7,  6,  5,  4,  3,  2,  1);

    FFT_IMPLEMENTATION_END(plan);
}


const static fft_complex_t TWIDDLE_ARRAY_R17[2][17] = {
        {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.9324722294043558, .i = -0.3612416661871529},
                { .r =  0.7390089172206591, .i = -0.6736956436465572},
                { .r =  0.4457383557765383, .i = -0.8951632913550623},
                { .r =  0.0922683594633020, .i = -0.9957341762950345},
                { .r = -0.2736629900720827, .i = -0.9618256431728192},
                { .r = -0.6026346363792563, .i = -0.7980172272802396},
                { .r = -0.8502171357296140, .i = -0.5264321628773561},
                { .r = -0.9829730996839018, .i = -0.1837495178165704},
                { .r = -0.9829730996839018, .i =  0.1837495178165701},
                { .r = -0.8502171357296143, .i =  0.5264321628773555},
                { .r = -0.6026346363792572, .i =  0.7980172272802388},
                { .r = -0.2736629900720831, .i =  0.9618256431728190},
                { .r =  0.0922683594633024, .i =  0.9957341762950345},
                { .r =  0.4457383557765378, .i =  0.8951632913550626},
                { .r =  0.7390089172206586, .i =  0.6736956436465578},
                { .r =  0.9324722294043558, .i =  0.3612416661871530},
        }, {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.9324722294043558, .i =  0.3612416661871529},
                { .r =  0.7390089172206591, .i =  0.6736956436465572},
                { .r =  0.4457383557765383, .i =  0.8951632913550623},
                { .r =  0.0922683594633020, .i =  0.9957341762950345},
                { .r = -0.2736629900720827, .i =  0.9618256431728192},
                { .r = -0.6026346363792563, .i =  0.7980172272802396},
                { .r = -0.8502171357296140, .i =  0.5264321628773561},
                { .r = -0.9829730996839018, .i =  0.1837495178165704},
                { .r = -0.9829730996839018, .i = -0.1837495178165701},
                { .r = -0.8502171357296143, .i = -0.5264321628773555},
                { .r = -0.6026346363792572, .i = -0.7980172272802388},
                { .r = -0.2736629900720831, .i = -0.9618256431728190},
                { .r =  0.0922683594633024, .i = -0.9957341762950345},
                { .r =  0.4457383557765378, .i = -0.8951632913550626},
                { .r =  0.7390089172206586, .i = -0.6736956436465578},
                { .r =  0.9324722294043558, .i = -0.3612416661871530},
        }
};


FORCE_INLINE fft_complex_t c_add17(
        const fft_complex_t x0, const fft_complex_t x1, const fft_complex_t x2, const fft_complex_t x3,
        const fft_complex_t x4, const fft_complex_t x5, const fft_complex_t x6, const fft_complex_t x7,
        const fft_complex_t x8, const fft_complex_t x9, const fft_complex_t x10, const fft_complex_t x11,
        const fft_complex_t x12, const fft_complex_t x13, const fft_complex_t x14, const fft_complex_t x15,
        const fft_complex_t x16) {
    fft_complex_t result = {
            .r = x0.r + x1.r + x2.r + x3.r + x4.r + x5.r + x6.r + x7.r + x8.r +
                    x9.r + x10.r + x11.r + x12.r + x13.r + x14.r + x15.r + x16.r,
            .i = x0.i + x1.i + x2.i + x3.i + x4.i + x5.i + x6.i + x7.i + x8.i +
                    x9.i + x10.i + x11.i + x12.i + x13.i + x14.i + x15.i + x16.i
    };
    return result;
}


#define CALC_S17(k1, k2, k3, k4, k5, k6, k7, k8, k9, k10, k11, k12, k13, k14, k15, k16) \
    c_add17(X(0), \
        c_mul(w[k1], X(1)), c_mul(w[k2], X(2)), c_mul(w[k3], X(3)), c_mul(w[k4], X(4)),  c_mul(w[k5],  X(5)), \
        c_mul(w[k6], X(6)), c_mul(w[k7], X(7)), c_mul(w[k8], X(8)), c_mul(w[k9], X(9)), c_mul(w[k10], X(10)), \
        c_mul(w[k11], X(11)), c_mul(w[k12], X(12)), c_mul(w[k13], X(13)), c_mul(w[k14], X(14)), \
        c_mul(w[k15], X(15)), c_mul(w[k16], X(16)))


void fft_litho_c17(struct fft_plan_t *plan) {
    FFT_IMPLEMENTATION_BEGIN(plan, 17);

        const fft_complex_t *w = TWIDDLE_ARRAY_R17[plan->direction == FFT_LITHO_BACKWARD];

        *ovp(plan, s,  0) = c_add17(
                X(0), X(1), X(2), X(3), X(4), X(5), X(6), X(7), X(8),
                X(9), X(10), X(11), X(12), X(13), X(14), X(15), X(16));
        *ovp(plan, s,  1) = CALC_S17( 1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16);
        *ovp(plan, s,  2) = CALC_S17( 2,  4,  6,  8, 10, 12, 14, 16,  1,  3,  5,  7,  9, 11, 13, 15);
        *ovp(plan, s,  3) = CALC_S17( 3,  6,  9, 12, 15,  1,  4,  7, 10, 13, 16,  2,  5,  8, 11, 14);
        *ovp(plan, s,  4) = CALC_S17( 4,  8, 12, 16,  3,  7, 11, 15,  2,  6, 10, 14,  1,  5,  9, 13);
        *ovp(plan, s,  5) = CALC_S17( 5, 10, 15,  3,  8, 13,  1,  6, 11, 16,  4,  9, 14,  2,  7, 12);
        *ovp(plan, s,  6) = CALC_S17( 6, 12,  1,  7, 13,  2,  8, 14,  3,  9, 15,  4, 10, 16,  5, 11);
        *ovp(plan, s,  7) = CALC_S17( 7, 14,  4, 11,  1,  8, 15,  5, 12,  2,  9, 16,  6, 13,  3, 10);
        *ovp(plan, s,  8) = CALC_S17( 8, 16,  7, 15,  6, 14,  5, 13,  4, 12,  3, 11,  2, 10,  1,  9);
        *ovp(plan, s,  9) = CALC_S17( 9,  1, 10,  2, 11,  3, 12,  4, 13,  5, 14,  6, 15,  7, 16,  8);
        *ovp(plan, s, 10) = CALC_S17(10,  3, 13,  6, 16,  9,  2, 12,  5, 15,  8,  1, 11,  4, 14,  7);
        *ovp(plan, s, 11) = CALC_S17(11,  5, 16, 10,  4, 15,  9,  3, 14,  8,  2, 13,  7,  1, 12,  6);
        *ovp(plan, s, 12) = CALC_S17(12,  7,  2, 14,  9,  4, 16, 11,  6,  1, 13,  8,  3, 15, 10,  5);
        *ovp(plan, s, 13) = CALC_S17(13,  9,  5,  1, 14, 10,  6,  2, 15, 11,  7,  3, 16, 12,  8,  4);
        *ovp(plan, s, 14) = CALC_S17(14, 11,  8,  5,  2, 16, 13, 10,  7,  4,  1, 15, 12,  9,  6,  3);
        *ovp(plan, s, 15) = CALC_S17(15, 13, 11,  9,  7,  5,  3,  1, 16, 14, 12, 10,  8,  6,  4,  2);
        *ovp(plan, s, 16) = CALC_S17(16, 15, 14, 13, 12, 11, 10,  9,  8,  7,  6,  5,  4,  3,  2,  1);

    FFT_IMPLEMENTATION_END(plan);
}

const static fft_complex_t TWIDDLE_ARRAY_R19[2][19] = {
        {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.9458172417006346, .i = -0.3246994692046835},
                { .r =  0.7891405093963937, .i = -0.6142127126896678},
                { .r =  0.5469481581224270, .i = -0.8371664782625285},
                { .r =  0.2454854871407992, .i = -0.9694002659393304},
                { .r = -0.0825793454723323, .i = -0.9965844930066698},
                { .r = -0.4016954246529693, .i = -0.9157733266550575},
                { .r = -0.6772815716257409, .i = -0.7357239106731317},
                { .r = -0.8794737512064890, .i = -0.4759473930370737},
                { .r = -0.9863613034027223, .i = -0.1645945902807340},
                { .r = -0.9863613034027224, .i =  0.1645945902807338},
                { .r = -0.8794737512064893, .i =  0.4759473930370731},
                { .r = -0.6772815716257414, .i =  0.7357239106731313},
                { .r = -0.4016954246529699, .i =  0.9157733266550573},
                { .r = -0.0825793454723327, .i =  0.9965844930066698},
                { .r =  0.2454854871407979, .i =  0.9694002659393307},
                { .r =  0.5469481581224266, .i =  0.8371664782625288},
                { .r =  0.7891405093963935, .i =  0.6142127126896680},
                { .r =  0.9458172417006346, .i =  0.3246994692046837},
        }, {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.9458172417006346, .i =  0.3246994692046835},
                { .r =  0.7891405093963937, .i =  0.6142127126896678},
                { .r =  0.5469481581224270, .i =  0.8371664782625285},
                { .r =  0.2454854871407992, .i =  0.9694002659393304},
                { .r = -0.0825793454723323, .i =  0.9965844930066698},
                { .r = -0.4016954246529693, .i =  0.9157733266550575},
                { .r = -0.6772815716257409, .i =  0.7357239106731317},
                { .r = -0.8794737512064890, .i =  0.4759473930370737},
                { .r = -0.9863613034027223, .i =  0.1645945902807340},
                { .r = -0.9863613034027224, .i = -0.1645945902807338},
                { .r = -0.8794737512064893, .i = -0.4759473930370731},
                { .r = -0.6772815716257414, .i = -0.7357239106731313},
                { .r = -0.4016954246529699, .i = -0.9157733266550573},
                { .r = -0.0825793454723327, .i = -0.9965844930066698},
                { .r =  0.2454854871407979, .i = -0.9694002659393307},
                { .r =  0.5469481581224266, .i = -0.8371664782625288},
                { .r =  0.7891405093963935, .i = -0.6142127126896680},
                { .r =  0.9458172417006346, .i = -0.3246994692046837},
        }
};

FORCE_INLINE fft_complex_t c_add19(const fft_complex_t x0, const fft_complex_t x1, const fft_complex_t x2, const fft_complex_t x3, const fft_complex_t x4, const fft_complex_t x5, const fft_complex_t x6, const fft_complex_t x7, const fft_complex_t x8, const fft_complex_t x9, const fft_complex_t x10, const fft_complex_t x11, const fft_complex_t x12, const fft_complex_t x13, const fft_complex_t x14, const fft_complex_t x15, const fft_complex_t x16, const fft_complex_t x17, const fft_complex_t x18) {
    fft_complex_t result = {
            .r = x0.r + x1.r + x2.r + x3.r + x4.r + x5.r + x6.r + x7.r + x8.r + x9.r + x10.r + x11.r + x12.r + x13.r + x14.r + x15.r + x16.r + x17.r + x18.r,
            .i = x0.i + x1.i + x2.i + x3.i + x4.i + x5.i + x6.i + x7.i + x8.i + x9.i + x10.i + x11.i + x12.i + x13.i + x14.i + x15.i + x16.i + x17.i + x18.i
    };
    return result;
}

#define CALC_S19(k1, k2, k3, k4, k5, k6, k7, k8, k9, k10, k11, k12, k13, k14, k15, k16, k17, k18) \
    c_add19(X(0), c_mul(w[k1], X(1)), c_mul(w[k2], X(2)), c_mul(w[k3], X(3)), c_mul(w[k4], X(4)), c_mul(w[k5], X(5)), c_mul(w[k6], X(6)), c_mul(w[k7], X(7)), c_mul(w[k8], X(8)), c_mul(w[k9], X(9)), c_mul(w[k10], X(10)), c_mul(w[k11], X(11)), c_mul(w[k12], X(12)), c_mul(w[k13], X(13)), c_mul(w[k14], X(14)), c_mul(w[k15], X(15)), c_mul(w[k16], X(16)), c_mul(w[k17], X(17)), c_mul(w[k18], X(18)))

void fft_litho_c19(struct fft_plan_t *plan) {
    FFT_IMPLEMENTATION_BEGIN(plan, 19) ;

        const fft_complex_t *w = TWIDDLE_ARRAY_R19[plan->direction == FFT_LITHO_BACKWARD];

        *ovp(plan, s, 0) = c_add19(X(0), X(1), X(2), X(3), X(4), X(5), X(6), X(7), X(8), X(9), X(10), X(11), X(12), X(13), X(14), X(15), X(16), X(17), X(18));
        *ovp(plan, s, 0) = CALC_S19(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
        *ovp(plan, s, 1) = CALC_S19(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18);
        *ovp(plan, s, 2) = CALC_S19(2, 4, 6, 8, 10, 12, 14, 16, 18, 1, 3, 5, 7, 9, 11, 13, 15, 17);
        *ovp(plan, s, 3) = CALC_S19(3, 6, 9, 12, 15, 18, 2, 5, 8, 11, 14, 17, 1, 4, 7, 10, 13, 16);
        *ovp(plan, s, 4) = CALC_S19(4, 8, 12, 16, 1, 5, 9, 13, 17, 2, 6, 10, 14, 18, 3, 7, 11, 15);
        *ovp(plan, s, 5) = CALC_S19(5, 10, 15, 1, 6, 11, 16, 2, 7, 12, 17, 3, 8, 13, 18, 4, 9, 14);
        *ovp(plan, s, 6) = CALC_S19(6, 12, 18, 5, 11, 17, 4, 10, 16, 3, 9, 15, 2, 8, 14, 1, 7, 13);
        *ovp(plan, s, 7) = CALC_S19(7, 14, 2, 9, 16, 4, 11, 18, 6, 13, 1, 8, 15, 3, 10, 17, 5, 12);
        *ovp(plan, s, 8) = CALC_S19(8, 16, 5, 13, 2, 10, 18, 7, 15, 4, 12, 1, 9, 17, 6, 14, 3, 11);
        *ovp(plan, s, 9) = CALC_S19(9, 18, 8, 17, 7, 16, 6, 15, 5, 14, 4, 13, 3, 12, 2, 11, 1, 10);
        *ovp(plan, s, 10) = CALC_S19(10, 1, 11, 2, 12, 3, 13, 4, 14, 5, 15, 6, 16, 7, 17, 8, 18, 9);
        *ovp(plan, s, 11) = CALC_S19(11, 3, 14, 6, 17, 9, 1, 12, 4, 15, 7, 18, 10, 2, 13, 5, 16, 8);
        *ovp(plan, s, 12) = CALC_S19(12, 5, 17, 10, 3, 15, 8, 1, 13, 6, 18, 11, 4, 16, 9, 2, 14, 7);
        *ovp(plan, s, 13) = CALC_S19(13, 7, 1, 14, 8, 2, 15, 9, 3, 16, 10, 4, 17, 11, 5, 18, 12, 6);
        *ovp(plan, s, 14) = CALC_S19(14, 9, 4, 18, 13, 8, 3, 17, 12, 7, 2, 16, 11, 6, 1, 15, 10, 5);
        *ovp(plan, s, 15) = CALC_S19(15, 11, 7, 3, 18, 14, 10, 6, 2, 17, 13, 9, 5, 1, 16, 12, 8, 4);
        *ovp(plan, s, 16) = CALC_S19(16, 13, 10, 7, 4, 1, 17, 14, 11, 8, 5, 2, 18, 15, 12, 9, 6, 3);
        *ovp(plan, s, 17) = CALC_S19(17, 15, 13, 11, 9, 7, 5, 3, 1, 18, 16, 14, 12, 10, 8, 6, 4, 2);
        *ovp(plan, s, 18) = CALC_S19(18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1);

    FFT_IMPLEMENTATION_END(plan);
}


const static fft_complex_t TWIDDLE_ARRAY_R47[2][47] = {
        {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.9910774881547801, .i = -0.1332869553737788},
                { .r =  0.9644691750543766, .i = -0.2641954018712860},
                { .r =  0.9206498866764288, .i = -0.3903892751634948},
                { .r =  0.8604015792601394, .i = -0.5096166425919174},
                { .r =  0.7847993852786610, .i = -0.6197498889602449},
                { .r =  0.6951924276746423, .i = -0.7188236838779293},
                { .r =  0.5931797447293553, .i = -0.8050700531275629},
                { .r =  0.4805817551866838, .i = -0.8769499282066715},
                { .r =  0.3594077728375128, .i = -0.9331806110416025},
                { .r =  0.2318201502675284, .i = -0.9727586637650372},
                { .r =  0.1000956916240987, .i = -0.9949778150885040},
                { .r = -0.0334149770076745, .i = -0.9994415637302546},
                { .r = -0.1663293545831300, .i = -0.9860702539900286},
                { .r = -0.2962755808856338, .i = -0.9551024972069124},
                { .r = -0.4209347624283349, .i = -0.9070909137343408},
                { .r = -0.5380823531633726, .i = -0.8428922714167971},
                { .r = -0.6456278515588023, .i = -0.7636521965473321},
                { .r = -0.7416521056479576, .i = -0.6707847301392235},
                { .r = -0.8244415603417601, .i = -0.5659470943305954},
                { .r = -0.8925188358598811, .i = -0.4510101192161021},
                { .r = -0.9446690916079189, .i = -0.3280248578395689},
                { .r = -0.9799617050365866, .i = -0.1991859851038367},
                { .r = -0.9977668786231532, .i = -0.0667926337451217},
                { .r = -0.9977668786231532, .i =  0.0667926337451215},
                { .r = -0.9799617050365869, .i =  0.1991859851038361},
                { .r = -0.9446690916079188, .i =  0.3280248578395691},
                { .r = -0.8925188358598815, .i =  0.4510101192161015},
                { .r = -0.8244415603417605, .i =  0.5659470943305949},
                { .r = -0.7416521056479577, .i =  0.6707847301392232},
                { .r = -0.6456278515588026, .i =  0.7636521965473319},
                { .r = -0.5380823531633728, .i =  0.8428922714167969},
                { .r = -0.4209347624283351, .i =  0.9070909137343407},
                { .r = -0.2962755808856340, .i =  0.9551024972069124},
                { .r = -0.1663293545831301, .i =  0.9860702539900286},
                { .r = -0.0334149770076754, .i =  0.9994415637302546},
                { .r =  0.1000956916240984, .i =  0.9949778150885040},
                { .r =  0.2318201502675284, .i =  0.9727586637650372},
                { .r =  0.3594077728375122, .i =  0.9331806110416028},
                { .r =  0.4805817551866832, .i =  0.8769499282066718},
                { .r =  0.5931797447293546, .i =  0.8050700531275633},
                { .r =  0.6951924276746418, .i =  0.7188236838779297},
                { .r =  0.7847993852786612, .i =  0.6197498889602445},
                { .r =  0.8604015792601392, .i =  0.5096166425919177},
                { .r =  0.9206498866764283, .i =  0.3903892751634960},
                { .r =  0.9644691750543765, .i =  0.2641954018712863},
                { .r =  0.9910774881547800, .i =  0.1332869553737791},
        }, {
                { .r =  1.0000000000000000, .i =  0.0000000000000000},
                { .r =  0.9910774881547801, .i =  0.1332869553737788},
                { .r =  0.9644691750543766, .i =  0.2641954018712860},
                { .r =  0.9206498866764288, .i =  0.3903892751634948},
                { .r =  0.8604015792601394, .i =  0.5096166425919174},
                { .r =  0.7847993852786610, .i =  0.6197498889602449},
                { .r =  0.6951924276746423, .i =  0.7188236838779293},
                { .r =  0.5931797447293553, .i =  0.8050700531275629},
                { .r =  0.4805817551866838, .i =  0.8769499282066715},
                { .r =  0.3594077728375128, .i =  0.9331806110416025},
                { .r =  0.2318201502675284, .i =  0.9727586637650372},
                { .r =  0.1000956916240987, .i =  0.9949778150885040},
                { .r = -0.0334149770076745, .i =  0.9994415637302546},
                { .r = -0.1663293545831300, .i =  0.9860702539900286},
                { .r = -0.2962755808856338, .i =  0.9551024972069124},
                { .r = -0.4209347624283349, .i =  0.9070909137343408},
                { .r = -0.5380823531633726, .i =  0.8428922714167971},
                { .r = -0.6456278515588023, .i =  0.7636521965473321},
                { .r = -0.7416521056479576, .i =  0.6707847301392235},
                { .r = -0.8244415603417601, .i =  0.5659470943305954},
                { .r = -0.8925188358598811, .i =  0.4510101192161021},
                { .r = -0.9446690916079189, .i =  0.3280248578395689},
                { .r = -0.9799617050365866, .i =  0.1991859851038367},
                { .r = -0.9977668786231532, .i =  0.0667926337451217},
                { .r = -0.9977668786231532, .i = -0.0667926337451215},
                { .r = -0.9799617050365869, .i = -0.1991859851038361},
                { .r = -0.9446690916079188, .i = -0.3280248578395691},
                { .r = -0.8925188358598815, .i = -0.4510101192161015},
                { .r = -0.8244415603417605, .i = -0.5659470943305949},
                { .r = -0.7416521056479577, .i = -0.6707847301392232},
                { .r = -0.6456278515588026, .i = -0.7636521965473319},
                { .r = -0.5380823531633728, .i = -0.8428922714167969},
                { .r = -0.4209347624283351, .i = -0.9070909137343407},
                { .r = -0.2962755808856340, .i = -0.9551024972069124},
                { .r = -0.1663293545831301, .i = -0.9860702539900286},
                { .r = -0.0334149770076754, .i = -0.9994415637302546},
                { .r =  0.1000956916240984, .i = -0.9949778150885040},
                { .r =  0.2318201502675284, .i = -0.9727586637650372},
                { .r =  0.3594077728375122, .i = -0.9331806110416028},
                { .r =  0.4805817551866832, .i = -0.8769499282066718},
                { .r =  0.5931797447293546, .i = -0.8050700531275633},
                { .r =  0.6951924276746418, .i = -0.7188236838779297},
                { .r =  0.7847993852786612, .i = -0.6197498889602445},
                { .r =  0.8604015792601392, .i = -0.5096166425919177},
                { .r =  0.9206498866764283, .i = -0.3903892751634960},
                { .r =  0.9644691750543765, .i = -0.2641954018712863},
                { .r =  0.9910774881547800, .i = -0.1332869553737791},
        }
};

FORCE_INLINE fft_complex_t c_add47(const fft_complex_t x0, const fft_complex_t x1, const fft_complex_t x2, const fft_complex_t x3, const fft_complex_t x4, const fft_complex_t x5, const fft_complex_t x6, const fft_complex_t x7, const fft_complex_t x8, const fft_complex_t x9, const fft_complex_t x10, const fft_complex_t x11, const fft_complex_t x12, const fft_complex_t x13, const fft_complex_t x14, const fft_complex_t x15, const fft_complex_t x16, const fft_complex_t x17, const fft_complex_t x18, const fft_complex_t x19, const fft_complex_t x20, const fft_complex_t x21, const fft_complex_t x22, const fft_complex_t x23, const fft_complex_t x24, const fft_complex_t x25, const fft_complex_t x26, const fft_complex_t x27, const fft_complex_t x28, const fft_complex_t x29, const fft_complex_t x30, const fft_complex_t x31, const fft_complex_t x32, const fft_complex_t x33, const fft_complex_t x34, const fft_complex_t x35, const fft_complex_t x36, const fft_complex_t x37, const fft_complex_t x38, const fft_complex_t x39, const fft_complex_t x40, const fft_complex_t x41, const fft_complex_t x42, const fft_complex_t x43, const fft_complex_t x44, const fft_complex_t x45, const fft_complex_t x46) {
    fft_complex_t result = {
            .r = x0.r + x1.r + x2.r + x3.r + x4.r + x5.r + x6.r + x7.r + x8.r + x9.r + x10.r + x11.r + x12.r + x13.r + x14.r + x15.r + x16.r + x17.r + x18.r + x19.r + x20.r + x21.r + x22.r + x23.r + x24.r + x25.r + x26.r + x27.r + x28.r + x29.r + x30.r + x31.r + x32.r + x33.r + x34.r + x35.r + x36.r + x37.r + x38.r + x39.r + x40.r + x41.r + x42.r + x43.r + x44.r + x45.r + x46.r,
            .i = x0.i + x1.i + x2.i + x3.i + x4.i + x5.i + x6.i + x7.i + x8.i + x9.i + x10.i + x11.i + x12.i + x13.i + x14.i + x15.i + x16.i + x17.i + x18.i + x19.i + x20.i + x21.i + x22.i + x23.i + x24.i + x25.i + x26.i + x27.i + x28.i + x29.i + x30.i + x31.i + x32.i + x33.i + x34.i + x35.i + x36.i + x37.i + x38.i + x39.i + x40.i + x41.i + x42.i + x43.i + x44.i + x45.i + x46.i
    };
    return result;
}

#define CALC_S47(k1, k2, k3, k4, k5, k6, k7, k8, k9, k10, k11, k12, k13, k14, k15, k16, k17, k18, k19, k20, k21, k22, k23, k24, k25, k26, k27, k28, k29, k30, k31, k32, k33, k34, k35, k36, k37, k38, k39, k40, k41, k42, k43, k44, k45, k46) \
    c_add47(X(0), c_mul(w[k1], X(1)), c_mul(w[k2], X(2)), c_mul(w[k3], X(3)), c_mul(w[k4], X(4)), c_mul(w[k5], X(5)), c_mul(w[k6], X(6)), c_mul(w[k7], X(7)), c_mul(w[k8], X(8)), c_mul(w[k9], X(9)), c_mul(w[k10], X(10)), c_mul(w[k11], X(11)), c_mul(w[k12], X(12)), c_mul(w[k13], X(13)), c_mul(w[k14], X(14)), c_mul(w[k15], X(15)), c_mul(w[k16], X(16)), c_mul(w[k17], X(17)), c_mul(w[k18], X(18)), c_mul(w[k19], X(19)), c_mul(w[k20], X(20)), c_mul(w[k21], X(21)), c_mul(w[k22], X(22)), c_mul(w[k23], X(23)), c_mul(w[k24], X(24)), c_mul(w[k25], X(25)), c_mul(w[k26], X(26)), c_mul(w[k27], X(27)), c_mul(w[k28], X(28)), c_mul(w[k29], X(29)), c_mul(w[k30], X(30)), c_mul(w[k31], X(31)), c_mul(w[k32], X(32)), c_mul(w[k33], X(33)), c_mul(w[k34], X(34)), c_mul(w[k35], X(35)), c_mul(w[k36], X(36)), c_mul(w[k37], X(37)), c_mul(w[k38], X(38)), c_mul(w[k39], X(39)), c_mul(w[k40], X(40)), c_mul(w[k41], X(41)), c_mul(w[k42], X(42)), c_mul(w[k43], X(43)), c_mul(w[k44], X(44)), c_mul(w[k45], X(45)), c_mul(w[k46], X(46)))

void fft_litho_c47(struct fft_plan_t *plan) {
    FFT_IMPLEMENTATION_BEGIN(plan, 47);

        const fft_complex_t *w = TWIDDLE_ARRAY_R47[plan->direction == FFT_LITHO_BACKWARD];

        *ovp(plan, s,  0) = c_add47(X(0), X(1), X(2), X(3), X(4), X(5), X(6), X(7), X(8), X(9), X(10), X(11), X(12), X(13), X(14), X(15), X(16), X(17), X(18), X(19), X(20), X(21), X(22), X(23), X(24), X(25), X(26), X(27), X(28), X(29), X(30), X(31), X(32), X(33), X(34), X(35), X(36), X(37), X(38), X(39), X(40), X(41), X(42), X(43), X(44), X(45), X(46));
        *ovp(plan, s,  0) = CALC_S47( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0);
        *ovp(plan, s,  1) = CALC_S47( 1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46);
        *ovp(plan, s,  2) = CALC_S47( 2,  4,  6,  8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46,  1,  3,  5,  7,  9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 43, 45);
        *ovp(plan, s,  3) = CALC_S47( 3,  6,  9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45,  1,  4,  7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37, 40, 43, 46,  2,  5,  8, 11, 14, 17, 20, 23, 26, 29, 32, 35, 38, 41, 44);
        *ovp(plan, s,  4) = CALC_S47( 4,  8, 12, 16, 20, 24, 28, 32, 36, 40, 44,  1,  5,  9, 13, 17, 21, 25, 29, 33, 37, 41, 45,  2,  6, 10, 14, 18, 22, 26, 30, 34, 38, 42, 46,  3,  7, 11, 15, 19, 23, 27, 31, 35, 39, 43);
        *ovp(plan, s,  5) = CALC_S47( 5, 10, 15, 20, 25, 30, 35, 40, 45,  3,  8, 13, 18, 23, 28, 33, 38, 43,  1,  6, 11, 16, 21, 26, 31, 36, 41, 46,  4,  9, 14, 19, 24, 29, 34, 39, 44,  2,  7, 12, 17, 22, 27, 32, 37, 42);
        *ovp(plan, s,  6) = CALC_S47( 6, 12, 18, 24, 30, 36, 42,  1,  7, 13, 19, 25, 31, 37, 43,  2,  8, 14, 20, 26, 32, 38, 44,  3,  9, 15, 21, 27, 33, 39, 45,  4, 10, 16, 22, 28, 34, 40, 46,  5, 11, 17, 23, 29, 35, 41);
        *ovp(plan, s,  7) = CALC_S47( 7, 14, 21, 28, 35, 42,  2,  9, 16, 23, 30, 37, 44,  4, 11, 18, 25, 32, 39, 46,  6, 13, 20, 27, 34, 41,  1,  8, 15, 22, 29, 36, 43,  3, 10, 17, 24, 31, 38, 45,  5, 12, 19, 26, 33, 40);
        *ovp(plan, s,  8) = CALC_S47( 8, 16, 24, 32, 40,  1,  9, 17, 25, 33, 41,  2, 10, 18, 26, 34, 42,  3, 11, 19, 27, 35, 43,  4, 12, 20, 28, 36, 44,  5, 13, 21, 29, 37, 45,  6, 14, 22, 30, 38, 46,  7, 15, 23, 31, 39);
        *ovp(plan, s,  9) = CALC_S47( 9, 18, 27, 36, 45,  7, 16, 25, 34, 43,  5, 14, 23, 32, 41,  3, 12, 21, 30, 39,  1, 10, 19, 28, 37, 46,  8, 17, 26, 35, 44,  6, 15, 24, 33, 42,  4, 13, 22, 31, 40,  2, 11, 20, 29, 38);
        *ovp(plan, s, 10) = CALC_S47(10, 20, 30, 40,  3, 13, 23, 33, 43,  6, 16, 26, 36, 46,  9, 19, 29, 39,  2, 12, 22, 32, 42,  5, 15, 25, 35, 45,  8, 18, 28, 38,  1, 11, 21, 31, 41,  4, 14, 24, 34, 44,  7, 17, 27, 37);
        *ovp(plan, s, 11) = CALC_S47(11, 22, 33, 44,  8, 19, 30, 41,  5, 16, 27, 38,  2, 13, 24, 35, 46, 10, 21, 32, 43,  7, 18, 29, 40,  4, 15, 26, 37,  1, 12, 23, 34, 45,  9, 20, 31, 42,  6, 17, 28, 39,  3, 14, 25, 36);
        *ovp(plan, s, 12) = CALC_S47(12, 24, 36,  1, 13, 25, 37,  2, 14, 26, 38,  3, 15, 27, 39,  4, 16, 28, 40,  5, 17, 29, 41,  6, 18, 30, 42,  7, 19, 31, 43,  8, 20, 32, 44,  9, 21, 33, 45, 10, 22, 34, 46, 11, 23, 35);
        *ovp(plan, s, 13) = CALC_S47(13, 26, 39,  5, 18, 31, 44, 10, 23, 36,  2, 15, 28, 41,  7, 20, 33, 46, 12, 25, 38,  4, 17, 30, 43,  9, 22, 35,  1, 14, 27, 40,  6, 19, 32, 45, 11, 24, 37,  3, 16, 29, 42,  8, 21, 34);
        *ovp(plan, s, 14) = CALC_S47(14, 28, 42,  9, 23, 37,  4, 18, 32, 46, 13, 27, 41,  8, 22, 36,  3, 17, 31, 45, 12, 26, 40,  7, 21, 35,  2, 16, 30, 44, 11, 25, 39,  6, 20, 34,  1, 15, 29, 43, 10, 24, 38,  5, 19, 33);
        *ovp(plan, s, 15) = CALC_S47(15, 30, 45, 13, 28, 43, 11, 26, 41,  9, 24, 39,  7, 22, 37,  5, 20, 35,  3, 18, 33,  1, 16, 31, 46, 14, 29, 44, 12, 27, 42, 10, 25, 40,  8, 23, 38,  6, 21, 36,  4, 19, 34,  2, 17, 32);
        *ovp(plan, s, 16) = CALC_S47(16, 32,  1, 17, 33,  2, 18, 34,  3, 19, 35,  4, 20, 36,  5, 21, 37,  6, 22, 38,  7, 23, 39,  8, 24, 40,  9, 25, 41, 10, 26, 42, 11, 27, 43, 12, 28, 44, 13, 29, 45, 14, 30, 46, 15, 31);
        *ovp(plan, s, 17) = CALC_S47(17, 34,  4, 21, 38,  8, 25, 42, 12, 29, 46, 16, 33,  3, 20, 37,  7, 24, 41, 11, 28, 45, 15, 32,  2, 19, 36,  6, 23, 40, 10, 27, 44, 14, 31,  1, 18, 35,  5, 22, 39,  9, 26, 43, 13, 30);
        *ovp(plan, s, 18) = CALC_S47(18, 36,  7, 25, 43, 14, 32,  3, 21, 39, 10, 28, 46, 17, 35,  6, 24, 42, 13, 31,  2, 20, 38,  9, 27, 45, 16, 34,  5, 23, 41, 12, 30,  1, 19, 37,  8, 26, 44, 15, 33,  4, 22, 40, 11, 29);
        *ovp(plan, s, 19) = CALC_S47(19, 38, 10, 29,  1, 20, 39, 11, 30,  2, 21, 40, 12, 31,  3, 22, 41, 13, 32,  4, 23, 42, 14, 33,  5, 24, 43, 15, 34,  6, 25, 44, 16, 35,  7, 26, 45, 17, 36,  8, 27, 46, 18, 37,  9, 28);
        *ovp(plan, s, 20) = CALC_S47(20, 40, 13, 33,  6, 26, 46, 19, 39, 12, 32,  5, 25, 45, 18, 38, 11, 31,  4, 24, 44, 17, 37, 10, 30,  3, 23, 43, 16, 36,  9, 29,  2, 22, 42, 15, 35,  8, 28,  1, 21, 41, 14, 34,  7, 27);
        *ovp(plan, s, 21) = CALC_S47(21, 42, 16, 37, 11, 32,  6, 27,  1, 22, 43, 17, 38, 12, 33,  7, 28,  2, 23, 44, 18, 39, 13, 34,  8, 29,  3, 24, 45, 19, 40, 14, 35,  9, 30,  4, 25, 46, 20, 41, 15, 36, 10, 31,  5, 26);
        *ovp(plan, s, 22) = CALC_S47(22, 44, 19, 41, 16, 38, 13, 35, 10, 32,  7, 29,  4, 26,  1, 23, 45, 20, 42, 17, 39, 14, 36, 11, 33,  8, 30,  5, 27,  2, 24, 46, 21, 43, 18, 40, 15, 37, 12, 34,  9, 31,  6, 28,  3, 25);
        *ovp(plan, s, 23) = CALC_S47(23, 46, 22, 45, 21, 44, 20, 43, 19, 42, 18, 41, 17, 40, 16, 39, 15, 38, 14, 37, 13, 36, 12, 35, 11, 34, 10, 33,  9, 32,  8, 31,  7, 30,  6, 29,  5, 28,  4, 27,  3, 26,  2, 25,  1, 24);
        *ovp(plan, s, 24) = CALC_S47(24,  1, 25,  2, 26,  3, 27,  4, 28,  5, 29,  6, 30,  7, 31,  8, 32,  9, 33, 10, 34, 11, 35, 12, 36, 13, 37, 14, 38, 15, 39, 16, 40, 17, 41, 18, 42, 19, 43, 20, 44, 21, 45, 22, 46, 23);
        *ovp(plan, s, 25) = CALC_S47(25,  3, 28,  6, 31,  9, 34, 12, 37, 15, 40, 18, 43, 21, 46, 24,  2, 27,  5, 30,  8, 33, 11, 36, 14, 39, 17, 42, 20, 45, 23,  1, 26,  4, 29,  7, 32, 10, 35, 13, 38, 16, 41, 19, 44, 22);
        *ovp(plan, s, 26) = CALC_S47(26,  5, 31, 10, 36, 15, 41, 20, 46, 25,  4, 30,  9, 35, 14, 40, 19, 45, 24,  3, 29,  8, 34, 13, 39, 18, 44, 23,  2, 28,  7, 33, 12, 38, 17, 43, 22,  1, 27,  6, 32, 11, 37, 16, 42, 21);
        *ovp(plan, s, 27) = CALC_S47(27,  7, 34, 14, 41, 21,  1, 28,  8, 35, 15, 42, 22,  2, 29,  9, 36, 16, 43, 23,  3, 30, 10, 37, 17, 44, 24,  4, 31, 11, 38, 18, 45, 25,  5, 32, 12, 39, 19, 46, 26,  6, 33, 13, 40, 20);
        *ovp(plan, s, 28) = CALC_S47(28,  9, 37, 18, 46, 27,  8, 36, 17, 45, 26,  7, 35, 16, 44, 25,  6, 34, 15, 43, 24,  5, 33, 14, 42, 23,  4, 32, 13, 41, 22,  3, 31, 12, 40, 21,  2, 30, 11, 39, 20,  1, 29, 10, 38, 19);
        *ovp(plan, s, 29) = CALC_S47(29, 11, 40, 22,  4, 33, 15, 44, 26,  8, 37, 19,  1, 30, 12, 41, 23,  5, 34, 16, 45, 27,  9, 38, 20,  2, 31, 13, 42, 24,  6, 35, 17, 46, 28, 10, 39, 21,  3, 32, 14, 43, 25,  7, 36, 18);
        *ovp(plan, s, 30) = CALC_S47(30, 13, 43, 26,  9, 39, 22,  5, 35, 18,  1, 31, 14, 44, 27, 10, 40, 23,  6, 36, 19,  2, 32, 15, 45, 28, 11, 41, 24,  7, 37, 20,  3, 33, 16, 46, 29, 12, 42, 25,  8, 38, 21,  4, 34, 17);
        *ovp(plan, s, 31) = CALC_S47(31, 15, 46, 30, 14, 45, 29, 13, 44, 28, 12, 43, 27, 11, 42, 26, 10, 41, 25,  9, 40, 24,  8, 39, 23,  7, 38, 22,  6, 37, 21,  5, 36, 20,  4, 35, 19,  3, 34, 18,  2, 33, 17,  1, 32, 16);
        *ovp(plan, s, 32) = CALC_S47(32, 17,  2, 34, 19,  4, 36, 21,  6, 38, 23,  8, 40, 25, 10, 42, 27, 12, 44, 29, 14, 46, 31, 16,  1, 33, 18,  3, 35, 20,  5, 37, 22,  7, 39, 24,  9, 41, 26, 11, 43, 28, 13, 45, 30, 15);
        *ovp(plan, s, 33) = CALC_S47(33, 19,  5, 38, 24, 10, 43, 29, 15,  1, 34, 20,  6, 39, 25, 11, 44, 30, 16,  2, 35, 21,  7, 40, 26, 12, 45, 31, 17,  3, 36, 22,  8, 41, 27, 13, 46, 32, 18,  4, 37, 23,  9, 42, 28, 14);
        *ovp(plan, s, 34) = CALC_S47(34, 21,  8, 42, 29, 16,  3, 37, 24, 11, 45, 32, 19,  6, 40, 27, 14,  1, 35, 22,  9, 43, 30, 17,  4, 38, 25, 12, 46, 33, 20,  7, 41, 28, 15,  2, 36, 23, 10, 44, 31, 18,  5, 39, 26, 13);
        *ovp(plan, s, 35) = CALC_S47(35, 23, 11, 46, 34, 22, 10, 45, 33, 21,  9, 44, 32, 20,  8, 43, 31, 19,  7, 42, 30, 18,  6, 41, 29, 17,  5, 40, 28, 16,  4, 39, 27, 15,  3, 38, 26, 14,  2, 37, 25, 13,  1, 36, 24, 12);
        *ovp(plan, s, 36) = CALC_S47(36, 25, 14,  3, 39, 28, 17,  6, 42, 31, 20,  9, 45, 34, 23, 12,  1, 37, 26, 15,  4, 40, 29, 18,  7, 43, 32, 21, 10, 46, 35, 24, 13,  2, 38, 27, 16,  5, 41, 30, 19,  8, 44, 33, 22, 11);
        *ovp(plan, s, 37) = CALC_S47(37, 27, 17,  7, 44, 34, 24, 14,  4, 41, 31, 21, 11,  1, 38, 28, 18,  8, 45, 35, 25, 15,  5, 42, 32, 22, 12,  2, 39, 29, 19,  9, 46, 36, 26, 16,  6, 43, 33, 23, 13,  3, 40, 30, 20, 10);
        *ovp(plan, s, 38) = CALC_S47(38, 29, 20, 11,  2, 40, 31, 22, 13,  4, 42, 33, 24, 15,  6, 44, 35, 26, 17,  8, 46, 37, 28, 19, 10,  1, 39, 30, 21, 12,  3, 41, 32, 23, 14,  5, 43, 34, 25, 16,  7, 45, 36, 27, 18,  9);
        *ovp(plan, s, 39) = CALC_S47(39, 31, 23, 15,  7, 46, 38, 30, 22, 14,  6, 45, 37, 29, 21, 13,  5, 44, 36, 28, 20, 12,  4, 43, 35, 27, 19, 11,  3, 42, 34, 26, 18, 10,  2, 41, 33, 25, 17,  9,  1, 40, 32, 24, 16,  8);
        *ovp(plan, s, 40) = CALC_S47(40, 33, 26, 19, 12,  5, 45, 38, 31, 24, 17, 10,  3, 43, 36, 29, 22, 15,  8,  1, 41, 34, 27, 20, 13,  6, 46, 39, 32, 25, 18, 11,  4, 44, 37, 30, 23, 16,  9,  2, 42, 35, 28, 21, 14,  7);
        *ovp(plan, s, 41) = CALC_S47(41, 35, 29, 23, 17, 11,  5, 46, 40, 34, 28, 22, 16, 10,  4, 45, 39, 33, 27, 21, 15,  9,  3, 44, 38, 32, 26, 20, 14,  8,  2, 43, 37, 31, 25, 19, 13,  7,  1, 42, 36, 30, 24, 18, 12,  6);
        *ovp(plan, s, 42) = CALC_S47(42, 37, 32, 27, 22, 17, 12,  7,  2, 44, 39, 34, 29, 24, 19, 14,  9,  4, 46, 41, 36, 31, 26, 21, 16, 11,  6,  1, 43, 38, 33, 28, 23, 18, 13,  8,  3, 45, 40, 35, 30, 25, 20, 15, 10,  5);
        *ovp(plan, s, 43) = CALC_S47(43, 39, 35, 31, 27, 23, 19, 15, 11,  7,  3, 46, 42, 38, 34, 30, 26, 22, 18, 14, 10,  6,  2, 45, 41, 37, 33, 29, 25, 21, 17, 13,  9,  5,  1, 44, 40, 36, 32, 28, 24, 20, 16, 12,  8,  4);
        *ovp(plan, s, 44) = CALC_S47(44, 41, 38, 35, 32, 29, 26, 23, 20, 17, 14, 11,  8,  5,  2, 46, 43, 40, 37, 34, 31, 28, 25, 22, 19, 16, 13, 10,  7,  4,  1, 45, 42, 39, 36, 33, 30, 27, 24, 21, 18, 15, 12,  9,  6,  3);
        *ovp(plan, s, 45) = CALC_S47(45, 43, 41, 39, 37, 35, 33, 31, 29, 27, 25, 23, 21, 19, 17, 15, 13, 11,  9,  7,  5,  3,  1, 46, 44, 42, 40, 38, 36, 34, 32, 30, 28, 26, 24, 22, 20, 18, 16, 14, 12, 10,  8,  6,  4,  2);
        *ovp(plan, s, 46) = CALC_S47(46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10,  9,  8,  7,  6,  5,  4,  3,  2,  1);

    FFT_IMPLEMENTATION_END(plan);
}


const fft_handler_desc_t fft_handlers[] = {
        {  2, fft_litho_c2},
        {  3, fft_litho_c3},
        {  4, fft_litho_c4},
        {  5, fft_litho_c5},
        {  6, fft_litho_c6},
        {  7, fft_litho_c7},
        { 11, fft_litho_c11},
        { 13, fft_litho_c13},
        { 17, fft_litho_c17},
        { 19, fft_litho_c19},
        { 47, fft_litho_c47},
};


const unsigned int FFT_IMPLEMENTED_RADIX_COUNT = sizeof(fft_handlers)/sizeof(fft_handler_desc_t);