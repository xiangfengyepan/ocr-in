from __future__ import annotations

import torch
from PIL import Image

from training.augmentation.transforms import IMG_HEIGHT, IMG_WIDTH, Preprocess
from training.eval.metrics import cer, wer
from training.models import CRNN, greedy_decode
from training.util.charset import Charset
from training.util.collate import ctc_collate


def test_preprocess_shape_and_range():
    img = Image.new("L", (120, 50), color=128)
    x = Preprocess(train=False)(img)
    assert x.shape == (1, IMG_HEIGHT, IMG_WIDTH)
    assert x.min() >= -1.0 and x.max() <= 1.0


def test_preprocess_train_augments_runs():
    img = Image.new("L", (120, 50), color=128)
    x = Preprocess(train=True)(img)
    assert x.shape == (1, IMG_HEIGHT, IMG_WIDTH)


def test_crnn_forward_shape():
    cs = Charset.from_texts(["abcde"])
    model = CRNN(cs.num_classes)
    x = torch.randn(2, 1, IMG_HEIGHT, IMG_WIDTH)
    out = model(x)
    assert out.shape[1] == 2
    assert out.shape[2] == cs.num_classes
    probs = out.exp().sum(dim=2)
    assert torch.allclose(probs, torch.ones_like(probs), atol=1e-4)


def test_greedy_decode_runs():
    cs = Charset.from_texts(["abc"])
    model = CRNN(cs.num_classes)
    out = model(torch.randn(3, 1, IMG_HEIGHT, IMG_WIDTH))
    decoded = greedy_decode(out, cs)
    assert len(decoded) == 3


def test_collate_shapes():
    batch = [
        (torch.zeros(1, IMG_HEIGHT, IMG_WIDTH), torch.tensor([1, 2, 3]), "abc"),
        (torch.zeros(1, IMG_HEIGHT, IMG_WIDTH), torch.tensor([4, 5]), "de"),
    ]
    images, targets, lengths, texts = ctc_collate(batch)
    assert images.shape == (2, 1, IMG_HEIGHT, IMG_WIDTH)
    assert targets.tolist() == [1, 2, 3, 4, 5]
    assert lengths.tolist() == [3, 2]
    assert texts == ["abc", "de"]


def test_metrics():
    assert cer(["abc"], ["abc"]) == 0.0
    assert wer(["a b c"], ["a b c"]) == 0.0
    assert cer(["abc"], ["abd"]) > 0.0
