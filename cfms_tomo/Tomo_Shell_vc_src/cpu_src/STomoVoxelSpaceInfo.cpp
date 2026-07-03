#include "pch.h"
#include "STomoVoxelSpaceInfo.h"

using namespace Tomo;

STomoVoxelSpaceInfo::STomoVoxelSpaceInfo(int _x_dim, int _y_dim, int _z_dim)
{
  Init();
  SetMem( _x_dim, _y_dim, _z_dim);
}

STomoVoxelSpaceInfo::~STomoVoxelSpaceInfo()
{
  Reset();
}

STomoVoxelSpaceInfo::STomoVoxelSpaceInfo(const STomoVoxelSpaceInfo& Source)
{
  Init();
  _Copy(Source);
}

void	STomoVoxelSpaceInfo::operator=(const STomoVoxelSpaceInfo& Source)
{
  Reset();
  _Copy(Source);
}

void	STomoVoxelSpaceInfo::_Copy(const STomoVoxelSpaceInfo& Source)
{
  memcpy(iData, Source.iData, siData);
  nTotalVxls = Source.nTotalVxls;
  SetMem( x_dim, y_dim, z_dim);
}

void	STomoVoxelSpaceInfo::Reset(void)
{
  if (SlotBuf_108f != nullptr) { delete[] SlotBuf_108f; SlotBuf_108f = nullptr; }
  if (SlotVo_32i != nullptr) { delete[] SlotVo_32i; SlotVo_32i = nullptr; }
  if (SlotVss_32i != nullptr) { delete[] SlotVss_32i; SlotVss_32i = nullptr; }
  Init();
}

void	STomoVoxelSpaceInfo::Init(void)
{
  memset(iData, 0x00, siData);
  SlotBuf_108f = nullptr;
  SlotVo_32i = nullptr;
  SlotVss_32i = nullptr;
  nTotalVxls = 0;//debug
  nSlotCapacityWidth = 3;//always 3
  nSlotCapacityHeight = 16;//you can increase this number if needed.
#ifdef _USE_BRIEF_SLOT_PAIRING
  nSlotCapacityHeight = 64;//�� ������ �ȼ� ������ ���� �����Ƿ� �˳��ϰ� ������ش�.
#endif 
}


void  STomoVoxelSpaceInfo::InitSlotBuf(void)
{
  VOXEL_ID_TYPE n_slotbuf_size = x_dim * y_dim * nSlotCapacityWidth * nSlotCapacityHeight;
  memset(SlotBuf_108f, 0x00, sizeof(SLOT_BUFFER_TYPE) * n_slotbuf_size);
  VOXEL_ID_TYPE n_slot_count = x_dim * y_dim;
  memset(SlotVo_32i, 0x00, sizeof(SLOT_SUM_TYPE) * n_slot_count);
  memset(SlotVss_32i, 0x00, sizeof(SLOT_SUM_TYPE) * n_slot_count);
}

void  STomoVoxelSpaceInfo::SetMem(int _x_dim, int _y_dim, int _z_dim)
{
  if (SlotBuf_108f != nullptr) { delete[] SlotBuf_108f; SlotBuf_108f = nullptr; }
  if (SlotVo_32i != nullptr) { delete[] SlotVo_32i; SlotVo_32i = nullptr; }
  if (SlotVss_32i != nullptr) { delete[] SlotVss_32i; SlotVss_32i = nullptr; }

  x_dim = _x_dim;
  y_dim = _y_dim;
  z_dim = _z_dim;

  nTotalVxls = x_dim * y_dim * z_dim;
  VOXEL_ID_TYPE n_slotbuf_size = x_dim * y_dim * nSlotCapacityWidth * nSlotCapacityHeight;
  //long long int total_size = n_slotbuf_size * sizeof(SLOT_BUFFER_TYPE);//debug
  SlotBuf_108f = new SLOT_BUFFER_TYPE[n_slotbuf_size + 2];
  VOXEL_ID_TYPE n_slot_count = x_dim * y_dim;
  SlotVo_32i = new SLOT_SUM_TYPE[n_slot_count + 2];
  SlotVss_32i = new SLOT_SUM_TYPE[n_slot_count + 2];
  InitSlotBuf();
}

VOXEL_ID_TYPE STomoVoxelSpaceInfo::coord2vID(/*input*/FLOAT32* coord,  /*output2*/int slotXYZ[3])
{
  //[x][y][z]. x,y,�� slot�� (x,y)��ǥ. z�� �ȼ� ����.
  slotXYZ[0] = int(coord[0]);
  slotXYZ[1] = int(coord[1]);
  slotXYZ[2] = z_dim - 1 - int(coord[2]);//���������� ����. for later slot-pairing

  return  VOXEL_ID_TYPE(slotXYZ[0] * y_dim * z_dim + slotXYZ[1] * z_dim + slotXYZ[2]);
}

VOXEL_ID_TYPE STomoVoxelSpaceInfo::coord2vID(/*input*/int* coord,   /*output2*/int slotXYZ[3])
{
  //[x][y][z]. x,y,�� slot�� (x,y)��ǥ. z�� �ȼ� ����.
  slotXYZ[0] = int(coord[0]);
  slotXYZ[1] = int(coord[1]);
  slotXYZ[2] = z_dim - 1 - int(coord[2]);//���������� ����. for later slot-pairing

  return  VOXEL_ID_TYPE(slotXYZ[0] * y_dim * z_dim + slotXYZ[1] * z_dim + slotXYZ[2]);
}

void          STomoVoxelSpaceInfo::vID2coord(VOXEL_ID_TYPE _id, int& _x, int& _y, int& _z)
{
  //[x][y][z]. x,y,�� slot�� (x,y)��ǥ. z�� �ȼ� ����.
  VOXEL_ID_TYPE X_idx = VOXEL_ID_TYPE( _id / y_dim / z_dim);
  VOXEL_ID_TYPE Y_idx = VOXEL_ID_TYPE( _id - X_idx * y_dim * z_dim);
  Y_idx = VOXEL_ID_TYPE(Y_idx / z_dim);
  VOXEL_ID_TYPE Z_idx = VOXEL_ID_TYPE( _id - X_idx * y_dim * z_dim - Y_idx * z_dim);
    
  _x = int(X_idx);
  _y = int(Y_idx);
  _z = int(z_dim-1 - Z_idx);
}

  void  STomoVoxelSpaceInfo::SetBit_Type(
  /*target position*/SLOT_BUFFER_TYPE* slot_buf, unsigned int _ID, unsigned int slotXYZ[3],
  /*values to insert*/ int pxl_z, int pxl_nZ, int _typeByte)
{
  int X_D = x_dim;
  int Y_D = y_dim;
  int S_W = nSlotCapacityWidth;
  int S_H = nSlotCapacityHeight;

  VOXEL_ID_TYPE slot_start_pos = (slotXYZ[0] * Y_D + slotXYZ[1] )* S_W * S_H;//overflow ����. type_buffer������ ��� ������ vxl_id�� �������.

  SLOT_BUFFER_TYPE& n_pixels_in_curr_slot = *(slot_buf + slot_start_pos + 0);//���� slot�ȿ� �ȼ��� �� �� ����ִ��� Ȯ������,

  //�̹� �ִ� �ȼ����� Ȯ��
  int newpxl_ID = -1;
  for (int p = 0; p < n_pixels_in_curr_slot; p++)
  {
    int old_z = *(slot_buf + slot_start_pos + (p +1) * S_W + 1);
    int old_nz = *(slot_buf + slot_start_pos + (p +1) * S_W + 2);
    if (old_z == pxl_z && old_nz == pxl_nZ)
    {
      newpxl_ID = p;//�̹� ����. overwrite/update
      break;
    }
  }

  if (newpxl_ID == -1)
  {
    //slot row 0 is the header, so pixel p occupies row (p+1). The last usable row is (S_H-1),
    //i.e. the maximum pixel index is (S_H-2). Reject before inflating the counter to avoid
    //writing into the next slot (the off-by-one that caused 'illegal memory access').
    if (n_pixels_in_curr_slot >= nSlotCapacityHeight - 1) return;
    newpxl_ID = n_pixels_in_curr_slot++;//����. ���� �߰�.
  }
  if (newpxl_ID < nSlotCapacityHeight - 1)
  {
    VOXEL_ID_TYPE newpxl_pos = VOXEL_ID_TYPE(slot_start_pos + (newpxl_ID + 1) * S_W);

    *(slot_buf + newpxl_pos + 0) |= _typeByte;//type�� �Է�
    *(slot_buf + newpxl_pos + 1) = static_cast<SLOT_BUFFER_TYPE>(pxl_z);//��ǥ��(z��)�Է�
    *(slot_buf + newpxl_pos + 2) = static_cast<SLOT_BUFFER_TYPE>(pxl_nZ);//�븻 z�� �Է�
  }
}

void  STomoVoxelSpaceInfo::SetBit(SLOT_BUFFER_TYPE* slot_buf, FLOAT32* pxl, FLOAT32* nrm, int _typeByte)
{
  int slotXYZ[3] = {};
  VOXEL_ID_TYPE vxl_id = coord2vID(pxl, slotXYZ);
  SLOT_BUFFER_TYPE pxl_z = SLOT_BUFFER_TYPE(pxl[2]);
  SLOT_BUFFER_TYPE nrm_z = SLOT_BUFFER_TYPE(nrm[2] * g_fNORMALFACTOR);

  int X_D = x_dim;
  int Y_D = y_dim;
  int S_W = nSlotCapacityWidth;
  int S_H = nSlotCapacityHeight;

  VOXEL_ID_TYPE slot_start_pos = (slotXYZ[0] * Y_D + slotXYZ[1]) * S_W * S_H;//overflow ����. type_buffer������ ��� ������ vxl_id�� �������.
    
  SLOT_BUFFER_TYPE* curr_Pxl_slot         =  slot_buf + slot_start_pos;//current slot
  SLOT_BUFFER_TYPE& n_pixels_in_curr_slot = *(slot_buf + slot_start_pos + 0);//���� slot�ȿ� �ȼ��� �� �� ����ִ��� Ȯ������,

#ifdef _DEBUG
  //if (slotXYZ[0] == 18 && slotXYZ[1] == 20)
  //{
  //  int debug = 0;
  //}
#endif

  //�̹� �ִ� �ȼ����� Ȯ��
  int newpxl_ID = -1;
  for (int p = 0; p < n_pixels_in_curr_slot; p++)
  {
    int old_z  = *(slot_buf + slot_start_pos + (p + 1) * S_W + 1);
    int old_nz = *(slot_buf + slot_start_pos + (p + 1) * S_W + 2);
    if (old_z == pxl_z && old_nz == nrm_z)
    {
      newpxl_ID = p;//�̹� ����. overwrite/update
      break;
    }
  }

  if (newpxl_ID == -1)
  {
    //slot row 0 is the header, so pixel p occupies row (p+1). The last usable row is (S_H-1),
    //i.e. the maximum pixel index is (S_H-2). Reject before inflating the counter to avoid
    //writing into the next slot (the off-by-one that caused 'illegal memory access').
    if (n_pixels_in_curr_slot >= nSlotCapacityHeight - 1) return;
    newpxl_ID = n_pixels_in_curr_slot++;//����. ���� �߰�.
  }
  if (newpxl_ID < nSlotCapacityHeight - 1)
  {
    VOXEL_ID_TYPE newpxl_pos = VOXEL_ID_TYPE(slot_start_pos + (newpxl_ID + 1) * S_W);

    *(slot_buf + newpxl_pos + 0) |= _typeByte;//type�� �Է�
    *(slot_buf + newpxl_pos + 1) = static_cast<SLOT_BUFFER_TYPE>(pxl_z);//��ǥ��(z��)�Է�
    *(slot_buf + newpxl_pos + 2) = static_cast<SLOT_BUFFER_TYPE>(nrm_z);//�븻 z�� �Է�
  }

}
