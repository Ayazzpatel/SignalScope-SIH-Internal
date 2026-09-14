from __future__ import annotations

import timm
import torch
from torch import nn


class SignalScopeDetector(nn.Module):
    def __init__(self, model_name: str = "convnext_tiny", pretrained: bool = True):
        super().__init__()
        self.backbone = timm.create_model(
            model_name,
            pretrained=pretrained,
            num_classes=0,
            global_pool="avg",
        )
        features = self.backbone.num_features
        self.head = nn.Sequential(
            nn.LayerNorm(features),
            nn.Dropout(0.25),
            nn.Linear(features, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.backbone(x)
        return self.head(features).squeeze(1)


def build_model(pretrained: bool = True) -> SignalScopeDetector:
    return SignalScopeDetector(pretrained=pretrained)

