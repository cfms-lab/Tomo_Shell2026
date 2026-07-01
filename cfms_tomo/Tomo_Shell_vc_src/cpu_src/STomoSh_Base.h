#pragma once
#include "STPSlot.h"
#include "STomoVoxelSpaceInfo.h"
#include "S3DPrinterInfo.h"
#include "STomoVoxel.h"
#include "SMatrix4f.h"


using namespace Tomo;

class DLLEXPORT STomoSh_Base
{
public:
  STomoSh_Base();
  STomoSh_Base(const STomoSh_Base& Source);
  void	operator=(const STomoSh_Base& Source);
  void	_Copy(const STomoSh_Base& Source);
  ~STomoSh_Base();

  void	Reset(void);
  void	Init(void);

  S3DPrinterInfo    printer_info;
  STomoVolMassInfo  vm_info;
  TPSlotVector slotVec;
  STomoAABB2D AABB2D;
  SMatrix4f mat4x4;

  void  Rotate(void); //rotate by (yaw, pitch, roll) and move to origin

  virtual void  Pixelize() {}
  virtual TPVector  slotsToPxls(enumPixelType _type) { TPVector tmp; return tmp;}//for rendering. time consuming. 
  virtual void      pxlsToSlots(TPVector& tri_pxls) {}
  virtual void  Pairing(void) {}//slot paring.
  virtual void  GenerateBed(void) {}
  virtual void  Calculate(void) {}//get Vss value
  //void  volToMass(void);

  virtual TPVector GetSSPixels(bool) { TPVector tmp; return tmp; }




};
