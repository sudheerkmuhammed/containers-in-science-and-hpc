"""
PyTorch DistributedDataParallel (DDP) Multi-GPU Benchmark
Author: Sudheer K. Mohammed
"""

import os
import sys
import time
import torch
import torch.nn as nn
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, Dataset
from torch.utils.data.distributed import DistributedSampler

class BenchmarkDataset(Dataset):
    def __init__(self, size=20000, features=256):
        self.data = torch.randn(size, features)
        self.labels = torch.randint(0, 10, (size,))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx], self.labels[idx]

class DeepClassifier(nn.Module):
    def __init__(self, in_features=256, num_classes=10):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, 1024),
            nn.BatchNorm1d(1024),
            nn.SiLU(),
            nn.Linear(1024, 1024),
            nn.BatchNorm1d(1024),
            nn.SiLU(),
            nn.Linear(1024, num_classes)
        )

    def forward(self, x):
        return self.net(x)

def setup():
    # Read environment variables set by torchrun/SLURM
    rank = int(os.environ.get("RANK", 0))
    world_size = int(os.environ.get("WORLD_SIZE", 1))
    local_rank = int(os.environ.get("LOCAL_RANK", 0))

    if torch.cuda.is_available():
        torch.cuda.set_device(local_rank)
        backend = "nccl"
    else:
        backend = "gloo"

    dist.init_process_group(
        backend=backend,
        init_method="env://",
        world_size=world_size,
        rank=rank
    )
    return rank, world_size, local_rank

def main():
    rank, world_size, local_rank = setup()
    device = torch.device(f"cuda:{local_rank}" if torch.cuda.is_available() else "cpu")

    if rank == 0:
        print(f"--> [INIT] PyTorch DDP active across {world_size} ranks on device: {device}")

    # Build model and wrap in DDP
    model = DeepClassifier().to(device)
    if torch.cuda.is_available():
        ddp_model = DDP(model, device_ids=[local_rank])
    else:
        ddp_model = DDP(model)

    dataset = BenchmarkDataset()
    sampler = DistributedSampler(dataset, num_replicas=world_size, rank=rank, shuffle=True)
    loader = DataLoader(dataset, batch_size=128, sampler=sampler, num_workers=2, pin_memory=True)

    criterion = nn.CrossEntropyLoss().to(device)
    optimizer = torch.optim.Adam(ddp_model.parameters(), lr=1e-3)

    start_time = time.time()
    for epoch in range(2):
        sampler.set_epoch(epoch)
        total_loss = 0.0

        for inputs, targets in loader:
            inputs, targets = inputs.to(device, non_blocking=True), targets.to(device, non_blocking=True)
            optimizer.zero_grad()
            outputs = ddp_model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        if rank == 0:
            print(f"--> Epoch {epoch+1}/2 complete | Average Loss: {total_loss / len(loader):.4f}")

    dist.destroy_process_group()
    if rank == 0:
        print(f"--> [COMPLETE] Training finished in {round(time.time() - start_time, 2)} seconds.")

if __name__ == "__main__":
    main()
