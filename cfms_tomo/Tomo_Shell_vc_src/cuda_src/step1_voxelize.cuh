#pragma once
#include "CUDA_types.cuh" 


//ToDo1: SLOT_CAPACITY->16
//ToDo2: int32 -> uchar8   https://stackoverflow.com/questions/5447570/cuda-atomic-operations-on-unsigned-chars


__global__ void cu_rotVoxel_16x16(
	int nTri, int nYPR, int nVoxelX, int yprID_to_start,
	float* dev_m4m,  float* dev_tri0,  
	CU_SLOT_BUFFER_TYPE* dev_nPixel, 
	CU_SLOT_BUFFER_TYPE* dev_pType, 
	CU_SLOT_BUFFER_TYPE* dev_pZcrd, 
	CU_SLOT_BUFFER_TYPE* dev_pZnrm);


__global__ void cu_rotVoxel_Streamed_16x16(
	int nVoxelX, int nYPR, int nFlatTri, int yprID, int triID_to_start,
	float* cu_m4x3, float* cu_flattri0,
	int* cu_parentHit,
	CU_SLOT_BUFFER_TYPE* cu_nPixel,
	CU_SLOT_BUFFER_TYPE* cu_pKey,
	CU_SLOT_BUFFER_TYPE* cu_pTri,
	CU_SLOT_BUFFER_TYPE* cu_pType,
	CU_SLOT_BUFFER_TYPE* cu_pZcrd,
	CU_SLOT_BUFFER_TYPE* cu_pZnrm,
	bool bShellMesh,
	int shell_z_offset);


__global__ void cu_rotVoxelFallback_Streamed_1d(
	int nVoxelX, int nYPR, int nTri, int yprID,
	float* cu_m4x3, float* cu_parentFallbackTri,
	int* cu_parentHit,
	CU_SLOT_BUFFER_TYPE* cu_nPixel,
	CU_SLOT_BUFFER_TYPE* cu_pKey,
	CU_SLOT_BUFFER_TYPE* cu_pTri,
	CU_SLOT_BUFFER_TYPE* cu_pType,
	CU_SLOT_BUFFER_TYPE* cu_pZcrd,
	CU_SLOT_BUFFER_TYPE* cu_pZnrm,
	bool bShellMesh,
	int shell_z_offset);

__global__ void cu_rotVoxelOriginal_Streamed_16x16(
	int nVoxelX, int nYPR, int nTri, int yprID,
	float* cu_m4x3, int* cu_tri0, float* cu_vtx0, float* cu_vtxNrm0,
	int* cu_triHitCount,
	CU_SLOT_BUFFER_TYPE* cu_nPixel,
	CU_SLOT_BUFFER_TYPE* cu_pKey,
	CU_SLOT_BUFFER_TYPE* cu_pTri,
	CU_SLOT_BUFFER_TYPE* cu_pType,
	CU_SLOT_BUFFER_TYPE* cu_pZcrd,
	CU_SLOT_BUFFER_TYPE* cu_pZnrm,
	bool bShellMesh,
	int shell_z_offset);

__global__ void cu_rotVoxelOriginal_WarpPerTri(
	int nVoxelX, int nYPR, int nTri, int yprID,
	float* cu_m4x3, int* cu_tri0, float* cu_vtx0, float* cu_vtxNrm0,
	int* cu_triHitCount,
	CU_SLOT_BUFFER_TYPE* cu_nPixel,
	CU_SLOT_BUFFER_TYPE* cu_pKey,
	CU_SLOT_BUFFER_TYPE* cu_pTri,
	CU_SLOT_BUFFER_TYPE* cu_pType,
	CU_SLOT_BUFFER_TYPE* cu_pZcrd,
	CU_SLOT_BUFFER_TYPE* cu_pZnrm,
	bool bShellMesh,
	int shell_z_offset);

__global__ void cu_truncateSlots(
	int nSlot, int keepN,
	CU_SLOT_BUFFER_TYPE* cu_nPixel,
	CU_SLOT_BUFFER_TYPE* cu_pKey,
	CU_SLOT_BUFFER_TYPE* cu_pTri,
	CU_SLOT_BUFFER_TYPE* cu_pType,
	CU_SLOT_BUFFER_TYPE* cu_pZcrd,
	CU_SLOT_BUFFER_TYPE* cu_pZnrm);