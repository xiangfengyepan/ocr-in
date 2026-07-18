from __future__ import annotations

import albumentations as A
import numpy as np
import torch
from PIL import Image

IMG_HEIGHT = 32
IMG_WIDTH = 256


def _augmentation() -> A.Compose:
    return A.Compose(
        [
            A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
            A.OneOf(
                [
                    A.GaussianBlur(blur_limit=(3, 5), p=1.0),
                    A.MotionBlur(blur_limit=5, p=1.0),
                ],
                p=0.3,
            ),
            A.GaussNoise(std_range=(0.02, 0.1), p=0.3),
            A.OneOf(
                [
                    A.ElasticTransform(alpha=20, sigma=5, p=1.0),
                    A.GridDistortion(num_steps=5, distort_limit=0.2, p=1.0),
                ],
                p=0.3,
            ),
            A.Morphological(scale=(2, 3), operation="dilation", p=0.2),
            A.Morphological(scale=(2, 3), operation="erosion", p=0.2),
            A.ImageCompression(quality_range=(50, 90), p=0.2),
        ]
    )


class Preprocess:
    def __init__(
        self, height: int = IMG_HEIGHT, width: int = IMG_WIDTH, train: bool = False
    ) -> None:
        self.height = height
        self.width = width
        self.train = train
        self.aug = _augmentation() if train else None

    def __call__(self, image: Image.Image) -> torch.Tensor:
        arr = np.array(image.convert("L"), dtype=np.uint8)
        arr = self._resize_pad(arr)
        if self.aug is not None:
            arr = self.aug(image=arr)["image"]
        x = torch.from_numpy(arr).float().unsqueeze(0) / 255.0
        return (x - 0.5) / 0.5

    def _resize_pad(self, arr: np.ndarray) -> np.ndarray:
        h0, w0 = arr.shape[:2]
        scale = self.height / max(h0, 1)
        new_w = max(1, min(self.width, round(w0 * scale)))
        resized = np.array(
            Image.fromarray(arr).resize((new_w, self.height), Image.BILINEAR), dtype=np.uint8
        )
        canvas = np.full((self.height, self.width), 255, dtype=np.uint8)
        canvas[:, :new_w] = resized
        return canvas
