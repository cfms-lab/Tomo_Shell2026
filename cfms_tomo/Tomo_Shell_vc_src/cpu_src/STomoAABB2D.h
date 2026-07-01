#pragma once
#include "..\Tomo_types.h"

using namespace Tomo;

class DLLEXPORT STomoAABB2D
{
public:
  STomoAABB2D(INT16 _x0 = 0, INT16 _y0 = 0, INT16 _x1 = 0, INT16 _y1 = 0)
    : x0(_x0), y0(_y0), x1(_x1), y1(_y1) {}
  STomoAABB2D(INT16* aabb2d) :
    x_min(aabb2d[0]),
    y_min(aabb2d[1]),
    x_max(aabb2d[2]),
    y_max(aabb2d[3]) {}
  ~STomoAABB2D() {}

  static const int niData = 4;
  static const int siData = sizeof(INT16) * niData;
  union
  {
    struct { INT16	x_min, y_min, x_max, y_max; };
    struct { INT16	x0, y0, x1, y1; };
    INT16 iData[niData];
  };

  INT16 nRow(void) const { return x1 - x0 + 1; }
  INT16 nCol(void) const { return y1 - y0 + 1; }

  void  GetAABB2D(MESH_ELE_ID_TYPE _nVtx, FLOAT32* _pVtx);
};

