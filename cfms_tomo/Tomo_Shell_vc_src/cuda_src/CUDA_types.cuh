#pragma once
#define CUDA_API_PER_THREAD_DEFAULT_STREAM 1
#pragma warning(disable: 4819)//Unicode
#include <iostream>
#include "cuda.h"
#include "cuda_runtime.h"
#include "device_launch_parameters.h"
#include "cuda_runtime_api.h"
#include "..\Tomo_types.h"


#ifdef __INTELLISENSE__ //__syncthreads()������ ���ֱ� https://jueony.tistory.com/10
#define __CUDACC__
#define __global__ 
#define __host__ 
#define __device__ 
#define __device_builtin__
#define __device_builtin_texture_type__
#define __device_builtin_surface_type__
#define __cudart_builtin__
#define __constant__ 
#define __shared__ 
#define __restrict__
#define __noinline__
#define __forceinline__
#define __managed__
#endif 


using namespace Tomo;
typedef FLOAT32 CU_FLOAT32;
typedef unsigned long int CU_ULInt;

#define _CUDA_USE_ATOMIC_WRITE_FOR_INT32_SLOTBUFFER
#define _CUDA_USE_ROTATE_AND_PIXELIZE_IN_ONE_STEP
	#define _CUDA_USE_MULTI_STREAM //�Ⱦ��� 4090���� ������.

//#define _CUDA_USE_NONZERO_SLOTBUFFER_ONLY //not working in 4090?? 
#define _CUDA_USE_SHARED_MEMORY_IN_SLOTPAIRING
#define _CUDA_USE_SPLIT_AL_BE_IN_VOXELIZE_STEP// 2025-07-30. bShellMesh 일 때에는 켜는 게 낫다.

#define _CUDA_USE_SERIALIZED_SLOTDATA_MEMORY
//#define _CUDA_USE_SERIALIZED_VO_VSS_MEMORY //4090���� �� �̻��ϰ� ����� ����.
#define _CUDA_USE_REDUCED_SUM_BATCH //reduced sum�� �� ���� ��Ƽ� ó���ϱ�. ���� �ϴ� �ͺ��� ������.

	//CUDA version TomoNV types
typedef			 int CU_SLOT_BUFFER_TYPE;//4 bytes [	-2,147,483,648 ~ 2,147,483,647]

static const int CU_FLATTRI_SIZE_16		= 20;//triangle data cpu->gpu: vtx0,vtx1,vtx2,nrm0,nrm1,nrm2 (3*6) + AABB[2]. 3 per-vertex normals enable CPU-matching normal interpolation.
static const int CU_SLOT_CAPACITY_16	= 64;//larger slot capacity for shell-thickness voxelization
static const int CU_MATRIX_SIZE_12		= 12;//4x3 rotation/translation matrix

static const int CU_TRI_PER_WORK			= 32;//RTX4090�� 16���� 32�� �� �� ������. https://junstar92.tistory.com/430
static const int CU_SLOTS_PER_WORK		= 8;//RTX4090�� 32���� 16�� ����.

static const int CU_MAX_NUMBER_OF_STREAM = 16;

__device__ const CU_FLOAT32 cu_fMARGIN = 0.001;//epsilon
__device__ const CU_FLOAT32 cu_fNORMALFACTOR = 1000.;//store normal vector [-1.f, +1.f] to [-1000i, +1000i]
__device__ const CU_FLOAT32 cu_HALF_VOXEL_SIZE = 0.5;

__device__ const CU_SLOT_BUFFER_TYPE cu_typeAl	= 1 << (int)enumPixelType::eptAl;//1
__device__ const CU_SLOT_BUFFER_TYPE cu_typeBe	= 1 << (int)enumPixelType::eptBe;//2
__device__ const CU_SLOT_BUFFER_TYPE cu_typeSSB	= 1 << (int)enumPixelType::eptSSB;//4
__device__ const CU_SLOT_BUFFER_TYPE cu_typeSSA	= 1 << (int)enumPixelType::eptSSA;//8
__device__ const CU_SLOT_BUFFER_TYPE cu_typeSS	= 1 << (int)enumPixelType::eptSS;//16
__device__ const CU_SLOT_BUFFER_TYPE cu_typeBed	= 1 << (int)enumPixelType::eptBed;//32
__device__ const CU_SLOT_BUFFER_TYPE cu_typeVo	= 1 << (int)enumPixelType::eptVo;//64
__device__ const CU_SLOT_BUFFER_TYPE cu_typeVss	= 1 << (int)enumPixelType::eptVss;//128
__device__ const CU_SLOT_BUFFER_TYPE cu_typeTC	= 1 << (int)enumPixelType::eptTC;//256
__device__ const CU_SLOT_BUFFER_TYPE cu_typeNVB	= 1 << (int)enumPixelType::eptNVB;//512
__device__ const CU_SLOT_BUFFER_TYPE cu_typeNVA	= 1 << (int)enumPixelType::eptNVA;//1024



template<typename T> struct ShouldSwap
{//https://github.com/master-hpc/mp-generic-bubble-sort/blob/master/generic-bubble-sort.cu
	ShouldSwap(bool _bOrder = true) : bDescendingOrder(_bOrder) {}
	~ShouldSwap() {}
	bool  bDescendingOrder;
	__host__ __device__ 	bool operator() (const T left, const T right) const;
};


template<typename T> __host__ __device__ bool ShouldSwap<T>::operator() (const T left, const T right) const
{
	if (bDescendingOrder) 	return left < right;
	else return left > right;
}


template<typename T> __host__ __device__ __inline__ void swap(T* a, T* b)
{
	T tmp = *a; 	*a = *b;	*b = tmp;
}


__device__ __inline__ CU_FLOAT32 cu_dot2D(CU_FLOAT32* a, CU_FLOAT32* b) {	return a[0] * b[0] + a[1] * b[1]; }

void  cu_startTimer(void);
void  cu_endTimer(const char* title);


#define cudaCheckError() {                                          \
	cudaError_t e=cudaGetLastError();                                  \
	if(e!=cudaSuccess) {                                               \
	printf("Cuda failure %s:%d: '%s'\n",__FILE__,__LINE__,cudaGetErrorString(e));           \
	exit(0); \
	}                                                                  \
}
__device__ __inline__  void cu_matrixOp(float* mat4x3, float* xyz)
{
	float temp[4] = { xyz[0], xyz[1], xyz[2], 1. };//add homogeneous coordinate.

	xyz[0]  = mat4x3[0 * 4 + 0] * temp[0];
	xyz[0] += mat4x3[0 * 4 + 1] * temp[1];
	xyz[0] += mat4x3[0 * 4 + 2] * temp[2];
	xyz[0] += mat4x3[0 * 4 + 3] * temp[3];

	xyz[1]  = mat4x3[1 * 4 + 0] * temp[0];
	xyz[1] += mat4x3[1 * 4 + 1] * temp[1];
	xyz[1] += mat4x3[1 * 4 + 2] * temp[2];
	xyz[1] += mat4x3[1 * 4 + 3] * temp[3];

	xyz[2]  = mat4x3[2 * 4 + 0] * temp[0];
	xyz[2] += mat4x3[2 * 4 + 1] * temp[1];
	xyz[2] += mat4x3[2 * 4 + 2] * temp[2];
	xyz[2] += mat4x3[2 * 4 + 3] * temp[3];

	//xyz[3] calculation is not neeed (affine transform).

}
