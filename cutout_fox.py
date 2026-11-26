#!/usr/bin/env python3
"""Create soft-alpha PNG cutouts of the fox poses from white-background plates.
Flood-fill from the border -> mask; feather edges; keep internal details.
Saves assets2/cut/fox_*.png with premultiplied-safe straight alpha.
"""
import os, numpy as np, cv2
os.makedirs("assets2/cut", exist_ok=True)

def cutout(src, dst, name):
    img = cv2.imread(src, cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    # near-white mask
    b, g, r = img[:, :, 0].astype(np.int16), img[:, :, 1].astype(np.int16), img[:, :, 2].astype(np.int16)
    whiteish = ((b > 228) & (g > 228) & (r > 228)).astype(np.uint8)
    # connected components touching the border = background
    n, lab = cv2.connectedComponents(whiteish)
    border_labels = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    bg = np.isin(lab, list(border_labels)).astype(np.uint8)
    # close small holes inside the fox (e.g. paws gaps belong to bg anyway)
    alpha = (1 - bg) * 255
    alpha = cv2.medianBlur(alpha, 5)
    # remove tiny specks
    n2, lab2, stats, _ = cv2.connectedComponentsWithStats((alpha > 20).astype(np.uint8), 8)
    keep = np.zeros_like(alpha)
    for i in range(1, n2):
        if stats[i, cv2.CC_STAT_AREA] > 400:
            keep[lab2 == i] = 255
    # components not touching previous alpha... just multiply
    alpha = np.minimum(alpha, keep)
    # feather 2px
    alpha = cv2.GaussianBlur(alpha, (5, 5), 1.2)
    # slight erode to kill white fringe
    alpha = cv2.erode(alpha, np.ones((3, 3), np.uint8))
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0.8)
    # de-fringe: pull edge colors inward slightly using premultiply trick
    a = (alpha.astype(np.float32) / 255.0)[:, :, None]
    fg = img.astype(np.float32)
    # estimate bg = pure white; unpremultiply
    out = (fg - (1 - a) * 255.0) / np.maximum(a, 1e-3)
    out = np.clip(out, 0, 255).astype(np.uint8)
    bgra = cv2.cvtColor(out, cv2.COLOR_BGR2BGRA)
    bgra[:, :, 3] = alpha
    # trim to content bbox with margin
    ys, xs = np.where(alpha > 10)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    m = 6
    y0, x0 = max(0, y0 - m), max(0, x0 - m)
    y1, x1 = min(h, y1 + m), min(w, x1 + m)
    cv2.imwrite(dst, bgra[y0:y1, x0:x1])
    print(name, "->", dst, "bbox", (x1 - x0, y1 - y0))

for n in ["fox_stand", "fox_jump", "fox_sad", "fox_sit", "fox_reach", "fox_run", "fox_shock"]:
    cutout(f"assets2/{n}.jpg", f"assets2/cut/{n}.png", n)
