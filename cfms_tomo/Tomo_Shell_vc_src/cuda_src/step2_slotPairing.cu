#include "step2_slotPairing.cuh"
#include "atomicWrite.cuh"

template<typename T> __global__ void cu_slotPairing(
	CU_SLOT_BUFFER_TYPE* cu_nPixel ,
	CU_SLOT_BUFFER_TYPE* cu_pType ,
	CU_SLOT_BUFFER_TYPE* cu_pZcrd ,
	CU_SLOT_BUFFER_TYPE* cu_pZnrm ,
	CU_SLOT_BUFFER_TYPE* cu_Vo ,
	CU_SLOT_BUFFER_TYPE* cu_Vss ,
	ShouldSwap<T> shouldSwap , int nSlot , int sin_theta_c_x1000)
{
	const int slotID = blockIdx.x;//YPR ID 
	const int wrkID = blockIdx.y;//YPR ID 
	const int thID = threadIdx.x;//[SLOT_CAPACITY]


	const CU_ULInt nSlotData = nSlot * CU_SLOT_CAPACITY_16;

	CU_ULInt uliSlotIdx = wrkID * nSlot + slotID;
	CU_ULInt uliSlotDataIdx = wrkID * nSlotData + slotID * CU_SLOT_CAPACITY_16;

	CU_SLOT_BUFFER_TYPE* memNPxl = cu_nPixel + uliSlotIdx;
	CU_SLOT_BUFFER_TYPE* memVo = cu_Vo + uliSlotIdx;
	CU_SLOT_BUFFER_TYPE* memVss = cu_Vss + uliSlotIdx;

#ifdef _CUDA_USE_NONZERO_SLOTBUFFER_ONLY
	CU_SLOT_BUFFER_TYPE S_L = *memNPxl;//Slot Length. (number of all the pixels in slot, including noises)
	if (S_L > CU_SLOT_CAPACITY_16) S_L = CU_SLOT_CAPACITY_16;//clamp: voxelize may over-count a saturated slot
#else
	CU_SLOT_BUFFER_TYPE S_L = CU_SLOT_CAPACITY_16;
#endif

#ifdef _CUDA_USE_SHARED_MEMORY_IN_SLOTPAIRING
	__shared__ CU_SLOT_BUFFER_TYPE memType[CU_SLOT_CAPACITY_16];
	__shared__ CU_SLOT_BUFFER_TYPE memZcrd[CU_SLOT_CAPACITY_16];
	__shared__ CU_SLOT_BUFFER_TYPE memZnrm[CU_SLOT_CAPACITY_16];

	//per-BLOCK operation +++++++++++++++
	if (thID < CU_SLOT_CAPACITY_16) { //copy slotbuffet pxl data to shared memory.
		memType[thID] = cu_pType[uliSlotDataIdx + thID];
		memZcrd[thID] = cu_pZcrd[uliSlotDataIdx + thID];
		memZnrm[thID] = cu_pZnrm[uliSlotDataIdx + thID];
	}
	__syncthreads();
	//+++++++++++++++++++++++++++++++++++

#else
	CU_SLOT_BUFFER_TYPE* memType = cu_pType + uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZcrd = cu_pZcrd + uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZnrm = cu_pZnrm + uliSlotDataIdx;
#endif

	//#1. sortSlotByZ()
	//per-BLOCK operation +++++++++++++++
	{
		for (CU_SLOT_BUFFER_TYPE p = 0; p < CU_SLOT_CAPACITY_16; p++)
		{
			unsigned int offset = p - (p / 2) * 2;//p % 2
			unsigned int iLeft = 2 * thID + offset;
			unsigned int iRght = iLeft + 1;

			if (iRght < CU_SLOT_CAPACITY_16)
			{
				bool bSwap = shouldSwap(memZcrd[iLeft] , memZcrd[iRght]);
				if (!bSwap && memZcrd[iLeft] == memZcrd[iRght]) {
					bSwap = shouldSwap(memZnrm[iLeft] , memZnrm[iRght]);
				}
				if (bSwap)
				{
					swap<T>(&memZcrd[iLeft] , &memZcrd[iRght]);
					swap<T>(&memZnrm[iLeft] , &memZnrm[iRght]);
					swap<T>(&memType[iLeft] , &memType[iRght]);
				}
			}
			__syncthreads();
		}
	}
	//+++++++++++++++++++++++++++++++++++


	//#2. slitAlBe()
	{
#ifndef _CUDA_USE_SPLIT_AL_BE_IN_VOXELIZE_STEP
		//per-BLOCK operation +++++++++++++++
		if (thID < CU_SLOT_CAPACITY_16) {//Omit side-face points(nZ==0).
			if (memZnrm[thID] > 10) { cu_Or(memType + thID , typeAl); }
			else if (memZnrm[thID] < -10) { cu_Or(memType + thID , typeBe); }
		}
		__syncthreads();
		//+++++++++++++++++++++++++++++++++++
#endif

//#3. matchAlBePair()
		if (thID == 0)
		{
			bool _b_P_started = false;//check pair is started.
			for (int p = 0; p < S_L; p++)
			{
				CU_SLOT_BUFFER_TYPE p_type = memType[p];
				CU_SLOT_BUFFER_TYPE p_z = memZcrd[p];

				if (!_b_P_started && p_type == cu_typeAl) { _b_P_started = true; }//true pixel. leave it.
				else if (_b_P_started && p_type == cu_typeBe) { _b_P_started = false; }//true pixel. leave it.
				else if ((p_type == cu_typeAl || p_type == cu_typeBe)) { cu_Exch(memType + p , 0); }//noise pixel. Hide it.
			}
		}
		__syncthreads();
	}

	//#4. createShadow()
	if (thID == 0)
	{
		bool bShadowStarted = false;
		for (int p = 0; p < S_L; p++)
		{
			CU_SLOT_BUFFER_TYPE p_type = memType[p];
			CU_SLOT_BUFFER_TYPE p_nZ = memZnrm[p];

			//explicitly create SS segments
			if (p_type > 0) {///except for noise
				if (!bShadowStarted && (p_type & cu_typeBe) && (p_nZ < sin_theta_c_x1000)) {
					cu_Or(memType + p , cu_typeSSB);			bShadowStarted = true;
				}
				else if (bShadowStarted && (p_type & cu_typeAl)) {
					cu_Or(memType + p , cu_typeSSA);			bShadowStarted = false;
				}
			}
		}

		if (bShadowStarted && S_L < CU_SLOT_CAPACITY_16 - 1) {//mark the bottom plate as shadow acceptor (for rendering).
			cu_Add(memNPxl , 1); S_L++;
			cu_Or(memType + S_L - 1 , cu_typeSSA);//Note: this empty pxl is not Alpha.
		}
	}

	//#5. calculate()
	{
		bool _b_P_started = false;
		int al_sum = 0 , be_sum = 0 , ssb_sum = 0 , ssa_sum = 0;
		__shared__ int sums[4];
		sums[0] = sums[1] = sums[2] = sums[3] = 0;

		//per-BLOCK operation +++++++++++++++
		if (thID < S_L) {
			CU_SLOT_BUFFER_TYPE p_z = memZcrd[thID];
			if (p_z >= 0)
			{
				CU_SLOT_BUFFER_TYPE p_type = memType[thID];
				if (p_type & cu_typeAl) { cu_Add(sums + (int)enumPixelType::eptAl , p_z); }
				if (p_type & cu_typeBe) { cu_Add(sums + (int)enumPixelType::eptBe , p_z); }
				if (p_type & cu_typeSSB) { cu_Add(sums + (int)enumPixelType::eptSSB , p_z); }
				if (p_type & cu_typeSSA) { cu_Add(sums + (int)enumPixelType::eptSSA , p_z); }
			}

		}
		__syncthreads();
		//+++++++++++++++++++++++++++++++++++

		CU_SLOT_BUFFER_TYPE Vo = max(sums[(int)enumPixelType::eptAl] - sums[(int)enumPixelType::eptBe] , 0);//max(,0): sometimes can have noisy minus values
		CU_SLOT_BUFFER_TYPE Vss = max(sums[(int)enumPixelType::eptSSB] - sums[(int)enumPixelType::eptSSA] , 0);
		cu_Exch(memVo , Vo);
		cu_Exch(memVss , Vss);
	}

#ifdef _CUDA_USE_SHARED_MEMORY_IN_SLOTPAIRING
	//per-BLOCK operation +++++++++++++++
	if (thID < CU_SLOT_CAPACITY_16) { //write back.
		cu_pType[uliSlotDataIdx + thID] = memType[thID];
		cu_pZcrd[uliSlotDataIdx + thID] = memZcrd[thID];
		cu_pZnrm[uliSlotDataIdx + thID] = memZnrm[thID];
	}
	__syncthreads();
	//+++++++++++++++++++++++++++++++++++
#endif

}

//**********************************************************************************************
//
// concurrent stream version
// 
//**********************************************************************************************

#define _TURN_ON_PAIRING_STEP_1  //does not work in RTX-4090. 2023-06-13
#define _TURN_ON_PAIRING_STEP_3

template<typename T> __global__ void cu_slotPairing_Streamed(
	int nSlot , ShouldSwap<T> shouldSwap , int sin_theta_c_x1000 ,
	bool bWriteBack , bool bUseExplicitSS ,
	CU_SLOT_BUFFER_TYPE* cu_nPixel ,
	CU_SLOT_BUFFER_TYPE* cu_Vo ,
	CU_SLOT_BUFFER_TYPE* cu_Vss ,
	CU_SLOT_BUFFER_TYPE* cu_pType ,
	CU_SLOT_BUFFER_TYPE* cu_pZcrd ,
	CU_SLOT_BUFFER_TYPE* cu_pZnrm)
{
	//(nWorksPerBlocks, 1, 1) x (CU_SLOT_CAPACITY_16 , CU_SLOTS_PER_WORK, 1)
	const int thIDx = threadIdx.x;//[SLOT_CAPACITY]
	const int thIDy = threadIdx.y;//local slot ID, =CU_SLOTS_PER_WORK
	const int slotID0 = blockIdx.x * CU_SLOTS_PER_WORK;// + thIDy;//global slot ID

	const bool slotValid = (slotID0 + thIDy < nSlot);

	CU_ULInt uliSlotIdx = slotID0;
	CU_ULInt uliSlotDataIdx = slotID0 * CU_SLOT_CAPACITY_16;

	CU_SLOT_BUFFER_TYPE* memNPxl = cu_nPixel + uliSlotIdx;//write directly to global memory
	CU_SLOT_BUFFER_TYPE* memVo = cu_Vo + uliSlotIdx;
	CU_SLOT_BUFFER_TYPE* memVss = cu_Vss + uliSlotIdx;

	__shared__ CU_SLOT_BUFFER_TYPE slotLenPair[CU_SLOTS_PER_WORK];
	if (thIDx == 0 && thIDy < CU_SLOTS_PER_WORK) {
		CU_SLOT_BUFFER_TYPE n_ = slotValid ? cu_nPixel[slotID0 + thIDy] : 0;
		slotLenPair[thIDy] = (n_ > CU_SLOT_CAPACITY_16) ? CU_SLOT_CAPACITY_16 : n_;
	}
	__syncthreads();

#ifdef _CUDA_USE_NONZERO_SLOTBUFFER_ONLY
	__shared__ CU_SLOT_BUFFER_TYPE S_L[CU_SLOTS_PER_WORK];
	if (thIDx == 0 && thIDy < CU_SLOTS_PER_WORK) { CU_SLOT_BUFFER_TYPE n_ = slotValid ? cu_nPixel[slotID0 + thIDy] : 0; S_L[thIDy] = (n_ > CU_SLOT_CAPACITY_16) ? CU_SLOT_CAPACITY_16 : n_; }//Slot Length, clamped to capacity (voxelize may over-count a saturated slot)
	__syncthreads();
#else
	CU_SLOT_BUFFER_TYPE S_L = slotValid ? CU_SLOT_CAPACITY_16 : 0;
#endif

#ifdef _CUDA_USE_SHARED_MEMORY_IN_SLOTPAIRING
	__shared__ CU_SLOT_BUFFER_TYPE memType[CU_SLOTS_PER_WORK][CU_SLOT_CAPACITY_16];//write via shared memory.
	__shared__ CU_SLOT_BUFFER_TYPE memZcrd[CU_SLOTS_PER_WORK][CU_SLOT_CAPACITY_16];
	__shared__ CU_SLOT_BUFFER_TYPE memZnrm[CU_SLOTS_PER_WORK][CU_SLOT_CAPACITY_16];

	if (thIDx < CU_SLOT_CAPACITY_16) {
		memType[thIDy][thIDx] = 0;		memZcrd[thIDy][thIDx] = 0;		memZnrm[thIDy][thIDx] = 0;
	}
	__syncthreads();

	//per-BLOCK operation +++++++++++++++
#ifdef _CUDA_USE_NONZERO_SLOTBUFFER_ONLY
	if (thIDx < S_L[thIDy])
#else
	if (slotValid && thIDx < slotLenPair[thIDy])//rows beyond the (truncated) count are stale/unused - skip their traffic
#endif
	{ //copy slotbuffer pxl data in global memory to local shared memory.
		memType[thIDy][thIDx] = cu_pType[uliSlotDataIdx + thIDy * CU_SLOT_CAPACITY_16 + thIDx];
		memZcrd[thIDy][thIDx] = cu_pZcrd[uliSlotDataIdx + thIDy * CU_SLOT_CAPACITY_16 + thIDx];
		memZnrm[thIDy][thIDx] = cu_pZnrm[uliSlotDataIdx + thIDy * CU_SLOT_CAPACITY_16 + thIDx];
	}	__syncthreads();
	//+++++++++++++++++++++++++++++++++++
#else
	CU_SLOT_BUFFER_TYPE* memType = cu_pType + uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZcrd = cu_pZcrd + uliSlotDataIdx;
	CU_SLOT_BUFFER_TYPE* memZnrm = cu_pZnrm + uliSlotDataIdx;
#endif

#ifdef _TURN_ON_PAIRING_STEP_1
	//#1. sortSlotByZ()
	//odd-even transposition sort finishes in max(slotLen) passes; with CAPACITY=256
	//running all 256 passes for mostly-short slots would waste ~4x sync/compute.
	__shared__ int sortPasses;
	if (thIDx == 0 && thIDy == 0) { sortPasses = 0; }
	__syncthreads();
	if (thIDx == 0) { atomicMax(&sortPasses, (int)slotLenPair[thIDy]); }
	__syncthreads();
	//per-BLOCK operation +++++++++++++++
	for (CU_SLOT_BUFFER_TYPE p = 0; p < sortPasses; p++)
	{
		unsigned int offset = p - (p / 2) * 2;//p % 2
		unsigned int iLeft = 2 * thIDx + offset;
		unsigned int iRght = iLeft + 1;

		if (iRght < slotLenPair[thIDy])
		{
			bool bSwap = shouldSwap(memZcrd[thIDy][iLeft] , memZcrd[thIDy][iRght]);
			if (!bSwap && memZcrd[thIDy][iLeft] == memZcrd[thIDy][iRght]) {
				bSwap = shouldSwap(memZnrm[thIDy][iLeft] , memZnrm[thIDy][iRght]);
			}
			if (bSwap)
			{
				swap<T>(&memZcrd[thIDy][iLeft] , &memZcrd[thIDy][iRght]);
				swap<T>(&memZnrm[thIDy][iLeft] , &memZnrm[thIDy][iRght]);
				swap<T>(&memType[thIDy][iLeft] , &memType[thIDy][iRght]);
			}
		}
		__syncthreads();
	}
	//+++++++++++++++++++++++++++++++++++
#endif


	//#2. slitAlBe()
	{
#ifndef _CUDA_USE_SPLIT_AL_BE_IN_VOXELIZE_STEP
		//per-BLOCK operation +++++++++++++++
		if (thIDx < CU_SLOT_CAPACITY_16) {//Omit lateral-face points(nZ==0).
			if (memZnrm[thIDy][thIDx] > 10) { cu_Or(&memType[thIDy][thIDx] , typeAl); }
			else if (memZnrm[thIDy][thIDx] < -10) { cu_Or(&memType[thIDy][thIDx] , typeBe); }
		}
		__syncthreads();
		//+++++++++++++++++++++++++++++++++++
#endif
	}

#ifdef _TURN_ON_PAIRING_STEP_3
	//#3. matchAlBePair() 
	__shared__ int nSSA[CU_SLOTS_PER_WORK] , nSSB[CU_SLOTS_PER_WORK];//number pf SSA, SSB pixels
	if (thIDx == 0) { nSSA[thIDy] = 0; nSSB[thIDy] = 0; }

#if 0
#ifdef _CUDA_USE_NONZERO_SLOTBUFFER_ONLY
	else if (thIDx < S_L[thIDy]) {
#else
	else if (thIDx < CU_SLOT_CAPACITY_16) {
#endif
		CU_SLOT_BUFFER_TYPE p_type = memType[thIDy][thIDx];
		CU_SLOT_BUFFER_TYPE p_type0 = shfl_up(1 , (unsigned)p_type , CU_SLOT_CAPACITY_16);//ToDo: shuffle operation not working in 4090
		if (p_type & p_type0) { cu_Exch(memType[thIDy] + thIDx , 0); }//noise pixel. Hide it.
	}
	__syncthreads();
#endif

#if 0
	//#4-1. createSSB
#ifdef _CUDA_USE_NONZERO_SLOTBUFFER_ONLY
	if (thIDx >= 1 && thIDx < S_L[thIDy]) {
#else
	if (thIDx >= 1 && thIDx < CU_SLOT_CAPACITY_16) {
#endif
		CU_SLOT_BUFFER_TYPE p_type = memType[thIDy][thIDx];
		CU_SLOT_BUFFER_TYPE p_nZ = memZnrm[thIDy][thIDx];
		if ((p_type & cu_typeBe) && (p_nZ < sin_theta_c_x1000)) { cu_Or(memType[thIDy] + thIDx , cu_typeSSB); nSSB[thIDy]++; }
	}__syncthreads();

	//#4-2. createSSA
#ifdef _CUDA_USE_NONZERO_SLOTBUFFER_ONLY
	if (thIDx >= 1 && thIDx < S_L[thIDy]) {
#else
	if (thIDx >= 1 && thIDx < CU_SLOT_CAPACITY_16) {
#endif
		CU_SLOT_BUFFER_TYPE p_type = memType[thIDy][thIDx];
		CU_SLOT_BUFFER_TYPE p_type0 = shfl_up(1 , (unsigned)p_type , CU_SLOT_CAPACITY_16);//ToDo: shuffle operation not working in 4090
		if ((p_type & cu_typeAl) && (p_type0 & cu_typeSSB)) { cu_Or(memType[thIDy] + thIDx , cu_typeSSA); nSSA[thIDy]++; }
	}__syncthreads();

	//#4-2-1. create bottom SSA
	if (thIDx == 0) {//mark the bottom plate as shadow acceptor (for rendering).
		if (nSSB[thIDy] > nSSA[thIDy])
		{
			cu_Add(memNPxl + thIDy , 1);
#ifdef _CUDA_USE_NONZERO_SLOTBUFFER_ONLY
			S_L[thIDy]++;				cu_Or(memType[thIDy] + S_L[thIDy] - 1 , cu_typeSSA);
#else
			cu_Or(memType[thIDy] + *(memNPxl + thIDy) - 1 , cu_typeSSA);
#endif
		}//Note: this empty pxl is not typeAl.
	}__syncthreads();

#else
	//#4-#5. CPU brief slot pairing path: matchAlBePairBriefly(), createVoPixels(),
	// createShadowBriefly(), createTCPixels(), then createVss_*().
	if (slotValid && thIDx == 0)
	{
		int slotLen = slotLenPair[thIDy];
		if (slotLen <= 1)
		{
			cu_Exch(memVo + thIDy, 0);
			cu_Exch(memVss + thIDy, 0);
		}
		else
		{
		bool bPairStarted = false;
		for (int p = 0; p < slotLen; p++)
		{
			CU_SLOT_BUFFER_TYPE p_type = memType[thIDy][p];
			if (!bPairStarted && p_type == cu_typeAl) { bPairStarted = true; }
			else if (bPairStarted && p_type == cu_typeBe) { bPairStarted = false; }
			else if (p_type == cu_typeAl || p_type == cu_typeBe) { cu_Exch(memType[thIDy] + p, 0); }
		}

		int al_sum = 0;
		int be_sum = 0;
		for (int p = 0; p < slotLen; p++)
		{
			CU_SLOT_BUFFER_TYPE p_type = memType[thIDy][p];
			CU_SLOT_BUFFER_TYPE p_z = memZcrd[thIDy][p];
			if (p_type & cu_typeAl) { al_sum += p_z; }
			if (p_type & cu_typeBe) { be_sum += p_z; }
		}
		cu_Exch(memVo + thIDy, max(al_sum - be_sum, 0));

		bool bExplicitPairStarted = false;
		bool bImplicitPairStarted = false;
		for (int p = 0; p < slotLen; p++)
		{
			CU_SLOT_BUFFER_TYPE p_type = memType[thIDy][p];
			CU_SLOT_BUFFER_TYPE p_nZ = memZnrm[thIDy][p];
			if ((p_type & cu_typeBe) && p_nZ < 1)
			{
				if (!bExplicitPairStarted && p_nZ < sin_theta_c_x1000)
				{
					cu_Or(memType[thIDy] + p, cu_typeSSB);
					bExplicitPairStarted = true;
				}
				if (!bImplicitPairStarted && p_nZ > sin_theta_c_x1000)
				{
					cu_Or(memType[thIDy] + p, cu_typeNVB);
					bImplicitPairStarted = true;
				}
			}
			else if (p_type & cu_typeAl)
			{
				if (bExplicitPairStarted)
				{
					cu_Or(memType[thIDy] + p, cu_typeSSA);
					bExplicitPairStarted = false;
				}
				if (bImplicitPairStarted)
				{
					cu_Or(memType[thIDy] + p, cu_typeNVA);
					bImplicitPairStarted = false;
				}
			}
		}

		if (bExplicitPairStarted && slotLen < CU_SLOT_CAPACITY_16)
		{
			int bottomIdx = slotLen;
			cu_Add(memNPxl + thIDy, 1);
#ifdef _CUDA_USE_NONZERO_SLOTBUFFER_ONLY
			S_L[thIDy]++;
#endif
			slotLen++;
			cu_Or(memType[thIDy] + bottomIdx, cu_typeSSA);
			cu_Exch(memZcrd[thIDy] + bottomIdx, 0);
			cu_Exch(memZnrm[thIDy] + bottomIdx, 0);
		}
		if (bImplicitPairStarted && slotLen < CU_SLOT_CAPACITY_16)
		{
			int bottomIdx = slotLen;
			cu_Add(memNPxl + thIDy, 1);
#ifdef _CUDA_USE_NONZERO_SLOTBUFFER_ONLY
			S_L[thIDy]++;
#endif
			slotLen++;
			cu_Or(memType[thIDy] + bottomIdx, cu_typeNVA);
			cu_Exch(memZcrd[thIDy] + bottomIdx, 0);
			cu_Exch(memZnrm[thIDy] + bottomIdx, 0);
		}

		if (!bUseExplicitSS)
		{
			for (int p = 0; p < slotLen; p++)
			{
				if (memType[thIDy][p] & cu_typeAl)
				{
					cu_Or(memType[thIDy] + p, cu_typeTC);
					break;
				}
			}
		}

		int ssb_sum = 0;
		int ssa_sum = 0;
		int tc_sum = 0;
		int nvb_sum = 0;
		int nva_sum = 0;
		al_sum = 0;
		be_sum = 0;
		for (int p = 0; p < slotLen; p++)
		{
			CU_SLOT_BUFFER_TYPE p_type = memType[thIDy][p];
			CU_SLOT_BUFFER_TYPE p_z = memZcrd[thIDy][p];
			if (p_type & cu_typeAl) { al_sum += p_z; }
			if (p_type & cu_typeBe) { be_sum += p_z; }
			if (p_type & cu_typeSSB) { ssb_sum += p_z; }
			if (p_type & cu_typeSSA) { ssa_sum += p_z; }
			if (p_type & cu_typeTC) { tc_sum += p_z; }
			if (p_type & cu_typeNVB) { nvb_sum += p_z; }
			if (p_type & cu_typeNVA) { nva_sum += p_z; }
		}

		CU_SLOT_BUFFER_TYPE Vss = bUseExplicitSS ? (ssb_sum - ssa_sum) : (-al_sum + be_sum + tc_sum - nvb_sum + nva_sum);
		cu_Exch(memVss + thIDy, Vss);
		}
	}
	__syncthreads();

#endif
#endif

#ifdef _CUDA_USE_SHARED_MEMORY_IN_SLOTPAIRING
	//per-BLOCK operation +++++++++++++++
#ifdef _CUDA_USE_NONZERO_SLOTBUFFER_ONLY
	if (bWriteBack && thIDx < S_L[thIDy]) { //write back.
#else
	if (slotValid && bWriteBack && thIDx < min(slotLenPair[thIDy] + 2, (CU_SLOT_BUFFER_TYPE)CU_SLOT_CAPACITY_16)) { //write back pairing results (+2: bottom SSA/NVA pixels appended by the brief path).
#endif
		cu_pType[uliSlotDataIdx + thIDy * CU_SLOT_CAPACITY_16 + thIDx] = memType[thIDy][thIDx];
		cu_pZcrd[uliSlotDataIdx + thIDy * CU_SLOT_CAPACITY_16 + thIDx] = memZcrd[thIDy][thIDx];
		cu_pZnrm[uliSlotDataIdx + thIDy * CU_SLOT_CAPACITY_16 + thIDx] = memZnrm[thIDy][thIDx];
	}	__syncthreads();
	//+++++++++++++++++++++++++++++++++++
#endif

	}

void DoNothing(void)
{
	ShouldSwap<CU_SLOT_BUFFER_TYPE> shouldSwap;
	CU_SLOT_BUFFER_TYPE* _P = nullptr;
	cu_slotPairing	<CU_SLOT_BUFFER_TYPE> << <0 , 0 >> > (_P , _P , _P , _P , _P , _P , shouldSwap , 0 , 0);

	cu_slotPairing_Streamed<CU_SLOT_BUFFER_TYPE> << <1 , 1 >> > (0 , shouldSwap , 0 , true , false , _P , _P , _P , _P , _P , _P);
}
