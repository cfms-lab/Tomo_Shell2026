#pragma once
#include "CUDA_types.cuh" 

__global__ void cu_rotPixel_Streamed_16x16(
	int nVoxelX, int nCVVoxel, int nYPR, int yprID,
	float* cu_m4x3, 
	float* cu_CVVoxels, //obsolete..
	CU_SLOT_BUFFER_TYPE* cu_nPixl,
	CU_SLOT_BUFFER_TYPE* cu_pType,
	CU_SLOT_BUFFER_TYPE* cu_pZcrd,
	CU_SLOT_BUFFER_TYPE* cu_pZnrm,
	bool bInputMeshNotClosed,
	int shell_z_offset);
