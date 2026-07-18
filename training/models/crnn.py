from __future__ import annotations

import torch
from torch import nn


class _BiLSTM(nn.Module):
    def __init__(self, in_features: int, hidden: int, out_features: int) -> None:
        super().__init__()
        self.rnn = nn.LSTM(in_features, hidden, bidirectional=True, batch_first=False)
        self.fc = nn.Linear(hidden * 2, out_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        recurrent, _ = self.rnn(x)
        t, b, h = recurrent.shape
        return self.fc(recurrent.view(t * b, h)).view(t, b, -1)


class CRNN(nn.Module):
    def __init__(self, num_classes: int, in_channels: int = 1, hidden: int = 256) -> None:
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(in_channels, 64, 3, 1, 1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, 3, 1, 1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(128, 256, 3, 1, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, 1, 1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2), (2, 1), (0, 1)),
            nn.Conv2d(256, 512, 3, 1, 1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.Conv2d(512, 512, 3, 1, 1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2), (2, 1), (0, 1)),
            nn.Conv2d(512, 512, 2, 1, 0),
            nn.ReLU(inplace=True),
        )
        self.rnn = nn.Sequential(
            _BiLSTM(512, hidden, hidden),
            _BiLSTM(hidden, hidden, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        conv = self.cnn(x)
        b, c, h, w = conv.shape
        if h != 1:
            conv = conv.mean(dim=2, keepdim=True)
        conv = conv.squeeze(2).permute(2, 0, 1)
        logits = self.rnn(conv)
        return logits.log_softmax(2)
