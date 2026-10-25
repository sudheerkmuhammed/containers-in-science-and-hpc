#!/bin/bash
# ==============================================================================
# SLURM BATCH SUBMISSION SCRIPT: MULTI-NODE HYBRID MPI WITH APPTAINER
# Author: Sudheer K. Mohammed
# ==============================================================================
#SBATCH --job-name=hybrid_mpi_apptainer
#SBATCH --output=logs/mpi_%j.out
#SBATCH --error=logs/mpi_%j.err
#SBATCH --partition=compute
#SBATCH --nodes=2                   # Request 2 physical compute nodes
#SBATCH --ntasks-per-node=8         # 8 MPI tasks per node (16 ranks total)
#SBATCH --cpus-per-task=1           # 1 core per MPI rank
#SBATCH --time=00:30:00             # Wallclock limit
#SBATCH --mem=8G                    # RAM per node

# Purge and load host modules
module purge
module load slurm
module load mpich/3.4.3

mkdir -p logs

CONTAINER="mpi_cluster.sif"

echo "Executing Hybrid MPI Job across $SLURM_NNODES nodes ($SLURM_NTASKS total ranks)..."

# Host SLURM launcher (srun) dispatches tasks into the container
srun apptainer exec \
     --bind /scratch:/scratch \
     "$CONTAINER" \
     /usr/local/bin/mpi_hello_world
