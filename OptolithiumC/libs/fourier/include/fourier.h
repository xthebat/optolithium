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

#ifndef FOURIER_H_
#define FOURIER_H_


#ifdef __cplusplus
extern "C" {
#endif


#define FOURIER_ASSERT_UNCONDITION 0


#define FOURIER_ECHO_DEBUG     0
#define FOURIER_ECHO_VERBOSE   1
#define FOURIER_ECHO_CRITICAL  2
#define FOURIER_ECHO_NONE      3


#define FFT_LITHO_FORWARD  (-1)
#define FFT_LITHO_BACKWARD (+1)


#define FOURIER_DISABLE_NORMALIZATION 0
#define FOURIER_BACKWARD_NORMALIZATION FFT_LITHO_BACKWARD
#define FOURIER_FORWARD_NORMALIZATION FFT_LITHO_FORWARD


#ifndef FOURIER_LOG_VERBOSE_LEVEL
#define FOURIER_LOG_VERBOSE_LEVEL 100
#endif

#ifndef FOURIER_ASSERT_VERBOSE_LEVEL
#define FOURIER_ASSERT_VERBOSE_LEVEL FOURIER_ECHO_NONE
//#define FOURIER_ASSERT_VERBOSE_LEVEL FOURIER_ECHO_DEBUG
#endif

#ifndef FOURIER_NORMALIZATION_TYPE
#define FOURIER_NORMALIZATION_TYPE FOURIER_DISABLE_NORMALIZATION
//#define FOURIER_NORMALIZATION_TYPE FFT_LITHO_BACKWARD
#endif


#define MAX_PRIMES_COUNT 32


typedef struct {
    double r;
    double i;
} fft_complex_t;


void fftshift(fft_complex_t *data, unsigned int count);
void ifftshift(fft_complex_t *data, unsigned int count);


/*
 * result - Obtained primes of the number N
 * 		    Note: Maximum number of element after factorization may occurred if number is only radix-2.
 * 		    For 32-bit int value in this case obviously that maximum prime multipliers count is 32.
 * 		    This value is also maximum multiplier count because for any other prime value number of
 * 		    multiplier will be reduced.
 * return: Count of prime factors
 */
// TODO: Sieve of Eratosthenes
int prime_factorize(int result[32], unsigned int N);
int is_prime(unsigned int N);
int is_power2(unsigned int x);

// Twiddles cache structure definition

#define MAX_TWIDDLES_CACHE_CHILDREN 3
struct _fft_twiddles_cache_t;


typedef struct {
    int is_calculated;
    fft_complex_t value;
} fft_cache_item_t;


struct _fft_twiddles_cache_t {
    unsigned int count;
    fft_cache_item_t* data;
    struct _fft_twiddles_cache_t* children[MAX_TWIDDLES_CACHE_CHILDREN];
};

// FFT plan structure definition

#define FFT_NO_FLAGS          0x00
#define FFT_USE_CACHE         0x01
#define FFT_USE_RADIX2_TABLE  0x02


struct fft_plan_t {
	unsigned int count;     // Number of FFT samples
	unsigned int howMany;   // Number of FFT transforms
    fft_complex_t* in;      // Memory block of input array
	int idist;              // Shift between samples for the same signal (for single normal FFT transform istride = 1)
	int istride;            // Shift between samples for different signal (algorithm use it only if howMany > 1)
	int __unused _inext;    // Used only if required to calculate only one harmonic for many signals and should
	                        // be set to shift between different signal (else equal to 0).
                            // Option is used to calculate one frequency sample
	                        // for different input signal. For first frequency in[n] will be used, for
	                        // the second frequency in[count + n], etc. So result spectrum calculated
	                        // using in[k*count+n], where k - frequency number, n - input signal sample
	fft_complex_t* out;     // Memory block of output array (memory must be preallocated)
	int ostride;            // See istride.
	int odist;              // See idist.
	int direction;          // One of FFT_LITHO_FORWARD or FFT_LITHO_BACKWARD

    // Input sample address calculated as: in + k*inext + s*istride + k*idist
	// Output sample address calculated as: out + s*ostride + k*odist
    //       where s - iterate to howMany, k - iterate to sample count

    fft_complex_t *tmpbuf;  // Temporary buffer for in place transformation

    struct _fft_twiddles_cache_t** cache;
    unsigned int flags;

    // Multi-dimension extensions
    unsigned int total;     // Total items for N-dimensions transformation
    unsigned int rank;      // Number of independent dimensions
    unsigned int *dims;     // Pointer to array with each dimension elements count

    // Performance debug
#if FOURIER_LOG_VERBOSE_LEVEL <= 50
    unsigned int calculated_twiddles;
#endif
};

typedef struct _fft_twiddles_cache_t fft_twiddles_cache_t;


//void fft_radix_2(struct fft_plan_t* plan);
//void fft_prime(struct fft_plan_t *plan);
//void fft_mixed_radix(struct fft_plan_t *plan);

// Initialize internal arrays for radix-2 transform.
// This function perform at the first plan creation,
// but it can be called at any point program before FFT used.
void fft_initialize_radix_2(void);

struct fft_plan_t* fft_plan_create_1d(
        unsigned int count, fft_complex_t* in, fft_complex_t* out,
        int direction, unsigned int flags);

struct fft_plan_t* fft_plan_create_many_1d(
        unsigned int count, unsigned int howMany,
        fft_complex_t* in, fft_complex_t* out,
        int direction, unsigned int flags);

struct fft_plan_t* fft_plan_create_2d(
        unsigned int n_rows, unsigned int n_cols,
        fft_complex_t* in, fft_complex_t* out,
        int direction, unsigned int flags);

struct fft_plan_t* fft_plan_create_nd(
        unsigned int rank, unsigned int* dims,
        fft_complex_t* in, fft_complex_t* out,
        int direction, unsigned int flags);

void fft_plan_destroy(struct fft_plan_t* state);

void fft_execute_1d(struct fft_plan_t* plan);
void fft_execute_2d(struct fft_plan_t* plan);
void fft_execute_nd(struct fft_plan_t* plan);
void fft_execute(struct fft_plan_t* plan);

#ifdef __cplusplus
}
#endif

#endif /* FOURIER_H_ */
