#include "pch.h"
#include <cstring>//memcpy()
#include "STomoAABB3Df.h"

using namespace Tomo;

STomoAABB3Df::STomoAABB3Df()
{
  Init();
}

STomoAABB3Df::~STomoAABB3Df()
{
  Reset();
}

STomoAABB3Df::STomoAABB3Df(const STomoAABB3Df& Source)
{
  Init();
  _Copy(Source);
}

void	STomoAABB3Df::operator=(const STomoAABB3Df& Source)
{
  Reset();
  _Copy(Source);
}

void	STomoAABB3Df::_Copy(const STomoAABB3Df& Source)
{
  memcpy(dData, Source.dData, sdData);
}

void	STomoAABB3Df::Reset(void)
{
  Init();
}

void	STomoAABB3Df::Init(void)
{
  //memset(dData, 0x00, sdData);
  x_min = y_min = z_min = FLOAT32(1e5);
  x_max = y_max = z_max = FLOAT32(-1e5);
}

void	STomoAABB3Df::operator<<(const FLOAT32* _d)
{
  x_min = _min(x_min, _d[0]);
  y_min = _min(y_min, _d[1]);
  z_min = _min(z_min, _d[2]);

  x_max = _max(x_max, _d[0]);
  y_max = _max(y_max, _d[1]);
  z_max = _max(z_max, _d[2]);
}


void  STomoAABB3Df::Set(MESH_ELE_ID_TYPE nV, FLOAT32* vtx)
{
  Init();
  for (MESH_ELE_ID_TYPE v = 0; v < nV; v++)
  {
    operator<< (vtx + v * 3);
  }
}

void  STomoAABB3Df::GetCenter(FLOAT32* _center)
{
  _center[0] = FLOAT32((x_min + x_max) * 0.5);
  _center[1] = FLOAT32((y_min + y_max) * 0.5);
  _center[2] = FLOAT32((z_min + z_max) * 0.5);
}

FLOAT32 STomoAABB3Df::GetXSpan(void) const {  return x1-x0; }
FLOAT32 STomoAABB3Df::GetYSpan(void) const {  return y1-y0; }
FLOAT32 STomoAABB3Df::GetZSpan(void) const {  return z1-z0; }
FLOAT32 STomoAABB3Df::GetMaxSpan(void) const {  return _max( x1-x0, _max( y1-y0, z1-z0)); }
//------------------------------------------------------------------
