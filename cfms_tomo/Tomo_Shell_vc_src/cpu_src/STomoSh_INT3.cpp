#include "pch.h"
#include "STomoSh_INT3.h"
#include "SMatrix4f.h"
#include <cstdlib>
#include <cstdio>
#include <algorithm>


using namespace Tomo;

static SLOT_BUFFER_TYPE clampSlotSumToBuffer(SLOT_SUM_TYPE value)
{
  if (value > 32767) return SLOT_BUFFER_TYPE(32767);
  if (value < -32768) return SLOT_BUFFER_TYPE(-32768);
  return SLOT_BUFFER_TYPE(value);
}

static bool tomoDebugSlotInputEnabled()
{
  char* env = nullptr;
  size_t envLen = 0;
  bool enabled = false;
  if (_dupenv_s(&env, &envLen, "TOMO_DEBUG_SLOT_INPUT") == 0 && env != nullptr) {
    enabled = (std::atoi(env) != 0);
    free(env);
  }
  return enabled;
}

static int tomoDebugSlotInputLimit()
{
  char* env = nullptr;
  size_t envLen = 0;
  int limit = 0;
  if (_dupenv_s(&env, &envLen, "TOMO_DEBUG_SLOT_LIMIT") == 0 && env != nullptr) {
    limit = std::atoi(env);
    free(env);
  }
  return limit;
}

static void tomoDebugPrintCpuSlotInput(const STomoSh_INT3* tomo)
{
  static int callNo = 0;
  if (!tomoDebugSlotInputEnabled()) return;
  int limit = tomoDebugSlotInputLimit();
  if (limit > 0 && callNo >= limit) { callNo++; return; }

  const int X_D = tomo->voxel_info.x_dim;
  const int Y_D = tomo->voxel_info.y_dim;
  const int S_W = tomo->voxel_info.nSlotCapacityWidth;
  const int S_H = tomo->voxel_info.nSlotCapacityHeight;
  long long nonempty = 0, pairable = 0, rows = 0, sat = 0;
  long long alCnt = 0, beCnt = 0, sideCnt = 0;
  long long alZ = 0, beZ = 0, allZ = 0;
  int maxLen = 0;

  for (int slotX = 0; slotX < X_D; slotX++) {
    for (int slotY = 0; slotY < Y_D; slotY++) {
      SLOT_BUFFER_TYPE* slot = tomo->voxel_info.SlotBuf_108f + (slotX * Y_D + slotY) * S_W * S_H;
      int S_L = slot[0];
      if (S_L <= 0) continue;
      nonempty++;
      if (S_L > 1) pairable++;
      if (S_L > maxLen) maxLen = S_L;
      if (S_L >= S_H - 1) sat++;
      rows += S_L;
      for (int p = 0; p < S_L; p++) {
        const int z = slot[(p + 1) * S_W + 1];
        const int nz = slot[(p + 1) * S_W + 2];
        allZ += z;
        if (nz > 0) { alCnt++; alZ += z; }
        else if (nz < 0) { beCnt++; beZ += z; }
        else { sideCnt++; }
      }
    }
  }

  char* dumpDir = nullptr;
  size_t dumpDirLen = 0;
  char* dumpCallEnv = nullptr;
  size_t dumpCallLen = 0;
  int dumpCall = -1;
  if (_dupenv_s(&dumpCallEnv, &dumpCallLen, "TOMO_DEBUG_SLOT_DUMP_CALL") == 0 && dumpCallEnv != nullptr) {
    dumpCall = std::atoi(dumpCallEnv);
    free(dumpCallEnv);
  }
  if (dumpCall == callNo && _dupenv_s(&dumpDir, &dumpDirLen, "TOMO_DEBUG_SLOT_DUMP_DIR") == 0 && dumpDir != nullptr) {
    char fname[1024];
    std::snprintf(fname, sizeof(fname), "%s\\slot_CPU_%03d.csv", dumpDir, callNo);
    FILE* fp = nullptr;
    if (fopen_s(&fp, fname, "w") == 0 && fp != nullptr) {
      std::fprintf(fp, "slot,x,y,p,z,nz,cls\n");
      for (int slotX = 0; slotX < X_D; slotX++) {
        for (int slotY = 0; slotY < Y_D; slotY++) {
          int slotID = slotX * Y_D + slotY;
          SLOT_BUFFER_TYPE* slot = tomo->voxel_info.SlotBuf_108f + slotID * S_W * S_H;
          int S_L = slot[0];
          for (int p = 0; p < S_L; p++) {
            const int z = slot[(p + 1) * S_W + 1];
            const int nz = slot[(p + 1) * S_W + 2];
            const int cls = (nz > 0) ? 1 : ((nz < 0) ? 2 : 0);
            std::fprintf(fp, "%d,%d,%d,%d,%d,%d,%d\n", slotID, slotX, slotY, p, z, nz, cls);
          }
        }
      }
      std::fclose(fp);
    }
    free(dumpDir);
  }
  std::printf("TOMO_SLOT_INPUT CPU call=%d yaw=%.6f pitch=%.6f roll=%.6f nonempty=%lld pairable=%lld rows=%lld alCnt=%lld alZ=%lld beCnt=%lld beZ=%lld sideCnt=%lld allZ=%lld sat=%lld maxLen=%d\n",
    callNo, tomo->printer_info.yaw, tomo->printer_info.pitch, tomo->printer_info.roll,
    nonempty, pairable, rows, alCnt, alZ, beCnt, beZ, sideCnt, allZ, sat, maxLen);
  callNo++;
}

static bool tomoDebugPairOutputEnabled()
{
  char* env = nullptr;
  size_t envLen = 0;
  bool enabled = false;
  if (_dupenv_s(&env, &envLen, "TOMO_DEBUG_PAIR_OUTPUT") == 0 && env != nullptr) {
    enabled = (std::atoi(env) != 0);
    free(env);
  }
  return enabled;
}

static void tomoCalcCpuSlotPairSums(
  const STomoSh_INT3* tomo,
  SLOT_BUFFER_TYPE slotLen,
  SLOT_BUFFER_TYPE* slot,
  SLOT_SUM_TYPE& vo,
  SLOT_SUM_TYPE& vss)
{
  vo = 0;
  vss = 0;
  if (slotLen <= 1) return;

  const int S_W = tomo->voxel_info.nSlotCapacityWidth;
  SLOT_SUM_TYPE al_sum = 0, be_sum = 0;
  SLOT_SUM_TYPE ssb_sum = 0, ssa_sum = 0;
  SLOT_SUM_TYPE TC_sum = 0, NVB_sum = 0, NVA_sum = 0;

  for (int p = 0; p < slotLen; p++)
  {
    SLOT_BUFFER_TYPE p_type = *(slot + (p + 1) * S_W + 0);
    SLOT_SUM_TYPE p_z = *(slot + (p + 1) * S_W + 1);

    if (p_type & typeAl)
    {
      al_sum += p_z;
      if (p_type & typeTC)  { TC_sum += p_z; }
      if (p_type & typeNVA) { NVA_sum += p_z; }
    }
    else if (p_type & typeBe)
    {
      be_sum += p_z;
      if (p_type & typeNVB) { NVB_sum += p_z; }
    }

    if (p_type & typeSSB) { ssb_sum += p_z; }
    else if (p_type & typeSSA) { ssa_sum += p_z; }
  }

  vo = (al_sum > be_sum) ? (al_sum - be_sum) : 0;
  vss = tomo->printer_info.bUseExplicitSS
    ? (ssb_sum - ssa_sum)
    : (-al_sum + be_sum + TC_sum - NVB_sum + NVA_sum);
}

static void tomoDebugPrintCpuPairOutput(const STomoSh_INT3* tomo)
{
  static int callNo = 0;
  if (!tomoDebugPairOutputEnabled()) { callNo++; return; }

  char* dumpCallEnv = nullptr;
  size_t dumpCallLen = 0;
  int dumpCall = -1;
  if (_dupenv_s(&dumpCallEnv, &dumpCallLen, "TOMO_DEBUG_PAIR_DUMP_CALL") == 0 && dumpCallEnv != nullptr) {
    dumpCall = std::atoi(dumpCallEnv);
    free(dumpCallEnv);
  }

  const int X_D = tomo->voxel_info.x_dim;
  const int Y_D = tomo->voxel_info.y_dim;
  const int S_W = tomo->voxel_info.nSlotCapacityWidth;
  const int S_H = tomo->voxel_info.nSlotCapacityHeight;
  long long voSum = 0, vssSum = 0, nonzeroVo = 0, nonzeroVss = 0;
  for (int slotX = 0; slotX < X_D; slotX++) {
    for (int slotY = 0; slotY < Y_D; slotY++) {
      int slotID = slotX * Y_D + slotY;
      SLOT_BUFFER_TYPE* slot = tomo->voxel_info.SlotBuf_108f + slotID * S_W * S_H;
      SLOT_SUM_TYPE vo = 0, vss = 0;
      tomoCalcCpuSlotPairSums(tomo, slot[0], slot, vo, vss);
      voSum += vo;
      vssSum += vss;
      if (vo != 0) nonzeroVo++;
      if (vss != 0) nonzeroVss++;
    }
  }

  char* dumpDir = nullptr;
  size_t dumpDirLen = 0;
  if (dumpCall == callNo && _dupenv_s(&dumpDir, &dumpDirLen, "TOMO_DEBUG_PAIR_DUMP_DIR") == 0 && dumpDir != nullptr) {
    char fname[1024];
    std::snprintf(fname, sizeof(fname), "%s\\pair_CPU_%03d.csv", dumpDir, callNo);
    FILE* fp = nullptr;
    if (fopen_s(&fp, fname, "w") == 0 && fp != nullptr) {
      std::fprintf(fp, "slot,x,y,n,vo,vss,p,z,nz,type\n");
      for (int slotX = 0; slotX < X_D; slotX++) {
        for (int slotY = 0; slotY < Y_D; slotY++) {
          int slotID = slotX * Y_D + slotY;
          SLOT_BUFFER_TYPE* slot = tomo->voxel_info.SlotBuf_108f + slotID * S_W * S_H;
          int S_L = slot[0];
          SLOT_SUM_TYPE vo = 0, vss = 0;
          tomoCalcCpuSlotPairSums(tomo, S_L, slot, vo, vss);
          std::fprintf(fp, "%d,%d,%d,%d,%d,%d,-1,0,0,0\n", slotID, slotX, slotY, S_L, vo, vss);
          for (int p = 0; p < S_L; p++) {
            const int typ = slot[(p + 1) * S_W + 0];
            const int z = slot[(p + 1) * S_W + 1];
            const int nz = slot[(p + 1) * S_W + 2];
            std::fprintf(fp, "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n", slotID, slotX, slotY, S_L, vo, vss, p, z, nz, typ);
          }
        }
      }
      std::fclose(fp);
    }
    free(dumpDir);
  }

  std::printf("TOMO_PAIR_OUTPUT CPU call=%d vo=%lld vss=%lld nonzeroVo=%lld nonzeroVss=%lld\n",
    callNo, voSum, vssSum, nonzeroVo, nonzeroVss);
  callNo++;
}
STomoSh_INT3::STomoSh_INT3() : STomoSh_Base()
{
}

STomoSh_INT3::~STomoSh_INT3()
{
  Reset();
}

STomoSh_INT3::STomoSh_INT3(const STomoSh_INT3& Source)
{
  Init();
  _Copy(Source);
}

void	STomoSh_INT3::operator=(const STomoSh_INT3& Source)
{
  Reset();
  _Copy(Source);
}

void	STomoSh_INT3::_Copy(const STomoSh_INT3& Source)
{
  STomoSh_Base::_Copy(Source);  
}

void	STomoSh_INT3::Reset(void)
{
  STomoSh_Base::Reset();
  voxel_info.Reset();
}

void	STomoSh_INT3::Init(void)
{
  STomoSh_Base::Init();
  voxel_info.Init();
}

VOXEL_ID_TYPE STomoSh_INT3::slotIDFromPtr(const size_t S_W, SLOT_BUFFER_TYPE* curr_Pxl_slot) const
{
  return VOXEL_ID_TYPE((curr_Pxl_slot - voxel_info.SlotBuf_108f) / (S_W * voxel_info.nSlotCapacityHeight));
}

void  STomoSh_INT3::Rotate(void)
{
  STomoSh_Base::Rotate();
}


void  STomoSh_INT3::Pixelize()
{
  voxel_info.ClearDirtySlots();//zero only last direction's touched slots (was: full 6MB memset)

  static int tomoTriHitCallNo = 0;
  int tomoThisTriHitCall = tomoTriHitCallNo++;
  FILE* tomoTriHitFile = nullptr;
  char* tomoTriHitCallEnv = nullptr;
  char* tomoTriHitDirEnv = nullptr;
  size_t tomoTriHitEnvLen = 0;
  int tomoTriHitTarget = -1;
  if (_dupenv_s(&tomoTriHitCallEnv, &tomoTriHitEnvLen, "TOMO_DEBUG_TRI_HIT_CALL") == 0 && tomoTriHitCallEnv != nullptr) {
    tomoTriHitTarget = std::atoi(tomoTriHitCallEnv);
    free(tomoTriHitCallEnv);
  }
  if (tomoTriHitTarget == tomoThisTriHitCall) {
    const char* tomoTriHitDir = ".";
    if (_dupenv_s(&tomoTriHitDirEnv, &tomoTriHitEnvLen, "TOMO_DEBUG_TRI_HIT_DIR") == 0 && tomoTriHitDirEnv != nullptr) {
      tomoTriHitDir = tomoTriHitDirEnv;
    }
    char tomoTriHitPath[1024];
    std::snprintf(tomoTriHitPath, sizeof(tomoTriHitPath), "%s\\trihit_CPU_%03d.csv", tomoTriHitDir, tomoThisTriHitCall);
    fopen_s(&tomoTriHitFile, tomoTriHitPath, "w");
    if (tomoTriHitFile != nullptr) std::fprintf(tomoTriHitFile, "tri,hits,x0,y0,x1,y1,x2,y2\n");
    if (tomoTriHitDirEnv != nullptr) free(tomoTriHitDirEnv);
  }

#ifdef _USE_CUDA_FOR_TOMONV
  char* envCpuFlat = nullptr;
  size_t envCpuFlatLen = 0;
  bool useCpuFlat = false;
  if (_dupenv_s(&envCpuFlat, &envCpuFlatLen, "TOMO_CPU_FLAT_TRI") == 0 && envCpuFlat != nullptr) {
    useCpuFlat = (std::atoi(envCpuFlat) != 0);
    free(envCpuFlat);
  }
  if (useCpuFlat && printer_info.pFlatTri != nullptr && printer_info.nFlatTri > 0)
  {
    for (MESH_ELE_ID_TYPE t = 0; t < printer_info.nFlatTri; t++)
    {
      FlatTriInfo* pFT = (FlatTriInfo*)(printer_info.pFlatTri + t * nFlatTriInfoSize);
      FLOAT32 v0[3], v1[3], v2[3], n0[3], n1[3], n2[3];
      mat4x4.Dot(pFT->vtx0, v0);
      mat4x4.Dot(pFT->vtx1, v1);
      mat4x4.Dot(pFT->vtx2, v2);
      for (int i = 0; i < 3; i++) {
        n0[i] = mat4x4.Data[i][0] * pFT->nrm0[0] + mat4x4.Data[i][1] * pFT->nrm0[1] + mat4x4.Data[i][2] * pFT->nrm0[2];
        n1[i] = mat4x4.Data[i][0] * pFT->nrm1[0] + mat4x4.Data[i][1] * pFT->nrm1[1] + mat4x4.Data[i][2] * pFT->nrm1[2];
        n2[i] = mat4x4.Data[i][0] * pFT->nrm2[0] + mat4x4.Data[i][1] * pFT->nrm2[1] + mat4x4.Data[i][2] * pFT->nrm2[2];
      }
      int tomoHits = triVoxel(v0, v1, v2, n0, n1, n2, voxel_info.SlotBuf_108f);
      if (tomoTriHitFile != nullptr) std::fprintf(tomoTriHitFile, "%d,%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n", (int)t, tomoHits, v0[0], v0[1], v1[0], v1[1], v2[0], v2[1]);
    }
    if (tomoTriHitFile != nullptr) fclose(tomoTriHitFile);
    return;
  }
#endif
for (MESH_ELE_ID_TYPE t = 0; t < printer_info.nTri; t++)
  {
    MESH_ELE_ID_TYPE t0 = printer_info.rpTri0[t * 3 + 0];
    MESH_ELE_ID_TYPE t1 = printer_info.rpTri0[t * 3 + 1];
    MESH_ELE_ID_TYPE t2 = printer_info.rpTri0[t * 3 + 2];

    int tomoHits = triVoxel(
      printer_info.pVtx1 + t0 * 3,
      printer_info.pVtx1 + t1 * 3,
      printer_info.pVtx1 + t2 * 3,
#ifdef _USE_VTX_NRM_FOR_PIXEL
      printer_info.pNrm1 + t0 * 3,
      printer_info.pNrm1 + t1 * 3,
      printer_info.pNrm1 + t2 * 3,
#else
      printer_info.pTriNrm1 + t * 3,
      printer_info.pTriNrm1 + t * 3,
      printer_info.pTriNrm1 + t * 3,
#endif
      voxel_info.SlotBuf_108f);
    if (tomoTriHitFile != nullptr) std::fprintf(tomoTriHitFile, "%d,%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n", (int)t, tomoHits, printer_info.pVtx1[t0 * 3 + 0], printer_info.pVtx1[t0 * 3 + 1], printer_info.pVtx1[t1 * 3 + 0], printer_info.pVtx1[t1 * 3 + 1], printer_info.pVtx1[t2 * 3 + 0], printer_info.pVtx1[t2 * 3 + 1]);
  }
  if (tomoTriHitFile != nullptr) fclose(tomoTriHitFile);
}

void  STomoSh_INT3::Pairing(void)//CUDA nvcc compatible version slot-pairing
{
  tomoDebugPrintCpuSlotInput(this);

  int X_D = voxel_info.x_dim;
  int Y_D = voxel_info.y_dim;
  int Z_D = voxel_info.z_dim;
  int S_W = voxel_info.nSlotCapacityWidth;
  int S_H = voxel_info.nSlotCapacityHeight;
  vm_info.Vo = 0;
  vm_info.Vss = 0;
  //Only occupied slots need pairing; the full X_D*Y_D scan re-read slot headers across the whole
  //6MB buffer every direction. Iterate the recorded dirty (occupied) slots instead. Sort ascending
  //so the int->float Vo/Vss accumulation happens in the same slotID order as the old row-major scan
  //(float sums aren't associative; this keeps results bit-identical for large volumes too).
  std::sort(voxel_info.dirtySlots.begin(), voxel_info.dirtySlots.end());
  for (size_t i = 0; i < voxel_info.dirtySlots.size(); i++)
  {
    SLOT_BUFFER_TYPE* curr_Pxl_slot = voxel_info.SlotBuf_108f + voxel_info.dirtySlots[i] * S_W * S_H;//pointer to current slot
    SLOT_BUFFER_TYPE& n_pixels_in_curr_slot = *(curr_Pxl_slot + 0);//number of pixels in the current slot. Can be modififd in the sub-functions.
    if(n_pixels_in_curr_slot>1)
    {
      SLOT_SUM_TYPE slotVo = 0, slotVss = 0;
      vslotPair(S_W, n_pixels_in_curr_slot, curr_Pxl_slot, printer_info.theta_c, slotVo, slotVss);
      vm_info.Vo += slotVo;
      vm_info.Vss += slotVss;
    }
  }
  tomoDebugPrintCpuPairOutput(this);
}


void  STomoSh_INT3::sortSlotByZ(
  const size_t S_W/*slot width, always 3*/, 
  const SLOT_BUFFER_TYPE S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot)
{
  size_t*index  = new size_t[S_L +2];
  SLOT_BUFFER_TYPE*z_data = new SLOT_BUFFER_TYPE[S_L + 2];
  for( int p = 0 ; p < S_L; p++)
  { 
    index[p] = p;
    z_data[p] = *(curr_Pxl_slot + (p+1)*3 + 1);
  };

  QuickSort( z_data, index, size_t(0), size_t(S_L -1));

  SLOT_BUFFER_TYPE *temp_buf = new SLOT_BUFFER_TYPE[S_W * S_L + 2];
  for (int p = 0; p < S_L; p++)
  {
    size_t new_p = index[S_L-1-p];//z�� ��������.
    temp_buf[p * S_W + 0] = *(curr_Pxl_slot + (new_p + 1) * S_W + 0);
    temp_buf[p * S_W + 1] = *(curr_Pxl_slot + (new_p + 1) * S_W + 1);
    temp_buf[p * S_W + 2] = *(curr_Pxl_slot + (new_p + 1) * S_W + 2);
  }

  for (int p = 0; p < S_L - 1; p++)
  {
    for (int q = p + 1; q < S_L; q++)
    {
      SLOT_BUFFER_TYPE p_z  = temp_buf[p * S_W + 1];
      SLOT_BUFFER_TYPE q_z  = temp_buf[q * S_W + 1];
      SLOT_BUFFER_TYPE p_nz = temp_buf[p * S_W + 2];
      SLOT_BUFFER_TYPE q_nz = temp_buf[q * S_W + 2];
      if (p_z == q_z && p_nz < q_nz)
      {
        for (int k = 0; k < S_W; k++)
        {
          SLOT_BUFFER_TYPE tmp = temp_buf[p * S_W + k];
          temp_buf[p * S_W + k] = temp_buf[q * S_W + k];
          temp_buf[q * S_W + k] = tmp;
        }
      }
    }
  }

  memcpy(curr_Pxl_slot + S_W, temp_buf, sizeof(SLOT_BUFFER_TYPE) * S_W * S_L);
  delete[] temp_buf;
  delete[] z_data;
  delete[] index;
}

  SLOT_BUFFER_TYPE STomoSh_INT3::erasePxl(const size_t S_W, const size_t S_L, int p_id, SLOT_BUFFER_TYPE* curr_Pxl_slot)
{
#if 1
  memcpy(curr_Pxl_slot + (p_id + 1) * S_W + 0, curr_Pxl_slot + (p_id + 2) * S_W + 0, sizeof(SLOT_BUFFER_TYPE)*3*(S_L - 1 - p_id));
#else
  for( int p = p_id ; p < S_L-1 ; p++)
  {
    *(curr_Pxl_slot + (p + 1) * S_W + 0) = *(curr_Pxl_slot + (p + 2) * S_W + 0);
    *(curr_Pxl_slot + (p + 1) * S_W + 1) = *(curr_Pxl_slot + (p + 2) * S_W + 1);
    *(curr_Pxl_slot + (p + 1) * S_W + 2) = *(curr_Pxl_slot + (p + 2) * S_W + 2);
  }
#endif
  size_t p = S_L-1;//reset mem
  *(curr_Pxl_slot + (p + 1) * S_W + 0) = 0;
  *(curr_Pxl_slot + (p + 1) * S_W + 1) = 0;
  *(curr_Pxl_slot + (p + 1) * S_W + 2) = 0;

  return SLOT_BUFFER_TYPE(S_L-1);
}

void  STomoSh_INT3::removeZNearPxls(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot, int typeByte)
{ //���� type�ε� z���� +1�� �̿� �ȼ��� ����.
  for( int p = 0 ; p < S_L-1 ; p++)
  {
    SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p+1)*S_W + 0);
    SLOT_BUFFER_TYPE p_z    = *(curr_Pxl_slot + (p + 1) * S_W + 1);
    for( int q = p+1 ; q < S_L ; q++)
    {
      SLOT_BUFFER_TYPE q_type = *(curr_Pxl_slot + (q + 1) * S_W + 0);
      SLOT_BUFFER_TYPE q_z    = *(curr_Pxl_slot + (q + 1) * S_W + 1);
      if( (p_type & typeByte) && ( q_type & typeByte))
      {
        if( _abs(INT16(p_z - q_z)) <= 1)
        {
          S_L = erasePxl(S_W, S_L, p, curr_Pxl_slot);//including S_L--          
          p--; q = S_L;//search again
        }
      }
    }
  }
}

void  STomoSh_INT3::splitAlBe(
  const size_t S_W/*slot width, always 3*/,
  const size_t S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot)
{
  for (int p = 0; p < S_L; p++)
  {
    SLOT_BUFFER_TYPE& pxl_type  = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    SLOT_BUFFER_TYPE pxl_z      = *(curr_Pxl_slot + (p + 1) * S_W + 1);
    SLOT_BUFFER_TYPE pxl_nZ     = *(curr_Pxl_slot + (p + 1) * S_W + 2);

    if(pxl_nZ * g_fNORMALFACTOR > g_fMARGIN * 10.)//nz==0. �� ���鿡 �ִ� �͵��� ������.
    {
      pxl_type |= typeAl;
    }
    else if(pxl_nZ * g_fNORMALFACTOR <  g_fMARGIN * -10.)
    {
      pxl_type |= typeBe;
    }
  }
}

bool  STomoSh_INT3::_hasPxlBetween(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot, 
  int z0, int z1,  int iTypeByte)
{
  for (int p = 0; p < S_L ; p++)
  {
    SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    SLOT_BUFFER_TYPE p_z    = *(curr_Pxl_slot + (p + 1) * S_W + 1);

    if( p_type == iTypeByte )
    {
      if( (p_z <= z1 && p_z >= z0) ||
          (p_z <= z0 && p_z >= z1) )
      {
        return true;
      }         
    }
  }

  return false;
}

inline int STomoSh_INT3::_xorAlBe(int _iTypeByte)
{
  return  (_iTypeByte & typeAl)? typeBe : typeAl;
}

void  STomoSh_INT3::matchAlBeAlternation(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot)
{
  if(S_L <2) return;

  //assume there are either alpha or beta types only.
  //check alpha-beta-alpha-beta is alternating. using hasPxlBetween().

  for (int p = 0; p < S_L - 1; p++)
  {
    SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    SLOT_BUFFER_TYPE p_z    = *(curr_Pxl_slot + (p + 1) * S_W + 1);

    bool b_hasPixelBtwn = true;
    for (int q = max(p -1, 0); q < S_L; q++)//occasionally alpha, beta can have same z-value due to integer conversion. so start with (p-1).
    {
      SLOT_BUFFER_TYPE q_type = *(curr_Pxl_slot + (q + 1) * S_W + 0);
      SLOT_BUFFER_TYPE q_z    = *(curr_Pxl_slot + (q + 1) * S_W + 1);

      if ((p!=q) //skip comparison bewteen the same elements.
      && (p_type & q_type))
      {
        b_hasPixelBtwn = _hasPxlBetween(S_W, S_L, curr_Pxl_slot, p_z, q_z, _xorAlBe(p_type));//e.g. if p and q is alpha, check if there is beta pixel between them
        if (!b_hasPixelBtwn)
        {
          S_L = erasePxl(S_W, S_L, p, curr_Pxl_slot); //Failure. delete p.
          p--;//restart search.
          q = S_L;//Ok. stop searching.
          b_hasPixelBtwn = true;
        }
      }
    }
    
  }

}

void  STomoSh_INT3::matchAlBePairBriefly(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot)
{ 
  if (S_L < 2) return;

#if 1
  //������� ������ ����, (al,be)���� �ƴѰ� type�� 0���� �����.
  bool _b_P_started = false;
  int n_delete=0;
  for (int p = 0; p < S_L ; p++)
  {
    SLOT_BUFFER_TYPE& p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);

    if (!_b_P_started && p_type == typeAl)
    {
      _b_P_started = true;//���� ����. ���д�.
    }
    else if (_b_P_started && p_type == typeBe)
    {
      _b_P_started = false;//���� ��. ���д�.
    }
    else if(p_type == typeAl || p_type == typeBe)
    {
      p_type = 0;//������. �����.
      n_delete++;
    }
  }
#else
  //���� ������ 2-pass�� �� ��. ������ �ణ ����.
  std::vector<std::pair<int, int>> PQ_pairs;

  bool _b_P_started = false;
  int index_p= -1, index_q = -1;
  for (int i = 0; i < S_L - 1; i++)
  {
    SLOT_BUFFER_TYPE i_type = *(curr_Pxl_slot + (i + 1) * S_W + 0);
    SLOT_BUFFER_TYPE i_z = *(curr_Pxl_slot + (i + 1) * S_W + 1);
    SLOT_BUFFER_TYPE i_nz = *(curr_Pxl_slot + (i + 1) * S_W + 2);

    if( !_b_P_started && i_type == type_byte_P)
    {
      index_p = i; _b_P_started = true;
    }
    if(_b_P_started && i_type == type_byte_Q)
    {
      std::pair<int, int> new_pair = std::make_pair( index_p, i);
      PQ_pairs.push_back( new_pair);
      _b_P_started = false;
    }
  }

  if(_b_P_started)//������ �ٴڸ� ó��
  {
    std::pair<int, int> new_pair = std::make_pair(index_p, S_L);//������ �� Ȱ��. 0�� ����ְ���.
    PQ_pairs.push_back(new_pair);
  }

  //dump. ���� �����͸� �� �����, PQ_pairs����� �����.
  int n_pair= 0 ;
  for( auto& pair : PQ_pairs)
  {
    int index_p = pair.first;    int index_q = pair.second;

    SLOT_BUFFER_TYPE *target_P = (curr_Pxl_slot + ((n_pair * 2 + 0) + 1) * S_W + 0);
    SLOT_BUFFER_TYPE* target_Q = (curr_Pxl_slot + ((n_pair * 2 + 1) + 1) * S_W + 0);

    SLOT_BUFFER_TYPE* source_P = (curr_Pxl_slot + (index_p + 1) * S_W + 0);
    SLOT_BUFFER_TYPE* source_Q = (curr_Pxl_slot + (index_q + 1) * S_W + 0);

    memcpy(target_P, source_P, sizeof(SLOT_BUFFER_TYPE) * 3);
    memcpy(target_Q, source_Q, sizeof(SLOT_BUFFER_TYPE) * 3);

    n_pair++;
  }
  S_L = n_pair*2;
#endif
}

size_t STomoSh_INT3::countType(const size_t S_W/*slot width, always 3*/,
  const size_t S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot, int _typeByte)
{
  int n_type = 0;
  for (int p = 0; p < S_L; p++)
  {
    SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    if (p_type & _typeByte)
    {
      n_type++;
    }
  }
  return n_type;
}

SLOT_SUM_TYPE STomoSh_INT3::sumType(const size_t S_W/*slot width, always 3*/,
  const size_t S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot, int _typeByte)
{
  SLOT_SUM_TYPE sum_type = 0;
  for (int p = 0; p < S_L; p++)
  {
    SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    if (p_type & _typeByte)
    {
      SLOT_BUFFER_TYPE p_z = *(curr_Pxl_slot + (p + 1) * S_W + 1);
      sum_type += p_z;
    }
  }
  return sum_type;
}

void  STomoSh_INT3::matchPairNumber_Al_Be(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot)
{
  //check if alphas and betas have same number, assuming the input object is a closed volume.
  //alpha-beta�� ������ ����.�� ������ al�� z�� ���� ��, be�� ���� ���� ����.
  size_t n_al = countType(S_W, S_L, curr_Pxl_slot, typeAl);
  size_t n_be = countType(S_W, S_L, curr_Pxl_slot, typeBe);

  if (n_al > n_be)
  {//if there are more alphas, delete alpha with higher  z, to reduce error to the final Vss .
    size_t n_diff = n_al - n_be;    int p = 0; 
    while (n_diff > 0 && p < S_L)
    {
      SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
      if (p_type & typeAl)
      {
        S_L = erasePxl(S_W, S_L, p, curr_Pxl_slot);  n_diff--;
      }
      p++;
    };
  }
  else if( n_al < n_be)
  {//if there are more betas, delete one with lower z, to reduce error to the final Vss .
    size_t n_diff = n_be - n_al;    int p = S_L - 1;
    while (n_diff > 0 && p >= 0)
    {
      SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
      if(p_type &typeBe)
      {
        S_L = erasePxl(S_W, S_L, p, curr_Pxl_slot);  n_diff--;
      }
      else   {   p--; }
    };
  }
}

void STomoSh_INT3::createTCPixels(const size_t S_W/*slot width, always 3*/,
  const size_t S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot)
{
  for (int p = 0; p < S_L; p++)
  {
    SLOT_BUFFER_TYPE& p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    if( p_type & typeAl)
    {
      p_type |= typeTC;
      return;
    }
  }
}

void  STomoSh_INT3::createShadowBriefly(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot,
  FLOAT32 theta_c_Radian
  )
{//Be�ȼ��߿��� �Ӱ谢 ������ �����ϸ� espNVB bit���� �߰��Ѵ�.
  FLOAT32 threshold = FLOAT32(-1. * ::sin(theta_c_Radian));

  bool _bPairStarted = false;
  bool bExplicitPairStarted = false;
  bool bImplicitPairStarted = false;
  for (int p = 0; p < S_L; p++)
  {
    SLOT_BUFFER_TYPE& p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    FLOAT32      p_nZ   = *(curr_Pxl_slot + (p + 1) * S_W + 2) / g_fNORMALFACTOR;
     //explicit, implicit ���о��� NV, SS�� ���ÿ� ó��.
    if ((p_type & typeBe) && (p_nZ < g_fMARGIN))//beta �ȼ� ����
    {
      if (!bExplicitPairStarted && p_nZ < threshold)
      {
        p_type |= typeSSB; bExplicitPairStarted = true;
      }
      if(!bImplicitPairStarted && p_nZ > threshold)
      {
        p_type |= typeNVB; bImplicitPairStarted = true;
      }
    }
    else if ((p_type & typeAl))
    {
      if(bExplicitPairStarted)
      {
        p_type |= typeSSA; bExplicitPairStarted = false;
      }
      if (bImplicitPairStarted)
      {
        p_type |= typeNVA; bImplicitPairStarted = false;
      }
    }
  }

  if (bExplicitPairStarted)//�� ã������ �ٴ��� NVA�� ����.
  {
  //Note: the floor sentinel has z=0, so skipping it when the slot is full does not
  //change the Vss sums; writing past the slot end would corrupt the next slot's
  //header (count |= typeSSA/typeNVA), which is what broke dense meshes (mss=0).
    if (S_L < voxel_info.nSlotCapacityHeight - 1)
    {
       *(curr_Pxl_slot + (S_L + 1) * S_W + 0) |=typeSSA; //�� ���Կ� 0�� �ְ�.
       S_L++;//���� ũ�⸦ ����.
    }
     bExplicitPairStarted = false;
  }
  if (bImplicitPairStarted)//�� ã������ �ٴ��� NVA�� ����.
  {
    if (S_L < voxel_info.nSlotCapacityHeight - 1)
    {
      *(curr_Pxl_slot + (S_L + 1) * S_W + 0) |= typeNVA;
      S_L++;//���� ũ�⸦ ����.
    }
    bImplicitPairStarted = false;
  }

}


size_t  STomoSh_INT3::createShadowCastor(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot,
  FLOAT32 theta_c_Radian,
  bool _bUseExplicitSS)
{//Be�ȼ��߿��� �Ӱ谢 ������ �����ϸ� espNVB bit���� �߰��Ѵ�.
  FLOAT32 threshold = FLOAT32 (-1. * ::sin(theta_c_Radian));

  int n_castor = 0;
  for (int p = 0; p < S_L; p++)
  {
    SLOT_BUFFER_TYPE& p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    FLOAT32      nZ_p   = *(curr_Pxl_slot + (p + 1) * S_W + 2) / g_fNORMALFACTOR;
    if ((p_type & typeBe) && ( nZ_p < g_fMARGIN))
    {
      if (_bUseExplicitSS && nZ_p < threshold)
      {
        p_type |= typeSSB; n_castor++;
      }
      else if(!_bUseExplicitSS && nZ_p > threshold)
      {
        p_type |= typeNVB; n_castor++;
      }
    }
  }

  return n_castor;
}

size_t  STomoSh_INT3::matchPairNumber_SS(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot,
  int nvb_type_byte, int be_type_byte)
{ //compare the number of two types. if there are more NVB than be, delete NVB with lower z values.
  //NVB�� ������ Be���� ������ z�� ���� ������ �����Ѵ�.
  size_t n_NVB = countType(S_W, S_L, curr_Pxl_slot, nvb_type_byte);
  size_t n_be  = countType(S_W, S_L, curr_Pxl_slot, be_type_byte);

  size_t n_diff = n_NVB - n_be;
  if(n_diff<= 0) { return n_NVB; }

  int p = S_L-1;
  while (n_diff > 0 && p>=0)
  {
    SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    if (p_type & nvb_type_byte)   {  S_L = erasePxl(S_W, S_L, p, curr_Pxl_slot);    n_diff--;    }
    else    {      p--;    }
  };

  return n_NVB - n_diff;
}

void  STomoSh_INT3::insertPxl(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot,
  SLOT_BUFFER_TYPE _type, SLOT_BUFFER_TYPE _z, SLOT_BUFFER_TYPE _nZ)
{
  if(S_L >= voxel_info.nSlotCapacityHeight-1) return;//error

  int p_insert = 0;//position to insert
  for (int p = 0; p < S_L ; p++)
  {
    SLOT_BUFFER_TYPE p_z = *(curr_Pxl_slot + (p + 1) * S_W + 1);

    if(p_z == _z)//if there is already a pipxel with the same z value, update type only..
    {
      *(curr_Pxl_slot + (p + 1) * S_W + 0) |= _type;
      return;
    }
    else if(p_z > _z)
    {
      p_insert = p+1;
    }
  }

  memcpy(curr_Pxl_slot + (p_insert + 2) * S_W +0, curr_Pxl_slot + (p_insert + 1) * S_W, sizeof(SLOT_BUFFER_TYPE) * S_W * (S_L -p_insert));
    
  S_L++;
  *(curr_Pxl_slot + (p_insert + 1) * S_W + 0) = _type;
  *(curr_Pxl_slot + (p_insert + 1) * S_W + 1) = _z;
  *(curr_Pxl_slot + (p_insert + 1) * S_W + 2) = _nZ;
}

void  STomoSh_INT3::createShadowAcceptor(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot,
  int shadow_castor, int shadow_acceptor)
{
  //Be�ȼ��� z�� �Ʒ� �������� ù��° �߰ߵǴ� al�ȼ���, ������ �ٴ��� nva_type_byte�� ��Ʈ �����Ѵ�.
  for (int p = 0; p < S_L; p++)
  {
    SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    SLOT_BUFFER_TYPE p_z    = *(curr_Pxl_slot + (p + 1) * S_W + 1);
    if (p_type & shadow_castor)
    {
      bool bFoundNVA = false;
      for(int q = 0 ; q < S_L ; q++)
      {
        SLOT_BUFFER_TYPE& q_type = *(curr_Pxl_slot + (q + 1) * S_W + 0);
        SLOT_BUFFER_TYPE& q_z    = *(curr_Pxl_slot + (q + 1) * S_W + 1);
        if ( (q_type & typeAl) > 0 && p_z >= q_z)
        {
          q_type |= shadow_acceptor; bFoundNVA = true;  q = S_L;//exit loop
        }
      }
      if(!bFoundNVA)//�� ã������ �ٴ��� NVA�� ����.
      {
        /**(curr_Pxl_slot + (S_L + 1) * S_W + 0) = nva_type_byte; S_L++;*/
        insertPxl(S_W, S_L, curr_Pxl_slot, shadow_acceptor, 0, 0);
      }
    }
  }
}


SLOT_SUM_TYPE  STomoSh_INT3::createVoPixels(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot)
{//calculate Vo value from (al - be), and insert a pixel.
  //(Al - Be)�� ���� Vo���� ����ϰ�, �������� ���� ���Կ� �ȼ��� �߰��Ѵ�.
  SLOT_SUM_TYPE al_sum = 0, be_sum = 0;
  for (int p = 0; p < S_L ; p++)
  {
    SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    SLOT_SUM_TYPE p_z = *(curr_Pxl_slot + (p + 1) * S_W + 1);
    if (p_type & typeAl)
    {
      al_sum += p_z;
    }
    else if (p_type & typeBe)
    {
      be_sum += p_z;
    }
  }

  SLOT_SUM_TYPE Vo_z = (al_sum > be_sum) ? (al_sum - be_sum) : 0;//���� ������� ���� ���̳ʽ� ���� ���� �� �ִ�.
#ifndef _USE_BRIEF_SLOT_PAIRING
  insertPxl(S_W, S_L, curr_Pxl_slot, toTypeByte(enumPixelType::eptVo), clampSlotSumToBuffer(Vo_z), 0);
#endif
  return Vo_z;
}

SLOT_SUM_TYPE  STomoSh_INT3::createVss_Explicit(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot)
{//calculate Vss value from (ssb - ssa). and insert a pixel
  //(SSB - SSA)�� ���� SS���� ���ϰ�, �������� ���� �ȼ��� �߰��Ѵ�.

  SLOT_SUM_TYPE ssb_sum = 0, ssa_sum = 0;

  for (int p = 0; p < S_L; p++)
  {
    SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    SLOT_SUM_TYPE p_z       = *(curr_Pxl_slot + (p + 1) * S_W + 1);
    if (p_type & typeSSB)      {   ssb_sum += p_z;    }
    else if (p_type & typeSSA) {   ssa_sum += p_z;    }
  }

  SLOT_SUM_TYPE Vss_z = ssb_sum - ssa_sum;
#ifdef _USE_BRIEF_SLOT_PAIRING
 #else
  if (Vss_z != 0)//hide zero-height pixel, for pretty rendering
  {  insertPxl(S_W, S_L, curr_Pxl_slot, toTypeByte(enumPixelType::eptVss), clampSlotSumToBuffer(Vss_z), 0); }
#endif
  return Vss_z;

}

SLOT_SUM_TYPE  STomoSh_INT3::createVss_Implicit(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L/*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot)
{ //calculate Vss value from (-al + be + TC - NVB + NBA). and insert a pixel
  //(-al + be + TC - NVB + NBA)�� ���� Vss���� ���ϰ�, �������� ���� �ȼ��� �߰��Ѵ�.
  SLOT_SUM_TYPE al_sum = 0, be_sum = 0, TC_sum = 0, NVB_sum = 0, NVA_sum = 0;


  for (int p = 0; p < S_L; p++)
  {
    SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
    SLOT_SUM_TYPE p_z       = *(curr_Pxl_slot + (p + 1) * S_W + 1);
    if (p_type & typeAl)
    {
      al_sum += p_z;
      if (p_type & typeTC)  { TC_sum += p_z;  }
      if (p_type & typeNVA) {NVA_sum += p_z;  }
    }
    else if (p_type & typeBe)
    {
      be_sum += p_z;
      if (p_type & typeNVB) {NVB_sum += p_z;  }
    }
  }

  SLOT_SUM_TYPE Vss_z = -al_sum + be_sum + TC_sum - NVB_sum + NVA_sum;
#ifdef _USE_BRIEF_SLOT_PAIRING
#else
  if (Vss_z != 0)//hide zero-height pixel, for pretty rendering
  {
    insertPxl(S_W, S_L, curr_Pxl_slot, toTypeByte(enumPixelType::eptVss), clampSlotSumToBuffer(Vss_z), 0);
  }
#endif
  return Vss_z;

}


void  STomoSh_INT3::createAlBePxls(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L /*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot)
{
  sortSlotByZ(S_W, S_L, curr_Pxl_slot);//sort pixels with highest z-coorinates first.
  splitAlBe(S_W, S_L, curr_Pxl_slot);//mark types as either alpha or beta. 
#ifndef _USE_BRIEF_SLOT_PAIRING
  removeZNearPxls(S_W, S_L, curr_Pxl_slot, toTypeByte(enumPixelType::espAl));//remove pixels with same type and z_coordinate
  removeZNearPxls(S_W, S_L, curr_Pxl_slot, toTypeByte(enumPixelType::espBe));
#endif
}

void  STomoSh_INT3::vslotPair(
  const size_t S_W/*slot width, always 3*/,
  SLOT_BUFFER_TYPE& S_L /*slot length. n_pixels_in_curr_slot*/,
  SLOT_BUFFER_TYPE* curr_Pxl_slot,
  FLOAT32 theta_c,
  SLOT_SUM_TYPE& slotVo,
  SLOT_SUM_TYPE& slotVss)
{
  slotVo = 0;
  slotVss = 0;
#ifdef _USE_BRIEF_SLOT_PAIRING
  createAlBePxls(S_W, S_L, curr_Pxl_slot);
  matchAlBePairBriefly(S_W, S_L, curr_Pxl_slot);
  slotVo = createVoPixels(S_W, S_L, curr_Pxl_slot);//calculate object volume from V_al - V_be.
  createShadowBriefly(S_W, S_L, curr_Pxl_slot, theta_c);//create NVB, SSB simultaensouly.

  if (printer_info.bUseExplicitSS)
  { slotVss = createVss_Explicit(S_W, S_L, curr_Pxl_slot); }//Vss = sum of SS pixels' z values
  else
  { createTCPixels(S_W, S_L, curr_Pxl_slot);//find top-covering pixels. the first-coming alpha pixel.
    slotVss = createVss_Implicit(S_W, S_L, curr_Pxl_slot);}//Vss = -V_al + V_be + V_tc + V_nvb - V_nva
  
#else
  //At the start, each slot has only alpha and beta pixels only.
  createAlBePxls(           S_W, S_L, curr_Pxl_slot);

  //Al-Be slot pairing.
  matchAlBeAlternation(     S_W, S_L, curr_Pxl_slot);//check if alpha-beta-alpha-beta-... alternation order is right.
  matchPairNumber_Al_Be(    S_W, S_L, curr_Pxl_slot);//check if alphas and betas have same number, assuming the input object is a closed volume.

  slotVo = createVoPixels(           S_W, S_L, curr_Pxl_slot);//calculate object volume from V_al - V_be.

  if (printer_info.bUseExplicitSS)
  {
    size_t n_SSB = createShadowCastor(S_W, S_L, curr_Pxl_slot, theta_c, true);//find starting point of shadows(=support structures)
    if( n_SSB>0)
    {
      removeZNearPxls(      S_W, S_L, curr_Pxl_slot, toTypeByte(enumPixelType::espSSB));//delete noise
      createShadowAcceptor( S_W, S_L, curr_Pxl_slot, toTypeByte(enumPixelType::espSSB), toTypeByte(enumPixelType::espSSA));//find end point of shadows.
      matchPairNumber_SS(   S_W, S_L, curr_Pxl_slot, toTypeByte(enumPixelType::espSSB), toTypeByte(enumPixelType::espBe));//delete noise
    }
    slotVss = createVss_Explicit(     S_W, S_L, curr_Pxl_slot);//Vss = sum of SS pixels' z values
  }
  else
  {
    createTCPixels(         S_W, S_L, curr_Pxl_slot);//find top-covering pixels. the first-coming alpha pixel.

    size_t n_NVB = createShadowCastor(S_W, S_L, curr_Pxl_slot, theta_c, false);//find start point of NV pixels.
    if (n_NVB > 0)
    {
      removeZNearPxls(      S_W, S_L, curr_Pxl_slot, toTypeByte(enumPixelType::espNVB));//delete noise
      createShadowAcceptor( S_W, S_L, curr_Pxl_slot, toTypeByte(enumPixelType::espNVB), toTypeByte(enumPixelType::espNVA));//find end point of NV pixels.
      matchPairNumber_SS(   S_W, S_L, curr_Pxl_slot, toTypeByte(enumPixelType::espNVB), toTypeByte(enumPixelType::espBe));//delete noise
    }
    slotVss = createVss_Implicit(     S_W, S_L, curr_Pxl_slot);//Vss = -V_al + V_be + V_tc + V_nvb - V_nva
  }
#endif


}


TPVector  STomoSh_INT3::slotsToPxls(enumPixelType _enum_type)//send data to python
{
  int _typeByte = toTypeByte(_enum_type);
  TPVector pxls;

  SLOT_BUFFER_TYPE* slot_buf = voxel_info.SlotBuf_108f;
  int X_D = voxel_info.x_dim;
  int Y_D = voxel_info.y_dim;
  int S_W = voxel_info.nSlotCapacityWidth;
  int S_H = voxel_info.nSlotCapacityHeight;
  for (int slotX = 0; slotX < X_D; slotX++)
  {
    for (int slotY = 0; slotY < Y_D; slotY++)
    {
      VOXEL_ID_TYPE slot_start_pos = (slotX * Y_D + slotY) * S_W * S_H;//����: type_buffer������ ��� ������ vxl_id�� �������.
      SLOT_BUFFER_TYPE n_pixels_in_curr_slot = *(slot_buf + slot_start_pos + 0);
      for (int p = 0; p < n_pixels_in_curr_slot; p++)
      {
        VOXEL_ID_TYPE newpxl_pos = VOXEL_ID_TYPE(slot_start_pos + (p + 1) * S_W);// (p+1): 0��°�� slot info�̹Ƿ� ����.
        SLOT_BUFFER_TYPE pxl_type = *(slot_buf + newpxl_pos + 0);
        if (pxl_type & _typeByte)
        {
          int slotZ = *(slot_buf + newpxl_pos + 1);
          int nrmZ  = *(slot_buf + newpxl_pos + 2);
          STomoPixel new_pxl(slotX, slotY, slotZ, 0, 0, nrmZ);
          pxls.push_back(new_pxl);
        }
      }
    }
  }

  return pxls;
}


int  STomoSh_INT3::triVoxel(  
  FLOAT32* _v0,
  FLOAT32* _v1,
  FLOAT32* _v2,
  FLOAT32* n0,
  FLOAT32* n1,
  FLOAT32* n2,
  /*output */ SLOT_BUFFER_TYPE* _Type_buffer)
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

  FLOAT32  HALF_VOXEL_SIZE = printer_info.dVoxel * FLOAT32(0.5);
  FLOAT32 shell_z_offset = FLOAT32(int(printer_info.shell_thickness + FLOAT32(0.999)));
  FLOAT32 v_center[3] = {0.,0.,HALF_VOXEL_SIZE };

  int n_voxel = 0;
  for (int x = x0; x <= x1; x++)
  {
    v_center[0] = FLOAT32(x + g_fMARGIN + HALF_VOXEL_SIZE);
    for (int y = y0; y <= y1; y++)
    {
      v_center[1] = FLOAT32(y + g_fMARGIN + HALF_VOXEL_SIZE);
      FLOAT32 u, v, w;
      if (_getBaryCoord(v_center, v0, v1, v2, u, v, w))
      {
        FLOAT32 pxl[3], nrm[3];
        _bary_product(v0, v1, v2, u, v, w, pxl);
        _bary_product(n0, n1, n2, u, v, w, nrm);
        voxel_info.SetBit(_Type_buffer, pxl, nrm, 0x00); n_voxel++;
        if(printer_info.bShellMesh && printer_info.shell_thickness > g_fMARGIN)
        { 
          pxl[2] += (nrm[2]>=0)? -shell_z_offset : shell_z_offset;//Note: put the subsidiary beta pixel under the alpha
                                     //Note: put the subsidiary alpha pixel above the beta 
          nrm[0] *= -1.; nrm[1] *= -1.;   nrm[2] *= -1.;
          voxel_info.SetBit(_Type_buffer, pxl, nrm, 0x00); n_voxel++;
        }
      }
    }
  }

  if (n_voxel == 0)//very small triangle
  {
    FLOAT32 tri_center[3];
    for (int i = 0; i < 3; i++)
    {
      tri_center[i] = (_v0[i] + _v1[i] + _v2[i]) * FLOAT32(0.333333) + g_fMARGIN;
    }

    voxel_info.SetBit(_Type_buffer, tri_center, n0, 0x00);
    if (printer_info.bShellMesh && printer_info.shell_thickness > g_fMARGIN)
    {
      FLOAT32 sub_center[3] = { tri_center[0], tri_center[1], tri_center[2] };
      FLOAT32 sub_nrm[3] = { -n0[0], -n0[1], -n0[2] };
      sub_center[2] += (n0[2] >= 0) ? -shell_z_offset : shell_z_offset;
      voxel_info.SetBit(_Type_buffer, sub_center, sub_nrm, 0x00);
    }
  }

  return n_voxel;
}

void  STomoSh_INT3::Calculate(void)
{
  FLOAT32 pairedVo = vm_info.Vo;
  FLOAT32 pairedVss = vm_info.Vss;
  vm_info.Init();
  vm_info.Vo = pairedVo;
  vm_info.Vss = pairedVss;

  int X_D = voxel_info.x_dim;
  int Y_D = voxel_info.y_dim;
  int S_W = voxel_info.nSlotCapacityWidth;
  int S_H = voxel_info.nSlotCapacityHeight;
  //Empty slots contribute 0 to every sumType, so iterate only occupied slots. dirtySlots now
  //holds voxelize + bed slots; sort ascending to keep the float accumulation order identical to
  //the old row-major full-grid scan.
  std::sort(voxel_info.dirtySlots.begin(), voxel_info.dirtySlots.end());
  for (size_t i = 0; i < voxel_info.dirtySlots.size(); i++)
  {
      SLOT_BUFFER_TYPE* curr_Pxl_slot = voxel_info.SlotBuf_108f + voxel_info.dirtySlots[i] * S_W * S_H;//current slot

      SLOT_BUFFER_TYPE slot_len = *(curr_Pxl_slot + 0);

      vm_info.Va  += sumType(S_W, slot_len, curr_Pxl_slot, typeAl);
      vm_info.Vb  += sumType(S_W, slot_len, curr_Pxl_slot, typeBe);
      vm_info.Vnv += sumType(S_W, slot_len, curr_Pxl_slot, typeNVB) \
                    - sumType(S_W, slot_len, curr_Pxl_slot,typeNVA);
      vm_info.Vtc += sumType(S_W, slot_len, curr_Pxl_slot, typeTC);//p-orbital test

      //consider bed structure
      vm_info.Vbed += sumType(S_W, slot_len, curr_Pxl_slot, typeBed) * printer_info.BedThickness;
      //vm_info.Vss +=  vm_info.Vbed;
  }

  #if 0
  double v_scale_factor = 1. / pow(double(iVOXELFACTOR), 3.);
  vm_info.Vo  *= v_scale_factor;
  vm_info.Vss *= v_scale_factor;
  vm_info.Va  *= v_scale_factor;
  vm_info.Vb  *= v_scale_factor;
  vm_info.Vtc *= v_scale_factor;
  vm_info.Vnv *= v_scale_factor;
  #endif

  vm_info.VolToMass(printer_info);
}

TPVector   STomoSh_INT3::GetSSPixels(bool _bUseExplicitSS)
{
  TPVector pxls;

  int X_D = voxel_info.x_dim;
  int Y_D = voxel_info.y_dim;
  int S_W = voxel_info.nSlotCapacityWidth;
  int S_H = voxel_info.nSlotCapacityHeight;
  SLOT_BUFFER_TYPE* slot_buf = voxel_info.SlotBuf_108f;

  int ss_start_z=-1, ss_end_z=-1;
  for (int slotX = 0; slotX < X_D; slotX++)
  {
    for (int slotY = 0; slotY < Y_D; slotY++)
    {
#ifdef _DEBUG
  //if (slotX == 3 && slotY == 63)
  //{
  //int debug = 0;
  //}
#endif
      SLOT_BUFFER_TYPE* curr_Pxl_slot = voxel_info.SlotBuf_108f + (slotX * Y_D + slotY) * S_W * S_H;//current slot

      SLOT_BUFFER_TYPE slot_len = *(curr_Pxl_slot + 0);
      ss_start_z = -1; ss_end_z = -1;//reset
      for (int p = 0; p < slot_len; p++)
      {
        SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
        SLOT_BUFFER_TYPE p_z    = *(curr_Pxl_slot + (p + 1) * S_W + 1);

#ifdef _USE_BRIEF_SLOT_PAIRING
        //�̹����� NV, SS ��� ������ ����.
        if (p_type & typeSSB) { ss_start_z = p_z; }//start of SS pxls.
        if (p_type & typeSSA) { ss_end_z = p_z; }//shadow acceptor
#else
        if (_bUseExplicitSS)
        {
          if (p_type & typeSSB) { ss_start_z = p_z; }//start of SS pxls.
          if (p_type & typeSSA) { ss_end_z   = p_z; }//shadow acceptor
        }
        else
        {
          if ((p_type & typeBe) && !(p_type & typeNVB)) { ss_start_z = p_z; }//start of SS pxls.
          if ((ss_start_z >= 0) && (p_type & typeAl)) { ss_end_z = p_z; }//al_pxl is shadow acceptor
          if ((ss_start_z >= 0) && (p == slot_len - 1)) { ss_end_z = 0; }//bottom plate is shadow acceptor
        }
#endif

        if (ss_start_z > -1 && ss_end_z > -1)
        { //register ss_pxls 
          for (int ss_z = ss_start_z; ss_z >= ss_end_z; ss_z--)
          {
            STomoPixel new_pxl(slotX, slotY, ss_z, 0, 0, 0);    pxls.push_back(new_pxl);
          }
          ss_start_z = -1; ss_end_z = -1;//reset
        }

      }
    }
  }
  return pxls;
}

//----------------------------------------------------------------------------------------------
//
//	bed structure
// 
//----------------------------------------------------------------------------------------------

inline float dist2D(int x0 , int y0 , int x1 , int y1)
{
  return sqrt( ((float(x0) - x1)*(float(x0) - x1) + (float(y0) - y1)*(float(y0) - y1)));
}

bool  STomoSh_INT3::IsBedCandidate(int  X , int  Y)//(X,Y)�� ���� �ִ� �Ÿ���  ak, be, SSA ���� �ִ��� Ȯ���Ѵ�. ����: type=0�� ����� ���� ����.
{
  int X_D = voxel_info.x_dim;
  int Y_D = voxel_info.y_dim;
  int S_W = voxel_info.nSlotCapacityWidth;
  int S_H = voxel_info.nSlotCapacityHeight;
  SLOT_BUFFER_TYPE* slot_buf = voxel_info.SlotBuf_108f;

  int radius = printer_info.BedOuterBound;

  float min_dist = 1e5;

  //find min distance to nearest pxl
  for (int slotX = max( X - radius, 0); slotX < min( X + radius, X_D); slotX++)
  {
    for (int slotY = max( Y - radius, 0) ; slotY < min( Y+ radius, Y_D); slotY++)
    {
      SLOT_BUFFER_TYPE* curr_Pxl_slot = voxel_info.SlotBuf_108f + (slotX * Y_D + slotY) * S_W * S_H;//current slot
      SLOT_BUFFER_TYPE slot_len = *(curr_Pxl_slot + 0);
      if(slot_len > 0)
      {
        int p = slot_len-1;// last pxl, on bottom plate. 
        SLOT_BUFFER_TYPE p_z    = *(curr_Pxl_slot + (p + 1) * S_W + 1);
        SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
        float dist = dist2D( X, Y, slotX, slotY);
        if(p_z == 0 && 
          ((p_type & typeAl) || (p_type & typeBe) || (p_type & typeSSA) || (p_type & typeSS) ) )
        {
          min_dist = min( min_dist, dist);  
        }
      }
    }
  }

  if(min_dist > printer_info.BedOuterBound) return false;

  if(     printer_info.BedType == enumBedType::ebtBrim ||
          printer_info.BedType == enumBedType::ebtRaft)   return true;  
  else if(printer_info.BedType == enumBedType::ebtSkirt && 
    min_dist > printer_info.BedInnerBound) return true;

  return false;
}

void  STomoSh_INT3::GenerateBed(void)
{
  if(printer_info.BedType == enumBedType::ebtNone) return;

  int X_D = voxel_info.x_dim;
  int Y_D = voxel_info.y_dim;
  int S_W = voxel_info.nSlotCapacityWidth;
  int S_H = voxel_info.nSlotCapacityHeight;
  SLOT_BUFFER_TYPE* slot_buf = voxel_info.SlotBuf_108f;

  int ss_start_z=-1, ss_end_z=-1;
  FLOAT32 pxl[3] = {}, nrm[3] = {};

  //The bed only appears within BedOuterBound of the object footprint, so far-away empty
  //slots (the vast majority) can never be candidates and IsBedCandidate would reject them.
  //Restrict the scan to the occupied-slot bounding box grown by the outer bound. This is a
  //strict superset of every candidate slot -> bit-identical to the full-grid scan, but for a
  //small mesh it turns O(X_D*Y_D * radius^2) into O(footprint * radius^2).
  if (voxel_info.dirtySlots.empty()) return;//no object voxels -> no bed
  int minX = X_D, minY = Y_D, maxX = -1, maxY = -1;
  for (size_t i = 0; i < voxel_info.dirtySlots.size(); i++)
  {
    int sx = int(voxel_info.dirtySlots[i] / Y_D);
    int sy = int(voxel_info.dirtySlots[i] % Y_D);
    if (sx < minX) minX = sx;  if (sx > maxX) maxX = sx;
    if (sy < minY) minY = sy;  if (sy > maxY) maxY = sy;
  }
  const int bedMargin = int(printer_info.BedOuterBound) + 1;//ceil(BedOuterBound)+safety
  const int bx0 = max(minX - bedMargin, 0),  bx1 = min(maxX + bedMargin + 1, X_D);
  const int by0 = max(minY - bedMargin, 0),  by1 = min(maxY + bedMargin + 1, Y_D);
  for (int slotX = bx0; slotX < bx1; slotX++)
  {
    for (int slotY = by0; slotY < by1; slotY++)
    {

      //�ٴڸ��� al, be, SSA �ȼ� ���� dilation. nPxl = 0�� ���� ���ؼ���.
      SLOT_BUFFER_TYPE* curr_Pxl_slot = voxel_info.SlotBuf_108f + (slotX * Y_D + slotY) * S_W * S_H;//current slot
      SLOT_BUFFER_TYPE  slot_len = *(curr_Pxl_slot + 0);

      bool bPossibleBedPosition = false;
      if( slot_len ==0) { bPossibleBedPosition = true; }//�ƹ��͵� ���� ���� ���ؼ� �켱 ����.
      else
      {
        int p = slot_len-1;// pxl on bottom. 
        SLOT_BUFFER_TYPE p_z    = *(curr_Pxl_slot + (p + 1) * S_W + 1);
        SLOT_BUFFER_TYPE p_type = *(curr_Pxl_slot + (p + 1) * S_W + 0);
        if( p_z == 0)     {
          if(p_type == typeNVA || p_type == typeVo || p_type == typeVss) bPossibleBedPosition = true;//����: nvB�ȼ��� �������.

          if((p_type & typeAl) || (p_type & typeBe) || (p_type & typeSSA) || (p_type & typeSS)) //�ٴڿ� al, be, ssa �ȼ��� �ִ� ���� ����ϸ� �ȵ�.
          {   bPossibleBedPosition = false; }

          if( printer_info.BedType == enumBedType::ebtRaft && ((p_type & typeBe) || (p_type & typeSSA )))
          {bPossibleBedPosition = true;}//����Ʈ�� ���� beta�Ʒ� �� �� �� ����ش�.
        }
      }


      if(bPossibleBedPosition && IsBedCandidate( slotX, slotY))
      {
        pxl[0] = slotX; pxl[1] = slotY;
        pxl[2] = 1;//�̰� ������ V_bed=0�� ��.
        voxel_info.SetBit( voxel_info.SlotBuf_108f, pxl, nrm, typeBed);       
      }
    }
  }
   

}
