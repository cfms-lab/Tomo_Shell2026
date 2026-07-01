#include "step3_generateBed.cuh"
#include "atomicWrite.cuh"

using namespace Tomo;

__device__ __inline__ float cu_dist2D(int x0 , int y0 , int x1 , int y1)
{
	return sqrt( ((float(x0) - x1)*(float(x0) - x1) + (float(y0) - y1)*(float(y0) - y1)));
}
__device__ __inline__ CU_SLOT_BUFFER_TYPE cu_bottomSolidMask(
	CU_SLOT_BUFFER_TYPE S_L,
	CU_SLOT_BUFFER_TYPE* memType,
	CU_SLOT_BUFFER_TYPE* memZcrd)
{
	CU_SLOT_BUFFER_TYPE mask = 0;
	if (S_L > CU_SLOT_CAPACITY_16) S_L = CU_SLOT_CAPACITY_16;
	for (int p = 0; p < S_L; p++)
	{
		CU_SLOT_BUFFER_TYPE p_type = memType[p];
		if (memZcrd[p] == 0 &&
			((p_type & cu_typeAl) || (p_type & cu_typeBe) || (p_type & cu_typeSSA) || (p_type & cu_typeSS)))
		{
			mask |= p_type;
		}
	}
	return mask;
}


__global__ void cu_genBed(
	int nVoxelX, int nSlot, //constants
	enumBedType bedtype, float outerRadius, float innerRadius, float height, //bed parameter
	CU_SLOT_BUFFER_TYPE* cu_nPixl, //slot data
	CU_SLOT_BUFFER_TYPE* cu_pType, 
	CU_SLOT_BUFFER_TYPE* cu_pZcrd, 
	CU_SLOT_BUFFER_TYPE* cu_pZnrm, 
	CU_SLOT_BUFFER_TYPE* cu_Vo, 
	CU_SLOT_BUFFER_TYPE* cu_Vss)
{
	//Find nearby nonzero pxl to make bed structure. each thread takes care of 1 slot 
	const int slotID		= blockIdx.x * blockDim.x + threadIdx.x;
	if(slotID >= nSlot) return;
	
	const CU_ULInt nSlotData	= nSlot * CU_SLOT_CAPACITY_16;

	CU_ULInt uliSlotIdx				= slotID;
	CU_ULInt uliSlotDataIdx		= slotID * CU_SLOT_CAPACITY_16;

	CU_SLOT_BUFFER_TYPE* memNPxl	= cu_nPixl	+ uliSlotIdx;
	CU_SLOT_BUFFER_TYPE* memVo		= cu_Vo			+ uliSlotIdx;
	CU_SLOT_BUFFER_TYPE* memVss		= cu_Vss		+ uliSlotIdx;
	CU_SLOT_BUFFER_TYPE* memType	= cu_pType	+ uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZcrd	= cu_pZcrd	+ uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZnrm	= cu_pZnrm	+ uliSlotDataIdx;
	int S_L = *memNPxl;
	if (S_L > CU_SLOT_CAPACITY_16) S_L = CU_SLOT_CAPACITY_16;
	
	CU_SLOT_BUFFER_TYPE bottomMask = cu_bottomSolidMask(S_L, memType, memZcrd);
	if(bottomMask != 0)
	{
		if( bedtype == enumBedType::ebtRaft && ((bottomMask & cu_typeBe) || (bottomMask & cu_typeSSA)) )
		{
			// raft can be generated below beta / SSA bottom pixels.
		}
		else
		{
			return;//pass. this slot already has a bottom solid/support pixel.
		}
	}


	int Xcrd = slotID % nVoxelX;
	int Ycrd = slotID / nVoxelX;
	int I0 = max( Xcrd - int(outerRadius), 0);
	int I1 = min( Xcrd + int(outerRadius), nVoxelX);
	int J0 = max( Ycrd - int(outerRadius), 0);
	int J1 = min( Ycrd + int(outerRadius), nVoxelX);

	//compare distance to nearby target non-zero-type pxl
	float min_dist = 1e5;
	for( int i = I0 ; i < I1 ; i++)	
	{
		for( int j = J0 ; j < J1 ; j++)	
		{
			int slotID = j * nVoxelX + i;
			SLOT_BUFFER_TYPE S_L_tgt = *(cu_nPixl + slotID);
			if (S_L_tgt > CU_SLOT_CAPACITY_16) S_L_tgt = CU_SLOT_CAPACITY_16;
			if(S_L_tgt > 0)
			{
				CU_ULInt uliSlotDataIdx_tgt		= slotID * CU_SLOT_CAPACITY_16;
				CU_SLOT_BUFFER_TYPE* memType_tgt	= cu_pType	+ uliSlotDataIdx_tgt;
				CU_SLOT_BUFFER_TYPE* memZcrd_tgt	= cu_pZcrd	+ uliSlotDataIdx_tgt;
				CU_SLOT_BUFFER_TYPE bottomMask_tgt = cu_bottomSolidMask(S_L_tgt, memType_tgt, memZcrd_tgt);
				float dist = cu_dist2D( Xcrd, Ycrd, i, j);
				if( bottomMask_tgt != 0 )
				{
					min_dist = min( min_dist, dist);  
				}
			}//end of if(S_L_tgt > 0)
		}//end of for(j..)
	}//end of for(i..)

	if(min_dist > outerRadius) return;

	bool bBedPxl = false;
	if(     bedtype == enumBedType::ebtSkirt && min_dist > innerRadius) bBedPxl = true;
	else if(bedtype == enumBedType::ebtBrim)   bBedPxl = true;  
	else if(bedtype == enumBedType::ebtRaft)   bBedPxl = true;  

	if(bBedPxl)	
	{
		// Keep the source slot buffers immutable while this kernel scans neighboring slots.
		// Updating cu_nPixl/cu_pType here makes other slots observe schedule-dependent
		// "last pixels". The orientation score only needs the bed contribution in Vss.
		cu_Add(		memVss, 1);
	}

}
