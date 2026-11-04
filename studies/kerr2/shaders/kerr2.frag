#version 300 es
// Kerr 2 · The Photon Ring. Displays computed rays only: the base image (one ray per pixel centre) and,
// within 1.5 M of the analytic critical curve, the polar ring atlas (log-spaced offsets down to 1e-6 M).
// Texture row convention (X_ITE custom samplers): v = 0 is the PNG's first (top) row.
precision highp float;
precision highp int;
uniform sampler2D img0, img1, img2, img3, ring0, ring1, ring2, ring3, curve;
uniform float aspect, imageAspect, span, zoom, panX, panY, exposure, centerAlpha, npsi, ndelta, deltaMin, deltaMax;
uniform vec2 resolution;
uniform int viewMode, layerMask, showCurve, samples;
in vec2 screenUV;
out vec4 x3d_FragColor;
const float TAU = 6.28318530718;

vec3 rgbm(vec4 s) { return s.rgb * s.a * 16.0; }

float decode24(vec3 c) {
  vec3 b = floor(c * 255.0 + 0.5);
  return ((b.r * 256.0 + b.g) * 256.0 + b.b) / 16777215.0 * 16.0;
}

// rho_c(psi), sampled at psi_k = (k + 0.5) 2pi / npsi; fetched exactly and interpolated here,
// because filtering the three bytes separately would break the 24-bit code.
float rhoC(float psi) {
  float k = psi / TAU * npsi - 0.5;
  float k0 = floor(k);
  float f = k - k0;
  int i0 = int(mod(k0, npsi));
  int i1 = int(mod(k0 + 1.0, npsi));
  return mix(decode24(texelFetch(curve, ivec2(i0, 0), 0).rgb), decode24(texelFetch(curve, ivec2(i1, 0), 0).rgb), f);
}

vec3 imageLayers(vec2 t) {
  vec3 c = vec3(0.0);
  if ((layerMask & 1) != 0) c += rgbm(texture(img0, t));
  if ((layerMask & 2) != 0) c += rgbm(texture(img1, t));
  if ((layerMask & 4) != 0) c += rgbm(texture(img2, t));
  if ((layerMask & 8) != 0) c += rgbm(texture(img3, t));
  return c;
}

vec3 ringLayers(vec2 t) {
  vec3 c = vec3(0.0);
  if ((layerMask & 1) != 0) c += rgbm(texture(ring0, t));
  if ((layerMask & 2) != 0) c += rgbm(texture(ring1, t));
  if ((layerMask & 4) != 0) c += rgbm(texture(ring2, t));
  if ((layerMask & 8) != 0) c += rgbm(texture(ring3, t));
  return c;
}

// Atlas row coordinate for an offset d from the critical curve (first half negative, second half positive).
float rowOf(float d) {
  float h = ndelta * 0.5;
  float m = clamp(abs(d), deltaMin, deltaMax);
  float k = log(m / deltaMin) / log(deltaMax / deltaMin) * (h - 1.0);
  float j = d > 0.0 ? h + k : h - 1.0 - k;
  return (j + 0.5) / ndelta;
}

vec3 sky(vec2 ab) {
  vec2 rel = ab - vec2(centerAlpha, 0.0);
  float psi = mod(atan(rel.y, rel.x), TAU);
  float d = length(rel) - rhoC(psi);
  if (abs(d) <= deltaMax) return ringLayers(vec2(psi / TAU, rowOf(d)));
  vec2 t = vec2(ab.x / span + 0.5, 1.0 - (ab.y / (span / imageAspect) + 0.5));
  if (any(lessThan(t, vec2(0.0))) || any(greaterThan(t, vec2(1.0)))) return vec3(0.0);
  return imageLayers(t);
}

vec3 tonemap(vec3 c) {
  c *= exposure;
  c = clamp((c * (2.51 * c + 0.03)) / (c * (2.43 * c + 0.59) + 0.14), 0.0, 1.0);
  return pow(c, vec3(1.0 / 2.2));
}

void main() {
  vec3 c = vec3(0.0);
  if (viewMode == 1) {
    // Unrolled ring: psi across, offset from the curve up (outside on top, the curve at mid-height).
    c = ringLayers(vec2(screenUV.x, screenUV.y));
    if (showCurve == 1 && abs(screenUV.y - 0.5) < 0.6 / resolution.y) c = vec3(0.25, 0.85, 1.0);
    x3d_FragColor = vec4(tonemap(c), 1.0);
    return;
  }
  vec2 p = screenUV - 0.5;
  float vh = span / imageAspect / zoom;               // visible height in M
  vec2 px = vec2(vh * aspect, vh) / resolution;       // M per screen pixel
  vec2 centre = vec2(panX, panY) + vec2(p.x * vh * aspect, p.y * vh);
  int side = samples >= 16 ? 4 : (samples >= 4 ? 2 : 1);
  for (int i = 0; i < 4; i++) {
    if (i >= side) break;
    for (int j = 0; j < 4; j++) {
      if (j >= side) break;
      vec2 o = (vec2(float(i), float(j)) + 0.5) / float(side) - 0.5;
      c += sky(centre + o * px);
    }
  }
  c /= float(side * side);
  vec3 col = tonemap(c);
  if (showCurve == 1) {
    vec2 rel = centre - vec2(centerAlpha, 0.0);
    float d = length(rel) - rhoC(mod(atan(rel.y, rel.x), TAU));
    if (abs(d) < 1.0 * px.y) col = mix(col, vec3(0.25, 0.85, 1.0), 0.85);
  }
  x3d_FragColor = vec4(col, 1.0);
}
