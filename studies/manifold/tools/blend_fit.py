"""Fits the overlay curve used by every light layer of the scene (shaders/common.glsl overlay()).

The original adds its light layers (ribbons, sprites, filaments, motes, veil) to the surface in linear HDR and
tone-maps the sum: shown = T(S + F). X_ITE's framebuffer is 8-bit, so the scene tone-maps each fragment and
the overlays must be blended in display space, where only d = T(S) is known (blend factor ONE_MINUS_DST_COLOR:
shown = d + (1 - d) g(F)). This finds g, linear near zero and saturating, that best matches T(S + F) - T(S)
for surface values weighted around d = 0.3 (most of the frame). Grade L: a fitted model, with its error below.
Run 6 Nov: g(F) = 6.1615 F / (1 + 4.9597 F)^1.0704; mean |error| 0.0096 against 0.0258 for screen-blending
T(F); 0.0072 against 0.0331 for faint light (F < 0.1); a 2:1 colour ratio kept as 1.90 (true 1.92, T(F): 1.62).
"""
import numpy as np
from scipy.optimize import least_squares


def T(x):
    x = np.maximum(x * 1.32, 0)
    return np.clip((x * (2.51 * x + .03)) / (x * (2.43 * x + .59) + .14), 0, 1) ** (1 / 2.2)


xs = np.linspace(0, 20, 200001); ts = T(xs)
d = np.linspace(.05, .75, 71)
F = np.concatenate([np.linspace(0, .05, 26), np.linspace(.05, 1.5, 120)])
D, FF = np.meshgrid(d, F)
target = T(np.interp(D, ts, xs) + FF) - D
w = np.exp(-((D - .3) / .2) ** 2)
g = lambda p, f: np.clip(p[0] * f / (1 + p[1] * f) ** p[2], 0, 1)
p = least_squares(lambda p: (w * ((1 - D) * g(p, FF) - target)).ravel(), [2, 1, 1], bounds=([0, 0, 0], [20, 50, 3])).x
e_fit, e_scr = (1 - D) * g(p, FF) - target, (1 - D) * T(FF) - target
print("g(F) = %.4f F / (1 + %.4f F)^%.4f" % tuple(p))
print("mean |error|: fitted %.4f, screen-T %.4f" % (np.average(np.abs(e_fit), weights=w), np.average(np.abs(e_scr), weights=w)))
