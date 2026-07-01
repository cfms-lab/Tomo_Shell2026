#include "pch.h"
#include "STomoSh_TMPxl.h"
#include <iostream> //cout. for debug
#include <omp.h>


using namespace Tomo;

STomoSh_TMPxl::STomoSh_TMPxl() : STomoSh_Base()
{

}

STomoSh_TMPxl::~STomoSh_TMPxl() 
{
  Reset();
}

STomoSh_TMPxl::STomoSh_TMPxl(const STomoSh_TMPxl& Source)
{
  Init();
  _Copy(Source);
}

void	STomoSh_TMPxl::operator=(const STomoSh_TMPxl& Source)
{
  Reset();
  _Copy(Source);
}

void	STomoSh_TMPxl::_Copy(const STomoSh_TMPxl& Source)
{
  STomoSh_Base::_Copy(Source);
}

void	STomoSh_TMPxl::Reset(void)
{
  STomoSh_Base::Reset();
}

void	STomoSh_TMPxl::Init(void)
{
  STomoSh_Base::Init();
}

void STomoSh_TMPxl::pxlsToSlots(TPVector& _pxls)
{
  INT16 shell_z_offset = INT16(printer_info.shell_thickness + FLOAT32(0.999));

  for (auto& pxl : _pxls)//sparse data. slow.
  {
    FLOAT32 nrm[3] = { pxl.nx / g_fNORMALFACTOR, pxl.ny / g_fNORMALFACTOR, pxl.nz / g_fNORMALFACTOR };

    if(nrm[2] >  g_fMARGIN)
    {
      if (printer_info.bShellMesh && printer_info.shell_thickness > g_fMARGIN)
      {
        STomoPixel sub_pxl(
          pxl.x, pxl.y, pxl.z - shell_z_offset,//Note: put the subsidiary beta pixel under the alpha
          INT16(nrm[0] * -g_fNORMALFACTOR),
          INT16(nrm[1] * -g_fNORMALFACTOR),
          INT16(nrm[2] * -g_fNORMALFACTOR),
          pxl.iTypeByte | typeBe);
        _insert_to_pxls(sub_pxl);
      }

      pxl.iTypeByte |= typeAl;
      _insert_to_pxls( pxl);

    }
    else// if (nrm[2] < -g_fMARGIN)  
    {      
      if (printer_info.bShellMesh && printer_info.shell_thickness > g_fMARGIN)
      {
        STomoPixel sub_pxl(
          pxl.x, pxl.y, pxl.z + shell_z_offset,//Note: put the subsidiary alpha pixel above the beta
          INT16(nrm[0] * -g_fNORMALFACTOR),
          INT16(nrm[1] * -g_fNORMALFACTOR),
          INT16(nrm[2] * -g_fNORMALFACTOR),
          pxl.iTypeByte | typeAl);
        _insert_to_pxls(sub_pxl);
      }

      pxl.iTypeByte |= typeBe;
      _insert_to_pxls( pxl);

    }

  }
}

void inline STomoSh_TMPxl::_insert_to_pxls(const STomoPixel& pxl)
{
  INT16 nCol = AABB2D.nCol();
  INT16 slot_id = (pxl.x - AABB2D.x0) * (nCol - 1) + (pxl.y - AABB2D.y0);//주의: nCol() = y1 - y0 + 1 이니까, coㅣ 갯수는 nCol()-1이다.
  TPSlotIterator sIt = (slotVec.begin() + slot_id);
  TPVector& target_pxls = sIt->pxls;
  target_pxls.push_back(pxl);
}


TPVector  STomoSh_TMPxl::slotsToPxls(enumPixelType _type)
{
  TPVector pxls;

  for (auto& slot : slotVec)
  {
    TPVector new_pxls = slot.slotToPxls(_type);
    pxls.insert(pxls.end(), new_pxls.begin(), new_pxls.end());
  }

  return pxls;
}
void STomoSh_TMPxl::triPixel(
  FLOAT32* _v0, FLOAT32* _v1, FLOAT32* _v2,
  FLOAT32* n0, FLOAT32* n1, FLOAT32* n2,
  TPVector& tri_pxls)
{
  FLOAT32 v0[3] = {}, v1[3] = {}, v2[3] = {};

  for (int i = 0; i < 3; i++)
  {
    v0[i] = _v0[i] + g_fMARGIN;
    v1[i] = _v1[i] + g_fMARGIN;
    v2[i] = _v2[i] + g_fMARGIN;
  }

  int x0 = int(_min(_min(v0[0], v1[0]), v2[0]));
  int y0 = int(_min(_min(v0[1], v1[1]), v2[1]));
  int x1 = int(_max(_max(v0[0], v1[0]), v2[0]));
  int y1 = int(_max(_max(v0[1], v1[1]), v2[1]));

  FLOAT32 HALF_VOXEL_SIZE = printer_info.dVoxel * 0.5;
  FLOAT32 v_center[3] = { 0.,0.,HALF_VOXEL_SIZE };

  for (int x = x0; x <= x1; x++)//Caution! "x <= x1", not "x < x1"
  {
    v_center[0] = FLOAT32(x + g_fMARGIN + HALF_VOXEL_SIZE);
    for (int y = y0; y <= y1; y++)//Caution! "y <= y1", not "y < y1"
    {
      v_center[1] = FLOAT32(y + g_fMARGIN + HALF_VOXEL_SIZE);
      FLOAT32 u, v, w;
      if (_getBaryCoord(v_center, v0, v1, v2, u, v, w))
      {
        FLOAT32 pxl[3], nrm[3];
        _bary_product(v0, v1, v2, u, v, w, pxl);
        _bary_product(n0, n1, n2, u, v, w, nrm);
        STomoPixel new_pxl(pxl, nrm);
        tri_pxls.push_back(new_pxl);
      }
    }
  }

  if( tri_pxls.size() == 0)//exceptional case. triangle is as small as 1 pixel. not a desirable situation.
  {
    FLOAT32 tri_center[3];
    for (int i = 0; i < 3; i++)    {      tri_center[i] = (_v0[i] + _v1[i] + _v2[i])*0.333333 + g_fMARGIN;    }

    STomoPixel new_pxl(tri_center, n0);
    tri_pxls.push_back(new_pxl);
  }
}


void  STomoSh_TMPxl::Pixelize()
{
  FLOAT32* Vtx = printer_info.pVtx1;
  FLOAT32* TriNrm = printer_info.pNrm1;
  slotVec.clear();

  //find AABB2D
  AABB2D.GetAABB2D( printer_info.nVtx, Vtx);

  //create slotVec
  INT16 nRow = AABB2D.nRow();
  INT16 nCol = AABB2D.nCol();
  for (INT16 i = 0; i < nRow; i++)//Caution! not "i =< nRow"
  {
    for (INT16 j = 0; j < nCol; j++)
    {
      STPSlot new_slot;
      new_slot.X = AABB2D.x0 + i;
      new_slot.Y = AABB2D.y0 + j;
      slotVec.push_back(new_slot);
    }
  }

  //put pixels to slots
  for (MESH_ELE_ID_TYPE t = 0; t < printer_info.nTri; t++)
  {
    MESH_ELE_ID_TYPE t0 = printer_info.rpTri0[t * 3 + 0];
    MESH_ELE_ID_TYPE t1 = printer_info.rpTri0[t * 3 + 1];
    MESH_ELE_ID_TYPE t2 = printer_info.rpTri0[t * 3 + 2];
    TPVector tri_pxls;
    triPixel(
      &Vtx[t0 * 3], &Vtx[t1 * 3], &Vtx[t2 * 3],
#ifdef _USE_VTX_NRM_FOR_PIXEL
      & TriNrm[t0 * 3], & TriNrm[t1 * 3], & TriNrm[t2 * 3],
#else
      &TriNrm[t * 3], &TriNrm[t * 3], &TriNrm[t * 3],
#endif
      tri_pxls);
    pxlsToSlots( tri_pxls);//to slots, with typeByte.
  }
}
  
void  STomoSh_TMPxl::Pairing(void)
{
  for (auto& slot : slotVec)
  {
    slot.Pairing( printer_info.theta_c, printer_info.bUseExplicitSS);
  }
}

  
void  STomoSh_TMPxl::Calculate(void)//calculate global vol/mass value.
{
  for (auto& slot : slotVec)
  {
    slot.Calculate();
  }

  vm_info.Init();
  for (auto& slot : slotVec)
  {
    vm_info.Va  += slot.vm_info.Va;
    vm_info.Vb  += slot.vm_info.Vb;
    vm_info.Vtc += slot.vm_info.Vtc;
    vm_info.Vnv += slot.vm_info.Vnv;
    vm_info.Vo  += slot.vm_info.Vo;
    vm_info.Vss += slot.vm_info.Vss;
#ifdef _DEBUG
    vm_info.SS_vol += slot.vm_info.SS_vol;//debug
#endif
  }
  
  vm_info.VolToMass(printer_info);
}

#if 1
TPVector STomoSh_TMPxl::GetSSPixels(bool _bUseExplicitSS)
{
  TPVector ss_pxls;
  for (auto& slot : slotVec)
  {
    TPVector new_pxls = slot.GetSSPxls(_bUseExplicitSS);
    ss_pxls.insert(ss_pxls.end(), new_pxls.begin(), new_pxls.end());
  }
  return ss_pxls;
}
#endif


void STomoSh_TMPxl::GenerateBed(void) //ToDo.
{
}