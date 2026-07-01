#pragma once
#include "CUDA_types.cuh" 

template<typename T> __global__ void cu_slotPairing(
	CU_SLOT_BUFFER_TYPE* cu_nPixel , 
	CU_SLOT_BUFFER_TYPE* cu_pType , 
	CU_SLOT_BUFFER_TYPE* cu_pZcrd , 
	CU_SLOT_BUFFER_TYPE* cu_pZnrm , 
	CU_SLOT_BUFFER_TYPE*  cu_Vo, 
	CU_SLOT_BUFFER_TYPE*  cu_Vss, 
	ShouldSwap<T> shouldSwap , int nSlot , int sin_theta_c_x1000);

template<typename T> __global__ void cu_slotPairing_Streamed(
	int nSlot , ShouldSwap<T> shouldSwap , int sin_theta_c_x1000,
	bool bWriteBackPxlsForRendering, bool bUseExplicitSS,
	CU_SLOT_BUFFER_TYPE* cu_nPixel , 
	CU_SLOT_BUFFER_TYPE*  cu_Vo, 
	CU_SLOT_BUFFER_TYPE*  cu_Vss, 
	CU_SLOT_BUFFER_TYPE* cu_pType , 
	CU_SLOT_BUFFER_TYPE* cu_pZcrd , 
	CU_SLOT_BUFFER_TYPE* cu_pZnrm);
