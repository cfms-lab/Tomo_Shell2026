#pragma once
#include "../Tomo_types.h"
#include "../cpu_src/SMatrix4f.h"
#include "../cpu_src/STomoVoxel.h"
#include "CUDA_types.cuh"//MATRIX_SIZE_12

using namespace Tomo;

class DLLEXPORT SYPRInfo
{
public:
  SYPRInfo(FLOAT32 *ypr, int n_chull_vtx, FLOAT32 * _chull_vtx);
  SYPRInfo(FLOAT32 *ypr, const TVVector& CVVoxels);
  SYPRInfo(const SYPRInfo& Source);
  void	operator=(const SYPRInfo& Source);
  void	_Copy(const SYPRInfo& Source);
  ~SYPRInfo();

  void	Reset(void);
  void	Init(void);

  static const int nfData = 3+16;
  static const int sfData = sizeof(FLOAT32) * nfData;
  union
  {
    struct { FLOAT32 Yaw, Pitch, Roll, m4x3[CU_MATRIX_SIZE_12]; };//https://en.wikipedia.org/wiki/Homogeneous_coordinates
    FLOAT32 fData[nfData];
  };

  void  Set_m4x3(int nCHvtx, FLOAT32* _chull_vtx);
  void  Set_m4x3(const TVVector& CVVoxels);

};

