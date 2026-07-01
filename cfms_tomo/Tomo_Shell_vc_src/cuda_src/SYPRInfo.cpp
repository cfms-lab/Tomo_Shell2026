#include "pch.h"
#include "SYPRInfo.h"
#include <string.h> //memcpy()

SYPRInfo::SYPRInfo(FLOAT32 * _ypr, int n_chull_vtx, FLOAT32* _chull_vtx)
{
  Init();
  if(_ypr!=nullptr)
  {
    Yaw   = _ypr[0];
    Pitch = _ypr[1];
    Roll  = _ypr[2];
    Set_m4x3(n_chull_vtx, _chull_vtx);
  }
}

SYPRInfo::SYPRInfo(FLOAT32 * _ypr, const TVVector& CVVoxels)
{
  Init();
  if(_ypr!=nullptr)
  {
    Yaw   = _ypr[0];
    Pitch = _ypr[1];
    Roll  = _ypr[2];
    Set_m4x3(CVVoxels);
  }
}

SYPRInfo::~SYPRInfo()
{
  Reset();
}

SYPRInfo::SYPRInfo(const SYPRInfo& Source)
{
  Init();
  _Copy(Source);
}

void	SYPRInfo::operator=(const SYPRInfo& Source)
{
  Reset();
  _Copy(Source);
}

void	SYPRInfo::_Copy(const SYPRInfo& Source)
{
  memcpy(fData, Source.fData, sfData);
}

void	SYPRInfo::Reset(void)
{
  Init();
}

void	SYPRInfo::Init(void)
{
  memset( fData, 0x00, sfData);
}


void  SYPRInfo::Set_m4x3(int n_chull_vtx, FLOAT32* _chull_vtx)
{
  if(n_chull_vtx<=0) return;

  SMatrix4f mtx(Yaw, Pitch, Roll);
  FLOAT32 center[3] = { 0.f, 0.f, 0.f };
  FLOAT32 minRaw[3] = { 1e5f, 1e5f, 1e5f };
  FLOAT32 maxRaw[3] = { -1e5f, -1e5f, -1e5f };
  for (int chv = 0; chv < n_chull_vtx; chv++)
  {
    FLOAT32* vtx = _chull_vtx + chv * 3;
    for (int k = 0; k < 3; k++)
    {
      minRaw[k] = _min(minRaw[k], vtx[k]);
      maxRaw[k] = _max(maxRaw[k], vtx[k]);
    }
  }
  for (int k = 0; k < 3; k++) { center[k] = (minRaw[k] + maxRaw[k]) * FLOAT32(0.5); }

  FLOAT32 _minXYZ[3] = { 1e5f, 1e5f, 1e5f }, shifted[3] = {}, rotated_vtx[3] = {};
  for (int chv = 0; chv < n_chull_vtx; chv++)
  {
    FLOAT32* vtx = _chull_vtx + chv * 3;
    shifted[0] = vtx[0] - center[0];
    shifted[1] = vtx[1] - center[1];
    shifted[2] = vtx[2] - center[2];
    mtx.Dot(shifted, rotated_vtx);
    _minXYZ[0] = _min(_minXYZ[0], rotated_vtx[0]);
    _minXYZ[1] = _min(_minXYZ[1], rotated_vtx[1]);
    _minXYZ[2] = _min(_minXYZ[2], rotated_vtx[2]);
  }

  FLOAT32 m = -center[0], n = -center[1], o = -center[2];
  mtx.Data[0][3] = -_minXYZ[0] + mtx.Data[0][0] * m + mtx.Data[0][1] * n + mtx.Data[0][2] * o;
  mtx.Data[1][3] = -_minXYZ[1] + mtx.Data[1][0] * m + mtx.Data[1][1] * n + mtx.Data[1][2] * o;
  mtx.Data[2][3] = -_minXYZ[2] + mtx.Data[2][0] * m + mtx.Data[2][1] * n + mtx.Data[2][2] * o;

  memcpy(m4x3, mtx.fData, sizeof(FLOAT32) * CU_MATRIX_SIZE_12);
}

void  SYPRInfo::Set_m4x3(const TVVector& CVVoxels)
{
  int nCVVoxel = CVVoxels.size();
  if(nCVVoxel<=0) return;

  SMatrix4f     mtx( Yaw, Pitch, Roll);
  FLOAT32 _minXYZ[3] = { 1e5,1e5,1e5 }, rotated_chull_vtx[3] = {};
  for (int chv = 0; chv < nCVVoxel; chv++)
  {
    mtx.Dot( (FLOAT32* ) (CVVoxels.begin() + chv)->crd, rotated_chull_vtx);
    _minXYZ[0] = _min(_minXYZ[0], rotated_chull_vtx[0]);
    _minXYZ[1] = _min(_minXYZ[1], rotated_chull_vtx[1]);
    _minXYZ[2] = _min(_minXYZ[2], rotated_chull_vtx[2]);
  }
  mtx.Data[0][3] = -_minXYZ[0];
  mtx.Data[1][3] = -_minXYZ[1];
  mtx.Data[2][3] = -_minXYZ[2];

  memcpy(m4x3, mtx.fData, sizeof(FLOAT32) * CU_MATRIX_SIZE_12);
}