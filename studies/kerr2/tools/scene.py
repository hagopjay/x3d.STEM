"""Generate scenes/kerr2.x3d: one full-screen quad with the photon-ring shader.
Components are declared (Shaders 1, Texturing 2) so the fork's Meaning witness and X_ITE agree;
textures are attached at runtime from verified bytes, so the scene carries empty placeholders.
"""
from common import ROOT, atomic_bytes

FLOATS = {"aspect": "1.6", "imageAspect": "1.6", "span": "36", "zoom": "1", "panX": "0", "panY": "0",
          "exposure": "1.2", "centerAlpha": "0", "npsi": "2048", "ndelta": "1024", "deltaMin": "0.000001", "deltaMax": "1.5"}
INTS = {"viewMode": "0", "layerMask": "15", "showCurve": "0", "samples": "4"}
TEXTURES = ["img0", "img1", "img2", "img3", "ring0", "ring1", "ring2", "ring3", "curve"]


def make() -> str:
    fields = "".join(f'<field name="{n}" type="SFFloat" accessType="inputOutput" value="{v}"/>' for n, v in FLOATS.items())
    fields += '<field name="resolution" type="SFVec2f" accessType="inputOutput" value="1600 1000"/>'
    fields += "".join(f'<field name="{n}" type="SFInt32" accessType="inputOutput" value="{v}"/>' for n, v in INTS.items())
    fields += "".join(f'<field name="{n}" type="SFNode" accessType="inputOutput"/>' for n in TEXTURES)
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<X3D profile="Immersive" version="4.0"><head>'
            '<component name="Shaders" level="1"/><component name="Texturing" level="2"/>'
            '<meta name="title" content="Kerr 2 · The Photon Ring"/>'
            '<meta name="generator" content="studies/kerr2/tools/scene.py"/></head><Scene>'
            '<WorldInfo title="Kerr 2 · The Photon Ring"/><NavigationInfo type=\'"NONE"\' headlight="false"/>'
            '<Viewpoint position="0 0 3"/><Shape><Appearance><ComposedShader DEF="RingShader" language="GLSL">'
            + fields +
            '<ShaderPart type="VERTEX" url=\'"../shaders/screen.vert"\'/>'
            '<ShaderPart type="FRAGMENT" url=\'"../shaders/kerr2.frag"\'/>'
            '</ComposedShader></Appearance>'
            '<IndexedFaceSet coordIndex="0 1 2 -1 0 2 3 -1" solid="false"><Coordinate point="-1 -1 0 1 -1 0 1 1 0 -1 1 0"/></IndexedFaceSet>'
            '</Shape></Scene></X3D>\n')


if __name__ == "__main__":
    atomic_bytes(ROOT / "scenes/kerr2.x3d", make().encode())
    print("wrote scenes/kerr2.x3d")
