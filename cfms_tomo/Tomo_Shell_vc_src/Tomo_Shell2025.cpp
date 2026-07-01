// TomoShC_Win32.cpp : Defines the exported functions for the DLL.

#include "pch.h"
#include "framework.h"
#include "Tomo_Shell2025.h"
#include "cpu_src\SMatrix4f.h"
#include "cpu_src\STomoPixel.h"
#include "cpu_src\STPSlot.h"
#include "cpu_src\STomoSh_TMPxl.h"
#include "cpu_src\STomoSh_INT3.h"
#include "cuda_src\STomoSh_CUDA.cuh"

#include <algorithm>  // std::find_if
#include <thread>
#include <iostream>//std::cout
#include <cstdlib>


//global variables
FLOAT32** vtx = nullptr;
FLOAT32** nrm = nullptr;
INT16  ** tri = nullptr;
INT16 nV = 0;
INT16 nT = 0;
INT16 n_pxls = 0;
MESH_ELE_ID_TYPE*  nData2i = nullptr;
INT16** pData2i = nullptr;
FLOAT32* Mss = nullptr;
FLOAT32* Mo = nullptr;
FLOAT32* Vtc = nullptr;//debug. for p-orbital test
FLOAT32* g_mat4x4 = nullptr;
bool  g_bUseExplicitSS = false;
STomoVolMassInfo VolMassInfo;

TPVector al_pxls, be_pxls, TC_pxls, NVB_pxls, NVA_pxls, Vo_pxls, Vss_pxls, SS_pxls, SSB_pxls, SSA_pxls, Bed_pxls;

using namespace Tomo;

inline FLOAT32 toRadian(INT16 a) { return a * 3.141592 / 180.; }

FLOAT32* identity4x4(void)
{
	FLOAT32 *mat = new FLOAT32[4*4];
	memset(mat, 0x00, sizeof(FLOAT32) * 16);
	mat[0] = mat[4] = mat[8] = mat[12] = 1.;
	return mat;
}


INT16* pxlsToDat2i(TPVector& pxls, MESH_ELE_ID_TYPE& n_pxl)
{
	n_pxl = pxls.size();
	if(n_pxl<=0) return nullptr;

	INT16* _Data2i = new INT16[n_pxl * g_nPixelFormat];
	memset(_Data2i, 0x00, sizeof(INT16) * n_pxl * g_nPixelFormat);
	MESH_ELE_ID_TYPE p = 0;
	for (TPIterator pIt = pxls.begin(); pIt != pxls.end(); ++pIt, ++p)
	{
		pIt->DumpTo(_Data2i + p * g_nPixelFormat);
	}
	return _Data2i;
}

INT16*       getpData2i(Tomo::enumPixelType iSubPixel) { return ::pData2i[static_cast<int>(iSubPixel)];}
MESH_ELE_ID_TYPE  getnData2i(Tomo::enumPixelType iSubPixel) { return ::nData2i[static_cast<int>(iSubPixel)];}
FLOAT32* getMss(void) { return ::Mss;}
FLOAT32* getMo(void)  { return ::Mo; }
FLOAT32* getVtc(void) { return ::Vtc; }
FLOAT32* getVolMassInfo(void) { 	return ::VolMassInfo.dData; }
FLOAT32* getMat4x4(void) { return ::g_mat4x4;}

void  OnDestroy(void)
{
	if(pData2i!=nullptr)
	{
		for (int i = 0; i < static_cast<int>(enumPixelType::eptNumberOfSubPixels); i++)    {      if(pData2i[i] != nullptr) delete[] pData2i[i];    }
		delete[] pData2i;    pData2i = nullptr;
	}
	vtx = nullptr;  nrm = nullptr;  tri = nullptr;
	if (Mss != nullptr) { delete[] Mss;  Mss = nullptr;  }
	if (Mo != nullptr)  { delete[] Mo;   Mo = nullptr; }
	if (Vtc != nullptr) { delete[] Vtc;  Vtc = nullptr; }
	if(g_mat4x4!=nullptr) { delete[] g_mat4x4; g_mat4x4 = nullptr;}

	cudaDeviceReset();
}

MESH_ELE_ID_TYPE _find1stOptimal(MESH_ELE_ID_TYPE _nData, FLOAT32* _pData)
{
	if(_nData<=1) return 0;

	MESH_ELE_ID_TYPE min_index = 0;
	FLOAT32 min_value = FLOAT32( 1e5);
	for (MESH_ELE_ID_TYPE i = 0; i < _nData; i++)  {  if (_pData[i] < min_value)  { min_value = _pData[i]; min_index = i;  }  }
	return min_index;
}

template <typename T> void thread_func(T* _pNV, int thread_id, FLOAT32* _YPR, int ypr_id)
{
	T* nv = _pNV + thread_id;

	S3DPrinterInfo& info = nv->printer_info;
	info.yaw = _YPR[ypr_id * 3 + 0];//YPR data is input here.
	info.pitch = _YPR[ypr_id * 3 + 1];
	info.roll = _YPR[ypr_id * 3 + 2];

	nv->Rotate();
	nv->Pixelize();
	nv->Pairing();
	nv->GenerateBed();
	nv->Calculate();

	Mo[ypr_id] = nv->vm_info.Mo;
	Mss[ypr_id] = nv->vm_info.Mss;
	Vtc[ypr_id] = nv->vm_info.Vtc;
}

template <class T>
MESH_ELE_ID_TYPE  _TomoSh_Function_Call(
	FLOAT32* _float32_info_x12,
	MESH_ELE_ID_TYPE* _int32_info_x11,
	FLOAT32* _YPR,
	MESH_ELE_ID_TYPE* _tri,
	FLOAT32* _vtx,
	FLOAT32* _vtx_nrm,
	FLOAT32* _tri_nrm,
	MESH_ELE_ID_TYPE* _chull_tri,
	FLOAT32* _cvhull_vtx,
	FLOAT32* _chull_trinrm
)
{
	startTimer();

	#ifdef _DEBUG
	std::cout << "Warning:: __DEBUG__MODE__";
	#endif

	S3DPrinterInfo info(_float32_info_x12, _int32_info_x11, _tri, _vtx, _vtx_nrm, _tri_nrm, _chull_tri, _cvhull_vtx, _chull_trinrm, 0, 0, 0);//takes some memory.

#ifdef _USE_CUDA_FOR_TOMONV
  bool useCpuFlatDebug = false;
  char* envCpuFlat = nullptr;
  size_t envCpuFlatLen = 0;
  if (_dupenv_s(&envCpuFlat, &envCpuFlatLen, "TOMO_CPU_FLAT_TRI") == 0 && envCpuFlat != nullptr) {
    useCpuFlatDebug = (std::atoi(envCpuFlat) != 0);
    free(envCpuFlat);
  }
#endif

	Mss = new FLOAT32[info.nYPR + 2];
	Mo = new FLOAT32[info.nYPR + 2];
	Vtc = new FLOAT32[info.nYPR + 2];

	//mult-thread info.
	const auto processor_count = std::thread::hardware_concurrency();
	int nThread = min(processor_count, info.nYPR);
	char* envCpuThreads = nullptr;
	size_t envCpuThreadsLen = 0;
	if (_dupenv_s(&envCpuThreads, &envCpuThreadsLen, "TOMO_CPU_THREADS") == 0 && envCpuThreads != nullptr) {
		const int forcedCpuThreads = std::atoi(envCpuThreads);
		if (forcedCpuThreads > 0) { nThread = min(forcedCpuThreads, info.nYPR); }
		free(envCpuThreads);
	}
	int nBlock = info.nYPR / nThread;
	int nBlRest = info.nYPR % nThread;

		T *pNV = new T[nThread +2];

	for (int thread_id = 0; thread_id < nThread; thread_id++)
	{
		pNV[thread_id].printer_info  = info;
#ifdef _USE_CUDA_FOR_TOMONV
		if (useCpuFlatDebug) { pNV[thread_id].printer_info.SetMaxTriDiameter(); }
#endif
	}


#ifdef _DEBUG
	//non-threaded version
	int ypr_id = 0;
	for (int b = 0; b < nBlock; b++)
	{
		for (int thread_id = 0; thread_id < nThread; thread_id++)
		{ 
			thread_func<T>(pNV, thread_id, _YPR, ypr_id++); 
		}
		if (info.bVerbose && b % nBlock == 0) { std::cout << "Step" << ypr_id + 1 << "/" << info.nYPR << std::endl; }
	}

	{ for (int thread_id = 0; thread_id < nBlRest; thread_id++) { thread_func<T>(pNV, thread_id, _YPR, ypr_id++); }  }
#else
	//std::thread version
	int ypr_id = 0;
	for (int b = 0; b < nBlock; b++) //Repeat # of CPU core * integer(nBlock) jobs
	{
		std::vector< std::thread> thVec;
		for (int thread_id = 0; thread_id < nThread; thread_id++) { thVec.push_back(std::thread(thread_func<T>, pNV, thread_id, _YPR, ypr_id++)); }

		for (auto& th : thVec) { th.join(); }

		if (info.bVerbose && b % 1000 == 0) { std::cout << "Step" << ypr_id + 1 << "/" << info.nYPR << std::endl; }
}

	{ std::vector< std::thread> thVec; //Do the rest jobs
	for (int thread_id = 0; thread_id < nBlRest; thread_id++) { thVec.push_back(std::thread(thread_func<T>, pNV, thread_id, _YPR, ypr_id++)); }
	for (auto& th : thVec) { th.join(); }  }

#endif

	MESH_ELE_ID_TYPE  optID =  _find1stOptimal( info.nYPR, Mss);
	if( info.nYPR >1)  thread_func<T>(pNV, 0, _YPR, optID);//Find information of optID again.

	//prepare rendering data for python
	::nData2i = new MESH_ELE_ID_TYPE[g_nPixelType];
	::pData2i = new INT16*     [g_nPixelType];

	for (int i = 0; i < g_nPixelType; i++)
	{
		TPVector tmp_pxls = pNV[0].slotsToPxls(enumPixelType(i));
		pData2i[i] = pxlsToDat2i( tmp_pxls, nData2i[i]);
	}

	//Find SS_pxls for rendering.
	{
		TPVector tmp_pxls = pNV[0].GetSSPixels(info.bUseExplicitSS);
		int _SS = static_cast<int>(enumPixelType::eptSS);
		pData2i[_SS] = pxlsToDat2i(tmp_pxls, nData2i[_SS]);
	}

	//return matrix data for Tomo_clutser.py project
	{
		::g_mat4x4 = new FLOAT32[16];
		memcpy(::g_mat4x4, pNV[0].mat4x4.Data, sizeof(FLOAT32) * 16);
	}

	VolMassInfo = pNV[0].vm_info; //final result

	delete[] pNV;
	if (info.bVerbose)	endTimer("TomoSh C++ DLL ");
	return optID;
}

//python interface functions
MESH_ELE_ID_TYPE  TomoSh_TMPxl(FLOAT32* _float32_info_x12, MESH_ELE_ID_TYPE* _int32_info_x11, FLOAT32* _YPR, MESH_ELE_ID_TYPE* _tri, FLOAT32* _vtx, FLOAT32* _vtx_nrm, FLOAT32* _tri_nrm, MESH_ELE_ID_TYPE* _chull_tri, FLOAT32* _chull_vtx, FLOAT32* _chull_trinrm)
{
	return  _TomoSh_Function_Call<STomoSh_TMPxl>(_float32_info_x12, _int32_info_x11, _YPR, _tri, _vtx, _vtx_nrm, _tri_nrm, _chull_tri, _chull_vtx, _chull_trinrm);
}

MESH_ELE_ID_TYPE TomoSh_INT3(FLOAT32* _float32_info_x12, MESH_ELE_ID_TYPE* _int32_info_x11, FLOAT32* _YPR, MESH_ELE_ID_TYPE* _tri, FLOAT32* _vtx, FLOAT32* _vtx_nrm, FLOAT32* _tri_nrm, MESH_ELE_ID_TYPE* _chull_tri, FLOAT32* _chull_vtx, FLOAT32* _chull_trinrm)
{
	return  _TomoSh_Function_Call<STomoSh_INT3>(_float32_info_x12, _int32_info_x11, _YPR, _tri, _vtx, _vtx_nrm, _tri_nrm, _chull_tri, _chull_vtx, _chull_trinrm);
}



#ifdef _USE_CUDA_FOR_TOMONV_0
//CUDA���� �׽�Ʈ 1.1 subdivision
TOMO_FLOAT32 a0[3] = { 0, 10, 10 };
TOMO_FLOAT32 a1[3] = { 0, 0, 10 };
TOMO_FLOAT32 a2[3] = { 10, 0, 10 };
TOMO_FLOAT32 an[3] = { 0, 0, 1 };

STomoVoxel al_0(a0, an);
STomoVoxel al_1(a1, an);
STomoVoxel al_2(a2, an);

STomoTriangle tri0(al_0, al_1, al_2);
std::cout << "before" << std::endl;
tri0.Print();

TTriVector tri_vec;
TOMO_FLOAT32 threshold = 8;
triDivide(tri_vec, tri0, threshold);
std::cout << "after" << std::endl;
for (auto& t : tri_vec)
{
	t.Print();
}
int i = 0;

#endif


#ifdef _DEBUG
#include <iostream>//std::cout
#include <cstdlib>
void  saveSTL(int nTri, FLOAT32 *_flattri)
{
	if(nTri == 0 || _flattri == nullptr) return;

	std::cout << "solid \"_flattri\" \n";
#if 1
	for (int t = 0; t < nTri; t++)
	{
		FlatTriInfo* pFT = (FlatTriInfo*) (_flattri + t * nFlatTriInfoSize);

		std::cout << "  facet normal " << pFT->tri_nrm[0] << " " << pFT->tri_nrm[1] << " " << pFT->tri_nrm[2] << "\n";
		std::cout << "    outer loop\n";
		std::cout << "      vertex " << pFT->vtx0[0] << " " << pFT->vtx0[1] << " " << pFT->vtx0[2] << "\n";
		std::cout << "      vertex " << pFT->vtx1[0] << " " << pFT->vtx1[1] << " " << pFT->vtx1[2] << "\n";
		std::cout << "      vertex " << pFT->vtx2[0] << " " << pFT->vtx2[1] << " " << pFT->vtx2[2] << "\n";
		std::cout << "    endloop\n";
		std::cout << "  endfacet\n";
	}
#else
	for( int t = 0 ;t < nTri ; t++)
	{
		for( int i = 0 ; i < nFlatTriInfoSize ; i++)
		{
			std::cout << _flattri[ t * nFlatTriInfoSize + i] << " ";
		}
		std::cout << std::endl;
	}
#endif
	std::cout << "endsolid \"_flattri\" " << std::endl;
}
#endif


MESH_ELE_ID_TYPE  TomoSh_CUDA(FLOAT32* _float32_info_x12, MESH_ELE_ID_TYPE* _int32_info_x11, FLOAT32* _YPR, MESH_ELE_ID_TYPE* _tri, FLOAT32* _vtx, FLOAT32* _vtx_nrm, FLOAT32* _tri_nrm, MESH_ELE_ID_TYPE* _chull_tri, FLOAT32* _chull_vtx, FLOAT32* _chull_trinrm)
{
	STomoSh_CUDA  Cuda1;
	S3DPrinterInfo& P_info = Cuda1.printer_info;

	P_info.Set(_float32_info_x12, _int32_info_x11, _tri, _vtx, _vtx_nrm, _tri_nrm, _chull_tri, _chull_vtx, _chull_trinrm, 0, 0, 0);//input mesh data. takes some memory.

	MESH_ELE_ID_TYPE nYPR = P_info.nYPR;
	int   nCHullVtx = P_info.nCHull_Vtx;

	Mss = new FLOAT32[nYPR + 2];
	Mo  = new FLOAT32[nYPR + 2];
	Vtc = new FLOAT32[nYPR + 2];
	memset(Mss, 0x00, sizeof(FLOAT32) * nYPR);
	memset(Mo , 0x00, sizeof(FLOAT32) * nYPR);
	memset(Vtc, 0x00, sizeof(FLOAT32) * nYPR);

	P_info.SetMaxTriDiameter();//do subdivision and make triangles smaller than CU_TRI_MAX_DIAMETER.
	P_info.GetYPR4x3Matrix( _YPR, nCHullVtx, _chull_vtx);//prepare rotation matrices

	Cuda1.bWriteBackPxlsForRendering = (nYPR == 1);
	Cuda1.Run(Mo, Mss, 0);//find optimals 

	MESH_ELE_ID_TYPE  optID = _find1stOptimal(nYPR, Mss);//ID to display

	std::cout << "bShellMesh is " << ((P_info.bShellMesh)? "true": "false") << std::endl;//debug

	if (nYPR > 1)
	{//prepare optID's pxls. for rendering.
		P_info.nYPR = 1;  P_info.bVerbose = false;
		FLOAT32 optYPR[3];
		memcpy(optYPR, _YPR + optID * 3, sizeof(FLOAT32) * 3);
		Cuda1.bWriteBackPxlsForRendering = true;
		P_info.GetYPR4x3Matrix(optYPR, nCHullVtx, _chull_vtx);//prepare rotation matrices
		Cuda1.Run(nullptr, nullptr);

		::g_mat4x4 = identity4x4();//DEBUG
		memcpy(::g_mat4x4, P_info.YPR_m4x3, sizeof(FLOAT32) * 4*3);
	}

	//deliver pxl data to python
	::VolMassInfo = Cuda1.vm_info;//for debug. deliver volume/mass data to python's Print_tabbed() function. 
	::nData2i = new MESH_ELE_ID_TYPE[g_nPixelType];  
	::pData2i = new INT16 * [g_nPixelType];
	for (int i = 0; i < g_nPixelType; i++) { ::nData2i[i] = 0; ::pData2i[i] = nullptr; }

	Cuda1.ReadPxls(0, nData2i, pData2i);//time consuming. for Python rendering.


return optID;
}

