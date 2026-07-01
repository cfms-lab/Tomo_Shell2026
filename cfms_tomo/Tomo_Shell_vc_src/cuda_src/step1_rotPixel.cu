
#include <iostream>
#include <stdio.h>
#include <device_functions.h>
#include "atomicWrite.cuh"
#include "step1_rotPixel.cuh"

using namespace Tomo;


__global__ void cu_rotPixel_Streamed_16x16(
	int nVoxelX, int nCVVoxel ,  int nYPR,	int yprID ,
	float* cu_m4x3 , 
	float* cu_CVVoxels ,//obsolete..
	CU_SLOT_BUFFER_TYPE* cu_nPixl, 
	CU_SLOT_BUFFER_TYPE* cu_pType, 
	CU_SLOT_BUFFER_TYPE* cu_pZcrd, 
	CU_SLOT_BUFFER_TYPE* cu_pZnrm,
	bool bShellMesh,
	int shell_z_offset)
{
	const int thID		= blockIdx.x * blockDim.x + threadIdx.x;
	if(yprID >= nYPR || thID >= nCVVoxel) return;

	//per-BLOCK operation +++++++++++++++
	const int thIDx		= threadIdx.x;
	__shared__ float m4x3[CU_MATRIX_SIZE_12];
	if (thIDx <  CU_MATRIX_SIZE_12)	{//copy matrix data to shared memory..
		 m4x3[thIDx]	= cu_m4x3[yprID * CU_MATRIX_SIZE_12 + thIDx];
	}
	__syncthreads();
	//+++++++++++++++++++++++++++++++++++

	float crd[3], nrm[3];
	//get new coord after rotation.
	crd[0] = cu_CVVoxels[thID * 6 + 0];
	crd[1] = cu_CVVoxels[thID * 6 + 1];
	crd[2] = cu_CVVoxels[thID * 6 + 2];
	cu_matrixOp(m4x3, crd);

	//get new normal vector
	nrm[0] = cu_CVVoxels[thID * 6 + 3];
	nrm[1] = cu_CVVoxels[thID * 6 + 4];
	nrm[2] = cu_CVVoxels[thID * 6 + 5];
#if 0
	cu_matrixOp(m4x3, nrm);
	nrm[0] -= m4x3[3];//eliminate translation
	nrm[1] -= m4x3[7];
	nrm[2] -= m4x3[11];
#else
	nrm[2] = m4x3[8] * nrm[0] + m4x3[9] * nrm[1] + m4x3[10] * nrm[2];
#endif

	//slot Pixel info
	int X = int(crd[0] + cu_fMARGIN);
	int Y = int(crd[1] + cu_fMARGIN);
	int Z = int(crd[2]);
	int nZ = int(nrm[2] * cu_fNORMALFACTOR);

	if( X< 0 || Y < 0 || X >= nVoxelX || Y >=  nVoxelX || Z <0 || Z >= nVoxelX) return;

	//insert pxl to slot.
	const int				slot_ID			= Y * nVoxelX + X;//target slot ID.
	int S_L = cu_nPixl[slot_ID];//current number of pxls in the slot
	if(S_L < CU_SLOT_CAPACITY_16 - 1)
	{ 
		S_L = atomicAdd(	 (int*) cu_nPixl + slot_ID, 1);//increase target slot's current # of pxls
		const CU_ULInt	slotdata_ID	= slot_ID * CU_SLOT_CAPACITY_16 + S_L;//pxl ID inside the target slot
		cu_Exch( cu_pZcrd + slotdata_ID, Z);
		cu_Exch( cu_pZnrm + slotdata_ID, nZ);
		#ifdef _CUDA_USE_SPLIT_AL_BE_IN_VOXELIZE_STEP
		cu_Or(	 cu_pType + slotdata_ID, (nZ > 10) ? typeAl : ((nZ < -10) ? typeBe : 0));// = splitAlBe()
		#endif

		if (bShellMesh && shell_z_offset > 0) //입력 데이터가 닫히지 않은 shell 형태인경우
		{
			S_L = cu_nPixl[slot_ID];//slot_ID=(x,y)는 동일
			if (S_L < CU_SLOT_CAPACITY_16 - 1)
			{
				S_L = atomicAdd((int*)cu_nPixl + slot_ID, 1);//increase target slot's current # of pxls
				const CU_ULInt	slotdata_ID = slot_ID * CU_SLOT_CAPACITY_16 + S_L;//pxl ID inside the target slot
				cu_Exch(cu_pZcrd + slotdata_ID, (nZ > 0) ? Z - shell_z_offset : Z + shell_z_offset);
				cu_Exch(cu_pZnrm + slotdata_ID, nZ * -1);
#ifdef _CUDA_USE_SPLIT_AL_BE_IN_VOXELIZE_STEP
				cu_Or(cu_pType + slotdata_ID, ((nZ * -1) > 10) ? typeAl : (((nZ * -1) < -10) ? typeBe : 0));// = splitAlBe()
#endif
			}
		}
	}		
}