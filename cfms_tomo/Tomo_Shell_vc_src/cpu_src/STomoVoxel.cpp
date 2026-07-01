#include "pch.h"
#include <algorithm> //std::sort()
#include "STomoVoxel.h"
#include "SMatrix4f.h"

using namespace Tomo;

STomoVoxel::STomoVoxel(FLOAT32* _pxl3d, FLOAT32* _nrm3d)
{
  Init();

  if(_pxl3d!=nullptr)
  {
    x = (_pxl3d[0]);    y = (_pxl3d[1]);    z = (_pxl3d[2]);
  }
  if(_nrm3d!=nullptr)
  {
    nx = (_nrm3d[0]);    ny = (_nrm3d[1]);    nz = (_nrm3d[2]);
  }
}

STomoVoxel::STomoVoxel(const STomoPixel& p)
{
  Init();

  x = FLOAT32(p.x);
  y = FLOAT32(p.y);
  z = FLOAT32(p.z);
  nx = FLOAT32(p.nx / g_fNORMALFACTOR);
  ny = FLOAT32(p.ny / g_fNORMALFACTOR);
  nz = FLOAT32(p.nz / g_fNORMALFACTOR);
}

STomoVoxel::~STomoVoxel()
{
  Reset();
}

STomoVoxel::STomoVoxel(const STomoVoxel& Source)
{
  Init();
  _Copy(Source);
}

void	STomoVoxel::operator=(const STomoVoxel& Source)
{
  Reset();
  _Copy(Source);
}

void	STomoVoxel::DumpTo(FLOAT32* _data_6i) const
{
  memcpy(_data_6i, fData, sfData);
}

void	STomoVoxel::_Copy(const STomoVoxel& Source)
{
  memcpy(fData, Source.fData, sfData);
  iTypeByte = Source.iTypeByte;
}

void	STomoVoxel::Reset(void)
{
  Init();
}

void	STomoVoxel::Init(void)
{
  memset(fData, 0x00, sfData);
  iTypeByte = 0;
}


TVIterator _find(TVVector& pxls, const STomoVoxel& rhs)
{
  TVIterator pIt = pxls.end();
  for (pIt = pxls.begin() ; pIt != pxls.end() ; pIt++)
  {
    if (*pIt == rhs)
    {
      return pIt;
    }
  }
  return pxls.end();
}

bool operator==(const STomoVoxel& lhs, const STomoVoxel& rhs)
{
  return (lhs.x == rhs.x && lhs.y == rhs.y && lhs.z == rhs.z);
}

TVVector& operator<<(TVVector& lhs, const TVVector& rhs_pxls)
{
  for( auto& r_pxl : rhs_pxls)
  { 
    TVIterator pIt = _find( lhs, r_pxl);
    if (pIt == lhs.end())
    {
      lhs.push_back( r_pxl);
    }
    else
    {
      pIt->iTypeByte |= r_pxl.iTypeByte;
    }
  }
  return lhs;
}


void  moveVoxelCornersToOrigin(TVVector& CVV_vxls)
{
  FLOAT32 min[3] = { 1e5,1e5,1e5 };
  for (auto& vxl : CVV_vxls)
  {
    min[0] = _min(vxl.x, min[0]);
    min[1] = _min(vxl.y, min[1]);
    min[2] = _min(vxl.z, min[2]);
  }

  for (auto& vxl : CVV_vxls)
  {
    vxl.x -= min[0];
    vxl.y -= min[1];
    vxl.z -= min[2];
  }
}

void  moveVoxelCentersToOrigin(TVVector& CVV_vxls)
{
  if(CVV_vxls.size()==0) return ;

  FLOAT32 center[3] = { 0,0,0 };
  for (auto& vxl : CVV_vxls)
  {
    center[0] += vxl.x;
    center[1] += vxl.y;
    center[2] += vxl.z;
  }

  center[0] /= FLOAT32(CVV_vxls.size());
  center[1] /= FLOAT32(CVV_vxls.size());
  center[2] /= FLOAT32(CVV_vxls.size());

  for (auto& vxl : CVV_vxls)
  {
    vxl.x -= center[0];
    vxl.y -= center[1];
    vxl.z -= center[2];
  }
}

void  rotateVoxels(TVVector& CV_vxls, FLOAT32 yaw, FLOAT32 pitch, FLOAT32 roll)
{
  SMatrix4f m3x3( yaw, pitch, roll);
  FLOAT32 min[3] = { 1e5,1e5,1e5 };
  for (auto& vxl : CV_vxls)
  {
    m3x3.Dot(vxl.crd, vxl.crd);
    m3x3.Dot(vxl.nrm, vxl.nrm);
  }
}


STomoVoxel getMid(const STomoVoxel& a, const STomoVoxel& b)
{
  STomoVoxel ab;
  for (int i = 0; i < 3; i++)
  {
    ab.crd[i] = (a.crd[i] + b.crd[i]) * FLOAT32(0.5f);
    ab.nrm[i] = (a.nrm[i] + b.nrm[i]) * FLOAT32(0.5f);
  }

  return ab;
}

FLOAT32 distance(const STomoVoxel& a , const STomoVoxel& b)
{
  FLOAT32 dist = 0;
  dist += (a.x - b.x) * (a.x - b.x);
  dist += (a.y - b.y) * (a.y - b.y);
  dist += (a.z - b.z) * (a.z - b.z);
  dist = sqrt(dist);
  return dist;
}