<div align="center">

# CONTAINERS IN SCIENCE & HIGH-PERFORMANCE COMPUTING
## Mastering Docker, Apptainer, and Singularity for Enterprise and Supercomputing Workloads

**Author: Sudheer K. Mohammed**

![Book Cover](./images/book_cover.jpg)

*A comprehensive technical treatise on operating system virtualization, container runtimes, multi-tenant supercomputing architectures, and production orchestration across enterprise clouds and exascale supercomputers.*

---

</div>

## 📖 Book Overview & Architecture

Modern computational science and engineering exist at the crossroads of two competing paradigms: the agility of **enterprise cloud microservices** and the raw, unyielding scale of **High-Performance Computing (HPC)** clusters.

While **Docker** conquered developer desktops and cloud data centers with its layered Union Filesystem and declarative tooling, it created a severe architectural crisis when deployed on multi-user supercomputers: root privilege escalation vulnerabilities, filesystem lock storms on Lustre and GPFS, and virtual networking latency that paralyzed MPI workloads.

From this friction arose **Singularity** and **Apptainer**—architected from first principles with an *"Integration, Not Isolation"* philosophy, single-file immutable SIF images, zero-privilege execution, and native coupling with SLURM, InfiniBand, and NVIDIA/AMD accelerators.

This book provides the definitive, unified curriculum for software engineers, systems administrators, computational researchers, and MLOps practitioners.

---

## 📚 Table of Contents & Chapter Guide

Each chapter contains deep technical analysis, architectural schematics, terminal commands, and configuration specifications:

| Chapter | Title | Visual Blueprint |
| :---: | :--- | :---: |
| **Front Matter** | [Front Matter, Foreword & Dedication](./book/00_front_matter.md) | [Book Cover](./images/book_cover.jpg) |
| **Chapter 1** | [The Containerization Revolution: From Linux Kernel Primitives to Modern Runtimes](./book/01_foundations_of_containerization.md) | [Infographic](./images/chapter_01_arch.jpg) |
| **Chapter 2** | [Docker Deep Dive: Engine Architecture, Image Layering, and Container Lifecycles](./book/02_docker_deep_dive.md) | [Infographic](./images/chapter_02_docker.jpg) |
| **Chapter 3** | [Composing Multi-Tier Architectures: Networking, Storage Volumes, and Docker Compose](./book/03_orchestrating_microservices_with_docker_compose.md) | [Infographic](./images/chapter_03_compose.jpg) |
| **Chapter 4** | [The HPC Dilemma: Why Enterprise Docker Fails on Supercomputers](./book/04_the_hpc_security_and_architectural_dilemma.md) | [Infographic](./images/chapter_04_hpc_dilemma.jpg) |
| **Chapter 5** | [The Singularity & Apptainer Paradigm: SIF Architecture and Rootless Execution](./book/05_singularity_and_apptainer_architecture.md) | [Infographic](./images/chapter_05_sif_arch.jpg) |
| **Chapter 6** | [Building Apptainer Containers: Definition Files, Sandboxes, and Multi-Stage Builds](./book/06_authoring_apptainer_recipes_and_building_sifs.md) | [Infographic](./images/chapter_06_build_workflow.jpg) |
| **Chapter 7** | [Bridging Ecosystems: Converting Docker Images to Apptainer SIF and CI/CD Automation](./book/07_bridging_ecosystems_docker_to_apptainer.md) | [Infographic](./images/chapter_07_docker_to_sif.jpg) |
| **Chapter 8** | [HPC Workload Orchestration: SLURM Integration, Multi-Node MPI, and Native GPU Acceleration](./book/08_hpc_orchestration_slurm_mpi_and_gpus.md) | [Infographic](./images/chapter_08_slurm_mpi.jpg) |
| **Chapter 9** | [Scientific & Enterprise Case Studies: Distributed AI Training, Bioinformatics, and Simulations](./book/09_scientific_and_enterprise_case_studies.md) | [Infographic](./images/chapter_09_case_studies.jpg) |
| **Chapter 10**| [Security Audits, Compliance, Production Hardening, and Future Frontiers](./book/10_security_compliance_and_production_hardening.md) | [Infographic](./images/chapter_10_security.jpg) |
| **Appendices**| [Cross-Engine Command Matrix, Troubleshooting Guide, and SLURM Templates](./book/11_appendices_and_cheatsheets.md) | Reference |

---

## 🛠️ Complete Runnable Examples & Projects

The repository includes complete, production-ready code examples corresponding to each chapter:

```
examples/
├── 01_docker_web_api/          # Production FastAPI multi-stage Docker container (Non-root, tini, curl healthcheck)
│   ├── app/main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── 02_docker_compose_stack/     # 3-tier microservice: FastAPI + Redis + PostgreSQL with network isolation
│   ├── docker-compose.yml
│   └── .env.example
├── 03_apptainer_recipes/        # Production Apptainer definition recipes
│   ├── scientific_python.def   # Micromamba-based scientific Python stack
│   └── multi_stage_c_mpi.def   # Multi-stage C/MPI compilation shedding build tools
├── 04_slurm_mpi_cluster/        # Multi-node Hybrid MPI cluster test
│   ├── mpi_hello_world.c       # C MPI code reporting ranks, hostnames, PIDs
│   ├── mpich_apptainer.def     # ABI-compatible MPICH recipe
│   └── submit_slurm_mpi.sbatch # SLURM batch job script running MPI with Apptainer
├── 05_gpu_pytorch_ddp/          # Distributed Deep Learning
│   ├── train_ddp.py            # PyTorch DistributedDataParallel (DDP) benchmark
│   └── submit_pytorch_gpu.sbatch# SLURM multi-node GPU job script with --nv
└── 06_bioinformatics_nextflow/  # Reproducible genomic pipeline
    ├── main.nf                 # FastQC & Samtools DAG pipeline
    └── nextflow.config         # Dual profile: local Docker vs HPC SLURM + Apptainer
```

---

## 🖼️ High-Resolution Architectural Illustrations

All technical diagrams in the `images/` directory are generated specifically for this book:
1. **[Book Cover](./images/book_cover.jpg)**
2. **[Chapter 1: Linux Kernel Primitives vs. Virtual Machines](./images/chapter_01_arch.jpg)**
3. **[Chapter 2: Docker Engine Internal Architecture & Overlay2 UnionFS](./images/chapter_02_docker.jpg)**
4. **[Chapter 3: Docker Compose Multi-Container Network Topology](./images/chapter_03_compose.jpg)**
5. **[Chapter 4: The Enterprise Cloud vs. HPC Architecture Dilemma](./images/chapter_04_hpc_dilemma.jpg)**
6. **[Chapter 5: Singularity Image Format (SIF) Binary Anatomy & Rootless Execution](./images/chapter_05_sif_arch.jpg)**
7. **[Chapter 6: Apptainer Definition File (.def) Pipeline & Sandboxes](./images/chapter_06_build_workflow.jpg)**
8. **[Chapter 7: Docker Registry to Apptainer SIF Conversion & CI/CD Pipeline](./images/chapter_07_docker_to_sif.jpg)**
9. **[Chapter 8: SLURM Orchestration with Multi-Node MPI & InfiniBand RDMA](./images/chapter_08_slurm_mpi.jpg)**
10. **[Chapter 9: Scientific Case Studies (PyTorch AI, Nextflow Genomics, GROMACS MD)](./images/chapter_09_case_studies.jpg)**
11. **[Chapter 10: Enterprise Container Hardening & Security Compliance Matrix](./images/chapter_10_security.jpg)**

---

## 📜 Single-Volume Edition

For readers who prefer a single comprehensive document, the entire book is compiled into:
- **[CONTAINERS_IN_SCIENCE_AND_HPC.md](./CONTAINERS_IN_SCIENCE_AND_HPC.md)**
