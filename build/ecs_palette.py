"""Deterministic, undithered ECS palettes in perceptual color space."""
from functools import lru_cache

import numpy as np
from PIL import Image


def oklab(rgb):
    """Convert sRGB bytes using Bjorn Ottosson's public-domain Oklab matrices.

    https://bottosson.github.io/posts/oklab/#converting-from-linear-srgb-to-oklab
    """
    linear = np.asarray(rgb, dtype=np.float64) / 255
    linear = np.where(linear <= .04045, linear / 12.92,
                      ((linear + .055) / 1.055) ** 2.4)
    lms = linear @ np.array([
        [.4122214708, .2119034982, .0883024619],
        [.5363325363, .6806995451, .2817188376],
        [.0514459929, .1073969566, .6299787005],
    ])
    return np.cbrt(lms) @ np.array([
        [.2104542553, 1.9779984951, .0259040371],
        [.7936177850, -2.4285922050, .7827717662],
        [-.0040720468, .4505937099, -.8086757660],
    ])


@lru_cache(maxsize=1)
def ecs_colors():
    rgb = np.array([(r, g, b) for r in range(0, 256, 17)
                    for g in range(0, 256, 17) for b in range(0, 256, 17)],
                   dtype=np.uint8)
    # Give hue/chroma differences more weight than plain Oklab distance. This
    # preserves accents such as purple sprites and red mouths on blue scenery.
    return rgb, oklab(rgb) * [1, 2, 2]


def color_histogram(source):
    if source.mode == 'P':
        # IFF masters are indexed. Work on their <=256 palette entries rather
        # than sorting every pixel, while combining duplicate RGB entries.
        pixels = np.frombuffer(source.tobytes(), dtype=np.uint8)
        palette = np.array(source.getpalette(), dtype=np.uint8).reshape(-1, 3)
        counts = np.bincount(pixels, minlength=len(palette))
        used = np.flatnonzero(counts)
        colors, inverse_palette = np.unique(palette[used], axis=0, return_inverse=True)
        weights = np.bincount(inverse_palette, weights=counts[used])
        lookup = np.zeros(256, dtype=np.uint16)
        lookup[used] = inverse_palette
        return colors, weights, lookup[pixels]
    pixels = np.asarray(source.convert('RGB')).reshape(-1, 3)
    colors, inverse, weights = np.unique(pixels, axis=0, return_inverse=True, return_counts=True)
    return colors, weights, inverse


def quantize_perceptual(source):
    """Fit 13 graphics slots, reserving frame, black, and gradient text, with no dithering.

    Black occupies graphics slot zero as well as locked UI slot 14 because the
    launcher clears thumbnail padding with pen zero. White occupies graphics
    slot 1; slots 13, 14, and 15 are reserved for the steady frame, black, and
    Copper text respectively. Five fixed seeds avoid poor local
    minima. Every palette update selects an actual ECS color, not a rounded
    24-bit centroid. Pixel assignment uses the same perceptual metric.
    """
    rgb4, grid = ecs_colors()
    colors, weights, inverse = color_histogram(source)
    values = oklab(colors) * [1, 2, 2]
    best = None
    for trial in range(5):
        rng = np.random.default_rng(trial)
        chosen = [0, 4095]  # Fixed black and white.
        for _ in range(11):
            distance = ((values[:, None] - grid[chosen]) ** 2).sum(axis=2).min(axis=1)
            errors = distance * weights
            if errors.max() < 1e-14:
                break
            index = int(np.argmax(errors)) if trial == 0 else int(
                rng.choice(len(colors), p=errors / errors.sum()))
            chosen.append(int(np.argmin(((grid - values[index]) ** 2).sum(axis=1))))
        for _ in range(30):
            distance = ((values[:, None] - grid[chosen]) ** 2).sum(axis=2)
            assignment = distance.argmin(axis=1)
            updated = list(chosen)
            for cluster in range(2, len(chosen)):
                mask = assignment == cluster
                if mask.any():
                    mean = np.average(values[mask], axis=0, weights=weights[mask])
                    updated[cluster] = int(np.argmin(((grid - mean) ** 2).sum(axis=1)))
            if updated == chosen:
                break
            chosen = updated
        distance = ((values[:, None] - grid[chosen]) ** 2).sum(axis=2)
        score = float((distance.min(axis=1) * weights).sum())
        if best is None or score < best[0]:
            best = score, chosen, distance.argmin(axis=1)

    _, chosen, assignment = best
    palette = rgb4[chosen].reshape(-1).tolist()
    palette += [0] * (39 - len(palette))
    palette += [0, 153, 187, 0, 0, 0, 255, 255, 255]
    lookup = np.arange(len(chosen), dtype=np.uint8)
    pixels = lookup[assignment[inverse]].tobytes()
    indexed = Image.frombytes('P', source.size, pixels)
    indexed.putpalette(palette + [0] * 720)
    return indexed
