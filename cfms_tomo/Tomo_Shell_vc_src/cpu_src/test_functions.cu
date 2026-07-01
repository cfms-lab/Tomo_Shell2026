#pragma once

#include "cuda_runtime.h"
#include "cuda_runtime_api.h"//__syncthreads()
#include "device_launch_parameters.h"

#include "test_functions.cuh"
#include "TomoNV_GPU.cuh"
#include "reduced_sum.cuh"

#include <iostream>
#include <stdio.h>

extern FlatTriInfo* flatTri0;
extern float* dev_flatTri0;
extern int* nPixel, * dev_nPixel;
extern int* pType, * dev_pType;
extern int* pZcrd, * dev_pZcrd;
extern int* pZnrm, * dev_pZnrm;
extern int* Vo, * dev_Vo;
extern int* Vss, * dev_Vss;
extern float * m4x4, * dev_m4x4;
extern cudaEvent_t start, stop;


void  PrintSlotInfo(int X, int Y)
{
	cudaMemcpy(nPixel, dev_nPixel, nSlot * sizeof(int), cudaMemcpyDeviceToHost);  cudaCheckError();
	cudaMemcpy(pType, dev_pType, nSlotTotalData * sizeof(int), cudaMemcpyDeviceToHost);  cudaCheckError();
	cudaMemcpy(pZcrd, dev_pZcrd, nSlotTotalData * sizeof(int), cudaMemcpyDeviceToHost);  cudaCheckError();
	cudaMemcpy(pZnrm, dev_pZnrm, nSlotTotalData * sizeof(int), cudaMemcpyDeviceToHost);  cudaCheckError();

	int s = Y * nVoxelX + X;//slot ID
	int n_pxl = nPixel[s];
	if (n_pxl > 0)
	{
		printf("X=%d,Y=%d,nPxl=%d:", X, Y, n_pxl);
		for (int p = 0; p < n_pxl; p++)
		{
			printf("(% 2d,% 2d,% 3d), ", pType[p], pZcrd[p], pZnrm[p]);
		}
		printf("\n");
	}
}

void _InputTestData(void)
{
	// _USE_PINNED_MEMORY
	cudaMallocHost((void**)&flatTri0, nTri * sizeof(FlatTriInfo) * sizeof(int));

	for (int t = 0; t < nTri; t += 2)
	{
		float shiftX = 0;
		float shiftY = 0;

		if (BLOCK_SIZE + shiftX > nVoxelX)
		{
			shiftX = 0; shiftY += BLOCK_SIZE;
		}
		if (BLOCK_SIZE + shiftY > nVoxelX)
		{
			shiftX = 0; shiftY = 0;
		}

		//LefTop 절대좌표.
		//tri15f[t].x_min = float(BLOCK_SIZE * t);
		//tri15f[t].y_min = float(BLOCK_SIZE * t);
		flatTri0[t].x_min = 0;
		flatTri0[t].y_min = 0;

		//LefTop기준 vertex 상대좌표.
		flatTri0[t].crd0[0] = 0 + shiftX;
		flatTri0[t].crd0[1] = 0 + shiftY;
		flatTri0[t].crd0[2] = t * 2. + 4.;
		flatTri0[t].nrmZ0 = 1.;//alpha

		flatTri0[t].crd1[0] = float(BLOCK_SIZE - 1) + shiftX;
		flatTri0[t].crd1[1] = 0 + shiftY;
		flatTri0[t].crd1[2] = t * 2. + 4.;
		flatTri0[t].nrmZ1 = 1.;//alpha

		flatTri0[t].crd2[0] = 0 + shiftX;
		flatTri0[t].crd2[1] = float(BLOCK_SIZE - 1) + shiftX;
		flatTri0[t].crd2[2] = t * 2. + 4.;
		flatTri0[t].nrmZ2 = 1.;//alpha
	}

	for (int t = 1; t < nTri; t += 2)
	{
		float shiftX = 0;
		float shiftY = 0;

		if (BLOCK_SIZE + shiftX > nVoxelX)
		{
			shiftX = 0; shiftY += BLOCK_SIZE;
		}
		if (BLOCK_SIZE + shiftY > nVoxelX)
		{
			shiftX = 0; shiftY = 0;
		}

		//LefTop 절대좌표.
		flatTri0[t].x_min = 0;//float(BLOCK_SIZE * t);
		flatTri0[t].y_min = 0.;

		//LefTop기준 vertex 상대좌표.
		flatTri0[t].crd0[0] = 0 + shiftX;
		flatTri0[t].crd0[1] = float(BLOCK_SIZE - 1) + shiftY;
		flatTri0[t].crd0[2] = t * 2. + 1.;
		flatTri0[t].nrmZ0 = -1.;//beta

		flatTri0[t].crd1[0] = float(BLOCK_SIZE - 1) + shiftX;
		flatTri0[t].crd1[1] = float(BLOCK_SIZE - 1) + shiftY;
		flatTri0[t].crd1[2] = t * 2. + 1.;
		flatTri0[t].nrmZ1 = -1.;//beta

		flatTri0[t].crd2[0] = 0 + shiftX;
		flatTri0[t].crd2[1] = 0 + shiftY;
		flatTri0[t].crd2[2] = t * 2. + 1.;
		flatTri0[t].nrmZ2 = -1.;//beta
	}

}


void Voxelize_Test(void)
{
	//Voxelize();
	{
	dim3 dimGrid(nTri);    dim3 dimBlock(BLOCK_SIZE, BLOCK_SIZE);

	startTimer();
	triVoxel_cu << < dimGrid, dimBlock >> > (dev_flatTri0, dev_nPixel, dev_pType, dev_pZcrd, dev_pZnrm, dev_m4x4);
	//triVoxel_cu <<< 2, dimBlock >>> (dev_tri15f, dev_nPixel, dev_pType, dev_pZcrd, dev_pZnrm);
	cudaDeviceSynchronize();
	endTimer();
	}

	cudaMemcpy(nPixel,dev_nPixel,nSlot          * sizeof(int), cudaMemcpyDeviceToHost);  cudaCheckError();
	cudaMemcpy(pType, dev_pType, nSlotTotalData * sizeof(int), cudaMemcpyDeviceToHost);  cudaCheckError();
	cudaMemcpy(pZcrd, dev_pZcrd, nSlotTotalData * sizeof(int), cudaMemcpyDeviceToHost);  cudaCheckError();
	cudaMemcpy(pZnrm, dev_pZnrm, nSlotTotalData * sizeof(int), cudaMemcpyDeviceToHost);  cudaCheckError();

	//if (nTri < 100)
	{
		for (int j = 0; j < nVoxelY; j++)
		{
			for (int i = 0; i < nVoxelX; i++)
			{
				int data1 = nPixel[j * nVoxelX + i];
				printf("% 2d", data1);
			}
			printf("\n");
		}
	}

}



void  SlotPairing_Test(void)
{

#if 1
	{//bubble sorting test

		//int test_Zcrd[] = { 
		//  3, 1, 4, 1, 5, 9, 2, 0, 
		//  0, 0, 0, 0, 0, 0, 0, 0,
		//  0, 0, 0, 0, 0, 0, 0, 0,
		//  0, 0, 0, 0, 0, 0, 0, 0,

		//  3, 1, 4, 1, 5, 9, 2, 0,
		//  0, 0, 0, 0, 0, 0, 0, 0,
		//  0, 0, 0, 0, 0, 0, 0, 0,
		//  0, 0, 0, 0, 0, 0, 0, 0
		//};

		int test_Type[] = {// slot-pairing test.
			0, 0, 0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 0, 0, 0, 0,    0, 0, 0, 0, 0, 0, 0, 0 };
		int test_Zcrd[] = {
			3, 1, 4, 2, 5, 9, 0, 0,   0, 0, 0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 0, 0, 0, 0,    0, 0, 0, 0, 0, 0, 0, 0 };
		int test_Znrm[] = {
		 -999,-999,999,999,-999,999, 2, 0,   0, 0, 0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 0, 0, 0, 0,    0, 0, 0, 0, 0, 0, 0, 0 };
		int test_Vo[nSlot] = {};
		int test_Vss[nSlot] = {};
		int test_nPixel[nSlot] = {}; test_nPixel[0] = 6;

		const unsigned int nBlock = sizeof(test_Zcrd) / sizeof(int) / nSlotCapacity;

		cudaMemcpy(dev_Vo, test_Vo, nSlot * sizeof(int), cudaMemcpyHostToDevice);                  cudaCheckError();
		cudaMemcpy(dev_Vss, test_Vss, nSlot * sizeof(int), cudaMemcpyHostToDevice);                  cudaCheckError();

		cudaMemcpy(dev_pType, test_Type, nBlock * nSlotCapacity * sizeof(int), cudaMemcpyHostToDevice); cudaCheckError();
		cudaMemcpy(dev_pZcrd, test_Zcrd, nBlock * nSlotCapacity * sizeof(int), cudaMemcpyHostToDevice); cudaCheckError();
		cudaMemcpy(dev_pZnrm, test_Znrm, nBlock * nSlotCapacity * sizeof(int), cudaMemcpyHostToDevice); cudaCheckError();

		if (bVerbose)
		{
			printf("Raw data-----\n");
			for (auto p : test_Type) { printf("%4d ", p); } printf("\n");
			for (auto p : test_Zcrd) { printf("%4d ", p); } printf("\n");
			for (auto p : test_Znrm) { printf("%4d ", p); } printf("\n\n");
		}

		const dim3 grdDim(nBlock);
		const dim3 blkDim(nSlotCapacity);

		printf("Slot-pairing - 1) Bubble-sorting-----");
		startTimer();
		ShouldSwap<int> shouldSwap;
		cu_sortSlotByZ<int> << < grdDim, blkDim >> > (dev_pType, dev_pZcrd, dev_pZnrm, nSlotCapacity, shouldSwap);
		cudaDeviceSynchronize();
		endTimer();

		cudaMemcpy(test_Type, dev_pType, nBlock * nSlotCapacity * sizeof(int), cudaMemcpyDeviceToHost); cudaCheckError();
		cudaMemcpy(test_Zcrd, dev_pZcrd, nBlock * nSlotCapacity * sizeof(int), cudaMemcpyDeviceToHost); cudaCheckError();
		cudaMemcpy(test_Znrm, dev_pZnrm, nBlock * nSlotCapacity * sizeof(int), cudaMemcpyDeviceToHost); cudaCheckError();

		if (bVerbose)
		{
			for (auto p : test_Type) { printf("%4d ", p); } printf("\n");
			for (auto p : test_Zcrd) { printf("%4d ", p); } printf("\n");
			for (auto p : test_Znrm) { printf("%4d ", p); } printf("\n\n");
		}

		printf("Slot-pairing - 2) Al-Be split-----");
		startTimer();
		cu_splitAlBe<int> << < grdDim, blkDim >> > (dev_pType, dev_pZcrd, dev_pZnrm);
		cudaDeviceSynchronize();
		endTimer();

		cudaMemcpy(test_Type, dev_pType, nBlock * nSlotCapacity * sizeof(int), cudaMemcpyDeviceToHost);  cudaCheckError();

		if (bVerbose)
		{
			for (auto p : test_Type) { printf("%4d ", p); } printf("\n");
			for (auto p : test_Zcrd) { printf("%4d ", p); } printf("\n");
			for (auto p : test_Znrm) { printf("%4d ", p); } printf("\n\n");
		}

		//add noise
		test_Type[1] = 1; test_Znrm[1] = 10;
		cudaMemcpy(dev_pType, test_Type, nBlock * nSlotCapacity * sizeof(int), cudaMemcpyHostToDevice);  cudaCheckError();
		cudaMemcpy(dev_pZnrm, test_Znrm, nBlock * nSlotCapacity * sizeof(int), cudaMemcpyHostToDevice);  cudaCheckError();
		printf("(add noise)-----\n");
		if (bVerbose)
		{
			for (auto p : test_Type) { printf("%4d ", p); } printf("\n");
			for (auto p : test_Zcrd) { printf("%4d ", p); } printf("\n");
			for (auto p : test_Znrm) { printf("%4d ", p); } printf("\n\n");
		}


		printf("Slot-pairing - 3) _match Al Be Pair-----");
		startTimer();
		cu_matchAlBePair<int> << < grdDim, blkDim >> > (dev_pType, dev_pZcrd, dev_pZnrm);
		cudaDeviceSynchronize();
		endTimer();

		cudaMemcpy(test_Type, dev_pType, nBlock * nSlotCapacity * sizeof(int), cudaMemcpyDeviceToHost);  cudaCheckError();

		if (bVerbose)
		{
			for (auto p : test_Type) { printf("%4d ", p); } printf("\n");
			for (auto p : test_Zcrd) { printf("%4d ", p); } printf("\n");
			for (auto p : test_Znrm) { printf("%4d ", p); } printf("\n\n");
		}


		printf("Slot-pairing - 4) create shadow-----");
		startTimer();
		cu_createShadow<int> << < grdDim, blkDim >> > (dev_pType, dev_pZcrd, dev_pZnrm, threshold_c_int, dev_nPixel);
		cudaDeviceSynchronize();
		endTimer();

		cudaMemcpy(test_Type, dev_pType, nBlock * nSlotCapacity * sizeof(int), cudaMemcpyDeviceToHost);  cudaCheckError();

		if (bVerbose)
		{
			for (auto p : test_Type) { printf("%4d ", p); } printf("\n");
			for (auto p : test_Zcrd) { printf("%4d ", p); } printf("\n");
			for (auto p : test_Znrm) { printf("%4d ", p); } printf("\n\n");
		}

		printf("Slot-pairing - 5) calculate nPxl, Vo, Vss-----");
		startTimer();
		cu_calculate<int> << < grdDim, 1 >> > (dev_pType, dev_pZcrd, dev_pZnrm, dev_Vo, dev_Vss);//reduction이므로 thread 갯수는 1개.
		cudaDeviceSynchronize();
		endTimer();

		cudaMemcpy(test_nPixel, dev_nPixel, nSlot * sizeof(int), cudaMemcpyDeviceToHost); cudaCheckError();
		cudaMemcpy(test_Vo, dev_Vo, nSlot * sizeof(int), cudaMemcpyDeviceToHost); cudaCheckError();
		cudaMemcpy(test_Vss, dev_Vss, nSlot * sizeof(int), cudaMemcpyDeviceToHost); cudaCheckError();

		if (bVerbose)
		{
			//for (auto p : test_nPixel) { printf("%4d ", p); } printf("\n");
			//for (auto p : test_Vo) { printf("%4d ", p); } printf("\n");
			//for (auto p : test_Vss) { printf("%4d ", p); } printf("\n\n");

			int Vo = reducedSum(nSlot, dev_Vo);
			int Vss = reducedSum(nSlot, dev_Vss);
			printf("Total Vo=%d, Vss=%d \n", Vo, Vss);
		}


	}
#endif

}


void  ReducedSumTest(void)
{
	const int N = 256 * 256;
	const int REPEAT = 1;

	int* src = (int*)malloc(N * sizeof(int));
	int checksum = 0;
	for (int i = 0; i < N; i++)
	{
		src[i] = 1;
		checksum += src[i];
	}

	printf("sum=%d", reducedSum(N, src));

}


void  ReducedMinTest(void)
{
	const int N = 256 * 256;
	const int REPEAT = 1;

	int* src = (int*)malloc(N * sizeof(int));
	int checksum = 0;
	for (int i = 0; i < N; i++)
	{
		src[i] = i - N / 2;
		checksum += src[i];
	}

	printf("min=%d", reducedMin(N, src));

}



template<typename T> __global__ void cu_sortSlotByZ(CU_SLOT_BUFFER_TYPE* dev_nPixel, CU_SLOT_BUFFER_TYPE* dev_pType, CU_SLOT_BUFFER_TYPE* dev_pZcrd, CU_SLOT_BUFFER_TYPE* dev_pZnrm, \
ShouldSwap<T> shouldSwap, int nSlot);
__global__ void cu_splitAlBe(CU_SLOT_BUFFER_TYPE* dev_nPixel, CU_SLOT_BUFFER_TYPE* dev_pType, CU_SLOT_BUFFER_TYPE* dev_pZcrd, CU_SLOT_BUFFER_TYPE* dev_pZnrm, 
	int nSlot, int nBlockDimX_64); 
__global__ void cu_matchAlBePair(CU_SLOT_BUFFER_TYPE* dev_nPixel, CU_SLOT_BUFFER_TYPE* dev_pType, CU_SLOT_BUFFER_TYPE* dev_pZcrd, CU_SLOT_BUFFER_TYPE* dev_pZnrm, 
	int nSlot, int nBlockDimX_64); 
__global__ void cu_createShadow(CU_SLOT_BUFFER_TYPE* dev_nPixel, CU_SLOT_BUFFER_TYPE* dev_pType, CU_SLOT_BUFFER_TYPE* dev_pZcrd, CU_SLOT_BUFFER_TYPE* dev_pZnrm, 
	int nSlot, int sin_theta_c_x1000, int nBlockDimX_64);//finding SSB, SSA
__global__ void cu_calculate(CU_SLOT_BUFFER_TYPE* dev_nPixel, CU_SLOT_BUFFER_TYPE* dev_pType, CU_SLOT_BUFFER_TYPE* dev_pZcrd, CU_SLOT_BUFFER_TYPE* dev_pZnrm, \
	CU_SLOT_BUFFER_TYPE* dev_Vo, CU_SLOT_BUFFER_TYPE* dev_Vss, int nSlot, int nBlockDimX_64);//ToDo: remove this function.


template<typename T> __global__ void cu_sortSlotByZ(CU_SLOT_BUFFER_TYPE* cu_nPixel, 
	CU_SLOT_BUFFER_TYPE* cu_pType, CU_SLOT_BUFFER_TYPE* cu_pZcrd, CU_SLOT_BUFFER_TYPE* cu_pZnrm,
	 ShouldSwap<T> shouldSwap/*이거 빼라 */, int nSlot) /*template도 필요없잖아. 빼라 */
{
	//original source: https://github.com/master-hpc/mp-generic-bubble-sort/blob/master/generic-bubble-sort.cu

	const int slotID				= blockIdx.x;//YPR ID 
	const int wrkID					= blockIdx.y;//YPR ID 
	const unsigned int thID = threadIdx.x;//[SLOT_CAPACITY_32]
	const CU_ULInt nSlotData = nSlot * CU_SLOT_CAPACITY_16;
	CU_ULInt uliSlotDataIdx = wrkID * nSlotData + slotID * CU_SLOT_CAPACITY_16;

	CU_SLOT_BUFFER_TYPE* memNPxl = cu_nPixel+ (CU_ULInt)(wrkID * nSlot			+ slotID);
	CU_SLOT_BUFFER_TYPE* memType = cu_pType + uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZcrd = cu_pZcrd + uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZnrm = cu_pZnrm + uliSlotDataIdx;

#if 1
	CU_SLOT_BUFFER_TYPE S_L = *memNPxl;//Slot Length. (number of all the pixels in slot, including noises)
	const int n_pxl_to_sort = min( S_L + S_L % 2, CU_SLOT_CAPACITY_16);//make S_L an even number.
	if (n_pxl_to_sort <=1 || thID >= n_pxl_to_sort) return;
	for (CU_SLOT_BUFFER_TYPE p = 0; p < n_pxl_to_sort; p++)
#else
	for (CU_SLOT_BUFFER_TYPE p = 0; p < SLOT_CAPACITY_32; p++)
#endif
	{
		unsigned int offset = p % 2;
		unsigned int iLeft = 2 * thID + offset;
		unsigned int iRght = iLeft + 1;

		//if (indiceDroite < SLOT_CAPACITY_32)
		if (iRght < n_pxl_to_sort)
		{
			if (shouldSwap(memZcrd[iLeft], memZcrd[iRght]))
			{
				swap<T>(&memZcrd[iLeft], &memZcrd[iRght]);
				swap<T>(&memZnrm[iLeft], &memZnrm[iRght]);
				swap<T>(&memType[iLeft], &memType[iRght]);
			}
		}
		__syncthreads();
	}
}

__global__ void cu_splitAlBe(CU_SLOT_BUFFER_TYPE* cu_nPixel, CU_SLOT_BUFFER_TYPE* cu_pType,
	CU_SLOT_BUFFER_TYPE* cu_pZcrd, CU_SLOT_BUFFER_TYPE* cu_pZnrm, int nSlot, int nBlockDimX_64)
{
	const int wrkID			= blockIdx.y;
	const CU_ULInt nSlotData = nSlot * CU_SLOT_CAPACITY_16;
	const int thID = blockIdx.x * blockDim.x + threadIdx.x;

	CU_ULInt uliSlotIdx			= wrkID * nSlot + thID;
	CU_ULInt uliSlotDataIdx	= wrkID * nSlotData + thID * CU_SLOT_CAPACITY_16;

	CU_SLOT_BUFFER_TYPE* memNPxl = cu_nPixel + uliSlotIdx;
	CU_SLOT_BUFFER_TYPE* memType = cu_pType + uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZcrd = cu_pZcrd + uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZnrm = cu_pZnrm + uliSlotDataIdx;

	CU_SLOT_BUFFER_TYPE S_L = *memNPxl;//Slot Length. (number of all the pixels in slot, including noises)
	for (int p = 0; p < S_L; p++)
	{//Omit side-face points(nZ==0).
		if (memZnrm[p] > 10)				{			cu_Or( memType + p, typeAl);		}
		else if (memZnrm[p] < -10)	{			cu_Or( memType + p, typeBe);		}
	}
}

__global__ void cu_matchAlBePair(CU_SLOT_BUFFER_TYPE*  cu_nPixel, CU_SLOT_BUFFER_TYPE*  cu_pType,
	CU_SLOT_BUFFER_TYPE*  cu_pZcrd, CU_SLOT_BUFFER_TYPE*  cu_pZnrm, int nSlot, int nBlockDimX_64)
{
	int wrkID	= blockIdx.y;
	const CU_ULInt nSlotData = nSlot * CU_SLOT_CAPACITY_16;
	const  int thID = blockIdx.x * blockDim.x + threadIdx.x;//block size is (1024,1)
	CU_ULInt uliSlotIdx			= wrkID * nSlot + thID;
	CU_ULInt uliSlotDataIdx	= wrkID * nSlotData + thID * CU_SLOT_CAPACITY_16;

	CU_SLOT_BUFFER_TYPE* memNPxl = cu_nPixel + uliSlotIdx;
	CU_SLOT_BUFFER_TYPE* memType = cu_pType + uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZcrd = cu_pZcrd + uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZnrm = cu_pZnrm + uliSlotDataIdx;

	CU_SLOT_BUFFER_TYPE S_L = *memNPxl;//Slot Length. (number of all the pixels in slot, including noises)
	if (S_L < 2) return;

	bool _b_P_started = false;//check pair is started.
	for (int p = 0; p < S_L; p++)
	{
		CU_SLOT_BUFFER_TYPE p_type = memType[p];
		CU_SLOT_BUFFER_TYPE p_z = memZcrd[p];

		if (!_b_P_started && p_type == cu_typeAl)
		{
			_b_P_started = true;//true pixel. leave it.
		}
		else if (_b_P_started && p_type == cu_typeBe)
		{
			_b_P_started = false;//true pixel. leave it.
		}
		else if ((p_type == cu_typeAl || p_type == cu_typeBe))//&& p_z > 0)
		{
			cu_Exch( memType + p, 0);//noise pixel. Hide it.//ToDo: slotPair()는 1:1로 쓰기하는데 Atomic필요없지 않나. 
		}
	}

}

__global__ void cu_createShadow(CU_SLOT_BUFFER_TYPE*  cu_nPixel, CU_SLOT_BUFFER_TYPE*  cu_pType, 
	CU_SLOT_BUFFER_TYPE*  cu_pZcrd, CU_SLOT_BUFFER_TYPE*  cu_pZnrm, 
	int nSlot, int sin_theta_c_x1000, int nBlockDimX_64)//ToDo: Pairing 함수 병합하면 빨라지려나?
{
	const int wrkID			= blockIdx.y;
	const CU_ULInt  nSlotData = nSlot * CU_SLOT_CAPACITY_16;
	const int thID = blockIdx.x * blockDim.x + threadIdx.x;
	CU_ULInt uliSlotIdx			= wrkID * nSlot + thID;
	CU_ULInt uliSlotDataIdx	= wrkID * nSlotData + thID * CU_SLOT_CAPACITY_16;

	CU_SLOT_BUFFER_TYPE* memNPxl = cu_nPixel + uliSlotIdx;
	CU_SLOT_BUFFER_TYPE* memType = cu_pType + uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZcrd = cu_pZcrd + uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZnrm = cu_pZnrm + uliSlotDataIdx;

	CU_SLOT_BUFFER_TYPE S_L = *(memNPxl);
	bool bExplicitPairStarted = false;
	for (int p = 0; p < S_L; p++)
	{
		CU_SLOT_BUFFER_TYPE p_type = memType[p];
		CU_SLOT_BUFFER_TYPE p_z		= memZcrd[p];
		CU_SLOT_BUFFER_TYPE p_nZ		= memZnrm[p];

		//explicitly create SS segments
		if (p_type > 0 && p_z > 0)
		{
			if ((p_type & cu_typeBe) && (!bExplicitPairStarted && p_nZ < sin_theta_c_x1000))
			{
				cu_Or(memType + p, cu_typeSSB);			bExplicitPairStarted = true;
			}
			else if (bExplicitPairStarted && (p_type & cu_typeAl))
			{
				cu_Or(memType + p, cu_typeSSA);			bExplicitPairStarted = false;
			}
		}
	}

	if (bExplicitPairStarted)//mark the bottom plate as shadow acceptor (for rendering).
	{
			cu_Add(memNPxl, 1);
			cu_Or(memType + S_L, typeSSA);//Note: this empty pxl is not Alpha.
	}
}

__global__ void cu_calculate(CU_SLOT_BUFFER_TYPE*  cu_nPixel, CU_SLOT_BUFFER_TYPE*  cu_pType,
	CU_SLOT_BUFFER_TYPE*  cu_pZcrd, CU_SLOT_BUFFER_TYPE*  cu_pZnrm, 
	CU_SLOT_BUFFER_TYPE*  cu_Vo, CU_SLOT_BUFFER_TYPE*  cu_Vss, 
	int nSlot, int nBlockDimX_64)//reduction
{
	const int wrkID			= blockIdx.y;
	const CU_ULInt nSlotData = nSlot * CU_SLOT_CAPACITY_16;
	const int thID = blockIdx.x * blockDim.x + threadIdx.x;
	CU_ULInt uliSlotIdx			= wrkID * nSlot + thID;
	CU_ULInt uliSlotDataIdx	= wrkID * nSlotData + thID * CU_SLOT_CAPACITY_16;

	CU_SLOT_BUFFER_TYPE* memNPxl	= cu_nPixel + uliSlotIdx;
	CU_SLOT_BUFFER_TYPE* memVo		= cu_Vo			+ uliSlotIdx;
	CU_SLOT_BUFFER_TYPE* memVss		= cu_Vss		+ uliSlotIdx;
	CU_SLOT_BUFFER_TYPE* memType	= cu_pType	+ uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZcrd	= cu_pZcrd	+ uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZnrm	= cu_pZnrm	+ uliSlotDataIdx;

	bool _b_P_started = false;
	int al_sum = 0, be_sum = 0, ssb_sum = 0, ssa_sum = 0;

#if 0
	int S_L = min(*memNPxl,SLOT_CAPACITY_32);//Slot Length. (number of all the pixels in slot, including noises)
	for (int p = 0; p < S_L; p++)
#else
	for (int p = 0; p < CU_SLOT_CAPACITY_16; p++)
#endif
	{
		CU_SLOT_BUFFER_TYPE p_type = memType[p];
		CU_SLOT_BUFFER_TYPE p_z		= memZcrd[p];

		//if(p_z > 0)
		{
			if (p_type & cu_typeAl)	{  al_sum += p_z;}
			if (p_type & cu_typeBe)	{	 be_sum += p_z;}
			if (p_type & cu_typeSSA) { ssa_sum += p_z;}
			if (p_type & cu_typeSSB) { ssb_sum += p_z; }
		}
	}

	CU_SLOT_BUFFER_TYPE Vo = max(al_sum - be_sum, 0);//가끔 노이즈로 인해 마이너스 값이 나올 수 있다.
	CU_SLOT_BUFFER_TYPE Vss = max(ssb_sum - ssa_sum, 0);
	cu_Exch(memVo, Vo);
	cu_Exch(memVss, Vss);

}



	__global__ void cu_rotVoxel_16x1(
		int nFlatTri, int nYPR, int nVoxelX, int yprID_to_start,
		float* cu_m4x3,	float* cu_flattri0,	
		CU_SLOT_BUFFER_TYPE* cu_nPixel, CU_SLOT_BUFFER_TYPE* cu_pType, CU_SLOT_BUFFER_TYPE* cu_pZcrd, CU_SLOT_BUFFER_TYPE* cu_pZnrm)
	{
		//Note: blockDimx = ( nFlatTri * _nYPRInBatch, 1), (16, 1, 1)
		int triID	= blockIdx.x;//triangle ID within a same block(orientation).
		int wrkID	= blockIdx.y;//ypr data ID within a batch.

		const int thID	= threadIdx.x;//[0~16]
		int yprID = yprID_to_start  + wrkID;//Caution: m4x3_ID == 0 ~ nYPR-1.
		if (triID >= nFlatTri ||yprID >= nYPR) return;
	
		__shared__ float ftri[CU_FLATTRI_SIZE_16], m4x3[CU_MATRIX_SIZE_12];

		//per-BLOCK operation +++++++++++++++
		if (thID < CU_FLATTRI_SIZE_16)	{//copy tri coord data to shared memory.
			ftri[thID]	= cu_flattri0[triID * CU_FLATTRI_SIZE_16 + thID];
		}
		__syncthreads();
		if (thID <  CU_MATRIX_SIZE_12)	{//copy matrix data to shared memory
			m4x3[thID]	= cu_m4x3[yprID * CU_MATRIX_SIZE_12 + thID];
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
		//  로컬 픽셀좌표는 (threadIdx.x, y_crd)
		//  global 좌표계는 (AABB_x0 + threadIdx.x, AABB_y0 + y_crd)임.
		//AABB of current triangle
			const register int& global_AABB_x0 = ftri[12];
			const register int& global_AABB_y0 = ftri[13];
			const int nSlot			= nVoxelX * nVoxelX;
			const int nSlotData = nSlot * CU_SLOT_CAPACITY_16;


		for( int y_crd = 0 ; y_crd < CU_SLOT_CAPACITY_16 ; y_crd++)//50~100% slower.
		{
			register float vxl_global_cnt[2] = { //global 좌표계에서의 현재 복셀의 위치.
							(global_AABB_x0 + thID ) + cu_HALF_VOXEL_SIZE,
							(global_AABB_y0 + y_crd) + cu_HALF_VOXEL_SIZE };
			if (vxl_global_cnt[0] >= nVoxelX || vxl_global_cnt[1] >= nVoxelX) continue;

			float u,v,w;
			if( cu_getBaryCoord2D(vxl_global_cnt, ftri + 0, ftri + 3, ftri + 6, u, v, w))
			{
				register int  new_z  = int(u * ftri[2] + v * ftri[5] + w * ftri[8]);
				register int  new_nZ = int(ftri[11] * cu_fNORMALFACTOR);//use the same normal vector.

				//write back data to global memory
				const int slot_ID		= (global_AABB_y0 + y_crd) * nVoxelX + (global_AABB_x0 + thID);//target slot ID.

				//memory index. do not change this order.
				CU_SLOT_BUFFER_TYPE*	memNPxl		= cu_nPixel + wrkID * nSlot		+ slot_ID;
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
					cu_Exch( memType, (new_nZ > 0) ? typeAl : typeBe);// = splitAlBe()
					#endif
				}
			}

		}//end of for(y_crd..)
		//end of per-THREAD operation ------------------------------
	}


	__global__ void cu_rotVoxel_Streamed_16x1(
		int nVoxelX, int nYPR, int nFlatTri, 
		int yprID, int triID_to_start,
		float* cu_m4x3,	float* cu_flattri0,	
		CU_SLOT_BUFFER_TYPE* cu_nPixel, CU_SLOT_BUFFER_TYPE* cu_pType, CU_SLOT_BUFFER_TYPE* cu_pZcrd, CU_SLOT_BUFFER_TYPE* cu_pZnrm)
	{
		//Note: blockDim  = ( nTriToWork, 1, 1) x (16,1,1)
		int wrkID = blockIdx.x;//[nTriToWork]
		int triID	= triID_to_start + wrkID;//triangle ID to work in this stream.
		const int thID	= threadIdx.x;//[16]

		if (triID >= nFlatTri ||yprID >= nYPR) return;

		__shared__ float ftri[CU_FLATTRI_SIZE_16], m4x3[CU_MATRIX_SIZE_12];

		//per-BLOCK operation +++++++++++++++
		if (thID < CU_FLATTRI_SIZE_16)	{//copy tri coord data to shared memory.
			ftri[thID]	= cu_flattri0[triID * CU_FLATTRI_SIZE_16 + thID];
		}
		__syncthreads();
		if (thID <  CU_MATRIX_SIZE_12)	{//copy matrix data to shared memory
			m4x3[thID]	= cu_m4x3[yprID * CU_MATRIX_SIZE_12 +  thID];
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
		//  로컬 픽셀좌표는 (x_crd,threadIdx.x)
		//  global 좌표계는 (AABB_x0 + x_crd, AABB_y0 + threadIdx.x)임.
		//AABB of current triangle
			const register int& global_AABB_x0 = ftri[12];
			const register int& global_AABB_y0 = ftri[13];
		for( int x_crd = 0 ; x_crd < CU_BLOCK_SIZE_16 ; x_crd++)//50~100% slower.
		{
			register float vxl_global_cnt[2] = { //global 좌표계에서의 현재 복셀의 위치.
							(global_AABB_x0 + x_crd) + cu_HALF_VOXEL_SIZE,
							(global_AABB_y0 + thID) + cu_HALF_VOXEL_SIZE };
			if (vxl_global_cnt[0] >= nVoxelX || vxl_global_cnt[1] >= nVoxelX) return;

			float u = 0,v = 0,w = 1;
			if( cu_getBaryCoord2D(vxl_global_cnt, ftri + 0, ftri + 3, ftri + 6, u, v, w))
			{
				register int  new_z  = int(u * ftri[2] + v * ftri[5] + w * ftri[8]);
				register int  new_nZ = int(ftri[11] * cu_fNORMALFACTOR);//use the same normal vector.

				//write back data to global memory
				const int nSlot			= nVoxelX * nVoxelX;
				const int nSlotData = nSlot * CU_SLOT_CAPACITY_16;
				const int slot_ID		= (global_AABB_y0 + thID) * nVoxelX + (global_AABB_x0 + x_crd);//target slot ID.

				//memory index. do not change this order.
				CU_SLOT_BUFFER_TYPE*	memNPxl	= cu_nPixel + slot_ID;
				CU_SLOT_BUFFER_TYPE		n_pixel	= *memNPxl;//current number of pxls in the slot
				const CU_ULInt	slotdata_ID		= slot_ID * CU_SLOT_CAPACITY_16 + n_pixel;//pxl ID inside the target slot
				if(n_pixel < CU_SLOT_CAPACITY_16-1)
				{ 
					CU_SLOT_BUFFER_TYPE*	memType	= cu_pType + slotdata_ID;
					CU_SLOT_BUFFER_TYPE*	memZcrd	= cu_pZcrd + slotdata_ID;
					CU_SLOT_BUFFER_TYPE*	memZnrm	= cu_pZnrm + slotdata_ID;

					cu_Add(	 memNPxl, 1);//increase target slot's current # of pxls
					cu_Exch( memZcrd, new_z);
					cu_Exch( memZnrm, new_nZ);
					#ifdef _CUDA_USE_SPLIT_AL_BE_IN_VOXELIZE_STEP
					cu_Exch( memType, (new_nZ > 0) ? typeAl : typeBe);// = splitAlBe()
					#endif
				}
			}
		}//end of for(x_crd..)
		//end of per-THREAD operation ------------------------------

	}




__global__ void cu_rotate(
	int nFlatTri, int nYPR, int yprID_to_start,
	float* cu_m4x3,	float* cu_flattri0,	/*output*/float* cu_FlatTri1)
{
	//Note: blockIdx = ( nFlatTri * _nYPRInBatch, 1)
	int triID	= blockIdx.x;//triangle ID within a same block(orientation).
	int wrkID	= blockIdx.y;//ypr data ID within a batch.

	int thID	= threadIdx.x;//this block is (16,1,1) size. threadIdx.y is zero.
	int yprID = yprID_to_start + wrkID;//Caution: m4x3_ID == 0 ~ nYPR-1.
	if (triID >= nFlatTri || yprID >= nYPR) return;
	//if(yprID != 50) return;
	
	__shared__ float ftri[FLATTRI_SIZE_16], m4x3[MATRIX_SIZE_12];

	//per-BLOCK operation +++++++++++++++
	if (thID < FLATTRI_SIZE_16)	{//copy tri coord data to shared memory.
		ftri[thID]	= cu_flattri0[triID * FLATTRI_SIZE_16 + thID];
	}
	__syncthreads();
	if (thID < MATRIX_SIZE_12)	{//copy matrix data to shared memory
		m4x3[thID]	= cu_m4x3[ yprID * MATRIX_SIZE_12 + thID];
	}
	__syncthreads();
	//+++++++++++++++++++++++++++++++++++

#if 0
	if(thID==0)
	{//matrix operation(YPR rotation + translation of AABB corner to origin)
		cu_matrixOp(m4x3, ftri + 0);//1st vertex
		cu_matrixOp(m4x3, ftri + 3);//2nd vertex
		cu_matrixOp(m4x3, ftri + 6);//3rd vertex

		m4x3[3] = 0; m4x3[7] = 0; m4x3[11] = 0;//eliminate translation
		cu_matrixOp(m4x3, ftri + 9);//rotate normal vector

		//triangle AABB corner in glocal coordinates
		ftri[12] = min(min(ftri[0], ftri[3]), ftri[6]);//AABB_x_min
		ftri[13] = min(min(ftri[1], ftri[4]), ftri[7]);//AABB_y_min
		//ftri[14] = max(max(ftri[0], ftri[3]), ftri[6]);//AABB_x_max
		//ftri[15] = max(max(ftri[1], ftri[4]), ftri[7]);//AABB_y_max
		//Do not call __syncthreads() here.
	}
	__syncthreads();
#else
	//matrix operation(YPR rotation + translation of AABB corner to origin)
	if(thID==0) cu_matrixOp(m4x3, ftri + 0);//1st vertex
	if(thID==1) cu_matrixOp(m4x3, ftri + 3);//2nd vertex
	if(thID==2) cu_matrixOp(m4x3, ftri + 6);//3rd vertex
	if(thID==3) {cu_matrixOp(m4x3, ftri + 9);//rotate normal vector
			 ftri[9] -= m4x3[3]; ftri[10] -= m4x3[7]; ftri[11] -= m4x3[11];};//eliminate translation
	__syncthreads();
	if(thID==0) {
		ftri[12] = min(min(ftri[0], ftri[3]), ftri[6]);//AABB_x_min
		ftri[13] = min(min(ftri[1], ftri[4]), ftri[7]);//AABB_y_min
	}
	__syncthreads();
#endif

	//per-BLOCK operation +++++++++++++++
	if (thID < FLATTRI_SIZE_16)	{	//write back to global memory
		int ft_id = wrkID * nFlatTri + triID;//=blockIdx.x?
		cu_FlatTri1[ ft_id * FLATTRI_SIZE_16 + thID] = ftri[thID];
	}
	__syncthreads();
	//+++++++++++++++++++++++++++++++++++

}

__global__ void cu_triVoxel(
	int nFlatTri,	int nVoxelX,
	float* cu_flattri1, int* cu_nPixel, int* cu_pType, int* cu_pZcrd, int* cu_pZnrm)
{
	//Note: blockIdx = ( nFlatTri * _nYPRInBatch, 1)
	int triID	= blockIdx.x;//triangle ID within a same block(orientation).
	int wrkID	= blockIdx.y;//ypr data ID within a batch.

	const int thID	= threadIdx.y * blockDim.x + threadIdx.x;//this block is (16,16,1) size.
	if (triID >= nFlatTri) return;

	__shared__ float ftri[FLATTRI_SIZE_16];//vtx crd data

	//per-BLOCK operation +++++++++++++++
	if (thID < FLATTRI_SIZE_16)	{//copy tri coord + AABB data to shared memory.
		int ft_id = wrkID * nFlatTri + triID;//=blockIdx.x
		ftri[thID] = cu_flattri1[ ft_id * FLATTRI_SIZE_16 + thID];
	}
	__syncthreads();
	//+++++++++++++++++++++++++++++++++++

	//AABB of current triangle
	int global_AABB_x0 = ftri[12];//AABB_x_min;
	int global_AABB_y0 = ftri[13];//AABB_y_min;

	//per-THREAD operation ------------------------------------
	//  (16,16)내에서의 로컬 픽셀좌표는 (threadIdx.x, threadIdx.y)
	//  global 좌표계는 (AABB_x0 + threadIdx.x, AABB_y0 + threadIdx.y)임.
	
	float vxl_global_cnt[2] = { //global 좌표계에서의 현재 복셀의 위치.
					(global_AABB_x0 + threadIdx.x) + HALF_VOXEL_SIZE,
					(global_AABB_y0 + threadIdx.y) + HALF_VOXEL_SIZE };
	if (vxl_global_cnt[0] >= nVoxelX || vxl_global_cnt[1] >= nVoxelX) return;
	float u = -1, v = -1, w = -1;
	if (cu_getBaryCoord2D(vxl_global_cnt, ftri + 0, ftri + 3, ftri + 6, u, v, w))
	{
		//interpolation result.
		int  new_z  = int(u * ftri[2] + v * ftri[5] + w * ftri[8]);
		int  new_nZ = int(ftri[11] * cu_fNORMALFACTOR);

		//write back data to global memory
		const int nSlot			= nVoxelX * nVoxelX;
		const int nSlotData = nSlot * SLOT_CAPACITY_32;
		const int slot_ID		= (global_AABB_y0 + threadIdx.y) * nVoxelX + (global_AABB_x0 + threadIdx.x);//target slot ID.

		//index. do not change this order.
		int* memNPxl	= cu_nPixel + wrkID * nSlot		+ slot_ID;
		int n_pixel		= *memNPxl;
		const int slotdata_ID = slot_ID * SLOT_CAPACITY_32 + n_pixel;//pxl ID inside the target slot

		int* memType	= cu_pType + wrkID * nSlotData + slotdata_ID;
		int* memZcrd	= cu_pZcrd + wrkID * nSlotData + slotdata_ID;
		int* memZnrm	= cu_pZnrm + wrkID * nSlotData + slotdata_ID;

		cu_Add(  memNPxl, 1);//increase target slot's current # of pxls
		cu_Exch( memType, (new_nZ > 0) ? typeAl : typeBe);// = splitAlBe()
		cu_Exch( memZcrd, new_z);
		cu_Exch( memZnrm, new_nZ);
	}
	//end of per-THREAD operation ------------------------------
}



	__global__ void cu_rotVoxel_Streamed_16x1(
		int nVoxelX, int nYPR, int nFlatTri, 
		int yprID, int triID_to_start,
		float* dev_m4m,  float* dev_tri0,  
		CU_SLOT_BUFFER_TYPE* dev_nPixel, CU_SLOT_BUFFER_TYPE* dev_pType, CU_SLOT_BUFFER_TYPE* dev_pZcrd, CU_SLOT_BUFFER_TYPE* dev_pZnrm);


	__global__ void cu_rotVoxel_16x1(
		int nTri, int nYPR, int nVoxelX, int yprID_to_start,
		float* dev_m4m,  float* dev_tri0,  
		CU_SLOT_BUFFER_TYPE* dev_nPixel, CU_SLOT_BUFFER_TYPE* dev_pType, CU_SLOT_BUFFER_TYPE* dev_pZcrd, CU_SLOT_BUFFER_TYPE* dev_pZnrm);

__global__ void cu_rotate(
	int nTri, int nYPR, int yprID_to_start,
	float* dev_m4m,  float* dev_tri0,  /*output*/float* dev_tri1);

__global__ void cu_triVoxel(
	int nTri, int nVoxelX, float* dev_tri15f,
	CU_SLOT_BUFFER_TYPE* dev_nPixel, CU_SLOT_BUFFER_TYPE* dev_pType, CU_SLOT_BUFFER_TYPE* dev_pZcrd, CU_SLOT_BUFFER_TYPE* dev_pZnrm);
