#include "pch.h"
#include <algorithm> //std::sort()
#include <iostream>//std::cout
#include "STomoTriangle.h"
#include "SMatrix4f.h"


using namespace Tomo;

STomoTriangle::STomoTriangle()
{
  Init();
}

STomoTriangle::STomoTriangle(const STomoVoxel& a, const STomoVoxel& b, const STomoVoxel& c)
{
  Init();

  Vtx[0] = a;
  Vtx[1] = b;
  Vtx[2] = c;

  AABB << Vtx[0].crd;
  AABB << Vtx[1].crd;
  AABB << Vtx[2].crd;
}


STomoTriangle::~STomoTriangle()
{
  Reset();
}

STomoTriangle::STomoTriangle(const STomoTriangle& Source)
{
  Init();
  _Copy(Source);
}

void	STomoTriangle::operator=(const STomoTriangle& Source)
{
  Reset();
  _Copy(Source);
}

void	STomoTriangle::_Copy(const STomoTriangle& Source)
{
  for (int i = 0; i < iShape; i++)
  {
    Vtx[i] = Source.Vtx[i];
  }

  AABB = Source.AABB;
}

void	STomoTriangle::Reset(void)
{
  Init();
}

void	STomoTriangle::Init(void)
{
  for (int i = 0; i < iShape; i++)
  {
    Vtx[i].Init();
  }
}

void	STomoTriangle::DumpTo(FLOAT32* _vtx3f_nrm1f) const
{
  for (int i = 0; i < iShape; i++)
  {
    _vtx3f_nrm1f[i * 4 + 0] = Vtx[i].crd[0];//x
    _vtx3f_nrm1f[i * 4 + 1] = Vtx[i].crd[1];//y
    _vtx3f_nrm1f[i * 4 + 2] = Vtx[i].crd[2];//z
    _vtx3f_nrm1f[i * 4 + 3] = Vtx[i].nrm[2];//nZ
  }
}

TTriVector  STomoTriangle::DivideTo4(void) const
{
  TTriVector tri_vec;
  
  const STomoVoxel& a = Vtx[0];
  const STomoVoxel& b = Vtx[1];
  const STomoVoxel& c = Vtx[2];

  STomoVoxel ab = getMid(a, b);
  STomoVoxel bc = getMid(b, c);
  STomoVoxel ca = getMid(c, a);

  STomoTriangle tri0( a, ab, ca);
  STomoTriangle tri1( b, bc, ab);
  STomoTriangle tri2( c, ca, bc);
  STomoTriangle tri3(ab, bc, ca);

  tri_vec.push_back(tri0);
  tri_vec.push_back(tri1);
  tri_vec.push_back(tri2);
  tri_vec.push_back(tri3);
  return tri_vec;
}

void  STomoTriangle::Print(void)
{
  std::cout << "-----------" << std::endl;
  for (int i = 0; i < iShape; i++)
  {
    std::cout<< Vtx[i].crd[0] << "," << Vtx[i].crd[1] << "," << Vtx[i].crd[2] << "," << Vtx[i].nrm[2] << std::endl;
  }
}

FLOAT32 STomoTriangle::GetCurcumDiameter(void) const
{
  FLOAT32 diameter;
  FLOAT32 a = distance(Vtx[0], Vtx[1]);
  FLOAT32 b = distance(Vtx[1], Vtx[2]);
  FLOAT32 c = distance(Vtx[2], Vtx[0]);
  FLOAT32 s = (a + b + c) * 0.5;
  FLOAT32 in_sq = s * (s - a) * (s - b) * (s - c);
  if(fabs(in_sq)< 1e-4 ) return 0.f;//degenerate
  diameter  = a * b * c * 0.5f / sqrt( in_sq );// https://en.wikipedia.org/wiki/Circumscribed_circle#Other_properties
  return diameter;
}

void triDivide4( TTriVector& _triVec, const STomoTriangle& _tri_to_divide, FLOAT32 _triMaxDiameter)//split a triangle to three
{
  if( _tri_to_divide.AABB.GetMaxSpan()   > _triMaxDiameter * 0.5
   || _tri_to_divide.GetCurcumDiameter() > _max(_triMaxDiameter * 0.5, 2.f)) 
  {
    TTriVector tri4 = _tri_to_divide.DivideTo4();
    for (auto& tri : tri4)     {      triDivide4(_triVec, tri, _triMaxDiameter);    }
  }
  else  
  {    
    _triVec.push_back( _tri_to_divide);  
  }
}