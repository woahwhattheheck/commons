from __future__ import annotations

import torch
from torch import nn


class ResidualBlock3d(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super().__init__()
        self.body = nn.Sequential(
            nn.Conv3d(in_channels, out_channels, 3, stride=stride, padding=1, bias=False),
            nn.InstanceNorm3d(out_channels, affine=True),
            nn.SiLU(inplace=True),
            nn.Conv3d(out_channels, out_channels, 3, padding=1, bias=False),
            nn.InstanceNorm3d(out_channels, affine=True),
        )
        self.skip = nn.Identity() if stride == 1 and in_channels == out_channels else nn.Conv3d(in_channels, out_channels, 1, stride=stride, bias=False)
        self.act = nn.SiLU(inplace=True)

    def forward(self, x):
        return self.act(self.body(x) + self.skip(x))


class DaTNet3d(nn.Module):
    def __init__(self, width: int = 16, dropout: float = 0.20):
        super().__init__()
        self.stem = nn.Sequential(nn.Conv3d(1, width, 5, stride=2, padding=2, bias=False), nn.InstanceNorm3d(width, affine=True), nn.SiLU(inplace=True))
        self.blocks = nn.Sequential(
            ResidualBlock3d(width, width), ResidualBlock3d(width, width * 2, stride=2), ResidualBlock3d(width * 2, width * 2),
            ResidualBlock3d(width * 2, width * 4, stride=2), ResidualBlock3d(width * 4, width * 4),
        )
        self.head = nn.Sequential(nn.AdaptiveAvgPool3d(1), nn.Flatten(), nn.Dropout(dropout), nn.Linear(width * 4, 1))

    def forward(self, x):
        return self.head(self.blocks(self.stem(x))).squeeze(-1)
