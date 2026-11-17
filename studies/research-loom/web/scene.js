/* The browser renders saved geometry only. No scientific model is solved here. */
(function (root) {
  'use strict';
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
  const values = a => a.flat(Infinity).map(n => {
    if (typeof n !== 'number' || !Number.isFinite(n)) throw Error('Nonfinite scene coordinate.');
    return String(n);
  }).join(' ');
  function validateFrame(frame) {
    let count = 0;
    const ids = new Set();
    for (const key of ['meshes','lines','points']) for (const g of frame[key] || []) {
      if (!g.id || ids.has(g.id)) throw Error('Duplicate geometry identity.');
      ids.add(g.id);
      if (!Array.isArray(g.positions) || !g.positions.length) throw Error('Missing geometry positions.');
      count += g.positions.length;
      for (const p of g.positions) if (p.length !== 3 || !p.every(Number.isFinite)) throw Error('Invalid scene position.');
      if (g.colors && (g.colors.length !== g.positions.length || g.colors.some(c => c.length !== 3 || c.some(v => !Number.isFinite(v) || v<0 || v>1)))) throw Error('Invalid vertex colors.');
      if (!g.color || g.color.length!==3 || g.color.some(c => !Number.isFinite(c)||c<0||c>1)) throw Error('Invalid material color.');
      if (!Number.isFinite(g.opacity) || g.opacity<0 || g.opacity>1) throw Error('Invalid opacity.');
      if (key === 'meshes') for (const f of g.faces) if (f.length<3 || new Set(f).size!==f.length || f.some(i => !Number.isInteger(i)||i<0||i>=g.positions.length)) throw Error('Invalid mesh connectivity.');
    }
    if (!ids.size || ids.size>250 || count>30000) throw Error('Scene budget exceeded.');
    return count;
  }
  function bounds(packet) {
    const lo=[Infinity,Infinity,Infinity], hi=[-Infinity,-Infinity,-Infinity];
    for (const frame of packet.frames) for (const key of ['meshes','lines','points']) for (const g of frame[key] || []) for (const p of g.positions) p.forEach((v,i) => { lo[i]=Math.min(lo[i],v);hi[i]=Math.max(hi[i],v); });
    return {center:lo.map((v,i)=>(v+hi[i])/2),size:lo.map((v,i)=>Math.max(.1,hi[i]-v)*1.12)};
  }
  // One orthonormal projection, preserving scale and handedness in its plane.
  const depth=[.62,.42,1],dn=Math.hypot(...depth),d=depth.map(v=>v/dn);
  const rn=Math.hypot(1,.62),right=[1/rn,0,-.62/rn];
  const up=[d[1]*right[2],d[2]*right[0]-d[0]*right[2],-d[1]*right[0]];
  function project(p) {return [right,up,d].map(axis=>axis.reduce((sum,v,i)=>sum+v*p[i],0));}
  const api={esc,values,validateFrame,bounds,project};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.LoomScene=api;
})(typeof window!=='undefined'?window:globalThis);
