# 흰 배경 여백을 잘라내는 스크립트. regen_pics.ps1이 polyscope 스크린샷 후 호출한다.
#   사용법: python pics/crop_margins.py <image.png> [<image2.png> ...]
import sys

import numpy as np
from PIL import Image

PADDING = 24    # 남겨둘 여백 [px]
THRESHOLD = 8   # 배경(흰색)과의 채널당 최대 허용 오차

def crop_margins(path):
	img = Image.open(path).convert("RGB")
	arr = np.asarray(img, dtype=np.int16)
	content = (np.abs(arr - 255) > THRESHOLD).any(axis=2)
	rows = np.flatnonzero(content.any(axis=1))
	cols = np.flatnonzero(content.any(axis=0))
	if rows.size == 0 or cols.size == 0:
		print(f"skip (empty image): {path}")
		return
	top    = max(rows[0]  - PADDING, 0)
	bottom = min(rows[-1] + PADDING + 1, arr.shape[0])
	left   = max(cols[0]  - PADDING, 0)
	right  = min(cols[-1] + PADDING + 1, arr.shape[1])
	img.crop((left, top, right, bottom)).save(path)
	print(f"cropped {path}: {arr.shape[1]}x{arr.shape[0]} -> {right-left}x{bottom-top}")

if __name__ == "__main__":
	for p in sys.argv[1:]:
		crop_margins(p)
