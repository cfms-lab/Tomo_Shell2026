#include "CUDA_types.cuh"

using namespace Tomo;

cudaEvent_t start, stop;

void  cu_startTimer(void)
{
	cudaEventCreate(&start);
	cudaEventCreate(&stop);
	cudaEventRecord(start);
}

void  cu_endTimer(const char* title)
{

	cudaEventRecord(stop);
	cudaEventSynchronize(stop);
	float milliseconds = 0;
	cudaEventElapsedTime(&milliseconds, start, stop);
	if (title != nullptr) std::cout << title << " ";
	std::cout << "time=" << milliseconds << "[§Â] =" << milliseconds * 1000. << "[§Á]" << std::endl;
	cudaEventDestroy(start);
	cudaEventDestroy(stop);
}

