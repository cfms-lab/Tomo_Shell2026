#pragma once
#include "..\Tomo_types.h"

using namespace Tomo;

class DLLEXPORT STomoAABB3Df
{
public:
  STomoAABB3Df();
  STomoAABB3Df(const STomoAABB3Df& Source);
  void	operator=(const STomoAABB3Df& Source);
  void	_Copy(const STomoAABB3Df& Source);
  ~STomoAABB3Df();

  void	Reset(void);
  void	Init(void);

  static const int ndData = 6;
  static const int sdData = sizeof(FLOAT32) * ndData;
  union
  {
    struct { FLOAT32	x_min, y_min, x_max, y_max, z_min, z_max;};
    struct { FLOAT32	x0, y0, x1, y1, z0, z1;};
    FLOAT32 dData[ndData];
  };

  void	operator<<(const FLOAT32* _d);
  void  Set(MESH_ELE_ID_TYPE nV, FLOAT32* vtx);
  void  GetCenter(FLOAT32* center);

  FLOAT32	GetXSpan(void) const;
  FLOAT32	GetYSpan(void) const;
  FLOAT32	GetZSpan(void) const;
  FLOAT32	GetMaxSpan(void) const;
};
