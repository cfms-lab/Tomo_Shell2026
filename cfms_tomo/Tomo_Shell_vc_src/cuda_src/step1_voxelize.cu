#include "step1_voxelize.cuh"
#include <iostream>
#include <stdio.h>
#include "atomicWrite.cuh"

using namespace Tomo;

__device__  __inline__ bool  cu_getBaryCoord2D(
	/*inputs*/ CU_FLOAT32* p, CU_FLOAT32* triA, CU_FLOAT32* triB, CU_FLOAT32* triC,
	/*output*/ CU_FLOAT32& u, CU_FLOAT32& v, CU_FLOAT32& w)
{//https://ceng2.ktu.edu.tr/~cakir/files/grafikler/Texture_Mapping.pdf
	CU_FLOAT32 v0[2] = { triB[0] - triA[0], triB[1] - triA[1] };
	CU_FLOAT32 v1[2] = { triC[0] - triA[0], triC[1] - triA[1] };
	CU_FLOAT32 v2[2] = { p[0] - triA[0], p[1] - triA[1] };

	CU_FLOAT32 d00 = cu_dot2D(v0, v0);
	CU_FLOAT32 d01 = cu_dot2D(v0, v1);
	CU_FLOAT32 d11 = cu_dot2D(v1, v1);
	CU_FLOAT32 d20 = cu_dot2D(v2, v0);
	CU_FLOAT32 d21 = cu_dot2D(v2, v1);

	CU_FLOAT32 denom = d00 * d11 - d01 * d01;

	if ( abs(denom) <cu_fMARGIN) return false;

	v = (d11 * d20 - d01 * d21) / denom;
	w = (d00 * d21 - d01 * d20) / denom;
	u = 1.0 - v - w;

	return  (u >= -cu_fMARGIN && v >= -cu_fMARGIN && v <= 1.f + cu_fMARGIN && u + v <= 1.f + cu_fMARGIN);

}

__device__  __inline__ CU_SLOT_BUFFER_TYPE  cu_getBaryCoordZ(
	/*inputs*/ CU_FLOAT32 p_x,CU_FLOAT32 p_y, 
	CU_FLOAT32* triA, CU_FLOAT32* triB, CU_FLOAT32* triC)
{
	CU_FLOAT32 v0[2] = { triB[0] - triA[0], triB[1] - triA[1] };
	CU_FLOAT32 v1[2] = { triC[0] - triA[0], triC[1] - triA[1] };
	CU_FLOAT32 v2[2] = { p_x - triA[0], p_y - triA[1] };

	CU_FLOAT32 d00 = cu_dot2D(v0, v0);
	CU_FLOAT32 d01 = cu_dot2D(v0, v1);
	CU_FLOAT32 d11 = cu_dot2D(v1, v1);
	CU_FLOAT32 d20 = cu_dot2D(v2, v0);
	CU_FLOAT32 d21 = cu_dot2D(v2, v1);

	CU_FLOAT32 denom = d00 * d11 - d01 * d01;

	if ( abs(denom) > cu_fMARGIN)
	{
		CU_FLOAT32 v = (d11 * d20 - d01 * d21) / denom;
		CU_FLOAT32 w = (d00 * d21 - d01 * d20) / denom;
		CU_FLOAT32 u = 1.0 - v - w;
		if(u >= -cu_fMARGIN && v >= -cu_fMARGIN && v <= 1. + cu_fMARGIN && u + v <= 1. + cu_fMARGIN)
		{
			return int(u * triA[2] + v * triB[2] + w * triC[2]);
		}
	}
	return -1;
}
__device__ __inline__ void cu_insertSlotPixel_SetBit(
	CU_SLOT_BUFFER_TYPE* memNPxl,
	CU_SLOT_BUFFER_TYPE* cu_pType,
	CU_SLOT_BUFFER_TYPE* cu_pZcrd,
	CU_SLOT_BUFFER_TYPE* cu_pZnrm,
	int slot_ID,
	int z,
	int nZ,
	CU_SLOT_BUFFER_TYPE type)
{
	const int lockBit = 0x40000000;
	const int countMask = 0x3fffffff;
	int oldCount;
	do {
		do { oldCount = atomicCAS((int*)memNPxl, 0, 0); } while (oldCount & lockBit);
	} while (atomicCAS((int*)memNPxl, oldCount, oldCount | lockBit) != oldCount);

	int count = oldCount & countMask;
	int pxlIdx = -1;
	for (int p = 0; p < count && p < CU_SLOT_CAPACITY_16; p++)
	{
		const CU_ULInt id = slot_ID * CU_SLOT_CAPACITY_16 + p;
		if (cu_pZcrd[id] == z && cu_pZnrm[id] == nZ)
		{
			pxlIdx = p;
			break;
		}
	}

	if (pxlIdx < 0 && count < CU_SLOT_CAPACITY_16)
	{
		pxlIdx = count;
		count++;
	}

	if (pxlIdx >= 0)
	{
		const CU_ULInt id = slot_ID * CU_SLOT_CAPACITY_16 + pxlIdx;
		cu_pType[id] |= type;
		cu_pZcrd[id] = z;
		cu_pZnrm[id] = nZ;
	}
	__threadfence();
	atomicExch((int*)memNPxl, count);
}

__device__ __inline__ CU_SLOT_BUFFER_TYPE cu_typeFromNz_CPUThreshold(int nZ)
{
	if (nZ > 0) return cu_typeAl;
	if (nZ < 0) return cu_typeBe;
	return 0;
}





#ifdef _CUDA_USE_ROTATE_AND_PIXELIZE_IN_ONE_STEP

	__global__ void cu_rotVoxel_16x16(
		int nFlatTri, int nYPR, int nVoxelX, int yprID_to_start,
		float* cu_m4x3,	float* cu_flattri0,	
		CU_SLOT_BUFFER_TYPE* cu_nPixel, 
		CU_SLOT_BUFFER_TYPE* cu_pType, 
		CU_SLOT_BUFFER_TYPE* cu_pZcrd, 
		CU_SLOT_BUFFER_TYPE* cu_pZnrm)
	{

		//Note: blockIdx = ( nFlatTri * _nYPRInBatch, 1)
		int triID	= blockIdx.x;//triangle ID within a same block(orientation).
		int wrkID	= blockIdx.y;//ypr data ID within a batch.

		const int thID	= threadIdx.y * blockDim.x + threadIdx.x;//this block is (16,16,1) size.
		int yprID = yprID_to_start  + wrkID;//Caution: m4x3_ID == 0 ~ nYPR-1.
		if (triID >= nFlatTri ||yprID >= nYPR) return;
	
		__shared__ float ftri[CU_FLATTRI_SIZE_16], m4x3[CU_MATRIX_SIZE_12];

		//per-BLOCK operation +++++++++++++++
		if (thID < CU_FLATTRI_SIZE_16)	{//copy tri coord data to shared memory.
			ftri[thID]	= cu_flattri0[triID * CU_FLATTRI_SIZE_16 + thID];
		}
		else if ((thID-CU_FLATTRI_SIZE_16) >=0 && (thID-CU_FLATTRI_SIZE_16) <  + CU_MATRIX_SIZE_12)	{//copy matrix data to shared memory
			m4x3[(thID - CU_FLATTRI_SIZE_16)]	= cu_m4x3[ yprID * CU_MATRIX_SIZE_12 + (thID - CU_FLATTRI_SIZE_16)];
		}
		__syncthreads();

		//matrix operation(YPR rotation + translation of AABB corner to origin)
		if(thID<=3) {
			cu_matrixOp(m4x3, ftri + thID * 3);
		}
		__syncthreads();

		if(thID<=1) {
			ftri[12 + thID] = min(min(ftri[0 + thID], ftri[3+ thID]), ftri[6 + thID]);//global_AABB_x0, _y0
		}
		__syncthreads();

		if(thID<=2) {
			ftri[9+thID] -= m4x3[4*thID+3];//eliminate translation from normal vector
		}
		__syncthreads();
		//+++++++++++++++++++++++++++++++++++


		//per-THREAD operation ------------------------------------
		//  (16,16)내에서의 로컬 픽셀좌표는 (threadIdx.x, threadIdx.y)
		//  global 좌표계는 (AABB_x0 + threadIdx.x, AABB_y0 + threadIdx.y)임.
		//AABB of current triangle
		const register int& global_AABB_x0 = ftri[12];
		const register int& global_AABB_y0 = ftri[13];
		register float vxl_global_cnt[2] = { //global 좌표계에서의 현재 복셀의 위치.
						(global_AABB_x0 + threadIdx.x) + cu_fMARGIN + cu_HALF_VOXEL_SIZE,
						(global_AABB_y0 + threadIdx.y) + cu_fMARGIN + cu_HALF_VOXEL_SIZE };
		if (vxl_global_cnt[0] >= nVoxelX || vxl_global_cnt[1] >= nVoxelX) return;

		float u,v,w;
		if( cu_getBaryCoord2D(vxl_global_cnt, ftri + 0, ftri + 3, ftri + 6, u, v, w))
		{
			register int  new_z  = int(u * ftri[2] + v * ftri[5] + w * ftri[8]);
			register int  new_nZ = int(ftri[11] * cu_fNORMALFACTOR);//use the same normal vector.

			//write back data to global memory
			const int nSlot			= nVoxelX * nVoxelX;
			const int nSlotData = nSlot * CU_SLOT_CAPACITY_16;
			const int slot_ID		= (global_AABB_y0 + threadIdx.y) * nVoxelX + (global_AABB_x0 + threadIdx.x);//target slot ID.

			//memory index. do not change this order.
			CU_SLOT_BUFFER_TYPE*	memNPxl	= cu_nPixel + wrkID * nSlot		+ slot_ID;
			CU_SLOT_BUFFER_TYPE		n_pixel		= *memNPxl;//current number of pxls in the slot
			if(n_pixel < CU_SLOT_CAPACITY_16-1)
			{ 
				const CU_ULInt	slotdata_ID		= slot_ID * CU_SLOT_CAPACITY_16 + n_pixel;//pxl ID inside the target slot
				CU_ULInt	uliSlotDataIdx			= wrkID * nSlotData + slotdata_ID;
				CU_SLOT_BUFFER_TYPE*	memType	= cu_pType + uliSlotDataIdx;
				CU_SLOT_BUFFER_TYPE*	memZcrd	= cu_pZcrd + uliSlotDataIdx;
				CU_SLOT_BUFFER_TYPE*	memZnrm	= cu_pZnrm + uliSlotDataIdx;

				cu_Add(	 memNPxl, 1);//increase target slot's current # of pxls
				cu_Exch( memZcrd, new_z);
				cu_Exch( memZnrm, new_nZ);
				#ifdef _CUDA_USE_SPLIT_AL_BE_IN_VOXELIZE_STEP
				cu_Exch( memType, cu_typeFromNz_CPUThreshold(new_nZ));// = splitAlBe()
				#endif
			}
		}
		//end of per-THREAD operation ------------------------------
	}
	#else

	#endif


//**********************************************************************************************
//
// concurrent stream version
// 
// 
//**********************************************************************************************

	__global__ void cu_rotVoxel_Streamed_16x16(
		int nVoxelX, int nYPR, int nFlatTri, 	int yprID, int triID_to_start,
		float* cu_m4x3,	float* cu_flattri0,
		int* cu_parentHit,
		CU_SLOT_BUFFER_TYPE* cu_nPixel,
		CU_SLOT_BUFFER_TYPE* cu_pType,
		CU_SLOT_BUFFER_TYPE* cu_pZcrd,
		CU_SLOT_BUFFER_TYPE* cu_pZnrm,
		bool bShellMesh,
		int shell_z_offset)
	{
#if 0
		//Note: blockDim  = ( nTriToWork, 1, 1) x (16,16,1)
		int wrkID = blockIdx.x;//[nTriToWork]
		int triID	= triID_to_start + wrkID;//triangle ID to work in this stream.
		const int thID	= threadIdx.y * blockDim.x + threadIdx.x;//this block is (16,16,1) size.
#else
	//Note: blockDim  = ( nWorksPerBlocks, 1, 1) x (maxD,	maxD, CU_TRI_PER_WORK)
		int triID0	= triID_to_start + blockIdx.x * blockDim.z;//global tri ID
		const int thID	= threadIdx.y * blockDim.x + threadIdx.x;
		const int thIDz = threadIdx.z;//local tri ID, [CU_TRI_PER_WORK]
#endif

		if (yprID >= nYPR) return;
		const bool triValid = (triID0 + thIDz < nFlatTri);

		__shared__ float ftri[CU_TRI_PER_WORK][CU_FLATTRI_SIZE_16], m4x3[CU_MATRIX_SIZE_12];

		//per-BLOCK operation +++++++++++++++
		if (thIDz==0 && thID <  CU_MATRIX_SIZE_12) {	//copy matrix data to shared memory.
				m4x3[thID]	= cu_m4x3[yprID * CU_MATRIX_SIZE_12 + thID];
		}
		__syncthreads();

		//grid-stride copy: CU_FLATTRI_SIZE_16(=20) can exceed the 16 (4x4) xy-threads
		for (int _i = thID; triValid && _i < CU_FLATTRI_SIZE_16; _i += blockDim.x * blockDim.y) {
			ftri[thIDz][_i]	= cu_flattri0[(triID0 + thIDz) * CU_FLATTRI_SIZE_16 + _i];
		}
		__syncthreads();

		const int parentID = triValid ? int(ftri[thIDz][18]) : -1;

		//rotate ONLY the 3 vertices. The 3 per-vertex normals (ftri[9..17]) stay raw; their
		//rotated z is interpolated per pixel below (matches the CPU vertex-normal path).
		if (triValid && thID <= 2) {			cu_matrixOp(m4x3, &ftri[thIDz][thID * 3]); ftri[thIDz][thID * 3 + 0] += cu_fMARGIN; ftri[thIDz][thID * 3 + 1] += cu_fMARGIN; ftri[thIDz][thID * 3 + 2] += cu_fMARGIN;		}
		__syncthreads();

		if (triValid && thID <= 1) {//global_AABB_x0, _y0 from the rotated vertices
			ftri[thIDz][18 + thID] = min(min(ftri[thIDz][0 + thID], ftri[thIDz][3 + thID]), ftri[thIDz][6 + thID]);
		}
		__syncthreads();

		const int global_AABB_x0 = triValid ? int(ftri[thIDz][18]) : 0;
		const int global_AABB_y0 = triValid ? int(ftri[thIDz][19]) : 0;
		float vxl_global_crd[2] = {
						(global_AABB_x0 + threadIdx.x) + cu_fMARGIN + cu_HALF_VOXEL_SIZE,
						(global_AABB_y0 + threadIdx.y) + cu_fMARGIN + cu_HALF_VOXEL_SIZE };
		const bool slotInBounds = triValid &&
			vxl_global_crd[0] >= 0 && vxl_global_crd[1] >= 0 &&
			vxl_global_crd[0] < nVoxelX && vxl_global_crd[1] < nVoxelX;
		const int slot_ID		= (global_AABB_y0 + threadIdx.y) * nVoxelX + (global_AABB_x0 + threadIdx.x);//target slot ID.
		float u = -1.f, v = -1.f, w = -1.f;//barycentric coord.
		bool baryHit = slotInBounds && cu_getBaryCoord2D(vxl_global_crd,
				&ftri[thIDz][0], &ftri[thIDz][3], &ftri[thIDz][6],
				u, v, w);//point-in-triangle test

		float _rnz0 = m4x3[8]*ftri[thIDz][9]  + m4x3[9]*ftri[thIDz][10] + m4x3[10]*ftri[thIDz][11];
		float _rnz1 = m4x3[8]*ftri[thIDz][12] + m4x3[9]*ftri[thIDz][13] + m4x3[10]*ftri[thIDz][14];
		float _rnz2 = m4x3[8]*ftri[thIDz][15] + m4x3[9]*ftri[thIDz][16] + m4x3[10]*ftri[thIDz][17];

		if (baryHit)
		{
			if (parentID >= 0) { atomicExch(cu_parentHit + parentID, 1); }
			CU_SLOT_BUFFER_TYPE*	memNPxl	= cu_nPixel + slot_ID;
			int new_z  = int(u * ftri[thIDz][2] + v * ftri[thIDz][5] + w * ftri[thIDz][8]);
			int new_nZ = int((u * _rnz0 + v * _rnz1 + w * _rnz2) * cu_fNORMALFACTOR);
			cu_insertSlotPixel_SetBit(
				memNPxl, cu_pType, cu_pZcrd, cu_pZnrm, slot_ID,
				new_z, new_nZ, cu_typeFromNz_CPUThreshold(new_nZ));
			if (bShellMesh && shell_z_offset > 0)//subsidiary opposite-normal pixel for thin/zero-thickness shell
			{
				cu_insertSlotPixel_SetBit(
					memNPxl, cu_pType, cu_pZcrd, cu_pZnrm, slot_ID,
					(new_nZ >= 0) ? new_z - shell_z_offset : new_z + shell_z_offset,
					new_nZ * -1,
					cu_typeFromNz_CPUThreshold(new_nZ * -1));
			}
		}

		//+++++++++++++++++++++++++++++++++++
	}

	__global__ void cu_rotVoxelOriginal_Streamed_16x16(
		int nVoxelX, int nYPR, int nTri, int yprID,
		float* cu_m4x3, int* cu_tri0, float* cu_vtx0, float* cu_vtxNrm0,
		int* cu_triHitCount,
		CU_SLOT_BUFFER_TYPE* cu_nPixel,
		CU_SLOT_BUFFER_TYPE* cu_pType,
		CU_SLOT_BUFFER_TYPE* cu_pZcrd,
		CU_SLOT_BUFFER_TYPE* cu_pZnrm,
		bool bShellMesh,
		int shell_z_offset)
	{
		int triID = blockIdx.x;
		if (triID >= nTri || yprID >= nYPR) return;
		const int thx = threadIdx.x;
		const int thy = threadIdx.y;
		const int thID = thy * blockDim.x + thx;

		__shared__ float tri[9];
		__shared__ float nrm[9];
		__shared__ float m4x3[CU_MATRIX_SIZE_12];

		if (thID < CU_MATRIX_SIZE_12) { m4x3[thID] = cu_m4x3[yprID * CU_MATRIX_SIZE_12 + thID]; }
		if (thID < 3)
		{
			int vid = cu_tri0[triID * 3 + thID];
			tri[thID * 3 + 0] = cu_vtx0[vid * 3 + 0];
			tri[thID * 3 + 1] = cu_vtx0[vid * 3 + 1];
			tri[thID * 3 + 2] = cu_vtx0[vid * 3 + 2];
			nrm[thID * 3 + 0] = cu_vtxNrm0[vid * 3 + 0];
			nrm[thID * 3 + 1] = cu_vtxNrm0[vid * 3 + 1];
			nrm[thID * 3 + 2] = cu_vtxNrm0[vid * 3 + 2];
		}
		__syncthreads();

		if (thID < 3)
		{
			cu_matrixOp(m4x3, &tri[thID * 3]);
			tri[thID * 3 + 0] += cu_fMARGIN;
			tri[thID * 3 + 1] += cu_fMARGIN;
			tri[thID * 3 + 2] += cu_fMARGIN;
		}
		__syncthreads();

		float minx = min(min(tri[0], tri[3]), tri[6]);
		float miny = min(min(tri[1], tri[4]), tri[7]);
		float maxx = max(max(tri[0], tri[3]), tri[6]);
		float maxy = max(max(tri[1], tri[4]), tri[7]);
		int x0 = int(minx);
		int y0 = int(miny);
		int x1 = int(maxx);
		int y1 = int(maxy);

		float rnz0 = m4x3[8] * nrm[0] + m4x3[9] * nrm[1] + m4x3[10] * nrm[2];
		float rnz1 = m4x3[8] * nrm[3] + m4x3[9] * nrm[4] + m4x3[10] * nrm[5];
		float rnz2 = m4x3[8] * nrm[6] + m4x3[9] * nrm[7] + m4x3[10] * nrm[8];

		int nHits = 0;
		for (int x = x0 + thx; x <= x1; x += blockDim.x)
		{
			for (int y = y0 + thy; y <= y1; y += blockDim.y)
			{
				float vxl_global_crd[2] = { x + cu_fMARGIN + cu_HALF_VOXEL_SIZE, y + cu_fMARGIN + cu_HALF_VOXEL_SIZE };
				if (vxl_global_crd[0] < 0 || vxl_global_crd[1] < 0 || vxl_global_crd[0] >= nVoxelX || vxl_global_crd[1] >= nVoxelX) continue;
				float u = -1.f, v = -1.f, w = -1.f;
				if (cu_getBaryCoord2D(vxl_global_crd, &tri[0], &tri[3], &tri[6], u, v, w))
				{
					int slot_ID = y * nVoxelX + x;
					int new_z = int(u * tri[2] + v * tri[5] + w * tri[8]);
					int new_nZ = int((u * rnz0 + v * rnz1 + w * rnz2) * cu_fNORMALFACTOR);
					CU_SLOT_BUFFER_TYPE* memNPxl = cu_nPixel + slot_ID;
					cu_insertSlotPixel_SetBit(memNPxl, cu_pType, cu_pZcrd, cu_pZnrm, slot_ID,
						new_z, new_nZ, cu_typeFromNz_CPUThreshold(new_nZ));
					if (bShellMesh && shell_z_offset > 0)
					{
						cu_insertSlotPixel_SetBit(memNPxl, cu_pType, cu_pZcrd, cu_pZnrm, slot_ID,
							(new_nZ >= 0) ? new_z - shell_z_offset : new_z + shell_z_offset,
							new_nZ * -1, cu_typeFromNz_CPUThreshold(new_nZ * -1));
					}
					nHits++;
				}
			}
		}

		__shared__ int hitCount;
		if (thID == 0) hitCount = 0;
		__syncthreads();
		if (nHits > 0) atomicAdd(&hitCount, nHits);
		__syncthreads();
		if (thID == 0 && cu_triHitCount != nullptr) cu_triHitCount[triID] = hitCount;
		if (hitCount == 0 && thID == 0)
		{
			float cx = (tri[0] + tri[3] + tri[6]) * 0.333333f;
			float cy = (tri[1] + tri[4] + tri[7]) * 0.333333f;
			float cz = (tri[2] + tri[5] + tri[8]) * 0.333333f;
			int ix = int(cx);
			int iy = int(cy);
			if (ix >= 0 && iy >= 0 && ix < nVoxelX && iy < nVoxelX)
			{
				int slot_ID = iy * nVoxelX + ix;
				int new_z = int(cz);
				int new_nZ = int(rnz0 * cu_fNORMALFACTOR);
				CU_SLOT_BUFFER_TYPE* memNPxl = cu_nPixel + slot_ID;
				cu_insertSlotPixel_SetBit(memNPxl, cu_pType, cu_pZcrd, cu_pZnrm, slot_ID,
					new_z, new_nZ, cu_typeFromNz_CPUThreshold(new_nZ));
				if (bShellMesh && shell_z_offset > 0)
				{
					cu_insertSlotPixel_SetBit(memNPxl, cu_pType, cu_pZcrd, cu_pZnrm, slot_ID,
						(new_nZ >= 0) ? new_z - shell_z_offset : new_z + shell_z_offset,
						new_nZ * -1, cu_typeFromNz_CPUThreshold(new_nZ * -1));
				}
			}
		}
	}
	__global__ void cu_rotVoxelFallback_Streamed_1d(
		int nVoxelX, int nYPR, int nTri, int yprID,
		float* cu_m4x3, float* cu_parentFallbackTri,
		int* cu_parentHit,
		CU_SLOT_BUFFER_TYPE* cu_nPixel,
		CU_SLOT_BUFFER_TYPE* cu_pType,
		CU_SLOT_BUFFER_TYPE* cu_pZcrd,
		CU_SLOT_BUFFER_TYPE* cu_pZnrm,
		bool bShellMesh,
		int shell_z_offset)
	{
		int parentID = blockIdx.x * blockDim.x + threadIdx.x;
		if (parentID >= nTri || yprID >= nYPR) return;
		if (atomicCAS(cu_parentHit + parentID, 0, 1) != 0) return;

		float m4x3[CU_MATRIX_SIZE_12];
		for (int i = 0; i < CU_MATRIX_SIZE_12; i++) {
			m4x3[i] = cu_m4x3[yprID * CU_MATRIX_SIZE_12 + i];
		}

		float* pf = cu_parentFallbackTri + parentID * 6;
		float center[3] = { pf[0], pf[1], pf[2] };
		cu_matrixOp(m4x3, center);
		center[0] += cu_fMARGIN; center[1] += cu_fMARGIN; center[2] += cu_fMARGIN;

		int cx = int(center[0]);
		int cy = int(center[1]);
		if (cx < 0 || cy < 0 || cx >= nVoxelX || cy >= nVoxelX) return;

		float rnz = m4x3[8] * pf[3] + m4x3[9] * pf[4] + m4x3[10] * pf[5];
		int new_z = int(center[2]);
		int new_nZ = int(rnz * cu_fNORMALFACTOR);
		int slot_ID = cy * nVoxelX + cx;
		CU_SLOT_BUFFER_TYPE* memNPxl = cu_nPixel + slot_ID;
		cu_insertSlotPixel_SetBit(
			memNPxl, cu_pType, cu_pZcrd, cu_pZnrm, slot_ID,
			new_z, new_nZ, cu_typeFromNz_CPUThreshold(new_nZ));
		if (bShellMesh && shell_z_offset > 0)
		{
			cu_insertSlotPixel_SetBit(
				memNPxl, cu_pType, cu_pZcrd, cu_pZnrm, slot_ID,
				(new_nZ >= 0) ? new_z - shell_z_offset : new_z + shell_z_offset,
				new_nZ * -1,
				cu_typeFromNz_CPUThreshold(new_nZ * -1));
		}
	}