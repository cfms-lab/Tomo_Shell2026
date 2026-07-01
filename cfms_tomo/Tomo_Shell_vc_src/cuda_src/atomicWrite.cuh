#include "CUDA_types.cuh"


__device__ static inline char atomicAdd(char* address, char val);
__device__ static inline char atomicOr(char* address, char val);
__device__ static inline char atomicCAS(char* address, char expected, char desired);
__device__ static inline char atomicAdd2(char* address, char val);
__device__ static inline char atomicMinChar(char* address, char val);

__device__ void cu_Add( CU_SLOT_BUFFER_TYPE* mem, CU_SLOT_BUFFER_TYPE value);
__device__ void cu_Exch( CU_SLOT_BUFFER_TYPE* mem, CU_SLOT_BUFFER_TYPE value);
__device__ void cu_Or( CU_SLOT_BUFFER_TYPE* mem, CU_SLOT_BUFFER_TYPE value);


const unsigned FULL_MASK = 0xffffffff;
__device__ __inline__ CU_SLOT_BUFFER_TYPE shfl_down(int val, unsigned int offset, int width) // https://github.com/AstroAccelerateOrg/astro-accelerate/issues/61
{ 
	#if (CUDART_VERSION >= 10000) 
		return(__shfl_down_sync(FULL_MASK, val, offset, width)); 
	#else 
		return(__shfl_down(val, offset, width)); 
	#endif 
}

__device__ __inline__ CU_SLOT_BUFFER_TYPE shfl_up(int val, unsigned  int offset, int width) // https://github.com/AstroAccelerateOrg/astro-accelerate/issues/61
{ 
	#if (CUDART_VERSION >= 10000) 
		return(__shfl_up_sync(FULL_MASK, val, offset, width)); 
	#else 
		return(__shfl_up(val, offset, width)); 
	#endif 
}
