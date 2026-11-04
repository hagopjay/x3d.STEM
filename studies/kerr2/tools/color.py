"""Blackbody colour bound to the frequency shift g.

A blackbody of temperature T seen with frequency shift g is a blackbody of temperature gT (the
invariant I_nu / nu^3), so a pixel's colour follows from (g, T(r)) alone. Colour matching uses the
official CIE 1931 2-degree table (sources/CIE_xyz_1931_2deg.csv, DOI 10.25039/CIE.DS.xvudnb9b,
CC BY-SA 4.0, sha256 checked against the CIE's published checksum). The first run used the analytic
multi-lobe fit (Wyman, Sloan & Shirley 2013); its red-tail error failed the declared chromaticity gate
(0.0036 > 0.003, evidence/history/), which is why the table replaced it.
The witness compares the resulting Planckian chromaticities with an independent published fit to the
Planckian locus (Kang et al. 2002), so the check does not reuse the same assumptions (Loom law 25).
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import numpy as np

H, C, KB = 6.62607015e-34, 2.99792458e8, 1.380649e-23
CIE_CSV = Path(__file__).resolve().parents[1] / "sources/CIE_xyz_1931_2deg.csv"
CIE_SHA256 = "fa663e3535a7e0763a745993a1f0a192eb0275ac46ad2d1befd7626841e713c1"   # CIE's published checksum
_raw = CIE_CSV.read_bytes()
if hashlib.sha256(_raw).hexdigest() != CIE_SHA256:
    raise SystemExit("CIE colour-matching table does not match its published sha256")
_rows = np.array([[float(v) for v in r] for r in csv.reader(_raw.decode().splitlines())])
LAMBDA = _rows[:, 0]            # 360..830 nm, 1 nm
CMF_TABLE = _rows[:, 1:4]       # x-bar, y-bar, z-bar
ILLUMINANT_A_XY = (0.44757, 0.40745)   # CIE standard illuminant A: a 2856 K blackbody (ISO/CIE 11664-2)

XYZ_TO_SRGB = np.array([[3.2404542, -1.5371385, -0.4985314],
                        [-0.9692660, 1.8760108, 0.0415560],
                        [0.0556434, -0.2040259, 1.0572252]])


def _g(x, mu, s1, s2):
    s = np.where(x < mu, s1, s2)
    return np.exp(-0.5 * ((x - mu) / s) ** 2)


def cmf(lam=LAMBDA):
    """CIE 1931 x-bar, y-bar, z-bar from the official table (1 nm)."""
    if lam is LAMBDA:
        return CMF_TABLE
    return np.stack([np.interp(lam, LAMBDA, CMF_TABLE[:, k]) for k in range(3)], -1)


def cmf_fit(lam=LAMBDA):
    """The first run's analytic fit (Wyman, Sloan & Shirley 2013), kept for comparison only."""
    x = 1.056 * _g(lam, 599.8, 37.9, 31.0) + 0.362 * _g(lam, 442.0, 16.0, 26.7) - 0.065 * _g(lam, 501.1, 20.4, 26.2)
    y = 0.821 * _g(lam, 568.8, 46.9, 40.5) + 0.286 * _g(lam, 530.9, 16.3, 31.1)
    z = 1.217 * _g(lam, 437.0, 11.8, 36.0) + 0.681 * _g(lam, 459.0, 26.0, 13.8)
    return np.stack([x, y, z], -1)


def planck(lam_nm, T):
    lam = lam_nm * 1e-9
    with np.errstate(over="ignore"):
        return (2 * H * C ** 2 / lam ** 5) / np.expm1(H * C / (lam * KB * T))


def blackbody_xyz(T: np.ndarray) -> np.ndarray:
    """Absolute (unnormalised) XYZ of a blackbody at temperature T, by direct spectral integration."""
    T = np.atleast_1d(np.asarray(T, float))
    spec = planck(LAMBDA[None, :], T[:, None])  # (n, wavelengths)
    return spec @ cmf() * 1e-9


def chromaticity(T):
    xyz = blackbody_xyz(T)
    s = xyz.sum(-1)
    return xyz[:, 0] / s, xyz[:, 1] / s


def kang2002(T):
    """Independent cubic-spline fit to the Planckian locus, 1667 K to 25000 K (Kang et al. 2002)."""
    T = np.asarray(T, float)
    x = np.where(T <= 4000,
                 -0.2661239e9 / T ** 3 - 0.2343589e6 / T ** 2 + 0.8776956e3 / T + 0.179910,
                 -3.0258469e9 / T ** 3 + 2.1070379e6 / T ** 2 + 0.2226347e3 / T + 0.240390)
    y = np.where(T <= 2222, -1.1063814 * x ** 3 - 1.34811020 * x ** 2 + 2.18555832 * x - 0.20219683,
                 np.where(T <= 4000, -0.9549476 * x ** 3 - 1.37418593 * x ** 2 + 2.09137015 * x - 0.16748867,
                          3.0817580 * x ** 3 - 5.87338670 * x ** 2 + 3.75112997 * x - 0.37001483))
    return x, y


def illuminant_a_witness():
    x, y = chromaticity([2856.0])
    return float(np.hypot(x[0] - ILLUMINANT_A_XY[0], y[0] - ILLUMINANT_A_XY[1]))


def chromaticity_witness():
    T = np.array([2000, 2856, 3500, 4500, 5500, 6500, 8000, 10000, 15000, 20000.0])
    x, y = chromaticity(T)
    kx, ky = kang2002(T)
    err = np.hypot(x - kx, y - ky)
    return float(err.max()), {int(t): [round(float(a), 5), round(float(b), 5)] for t, a, b in zip(T, x, y)}


class Table:
    """Lookup from observed temperature to linear sRGB (D65 primaries), with physical T^4 scaling kept."""

    def __init__(self, t_min=300.0, t_max=60000.0, n=4096):
        self.logT = np.linspace(np.log(t_min), np.log(t_max), n)
        xyz = blackbody_xyz(np.exp(self.logT))
        self.rgb = xyz @ XYZ_TO_SRGB.T
        self.t_min, self.t_max = t_min, t_max

    def __call__(self, T: np.ndarray) -> tuple[np.ndarray, int]:
        """Linear sRGB for temperatures T (any shape); returns (rgb, count of out-of-gamut negatives clamped)."""
        T = np.asarray(T, float)
        lt = np.log(np.clip(T, self.t_min, self.t_max))
        rgb = np.stack([np.interp(lt, self.logT, self.rgb[:, k]) for k in range(3)], -1)
        rgb[T <= 0] = 0.0
        negatives = int(np.count_nonzero(rgb < 0))
        return np.clip(rgb, 0, None), negatives


if __name__ == "__main__":
    err, xy = chromaticity_witness()
    print("max chromaticity distance to Kang et al. 2002:", err)
    print("Illuminant A distance to the CIE published value:", illuminant_a_witness())
    print(xy)
