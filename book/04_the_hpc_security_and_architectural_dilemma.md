# Chapter 4: The High-Performance Computing (HPC) Dilemma
## Why Enterprise Docker Fails on Supercomputers

*Author: Sudheer K. Mohammed*

---

![Chapter 4 HPC Dilemma](../images/chapter_04_hpc_dilemma.jpg)

### Chapter Overview
Docker revolutionized enterprise web applications, microservices, and continuous delivery pipelines. Witnessing this success, computational scientists, bioinformaticians, and artificial intelligence researchers naturally attempted to bring Docker containers directly into their High-Performance Computing (HPC) clusters and national supercomputers.

Almost universally, HPC system administrators refused to install the Docker daemon on compute nodes.

This resistance was neither obstinacy nor technological conservatism. It was rooted in a profound architectural incompatibility: **the fundamental assumptions that make Docker brilliant for enterprise cloud platforms render it dangerous, inefficient, and disruptive on multi-tenant scientific supercomputers.**

In this chapter, we dissect:
1. The security crisis of the Docker daemon: The `/var/run/docker.sock` privilege-escalation vulnerability.
2. Shared parallel filesystems (Lustre, GPFS, NFS) and the failure of root squashing.
3. High-speed interconnects (InfiniBand, RoCE) and why virtual network bridges destroy MPI scalability.
4. Batch workload managers (SLURM, PBS, LSF) vs. background daemon lifecycles.
5. The architectural mandate that led directly to the creation of Singularity and Apptainer.

---

## 4.1 The Security Vulnerability: The "Docker Group is Root" Reality

In an enterprise cloud setting, a virtual machine is typically dedicated to a single tenant or a single application team. If a developer runs as root inside a container running on an Amazon EC2 instance, they compromise only their own ephemeral VM.

In an HPC environment, a single compute node costing $100,000+ (equipped with eight NVIDIA H100 GPUs and 2 Terabytes of RAM) is concurrently shared among dozens of untrusted researchers from different departments, institutions, or corporate competitors.

### The Privilege Escalation Vector
To allow an unprivileged user to execute Docker commands without typing `sudo`, administrators traditionally add the user to the `docker` UNIX group. 

**Adding a user to the `docker` group is cryptographically and operationally equivalent to granting them passwordless `sudo` root access to the entire cluster.**

Consider this simple exploit executed by an unprivileged user (`UID 1005`):

```bash
# An unprivileged user with docker group access escapes container isolation
$ id
uid=1005(researcher) gid=1005(researcher) groups=1005(researcher),999(docker)

# Mount the entire host root filesystem into an ephemeral container
$ docker run --rm -v /:/hostfs alpine chroot /hostfs /bin/bash

# Inside the container, the user is now the true host root!
# They can read /etc/shadow, add SSH keys, or alter system kernel modules:
root@node01:/# cat /etc/shadow
root@node01:/# echo "researcher ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
```

Even if the Docker daemon runs with user namespaces (`userns-remap`), complex volume mounts, raw device passthroughs, and system call capabilities still expose expansive kernel attack surfaces. On a multi-user supercomputer, this risk is unacceptable.

---

## 4.2 The Filesystem Conflict: Distributed Parallel Storage

HPC compute nodes do not rely on local solid-state drives for primary project data. Instead, thousands of nodes are interconnected to massive **Parallel Distributed Filesystems (PFS)** such as **Lustre**, **IBM Spectrum Scale (GPFS)**, or enterprise **NFS**.

```
+-----------------------------------------------------------------------------------+
|                        PARALLEL FILESYSTEM (LUSTRE / GPFS)                        |
|                                                                                   |
|           /home/userA (UID: 1001)           /scratch/userB (UID: 1002)            |
+-----------------------------------------------------------------------------------+
           ▲                                                 ▲
           │ NFS / Lustre Client                             │ NFS / Lustre Client
           │ (Enforces POSIX UID/GID)                        │ (Enforces POSIX UID/GID)
+----------┴------------------------+            +-----------┴----------------------+
|          COMPUTE NODE 01          |            |          COMPUTE NODE 02         |
|                                   |            |                                  |
|   [Docker Daemon (Root: UID 0)]   |            |   [Apptainer (Preserves UID)]    |
|   - Container writes as UID 0     |            |   - Container writes as UID 1002 |
|   - Triggers ROOT_SQUASH error!   |            |   - Native POSIX permissions!    |
|   - Files written as 'nobody'     |            |   - Clean user ownership!        |
+-----------------------------------+            +----------------------------------+
```

### 1. Root Squashing (`root_squash`)
To prevent compromised client nodes from overwriting cluster-wide data, storage filers enable **root squashing**. Any file operation initiated by `UID 0` (root) is automatically mapped by the NFS/Lustre server to the unprivileged identity `nobody:nogroup` (UID 65534).

When an enterprise Docker container attempts to write output or intermediate simulation checkpoints to `/home/user` as root:
- The NFS server intercepts the request.
- The write is squashed to `nobody`.
- The job crashes with `Permission Denied` because `nobody` lacks write permissions in `/home/user`.

### 2. The OverlayFS Breakdown on Network Filesystems
Docker's storage architecture relies on `Overlay2`. OverlayFS requires specific filesystem primitives—namely extended attributes (`xattr`), d_type directory support, and file locking semantics—that are either unsupported or incur massive performance penalties on distributed parallel filesystems like Lustre. Storing Docker's `/var/lib/docker` directory on a shared network mount leads to cache corruption, metadata lock storms, and node hangs.

---

## 4.3 The Interconnect & MPI Challenge

Enterprise microservices communicate over TCP/IP using HTTP REST, gRPC, or WebSockets. Latency on the order of 1 to 5 milliseconds is considered acceptable.

In High-Performance Computing, thousands of CPU cores and GPUs collaborate to solve a single mathematical problem (e.g., weather forecasting or molecular modeling) using the **Message Passing Interface (MPI)**. MPI jobs exchange millions of tiny messages per second across **InfiniBand** (HDR/NDR) or **RoCE (RDMA over Converged Ethernet)** fabrics, where latency is measured in **sub-microseconds (< 1 µs)**.

```
+-----------------------------------------------------------------------------+
|                           LATENCY COMPARISON                                |
+-----------------------------------------------------------------------------+
|  Docker Virtual Bridge (NAT/iptables):  ~ 15 to 30 microseconds             |
|  Host Ethernet (TCP/IP):                ~ 10 to 20 microseconds             |
|  InfiniBand RDMA (Native Verbs):        ~ 0.6 to 1.2 microseconds           |
+-----------------------------------------------------------------------------+
```

### Why Docker's Virtual Network Fails in HPC
- **Virtual Network Bridges:** Docker routes traffic through a software bridge (`docker0`), translating packets through Linux `iptables` or `nftables` Network Address Translation (NAT). This introduces massive latency jitter and destroys MPI performance.
- **Hardware Bypass (RDMA):** High-speed InfiniBand relies on **Remote Direct Memory Access (RDMA)**, allowing one compute node to read/write memory directly from another node's RAM across the PCI bus without operating system kernel intervention. Docker's network namespaces isolate the container from the host InfiniBand Host Channel Adapters (`/dev/infiniband/uverbsX`).

---

## 4.4 The Workload Scheduler Paradox: SLURM vs. Daemons

In cloud computing, containers are long-running daemons supervised by an orchestrator like Kubernetes. In HPC, supercomputers are governed by **Batch Workload Managers** such as **SLURM**, **PBS Pro**, or **Grid Engine**.

```mermaid
sequenceDiagram
    autonumber
    actor User as Scientist / Job Script
    participant Slurm as SLURM Workload Scheduler
    participant Node as Compute Node OS
    participant Apptainer as Apptainer Runtime
    participant Docker as Docker Daemon (dockerd)

    Note over User, Slurm: HPC Batch Paradigm
    User->>Slurm: sbatch --nodes=4 --gpus=16 job.sh
    Slurm->>Node: srun launches task on allocated cores

    rect rgb(20, 40, 20)
    Note over Node, Apptainer: The Apptainer Way
    Node->>Apptainer: Execute container directly as child process
    Apptainer->>Node: Inherits SLURM cgroups, CPU masks, & UID 1005
    Node-->>Slurm: Accurate CPU/RAM accounting; instant scancel cleanup
    end

    rect rgb(50, 20, 20)
    Note over Node, Docker: The Docker Breakdown
    Node->>Docker: Calls dockerd REST API over socket
    Docker->>Docker: Daemon spawns container under dockerd cgroup
    Note over Docker: SLURM loses visibility of process tree!
    Note over Docker: Memory limits bypassed; scancel fails to kill container!
    end
```

### The SLURM Architectural Conflict
When a job is launched under SLURM:
1. **Process Tracking & Cgroups:** SLURM creates a dedicated Linux cgroup hierarchy to track the CPU time, memory limits, and process IDs of that specific job.
2. **Accounting:** If the job exceeds its requested memory (e.g., 64 GB), SLURM's cgroup terminates the job to protect the node.
3. **Cancellation (`scancel`):** When a user or administrator cancels a job, SLURM sends `SIGKILL` to all processes in that cgroup tree.

If Docker is used:
- The command line client merely sends an HTTP request to `dockerd`.
- `dockerd` (running as a system-wide root service) spawns the container under the *system daemon's* cgroup hierarchy, not the SLURM job's cgroup hierarchy.
- **Result:** SLURM cannot measure the container's memory consumption, cannot enforce CPU affinity cores, and when the SLURM job ends, the container continues running orphaned on the node!

---

## 4.5 Summary Comparison: Cloud vs. HPC Container Models

The irreconcilable differences between the enterprise cloud container model and the HPC supercomputing container model are summarized below:

| Feature / Requirement | Enterprise Cloud (Docker Model) | Scientific HPC (Apptainer / Singularity Model) |
| :--- | :--- | :--- |
| **Primary Goal** | Isolation of microservices | Performance and reproducibility of scientific codes |
| **Execution User** | Typically `root` (UID 0) inside container | Strictly unprivileged host user (`UID = host UID`) |
| **Privilege Escalation** | Requires root daemon (`dockerd`) | Rootless; no background daemons permitted |
| **File Access Model** | Copy-on-Write overlays; private disks | Direct native read/write to Lustre, GPFS, NFS |
| **Storage Artifact** | Multi-layered directory tree in `/var/lib` | Single, immutable executable file (`.sif`) |
| **Networking** | Virtual software bridge (`veth`), private IPs | Direct host network namespace; zero-latency RDMA |
| **Hardware Coupling** | Virtualized abstractions | Native passthrough: NVIDIA GPUs, ROCm, InfiniBand |
| **Job Scheduling** | Long-running services (Kubernetes) | Ephemeral batch jobs (SLURM, PBS, LSF) |

---

## 4.6 The Resolution: The Birth of Singularity and Apptainer

By 2015, the scientific computing community faced an urgent dilemma: researchers desperately needed the dependency packaging and portability of containers, but supercomputing facilities could not compromise cluster security, filesystem integrity, and bare-metal performance.

Greg Kurtzer and a team of researchers at Lawrence Berkeley National Laboratory engineered the solution: **Singularity**. 

Instead of forcing supercomputers to adapt to cloud paradigms, Singularity redesigned the container runtime from first principles to fit the HPC ecosystem:
- **No daemons.**
- **No root execution.**
- **Single-file container images (SIF).**
- **Seamless integration with SLURM, InfiniBand, and GPUs.**

In Chapter 5, we explore the architecture of Singularity and its modern open-source successor, **Apptainer**.
