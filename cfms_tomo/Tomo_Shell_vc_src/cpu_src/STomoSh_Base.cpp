#include "pch.h"
#include "STomoSh_Base.h"

using namespace Tomo;

STomoSh_Base::STomoSh_Base()
{
  Init();
}

STomoSh_Base::~STomoSh_Base()
{
  Reset();
}

STomoSh_Base::STomoSh_Base(const STomoSh_Base& Source)
{
  Init();
  _Copy(Source);
}

void	STomoSh_Base::operator=(const STomoSh_Base& Source)
{
  Reset();
  _Copy(Source);
}

void	STomoSh_Base::_Copy(const STomoSh_Base& Source)
{
  printer_info = Source.printer_info;
  slotVec = Source.slotVec;

}

void	STomoSh_Base::Reset(void)
{
  slotVec.clear();
}

void	STomoSh_Base::Init(void)
{
  slotVec.clear();
}

void  STomoSh_Base::Rotate(void)
{
  if (printer_info.pVtx1 == nullptr) printer_info.pVtx1 = new FLOAT32[printer_info.nVtx * 3 + 2];
  if (printer_info.pNrm1 == nullptr) 
  {
#ifdef _USE_VTX_NRM_FOR_PIXEL
    printer_info.pNrm1 = new FLOAT32[printer_info.nVtx * 3 + 2];
#else
    printer_info.pTriNrm1 = new TOMO_FLOAT32[printer_info.nTri * 3 + 2];
#endif
  }
    
  FLOAT32* V0 = printer_info.rpVtx0;//raw data before rotation. do not change these.
  FLOAT32* N0 = printer_info.rpVtxNrm0;//raw data before rotation. do not change these.
  FLOAT32* Vtx = printer_info.pVtx1;//after rotation.
  FLOAT32* Nrm = printer_info.pNrm1;//after rotation.

  STomoAABB3Df AABB3Df;
  FLOAT32 center[3];

  #if 0
  for (MESH_ELE_ID_TYPE v = 0; v < rp_printer_info.nVtx; v++)
    //size up
    *(Vtx + v * 3 + 0) = *(V0 + v * 3 + 0) * TOMO_FLOAT32(iVOXELFACTOR);
    *(Vtx + v * 3 + 1) = *(V0 + v * 3 + 1) * TOMO_FLOAT32(iVOXELFACTOR);
    *(Vtx + v * 3 + 2) = *(V0 + v * 3 + 2) * TOMO_FLOAT32(iVOXELFACTOR);
  }
  #endif

  //move center of mass to origin.
  AABB3Df.Set(printer_info.nVtx, V0);
  AABB3Df.GetCenter(center);
  for (MESH_ELE_ID_TYPE  v = 0; v < printer_info.nVtx; v++)
  {
    *(Vtx + v * 3 + 0) = *(V0 + v * 3 + 0) - center[0];
    *(Vtx + v * 3 + 1) = *(V0 + v * 3 + 1) - center[1];
    *(Vtx + v * 3 + 2) = *(V0 + v * 3 + 2) - center[2];
  }

  //rotate
  SMatrix4f Rot(printer_info.yaw, printer_info.pitch, printer_info.roll);
  for (MESH_ELE_ID_TYPE v = 0; v < printer_info.nVtx; v++)
  {
    Rot.Dot(&Vtx[v * 3], &Vtx[v * 3]);
    #ifdef _USE_VTX_NRM_FOR_PIXEL
    Rot.Dot(&N0[v * 3], &Nrm[v * 3]);
    #endif
  }

 #ifndef _USE_VTX_NRM_FOR_PIXEL
  for (MESH_ELE_ID_TYPE t = 0; t < printer_info.nTri; t++)
 
  {
    m3x3.Dot(&N0[t * 3], &Nrm[t * 3]);
  }
#endif
 
  //translate so that corner lies on the origin.
  AABB3Df.Set(printer_info.nVtx, Vtx);
  for (MESH_ELE_ID_TYPE v = 0; v < printer_info.nVtx; v++)
  {
    *(Vtx + v * 3 + 0) -= AABB3Df.x_min - printer_info.BedOuterBound;
    *(Vtx + v * 3 + 1) -= AABB3Df.y_min - printer_info.BedOuterBound;
    *(Vtx + v * 3 + 2) -= AABB3Df.z_min;
  }

  //return matrix data
  FLOAT32 m = - center[0];
  FLOAT32 n = - center[1];
  FLOAT32 o = - center[2];

  FLOAT32 u = - (AABB3Df.x_min - printer_info.BedOuterBound);
  FLOAT32 v = - (AABB3Df.y_min - printer_info.BedOuterBound);
  FLOAT32 w = - (AABB3Df.z_min);

  mat4x4 = Rot;
  mat4x4.Data[0][3] = u + Rot.Data[0][0] * m + Rot.Data[0][1] * n + Rot.Data[0][2] * o;
  mat4x4.Data[1][3] = v + Rot.Data[1][0] * m + Rot.Data[1][1] * n + Rot.Data[1][2] * o;
  mat4x4.Data[2][3] = w + Rot.Data[2][0] * m + Rot.Data[2][1] * n + Rot.Data[2][2] * o;
     

#ifdef _DEBUG
  AABB3Df.Set(printer_info.nVtx, Vtx);
#endif
}

