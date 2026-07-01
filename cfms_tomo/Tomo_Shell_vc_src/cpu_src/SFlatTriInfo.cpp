#include "pch.h"
#include "SFlatTriInfo.h"
#include <cstring> //memcpy()

SFlatTriInfo::SFlatTriInfo()
{
  Init();
}

SFlatTriInfo::~SFlatTriInfo()
{
  Reset();
}

SFlatTriInfo::SFlatTriInfo(const SFlatTriInfo& Source)
{
  Init();
  _Copy(Source);
}

void	SFlatTriInfo::operator=(const SFlatTriInfo& Source)
{
  Reset();
  _Copy(Source);
}

void	SFlatTriInfo::_Copy(const SFlatTriInfo& Source)
{
  memcpy(fData, Source.fData, sfData);
}

void	SFlatTriInfo::Reset(void)
{
  Init();
}

void	SFlatTriInfo::Init(void)
{
  memset( fData, 0x00, sfData);
}

