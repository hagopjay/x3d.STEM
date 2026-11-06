"""Writes scenes/manifold.x3d, one portable X3D 4.0 file (Loom law 1: generator, not file).

  python3 -E -s tools/scene.py          (after tools/manifold.py)

What the file holds, and why it is X3D rather than a canvas:
  * the surface as an ElevationGrid of 513 x 513 rest heights (Reverie at t = 3.7, from the builder's
    verified payload): any X3D browser shows the manifold at rest, with a plain Material, if it runs no shader;
  * seven ComposedShaders (GLSL ES 3.00, inlined as data: URLs) that re-evaluate the live metric, the fold
    and the ripples every frame, so X_ITE draws the field moving;
  * the 900 particle seeds and the five filament ribbons baked as FloatVertexAttributes, the seven source
    sprites, the geodesic ribbon set (streamed by the page) and the TimeSensor that clocks the page;
  * MetadataSets that state the mathematics, the grades and the hashes of the evidence behind them.
The light layers blend with standard alpha (common.glsl lightOut approximates the screen blend), so the file
needs no blending extension and draws the same in any X3D browser that runs its shaders.
"""
from __future__ import annotations

import json
import re
import sys
import zlib
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parents[1] / "lib"))
import numpy as np                                             # noqa: E402
from stemkit.core import atomic_bytes, need, sha               # noqa: E402

EXTENT, REST_N, VEIL_N = 11.2, 513, 97
UNIFORM = re.compile(r"uniform\s+(float|vec2|vec3|vec4|int)\s+([^;]+);")
DEFAULTS = {"uTime": "3.7", "uEnergy": ".7", "uBreath": ".65", "uFold": ".65", "uGlow": ".65", "uMetal": ".7",
            "uContours": "1", "uMicro": "1", "uCurrents": "1", "uA": ".11 .59 .68", "uB": ".48 .24 .72", "uC": "1 .65 .38",
            "uEye": "0 16.33 14.97", "uResolution": "1280 720", "uPixelRatio": "1", "uSpriteScale": "1", "uAOStrength": "1",
            "uVeil": "1", "uRibbonWidth": ".9", "uRibbonGain": "1", "uLineScale": "1"}
ARRAYS = {"uSources": 7, "uShape": 7, "uPulse": 8, "uAnchors": 7}


def shader_parts(name: str) -> tuple[str, str, list[tuple[str, str]]]:
    common = (ROOT / "shaders/common.glsl").read_text()
    src = (ROOT / f"shaders/{name}.glsl").read_text()
    vert, frag = src.split("//// FRAGMENT")
    vert = vert.replace("//// VERTEX", "")
    fields, seen = [], set()
    for text in (common, vert, frag):
        for typ, names in UNIFORM.findall(text):
            for n in names.split(","):
                n = n.strip()
                base = n.split("[")[0]
                if base.startswith("x3d_") or base in seen:
                    continue
                seen.add(base)
                if "[" in n:
                    count = ARRAYS[base]
                    need(typ == "vec4", "ARRAY_TYPE", n)
                    fields.append((base, f"MFVec4f", " ".join(["0 0 -100 0"] * count) if base == "uPulse" else " ".join(["0 0 0 1"] * count)))
                else:
                    x3d = {"float": "SFFloat", "vec2": "SFVec2f", "vec3": "SFVec3f", "vec4": "SFVec4f", "int": "SFInt32"}[typ]
                    fields.append((base, x3d, DEFAULTS.get(base, "0")))
    head = "#version 300 es\n" + common
    return head + vert, head + frag, fields


def shader(defname: str, name: str) -> str:
    vert, frag, fields = shader_parts(name)
    need("]]>" not in vert + frag, "CDATA_BREAK", name)
    out = [f"<ComposedShader DEF='{defname}' language='GLSL'>"]
    for n, t, v in fields:
        out.append(f"  <field name='{n}' type='{t}' accessType='inputOutput' value='{v}'/>")
    out.append(f"  <ShaderPart type='VERTEX'><![CDATA[data:x-shader/x-vertex,{vert}]]></ShaderPart>")
    out.append(f"  <ShaderPart type='FRAGMENT'><![CDATA[data:x-shader/x-fragment,{frag}]]></ShaderPart>")
    out.append("</ComposedShader>")
    return "\n".join(out)


def nums(a, fmt="{:.4f}") -> str:
    return " ".join(fmt.format(v).rstrip("0").rstrip(".") if "." in fmt.format(v) else fmt.format(v) for v in np.ravel(a))


def look(eye, target) -> str:
    """position and orientation of an X3D Viewpoint looking from eye to target with no roll: the original's
    lookAt basis (x = normalize(z.z, 0, -z.x)), as an axis-angle rotation of the default -Z view."""
    e, t = np.asarray(eye, float), np.asarray(target, float)
    z = (e - t) / np.linalg.norm(e - t)
    x = np.array([z[2], 0, -z[0]]); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.c_[x, y, z]
    ang = np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))
    if ang < 1e-9:
        axis = np.array([0, 1, 0.])
    else:
        axis = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / (2 * np.sin(ang))
    return f"position='{e[0]:.4f} {e[1]:.4f} {e[2]:.4f}' orientation='{axis[0]:.6f} {axis[1]:.6f} {axis[2]:.6f} {ang:.6f}'"


def orbit(az, el, dist, target=(0, -1.5, 0)) -> str:
    t = np.asarray(target, float)
    return look(t + dist * np.array([np.cos(el) * np.sin(az), np.sin(el), np.cos(el) * np.cos(az)]), t)


def main() -> None:
    case = json.loads((ROOT / "cases/rest/case.json").read_text())
    need(all(w["pass"] for w in case["witnesses"]), "CASE_RED")
    fr = case["frames"][0]
    data = (ROOT / fr["file"]).read_bytes()
    need(sha(data) == fr["sha256"], "PAYLOAD_HASH", fr["file"])
    raw = zlib.decompress(data)
    need(sha(raw) == fr["decoded_sha256"], "PAYLOAD_DECODED_HASH", fr["file"])
    rest = np.frombuffer(raw, "<f4").astype(np.float64).reshape(REST_N, REST_N)       # row j = z, column i = x
    heights = nums(rest)                       # ElevationGrid: height[i + j * xDimension], i along x, j along z
    back = np.array([float(v) for v in heights.split()]).reshape(REST_N, REST_N)
    quant = float(np.max(np.abs(back - rest)))
    need(quant <= 5e-5, "HEIGHT_QUANTIZATION", f"{quant:.2e}")

    seeds = np.array(json.loads((ROOT / "cases/rest/particles.json").read_text())["seeds"])
    need(sha((ROOT / "cases/rest/particles.json").read_bytes()) == case["particles_sha256"], "PARTICLES_HASH")
    fib = []
    for a, b in [[0, 1], [1, 4], [2, 5], [3, 6], [4, 6]]:          # the original's filament pairs, 110 steps each
        for j in range(110):
            t, u = j / 110, (j + 1) / 110
            fib += [a, b, t, -1, a, b, t, 1, a, b, u, -1, a, b, t, 1, a, b, u, 1, a, b, u, -1]
    fib = np.array(fib, float).reshape(-1, 4)
    sp = 2 * EXTENT / (REST_N - 1)
    vsp = 2 * EXTENT / (VEIL_N - 1)
    witnesses = "; ".join(f"{w['id']} {w['observed']:.2e} (limit {w['limit']:.0e})" for w in case["witnesses"])

    x3d = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">
<X3D profile='Immersive' version='4.0' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>
<head>
 <component name='Shaders' level='1'/>
 <meta name='title' content='Manifold of Emotion'/>
 <meta name='description' content='An emotional field as a Riemannian surface: the conformal metric g = lambda^2 (dx^2 + dz^2), lambda = 1 + seven breathing anisotropic Gaussians, drawn as the height -1.72 ln(lambda) with a rotating four-dimensional fold, its Gaussian curvature in colour and its geodesics as light. Recreated in X3D from Manifold-of-Emotion.html (sha256 c088f86d...).'/>
 <meta name='generator' content='tools/scene.py (x3d.STEM studies/manifold), from cases/rest/case.json'/>
 <meta name='reference' content='reference/Manifold-of-Emotion.html'/>
 <meta name='rest-heights-sha256' content='{fr["decoded_sha256"]}'/>
</head>
<Scene>
<WorldInfo title='Manifold of Emotion' info='"Every surface, ribbon and sprite here is driven by one metric. The labels are illustrative names, not measurements of anyone&apos;s feelings."'>
 <MetadataSet name='riemannian-structure' containerField='metadata'>
  <MetadataString name='metric' value='"g = lambda(x,z)^2 (dx^2 + dz^2) on the square [-11.2, 11.2]^2"' containerField='value'/>
  <MetadataString name='conformal-factor' value='"lambda = 1 + sum over 7 sources of a_i exp(-1/2 d^T A_i d), A_i rotated, anisotropic, breathing in time"' containerField='value'/>
  <MetadataString name='gaussian-curvature' value='"K = -Laplacian(ln lambda) / lambda^2 (checked against the general Brioschi formula)"' containerField='value'/>
  <MetadataString name='geodesics' value='"unit Euclidean tangent T: dT/ds = grad ln lambda - (grad ln lambda . T) T (checked against the affine geodesic equation)"' containerField='value'/>
  <MetadataString name='display' value='"height -1.72 ln(lambda) + fold + ripples: a picture of the metric, not an isometric embedding; its own geodesics stray up to {next(m["value"] for m in case["metrics"] if m["id"] == "drawn_surface_geodesic_separation")} units from those of g within 20"' containerField='value'/>
  <MetadataString name='witnesses' value={quoteattr(chr(34) + witnesses + chr(34))} containerField='value'/>
  <MetadataString name='grades' value='"metric, curvature, geodesics: C (measured by the builder); affect labels: Authored (illustrative names)"' containerField='value'/>
 </MetadataSet>
</WorldInfo>
<NavigationInfo DEF='Nav' type='"NONE"' headlight='false' visibilityLimit='130' avatarSize='0.2 1.6 0.75' transitionType='"TELEPORT"'/>
<Viewpoint DEF='Cam' description='the page camera (the original&apos;s orbit: azimuth .62, elevation .69, distance 27.6)' {orbit(.62, .69, 27.6)} fieldOfView='0.733038'/>
<Viewpoint DEF='Overview' description='from above' {orbit(.0, 1.45, 30)} fieldOfView='0.733038'/>
<Viewpoint DEF='Horizon' description='low over the basins' {orbit(-.9, .2, 22)} fieldOfView='0.733038'/>
<TimeSensor DEF='Clock' loop='true' cycleInterval='1'/>
<Shape DEF='Sky' bboxSize='1000 1000 1000'>
 <Appearance>
{shader('SkyShader', 'background')}
 </Appearance>
 <TriangleSet><Coordinate point='-1 -1 0 3 -1 0 -1 3 0'/></TriangleSet>
</Shape>
<Transform translation='-11.2 0 -11.2'>
 <Shape DEF='Surface' bboxSize='22.4 16 22.4' bboxCenter='11.2 -2 11.2'>
  <Appearance DEF='SurfaceLook'>
   <Material diffuseColor='.11 .30 .38' specularColor='.6 .7 .8' shininess='.55'/>
{shader('SurfaceShader', 'surface')}
  </Appearance>
  <ElevationGrid DEF='RestHeights' xDimension='{REST_N}' zDimension='{REST_N}' xSpacing='{sp:.6f}' zSpacing='{sp:.6f}' solid='false' creaseAngle='3.14' height='{heights}'/>
 </Shape>
 <Shape DEF='Veil' bboxSize='22.4 16 22.4' bboxCenter='11.2 -2 11.2'>
  <Appearance DEF='VeilLook' alphaMode='BLEND'>
{shader('VeilShader', 'veil')}
  </Appearance>
  <ElevationGrid xDimension='{VEIL_N}' zDimension='{VEIL_N}' xSpacing='{vsp:.6f}' zSpacing='{vsp:.6f}' solid='false'/>
 </Shape>
</Transform>
<Shape DEF='Flows' bboxSize='22.4 16 22.4'>
 <Appearance DEF='FlowLook' alphaMode='BLEND'>
{shader('FlowShader', 'flow')}
 </Appearance>
 <IndexedTriangleSet DEF='FlowGeometry' solid='false' index='0 1 2'>
  <Coordinate DEF='FlowCoord' point='0 0 0 0 0 0 0 0 0'/>
  <FloatVertexAttribute DEF='FlowPath' name='aPath' numComponents='4' value='0 0 0 0 0 0 0 0 0 0 0 0'/>
  <FloatVertexAttribute DEF='FlowRibbon' name='aRibbon' numComponents='3' value='1 0 -1 1 0 1 1 0 -1'/>
 </IndexedTriangleSet>
</Shape>
<Shape DEF='Filaments' bboxSize='22.4 20 22.4'>
 <Appearance DEF='FiberLook' alphaMode='BLEND'>
{shader('FiberShader', 'fibers')}
 </Appearance>
 <TriangleSet solid='false'>
  <Coordinate point='{nums(np.zeros((len(fib), 3)), "{:.0f}")}'/>
  <FloatVertexAttribute name='aFiber' numComponents='4' value='{nums(fib, "{:.6f}")}'/>
 </TriangleSet>
</Shape>
<Shape DEF='Sources' bboxSize='22.4 16 22.4'>
 <Appearance DEF='NodeLook' alphaMode='BLEND'>
{shader('NodeShader', 'nodes')}
 </Appearance>
 <PointSet>  <!-- the X3D 4.0 XSD gives PointSet no vertex attributes: each source's id is its coordinate's x -->
  <Coordinate point='0 0 0 1 0 0 2 0 0 3 0 0 4 0 0 5 0 0 6 0 0'/>
 </PointSet>
</Shape>
<Shape DEF='Motes' bboxSize='22.4 16 22.4'>
 <Appearance DEF='MoteLook' alphaMode='BLEND'>
{shader('MoteShader', 'particles')}
 </Appearance>
 <PointSet>  <!-- seed (x, z, r1, r2) as Coordinate (x, r1, z) and Color (r2, 0, 0): no vertex attributes in a 4.0 PointSet -->
  <Color color='{nums(np.c_[seeds[:, 3], np.zeros(len(seeds)), np.zeros(len(seeds))], "{:.7f}")}'/>
  <Coordinate point='{nums(np.c_[seeds[:, 0], seeds[:, 2], seeds[:, 1]], "{:.7f}")}'/>
 </PointSet>
</Shape>
</Scene>
</X3D>
"""
    out = ROOT / "scenes/manifold.x3d"
    atomic_bytes(out, x3d.encode("utf-8"))
    print(f"scenes/manifold.x3d  {out.stat().st_size / 1e6:.2f} MB  sha256 {sha(out.read_bytes())[:16]}  rest-height quantization {quant:.2e}")


if __name__ == "__main__":
    main()
