#pragma once
#pragma warning(disable: 4819)//Unicode
#include "cuda_runtime.h"
#include "device_launch_parameters.h"
#include <cuda.h>
#include <device_functions.h>
#include <cuda_runtime_api.h>

int reducedSum(int nData, int* dev_Data);//default stream version

void reducedSum_2d(int _nSlot, int _nStream, int* matrix, int* row_sums);

void reducedSum_Streamed(int N, int* dev_src, cudaStream_t _stream, int * dev_out_buf);



