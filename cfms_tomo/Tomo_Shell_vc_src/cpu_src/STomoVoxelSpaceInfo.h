#pragma once
#include "STPSlot.h"
#include <vector>

using namespace Tomo;

class DLLEXPORT STomoVoxelSpaceInfo
{
public:
  STomoVoxelSpaceInfo(int _x_dim=256, int _y_dim = 256, int _z_dim = 256);
  STomoVoxelSpaceInfo(const STomoVoxelSpaceInfo& Source);
  void	operator=(const STomoVoxelSpaceInfo& Source);
  void	_Copy(const STomoVoxelSpaceInfo& Source);
  ~STomoVoxelSpaceInfo();

  void	Reset(void);
  void	Init(void);

  static const int niData = 6;
  static const int siData = sizeof(int) * niData;
  union
  {
    struct { int x_dim, y_dim, z_dim, nSlotCapacityWidth, nSlotCapacityHeight, nTri/*debug*/; };
    int iData[niData];
  };

  VOXEL_ID_TYPE nTotalVxls;//debug

  void      SetMem(int _x_dim, int _y_dim, int _z_dim);
  /*output1*/VOXEL_ID_TYPE  coord2vID(/*input*/FLOAT32* coord,  /*output2*/int slotXYZ[3]);
  /*output1*/VOXEL_ID_TYPE  coord2vID(/*input*/int* coord,           /*output2*/int slotXYZ[3]);
  unsigned int  coord2vID(int* coord);
  void          vID2coord(VOXEL_ID_TYPE  _id, int& _x, int& _y, int& _z);

  //pointers to CUDA
  //mem size: https://docs.microsoft.com/ko-kr/cpp/cpp/data-type-ranges?view=msvc-170
  //unsigned int = 4byte,  , SLOT_BUFFER_TYPE = 1 byte
  //const int nSlotBufMaxHeight = 36;//max. ray-mesh intersection number. assumption.
  //const int nSlotBufWidth = 3;// 0th row stores nPxl only.
  SLOT_BUFFER_TYPE* SlotBuf_108f;//3*8 bits  for voxel,  3 bytes * X_D * Y_D * nMaxZDepth. ��� ���� ���� �ȼ����� ��Ƽ� ����.
  void  InitSlotBuf(void);

  //Per-direction we only ever write a small subset of the X_D*Y_D slots (the mesh
  //silhouette + bed). Re-memset-ing the whole 6MB SlotBuf every direction was ~49% of
  //CPU time. Instead we record each slot the moment it goes empty->non-empty and, at the
  //start of the next direction, zero only those slots. ClearDirtySlots() must leave the
  //buffer in the same all-zero state InitSlotBuf() would (type column is written with |=,
  //so a stale non-zero payload would corrupt the next direction).
  std::vector<VOXEL_ID_TYPE> dirtySlots;
  void  ClearDirtySlots(void);

  void  SetBit_Type(SLOT_BUFFER_TYPE* slot_buf, unsigned int _ID, unsigned int slotXYZ[3],
      int pxl_z, int pxl_nZ_100, int _typeByte);
  void  SetBit(SLOT_BUFFER_TYPE* slot_buf, FLOAT32* pxl, FLOAT32* nrm, int _typeByte);
};
