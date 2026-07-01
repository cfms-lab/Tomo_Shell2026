#include "CUDA_types.cuh"
#include "step4_reducedSum.cuh"
#include <stdio.h>
#include "atomicWrite.cuh"

//https://github.com/NVIDIA-developer-blog/code-samples/blob/master/posts/parallel_reduction_with_shfl/main.cu


__device__ __inline__ int warpReduceSum(int val)
{
	for (int offset = warpSize / 2; offset > 0; offset /= 2) {    val += shfl_down(val, offset, warpSize); }
	return val;
}


__device__ __inline__ int blockReduceSum(int val) 
{
	static __shared__ int shared[32];
	int lane=threadIdx.x%warpSize;
	int wid=threadIdx.x/warpSize;
	val=warpReduceSum(val);

	//write reduced value to shared memory
	if(lane==0) shared[wid]=val;
	__syncthreads();

	//ensure we only grab a value from shared memory if that warp existed
	val = (threadIdx.x<blockDim.x/warpSize) ? shared[lane] : int(0);
	if(wid==0) val=warpReduceSum(val);

	return val;
}

__global__ void device_reduce_warp_atomic_kernel(int* in, int* out, int N)
{
	int sum = int(0);
	for (int i = blockIdx.x * blockDim.x + threadIdx.x; i < N; i += blockDim.x * gridDim.x) 
	{
		sum += in[i];  
	}

	sum = warpReduceSum(sum);
	if (threadIdx.x % warpSize == 0) 
	{ 
		atomicAdd(out, sum); 
	}    
}

__global__ void device_reduce_block_atomic_kernel(int *in, int* out, int N) {
	int sum=int(0);
	for(int i=blockIdx.x*blockDim.x+threadIdx.x;i<N;i+=blockDim.x*gridDim.x) {
		sum+=in[i];
	}
	sum=blockReduceSum(sum);
	if(threadIdx.x==0)
		atomicAdd(out,sum);
}

int reducedSum(int N, int* dev_src)//default stream version
{
	int threads = 256;
	//int blocks = min((N + threads - 1) / threads, 2048);// why 2048?
	int blocks = (N + threads - 1) / threads;

	int sum = 0, * dev_out_buf = nullptr;

	cudaMalloc(&dev_out_buf, sizeof(int) * 2);  //only stable version needs multiple elements, all others only need 1
	cudaMemsetAsync(dev_out_buf, 0, sizeof(int) * 2);cudaCheckError();
	//device_reduce_warp_atomic_kernel << <blocks, threads>> > (dev_src, dev_out_buf, N);    cudaCheckError();
	device_reduce_block_atomic_kernel << <blocks, threads>> > (dev_src, dev_out_buf, N);    cudaCheckError();
	cudaDeviceSynchronize();cudaCheckError();
	cudaMemcpy(&sum, dev_out_buf, sizeof(int), cudaMemcpyDeviceToHost); cudaCheckError();
	cudaFree( dev_out_buf); cudaCheckError();
	return sum;
}

//-----------------------------------------------------------------------
void reducedSum_Streamed(int N, int* dev_src, cudaStream_t _stream, int * dev_out_buf)// stream version
{
	int threads = 256;
	//int blocks = min((N + threads - 1) / threads, 2048);// why 2048?
	int blocks = (N + threads - 1) / threads;
	
	cudaEvent_t ev_stream_finished;
	cudaEventCreate(&ev_stream_finished);

	device_reduce_warp_atomic_kernel << <blocks, threads, 0, _stream>> > (dev_src, dev_out_buf, N);    cudaCheckError();
	//device_reduce_block_atomic_kernel << <blocks, threads, 0, _stream>> > (dev_src, dev_out_buf, N);    cudaCheckError();
	cudaEventRecord(ev_stream_finished, _stream);
	cudaEventSynchronize(ev_stream_finished);

}


__global__ void cu_reducedSum_2d(int nRow, int nCol, int* matrix, int* row_sum) //[nSlot * nThread]
{
	int warp_sum = 0;
	for (int i = blockIdx.x * blockDim.x + threadIdx.x; i < nRow * nCol; i += blockDim.x * gridDim.x) 
	{
		warp_sum += matrix[i];
	}

#if 0
	warp_sum = blockReduceSum(warp_sum);//133 us
	if (threadIdx.x == 0) 
	{ 
		int iRow = (blockIdx.x * blockDim.x ) / nCol;
		if(iRow < nRow) atomicAdd(row_sum+ iRow, warp_sum);
	}  
#else
	warp_sum = warpReduceSum(warp_sum);//110 us
	if (threadIdx.x % warpSize == 0) 
	{ 
		int iRow = (blockIdx.x * blockDim.x ) / nCol;
		if(iRow < nRow) atomicAdd(row_sum+ iRow, warp_sum);
	}    
#endif
}


void reducedSum_2d(int nRow, int nCol, int* cu_matrix, int* cu_row_sums)//do multiple summing at a time
{
	int threads = 128;
	int blocks = (nRow  * nCol + threads - 1) / threads;

	cu_reducedSum_2d <<<blocks, threads>>>(nRow, nCol, cu_matrix, cu_row_sums);cudaCheckError();
	cudaDeviceSynchronize();cudaCheckError();
}

