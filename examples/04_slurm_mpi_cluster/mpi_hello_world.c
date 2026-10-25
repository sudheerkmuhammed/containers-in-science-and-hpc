/*
 * High-Performance Computing MPI Benchmark Utility
 * Author: Sudheer K. Mohammed
 */

#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char** argv) {
    int world_rank;
    int world_size;
    char processor_name[MPI_MAX_PROCESSOR_NAME];
    int name_len;

    // Initialize MPI execution environment
    MPI_Init(&argc, &argv);

    // Determine calling process rank
    MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);

    // Determine total number of ranks in communicator
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);

    // Discover host/node processor name
    MPI_Get_processor_name(processor_name, &name_len);

    printf("[MPI Rank %03d / %03d] Host: %s | Container Process ID: %d\n",
           world_rank, world_size, processor_name, getpid());

    // Synchronize all ranks across the cluster
    MPI_Barrier(MPI_COMM_WORLD);

    if (world_rank == 0) {
        printf("--> [VERIFIED] All %d MPI ranks successfully initialized and synchronized across nodes.\n",
               world_size);
    }

    // Terminate MPI environment
    MPI_Finalize();
    return 0;
}
