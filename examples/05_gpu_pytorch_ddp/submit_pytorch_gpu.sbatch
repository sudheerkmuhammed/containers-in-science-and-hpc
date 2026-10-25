#!/bin/bash
# ==============================================================================
# SLURM BATCH SUBMISSION SCRIPT: MULTI-GPU PYTORCH DDP WITH APPTAINER
# Author: Sudheer K. Mohammed
# ==============================================================================
#SBATCH --job-name=pytorch_ddp_hpc
#SBATCH --output=logs/ddp_%j.out
#SBATCH --error=logs/ddp_%j.err
#SBATCH --partition=gpu
#SBATCH --nodes=2                   # 2 Nodes
#SBATCH --ntasks-per-node=1         # 1 torchrun manager per node
#SBATCH --gpus-per-node=4           # 4 GPUs per node (8 GPUs total)
#SBATCH --cpus-per-task=16          # 16 CPU cores for dataloading
#SBATCH --mem=64G
#SBATCH --time=02:00:00

mkdir -p logs

# Find head node hostname for master rendezvous
MASTER_ADDR=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -n 1)
MASTER_PORT=29500
export MASTER_ADDR
export MASTER_PORT

CONTAINER="pytorch_24.01.sif"

echo "Launching PyTorch DDP on nodes: $SLURM_JOB_NODELIST"
echo "Master Address: $MASTER_ADDR:$MASTER_PORT"

srun apptainer exec --nv \
     --bind /scratch:/scratch \
     "$CONTAINER" \
     torchrun \
     --nnodes=$SLURM_NNODES \
     --nproc_per_node=4 \
     --rdzv_id=$SLURM_JOB_ID \
     --rdzv_backend=c10d \
     --rdzv_endpoint=$MASTER_ADDR:$MASTER_PORT \
     train_ddp.py
