#pragma once
#include "..\Tomo_types.h"
#include "STomoVoxel.h"
#include "STomoTriangle.h"
#include <vector>

using namespace Tomo;

typedef DLLEXPORT struct
{
  FLOAT32 vtx0[3];//�������� �����ǥ. (0,0)~(16,16) �� �븻������ z ����.
  FLOAT32 vtx1[3];
  FLOAT32 vtx2[3];
  FLOAT32 nrm0[3];//per-vertex normals (was a single tri_nrm). GPU interpolates nz like the CPU path.
  FLOAT32 nrm1[3];
  FLOAT32 nrm2[3];
  FLOAT32 AABB[2];//host: parent id / first-in-parent flag; kernel overwrites with rotated AABB.
} FlatTriInfo;

static const int nFlatTriInfoSize = sizeof(FlatTriInfo) / sizeof(FLOAT32);//match to 16 (BLOCK_SIZE)
static const int nParentFallbackInfoSize = 6;//centroid xyz + fallback normal xyz per original triangle


class DLLEXPORT S3DPrinterInfo
{
public:
  S3DPrinterInfo(
    FLOAT32* _float32_x12 = nullptr,
    MESH_ELE_ID_TYPE* _int32_x10 = nullptr,
    MESH_ELE_ID_TYPE* _tri = nullptr, FLOAT32* _vtx = nullptr, FLOAT32* _vtx_nrm = nullptr, FLOAT32* _tri_nrm = nullptr,
    MESH_ELE_ID_TYPE* _chull_tri = nullptr, FLOAT32* _chull_vtx = nullptr, FLOAT32* _chull_trinrm = nullptr,
    FLOAT32 _yaw = 0, FLOAT32 _pitch = 0, FLOAT32 _roll = 0);
  S3DPrinterInfo(const S3DPrinterInfo& Source);
  void	operator=(const S3DPrinterInfo& Source);
  void	_Copy(const S3DPrinterInfo& Source);
  ~S3DPrinterInfo();

  static const int ndData = 16;
  static const int sdData = sizeof(FLOAT32) * ndData;
  union
  {
    struct {// Do not change this order!!
      FLOAT32	dVoxel, theta_c, surface_area, wall_thickness, \
        Fcore, Fclad, Fss, Css,
        PLA_density, BedInnerBound, BedOuterBound, BedThickness,
        //������� 12���� ���̽㿡�� �޾ƿ�.
        yaw, pitch, roll;
    };
    FLOAT32 dData[ndData];
  };

  bool  bVerbose;//for debug
  bool  bUseExplicitSS;
  bool  bShellMesh;
  FLOAT32 shell_thickness;

  //input mesh data
  FLOAT32* rpVtx0, * pVtx1;//[nVtx]
  FLOAT32* rpTriNrm0, * rpVtxNrm0, * pNrm1, * pTriCenter;//[nTri]  triangle normal before/after rotation.
  MESH_ELE_ID_TYPE* rpTri0;//[nTri]

  MESH_ELE_ID_TYPE nVtx, nTri;//Cuastion: Do not treat this as int.
  int  nVoxel;//default 256

  size_t  nYPR;

  enumBedType BedType;

  //p-orbital (CvxHull)
  MESH_ELE_ID_TYPE nCHull_Tri, nCHull_Vtx;
  MESH_ELE_ID_TYPE* pCHull_Tri;
  FLOAT32* pCHull_Vtx, * pCHull_TriNrm, * pCHull_TriCenter;


#ifdef _USE_CUDA_FOR_TOMONV
  void  SetMaxTriDiameter(void);
  void  SetFlatTri(const TTriVector&, const std::vector<int>&, const std::vector<int>&);
  FLOAT32* pFlatTri;//CUDA pinned memory
  FLOAT32* pParentFallbackTri;//[nTri * nParentFallbackInfoSize], raw centroid + raw fallback normal
  MESH_ELE_ID_TYPE nFlatTri;
  int  TriMaxDiameter;
  void  GetYPR4x3Matrix(FLOAT32* _YPR, int nCHullVtx, FLOAT32* _chull_vtx);
  FLOAT32* YPR_m4x3;
#endif

  void	Reset(void);
  void	Init(void);
  void  Set(FLOAT32* _float32_x12,
    MESH_ELE_ID_TYPE* _int32_info,
    MESH_ELE_ID_TYPE* _tri, FLOAT32* _vtx, FLOAT32* _vtx_nrm, FLOAT32* _tri_nrm,
    MESH_ELE_ID_TYPE* _chull_tri, FLOAT32* _chull_vtx, FLOAT32* _chull_trirnm,
    FLOAT32 _yaw, FLOAT32 _pitch, FLOAT32 _roll);

};
