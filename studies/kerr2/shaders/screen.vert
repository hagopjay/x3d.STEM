#version 300 es
precision highp float;
in vec4 x3d_Vertex;
out vec2 screenUV;
void main(){screenUV=x3d_Vertex.xy*.5+.5;gl_Position=vec4(x3d_Vertex.xy,0.,1.);}
