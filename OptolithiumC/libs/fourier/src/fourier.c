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
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 */

#include "basics.h"
#include "primes.h"


unsigned int RECURSION_DEPTH = 0;


void perform_bitrev(unsigned int *indexes, unsigned int count) {
    unsigned int i, forward, rev, zeros;

    // to hold bitwise negated or odd values
    unsigned int nodd, noddrev;
    unsigned int halfn, quartn, nmin1;

    // frequently used 'constants'
//	N = 1 << logN;
    halfn = count >> 1;
    quartn = count >> 2;
    nmin1 = count - 1;

    // variable initializations
    forward = halfn;
    rev = 1;

    // start of bitreversed permutation loop, N/4 iterations
    for (i = quartn; i; i--) {
        // Gray code generator for even values:

        // counting ones is easier
        nodd = ~i;

        // find trailing zero's in i
        for (zeros = 0; nodd & 1; zeros++) {
            nodd >>= 1;
        }

        // toggle one bit of forward
        forward ^= 2 << zeros;
        // toggle one bit of rev
        rev ^= quartn >> zeros;

        // swap even and ~even conditionally
        if (forward < rev) {
            SWAP(unsigned int, indexes[forward], indexes[rev]);
            // compute the bitwise negations
            nodd = nmin1 ^ forward;
            noddrev = nmin1 ^ rev;
            // swap bitwise-negated pairs
            SWAP(unsigned int, indexes[nodd], indexes[noddrev]);
        }

        // compute the odd values from the even
        nodd = forward ^ 1;
        noddrev = rev ^ halfn;
        // swap odd unconditionally
        SWAP(unsigned int, indexes[nodd], indexes[noddrev]);
    }
    // end of the bitreverse permutation loop
}


unsigned int *create_bitrev(unsigned int length) {
    FOURIER_LOG(35, "Create bit reversal array of length %d", length);
    unsigned int k = 0;
    unsigned int *bit_reversed_indx = MALLOC(length, unsigned int);
    for (k = 0; k < length; k++) {
        bit_reversed_indx[k] = k;
    }
    perform_bitrev(bit_reversed_indx, length);
    return bit_reversed_indx;
}


static int RADIX2_INIT = 0;

#define TWIDDLE_ARRAY_SIZE (1 << 18)
static double TWIDDLE_ARRAY[TWIDDLE_ARRAY_SIZE] = { 0.0 };

#define BITREV_POWERS_NUM 18
#define BITREV_MAX_LENGTH (1 << BITREV_POWERS_NUM)
static unsigned int* BITREV_ARRAY[BITREV_POWERS_NUM+1] = { NULL };


void fft_initialize_radix_2(void) {
    FOURIER_LOG(50, "Initialize FFT radix-2 internal arrays: %d", RADIX2_INIT)
    if (!RADIX2_INIT) {
        unsigned int k = 0;

        for (k = 0; k < TWIDDLE_ARRAY_SIZE; k++) {
            double x = 2.0 * M_PI * (double) k / (double) TWIDDLE_ARRAY_SIZE;
            TWIDDLE_ARRAY[k] = sin(x);
        }

        for (k = 1; k <= BITREV_POWERS_NUM; k++) {
            BITREV_ARRAY[k] = create_bitrev((unsigned int)(1 << k));
        }

        RADIX2_INIT = 1;
    }
}


unsigned int log2shift(unsigned int N) {
    FOURIER_LOG(5, "Calculate for N = %d", N);
    FOURIER_ASSERT(N > 0, FOURIER_ECHO_CRITICAL, "N must be greater than zero!\n");

    unsigned int log2N = 0;
    while (N != 0) {
        N >>= 1;
        log2N++;
    }
    return log2N - 1;
}


static FORCE_INLINE unsigned int *get_bitrev(unsigned int length) {
    unsigned int pow = log2shift(length);
    if (pow <= BITREV_POWERS_NUM) {
        FOURIER_LOG(35, "Get bitrev array from stored data: %d", length);
        return BITREV_ARRAY[pow];
    } else {
        return create_bitrev(length);
    }
}


static FORCE_INLINE void free_bitrev(unsigned int* ptr, unsigned int length) {
    if (length > BITREV_MAX_LENGTH) {
        wfree(ptr);
    }
}


void fftshift(fft_complex_t *data, unsigned int count) {
    int k = 0;
    // Central element
    int c = (int) floor((float) count / 2);
    // For odd and for even numbers of element use different algorithm
    if (count % 2 == 0) {
        for (k = 0; k < c; k++) {
            SWAP(fft_complex_t, data[k], data[k + c])
        }
    } else {
        fft_complex_t tmp = data[0];
        for (k = 0; k < c; k++) {
            data[k] = data[c + k + 1];
            data[c + k + 1] = data[k + 1];
        }
        data[c] = tmp;
    }
}


void ifftshift(fft_complex_t *data, unsigned int count) {
    int k = 0;
    int c = (int) floor((float) count / 2);
    if (count % 2 == 0) {
        for (k = 0; k < c; k++) {
            SWAP(fft_complex_t, data[k], data[k + c])
        }
    } else {
        fft_complex_t tmp = data[count - 1];
        for (k = c - 1; k >= 0; k--) {
            data[c + k + 1] = data[k];
            data[k] = data[c + k];
        }
        data[c] = tmp;
    }
}


int prime_factorize(int result[MAX_PRIMES_COUNT], unsigned int N) {
    FOURIER_ASSERT(N > 0, FOURIER_ECHO_DEBUG, "Argument N = %d less than or equal zero", N);

    if (N < 4) {
        result[0] = N;
        return 1;
    }

    // Count of prime factors
    int count = 0;

    // Current prime multiplier
    int div = 2;

    while (N > 1) {
        if (N % div != 0) {
            div++;
        } else {
            N /= div;
            result[count++] = div;
        }
    }

    return count;
}


FORCE_INLINE int is_prime(unsigned int N) {
    // TODO: I know that is ugly and very time expensive and it will be change later
    // (e.g. Sieve of Eratosthenes)
    int primes[MAX_PRIMES_COUNT];
    int count = prime_factorize(primes, N);
    return count > 1 ? 0 : 1;
}


FORCE_INLINE int is_power2(unsigned int x) {
    return x && !(x & (x - 1));
}


FORCE_INLINE int is_power4(unsigned int x) {
    return x && !(x & (x - 1)) && (x & 0x55555555);
}


FORCE_INLINE void _add_cache_as_table(const fft_twiddles_cache_t* cache, const int k) {
    int imag_indx = TWIDDLE_ARRAY_SIZE / cache->count * k;
    int real_indx = (imag_indx + TWIDDLE_ARRAY_SIZE / 4) % TWIDDLE_ARRAY_SIZE;
    fft_cache_item_t item = {
            .is_calculated = 1,
            .value.r = TWIDDLE_ARRAY[real_indx],
            .value.i = TWIDDLE_ARRAY[imag_indx]
    };
    cache->data[k] = item;
}


FORCE_INLINE void _add_cache_as_calc(const fft_twiddles_cache_t* cache, const int k) {
    fft_cache_item_t item = {
            .is_calculated = 1,
            .value = c_expi(2 * M_PI * (double) k / (double) cache->count)
    };
    cache->data[k] = item;
}


FORCE_INLINE fft_complex_t _cached(const fft_twiddles_cache_t* cache, const int k, const int dir) {
    fft_complex_t cached = cache->data[k].value;
    fft_complex_t twiddle = {
            .r = cached.r,
            .i = (dir == FFT_LITHO_BACKWARD) ? cached.i : -cached.i
    };
    return twiddle;
}


FORCE_INLINE fft_complex_t _calc_twiddle_by_table(const int k, const struct fft_plan_t* plan) {
    FOURIER_LOG(70, "Calculate twiddle using table...")
    int imag_indx = TWIDDLE_ARRAY_SIZE / plan->count * k;
    int real_indx = (imag_indx + TWIDDLE_ARRAY_SIZE / 4) % TWIDDLE_ARRAY_SIZE;
    fft_complex_t twiddle = {
            .r = TWIDDLE_ARRAY[real_indx],
            .i = (plan->direction == FFT_LITHO_BACKWARD) ? TWIDDLE_ARRAY[imag_indx] : -TWIDDLE_ARRAY[imag_indx]
    };
    return twiddle;
};


FORCE_INLINE fft_complex_t _calc_twiddle(const int k, const int N, const int d) {
    return c_expi(2 * M_PI * d * (double) k / (double) N);
};


FORCE_INLINE fft_complex_t _calc_twiddle_by_exp(const int k, const struct fft_plan_t* plan) {
    FOURIER_LOG(70, "Calculate twiddle using c_expi...")
    return _calc_twiddle(k, plan->count, plan->direction);
};


FORCE_INLINE fft_twiddles_cache_t* fft_cache_create_node(const unsigned int count) {
    unsigned int k = 0;

    fft_twiddles_cache_t* cache = MALLOC(1, fft_twiddles_cache_t);

    if (count != 0) {
        cache->count = count;
        cache->data = MALLOC(count, fft_cache_item_t);
        for (k = 0; k < count; k++) {
            cache->data[k].is_calculated = 0;
        }
    }

    for (k = 0; k < MAX_TWIDDLES_CACHE_CHILDREN; k++) {
        cache->children[k] = NULL;
    }

    return cache;
}


FORCE_INLINE fft_twiddles_cache_t* fft_cache_alloc_child(
        fft_twiddles_cache_t* cache, const struct fft_plan_t* plan, const int indx) {
    if (cache != NULL) {
        if (cache->children[indx] == NULL) {
            cache->children[indx] = fft_cache_create_node(plan->count);
        }
        return cache->children[indx];
    } else {
        return NULL;
    }
}


FORCE_INLINE void fft_cache_init(struct fft_plan_t* plan) {
    unsigned int k = 0;
    plan->cache = MALLOC(plan->rank, fft_twiddles_cache_t*);
    for (k = 0; k < plan->rank; k++) {
        plan->cache[k] = plan->flags & FFT_USE_CACHE ? fft_cache_create_node(plan->dims[k]) : NULL;
    }
}


FORCE_INLINE void _fft_cache_destroy(fft_twiddles_cache_t* cache) {
    if (cache != NULL) {
        unsigned int k = 0;

        for (k = 0; k < MAX_TWIDDLES_CACHE_CHILDREN; k++) {
            _fft_cache_destroy(cache->children[k]);
        }

        FREE(cache->data);
        FREE(cache);
    }
}


FORCE_INLINE void fft_cache_destroy(struct fft_plan_t* plan) {
    unsigned int k = 0;
    for (k = 0; k < plan->rank; k++) {
        _fft_cache_destroy(plan->cache[k]);
    }
}


#define USE_RADIX2_TABLE(_plan) \
    TWIDDLE_ARRAY_SIZE % _plan->count == 0 && _plan->count < TWIDDLE_ARRAY_SIZE && _plan->flags & FFT_USE_RADIX2_TABLE


FORCE_INLINE fft_complex_t calc_twiddle(const int k, struct fft_plan_t* plan, fft_twiddles_cache_t* cache) {
    // Get indexes from sinus array that represent specified complex exponent
    // cos(A + pi/2) = sin(A)
    // cos(-A) =  cos(A)
    // sin(-A) = -sin(A)
    INCREASE_CALCULATED_TWIDDLES(plan);

    fft_complex_t twiddle;

    if (cache != NULL) {
        if (!cache->data[k].is_calculated) {
            if (USE_RADIX2_TABLE(plan)) {
                _add_cache_as_table(cache, k);
            } else {
                _add_cache_as_calc(cache, k);
            }
        }
        twiddle = _cached(cache, k, plan->direction);
    } else {
        twiddle = USE_RADIX2_TABLE(plan) ? _calc_twiddle_by_table(k, plan) : _calc_twiddle_by_exp(k, plan);
    }

    FOURIER_LOG(45, "k = %3d N = %3d dir = %2d -> (%7.4f, %7.4f)",
                k, plan->count, plan->direction, twiddle.r, twiddle.i);

    return twiddle;
}


FORCE_INLINE int sign_rotation(int k, int p) {
    // Return value depending on k and p (period) by the next law:
    // 0 1 2 3 4 5 6 7 ...
    // 0 1 0 1 0 1 0 1 ... p = 1
    // 0 0 1 1 0 0 1 1 ... p = 2
    // 0 0 0 0 1 1 1 1 ... p = 4
    // Where alternation of 0 and 1 is equal to p
    return (k / p) % 2;
}


FORCE_INLINE int get_twiddle_sign(int k, int n) {
    // Table of what alternation period has each of twiddle factor
    //       2  4  8
    // 0 ->  0  0  0
    // 1 ->  1  0  0
    // 2 ->  0  1  0
    // 3 ->  1  1  0
    // 4 ->  0  0  1
    // .............
    // For example, sign of zero twiddle factor hasn't got rotation period throught frequency number
    // so for all frequency sign is equal. But for third twiddle factor sign has rotation period
    // by 2 and by 4 depending on frequency number (k). In this case sign equal to:
    // sign_period(k, 2) * sign_period(k, 4). In the code below multiplication replaced by XOR
    // because in the code boolean value used (XOR of boolean values equal to +1/-1 multiplication).

    int p = 0, sign = 0;

    for (p = 1; p <= n; p <<= 1) {
        if (p & n) {
            sign ^= sign_rotation(k, 2 * p);
        }
    }

    return sign ? -1 : 1;
}


#define FFT_RADIX2_CACHED(_plan, _cache, _childno) { \
    fft_twiddles_cache_t* child_cache = fft_cache_alloc_child(cache, _plan, _childno);\
    fft_radix_2(_plan, child_cache); \
}


/*
 * fft_radix_2 - Perform Fast Fourier Transform from input signal specified by <in>
 *               that have power of two number of samples.
 */
void fft_radix_2(struct fft_plan_t *plan, fft_twiddles_cache_t* cache) {
    INCREASE_RECURSION_DEPTH();
    FOURIER_ALGORITHM_STD_LOG(50, plan, "Cooley–Tukey Radix-2");
    FOURIER_ALGORITHM_STD_ASSERTS(FOURIER_ECHO_DEBUG, plan, 2);

    unsigned int s = 0;  // Transform number

    // If frequencies is generated for similar signals then pairs can be calculated once
    // else for different frequency (k) pairs will be also different.
    unsigned int *bitrev_indx = get_bitrev(plan->count);

    for (s = 0; s < plan->howMany; s++) {

        unsigned int stage, group, pair, k;

        for (k = 0; k < plan->count; k+=2) {
            *ovp(plan, s, k + 0) = c_add(iv(plan, s, bitrev_indx[k]), iv(plan, s, bitrev_indx[k+1]));
            *ovp(plan, s, k + 1) = c_sub(iv(plan, s, bitrev_indx[k]), iv(plan, s, bitrev_indx[k+1]));
        }

        for (stage = 2; stage < plan->count; stage <<= 1) {
            const unsigned int jump = stage << 1;
            for (group = 0; group < stage; group++) {
                fft_complex_t twiddle = calc_twiddle(plan->count*group/jump, plan, cache);
                for (pair = group; pair < plan->count; pair += jump) {
                    const unsigned int match = pair + stage;
                    FOURIER_LOG(70, "stage = %2d group = %2d pair = %2d, match = %d", stage, group, pair, match);
                    fft_complex_t t = c_mul(twiddle, ov(plan, s, match));
                    *ovp(plan, s, match) = c_sub(ov(plan, s, pair), t);
                    c_addto(ovp(plan, s, pair), t);
                }
            }
        }

        FOURIER_NORMALIZE(plan, s, k);
    }

    free_bitrev(bitrev_indx, plan->count);

    DECREASE_RECURSION_DEPTH();
}


// Calculate modulus exponent R(b, e, m) = b^e mod m
FORCE_INLINE unsigned int modpow(unsigned int base, unsigned int exp, unsigned int modulus) {
    unsigned int result = 1;
    base %= modulus;
    while (exp > 0) {
        if (exp & 1) {
            result = (result * base) % modulus;
        }
        base = (base * base) % modulus;
        exp >>= 1;
    }
    return result;
}


// Calculate generator number "g" for Galois Field. R(k) = g^k mod N
// If k = 1..M, then generator is "g" such that any number from R(k) not repeat and belong [1; M]
// For example if g = 2, N = 5, and
// k = 1  2  3  4  5  6  7  8
// R = 1  3  4  2  1  3  4  2
// then "g" is generator for "N"
//
// Criteria for "g" is generator is C(k) = g^((N-1)/p[k]) mod N != 1 for any p[k],
// where p[k] is primes of the N-1. One generator must exist for any prime "N".
unsigned int calc_primitive_root(unsigned int N) {
    if (N == 2) {
        return 1;
    } else if (N == 3) {
        return 2;
    }

    int primes[MAX_PRIMES_COUNT];

    unsigned int g, k = 0;

    // Calculate prime number of N-1
    int primes_count = prime_factorize(primes, N - 1);

    // Check that N is prime:
    //   if N-1 is have only one prime_count then N-1 is prime then N can't be prime
    FOURIER_ASSERT(
            primes_count != 1, FOURIER_ECHO_DEBUG,
            "N-1 = %d is prime number then N = %d can't be prime\n", N - 1, N);

    for (g = 2; g < N; g++) {
        int is_generator = 1;

        for (k = 0; is_generator && k < primes_count; k++) {
            is_generator = (modpow(g, (N - 1) / primes[k], N) != 1);
        }

        if (is_generator) {
            return g;
        }
    }

    FOURIER_ASSERT(FOURIER_ASSERT_UNCONDITION, FOURIER_ECHO_CRITICAL, "Generator not found for N = %d\n", N);
    return 0;
}


void fft_mixed_radix(struct fft_plan_t* plan, fft_twiddles_cache_t* cache);


#define FFT_MIXED_CACHED(_plan, _cache, _childno) { \
    fft_twiddles_cache_t* child_cache = fft_cache_alloc_child(cache, _plan, _childno);\
    fft_mixed_radix(_plan, child_cache); \
}


#define FFT_PRIME_CACHED(_plan, _cache, _childno) { \
    fft_twiddles_cache_t* child_cache = fft_cache_alloc_child(cache, _plan, _childno);\
    fft_prime(_plan, child_cache); \
}


void fft_prime(struct fft_plan_t *plan, fft_twiddles_cache_t* cache) {
    INCREASE_RECURSION_DEPTH();

    FOURIER_ALGORITHM_STD_LOG(50, plan, "Prime number");
    FOURIER_ALGORITHM_STD_ASSERTS(FOURIER_ECHO_DEBUG, plan, 2);

    unsigned int s = 0, k = 0;

    unsigned int twiddles_generator = calc_primitive_root(plan->count);

    // Samples generator is differ from twiddles generator and is equals to the next generator
    // number. It can be calculated as g^(-1) mod N. Because loop of the sequence [1] = [N],
    // [0] = [N-1] and [-1] = [N-2].
    unsigned int samples_generator = modpow(twiddles_generator, plan->count - 2, plan->count);

    // Number of samples used in convolution
    unsigned int conv_samples_count = plan->count - 1;

    // Make a convolution between twiddles from generator and part input samples (without zero sample)
    struct fft_plan_t twiddle_plan = {
            .count = conv_samples_count,
            .howMany = 1,
            .in = MALLOC(conv_samples_count, fft_complex_t),
            .idist = 1,
            .istride = 0,
            .out = MALLOC(conv_samples_count, fft_complex_t),
            .odist = 1,
            .ostride = 0,
            .direction = FFT_LITHO_FORWARD
    };

    unsigned int *twiddles_indxes = MALLOC(conv_samples_count, unsigned int);
    unsigned int *samples_indxes = MALLOC(conv_samples_count, unsigned int);

    FOURIER_LOG(30, "Calculate twiddles array to perform convolution");

    for (k = 0; k < conv_samples_count; k++) {
        twiddles_indxes[k] = modpow(twiddles_generator, k, plan->count);
        samples_indxes[k] = modpow(samples_generator, k, plan->count);
        twiddle_plan.in[k] = calc_twiddle(twiddles_indxes[k], plan, cache);
    }

    // Perform twiddle forward transform (required for convolution)
    FFT_MIXED_CACHED(&twiddle_plan, cache, 0);

    // Direction will be set within loop, because it changed in it
    struct fft_plan_t samples_plan = {
            .count = conv_samples_count,
            .howMany = 1,
            .in = MALLOC(conv_samples_count, fft_complex_t),
            .idist = 1,
            .istride = 0,
            .out = MALLOC(conv_samples_count, fft_complex_t),
            .odist = 1,
            .ostride = 0,
    };

    fft_twiddles_cache_t* sample_cache = fft_cache_alloc_child(cache, &samples_plan, 1);
    for (s = 0; s < plan->howMany; s++) {
        FOURIER_LOG(30, "Calculate of samples array #%d/%d FFT to perform convolution", s, plan->howMany);

        // Using modulus generator permutation fill twiddles and samples arrays for convolution
        for (k = 0; k < conv_samples_count; k++) {
            // Calculate result sample index with the offset
            samples_plan.in[k] = iv(plan, s, samples_indxes[k]);
        }

        // Perform FORWARD FFT (convolution, st.1)
        samples_plan.direction = FFT_LITHO_FORWARD;
        fft_mixed_radix(&samples_plan, sample_cache);

        FOURIER_LOG(30, "Calculate specturm multiplication of twiddles and samples #%d/%d", s, plan->howMany);

        // Perform spectrum multiplication (convolution, st.2)
        for (k = 0; k < conv_samples_count; k++) {
            c_mulby(&samples_plan.out[k], twiddle_plan.out[k]);
        }

        FOURIER_LOG(30, "Calculate backward FFT of multiplied spectrums #%d/%d", s, plan->howMany);

        // Perform BACKWARD FFT (convolution, st.3)
        SWAP(fft_complex_t*, samples_plan.in, samples_plan.out);
        samples_plan.direction = FFT_LITHO_BACKWARD;
        fft_mixed_radix(&samples_plan, sample_cache);

#if FOURIER_NORMALIZATION_TYPE == FOURIER_DISABLE_NORMALIZATION
        for (k = 0; k < conv_samples_count; k++) {
            // Normalize data after convolution if in standard FFT normalization disabled
            c_divbyv(&samples_plan.out[k], conv_samples_count);
        }
#endif

        FOURIER_LOG(30, "Calculate zero spectrum data of samples array #%d/%d", s, plan->howMany);
        // Calculate zero spectrum sample by summing all of input elements
        // and add zero input sample to calculated spectrum values (required according to algorithm).
        // Also perform reverse generator permutation

        // out[0] = in[0], assign the zero sample for s-th array
        *ovp(plan, s, 0) = *ivp(plan, s, 0);

        for (k = 1; k < plan->count; k++) {
            // Calculate zero spectrum sample
            c_addto(ovp(plan, s, 0), iv(plan, s, twiddles_indxes[k - 1]));

            // Calculate others spectrum samples by mean of sum with the zero spectrum sample
            *ovp(plan, s, twiddles_indxes[k - 1]) = c_add(samples_plan.out[k - 1], iv(plan, s, 0));
        }

        // Normalization for backward transform only.
        // TODO: may be divide in the above loop is faster?
        FOURIER_NORMALIZE(plan, s, k);
    }

    wfree(samples_indxes);
    wfree(twiddles_indxes);

    wfree(samples_plan.in);
    wfree(samples_plan.out);

    wfree(twiddle_plan.in);
    wfree(twiddle_plan.out);

    DECREASE_RECURSION_DEPTH();
}


int check_implemented_fft(int count, fft_handler_t *handler) {
    int k = 0;

    for (k = FFT_IMPLEMENTED_RADIX_COUNT - 1; k >= 0; k--) {
        if (count == fft_handlers[k].count) {
            if (handler != NULL) {
                *handler = fft_handlers[k].handler;
            }
            FOURIER_LOG(50, "Factor = %d, radix index = %d", fft_handlers[k].count, k);
            return k;
        }
    }

    // Automatical returns -1 if not found
    return k;
}


// TODO: NOT USED - DELETE?
int factorize_number(int result[MAX_PRIMES_COUNT], unsigned int N) {
    int k = 0, count = 0;

    // If number divide by 2 then lookup maximum nearest and lower than number power of two
    if (N % 2 == 0) {
        int radix2 = 1 << log2shift(N);

        while (N % radix2 != 0) {
            radix2 >>= 1;
        }

        result[count++] = radix2;
        N /= result[count];
    }

    // Look up for radix that have fast optimized implementation
    for (k = 0; N > 1 && k < FFT_IMPLEMENTED_RADIX_COUNT; k++) {
        if (N % fft_handlers[k].count == 0) {
            result[count++] = fft_handlers[k].count;
            N /= result[count];
        }
    }

    // Look up odd multipliers
    int div = 3;

    while (N > 1) {
        if (N % div != 0) {
            div += 2;
        } else {
            N /= div;
            result[count++] = div;
        }
    }

    return count;
}


unsigned int fft_get_factor(unsigned int N, int *imp_radix_indx) {
    FOURIER_LOG(10, "Factorize number N = %d", N);
    FOURIER_ASSERT(N > 1, FOURIER_ECHO_DEBUG, "N = %d and can't be factorized\n", N);

    int k = 0;

    // Look up for radix that have fast optimized implementation
    for (k = FFT_IMPLEMENTED_RADIX_COUNT-1; k >= 0; k--) {
        if (N % fft_handlers[k].count == 0) {
            if (imp_radix_indx != NULL) {
                *imp_radix_indx = k;
            }

            FOURIER_LOG(50, "Factor = %d, radix index = %d", fft_handlers[k].count, k);
            return fft_handlers[k].count;
        }
    }

    // If number divide by 2 then lookup maximum nearest and lower than number power of two
    if (N % 2 == 0) {
        unsigned int radix2 = (1U) << log2shift(N);

        while (N % radix2 != 0) {
            radix2 >>= 1;
        }

        if (imp_radix_indx != NULL) {
            *imp_radix_indx = -1;
        }

        FOURIER_LOG(10, "Factor = %d, radix index = %d", radix2, *imp_radix_indx);
        return radix2;
    }

    // Look up odd multipliers
    unsigned int div = 3;

    while (N % div != 0) {
        div += 2;
    }

    if (imp_radix_indx != NULL) {
        *imp_radix_indx = -1;
    }

    FOURIER_LOG(10, "Factor = %d, radix index = %d", div, *imp_radix_indx);
    return div;
}


void fft_singular(struct fft_plan_t *plan) {
    INCREASE_RECURSION_DEPTH();
    FOURIER_ALGORITHM_STD_LOG(50, plan, "Copy")
    // Copy input data to the output
    unsigned int s = 0;
    for (s = 0; s < plan->howMany; s++) {
        *ovp(plan, s, 0) = *ivp(plan, s, 0);
    }
    DECREASE_RECURSION_DEPTH();
}


void fft_split_radix(struct fft_plan_t* plan, fft_twiddles_cache_t* cache) {
    INCREASE_RECURSION_DEPTH();
    FOURIER_ALGORITHM_STD_LOG(50, plan, "Split radix");
    FOURIER_ALGORITHM_STD_ASSERTS(FOURIER_ECHO_DEBUG, plan, 2);

    unsigned int s, k;

    // Here value imp_radix_indx equal index of one of implemented FFT radix if plan->count divide on this radix
    int imp_radix_indx = -1;

    unsigned int prime_factor = fft_get_factor(plan->count, &imp_radix_indx);
    unsigned int mixed_factor = plan->count / prime_factor;

    struct fft_plan_t step_plan;

    step_plan.in = MALLOC(plan->count, fft_complex_t);
    step_plan.out = MALLOC(plan->count, fft_complex_t);
    step_plan.direction = plan->direction;

    for (s = 0; s < plan->howMany; s++) {

        FOURIER_LOG(30, "Calculate column-wise FFT for s = %d", s);

        for (k = 0; k < plan->count; k++) {
            step_plan.in[k] = iv(plan, s, k);
        }

        // Perform FFT by columns
        step_plan.count = prime_factor; // Number of samples in column (equals to rows count)
        step_plan.howMany = mixed_factor; // Number of columns
        step_plan.idist = step_plan.odist = step_plan.howMany; // Dist. between samples (equals to cols. count)
        step_plan.istride = step_plan.ostride = 1; // Dist. between columns

        // For example for 15 sample:
        //  0  1  2  3  4  5  6  7  8  9  10  11  12  13  14
        // fft_get_factor returns 3 then prime_factor = 3 and mixed_factor = 5
        //  0  1  2
        //  3  4  5
        //  6  7  8
        //  9 10 11
        // 12 13 14

        if (step_plan.count == 1) {
            fft_singular(&step_plan);
        } else if (imp_radix_indx != -1) {
            fft_handlers[imp_radix_indx].handler(&step_plan);
//        } else if (prime_factor % 4 == 0) {
//            fft_radix_4(&step_plan, cols_cache);
        } else if (prime_factor % 2 == 0) {
            FFT_RADIX2_CACHED(&step_plan, cache, 0);
        } else {
            FFT_PRIME_CACHED(&step_plan, cache, 0);
        }

        FOURIER_LOG(30, "Calculate columns twiddles multiplications for s = %d", s);

        // Addition twiddles multiplications
        unsigned int r = 0, c = 0;
        // Iterate through columns
        for (c = 1; c < step_plan.howMany; c++) {
            // Iterate through rows
            for (r = 1; r < step_plan.count; r++) {
                fft_complex_t twiddle = calc_twiddle(r * c, plan, cache);
                c_mulby(ovp(&step_plan, c, r), twiddle);
            }
        }

        FOURIER_LOG(30, "Calculate row-wise FFT for s = %d", s);

        //  0  1  2  3  4
        //  5  6  7  8  9
        // 10 11 12 13 14
        // Perform FFT by rows
        SWAP(fft_complex_t*, step_plan.in, step_plan.out);
        step_plan.count = mixed_factor; // Number of samples in row (columns count)
        step_plan.howMany = prime_factor; // Number of rows
        step_plan.idist = 1; // Dist. between samples (no shift, samples near)
        step_plan.odist = step_plan.howMany;
        step_plan.istride = step_plan.count; // Dist. between rows = columns count
        step_plan.ostride = 1;

        fft_twiddles_cache_t* rows_cache = fft_cache_alloc_child(cache, &step_plan, 1);

        fft_mixed_radix(&step_plan, rows_cache);

        for (k = 0; k < plan->count; k++) {
            *ovp(plan, s, k) = step_plan.out[k];
        }
    }

    FOURIER_LOG(5, "Free temporary step plan output buffer");

    // free memory of the temporary buffers
    wfree(step_plan.in);
    wfree(step_plan.out);

    DECREASE_RECURSION_DEPTH();
}


/*
 * count - Number of samples
 * in - Input two-dimensional array. This routine calculate one frequency sample
 *      for different input signal. For first frequency in[n] will be used, for
 *      the second frequency in[count + n], etc. So result spectrum calculated
 *      using in[k*count+n], where k - frequency number, n - input signal sample.
 *      Note: for this routine number of different signal must be equal to the
 *            result frequency number.
 * out - Result signal spectrum
 * direction - FFT_LITHO_FORWARD - forward transform and FFT_LITHO_BACKWARD - backward transform.
 */
void fft_mixed_radix(struct fft_plan_t* plan, fft_twiddles_cache_t* cache) {
    // N = 30 -> 2 * 3 * 5
    // 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29

    //     0  1  2  3  4
    // 0  00 01 02 03 04
    // 1  05 06 07 08 09
    // 2  10 11 12 13 14
    // 3  15 16 17 18 19
    // 4  20 21 22 23 24
    // 5  25 26 27 28 29

    FOURIER_ALGORITHM_STD_ASSERTS(FOURIER_ECHO_DEBUG, plan, 1);

    fft_handler_t implemented_fft;

    // In this case we check if plan->count is equal one of implemented FFT radix
    if (plan->count == 1) {
        fft_singular(plan);
    } else if (check_implemented_fft(plan->count, &implemented_fft) != -1) {
        implemented_fft(plan);
//    } else if (is_power4(plan->count)) {
//        fft_radix_4(plan, cache);
    } else if (is_power2(plan->count)) {
        fft_radix_2(plan, cache);
    } else if (is_prime(plan->count)) {
        fft_prime(plan, cache);
    } else {
        fft_split_radix(plan, cache);
    }
}


struct fft_plan_t* fft_plan_create_many_1d(
        unsigned int count, unsigned int howMany,
        fft_complex_t* in, fft_complex_t* out, int direction,
        unsigned int flags) {
    fft_initialize_radix_2();

    FOURIER_LOG(50, "Create %d one dimension FFT plans for %d samples in=%p out=%p dir=%d",
                howMany, count, in, out, direction);

    FOURIER_ASSERT(in != NULL, FOURIER_ECHO_CRITICAL, "Input buffer can't be NULL\n");
    FOURIER_ASSERT(out != NULL, FOURIER_ECHO_CRITICAL, "Output buffer can't be NULL\n");

    struct fft_plan_t *plan = MALLOC(1, struct fft_plan_t);

    plan->rank = 1;
    plan->total = count;

    plan->dims = MALLOC(1, unsigned int);
    plan->dims[0] = count;

    plan->in = in;
    plan->out = out;

    if (plan->in == plan->out) {
        FOURIER_LOG(50, "Initialize pseudo in place FFT one dimension plan");
        plan->tmpbuf = MALLOC(count * howMany, fft_complex_t);
        plan->out = plan->tmpbuf;
    } else {
        FOURIER_LOG(50, "Initialize out of place FFT one dimension plan");
        plan->tmpbuf = NULL;
    }

    plan->count = count;
    plan->howMany = howMany;
    plan->idist = plan->odist = 1;
    plan->istride = plan->ostride = plan->count;

    plan->direction = direction;

    plan->flags = flags;

    fft_cache_init(plan);

    return plan;
}


struct fft_plan_t* fft_plan_create_1d(unsigned int count,
        fft_complex_t* in, fft_complex_t* out, int direction,
        unsigned int flags) {
    FOURIER_LOG(50, "Create one dimension FFT plan for %d samples in=%p out=%p dir=%d", count, in, out, direction);
    return fft_plan_create_many_1d(count, 1, in, out, direction, flags);
}


struct fft_plan_t* fft_plan_create_nd(unsigned int rank, unsigned int* dims,
        fft_complex_t *in, fft_complex_t *out, int direction, unsigned int flags) {
    fft_initialize_radix_2();

    FOURIER_LOG(50, "Create %d-dimensions FFT plan: in=%p out=%p dir=%d", rank, in, out, direction);

    FOURIER_ASSERT(in != NULL, FOURIER_ECHO_CRITICAL, "Input buffer can't be NULL\n");
    FOURIER_ASSERT(out != NULL, FOURIER_ECHO_CRITICAL, "Output buffer can't be NULL\n");

    unsigned int k = 0;

    struct fft_plan_t *plan = MALLOC(1, struct fft_plan_t);

    plan->rank = rank;
    plan->dims = MALLOC(plan->rank, unsigned int);
    for (k = 0, plan->total = 1; k < plan->rank; k++) {
        plan->total *= dims[k];
        plan->dims[k] = dims[k];
    }

    if (in != out) {
        FOURIER_LOG(50, "Initialize out of place FFT multidimension plan");
        plan->tmpbuf = MALLOC(plan->total, fft_complex_t);
        MEMCPY(plan->tmpbuf, in, plan->total, fft_complex_t);
        plan->in = plan->tmpbuf;
        plan->out = out;
    } else {
        FOURIER_LOG(50, "Initialize in place FFT multidimension plan");
        plan->tmpbuf = MALLOC(plan->total, fft_complex_t);
        plan->in = in;
        plan->out = plan->tmpbuf;
    }

    plan->direction = direction;

    plan->flags = flags;

    fft_cache_init(plan);

    return plan;
}


struct fft_plan_t* fft_plan_create_2d(
        unsigned int n_rows, unsigned int n_cols,
        fft_complex_t *in, fft_complex_t *out, int direction,
        unsigned int flags) {
    FOURIER_LOG(50, "Create two dimensions FFT plan %dx%d: in=%p out=%p dir=%d", n_rows, n_cols, in, out, direction);
    unsigned int dims[2] = {n_rows, n_cols};
    return fft_plan_create_nd(2, dims, in, out, direction, flags);
}


void fft_plan_destroy(struct fft_plan_t* plan) {
    fft_cache_destroy(plan);
    FREE(plan->tmpbuf);
    FREE(plan->dims);
    FREE(plan);
}


void fft_execute_1d(struct fft_plan_t* plan) {
    fft_mixed_radix(plan, plan->cache[0]);

    if (plan->tmpbuf) {
        MEMCPY(plan->in, plan->tmpbuf, plan->count * plan->howMany, fft_complex_t);
    }
}


void fft_execute_2d(struct fft_plan_t* plan) {
    unsigned int k = 0;

    // Column-wise FFT

    plan->count = plan->dims[0];
    plan->howMany = plan->total / plan->dims[0];

    plan->istride = plan->ostride = plan->dims[0];
    plan->idist = plan->odist = 1;

    FOURIER_LOG(60, "Column-wise FFT: rank = %d count = %d howMany = %d stride = %d dist = %d",
                plan->rank, plan->count, plan->howMany, plan->istride, plan->idist);

    fft_mixed_radix(plan, plan->cache[0]);

    SWAP(fft_complex_t*, plan->in, plan->out);

    // Row-wise FFT

    fft_complex_t* backup_in = plan->in;
    fft_complex_t* backup_out = plan->out;

    plan->howMany = plan->dims[0];
    plan->count = plan->dims[1];
    plan->idist = plan->odist = plan->dims[0];
    plan->istride = plan->ostride = 1;
    unsigned int total2d = plan->count * plan->howMany;
    unsigned int howMany2d = plan->total / total2d;

    FOURIER_LOG(60, "total2d = %d howMany2d = %d", total2d, howMany2d);

    for (k = 0; k < howMany2d; k++) {
        FOURIER_LOG(60, "Row-wise FFT #%2d: rank = %d count = %d howMany = %d stride = %d dist = %d",
                    k, plan->rank, plan->count, plan->howMany, plan->istride, plan->idist);

        fft_mixed_radix(plan, plan->cache[1]);

        plan->in += total2d;
        plan->out += total2d;
    }

    plan->in = backup_in;
    plan->out = backup_out;

    // Copy if data from temporary buffer to the input buffer if out of place transformation perform
    if (plan->in != plan->tmpbuf) {
        MEMCPY(plan->in, plan->tmpbuf, plan->count, fft_complex_t);
    }
}


// TODO: not tested
void fft_execute_nd(struct fft_plan_t* plan) {
    unsigned int k = 0;

    fft_execute_2d(plan);

    for (k = 2; k < plan->rank; k++) {
        unsigned int dist = plan->total / plan->dims[k];

        plan->count = plan->dims[k];
        plan->howMany = dist;

        plan->istride = plan->ostride = 1;
        plan->idist = plan->odist = dist;

        FOURIER_LOG(60, "fft_execute_1d #%02d: rank = %d count = %d howMany = %d stride = %d odist = %d",
                    k, plan->rank, plan->count, plan->howMany, plan->istride, plan->idist);

        fft_mixed_radix(plan, plan->cache[k]);

        SWAP(fft_complex_t*, plan->in, plan->out);
    }

    // Copy if data from temporary buffer to the input buffer if out of place transformation perform
    if (plan->in != plan->tmpbuf) {
        MEMCPY(plan->in, plan->tmpbuf, plan->count, fft_complex_t);
    }
}


void fft_execute(struct fft_plan_t* plan) {
    INIT_CALCULATED_TWIDDLES(plan);

    if (plan->rank == 1) {
        fft_execute_1d(plan);
    } else if (plan->rank == 2) {
        fft_execute_2d(plan);
    } else {
        fft_execute_nd(plan);
    }

    PRINT_CALCULATED_TWIDDLES(plan);
}


