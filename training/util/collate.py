from __future__ import annotations

from collections.abc import Sequence

import torch


def ctc_collate(
    batch: Sequence[tuple[torch.Tensor, torch.Tensor, str]],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, list[str]]:
    images = torch.stack([item[0] for item in batch], dim=0)
    targets = torch.cat([item[1] for item in batch], dim=0)
    target_lengths = torch.tensor([len(item[1]) for item in batch], dtype=torch.long)
    texts = [item[2] for item in batch]
    return images, targets, target_lengths, texts
