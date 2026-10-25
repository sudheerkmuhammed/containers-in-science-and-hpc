# Chapter 6: Building Apptainer Containers
## Definition Files, Sandboxes, and Multi-Stage Builds

*Author: Sudheer K. Mohammed*

---

![Chapter 6 Build Workflow](../images/chapter_06_build_workflow.jpg)

### Chapter Overview
While it is common to pull existing images from public registries, production scientific computing demands custom containers tailored to specific compiler toolchains, optimized math libraries (BLAS/LAPACK), hardware drivers, and proprietary simulation codes.

In the Apptainer ecosystem, container images are authored using declarative **Definition Files** (conventionally ending in `.def`).

In this chapter, we explore:
1. The anatomy and execution lifecycle of an Apptainer Definition File.
2. The core sections: `%bootstrap`, `%files`, `%post`, `%environment`, `%runscript`, `%test`, and `%labels`.
3. Scientific Containers Interface (SCIF) apps (`%apprun`, `%appinstall`).
4. Building SIFs without root privileges using `--fakeroot`.
5. Mutable sandboxes (`--sandbox`) and interactive debugging workflows.
6. Advanced multi-stage Apptainer compilation strategies.
7. A hands-on scientific recipe: Compiling high-performance MPI C code and setting up a scientific Python stack.

---

## 6.1 Anatomy of an Apptainer Definition File

An Apptainer definition file consists of two primary structural blocks:
1. **The Header:** Specifies the base operating system, bootstrap agent, and upstream repository.
2. **Section Scripts:** Shell script blocks executed at specific phases of the container's build or runtime lifecycle.

```
+-------------------------------------------------------------------------------+
|                                  THE HEADER                                   |
|   Bootstrap: docker                                                           |
|   From: ubuntu:22.04                                                          |
|   Stage: build                                                                |
+-------------------------------------------------------------------------------+
|                              SECTION SCRIPTS                                  |
|                                                                               |
|   %files          -> Stage host files into the build chroot                   |
|   %post           -> Execute installation, compile source, download packages  |
|   %environment    -> Define variables exported at container runtime           |
|   %runscript      -> Define default entrypoint executable                     |
|   %test           -> Execute validation suite; aborts build if exit != 0      |
|   %labels         -> Attach key-value metadata (author, version, license)     |
|   %help           -> Text displayed when calling 'apptainer run-help'         |
+-------------------------------------------------------------------------------+
```

### Execution Lifecycle During `apptainer build`
When `apptainer build my_app.sif my_recipe.def` is invoked, the builder executes in strict sequence:
1. **Bootstrap Phase:** Initializes a temporary rootfs directory using the upstream provider (e.g., unpacking Docker layers or running `debootstrap`).
2. **`%files` Phase:** Copies declared host files into the temporary rootfs.
3. **`%post` Phase:** Enters a `chroot` inside the temporary rootfs with full write permissions. Executes all installation commands. Network access is enabled.
4. **`%environment` Phase:** Appends runtime environment variables to `/.singularity.d/env/90-environment.sh`.
5. **`%test` Phase:** Executes test assertions. If any command returns a non-zero exit code, the entire build is aborted and the incomplete SIF is deleted.
6. **Compression Phase:** Packs the verified rootfs into an immutable, compressed SquashFS partition inside the SIF container file.

---

## 6.2 Deep Dive into Recipe Sections

### 1. The Header
The header must be the first line of the definition file:
```apptainer
Bootstrap: docker
From: nvidia/cuda:12.3.1-devel-ubuntu22.04
```
Supported Bootstrap agents:
- `docker`: Pulls and unpacks from Docker Hub, Quay, or private OCI registries.
- `localimage`: Uses an existing local SIF or sandbox directory as the base image.
- `oras`: Pulls from OCI registries supporting OCI Artifacts.
- `debootstrap`: Bootstraps a pure Debian/Ubuntu OS from scratch using Debian mirrors.
- `yum` / `zypper`: Bootstraps Red Hat, Rocky Linux, AlmaLinux, or openSUSE.

### 2. The `%files` Section
Copies files from the host into the container filesystem during build time:
```apptainer
%files
    /home/user/src/solver.c /opt/src/solver.c
    configs/production.json /etc/app/config.json
```

### 3. The `%post` Section
The engine of the definition file. Everything in `%post` runs inside the container as simulated root:
```apptainer
%post
    export DEBIAN_FRONTEND=noninteractive
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gfortran \
        libopenmpi-dev \
        python3 \
        python3-pip

    # Clean package caches to minimize final image size
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    # Compile custom scientific code
    gcc -O3 -march=native /opt/src/solver.c -o /usr/local/bin/solver
```

### 4. The `%environment` Section
Defines environment variables that are activated whenever the container is invoked via `apptainer run`, `exec`, or `shell`.
```apptainer
%environment
    export LC_ALL=C
    export PATH=/usr/local/bin:/opt/venv/bin:$PATH
    export OMP_NUM_THREADS=4
```
*(Note: Variables set in `%environment` are NOT visible during the `%post` build phase! If you need a variable in both, export it explicitly in `%post` as well).*

### 5. The `%runscript` Section
The command executed when a user calls `apptainer run my_image.sif [args]`:
```apptainer
%runscript
    echo "Starting simulation engine..."
    exec /usr/local/bin/solver "$@"
```
*(Best Practice: Always use `exec` so that the application replaces the shell process, preserving signal handling for SLURM).*

---

## 6.3 Building Unprivileged: The `--fakeroot` Mechanism

Historically, building a Singularity image required root (`sudo`) access because creating device nodes and invoking package managers (`apt`, `yum`) requires UID 0. In shared HPC centers, regular users do not have `sudo`.

Apptainer solves this using **`--fakeroot`**.

### How `--fakeroot` Works
`--fakeroot` leverages Linux **User Namespaces** and the `/etc/subuid` and `/etc/subgid` kernel mapping files:
```bash
# Host /etc/subuid mapping:
sudheer:100000:65536
```
Inside the build namespace:
- The user's host UID (`1001`) is mapped to `UID 0` (fake root).
- A block of 65,536 subordinate UIDs are allocated to allow package managers to create system users (e.g., `www-data`, `nobody`).
- System calls that alter file ownership (`chown`) succeed inside the namespace.

```bash
# An unprivileged user builds a container directly on the cluster!
$ apptainer build --fakeroot my_scientific_app.sif recipe.def
```

---

## 6.4 The Interactive Sandbox Workflow (`--sandbox`)

Compiling massive scientific packages can take hours. If a syntax error occurs at the end of a long `%post` script, a standard build fails, discarding all progress.

To avoid this, Apptainer supports **Sandboxes**: mutable directories that represent the unpacked root filesystem.

```
+---------------------------------------------------------------------------------+
|                        THE SANDBOX ITERATION WORKFLOW                           |
|                                                                                 |
|   1. Create Sandbox from Base:                                                  |
|      $ apptainer build --sandbox dev_env/ docker://ubuntu:22.04                 |
|                                                                                 |
|   2. Enter Interactively as Writable Root:                                      |
|      $ apptainer shell --fakeroot --writable dev_env/                           |
|      dev_env# apt-get update && apt-get install -y cmake ...                    |
|      dev_env# cd /opt && git clone ... && make && make install                  |
|      dev_env# exit                                                              |
|                                                                                 |
|   3. Convert Verified Sandbox to Production SIF:                                |
|      $ apptainer build production_v1.sif dev_env/                               |
+---------------------------------------------------------------------------------+
```

The resulting `production_v1.sif` is an immutable, compressed, production-ready artifact containing all the changes made during the interactive session.

---

## 6.5 Multi-Stage Builds in Apptainer

Just like Docker, Apptainer supports multi-stage compilation to separate heavy build-time dependencies (compilers, kernel headers, git) from the final lightweight deployment image.

Below is an enterprise-grade multi-stage definition file:

```apptainer
# =====================================================================
# STAGE 1: Compilation Environment
# =====================================================================
Bootstrap: docker
From: gcc:13-bookworm
Stage: compile_stage

%files
    src/matrix_multiply.c /usr/src/matrix_multiply.c

%post
    # Compile with maximum AVX-512 vectorization
    gcc -O3 -mavx512f -fopenmp /usr/src/matrix_multiply.c -o /usr/bin/matrix_multiply

# =====================================================================
# STAGE 2: Minimal Production Runtime
# =====================================================================
Bootstrap: docker
From: debian:bookworm-slim
Stage: final_runtime

# Copy ONLY the compiled binary from Stage 1!
%files from compile_stage
    /usr/bin/matrix_multiply /usr/local/bin/matrix_multiply

%post
    # Install only the runtime OpenMP library, shedding all compilers
    apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/*

%environment
    export OMP_NUM_THREADS=8
    export LC_ALL=C

%runscript
    exec /usr/local/bin/matrix_multiply "$@"

%labels
    Author "Sudheer K. Mohammed"
    Version "1.0.0"
    Description "Multi-stage compiled matrix multiplication binary"
```

---

## 6.6 Practical Recipe: High-Performance Python & C MPI Stack

Let us examine a production-grade definition file that installs a clean Micromamba-based scientific Python environment (NumPy, SciPy, PyTorch) alongside compiled MPI tools:

```apptainer
Bootstrap: docker
From: ubuntu:22.04

%labels
    Author Sudheer K. Mohammed
    Title High-Performance Scientific Computing Container
    Version 2.0.0

%help
    This container provides an optimized scientific Python environment 
    coupled with OpenMPI and C/C++ compilation toolchains for supercomputing clusters.

    Usage:
        apptainer run --nv scientific_stack.sif [script.py]
        apptainer exec --nv scientific_stack.sif python3 -c "import torch; print(torch.cuda.is_available())"

%files
    examples/04_slurm_mpi_cluster/mpi_hello_world.c /opt/mpi_hello_world.c

%environment
    export MAMBA_ROOT_PREFIX=/opt/conda
    export PATH=/opt/conda/bin:$PATH
    export LC_ALL=C
    export PYTHONUNBUFFERED=1

%post
    export DEBIAN_FRONTEND=noninteractive
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        bzip2 \
        ca-certificates \
        curl \
        git \
        libopenmpi-dev \
        openmpi-bin \
        wget \
        && rm -rf /var/lib/apt/lists/*

    # Compile the MPI test utility
    mpicc -O3 /opt/mpi_hello_world.c -o /usr/local/bin/mpi_hello_world

    # Install Micromamba for ultra-fast, clean package resolution
    curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
    mv bin/micromamba /usr/local/bin/micromamba
    rm -rf bin

    # Create root conda environment
    export MAMBA_ROOT_PREFIX=/opt/conda
    micromamba create -y -n base -c conda-forge \
        python=3.11 \
        numpy \
        scipy \
        pandas \
        scikit-learn \
        numba

    # Clean cache
    micromamba clean -all -y

%test
    # Verify Python imports work as expected
    export MAMBA_ROOT_PREFIX=/opt/conda
    export PATH=/opt/conda/bin:$PATH
    python3 -c "import numpy; import scipy; print('NumPy & SciPy verification passed!')"
    /usr/local/bin/mpi_hello_world

%runscript
    export MAMBA_ROOT_PREFIX=/opt/conda
    export PATH=/opt/conda/bin:$PATH
    if [ $# -eq 0 ]; then
        exec python3 --version
    else
        exec python3 "$@"
    fi
```

---

## 6.7 Summary & Key Takeaways

1. **Declarative Recipes:** Apptainer `.def` files define reproducible builds across six main sections: `%files`, `%post`, `%environment`, `%runscript`, `%test`, and `%labels`.
2. **Unprivileged Building:** The `--fakeroot` flag uses Linux user namespaces to grant unprivileged users the ability to build images directly on cluster nodes.
3. **Sandbox Prototyping:** Use `apptainer build --sandbox` to debug, install, and test interactively before committing to an immutable SIF.
4. **Multi-Stage Efficiency:** Strip compilers and build headers using `%files from <stage_name>` to produce secure, minimal production containers.
