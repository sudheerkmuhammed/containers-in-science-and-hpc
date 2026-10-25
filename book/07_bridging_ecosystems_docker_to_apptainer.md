# Chapter 7: Bridging Ecosystems
## Converting Docker Images to Apptainer SIF and CI/CD Automation

*Author: Sudheer K. Mohammed*

---

![Chapter 7 Bridging Ecosystems](../images/chapter_07_docker_to_sif.jpg)

### Chapter Overview
In modern computational science and engineering organizations, software teams rarely develop directly on the supercomputer. Data scientists, machine learning engineers, and software developers build, prototype, and test their code on local workstations (macOS, Windows with WSL2, or Linux) where Docker is the ubiquitous standard.

However, when this software is deployed to production clusters, national supercomputers, or private clouds, it must run inside **Apptainer / Singularity SIF containers**.

Bridging these two ecosystems seamlessly—without requiring developers to maintain duplicative Dockerfiles and Apptainer definition files—is the golden standard of modern MLOps and scientific DevOps.

In this chapter, we explore:
1. Converting Docker Hub, Quay, and GitHub Container Registry (GHCR) images directly into SIF files.
2. Converting local Docker daemon images (`docker-daemon:`) and tarball exports (`docker-archive:`) without touching a public registry.
3. The translation mechanics: How Docker `ENTRYPOINT`, `CMD`, `ENV`, and `WORKDIR` map to Apptainer.
4. Traps and gotchas: File permissions, user masking, and hardcoded `/root` paths.
5. Building automated CI/CD pipelines in GitHub Actions to build, test, and push SIF images using OCI Artifacts (ORAS).

---

## 7.1 Direct Ingestion: Pulling Docker Registries into SIF

Apptainer has native, built-in comprehension of the Open Container Initiative (OCI) and Docker distribution protocols. You can pull any public or private Docker image directly into an immutable SIF file in a single step:

```bash
# Pull an official Docker Hub image into a local SIF
$ apptainer pull docker://python:3.11-slim

# The resulting file is an immutable SIF named python_3.11-slim.sif
$ ls -lh python_3.11-slim.sif
-rwxr-xr-x 1 sudheer sudheer 58M Oct 25 12:00 python_3.11-slim.sif

# Execute it immediately on the HPC cluster!
$ apptainer exec python_3.11-slim.sif python3 -c "print('Direct Docker-to-SIF execution!')"
```

### Pulling from NVIDIA NGC, Quay, and GitHub Container Registry (GHCR)
Apptainer supports arbitrary OCI registries:

```bash
# NVIDIA GPU Cloud (NGC) Optimized PyTorch
$ apptainer pull pytorch_ngc.sif docker://nvcr.io/nvidia/pytorch:24.01-py3

# Quay.io Bioinformatics Container (Biocontainers)
$ apptainer pull samtools.sif docker://quay.io/biocontainers/samtools:1.19.2--h50ea8bc_1

# GitHub Container Registry (GHCR) with custom output name
$ apptainer pull custom_sim.sif docker://ghcr.io/my-org/simulation-core:v1.4.0
```

### Authenticating to Private Docker Registries
If the target Docker image is stored in a private corporate or institutional registry, authenticate using environment variables or the CLI:

```bash
# Export standard OCI authentication tokens
export APPTAINER_DOCKER_USERNAME="sudheer-mohammed"
export APPTAINER_DOCKER_PASSWORD="ghp_SuperSecretPersonalAccessToken"

# Pull from private registry
apptainer pull private_app.sif docker://ghcr.io/my-org/private-analysis:latest
```

---

## 7.2 Local Conversions: Converting Without a Remote Registry

Frequently, you build an image locally using `docker build` and need to convert it to a SIF container without pushing proprietary code to an external registry. Apptainer provides two mechanisms:

### Method 1: Direct from the Docker Daemon (`docker-daemon:`)
If Docker is running on your build machine, Apptainer can read directly from the local Docker UNIX socket (`/var/run/docker.sock`):

```bash
# Step 1: Build locally in Docker
$ docker build -t local_algo:dev .

# Step 2: Convert directly from local Docker daemon into SIF
$ apptainer build local_algo.sif docker-daemon:local_algo:dev
```

### Method 2: Offline Tarball Export (`docker-archive:`)
If you are working across an air-gapped network boundary (e.g., building on a secure workstation and transferring to a classified cluster):

```bash
# Step 1: Export the Docker image as an OCI/Docker tar archive
$ docker save local_algo:dev -o local_algo.tar

# Step 2: Transfer local_algo.tar to the cluster via rsync / scp
$ scp local_algo.tar user@hpc-login.cluster.edu:/scratch/user/

# Step 3: On the cluster, convert the tarball to SIF without network access!
$ apptainer build local_algo.sif docker-archive:/scratch/user/local_algo.tar
```

---

## 7.3 Translation Mechanics: Docker vs. Apptainer Semantics

When Apptainer translates a Docker image into a SIF container, it maps OCI metadata constructs into Apptainer runtime configurations:

```
+-----------------------------------+---------------------------------------------+
|        DOCKER OCI DIRECTIVE       |          APPTAINER TRANSLATION              |
+-----------------------------------+---------------------------------------------+
|  ENTRYPOINT ["/bin/app"]          |  Becomes the default %runscript             |
|  CMD ["--default-arg"]            |  Appended to %runscript if no args supplied |
|  ENV KEY=VALUE                    |  Written to /.singularity.d/env/10-docker.sh|
|  WORKDIR /app                     |  Ignored! Apptainer stays in host $PWD      |
|  USER 10001                       |  Ignored! Apptainer enforces host UID/GID   |
|  VOLUME /data                     |  Ignored! Use -B /host/data:/data instead   |
|  EXPOSE 8080                      |  Informational only (host network shared)   |
+-----------------------------------+---------------------------------------------+
```

### Critical Gotchas to Avoid

#### Gotcha 1: The `WORKDIR` Fallacy
In Docker, `WORKDIR /app` causes commands to execute in `/app`. In Apptainer, **the container starts in whatever directory the user was standing in on the host when they typed the command**. If your application relies on relative paths (e.g., `open("config.json")`), it will search the host directory and fail.
- **Fix:** In your application code, resolve paths relative to the script directory (`os.path.dirname(__file__)`), or set `apptainer exec --pwd /app ...`.

#### Gotcha 2: The Hardcoded `/root` Path
Many quick-and-dirty Dockerfiles store files in `/root` (e.g., `COPY my_script.py /root/`). When run in Apptainer, the host user does not have permission to read `/root` (permissions `0700`). The container crashes with `Permission Denied`.
- **Fix:** Always copy code into neutral, world-readable directories like `/opt/app` or `/usr/local/bin` and ensure `chmod 755` permissions.

---

## 7.4 Automated CI/CD: Building SIFs in GitHub Actions

Maintaining automated continuous integration pipelines that build and validate SIF containers on every git push ensures scientific reproducibility.

Below is a complete, production-ready GitHub Actions workflow that:
1. Builds a Docker image on the runner.
2. Converts the Docker image into an Apptainer SIF using rootless tools.
3. Tests the SIF.
4. Publishes the SIF container back to GitHub Packages as an **OCI Artifact** using ORAS.

```yaml
name: Build and Publish Apptainer SIF

on:
  push:
    branches: [ "main" ]
    tags: [ "v*" ]
  pull_request:
    branches: [ "main" ]

jobs:
  build-and-deploy-sif:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build local Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: simulation-core:${{ github.sha }}

      - name: Install Apptainer
        uses: eWaterCycle/setup-apptainer@v2
        with:
          apptainer-version: 1.2.5

      - name: Convert Docker Image to Apptainer SIF
        run: |
          mkdir -p dist
          apptainer build dist/simulation_core.sif docker-daemon:simulation-core:${{ github.sha }}

      - name: Validate SIF Execution
        run: |
          apptainer run-help dist/simulation_core.sif || true
          apptainer exec dist/simulation_core.sif python3 -c "print('CI SIF Smoke Test PASSED!')"

      - name: Log in to GitHub Container Registry (GHCR)
        if: startsWith(github.ref, 'refs/tags/v')
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Push SIF to GHCR as OCI Artifact (ORAS)
        if: startsWith(github.ref, 'refs/tags/v')
        run: |
          # Push the SIF file directly to GHCR as an OCI Artifact
          apptainer push dist/simulation_core.sif oras://ghcr.io/${{ github.repository }}/simulation-sif:${{ github.ref_name }}
```

---

## 7.5 Pulling OCI Artifacts Directly on the HPC Cluster

Once your CI/CD pipeline pushes the SIF as an OCI artifact using `oras://`, any researcher on the supercomputer can pull the precompiled binary directly:

```bash
# Pull the prebuilt SIF artifact from GitHub Container Registry
$ apptainer pull oras://ghcr.io/my-org/simulation-sif:v1.0.0

# Execute on the compute nodes without compiling anything!
$ srun apptainer exec simulation-sif_v1.0.0.sif /usr/local/bin/simulation_engine
```

---

## 7.6 Summary & Key Takeaways

1. **Write Once, Run Everywhere:** Developers can build with standard Docker tools locally and deploy to HPC by pulling directly into SIF (`apptainer pull docker://...`).
2. **Offline Interoperability:** Use `docker-daemon:` or `docker-archive:` to convert images directly on local machines without touching public registries.
3. **Semantic Mapping:** Apptainer automatically converts Docker `ENTRYPOINT` to `%runscript` and translates `ENV` variables into standard initialization files.
4. **Automated MLOps:** Modern CI/CD pipelines can build SIF artifacts in GitHub Actions and distribute them worldwide using the `oras://` OCI artifact protocol.
