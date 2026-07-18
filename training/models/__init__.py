from __future__ import annotations

import torch

from training.util.charset import Charset

from .crnn import CRNN

__all__ = ["CRNN", "greedy_decode"]


def greedy_decode(log_probs: torch.Tensor, charset: Charset) -> list[str]:
    indices = log_probs.argmax(dim=2).permute(1, 0).tolist()
    return [charset.decode_greedy(seq) for seq in indices]
