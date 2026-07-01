#include "pch.h"
#include "STomoAABB2D.h"

void  STomoAABB2D::GetAABB2D(MESH_ELE_ID_TYPE _nVtx, FLOAT32* _pVtx)
{
  x0 = INT16(1e4);  x1 = INT16(-1e4);
  y0 = INT16(1e4);  y1 = INT16(-1e4);
  for (MESH_ELE_ID_TYPE v = 0; v < _nVtx; v++)
  {
    INT16 x = INT16(_pVtx[v * 3 + 0]); //FLOAT64 -> INT64
    INT16 y = INT16(_pVtx[v * 3 + 1]); //FLOAT64 -> INT64
    x0 = _min(x, x0);
    y0 = _min(y, y0);
    x1 = _max(x, x1);
    y1 = _max(y, y1);
  }
  //AABB2D;
}
