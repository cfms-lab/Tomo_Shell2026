#include "pch.h"
#include "STomoVolMassInfo.h"

STomoVolMassInfo::STomoVolMassInfo()
{
  Init();
}

STomoVolMassInfo::~STomoVolMassInfo()
{
  Reset();
}

STomoVolMassInfo::STomoVolMassInfo(const STomoVolMassInfo& Source)
{
  Init();
  _Copy(Source);
}

void	STomoVolMassInfo::operator=(const STomoVolMassInfo& Source)
{
  Reset();
  _Copy(Source);
}

void	STomoVolMassInfo::_Copy(const STomoVolMassInfo& Source)
{
  memcpy(dData, Source.dData, sdData);
}

void	STomoVolMassInfo::Reset(void)
{
  Init();
}

void	STomoVolMassInfo::Init(void)
{
  memset(dData, 0x00, sdData);
}


void  STomoVolMassInfo::VolToMass(const S3DPrinterInfo&printer_info)
{
  Vo_clad = Vo_core = Mo_clad = Mo_core = Mo = 0.f;
  Vss_clad = Vss_core = Ass_clad = Mss_clad = Mss_core = Mss = 0.f;
  Mbed = Mtotal = 0.f;

  Vo_clad = printer_info.surface_area * printer_info.wall_thickness;
  Vo_core = Vo - Vo_clad;
  Mo_clad = Vo_clad * printer_info.Fclad * printer_info.PLA_density;
  Mo_core = Vo_core * printer_info.Fcore * printer_info.PLA_density;
  Mo = Mo_core + Mo_clad;

#ifdef _EZAIR_THETAC_ZERO
  Vss = Vtc - Vo;
#endif

  if(printer_info.bUseExplicitSS)
  {
    if (Vss > g_fMARGIN)
    {
      FLOAT32 radius = pow(Vss / (4.f / 3.f * 3.141592f), 1.f / 3.f);//sphere volume V=(4/3)*pi*r^3  ->  r=(3V/4pi)^(1/3)
      Ass_clad = 4. * 3.141592 * radius * radius;//support structure ���Ǹ� sphere ���¶�� �����ϰ�, Ass_clad�� sphere�� ǥ�������� �ٻ�ȭ�Ѵ�.

      Vss_clad = Ass_clad * printer_info.wall_thickness;
      if (Vss_clad > Vss) Vss_clad = Vss;//clamp: cladding cannot exceed the whole SS volume (happens for small Vss)
      Vss_core = Vss - Vss_clad;
      Mss_clad = Vss_clad * printer_info.Fclad * printer_info.PLA_density;
      Mss_core = Vss_core * printer_info.Fcore * printer_info.PLA_density;
      Mss = Mss_core + Mss_clad;
    }
  }
  else//implicit
  {
    Mss = Vss * printer_info.Fss * printer_info.Css * printer_info.PLA_density;//obsolete..
 }

  Mbed = Vbed * printer_info.wall_thickness * printer_info.PLA_density;
  Mss += Mbed;//���̽㿡 Mo, Mss�� �����ϱ� ������, Mbed���� Mss�� �־�����.
  Mtotal = Mo + Mss;
}