#include "atomicWrite.cuh"

//refer to Greg Kramida @ https://stackoverflow.com/questions/5447570/cuda-atomic-operations-on-unsigned-chars
using namespace Tomo;

__device__ static inline char atomicAdd(char* address, char val) 
{
		// offset, in bytes, of the char* address within the 32-bit address of the space that overlaps it
		size_t long_address_modulo = (size_t) address & 3;
		// the 32-bit address that overlaps the same memory
		auto* base_address = (unsigned int*) ((char*) address - long_address_modulo);
		// A 0x3210 selector in __byte_perm will simply select all four bytes in the first argument in the same order.
		// The "4" signifies the position where the first byte of the second argument will end up in the output.
		unsigned int selectors[] = {0x3214, 0x3240, 0x3410, 0x4210};
		// for selecting bytes within a 32-bit chunk that correspond to the char* address (relative to base_address)
		unsigned int selector = selectors[long_address_modulo];
		unsigned int long_old, long_assumed, long_val, replacement;

		long_old = *base_address;

		do {
				long_assumed = long_old;
				// replace bits in long_old that pertain to the char address with those from val
				long_val = __byte_perm(long_old, 0, long_address_modulo) + val;
				replacement = __byte_perm(long_old, long_val, selector);
				long_old = atomicCAS(base_address, long_assumed, replacement);
		} while (long_old != long_assumed);
		return __byte_perm(long_old, 0, long_address_modulo);
}

__device__ static inline char atomicOr(char* address, char val) 
{
		size_t long_address_modulo = (size_t) address & 3;
		auto* base_address = (unsigned int*) ((char*) address - long_address_modulo);
		unsigned int selectors[] = {0x3214, 0x3240, 0x3410, 0x4210};
		unsigned int selector = selectors[long_address_modulo];
		unsigned int long_old, long_assumed, long_val, replacement;

		long_old = *base_address;

		do {
				long_assumed = long_old;
				long_val = __byte_perm(long_old, 0, long_address_modulo) + val;
				replacement = __byte_perm(long_old, long_val, selector);
				//long_old = atomicCAS(base_address, long_assumed, replacement);
				long_old = atomicOr(base_address, replacement);
		} while (long_old != long_assumed);
		return __byte_perm(long_old, 0, long_address_modulo);
}


__device__ static inline char atomicCAS(char* address, char expected, char desired) 
{
		size_t long_address_modulo = (size_t) address & 3;
		auto* base_address = (unsigned int*) ((char*) address - long_address_modulo);
		unsigned int selectors[] = {0x3214, 0x3240, 0x3410, 0x4210};

		unsigned int sel = selectors[long_address_modulo];
		unsigned int long_old, long_assumed, long_val, replacement;
		char old;

		long_val = (unsigned int) desired;
		long_old = *base_address;
		do {
				long_assumed = long_old;
				replacement = __byte_perm(long_old, long_val, sel);
				long_old = atomicCAS(base_address, long_assumed, replacement);
				old = (char) ((long_old >> (long_address_modulo * 8)) & 0x000000ff);
		} while (expected == old && long_assumed != long_old);

		return old;
}

__device__ static inline char atomicAdd2(char* address, char val) 
{
		size_t long_address_modulo = (size_t) address & 3;
		auto* base_address = (unsigned int*) ((char*) address - long_address_modulo);
		unsigned int long_val = (unsigned int) val << (8 * long_address_modulo);
		unsigned int long_old = atomicAdd(base_address, long_val);

		if (long_address_modulo == 3) {
				// the first 8 bits of long_val represent the char value,
				// hence the first 8 bits of long_old represent its previous value.
				return (char) (long_old >> 24);
		} else {
				// bits that represent the char value within long_val
				unsigned int mask = 0x000000ff << (8 * long_address_modulo);
				unsigned int masked_old = long_old & mask;
				// isolate the bits that represent the char value within long_old, add the long_val to that,
				// then re-isolate by excluding bits that represent the char value
				unsigned int overflow = (masked_old + long_val) & ~mask;
				if (overflow) {
						atomicSub(base_address, overflow);
				}
				return (char) (masked_old >> 8 * long_address_modulo);
		}
}

//refer to tera @ https://forums.developer.nvidia.com/t/atomicmin-on-char-is-there-a-way-to-compare-char-to-in-to-use-atomicmin/22246/2

__device__ static inline char atomicMinChar(char* address, char val)
{
	unsigned int *base_address = (unsigned int *)((size_t)address & ~3);
	unsigned int selectors[] = {0x3214, 0x3240, 0x3410, 0x4210};
	unsigned int sel = selectors[(size_t)address & 3];
	unsigned int old, assumed, min_, new_;

	old = *base_address;
	do {
		assumed = old;
		min_ = min(val, (char)__byte_perm(old, 0, ((size_t)address & 3) | 0x4440));
		new_ = __byte_perm(old, min_, sel);
		if (new_ == old)     break;
		old = atomicCAS(base_address, assumed, new_);
	} while (assumed != old);
	return old;
}

//---------------------------------------------------------------
__device__ void cu_Add( CU_SLOT_BUFFER_TYPE* mem, CU_SLOT_BUFFER_TYPE value)
{
#ifdef _CUDA_USE_ATOMIC_WRITE_FOR_INT32_SLOTBUFFER
	atomicAdd(  mem, value);
#else
	*mem += value;
#endif


}

__device__ void cu_Exch(CU_SLOT_BUFFER_TYPE* mem , CU_SLOT_BUFFER_TYPE value)
{
#ifdef _CUDA_USE_ATOMIC_WRITE_FOR_INT32_SLOTBUFFER
	atomicExch(  mem, value);
#else
	*mem = value;
#endif
}

__device__ void cu_Or(CU_SLOT_BUFFER_TYPE* mem , CU_SLOT_BUFFER_TYPE value)
{
#ifdef _CUDA_USE_ATOMIC_WRITE_FOR_INT32_SLOTBUFFER
	atomicOr(  mem, value);
#else
	*mem |= value;
#endif

}


//---------------------------------------------------------------


//__device__ __inline__ float shfl_xor(unsigned mask, float XX) // https://github.com/AstroAccelerateOrg/astro-accelerate/issues/61
//{ 
//	#if (CUDART_VERSION >= 7000) 
//		return(__shfl_xor_sync(FULL_MASK,mask, XX)); 
//	#else return(__shfl_xor(XX)); 
//	#endif 
//}


