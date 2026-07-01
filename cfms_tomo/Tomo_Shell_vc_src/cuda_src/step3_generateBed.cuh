#pragma once
#include "cuda_runtime.h"
#include "device_launch_parameters.h"
#include <cuda.h>
#include <cuda_runtime_api.h>

#include "CUDA_types.cuh" 

using namespace Tomo;

__global__ void cu_genBed(
	int nVoxelX, int nSlot ,
	enumBedType bedtype, float outerRadius, float innerRadius, float height, //bed parameter
	CU_SLOT_BUFFER_TYPE* cu_nPixl , 
	CU_SLOT_BUFFER_TYPE* cu_pType , 
	CU_SLOT_BUFFER_TYPE* cu_pZcrd , 
	CU_SLOT_BUFFER_TYPE* cu_pZnrm , 
	CU_SLOT_BUFFER_TYPE*  cu_Vo, 
	CU_SLOT_BUFFER_TYPE*  cu_Vss);

