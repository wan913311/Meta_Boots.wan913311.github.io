/* Meta-Booth 分身零件庫載入器（手機捏臉頁與主控台共用）
 * 讀 metabooth_avatar.glb → 依參數顯示零件、換色 → 回傳可驅動的骨架
 * 需要：THREE (r128) 與 THREE.GLTFLoader
 */
window.AvatarLib = (function () {
  const T = THREE;
  let template = null;
  const PALETTE = {
    hairColor: ['#2b2230', '#6b4a3a', '#d9a55b', '#e86a8e', '#6fa8dc', '#ecebe6'],
    skin: ['#fde3cf', '#f3c9a5', '#d9a07a', '#a8714f', '#6e4631'],
    outfitColor: ['#f2f2ee', '#ff5c7a', '#ffc93c', '#3ec7a6', '#4a7bf7', '#2e2a3a']
  };
  const matCache = {};

  // 老引擎感：全部換成逐頂點打光的 Lambert、貼圖不平滑
  function retroMaterial(old) {
    if (matCache[old.name]) return matCache[old.name];
    const m = new T.MeshLambertMaterial({
      name: old.name, color: old.color.clone(), map: old.map || null,
      emissive: old.emissive ? old.emissive.clone() : new T.Color(0), emissiveMap: old.emissiveMap || null,
      alphaTest: old.alphaTest || 0, transparent: false, side: T.DoubleSide
    });
    if (m.map) { m.map.magFilter = T.NearestFilter; m.map.minFilter = T.NearestFilter; m.map.generateMipmaps = false; m.map.needsUpdate = true; }
    matCache[old.name] = m;
    return m;
  }

  function prepare(scene) {
    scene.traverse(o => {
      if (o.isMesh) {
        o.material = Array.isArray(o.material) ? o.material.map(retroMaterial) : retroMaterial(o.material);
        o.frustumCulled = false;
      }
    });
    return scene;
  }

  function load(source) {
    return new Promise((resolve, reject) => {
      const loader = new T.GLTFLoader();
      const done = g => { template = prepare(g.scene); resolve(listParts()); };
      if (source instanceof ArrayBuffer) loader.parse(source, '', done, reject);
      else loader.load(source, done, undefined, reject);
    });
  }

  // 列出模型裡有哪些零件，方便檢查命名
  function listParts() {
    const found = {};
    template.traverse(o => {
      const m = /^(hair|eyes|mouth|blush|outfit|acc)_([0-9]+|open)/.exec(o.name);
      if (m) { (found[m[1]] = found[m[1]] || new Set()).add(m[2]); }
    });
    const out = {};
    Object.keys(found).forEach(k => { out[k] = [...found[k]].sort(); });
    out.pivots = ['ROOT', 'PIVOT_Upper', 'PIVOT_Head', 'PIVOT_Arm_L', 'PIVOT_Arm_R', 'PIVOT_Eye_L', 'PIVOT_Eye_R', 'PIVOT_Mouth']
      .filter(n => !template.getObjectByName(n));
    return out;  // pivots = 缺少的軸心
  }

  function partVisible(name, S) {
    let m;
    if ((m = /^hair_(\d+)/.exec(name))) return +m[1] === S.hair;
    if ((m = /^eyes_(\d+)/.exec(name))) return +m[1] === S.eyes;
    if (/^mouth_open/.test(name)) return false;
    if ((m = /^mouth_(\d+)/.exec(name))) return +m[1] === S.mouth;
    if ((m = /^blush_(\d+)/.exec(name))) return +m[1] === S.blush;
    if ((m = /^outfit_(\d+)/.exec(name))) return +m[1] === S.outfit;
    if ((m = /^acc_(\d+)/.exec(name))) return +m[1] === S.acc;
    return true;
  }

  function tint(S) {
    const set = (prefix, hex) => Object.values(matCache).forEach(m => {
      if (m.name.indexOf(prefix) === 0) m.color.setStyle(hex).convertSRGBToLinear();
    });
    set('TINT_HAIR', PALETTE.hairColor[S.hairColor]);
    set('TINT_SKIN', PALETTE.skin[S.skin]);
    set('TINT_OUTFIT', PALETTE.outfitColor[S.outfitColor]);
  }

  // 回傳和主控台一樣的骨架介面：root / upper / head / arms{1:左,-1:右} / eyes / mouthIdle / mouthOpen
  function make(S) {
    if (!template) return null;
    const clone = template.clone(true);
    clone.traverse(o => { if (o !== clone) o.visible = partVisible(o.name, S); });
    tint(S);
    const g = n => clone.getObjectByName(n);
    const root = new T.Group(); root.add(clone);
    const mouthIdle = g('mouth_' + S.mouth) || new T.Group();
    const mouthOpen = g('mouth_open') || new T.Group();
    return {
      root, upper: g('PIVOT_Upper') || new T.Group(), head: g('PIVOT_Head') || new T.Group(),
      arms: { 1: g('PIVOT_Arm_L') || new T.Group(), '-1': g('PIVOT_Arm_R') || new T.Group() },
      eyes: { 1: g('PIVOT_Eye_L') || new T.Group(), '-1': g('PIVOT_Eye_R') || new T.Group() },
      mouthIdle, mouthOpen, fromGLB: true
    };
  }

  return { load, make, listParts, get ready() { return !!template; } };
})();
