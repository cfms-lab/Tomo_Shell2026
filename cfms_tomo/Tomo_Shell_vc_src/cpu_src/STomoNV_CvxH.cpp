#include "pch.h"
#include "STomoNV_CvxH.h"
#include <iostream> //cout. for debug
#include <omp.h>
#include <algorithm> //std::sort
#include "SMatrix33f.h"

using namespace Tomo;

STomoNV_CvxH::STomoNV_CvxH() : STomoNV_Base()
{

}

STomoNV_CvxH::~STomoNV_CvxH()
{
  Reset();
}

STomoNV_CvxH::STomoNV_CvxH(const STomoNV_CvxH& Source)
{
  Init();
  _Copy(Source);
}

void	STomoNV_CvxH::operator=(const STomoNV_CvxH& Source)
{
  Reset();
  _Copy(Source);
}

void	STomoNV_CvxH::_Copy(const STomoNV_CvxH& Source)
{
  STomoNV_Base::_Copy(Source);
}

void	STomoNV_CvxH::Reset(void)
{
  STomoNV_Base::Reset();
  Init();
}

void	STomoNV_CvxH::Init(void)
{
  STomoNV_Base::Init();

  shadow_v3[0] = 0.;
  shadow_v3[1] = 0.;
  shadow_v3[2] = 1.;
}


void  STomoNV_CvxH::Rotate(void)
{
  //rotate
  FLOAT32 _shadow_v3[3] = { 0., 0., 1. };
  //SMatrix33f m3x3(printer_info.yaw, printer_info.pitch, printer_info.roll);
  SMatrix33f m3x3(printer_info.pitch, printer_info.yaw, printer_info.roll);
  m3x3.Dot(_shadow_v3, shadow_v3);

}

void  STomoNV_CvxH::Pixelize(const TVVector& CVV_vxls)
{

}

void  STomoNV_CvxH::Pairing(void)
{

}

void  STomoNV_CvxH::Calculate(void)//calculate global vol/mass value.
{
  getCHVtc();
  getCHVss();

  //vm_info.VolToMass(printer_info);

  vm_info.Vo_clad = printer_info.surface_area * printer_info.wall_thickness;
  vm_info.Vo = vm_info.Va - vm_info.Vb;
  vm_info.Vo_core = vm_info.Vo - vm_info.Vo_clad;
  vm_info.Mo_clad = vm_info.Vo_clad * printer_info.Fclad * printer_info.PLA_density;
  vm_info.Mo_core = vm_info.Vo_core * printer_info.Fcore * printer_info.PLA_density;
  vm_info.Mo = vm_info.Mo_core + vm_info.Mo_clad;

  //vm_info.Vss = vm_info.Vtc - vm_info.Vo  - vm_info.Vnv;//implicit
  //vm_info.Vss = vm_info.Vtc - 54476;
  vm_info.Mss = vm_info.Vss * printer_info.PLA_density;

  vm_info.Mbed = vm_info.Vbed * printer_info.wall_thickness * printer_info.PLA_density;
  vm_info.Mtotal = vm_info.Mo + vm_info.Mss + vm_info.Mbed;
}



FLOAT32  STomoNV_CvxH::getCHVtc(void)
{

  int iCHBottom = getCHBottom(shadow_v3);//convex hull vertex, on bottom plate.
  if (iCHBottom < 0) return 0.f;//error

  MESH_ELE_ID_TYPE nTri = printer_info.nCHull_Tri;
  FLOAT32* CvxTriNrm = printer_info.pCHull_TriNrm;
  FLOAT32* CvxTriCenter = printer_info.pCHull_TriCenter;
  FLOAT32* CvxVtx = printer_info.pCHull_Vtx;
  vm_info.Vtc = 0.;//temporarily reset values
  for (MESH_ELE_ID_TYPE t = 0; t < nTri; t++)
  {
    FLOAT32 dot = -_dot(CvxTriNrm + t * 3, shadow_v3);
    if (dot > -g_fMARGIN)//convex hull alpha triangle == TC로 간주.
    {
      FLOAT32 tri_area2D = CvxTriCenter[t * 4 + 3];
      FLOAT32 Ht = vtxToCHDist(CvxTriCenter + t * 4, shadow_v3, CvxVtx + iCHBottom * 3);//Ht가 마이너스가 나오면 에러다.
      FLOAT32 Vt = Ht * tri_area2D;//triangle pillar volume
      vm_info.Vtc += Vt;
    }
  }
  return vm_info.Vtc;
}


FLOAT32 STomoNV_CvxH::vtxToCHDist(FLOAT32* cnt_v3, FLOAT32* shadow_v3, FLOAT32* chull_v3)
{
  FLOAT32 dist = 0.;
  dist = (chull_v3[0] - cnt_v3[0]) * shadow_v3[0];
  dist += (chull_v3[1] - cnt_v3[1]) * shadow_v3[1];
  dist += (chull_v3[2] - cnt_v3[2]) * shadow_v3[2];
  return dist;
}

int STomoNV_CvxH::getCHBottom(FLOAT32* shadow_v3)
{
  std::vector<FLOAT32> vecDist;
  FLOAT32 origin[3] = { 0., 0., 0 };
  for (int v = 0; v < printer_info.nCHull_Vtx; v++)
  {
    FLOAT32 dist = vtxToCHDist(origin, shadow_v3, printer_info.pCHull_Vtx + v * 3);//find printer bed direction in advance.
    vecDist.push_back(dist);
  }
  auto maxDistIt = std::max_element(vecDist.begin(), vecDist.end());
  int id = (int)std::distance(vecDist.begin(), maxDistIt);
  if (id >= printer_info.nCHull_Vtx) id = -1;//error
  return id;
}

FLOAT32  STomoNV_CvxH::getCHVss(void)
{
  int iCHBottom = getCHBottom(shadow_v3);//find convex hull vertex, on bottom plate.
  if (iCHBottom < 0) return 0.f;//error

  MESH_ELE_ID_TYPE nTri = printer_info.nTri;
  FLOAT32* Vtx0 = printer_info.rpVtx0;
  FLOAT32* TriNrm0 = printer_info.rpTriNrm0;
  FLOAT32* TriCenter = printer_info.pTriCenter;
  FLOAT32* CvxVtx0 = printer_info.pCHull_Vtx;
  FLOAT32    _threshold = sin(printer_info.theta_c) * -1.f;//shadow_v3은 방향이 아래를 향하고 있으므로 부호를 반대로.
  vm_info.Vss = vm_info.Vnv = vm_info.Va = vm_info.Vb = 0.;//temporarily reset values
  for (MESH_ELE_ID_TYPE t = 0; t < nTri; t++)
  {
    FLOAT32 dot = _dot(TriNrm0 + t * 3, shadow_v3) * -1.f;//shadow_v3은 방향이 아래를 향하고 있으므로 부호를 반대로.
    FLOAT32 tri_area2D = TriCenter[t * 4 + 3] * ::fabs(dot);
    FLOAT32 Ht = vtxToCHDist(TriCenter + t * 4, shadow_v3, CvxVtx0 + iCHBottom * 3);//Ht가 마이너스가 나오면 에러다.
    FLOAT32 Vt = Ht * tri_area2D;//triangle pillar volume

    if (dot > g_fMARGIN) { vm_info.Va += Vt; }
    else if (dot < -g_fMARGIN) {
      vm_info.Vb += Vt;
      if (dot > _threshold) { vm_info.Vnv += Vt; }//implicit
      else { vm_info.Vss += Vt; }//explicit
    }
  }//end of for(t..)
  return vm_info.Vss;
}

