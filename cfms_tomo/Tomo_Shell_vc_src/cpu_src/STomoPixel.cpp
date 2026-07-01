#include "pch.h"
#include "STomoPixel.h"
#include <algorithm> //std::sort()

using namespace Tomo;

STomoPixel::STomoPixel(FLOAT32* _pxl3d, FLOAT32* _nrm3d)
{
    x = INT16(_pxl3d[0]);
    y = INT16(_pxl3d[1]);
    z = INT16(_pxl3d[2]);
  nx = INT16(_nrm3d[0] * g_fNORMALFACTOR);
  ny = INT16(_nrm3d[1] * g_fNORMALFACTOR);
  nz = INT16(_nrm3d[2] * g_fNORMALFACTOR);
  iTypeByte = 0;
}

STomoPixel::STomoPixel(INT16* _data_2i)
{
  memcpy(iData, _data_2i, siData);
}

STomoPixel::~STomoPixel()
{
  Reset();
}

STomoPixel::STomoPixel(const STomoPixel& Source)
{
  Init();
  _Copy(Source);
}

void	STomoPixel::operator=(const STomoPixel& Source)
{
  Reset();
  _Copy(Source);
}

void	STomoPixel::DumpTo(INT16* _data_6i)
{
  memcpy(_data_6i, iData, siData);
}

void	STomoPixel::_Copy(const STomoPixel& Source)
{
  memcpy(iData, Source.iData, siData);
  iTypeByte = Source.iTypeByte;
}

void	STomoPixel::Reset(void)
{
  Init();
}

void	STomoPixel::Init(void)
{
  memset(iData, 0x00, siData);
  iTypeByte = 0;
}

void inline sortSlotByZ(TPVector& slot, bool _Higher)
{
  (_Higher) ?
    std::sort(slot.begin(), slot.end(), _checkHigherPixel) :
    std::sort(slot.begin(), slot.end(), _checkLowerPixel);
}


TPVector removeZNearPxls(TPVector& pxls0)//pxls0 should be already sorted with higher Zvalue first.
{
  auto last = std::unique(pxls0.begin(), pxls0.end(), _checkZNear);
  pxls0.erase(last, pxls0.end());

  return pxls0;
}

TPVector _matchAlternationWRT(const TPVector& slot, const TPVector& ref_slot)
{//slot의 두 점 ni, ni+1 사이에 ref_slot의 아무 점이나 존재하면, slot의 ni를 보존한다.
  size_t nPxl = slot.size();
  TPVector new_slot;
  for (int s = 0; s < nPxl - 1; s++)
  {
    TPConstIterator pIt0 = slot.begin() + s;
    TPConstIterator pIt1 = slot.begin() + s + 1;
    if (_hasPxlBetween(ref_slot, pIt0->z, pIt1->z))
    {
      new_slot.push_back(*pIt0);
    }
  }
  new_slot.push_back(slot.back());
  return new_slot;
}

void _matchPairNumber(TPVector& al_slot, TPVector& be_slot)//Caution: slot은 z값에 대해 오름차순임. obsolete python version.. 
{
  if (al_slot.size() < be_slot.size())
  {
    be_slot.resize(al_slot.size());//be_slot은 z값이 큰 쪽을 삭제.
  }
  else if (al_slot.size() > be_slot.size())
  {
    TPVector temp(al_slot.end() - be_slot.size(), al_slot.end());
    al_slot = temp;//al_slot은 z값이 작은 쪽을 삭제.
  }
}

bool  _hasPxlBetween(const TPVector& slot, INT16 z0, INT16 z1)
{
  for (auto& pxl : slot)
  {
    if ( (z0 <= pxl.z && pxl.z <= z1)
      || (z1 <= pxl.z && pxl.z <= z0))//pxls sorting에 따라 반대일수도 있다.
    {
      return true;
    }
  }
  return false;
}

bool  _checkHigherPixel(const STomoPixel& a, const STomoPixel& b)
{
  return (a.z > b.z);
}

bool  _checkLowerPixel(const STomoPixel& a, const STomoPixel& b)
{
  return (a.z < b.z);
}

bool _checkUnique(const STomoPixel& a, const STomoPixel& b)
{
  return ((a.x == b.x) && (a.y == b.y) && (a.z == b.z));
}

bool  _checkZNear(const STomoPixel& a, const STomoPixel& b)
{
  return (abs(a.z - b.z) <= 1);
}


bool _checkBottomPixel(const STomoPixel& a)
{
  return (a.z == 0);
}

TPVector createShadowCastorPixels(FLOAT32 theta_c_in_Radian, TPVector& _be_pxls, bool _bExplicitSS)
{
  TPVector castor_pxls;
  FLOAT32 threshold = -1. * ::sin(theta_c_in_Radian);
  
  for (auto& be : _be_pxls)
  {
    FLOAT32 nrm[3];
    nrm[2] = be.nz / FLOAT32(g_fNORMALFACTOR);
    if (nrm[2] < -g_fMARGIN )
    {
      FLOAT32 dot = nrm[2];//=_dot(z_axis, nrm);
      if (_bExplicitSS && dot < threshold)
      {
        be.iTypeByte |= typeSSB;
        castor_pxls.push_back(be);
      }
      else if( !_bExplicitSS && dot > threshold)
      {
        be.iTypeByte |= typeNVB;
        castor_pxls.push_back(be);
      }
    }
  }
  return castor_pxls;
}

void _matchPairWRT(TPVector& pxls, const TPVector& ref_pxls)
{
  if (pxls.size() > ref_pxls.size())
  {
    pxls.resize(ref_pxls.size());
  }
}

void  copyPxls(const TPVector& src, TPVector& target)
{
  target.resize((int)(src.size()));
  std::copy(src.begin(), src.end(), target.begin());
}

void  negativeZ(TPVector& pxls)
{
  for (auto& pxl : pxls)
  {
    pxl.z *= -1;
  }
}

void  zero_nZ(TPVector& pxls)
{
  for (auto& pxl : pxls)
  {
    pxl.nz = 0;
  }
}

TPVector createVoPixels(const TPVector& alpha, const TPVector& beta, const STomoAABB2D& AABB2D)
{
  TPVector beta_minus;
  copyPxls(beta, beta_minus);
  negativeZ(beta_minus);
  TPVector pxls;
  copyPxls(alpha, pxls);
  pxls.insert(pxls.end(), beta_minus.begin(), beta_minus.end());
  TPVectorpp slots = pxlsToSlots(pxls, AABB2D);//이거 필요한가??->필요하다. ss_slots과는 다르다.
  pxls = addZs(slots, AABB2D);
  deleteSlots(slots, AABB2D);//이거 필요한가??->필요하다. ss_slots과는 다르다.
  return (pxls);
}

STomoPixel  getNVA(const STomoPixel& nvb, const TPVector& al_slot)
{
  TPVector al_slot2;
  copyPxls(al_slot, al_slot2);
  sortSlotByZ(al_slot2, true);
  INT16 z0 = nvb.z;
  for (auto& al_pxl : al_slot2)
  {
    if (al_pxl.z <= z0)//등호 꼭 필요함.
    {
      return al_pxl;
    }
  }
  STomoPixel bottom(nvb.x, nvb.y, 0);
  return bottom;
}


TPVector createNVAPixels(const TPVector& nvB0, const TPVector& alpha0, const STomoAABB2D& AABB2D)
{
  TPVector pxls;
  TPVectorpp al_slots = pxlsToSlots(alpha0, AABB2D);
  for (auto& nvb : nvB0)
  {
    INT16 x = nvb.x;
    INT16 y = nvb.y;
    STomoPixel new_nbA = getNVA(nvb, al_slots[x - AABB2D.x_min][y - AABB2D.y_min]);
    pxls.push_back(new_nbA);
  }
  return pxls;
}

TPVector createTCPixels(const TPVector& _al_pxls, const STomoAABB2D& AABB2D)
{
  TPVectorpp  slots = pxlsToSlots(_al_pxls, AABB2D);//?
  TPVector pxls = getHighestPxls(slots, AABB2D);
  uniqueIntList(pxls);
  return pxls;
}

TPVector createSSPixels(
  const TPVector& alpha, const TPVector& beta,
  const TPVector& tc0,
  const TPVector& nvB, const TPVector& nvA0,
  const STomoAABB2D& AABB2D)
{
  TPVector alpha_minus;
  copyPxls(alpha, alpha_minus);
  negativeZ(alpha_minus);

  TPVector nvB_minus;
  copyPxls(nvB, nvB_minus);
  negativeZ(nvB_minus);

  TPVector tc1;
  copyPxls(tc0, tc1);

  TPVector nva1;
  copyPxls(nvA0, nva1);

  zero_nZ(alpha_minus);// # we need only Nz of beta pixels
  zero_nZ(nvB_minus);
  zero_nZ(tc1);
  zero_nZ(nva1);

  TPVector pxls;
  pxls.insert(pxls.end(), alpha_minus.begin(), alpha_minus.end());
  pxls.insert(pxls.end(), beta.begin(), beta.end());
  pxls.insert(pxls.end(), tc1.begin(), tc1.end());
  pxls.insert(pxls.end(), nvB_minus.begin(), nvB_minus.end());
  pxls.insert(pxls.end(), nva1.begin(), nva1.end());

  TPVectorpp temp_slots = pxlsToSlots(pxls, AABB2D);
  TPVector SS_pxls = addZs(temp_slots, AABB2D);
  deleteSlots(temp_slots, AABB2D);

  return SS_pxls;
}

void uniqueIntList(TPVector& pxls0)
{
  TPVector pxls1;
  auto last = std::unique(pxls0.begin(), pxls0.end(), _checkUnique);
  pxls0.erase(last, pxls0.end());
}


TPVectorpp newSlots(const STomoAABB2D& AABB2D)
{
  INT16 nRow = AABB2D.nRow();
  INT16 nCol = AABB2D.nCol();
  TPVectorpp slots = new TPVector * [nRow + 1];
  for (int i = 0; i < nRow + 1; i++)
  {
    slots[i] = new TPVector[nCol + 1];
  }
  return slots;
}

void  deleteSlots(TPVectorpp slots, const STomoAABB2D& AABB2D)
{
  for (int i = 0; i < AABB2D.x_max; i++)
  {
    delete[] slots[i];
  }
  delete[] slots;
  slots = nullptr;
}

TPVectorpp pxlsToSlots(const TPVector& pxls, const STomoAABB2D& AABB2D)
{
  TPVectorpp slots = newSlots(AABB2D);

  for (auto& pxl : pxls)
  {
    INT16 i = pxl.x - AABB2D.x0; INT16 j = pxl.y - AABB2D.y0;
    slots[i][j].push_back(pxl);
  }

  INT16 nRow = AABB2D.nRow();
  INT16 nCol = AABB2D.nCol();
  for (int i = 0; i < nRow; i++)
  {
    for (int j = 0; j < nCol; j++)
    {
      if (slots[i][j].size() > 1) { sortSlotByZ(slots[i][j]); }
    }
  }
  return slots;
}

void slotsToPxls(TPVectorpp slots, const STomoAABB2D& AABB2D, TPVector& pxls)
{
  pxls.clear();
  INT16 nRow = AABB2D.nRow();
  INT16 nCol = AABB2D.nCol();
  for (int i = 0; i < nRow; i++)
  {
    for (int j = 0; j < nCol; j++)
    {
      pxls.insert(pxls.end(), slots[i][j].begin(), slots[i][j].end());
    }
  }
}

void removeZNearPxls(TPVectorpp slots, const STomoAABB2D& AABB2D)
{
  INT16 nRow = AABB2D.nRow();
  INT16 nCol = AABB2D.nCol();
  for (int i = 0; i < nRow; i++)
  {
    for (int j = 0; j < nCol; j++)
    {
      slots[i][j] = removeZNearPxls(slots[i][j]);
    }
  }
}

TPVector getHighestPxls(TPVectorpp slots0, const STomoAABB2D& AABB2D)
{
  TPVector pxls;
  INT16 nRow = AABB2D.nRow();
  INT16 nCol = AABB2D.nCol();
  for (int i = 0; i < nRow; i++)
  {
    for (int j = 0; j < nCol; j++)
    {
      if (slots0[i][j].size() > 0)
      {
        STomoPixel debug = slots0[i][j].rbegin()[0];
        pxls.push_back(debug);//assume slots are already sorted w.r.t. Z
      }
    }
  }
  return pxls;
}

STomoPixel _addZ(const TPVector& pxls, std::function<FLOAT32(FLOAT32)> wFunc)
{
  INT16 z_sum = 0;
  if(wFunc==nullptr)
  {
    for (auto& pxl : pxls)
    {
      z_sum += pxl.z;
    }
  }
  else
  {
    for (auto& pxl : pxls)
    {
      FLOAT32 theta_in_radian = ::asin(_abs(FLOAT32(pxl.nz / g_fNORMALFACTOR)));
      FLOAT32 weight = wFunc(theta_in_radian);
      z_sum += pxl.z * weight;
    }
  }
  STomoPixel new_pxl = *(pxls.begin());
  new_pxl.z = z_sum;
  return new_pxl;
}
    
TPVector addZs(TPVectorpp slots0, const STomoAABB2D& AABB2D, 
  std::function<FLOAT32(FLOAT32)> wFunc)
{
  TPVector pxls;
  for (int i = 0; i < AABB2D.x_max; i++)
  {
    for (int j = 0; j < AABB2D.y_max; j++)
    {
      if (slots0[i][j].size() > 0)
      {
        STomoPixel new_pxl = _addZ(slots0[i][j], wFunc);
        pxls.push_back(new_pxl);
      }
    }
  }
  return pxls;
}

void deleteBottomPxls(TPVector& pxls)
{
  auto zeroIt = std::find_if(pxls.begin(), pxls.end(), _checkBottomPixel);
  while (zeroIt != pxls.end())
  {
    pxls.erase(zeroIt);
    zeroIt = std::find_if(pxls.begin(), pxls.end(), _checkBottomPixel);
  };
}

void deleteNoise(TPVector& pxls, INT16 z_min, INT16 z_max)
{
  for (TPIterator pIt = pxls.begin(); pIt != pxls.end();)
  {
    if (pIt->z < z_min || pIt->z < z_max)
    {
      pIt = pxls.erase(pIt);
    }
    else
    {
      ++pIt;
    }
  }
}

void matchAlBeSlots(TPVectorpp& al_slots, TPVectorpp& be_slots, const STomoAABB2D& AABB2D)
{//#pair matcing for noise suppression (Aassume that number of alpha and beta pixels are same for closed volume object)
  INT16 nRow = AABB2D.nRow();
  INT16 nCol = AABB2D.nCol();
  for (int i = 0; i < nRow; i++)
  {
    for (int j = 0; j < nCol; j++)
    {
      if (al_slots[i][j].size() > 1) al_slots[i][j] = _matchAlternationWRT(al_slots[i][j], be_slots[i][j]);
      if (be_slots[i][j].size() > 1) be_slots[i][j] = _matchAlternationWRT(be_slots[i][j], al_slots[i][j]);
      _matchPairNumber(al_slots[i][j], be_slots[i][j]);
    }
  }
}

void matchSlotsWRT(TPVectorpp& slots, TPVectorpp& ref_slots, const STomoAABB2D& AABB2D)
{
  INT16 nRow = AABB2D.nRow();
  INT16 nCol = AABB2D.nCol();
  for (int i = 0; i < nRow; i++)
  {
    for (int j = 0; j < nCol; j++)
    {
      if (slots[i][j].size() > 0)  _matchPairWRT(slots[i][j], ref_slots[i][j]);
    }
  }
}

TPIterator _find(TPVector& pxls, const STomoPixel& rhs)
{
  TPIterator pIt = pxls.end();
  for (pIt = pxls.begin() ; pIt != pxls.end() ; pIt++)
  {
    if (*pIt == rhs)
    {
      return pIt;
    }
  }
  return pxls.end();
}

bool operator==(const STomoPixel& lhs, const STomoPixel& rhs)
{
  return (lhs.x == rhs.x && lhs.y == rhs.y && lhs.z == rhs.z);
}

TPVector& operator<<(TPVector& lhs, const TPVector& rhs_pxls)
{
  for( auto& r_pxl : rhs_pxls)
  { 
    TPIterator pIt = _find( lhs, r_pxl);
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
