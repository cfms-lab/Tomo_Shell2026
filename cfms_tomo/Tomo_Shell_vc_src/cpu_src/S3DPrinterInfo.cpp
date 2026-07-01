#include "pch.h"
#include "S3DPrinterInfo.h"
#include "SMatrix4f.h"
#include "../cuda_src/CUDA_types.cuh"//MATRIX_SIZE_12
#include "../cuda_src/SYPRInfo.h"

using namespace Tomo;

S3DPrinterInfo::S3DPrinterInfo(
  FLOAT32* _float32_x12,
  MESH_ELE_ID_TYPE* _int32_x10,
  MESH_ELE_ID_TYPE* _tri, FLOAT32* _vtx, FLOAT32* _vtx_nrm, FLOAT32* _tri_nrm,
  MESH_ELE_ID_TYPE* _chull_tri, FLOAT32* _chull_vtx, FLOAT32* _chull_trinrm,
  FLOAT32 _yaw, FLOAT32 _pitch, FLOAT32 _roll)
{
  Init();
  if (_float32_x12 != nullptr) Set(_float32_x12, _int32_x10, _tri, _vtx, _vtx_nrm, _tri_nrm, _chull_tri, _chull_vtx, _chull_trinrm, _yaw, _pitch, _roll);
}

S3DPrinterInfo::~S3DPrinterInfo()
{
  Reset();
}

S3DPrinterInfo::S3DPrinterInfo(const S3DPrinterInfo& Source)
{
  Init();
  _Copy(Source);
}

void	S3DPrinterInfo::operator=(const S3DPrinterInfo& Source)
{
  Reset();
  _Copy(Source);
}

void	S3DPrinterInfo::_Copy(const S3DPrinterInfo& Source)
{
  memcpy(dData, Source.dData, sdData);

  bVerbose = Source.bVerbose;
  bUseExplicitSS = Source.bUseExplicitSS;
  bShellMesh = Source.bShellMesh;
  shell_thickness = Source.shell_thickness;

  rpVtx0 = Source.rpVtx0;
  rpTriNrm0 = Source.rpTriNrm0;
  rpVtxNrm0 = Source.rpVtxNrm0;
  rpTri0 = Source.rpTri0;
  nVtx = Source.nVtx;
  nTri = Source.nTri;
  nVoxel = Source.nVoxel;
  nYPR = Source.nYPR;
  BedType = Source.BedType;

  pTriCenter = new FLOAT32[nTri * 4 + 2];
  memcpy(pTriCenter, Source.pTriCenter, sizeof(FLOAT32) * nTri * 4);

  nCHull_Vtx = Source.nCHull_Vtx;
  nCHull_Tri = Source.nCHull_Tri;
  if (nCHull_Vtx > 0)
  {
    pCHull_Vtx = new FLOAT32[nCHull_Vtx * 3 + 2];
    memcpy(pCHull_Vtx, Source.pCHull_Vtx, sizeof(FLOAT32) * nCHull_Vtx * 3);
  }

  if (nCHull_Tri > 0)
  {
    pCHull_Tri = new MESH_ELE_ID_TYPE[nCHull_Tri * 3 + 2];
    memcpy(pCHull_Tri, Source.pCHull_Tri, sizeof(MESH_ELE_ID_TYPE) * nCHull_Tri * 3);
    pCHull_TriNrm = new FLOAT32[nCHull_Tri * 3 + 2];
    memcpy(pCHull_TriNrm, Source.pCHull_TriNrm, sizeof(FLOAT32) * nCHull_Tri * 3);

    pCHull_TriCenter = new FLOAT32[nCHull_Tri * 4 + 2];
    memcpy(pCHull_TriCenter, Source.pCHull_TriCenter, sizeof(FLOAT32) * nCHull_Tri * 4);
  }


}

void	S3DPrinterInfo::Reset(void)
{
  if (pVtx1 != nullptr) { delete[] pVtx1;   pVtx1 = nullptr; }
  if (pNrm1 != nullptr) { delete[] pNrm1;   pNrm1 = nullptr; }
  if (pCHull_Vtx != nullptr) { delete[] pCHull_Vtx; pCHull_Vtx = nullptr; }

#ifdef _USE_CUDA_FOR_TOMONV
  if (pFlatTri != nullptr) { cudaFreeHost(pFlatTri);  pFlatTri = nullptr; }
  if (pParentFallbackTri != nullptr) { cudaFreeHost(pParentFallbackTri); pParentFallbackTri = nullptr; }
  if (YPR_m4x3 != nullptr) { cudaFreeHost(YPR_m4x3); YPR_m4x3 = nullptr; }
  nFlatTri = 0;
#endif

  Init();
}

void	S3DPrinterInfo::Init(void)
{
  memset(dData, 0x00, sdData);

  bVerbose = bUseExplicitSS = false;
  bShellMesh = false;
  shell_thickness = FLOAT32(0.);

  pTriCenter = rpVtx0 = rpTriNrm0 = rpVtxNrm0 = pVtx1 = pNrm1 = nullptr;
  rpTri0 = nullptr;
  nVtx = nTri = 0;
  nVoxel = 256;
  nYPR = 0;

#ifdef _USE_CUDA_FOR_TOMONV
  pFlatTri = nullptr; pParentFallbackTri = nullptr; YPR_m4x3 = nullptr;
  nFlatTri = 0;
  TriMaxDiameter = 16;
#endif

  BedType = enumBedType::ebtNone;

  nCHull_Tri = 0; nCHull_Vtx = 0;
  pCHull_Vtx = pCHull_TriNrm = nullptr; pCHull_Tri = nullptr;

}

void	S3DPrinterInfo::Set(FLOAT32* _float32_x12,
  MESH_ELE_ID_TYPE* _int32_x11,
  MESH_ELE_ID_TYPE* _tri, FLOAT32* _vtx, FLOAT32* _vtx_nrm, FLOAT32* _tri_nrm,
  MESH_ELE_ID_TYPE* _chull_tri, FLOAT32* _chull_vtx, FLOAT32* _chull_trinrm,
  FLOAT32 _yaw, FLOAT32 _pitch, FLOAT32 _roll)
{
  memcpy(dData, _float32_x12, sizeof(FLOAT32) * 12);

  bVerbose                = (_int32_x11[0] > g_fMARGIN);
  bUseExplicitSS          = (_int32_x11[1] > g_fMARGIN);
  bShellMesh     = (_int32_x11[2] > g_fMARGIN);//added. 2025-07-30
  shell_thickness = FLOAT32(_int32_x11[10]) * FLOAT32(0.001);
  nVoxel               = int(_int32_x11[3]);

  nTri       = VOXEL_ID_TYPE(_int32_x11[4]);
  nVtx       = VOXEL_ID_TYPE(_int32_x11[5]);
  nYPR              = size_t(_int32_x11[6]);

  nCHull_Tri           = int(_int32_x11[7]);
  nCHull_Vtx           = int(_int32_x11[8]);
  BedType      = enumBedType(_int32_x11[9]);

  
  if (nCHull_Vtx > 0)
  {
    pCHull_Vtx = new FLOAT32[nCHull_Vtx * 3 + 2];
    memcpy(pCHull_Vtx, _chull_vtx, sizeof(FLOAT32) * nCHull_Vtx * 3);
  }

  FLOAT32       divideBy3 = FLOAT32(1. / 3.);

  if (nCHull_Tri > 0)
  {
    pCHull_Tri = new MESH_ELE_ID_TYPE[nCHull_Tri * 3 + 2];
    memcpy(pCHull_Tri, _chull_tri, sizeof(MESH_ELE_ID_TYPE) * nCHull_Tri * 3);
    pCHull_TriNrm = new FLOAT32[nCHull_Tri * 3 + 2];
    memcpy(pCHull_TriNrm, _chull_trinrm, sizeof(FLOAT32) * nCHull_Tri * 3);

    pCHull_TriCenter = new FLOAT32[nCHull_Tri * 4 + 2];
    for (int t = 0; t < nCHull_Tri; t++)
    {
      int n0 = pCHull_Tri[t * 3 + 0];
      int n1 = pCHull_Tri[t * 3 + 1];
      int n2 = pCHull_Tri[t * 3 + 2];
      pCHull_TriCenter[t * 4 + 0] = (pCHull_Vtx[n0 * 3 + 0] + pCHull_Vtx[n1 * 3 + 0] + pCHull_Vtx[n2 * 3 + 0]) * divideBy3;
      pCHull_TriCenter[t * 4 + 1] = (pCHull_Vtx[n0 * 3 + 1] + pCHull_Vtx[n1 * 3 + 1] + pCHull_Vtx[n2 * 3 + 1]) * divideBy3;
      pCHull_TriCenter[t * 4 + 2] = (pCHull_Vtx[n0 * 3 + 2] + pCHull_Vtx[n1 * 3 + 2] + pCHull_Vtx[n2 * 3 + 2]) * divideBy3;
      pCHull_TriCenter[t * 4 + 3] = getTriArea3D(pCHull_Vtx + n0 * 3, pCHull_Vtx + n1 * 3, pCHull_Vtx + n2 * 3);
    }
  }

  yaw = _yaw;
  pitch = _pitch;
  roll = _roll;

  rpVtx0 = _vtx;
  rpTriNrm0 = _tri_nrm;
  rpVtxNrm0 = _vtx_nrm;
  rpTri0 = _tri;
  pVtx1 = nullptr;

  pTriCenter = new FLOAT32[nTri * 4 + 2];

  for (int t = 0; t < nTri; t++)
  {
    int n0 = rpTri0[t * 3 + 0];
    int n1 = rpTri0[t * 3 + 1];
    int n2 = rpTri0[t * 3 + 2];
    pTriCenter[t * 4 + 0] = (rpVtx0[n0 * 3 + 0] + rpVtx0[n1 * 3 + 0] + rpVtx0[n2 * 3 + 0]) * divideBy3;
    pTriCenter[t * 4 + 1] = (rpVtx0[n0 * 3 + 1] + rpVtx0[n1 * 3 + 1] + rpVtx0[n2 * 3 + 1]) * divideBy3;
    pTriCenter[t * 4 + 2] = (rpVtx0[n0 * 3 + 2] + rpVtx0[n1 * 3 + 2] + rpVtx0[n2 * 3 + 2]) * divideBy3;
    pTriCenter[t * 4 + 3] = getTriArea3D(rpVtx0 + n0 * 3, rpVtx0 + n1 * 3, rpVtx0 + n2 * 3);
  }

}


#include <cuda_runtime_api.h> //cudaMallocHost()
#ifdef _USE_CUDA_FOR_TOMONV

void  S3DPrinterInfo::SetFlatTri(const TTriVector& ttri_vec, const std::vector<int>& parent_vec, const std::vector<int>& first_vec)
{
  nFlatTri = ttri_vec.size();
#ifdef _USE_CUDA_FOR_TOMONV
  cudaMallocHost(&pFlatTri, sizeof(FLOAT32) * nFlatTri * nFlatTriInfoSize);
#else
  pFlatTri = new FLOAT32[nFlatTri * nFlatTriInfoSize];
#endif
  memset(pFlatTri, 0x00, sizeof(FLOAT32) * nFlatTri * nFlatTriInfoSize);


  FlatTriInfo** ppFlatTriInfo = new FlatTriInfo * [nFlatTri];

  MESH_ELE_ID_TYPE t = 0;
  for (auto& ttri : ttri_vec)
  {
    ppFlatTriInfo[t] = (FlatTriInfo*)(pFlatTri + t * nFlatTriInfoSize);

    //ȸ�� ������ ������ǥ�� �״�� ����.
    ppFlatTriInfo[t]->vtx0[0] = ttri.Vtx[0].x;
    ppFlatTriInfo[t]->vtx0[1] = ttri.Vtx[0].y;
    ppFlatTriInfo[t]->vtx0[2] = ttri.Vtx[0].z;

    ppFlatTriInfo[t]->vtx1[0] = ttri.Vtx[1].x;
    ppFlatTriInfo[t]->vtx1[1] = ttri.Vtx[1].y;
    ppFlatTriInfo[t]->vtx1[2] = ttri.Vtx[1].z;

    ppFlatTriInfo[t]->vtx2[0] = ttri.Vtx[2].x;
    ppFlatTriInfo[t]->vtx2[1] = ttri.Vtx[2].y;
    ppFlatTriInfo[t]->vtx2[2] = ttri.Vtx[2].z;

    ppFlatTriInfo[t]->nrm0[0] = ttri.Vtx[0].nx;
    ppFlatTriInfo[t]->nrm0[1] = ttri.Vtx[0].ny;
    ppFlatTriInfo[t]->nrm0[2] = ttri.Vtx[0].nz;

    ppFlatTriInfo[t]->nrm1[0] = ttri.Vtx[1].nx;
    ppFlatTriInfo[t]->nrm1[1] = ttri.Vtx[1].ny;
    ppFlatTriInfo[t]->nrm1[2] = ttri.Vtx[1].nz;

    ppFlatTriInfo[t]->nrm2[0] = ttri.Vtx[2].nx;
    ppFlatTriInfo[t]->nrm2[1] = ttri.Vtx[2].ny;
    ppFlatTriInfo[t]->nrm2[2] = ttri.Vtx[2].nz;

    ppFlatTriInfo[t]->AABB[0] = (t < parent_vec.size()) ? FLOAT32(parent_vec[t]) : FLOAT32(t);
    ppFlatTriInfo[t]->AABB[1] = (t < first_vec.size()) ? FLOAT32(first_vec[t]) : FLOAT32(1);

    t++;
  }
}

#ifdef _DEBUG
#include <iostream>//std::cout
#include <cstdlib>//std::getenv, std::atoi
void  saveSTL(const TTriVector& ttri_vec)
{
  std::cout << "solid \"tomoNV\" \n";
  for (auto& tri : ttri_vec)
  {
    std::cout << "  facet normal " << tri.Vtx[0].nx << " " << tri.Vtx[0].ny << " " << tri.Vtx[0].nz << "\n";
    std::cout << "    outer loop\n";
    std::cout << "      vertex " << tri.Vtx[0].x << " " << tri.Vtx[0].y << " " << tri.Vtx[0].z << "\n";
    std::cout << "      vertex " << tri.Vtx[1].x << " " << tri.Vtx[1].y << " " << tri.Vtx[1].z << "\n";
    std::cout << "      vertex " << tri.Vtx[2].x << " " << tri.Vtx[2].y << " " << tri.Vtx[2].z << "\n";
    std::cout << "    endloop\n";
    std::cout << "  endfacet\n";
  }
  std::cout << "endsolid \"tomoNV\" \n";
}
#endif

void  S3DPrinterInfo::SetMaxTriDiameter(void)//split triangle if its x- or y- dimension is bigger than "size"
{
  TTriVector small_tri_vec;
  std::vector<int> flat_parent_vec;
  std::vector<int> flat_first_vec;
  float avg_tri_diameter = 0;
  for (MESH_ELE_ID_TYPE t = 0; t < nTri; t++)
  {
    MESH_ELE_ID_TYPE t0 = rpTri0[t * 3 + 0];
    MESH_ELE_ID_TYPE t1 = rpTri0[t * 3 + 1];
    MESH_ELE_ID_TYPE t2 = rpTri0[t * 3 + 2];

#ifdef _USE_VTX_NRM_FOR_PIXEL
    STomoVoxel tv0(&rpVtx0[t0 * 3], &rpVtxNrm0[t0 * 3]);
    STomoVoxel tv1(&rpVtx0[t1 * 3], &rpVtxNrm0[t1 * 3]);
    STomoVoxel tv2(&rpVtx0[t2 * 3], &rpVtxNrm0[t2 * 3]);
#else
    STomoVoxel tv0(&rpVtx0[t0 * 3], &rpTriNrm0[t * 3]);
    STomoVoxel tv1(&rpVtx0[t1 * 3], &rpTriNrm0[t * 3]);
    STomoVoxel tv2(&rpVtx0[t2 * 3], &rpTriNrm0[t * 3]);
#endif

    STomoTriangle ttri(tv0, tv1, tv2);
    avg_tri_diameter += ttri.GetCurcumDiameter();
  }
  avg_tri_diameter /= float(nTri);


  TriMaxDiameter = (avg_tri_diameter > 4) ? 8 : 4;
  char* envTriMax = nullptr;
  size_t envTriMaxLen = 0;
  if (_dupenv_s(&envTriMax, &envTriMaxLen, "TOMO_CUDA_TRI_MAX_DIAMETER") == 0 && envTriMax != nullptr) {
    int forcedTriMax = std::atoi(envTriMax);
    if (forcedTriMax > 0 && forcedTriMax <= 16) { TriMaxDiameter = forcedTriMax; }
    free(envTriMax);
  }
  if (pParentFallbackTri != nullptr) { cudaFreeHost(pParentFallbackTri); pParentFallbackTri = nullptr; }
  cudaMallocHost(&pParentFallbackTri, sizeof(FLOAT32) * nTri * nParentFallbackInfoSize);
  memset(pParentFallbackTri, 0x00, sizeof(FLOAT32) * nTri * nParentFallbackInfoSize);

  if (bVerbose){
    std::cout << "Average triangle circum diameter= " << avg_tri_diameter << " [mm]" << std::endl;
    std::cout << "Setting TriMaxDiameter=" << TriMaxDiameter << " [mm]" << std::endl;
  }

  for (MESH_ELE_ID_TYPE t = 0; t < nTri; t++)
  {
    MESH_ELE_ID_TYPE t0 = rpTri0[t * 3 + 0];
    MESH_ELE_ID_TYPE t1 = rpTri0[t * 3 + 1];
    MESH_ELE_ID_TYPE t2 = rpTri0[t * 3 + 2];

#ifdef _USE_VTX_NRM_FOR_PIXEL
    STomoVoxel tv0(&rpVtx0[t0 * 3], &rpVtxNrm0[t0 * 3]);
    STomoVoxel tv1(&rpVtx0[t1 * 3], &rpVtxNrm0[t1 * 3]);
    STomoVoxel tv2(&rpVtx0[t2 * 3], &rpVtxNrm0[t2 * 3]);
#else
    STomoVoxel tv0(&rpVtx0[t0 * 3], &rpTriNrm0[t * 3]);
    STomoVoxel tv1(&rpVtx0[t1 * 3], &rpTriNrm0[t * 3]);
    STomoVoxel tv2(&rpVtx0[t2 * 3], &rpTriNrm0[t * 3]);
#endif

    FLOAT32* parentFallback = pParentFallbackTri + t * nParentFallbackInfoSize;
    parentFallback[0] = (rpVtx0[t0 * 3 + 0] + rpVtx0[t1 * 3 + 0] + rpVtx0[t2 * 3 + 0]) * FLOAT32(0.333333);
    parentFallback[1] = (rpVtx0[t0 * 3 + 1] + rpVtx0[t1 * 3 + 1] + rpVtx0[t2 * 3 + 1]) * FLOAT32(0.333333);
    parentFallback[2] = (rpVtx0[t0 * 3 + 2] + rpVtx0[t1 * 3 + 2] + rpVtx0[t2 * 3 + 2]) * FLOAT32(0.333333);
#ifdef _USE_VTX_NRM_FOR_PIXEL
    parentFallback[3] = rpVtxNrm0[t0 * 3 + 0];
    parentFallback[4] = rpVtxNrm0[t0 * 3 + 1];
    parentFallback[5] = rpVtxNrm0[t0 * 3 + 2];
#else
    parentFallback[3] = rpTriNrm0[t * 3 + 0];
    parentFallback[4] = rpTriNrm0[t * 3 + 1];
    parentFallback[5] = rpTriNrm0[t * 3 + 2];
#endif

    STomoTriangle ttri(tv0, tv1, tv2);
    size_t flat_begin = small_tri_vec.size();
    triDivide4(small_tri_vec, ttri, TriMaxDiameter);
    size_t flat_end = small_tri_vec.size();
    for (size_t ft = flat_begin; ft < flat_end; ft++) {
      flat_parent_vec.push_back(int(t));
      flat_first_vec.push_back((ft == flat_begin) ? 1 : 0);
    }
  }


  SetFlatTri(small_tri_vec, flat_parent_vec, flat_first_vec);
}

void S3DPrinterInfo::GetYPR4x3Matrix(FLOAT32* _YPR, int nCHullVtx, FLOAT32* _chull_vtx)
{
  //prepare YPR_m4x4
#ifdef _USE_CUDA_FOR_TOMONV
  cudaFreeHost(YPR_m4x3);
  cudaMallocHost((void**)&YPR_m4x3, nYPR * CU_MATRIX_SIZE_12 * sizeof(FLOAT32));
#else
  if (YPR_m4x3 != nullptr) delete[] YPR_m4x3;
  YPR_m4x3 = new FLOAT32[nYPR * CU_MATRIX_SIZE_12 + 2];
#endif
  for (int ypr_id = 0; ypr_id < nYPR; ypr_id++)
  {
    SYPRInfo yprinfo(_YPR + ypr_id * 3, nVtx, rpVtx0);

    yprinfo.m4x3[3] += BedOuterBound;
    yprinfo.m4x3[7] += BedOuterBound;

    memcpy(YPR_m4x3 + ypr_id * CU_MATRIX_SIZE_12, yprinfo.m4x3, sizeof(FLOAT32) * CU_MATRIX_SIZE_12);
  }
}

#endif

