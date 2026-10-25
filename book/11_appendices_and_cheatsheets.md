# Chapter 11: Appendices & Cheatsheets
## Command Matrix, Troubleshooting Guide, and SLURM Templates

*Author: Sudheer K. Mohammed*

---

## Appendix A: Cross-Engine Command Matrix

A direct, side-by-side operational mapping between Docker, Apptainer, and Singularity commands:

| Operational Task | Docker Command | Apptainer Command | Singularity Command |
| :--- | :--- | :--- | :--- |
| **Pull Image from Registry** | `docker pull ubuntu:22.04` | `apptainer pull ubuntu.sif docker://ubuntu:22.04` | `singularity pull ubuntu.sif docker://ubuntu:22.04` |
| **Run Default Entrypoint** | `docker run --rm -it image:tag` | `apptainer run image.sif` | `singularity run image.sif` |
| **Execute Custom Command** | `docker run --rm image:tag /bin/bash` | `apptainer exec image.sif /bin/bash` | `singularity exec image.sif /bin/bash` |
| **Interactive Shell** | `docker run --rm -it image:tag /bin/sh`| `apptainer shell image.sif` | `singularity shell image.sif` |
| **Bind Mount Host Directory**| `docker run -v /host/path:/container/path` | `apptainer run -B /host/path:/container/path image.sif` | `singularity run -B /host/path:/container/path image.sif` |
| **NVIDIA GPU Passthrough** | `docker run --gpus all image:tag` | `apptainer run --nv image.sif` | `singularity run --nv image.sif` |
| **AMD ROCm Passthrough** | `docker run --device=/dev/kfd ...` | `apptainer run --rocm image.sif` | `singularity run --rocm image.sif` |
| **Build from Recipe/File** | `docker build -t myapp:1.0 -f Dockerfile .` | `apptainer build myapp.sif myapp.def` | `singularity build myapp.sif myapp.def` |
| **Build Without Sudo** | Rootless Docker setup required | `apptainer build --fakeroot myapp.sif myapp.def` | `singularity build --fakeroot myapp.sif myapp.def` |
| **Create Mutable Sandbox** | N/A (Docker containers are mutable) | `apptainer build --sandbox my_dir/ recipe.def` | `singularity build --sandbox my_dir/ recipe.def` |
| **Shell into Writable Sandbox**| `docker run -it myapp /bin/sh` | `apptainer shell --writable --fakeroot my_dir/` | `singularity shell --writable --fakeroot my_dir/` |
| **Inspect Image Metadata** | `docker inspect image:tag` | `apptainer inspect image.sif` | `singularity inspect image.sif` |
| **Inspect Recipe File** | `docker history image:tag` | `apptainer inspect --deffile image.sif` | `singularity inspect --deffile image.sif` |
| **Sign Container Cryptographically**| `cosign sign --key k.key image:tag` | `apptainer sign image.sif` | `singularity sign image.sif` |
| **Verify Container Signature**| `cosign verify --key k.pub image:tag` | `apptainer verify image.sif` | `singularity verify image.sif` |

---

## Appendix B: Production Troubleshooting Guide & Error Dictionary

When orchestrating containers across heterogeneous enterprise and supercomputing clusters, you will inevitably encounter low-level system failures. Below are the most common errors and their exact resolutions.

---

### Error 1: Out of Disk Space During Build
```
FATAL:   While performing build: ... No space left on device
```
- **Root Cause:** By default, Apptainer builds temporary root filesystems in `/tmp`. On many HPC compute nodes, `/tmp` is a small in-memory `tmpfs` slice (e.g., 2 GB). Compiling large software or pulling heavy PyTorch images exhausts `/tmp`.
- **Resolution:** Redirect Apptainer's cache and temporary directories to a high-capacity parallel filesystem or scratch disk:
```bash
export APPTAINER_TMPDIR="/scratch/user/tmp"
export APPTAINER_CACHEDIR="/scratch/user/cache"
mkdir -p "$APPTAINER_TMPDIR" "$APPTAINER_CACHEDIR"
apptainer build myapp.sif recipe.def
```

---

### Error 2: CUDA Driver / Runtime Incompatibility
```
CUDA error: no kernel image is available for execution on the device
-- OR --
CUDA driver version is insufficient for CUDA runtime version
```
- **Root Cause:** The CUDA Toolkit compiled inside your container is newer than the NVIDIA kernel driver installed on the host compute node. (For example, container requires CUDA 12.3 requiring driver >= 545, but host has driver 525 supporting only CUDA 12.0).
- **Resolution:**
  1. Check host driver version on compute node: `nvidia-smi`
  2. Pull or build a container targeting a CUDA version supported by the host driver.
  3. Verify with: `apptainer exec --nv myapp.sif nvidia-smi`

---

### Error 3: MPI Undefined Symbol / ABI Mismatch
```
mpirun: symbol lookup error: /usr/lib/x86_64-linux-gnu/libmpi.so.40: undefined symbol: ...
```
- **Root Cause:** The host MPI launcher (`srun` or `mpirun`) is attempting to wire up a container that was built with an incompatible MPI library family or an incompatible major version (e.g., host runs OpenMPI 4.1.x, but container has OpenMPI 5.0.x or MPICH).
- **Resolution:** In the container recipe (`%post`), build the exact major and minor version of OpenMPI or MPICH installed on the host cluster. Configure with identical fabric support flags (e.g., `--with-ucx`).

---

### Error 4: OOMKilled: Exit Code 137
```
slurmstepd: error: Detected 1 oom-kill event(s) in StepId=123456.0. Some of your processes may have been killed by the cgroup out-of-memory handler.
Command exited with status 137
```
- **Root Cause:** The container process exceeded the memory limit allocated by the SLURM `#SBATCH --mem` directive or Docker's `memory.max` cgroup limit.
- **Resolution:** Increase the job memory allocation in your SLURM script:
```bash
#SBATCH --mem=128G   # Request 128 Gigabytes of RAM
```
Or optimize batch sizes in your application code (e.g., lower PyTorch training `batch_size`).

---

### Error 5: Lustre / NFS Permission Denied with Host Paths
```
FATAL:   container creation failed: mount /scratch/user->/scratch/user error: while mounting: permission denied
```
- **Root Cause:** The user does not have permission to access the target directory, or Apptainer is running with rootless user namespaces without proper GID mapping for auxiliary group permissions on shared project folders.
- **Resolution:** Verify group permissions on the host using `groups` and `ls -ld /scratch/user`. If auxiliary group permissions are required, run with:
```bash
apptainer exec --compat --bind /scratch/user image.sif ...
```

---

## Appendix C: Standard SLURM Job Submission Templates

### Template 1: High-Throughput Single-Node Multi-Core CPU Job
```bash
#!/bin/bash
#SBATCH --job-name=cpu_pipeline
#SBATCH --partition=standard
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x_%j.out

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

apptainer exec \
    --bind /scratch:/scratch \
    /projects/containers/genomics_stack.sif \
    bwa mem -t $SLURM_CPUS_PER_TASK /scratch/ref.fa /scratch/reads.fq
```

---

### Template 2: Single-Node Multi-GPU Training Job
```bash
#!/bin/bash
#SBATCH --job-name=gpu_single_node
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --gpus=4
#SBATCH --mem=128G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out

apptainer exec --nv \
    --bind /scratch:/scratch \
    /projects/containers/pytorch_latest.sif \
    python3 -m torch.distributed.run --nproc_per_node=4 train.py
```

---

### Template 3: Interactive Debugging Allocation (`salloc`)
To request an interactive compute node and launch a debugging shell directly inside your Apptainer container:

```bash
# 1. Request an interactive allocation with 1 GPU and 8 CPU cores for 1 hour
$ salloc --partition=gpu-debug --nodes=1 --cpus-per-task=8 --gpus=1 --time=01:00:00

# 2. Once the allocation is granted, drop directly into the container shell on that node:
$ srun --pty apptainer shell --nv --bind /scratch:/scratch /projects/containers/dev_env.sif

# 3. Inside the interactive container:
Apptainer> python3 -c "import torch; print(torch.cuda.get_device_name(0))"
NVIDIA A100-SXM4-80GB
Apptainer> exit
```
