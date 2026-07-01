#pragma once
#include "STPSlot.h"

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
  //const int nSlotBufWidth = 3;// 0th element is ( nPxl ,Vo, Vss), and then list of (Z, nZ * nNORMALFACTOR, type),..  0 <= nPxl <= nMaxZDepth-1.
  SLOT_BUFFER_TYPE* SlotBuf_108f;//3*8 bits  for voxel,  3 bytes * X_D * Y_D * nMaxZDepth. 비어 있지 않은 픽셀값만 모아서 저장.
  void  InitSlotBuf(void);

  void  SetBit_Type(SLOT_BUFFER_TYPE* slot_buf, unsigned int _ID, unsigned int slotXYZ[3],
      int pxl_z, int pxl_nZ_100, int _typeByte);
  void  SetBit(SLOT_BUFFER_TYPE* slot_buf, FLOAT32* pxl, FLOAT32* nrm, int _typeByte);
};
