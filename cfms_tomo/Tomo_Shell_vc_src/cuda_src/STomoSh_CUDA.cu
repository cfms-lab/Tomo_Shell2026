#include "STomoSh_CUDA.cuh"
//#include "device_launch_parameters.h"
#include <iostream>
#include <stdio.h>
#include <cstdlib>

#include "step1_voxelize.cuh"//obsolete..
#include "step1_rotPixel.cuh"
#include "step2_slotPairing.cuh"
#include "step3_generateBed.cuh"
#include "step4_reducedSum.cuh"
#include "atomicWrite.cuh"

using namespace Tomo;
ShouldSwap<CU_SLOT_BUFFER_TYPE> descendingOrder(true);

static bool tomoDebugSlotInputEnabled()
{
	char* env = nullptr;
	size_t envLen = 0;
	bool enabled = false;
	if (_dupenv_s(&env, &envLen, "TOMO_DEBUG_SLOT_INPUT") == 0 && env != nullptr) {
		enabled = (std::atoi(env) != 0);
		free(env);
	}
	return enabled;
}

static int tomoDebugSlotInputLimit()
{
	char* env = nullptr;
	size_t envLen = 0;
	int limit = 0;
	if (_dupenv_s(&env, &envLen, "TOMO_DEBUG_SLOT_LIMIT") == 0 && env != nullptr) {
		limit = std::atoi(env);
		free(env);
	}
	return limit;
}

static void tomoDebugPrintCudaSlotInput(SlotDataIterator sdIt, SlotData& hostSlotData, int nSlot, int nVoxelX, int yprID)
{
	static int callNo = 0;
	if (!tomoDebugSlotInputEnabled()) return;
	int limit = tomoDebugSlotInputLimit();
	if (limit > 0 && callNo >= limit) { callNo++; return; }

	cudaStreamSynchronize(sdIt->stream); cudaCheckError();
	sdIt->ReadPxls(hostSlotData.cu_sNPxl, hostSlotData.cu_sdType, hostSlotData.cu_sdZcrd, hostSlotData.cu_sdZnrm);

	long long nonempty = 0, pairable = 0, rows = 0, sat = 0;
	long long alCnt = 0, beCnt = 0, sideCnt = 0;
	long long alZ = 0, beZ = 0, allZ = 0;
	int maxLen = 0;
	for (int slotID = 0; slotID < nSlot; slotID++) {
		int S_L = hostSlotData.cu_sNPxl[slotID];
		if (S_L <= 0) continue;
		if (S_L > CU_SLOT_CAPACITY_16) S_L = CU_SLOT_CAPACITY_16;
		nonempty++;
		if (S_L > 1) pairable++;
		if (S_L > maxLen) maxLen = S_L;
		if (S_L >= CU_SLOT_CAPACITY_16) sat++;
		rows += S_L;
		for (int p = 0; p < S_L; p++) {
			const int idx = slotID * CU_SLOT_CAPACITY_16 + p;
			const int z = hostSlotData.cu_sdZcrd[idx];
			const int nz = hostSlotData.cu_sdZnrm[idx];
			allZ += z;
			if (nz > 0) { alCnt++; alZ += z; }
			else if (nz < 0) { beCnt++; beZ += z; }
			else { sideCnt++; }
		}
	}

	char* dumpDir = nullptr;
	size_t dumpDirLen = 0;
	char* dumpCallEnv = nullptr;
	size_t dumpCallLen = 0;
	int dumpCall = -1;
	if (_dupenv_s(&dumpCallEnv, &dumpCallLen, "TOMO_DEBUG_SLOT_DUMP_CALL") == 0 && dumpCallEnv != nullptr) {
		dumpCall = std::atoi(dumpCallEnv);
		free(dumpCallEnv);
	}
	if (dumpCall == callNo && _dupenv_s(&dumpDir, &dumpDirLen, "TOMO_DEBUG_SLOT_DUMP_DIR") == 0 && dumpDir != nullptr) {
		char fname[1024];
		std::snprintf(fname, sizeof(fname), "%s\\slot_CUDA_%03d.csv", dumpDir, callNo);
		FILE* fp = nullptr;
		if (fopen_s(&fp, fname, "w") == 0 && fp != nullptr) {
			std::fprintf(fp, "slot,x,y,p,z,nz,type,cls\n");
			for (int slotID = 0; slotID < nSlot; slotID++) {
				int S_L = hostSlotData.cu_sNPxl[slotID];
				if (S_L > CU_SLOT_CAPACITY_16) S_L = CU_SLOT_CAPACITY_16;
				for (int p = 0; p < S_L; p++) {
					const int idx = slotID * CU_SLOT_CAPACITY_16 + p;
					const int z = hostSlotData.cu_sdZcrd[idx];
					const int nz = hostSlotData.cu_sdZnrm[idx];
					const int typ = hostSlotData.cu_sdType[idx];
					const int cls = (nz > 0) ? 1 : ((nz < 0) ? 2 : 0);
					std::fprintf(fp, "%d,%d,%d,%d,%d,%d,%d,%d\n", slotID, slotID % nVoxelX, slotID / nVoxelX, p, z, nz, typ, cls);
				}
			}
			std::fclose(fp);
		}
		free(dumpDir);
	}
	std::printf("TOMO_SLOT_INPUT CUDA call=%d ypr=%d nonempty=%lld pairable=%lld rows=%lld alCnt=%lld alZ=%lld beCnt=%lld beZ=%lld sideCnt=%lld allZ=%lld sat=%lld maxLen=%d\n",
		callNo, yprID, nonempty, pairable, rows, alCnt, alZ, beCnt, beZ, sideCnt, allZ, sat, maxLen);
	callNo++;
}
static bool tomoDebugPairOutputEnabled()
{
	char* env = nullptr;
	size_t envLen = 0;
	bool enabled = false;
	if (_dupenv_s(&env, &envLen, "TOMO_DEBUG_PAIR_OUTPUT") == 0 && env != nullptr) {
		enabled = (std::atoi(env) != 0);
		free(env);
	}
	return enabled;
}

static void tomoDebugPrintCudaPairOutput(SlotDataIterator sdIt, SlotData& hostSlotData, int nSlot, int nVoxelX)
{
	static int callNo = 0;
	if (!tomoDebugPairOutputEnabled()) { callNo++; return; }

	cudaStreamSynchronize(sdIt->stream); cudaCheckError();
	sdIt->ReadPxls(hostSlotData.cu_sNPxl, hostSlotData.cu_sdType, hostSlotData.cu_sdZcrd, hostSlotData.cu_sdZnrm);
	cudaMemcpy(hostSlotData.cu_sVo, (void*)sdIt->cu_sVo, sizeof(CU_SLOT_BUFFER_TYPE) * nSlot, cudaMemcpyDeviceToHost); cudaCheckError();
	cudaMemcpy(hostSlotData.cu_sVss, (void*)sdIt->cu_sVss, sizeof(CU_SLOT_BUFFER_TYPE) * nSlot, cudaMemcpyDeviceToHost); cudaCheckError();

	long long voSum = 0, vssSum = 0, nonzeroVo = 0, nonzeroVss = 0;
	for (int slotID = 0; slotID < nSlot; slotID++) {
		int vo = hostSlotData.cu_sVo[slotID];
		int vss = hostSlotData.cu_sVss[slotID];
		voSum += vo;
		vssSum += vss;
		if (vo != 0) nonzeroVo++;
		if (vss != 0) nonzeroVss++;
	}

	char* dumpCallEnv = nullptr;
	size_t dumpCallLen = 0;
	int dumpCall = -1;
	if (_dupenv_s(&dumpCallEnv, &dumpCallLen, "TOMO_DEBUG_PAIR_DUMP_CALL") == 0 && dumpCallEnv != nullptr) {
		dumpCall = std::atoi(dumpCallEnv);
		free(dumpCallEnv);
	}
	char* dumpDir = nullptr;
	size_t dumpDirLen = 0;
	if (dumpCall == callNo && _dupenv_s(&dumpDir, &dumpDirLen, "TOMO_DEBUG_PAIR_DUMP_DIR") == 0 && dumpDir != nullptr) {
		char fname[1024];
		std::snprintf(fname, sizeof(fname), "%s\\pair_CUDA_%03d.csv", dumpDir, callNo);
		FILE* fp = nullptr;
		if (fopen_s(&fp, fname, "w") == 0 && fp != nullptr) {
			std::fprintf(fp, "slot,x,y,n,vo,vss,p,z,nz,type\n");
			for (int slotID = 0; slotID < nSlot; slotID++) {
				int S_L = hostSlotData.cu_sNPxl[slotID];
				if (S_L > CU_SLOT_CAPACITY_16) S_L = CU_SLOT_CAPACITY_16;
				int vo = hostSlotData.cu_sVo[slotID];
				int vss = hostSlotData.cu_sVss[slotID];
				std::fprintf(fp, "%d,%d,%d,%d,%d,%d,-1,0,0,0\n", slotID, slotID % nVoxelX, slotID / nVoxelX, S_L, vo, vss);
				for (int p = 0; p < S_L; p++) {
					const int idx = slotID * CU_SLOT_CAPACITY_16 + p;
					const int typ = hostSlotData.cu_sdType[idx];
					const int z = hostSlotData.cu_sdZcrd[idx];
					const int nz = hostSlotData.cu_sdZnrm[idx];
					std::fprintf(fp, "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n", slotID, slotID % nVoxelX, slotID / nVoxelX, S_L, vo, vss, p, z, nz, typ);
				}
			}
			std::fclose(fp);
		}
		free(dumpDir);
	}

	std::printf("TOMO_PAIR_OUTPUT CUDA call=%d vo=%lld vss=%lld nonzeroVo=%lld nonzeroVss=%lld\n",
		callNo, voSum, vssSum, nonzeroVo, nonzeroVss);
	callNo++;
}
__host__ STomoSh_CUDA::STomoSh_CUDA() : STomoSh_Base()
{
}

__host__ STomoSh_CUDA::~STomoSh_CUDA()
{
	Reset();
}

__host__ STomoSh_CUDA::STomoSh_CUDA(const STomoSh_CUDA& Source)
{
	Init();
	_Copy(Source);
}

__host__ void	STomoSh_CUDA::operator=(const STomoSh_CUDA& Source)
{
	Reset();
	_Copy(Source);
}

__host__ void	STomoSh_CUDA::_Copy(const STomoSh_CUDA& Source)
{
	STomoSh_Base::_Copy(Source);
	memcpy(iData, Source.iData, siData);//params.
	memcpy(cu_fpData, Source.cu_fpData, cu_sfpData);//GPU mem
	bWriteBackPxlsForRendering = Source.bWriteBackPxlsForRendering;
}

__host__ void	STomoSh_CUDA::Reset(void)
{
	STomoSh_Base::Reset();
}

__host__ void	STomoSh_CUDA::Init(void)
{
	STomoSh_Base::Init();
	memset(iData, 0x00, siData);//params.
	memset(cu_fpData, 0x00, cu_sfpData);//GPU mem

	nStream = 1;
	bWriteBackPxlsForRendering = true;
	cu_parentHit = nullptr;
	cu_parentFallbackTri = nullptr;
	cudaFree((void*)cu_Tri0); cu_Tri0 = nullptr;
	cudaFree((void*)cu_Vtx0); cu_Vtx0 = nullptr;
	cudaFree((void*)cu_VtxNrm0); cu_VtxNrm0 = nullptr;
}

__host__ void  STomoSh_CUDA::initCudaMem(void)
{
	if(printer_info.bVerbose) cu_startTimer();

	cudaError_t cudaStatus = cudaSetDevice(0); cudaCheckError();

	unsigned long int uliSlotSize = s_nSlot * nWorksInBatch;
	unsigned long int uliSlotDataSize = s_nSlotData * nWorksInBatch;

	//cpu memroy - as 1D, pinned
	cpu_SlotData.Reset();
	cpu_SlotData.bDevice = false;
	cpu_SlotData.Malloc(nSlot);

	//gpu memory
	gpu_SlotDataVec.clear();
	for( int s = 0 ; s < nWorksInBatch ; s++)
	{
		SlotData sd;		
		sd.Malloc( nSlot);
		gpu_SlotDataVec.push_back(sd);
	}


#ifndef _CUDA_USE_ROTATE_AND_PIXELIZE_IN_ONE_STEP
	cudaMalloc((void**)&cu_FlatTri1, s_nFlatTri * nYPR);		cudaCheckError();
	cudaMemsetAsync(cu_FlatTri1, 0x00, s_nFlatTri * nYPR);	cudaCheckError();//not necessary. for debug
#endif

#ifndef _CUDA_USE_MULTI_STREAM
	cudaMalloc((void**)&cu_FlatTri0,	s_nFlatTri);			cudaCheckError();
	cudaMalloc((void**)&cu_m4x3,			s_m4x3 * nYPR);					cudaCheckError();
	cudaMemcpy(cu_FlatTri0,	printer_info.pFlatTri,	s_nFlatTri,	cudaMemcpyHostToDevice); cudaCheckError();//Time Consuming!!
	cudaMemcpy(cu_m4x3,			printer_info.YPR_m4x3,	s_m4x3 * nYPR,			cudaMemcpyHostToDevice); cudaCheckError();
#endif

	if(printer_info.bVerbose) cu_endTimer("CUDA init() ");
}

__host__ void  STomoSh_CUDA::clearCudaMem(void)
{
	for( auto& sd : gpu_SlotDataVec)	{		sd.Free( );	}
	cpu_SlotData.Free();
	cudaFree((void*)cu_parentHit);
	cu_parentHit = nullptr;
	cudaFree((void*)cu_parentFallbackTri);
	cu_parentFallbackTri = nullptr;
	cudaFree((void*)cu_Tri0); cu_Tri0 = nullptr;
	cudaFree((void*)cu_Vtx0); cu_Vtx0 = nullptr;
	cudaFree((void*)cu_VtxNrm0); cu_VtxNrm0 = nullptr;

	cudaFree((void*)cu_FlatTri0);
	cudaFree((void*)cu_m4x3);

#ifndef _CUDA_USE_ROTATE_AND_PIXELIZE_IN_ONE_STEP
	cudaFree(cu_FlatTri1);
#endif
	
}

#include "../cpu_src/STomoPixel.h"
__host__ FLOAT32* STomoSh_CUDA::ReadPxls(int wrkID, int* _nData2i, INT16** _pData2i)
{
	unsigned long uliSlotIdx = wrkID * s_nSlot;
	unsigned long uliSlotDataIdx = wrkID * s_nSlotData;

	gpu_SlotDataVec.at(wrkID).ReadPxls( 
		cpu_SlotData.cu_sNPxl, 
		cpu_SlotData.cu_sdType, 
		cpu_SlotData.cu_sdZcrd, 
		cpu_SlotData.cu_sdZnrm);

	//for rendering(time-consuming)
	TPVector pxls[(int)enumPixelType::eptNumberOfSubPixels];
	vm_info.Va = vm_info.Vb = vm_info.Vss = 0;
	for (int slot_id = 0; slot_id < nSlot; slot_id++)
	{
		int p_x = slot_id % (nVoxelX);
		int p_y = slot_id / (nVoxelX);
		int S_L = cpu_SlotData.cu_sNPxl[slot_id];

		int ss_start_z = -1, ss_end_z = -1;//position of support structure segment
		for (int slotdata_id = 0; slotdata_id < S_L; slotdata_id++)
		{
			int p_z			= cpu_SlotData.cu_sdZcrd[slot_id * CU_SLOT_CAPACITY_16 + slotdata_id];
			int p_nZ		= cpu_SlotData.cu_sdZnrm[slot_id * CU_SLOT_CAPACITY_16 + slotdata_id];
			int p_type	= cpu_SlotData.cu_sdType[slot_id * CU_SLOT_CAPACITY_16 + slotdata_id];
			STomoPixel new_pxl(p_x, p_y, p_z, 0, 0, p_nZ, p_type);
			if (p_type & typeAl)
			{
				pxls[(int)enumPixelType::eptAl].push_back(new_pxl);
				vm_info.Va += p_z;
			}
			if (p_type & typeSSA)
			{
				pxls[(int)enumPixelType::eptSSA].push_back(new_pxl);
				vm_info.Vss -= p_z; ss_end_z = p_z; 
			}
			if (p_type & typeBe)
			{
				pxls[(int)enumPixelType::eptBe].push_back(new_pxl);
				vm_info.Vb += p_z;
			}
			if (p_type & typeSSB)
			{
				pxls[(int)enumPixelType::eptSSB].push_back(new_pxl);
				vm_info.Vss += p_z; ss_start_z = p_z;
			}
			if (p_type & typeBed)
			{
				pxls[(int)enumPixelType::eptBed].push_back(new_pxl);
				vm_info.Vbed += p_z;
			}

#if 1
			if(ss_start_z > -1 && ss_end_z > -1 && ss_start_z > ss_end_z)//������, ���� ����.
			{
				for(int z = ss_start_z ; z >= ss_end_z ; z--)
				{
					STomoPixel ss_pxl(p_x, p_y, z, typeSS, 0, 0);
					pxls[(int)enumPixelType::eptSS].push_back(ss_pxl);
				}
				ss_start_z = -1; ss_end_z = -1;
			}
#endif
		}

	}

#ifdef _DEBUG
	if(1)
	{
		int _n_Va = pxls[(int)enumPixelType::eptAl].size();
		int _n_Vb = pxls[(int)enumPixelType::eptBe].size();
	}
#endif

	if(_nData2i==nullptr) return nullptr;

	for (size_t pt = 0; pt < (int)enumPixelType::eptNumberOfSubPixels; pt++)
	{
		size_t n_pxl = pxls[pt].size();
		_nData2i[pt] = n_pxl;
		_pData2i[pt] = new INT16[n_pxl * g_nPixelFormat + 2];
		for (int p = 0; p < n_pxl; p++)
		{
			pxls[pt].at(p).DumpTo(_pData2i[pt] + p * g_nPixelFormat);
		}
	}

	//debug - cehck YPR rotation matrix 
	FLOAT32* rotated_pFlatTri = nullptr;
	return rotated_pFlatTri;
}




//**********************************************************************************************
//
//	concurrent stream version
// 
//**********************************************************************************************
__host__ void	STomoSh_CUDA::getBatchNumber(void)
{
	cudaDeviceProp prop;
	cudaGetDeviceProperties( &prop, 0);
	if(prop.asyncEngineCount == 0)//CUDA 13: 'deviceOverlap' was removed; asyncEngineCount>0 is the equivalent check.
	{
		std::cout<< "ERROR: device copy/exec overlap not supported" << std::endl;
	}
	
	if(printer_info.bVerbose) std::cout<< "CUDA compute capability=" << prop.major << "."<< prop.minor << std::endl;

	nMultiProcessor = prop.multiProcessorCount;
	nMaxThreadPerMP = prop.maxThreadsPerMultiProcessor;
	nMaxThreads			= nMultiProcessor * nMaxThreadPerMP;
	nMaxConcurrentStream = 8;//ToDo: API?

	//nStream = nMultiProcessor;//<= nMaxConcurrentStream
	if(nYPR >1) 	{	nWorksInBatch = nStream = min((int)nMultiProcessor, (int)nMaxConcurrentStream);}
	else	{	nWorksInBatch = nStream = 1;}

	const char* env_streams = std::getenv("TOMO_CUDA_STREAMS");
	if(env_streams != nullptr)
	{
		int forcedStreams = atoi(env_streams);
		if(forcedStreams > 0)
		{
			nStream = nWorksInBatch = min(forcedStreams, (int)nStream);
		}
	}
}

__host__ void	STomoSh_CUDA::Init_CUDA(void)
{
	clearCudaMem();

	nFlatTri	= printer_info.nFlatTri; 
	nYPR			= printer_info.nYPR;
	nVoxelY		= nVoxelX = printer_info.nVoxel;
	nSlot			= nVoxelX * nVoxelY;
	nSlotData	= nSlot * CU_SLOT_CAPACITY_16;

	s_nSlot			= sizeof(CU_SLOT_BUFFER_TYPE) * nSlot;
	s_nSlotData = sizeof(CU_SLOT_BUFFER_TYPE) * nSlotData;
	s_nFlatTri	= sizeof(float) * nFlatTri * nFlatTriInfoSize;
	s_m4x3			= sizeof(float) * CU_MATRIX_SIZE_12;

	getBatchNumber();
	initCudaMem();
}

#ifdef _CUDA_USE_SERIALIZED_VO_VSS_MEMORY
void	 STomoSh_CUDA::__Malloc_Serialized_Vo_Vss_memory(void)
{
	for(int s = 0 ; s < nStream ; s++)
	{
		SlotDataIterator sdIt = gpu_SlotDataVec.begin() + s;
		cudaFree(sdIt->cu_sVo);
		cudaFree(sdIt->cu_sVss);
	}

	CU_SLOT_BUFFER_TYPE *cu_buf = 0;
	cudaMalloc( (void**)&cu_buf,				sizeof(CU_SLOT_BUFFER_TYPE) * nSlot * 2* nStream);	cudaCheckError();
	for(int s = 0 ; s < nStream ; s++)
	{
		SlotDataIterator sdIt = gpu_SlotDataVec.begin() + s;
		sdIt->cu_sVo  = cu_buf + nSlot * (2* s + 0);
		sdIt->cu_sVss = cu_buf + nSlot * (2* s + 1);
	}
}

void	 STomoSh_CUDA::__Free_Serialized_Vo_Vss_memory(void)
{
	cudaFree( gpu_SlotDataVec.begin()->cu_sVo);
	for(int s = 0 ; s < nStream ; s++)
	{
		SlotDataIterator sdIt = gpu_SlotDataVec.begin() + s;
		sdIt->cu_sVo	= nullptr;
		sdIt->cu_sVss =  nullptr;
	}
}
#endif

__host__ void	STomoSh_CUDA::Run(float *_Mo, float *_Mss, int ypr_id_to_start)
{
	Init_CUDA();	

	if(printer_info.bVerbose)	{		std::cout << "nStream= " << nStream <<" , nWorksInBatch=" << nWorksInBatch<< std::endl;	}

	//send tri data to gpu
	unsigned long int uliSlotSize			= s_nSlot * nStream;
	unsigned long int uliSlotDataSize = s_nSlotData * nStream;
	cudaMalloc((void**)&cu_FlatTri0,		s_nFlatTri	* nStream);	cudaCheckError();
	cudaMalloc((void**)&cu_m4x3,				s_m4x3*nYPR	* nStream);	cudaCheckError();
	cudaMalloc((void**)&cu_parentHit,	sizeof(int) * printer_info.nTri * nStream);	cudaCheckError();
	cudaMalloc((void**)&cu_parentFallbackTri, sizeof(float) * printer_info.nTri * nParentFallbackInfoSize); cudaCheckError();
	cudaMalloc((void**)&cu_Tri0, sizeof(int) * printer_info.nTri * 3); cudaCheckError();
	cudaMalloc((void**)&cu_Vtx0, sizeof(float) * printer_info.nVtx * 3); cudaCheckError();
	cudaMalloc((void**)&cu_VtxNrm0, sizeof(float) * printer_info.nVtx * 3); cudaCheckError();

	cudaMalloc((void**)&cu_sum_buffer,	sizeof(int)* 2	* nStream);	cudaCheckError();//Step4_ReducedSum_Batch()�� ����� ��츦 ���� �˳��ϰ� ��´�.
	cudaMallocHost((void**)&sum_buffer,	sizeof(int)* 2	* nStream);	cudaCheckError();
	
#ifdef _CUDA_USE_SERIALIZED_VO_VSS_MEMORY
if(nYPR>1) __Malloc_Serialized_Vo_Vss_memory();
#endif

	cudaMemcpy(cu_FlatTri0,	printer_info.pFlatTri,	s_nFlatTri,			cudaMemcpyHostToDevice); cudaCheckError();
	cudaMemcpy(cu_parentFallbackTri, printer_info.pParentFallbackTri, sizeof(float) * printer_info.nTri * nParentFallbackInfoSize, cudaMemcpyHostToDevice); cudaCheckError();
	cudaMemcpy(cu_Tri0, printer_info.rpTri0, sizeof(int) * printer_info.nTri * 3, cudaMemcpyHostToDevice); cudaCheckError();
	cudaMemcpy(cu_Vtx0, printer_info.rpVtx0, sizeof(float) * printer_info.nVtx * 3, cudaMemcpyHostToDevice); cudaCheckError();
	cudaMemcpy(cu_VtxNrm0, printer_info.rpVtxNrm0, sizeof(float) * printer_info.nVtx * 3, cudaMemcpyHostToDevice); cudaCheckError();
	cudaMemcpy(cu_m4x3,			printer_info.YPR_m4x3,	s_m4x3 * nYPR,	cudaMemcpyHostToDevice); cudaCheckError();

	if(printer_info.bVerbose) cu_startTimer();

	for( auto& sd: gpu_SlotDataVec) 	{ 			sd.CreateStream(); }//cuda ��Ʈ�� ���� & �̺�Ʈ ���.

	cudaEvent_t last_event;
	for( int yprID = ypr_id_to_start; yprID < nYPR ; yprID += nStream)
	{
		for(int s = 0 ; s < nStream ; s++)		
		{
			if(yprID + s < nYPR)			
			{
				SlotDataIterator sdIt = gpu_SlotDataVec.begin() + s;
				Step1_RotateAndPixelize( sdIt, yprID + s);
				tomoDebugPrintCudaSlotInput(sdIt, cpu_SlotData, nSlot, nVoxelX, yprID + s);
				Step2_Pairing(sdIt);
				tomoDebugPrintCudaPairOutput(sdIt, cpu_SlotData, nSlot, nVoxelX);
				Step3_GenerateBed(sdIt);
#ifdef _CUDA_USE_REDUCED_SUM_BATCH
				cudaEventRecord( sdIt->event, sdIt->stream);	
#else		
				Step4_SlotSum( sdIt, cu_sum_buffer + 2 * s, sum_buffer + 2 * s, 	_Mo + yprID + s, _Mss + yprID + s);
#endif
			}
		}
#ifdef _CUDA_USE_REDUCED_SUM_BATCH
		Step4_SlotSum_Batch(yprID, _Mo, _Mss);//step1~3���� ����� Mo, Mss���� nStream�� �Ѳ����� �ջ��Ѵ�. 
#endif
	}
	cudaDeviceSynchronize(); cudaCheckError();
	if (printer_info.bVerbose) cu_endTimer("CUDA main loop: ");

	for( auto& sd: gpu_SlotDataVec) 	{ 			sd.DestroyStream(); }

#ifdef _CUDA_USE_SERIALIZED_VO_VSS_MEMORY
if(nYPR>1) __Free_Serialized_Vo_Vss_memory();
#endif
}


__host__ void STomoSh_CUDA::Step1_RotateAndPixelize( SlotDataIterator sdIt, int yprID_to_start)
{
	// Process one YPR orientation in the selected CUDA stream.
	static int tomoCudaTriHitCallNo = 0;
	int tomoThisTriHitCall = tomoCudaTriHitCallNo++;
	int problem_size = nFlatTri;
	int triBlockXY = printer_info.TriMaxDiameter + 1;
	int blocksize = 1024 / (triBlockXY * triBlockXY);
	if (blocksize < 1) blocksize = 1;
	if (blocksize > CU_TRI_PER_WORK) blocksize = CU_TRI_PER_WORK;
	int gridsize  = (problem_size + blocksize -1) / blocksize;
	const dim3 dgStep1( gridsize);//=nWorksPerBlocks
	const dim3 dbStep1(triBlockXY, triBlockXY, blocksize);// One block covers a small flat triangle AABB bounded by TriMaxDiameter.

	int triID_to_start = 0;//obsolete..
	int shell_z_offset = (printer_info.shell_thickness > g_fMARGIN) ? int(printer_info.shell_thickness + 0.999f) : 0;

	sdIt->SetZero();
	int streamID = int(sdIt - gpu_SlotDataVec.begin());
	int* streamParentHit = cu_parentHit + streamID * printer_info.nTri;
	cudaMemsetAsync(streamParentHit, 0, sizeof(int) * printer_info.nTri, sdIt->stream); cudaCheckError();

	const char* envOriginalTri = std::getenv("TOMO_CUDA_ORIGINAL_TRI_VOXELIZE");
	bool useOriginalTriVoxelizer = true;
	if (envOriginalTri != nullptr) useOriginalTriVoxelizer = (atoi(envOriginalTri) != 0);
	if (useOriginalTriVoxelizer)
	{
		const char* envWarpTri = std::getenv("TOMO_CUDA_WARP_TRI");
		bool useWarpPerTri = true;//warp-per-triangle rasterizer: same results, far less idle threads on ~10^6-face meshes
		int wptWarpsPerBlock = 4;//A/B on E3/E8 (RTX 5080): 2~8 all good, 4 best overall
		if (envWarpTri != nullptr)
		{
			const int v = atoi(envWarpTri);
			useWarpPerTri = (v != 0);
			if (v >= 2 && v <= 32) wptWarpsPerBlock = v;//A/B knob: warps per block
		}
		if (useWarpPerTri)
		{
			const dim3 dgWarp((printer_info.nTri + wptWarpsPerBlock - 1) / wptWarpsPerBlock);
			const dim3 dbWarp(wptWarpsPerBlock * 32);
			cu_rotVoxelOriginal_WarpPerTri << < dgWarp, dbWarp, 0, sdIt->stream >> > (
				nVoxelX, nYPR, printer_info.nTri, yprID_to_start,
				cu_m4x3 + 0 * CU_MATRIX_SIZE_12,
				cu_Tri0, cu_Vtx0, cu_VtxNrm0,
				streamParentHit,
				sdIt->cu_sNPxl,
				sdIt->cu_sdKey,
				sdIt->cu_sdTri,
				sdIt->cu_sdType,
				sdIt->cu_sdZcrd,
				sdIt->cu_sdZnrm,
				printer_info.bShellMesh,
				shell_z_offset); cudaCheckError();
		}
		else
		{
		const dim3 dgOrig(printer_info.nTri);
		const dim3 dbOrig(16, 16);
		cu_rotVoxelOriginal_Streamed_16x16 << < dgOrig, dbOrig, 0, sdIt->stream >> > (
			nVoxelX, nYPR, printer_info.nTri, yprID_to_start,
			cu_m4x3 + 0 * CU_MATRIX_SIZE_12,
			cu_Tri0, cu_Vtx0, cu_VtxNrm0,
			streamParentHit,
			sdIt->cu_sNPxl,
			sdIt->cu_sdKey,
			sdIt->cu_sdTri,
			sdIt->cu_sdType,
			sdIt->cu_sdZcrd,
			sdIt->cu_sdZnrm,
			printer_info.bShellMesh,
			shell_z_offset); cudaCheckError();
		}
		Step1_TruncateSlots(sdIt);
		char* tomoTriHitCallEnv = nullptr;
		char* tomoTriHitDirEnv = nullptr;
		size_t tomoTriHitEnvLen = 0;
		int tomoTriHitTarget = -1;
		if (_dupenv_s(&tomoTriHitCallEnv, &tomoTriHitEnvLen, "TOMO_DEBUG_TRI_HIT_CALL") == 0 && tomoTriHitCallEnv != nullptr) {
			tomoTriHitTarget = std::atoi(tomoTriHitCallEnv);
			free(tomoTriHitCallEnv);
		}
		if (tomoTriHitTarget == tomoThisTriHitCall) {
			cudaStreamSynchronize(sdIt->stream); cudaCheckError();
			int* hostTriHit = new int[printer_info.nTri];
			cudaMemcpy(hostTriHit, streamParentHit, sizeof(int) * printer_info.nTri, cudaMemcpyDeviceToHost); cudaCheckError();
			const char* tomoTriHitDir = ".";
			if (_dupenv_s(&tomoTriHitDirEnv, &tomoTriHitEnvLen, "TOMO_DEBUG_TRI_HIT_DIR") == 0 && tomoTriHitDirEnv != nullptr) {
				tomoTriHitDir = tomoTriHitDirEnv;
			}
			char tomoTriHitPath[1024];
			std::snprintf(tomoTriHitPath, sizeof(tomoTriHitPath), "%s\\trihit_CUDA_%03d.csv", tomoTriHitDir, tomoThisTriHitCall);
			FILE* tomoTriHitFile = nullptr;
			fopen_s(&tomoTriHitFile, tomoTriHitPath, "w");
			if (tomoTriHitFile != nullptr) {
				std::fprintf(tomoTriHitFile, "tri,hits,x0,y0,x1,y1,x2,y2\n");
								FLOAT32* m = printer_info.YPR_m4x3 + yprID_to_start * CU_MATRIX_SIZE_12;
				for (int t = 0; t < printer_info.nTri; t++) {
					FLOAT32 xy[6];
					for (int k = 0; k < 3; k++) {
						int vid = printer_info.rpTri0[t * 3 + k];
						FLOAT32* v = printer_info.rpVtx0 + vid * 3;
						xy[k * 2 + 0] = m[0] * v[0] + m[1] * v[1] + m[2] * v[2] + m[3];
						xy[k * 2 + 1] = m[4] * v[0] + m[5] * v[1] + m[6] * v[2] + m[7];
					}
					std::fprintf(tomoTriHitFile, "%d,%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n", t, hostTriHit[t], xy[0], xy[1], xy[2], xy[3], xy[4], xy[5]);
				}
				fclose(tomoTriHitFile);
			}
			if (tomoTriHitDirEnv != nullptr) free(tomoTriHitDirEnv);
			delete[] hostTriHit;
		}
		return;
	}

	cu_rotVoxel_Streamed_16x16 << < dgStep1, dbStep1, 0, sdIt->stream >> > (
					nVoxelX, nYPR, nFlatTri,	//constants
					yprID_to_start,			//variables
					triID_to_start,
					cu_m4x3					+ 0 * CU_MATRIX_SIZE_12, //input data
					cu_FlatTri0			+ 0 * nFlatTri,
					streamParentHit,
					sdIt->cu_sNPxl,
					sdIt->cu_sdKey,
					sdIt->cu_sdTri,
					sdIt->cu_sdType,
					sdIt->cu_sdZcrd,
					sdIt->cu_sdZnrm,
		printer_info.bShellMesh,
		shell_z_offset); cudaCheckError();

	const int fbBlock = 256;
	const int fbGrid = (printer_info.nTri + fbBlock - 1) / fbBlock;
	cu_rotVoxelFallback_Streamed_1d << < fbGrid, fbBlock, 0, sdIt->stream >> > (
					nVoxelX, nYPR, printer_info.nTri, yprID_to_start,
					cu_m4x3 + 0 * CU_MATRIX_SIZE_12,
					cu_parentFallbackTri,
					streamParentHit,
					sdIt->cu_sNPxl,
					sdIt->cu_sdKey,
					sdIt->cu_sdTri,
					sdIt->cu_sdType,
					sdIt->cu_sdZcrd,
					sdIt->cu_sdZnrm,
					printer_info.bShellMesh,
					shell_z_offset); cudaCheckError();
	Step1_TruncateSlots(sdIt);
}

__host__ void STomoSh_CUDA::Step1_TruncateSlots(SlotDataIterator sdIt)
{
	//deterministically keep the CU_SLOT_TRUNCATE_TO largest (z,nZ) keys per slot (CPU-capacity regime)
	if (CU_SLOT_TRUNCATE_TO >= CU_SLOT_CAPACITY_16) return;
	const int threads = 256;
	const int blocks = (nSlot + threads - 1) / threads;
	cu_truncateSlots << < blocks, threads, 0, sdIt->stream >> > (
					nSlot, CU_SLOT_TRUNCATE_TO,
					sdIt->cu_sNPxl,
					sdIt->cu_sdKey,
					sdIt->cu_sdTri,
					sdIt->cu_sdType,
					sdIt->cu_sdZcrd,
					sdIt->cu_sdZnrm); cudaCheckError();
}
__host__ void  STomoSh_CUDA::Step2_Pairing(SlotDataIterator sdIt)
{
	int sin_theta_c_x1000 = - sin(printer_info.theta_c) * 1000.;//SS critical angle condition

	int problem_size = nSlot;
	int blocksize = CU_SLOTS_PER_WORK;
	int gridsize  = (problem_size + blocksize -1) / blocksize;
	const dim3 dgStep2( gridsize);
	const dim3 dbStep2( CU_SLOT_CAPACITY_16, blocksize);

	cu_slotPairing_Streamed<CU_SLOT_BUFFER_TYPE> << < dgStep2, dbStep2, 0, sdIt->stream>> > (
				nSlot, descendingOrder, sin_theta_c_x1000,//constants
				bWriteBackPxlsForRendering, printer_info.bUseExplicitSS,//variables
				sdIt->cu_sNPxl, //input & output
				sdIt->cu_sVo, 
				sdIt->cu_sVss,
				sdIt->cu_sdType, 
				sdIt->cu_sdZcrd,
				sdIt->cu_sdZnrm);cudaCheckError();
}


__host__ void	STomoSh_CUDA::Step4_SlotSum(SlotDataIterator sdIt, int *_cu_reduced_sum_buffer, int *_reduced_sum_buffer, float *_Mo , float *_Mss)
{
	cudaMemsetAsync(_cu_reduced_sum_buffer, 0, sizeof(int) * 2 * 1, sdIt->stream);
	reducedSum_Streamed(nSlot, (int*)sdIt->cu_sVo, sdIt->stream, _cu_reduced_sum_buffer);
	reducedSum_Streamed(nSlot, (int*)sdIt->cu_sVss, sdIt->stream, _cu_reduced_sum_buffer + 1);
	cudaMemcpy(_reduced_sum_buffer, _cu_reduced_sum_buffer, sizeof(int) * 2, cudaMemcpyDeviceToHost); cudaCheckError();

	vm_info.Vo = *(_reduced_sum_buffer + 0);
	vm_info.Vss = *(_reduced_sum_buffer + 1);
	vm_info.VolToMass(printer_info);
	if(_Mo !=nullptr) *(_Mo) = vm_info.Mo;
	if(_Mss != nullptr) *(_Mss) = vm_info.Mss;
}

__host__ void	STomoSh_CUDA::Step4_SlotSum_Batch(int yprID, float *_Mo, float *_Mss) 
{
	if(_Mss==nullptr) return;

#if defined( _CUDA_USE_SERIALIZED_VO_VSS_MEMORY)
cudaMemset( cu_reduced_sum_buffer, 0, sizeof(int) * 2 * nStream);
reducedSum_2d( nStream * 2, nSlot, gpu_SlotDataVec.begin()->cu_sVo, cu_reduced_sum_buffer);
cudaMemcpy( reduced_sum_buffer,  cu_reduced_sum_buffer, sizeof(int) * 2 * nStream, cudaMemcpyDeviceToHost); cudaCheckError();

		for(int s = 0 ; s < nStream ; s++)
		{
			if(yprID + s < nYPR)
			{
				vm_info.Vo  = reduced_sum_buffer[2 * s];
				vm_info.Vss = reduced_sum_buffer[2 * s + 1];
				vm_info.VolToMass(printer_info);
				*(_Mo  + yprID + s) = vm_info.Mo;
				*(_Mss + yprID + s) = vm_info.Mss;
			}
		}

#elif defined( _CUDA_USE_MULTI_STREAM)
		//����� ������ Vo_stream, Vss_stream�� ����Ѵ�. 
#ifdef _CUDA_USE_REDUCED_SUM_BATCH
		 // reduction outputs are cleared in their own streams below
#endif
		for(int s = 0 ; s < nStream ; s++)
		{
			if(yprID + s < nYPR)
			{
				SlotDataIterator sdIt = gpu_SlotDataVec.begin() + s;
#ifdef _CUDA_USE_REDUCED_SUM_BATCH
				cudaStreamWaitEvent(sdIt->Vo_stream, sdIt->event);
				cudaStreamWaitEvent(sdIt->Vss_stream, sdIt->event);
				cudaMemsetAsync(cu_sum_buffer + 2 * s, 0, sizeof(int), sdIt->Vo_stream); cudaCheckError();
				cudaMemsetAsync(cu_sum_buffer + 2 * s + 1, 0, sizeof(int), sdIt->Vss_stream); cudaCheckError();
				reducedSum_Streamed(nSlot, (int*) sdIt->cu_sVo , sdIt->Vo_stream, cu_sum_buffer + 2 * s);
				reducedSum_Streamed(nSlot, (int*) sdIt->cu_sVss, sdIt->Vss_stream, cu_sum_buffer + 2 * s + 1);
#endif
			}
		}
#ifdef _CUDA_USE_REDUCED_SUM_BATCH
#endif
		cudaMemcpy( sum_buffer,  cu_sum_buffer, sizeof(int) * 2 * nStream, cudaMemcpyDeviceToHost); cudaCheckError();

		for(int s = 0 ; s < nStream ; s++)
		{
			if(yprID + s < nYPR)
			{
				vm_info.Vo  = sum_buffer[2 * s];
				vm_info.Vss = sum_buffer[2 * s + 1];
				vm_info.VolToMass(printer_info);
				*(_Mo  + yprID + s) = vm_info.Mo;
				*(_Mss + yprID + s) = vm_info.Mss;
			}
		}

#else
		for(int s = 0 ; s < nStream ; s++)
		{
			if(yprID + s < nYPR)
			{
				vm_info.Vo  = reducedSum(nSlot, (int*) gpu_SlotDataVec.at(s).cu_sVo);
				vm_info.Vss = reducedSum(nSlot,	(int*) gpu_SlotDataVec.at(s).cu_sVss);
				vm_info.VolToMass(printer_info);
				*(_Mo  + yprID + s) = vm_info.Mo;
				*(_Mss + yprID + s) = vm_info.Mss;
			}
		}

#endif
}


//----------------------------------------------------------------------------------------------
//
//	bed structure
// 
//----------------------------------------------------------------------------------------------

__host__ void  STomoSh_CUDA::Step3_GenerateBed(SlotDataIterator sdIt)
{

	const char* skip_bed = std::getenv("TOMO_CUDA_SKIP_BED");
	if(skip_bed != nullptr && atoi(skip_bed) != 0) return;
	if(printer_info.BedType == enumBedType::ebtNone) return;

	int threads = 256;
	int blocks = min( (int)(nSlot + threads - 1) / threads, 2048);
	const dim3 dgStep3(	blocks);
	const dim3 dbStep3(threads);

	cu_genBed<< < dgStep3, dbStep3, 0, sdIt->stream >> > (
							nVoxelX, nSlot, //constants
							printer_info.BedType, printer_info.BedOuterBound, printer_info.BedInnerBound, printer_info.BedThickness,//bed parameter
							sdIt->cu_sNPxl,			//slot data
							sdIt->cu_sdType,
							sdIt->cu_sdZcrd,
							sdIt->cu_sdZnrm,
							sdIt->cu_sVo,
							sdIt->cu_sVss); cudaCheckError();
}
