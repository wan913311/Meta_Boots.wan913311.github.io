"""
Meta-Booth Q 版分身零件庫 — Blender 建模腳本
用法：blender --background --python build_avatar.py -- <輸出資料夾>
      或 python3 build_avatar.py <輸出資料夾>（已安裝 bpy 模組時）

座標：Blender Z 向上，角色面向 -Y；_L = 角色左手邊 = +X。
所有尺寸用「網頁座標」思考 W(x, y, z)：y 向上、z 向鏡頭，再轉成 Blender。
"""
import sys, os, math, random
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix, Euler

OUT = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].endswith('.py') else os.getcwd()
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)
random.seed(7)
PI = math.pi

def W(x, y, z):
    """網頁座標 → Blender 座標"""
    return Vector((x, -z, y))

# ---------------------------------------------------------------- 場景
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

def collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or scene.collection).children.link(c)
    return c
COL = {k: collection(k) for k in ['00_ROOT_PIVOTS', '01_body', '02_hair', '03_eyes', '04_mouth', '05_outfit', '06_acc']}

# ---------------------------------------------------------------- 貼圖（低解析度、老引擎感）
def value_noise(w, h, cell, seed):
    r = np.random.default_rng(seed)
    gw, gh = w // cell + 2, h // cell + 2
    g = r.random((gh, gw))
    ys, xs = np.mgrid[0:h, 0:w] / cell
    x0, y0 = xs.astype(int), ys.astype(int)
    fx, fy = xs - x0, ys - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = g[y0, x0] * (1 - fx) + g[y0, x0 + 1] * fx
    b = g[y0 + 1, x0] * (1 - fx) + g[y0 + 1, x0 + 1] * fx
    return a * (1 - fy) + b * fy

def fbm(w, h, seed, cells=(16, 8, 4, 2)):
    out = np.zeros((h, w)); amp = 1; tot = 0
    for i, c in enumerate(cells):
        out += value_noise(w, h, c, seed + i) * amp; tot += amp; amp *= 0.5
    return out / tot

def to_image(name, rgba):
    """rgba: (h, w, 4) float 0..1，第 0 列是貼圖『上方』"""
    h, w, _ = rgba.shape
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.colorspace_settings.name = 'sRGB'
    img.pixels.foreach_set(np.flipud(np.clip(rgba, 0, 1)).astype(np.float32).ravel())
    img.update()
    tdir = os.path.join(OUT, 'textures'); os.makedirs(tdir, exist_ok=True)
    img.filepath_raw = os.path.join(tdir, name + '.png'); img.file_format = 'PNG'; img.save()
    img.pack()
    return img

def rgb(hexs):
    hexs = hexs.lstrip('#')
    return np.array([int(hexs[i:i + 2], 16) / 255 for i in (0, 2, 4)])

def solid_tex(name, base, size=64, noise=0.12, grad=0.18, seed=1, streak=None, extra=None):
    """底色 + 雜訊 + 由上到下的烘焙暗角（v 方向）"""
    n = fbm(size, size, seed)
    shade = 1 - noise / 2 + n * noise
    ys = np.linspace(0, 1, size)[:, None]
    shade = shade * (1 - grad * ys)
    if streak is not None:
        s = np.repeat(rng.random((1, size)), size, axis=0) * 0.5 + fbm(size, size, seed + 9, (8, 2)) * 0.5
        shade = shade * (1 - streak / 2 + s * streak)
    col = rgb(base)[None, None, :] * shade[:, :, None]
    if extra is not None:
        col = extra(col)
    a = np.ones((size, size, 1))
    return to_image(name, np.concatenate([col, a], axis=2))

# 像素畫小工具
def canvas(n):
    return np.zeros((n, n, 4))
def put(c, x, y, color, a=1.0):
    n = c.shape[0]
    if 0 <= x < n and 0 <= y < n:
        c[y, x, :3] = rgb(color) if isinstance(color, str) else color
        c[y, x, 3] = a
def disk(c, cx, cy, r, color, a=1.0):
    n = c.shape[0]
    for y in range(n):
        for x in range(n):
            if (x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 <= r * r:
                put(c, x, y, color, a)
def ellipse(c, cx, cy, rx, ry, color, a=1.0):
    n = c.shape[0]
    for y in range(n):
        for x in range(n):
            if ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1:
                put(c, x, y, color, a)
def arc(c, cx, cy, r, t0, t1, color, th=1.2):
    n = c.shape[0]
    for y in range(n):
        for x in range(n):
            dx, dy = x + .5 - cx, y + .5 - cy
            d = math.hypot(dx, dy); ang = math.atan2(-dy, dx)
            if abs(d - r) <= th / 2 + .3 and t0 <= ang <= t1:
                put(c, x, y, color)

def eye_textures():
    S = 24; out = {}
    # 0 圓眼：大虹膜 + 高光 + 上睫毛
    c = canvas(S)
    ellipse(c, 12, 13, 8.5, 9.5, '#f4efe9'); ellipse(c, 12, 14, 7, 8.5, '#e3dcd6')
    ellipse(c, 12, 14, 6, 7.5, '#4a2f2a'); ellipse(c, 12, 15, 4.5, 5.5, '#6d4535'); ellipse(c, 12, 15, 2.5, 3, '#160d10')
    disk(c, 15, 10, 2, '#ffffff'); put(c, 9, 18, '#ffffff')
    for x in range(3, 22): put(c, x, 4 + (1 if x in (3, 4, 20, 21) else 0), '#1d1418'); put(c, x, 5, '#2c1d22')
    put(c, 2, 6, '#1d1418'); put(c, 21, 6, '#1d1418'); put(c, 22, 7, '#1d1418')
    out[0] = c
    # 1 笑眼：倒 U 弧線
    c = canvas(S); arc(c, 12, 16, 7, 0.15, PI - 0.15, '#1d1418', 2.2); arc(c, 12, 16, 7.6, 0.4, PI - 0.4, '#3a2a2e', 1.0); out[1] = c
    # 2 睏睏眼：半閉 + 下垂眼皮
    c = canvas(S)
    ellipse(c, 12, 15, 8, 4, '#f4efe9'); ellipse(c, 12, 16, 5, 3.4, '#4a2f2a'); ellipse(c, 12, 16.5, 2, 2, '#160d10')
    for x in range(3, 22): put(c, x, 12, '#1d1418'); put(c, x, 13, '#1d1418'); put(c, x, 11, '#c9a99a', .9)
    out[2] = c
    # 3 星星眼
    c = canvas(S)
    ellipse(c, 12, 13, 8.5, 9.5, '#f4efe9'); ellipse(c, 12, 14, 6.5, 8, '#2b3a6b')
    pts = [(12 + math.cos(i * PI / 5 - PI / 2) * (6 if i % 2 == 0 else 2.6), 14 + math.sin(i * PI / 5 - PI / 2) * (6 if i % 2 == 0 else 2.6)) for i in range(10)]
    def inside(px, py):
        hit = False
        for i in range(len(pts)):
            (x1, y1), (x2, y2) = pts[i], pts[i - 1]
            if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1: hit = not hit
        return hit
    for y in range(S):
        for x in range(S):
            if inside(x + .5, y + .5): put(c, x, y, '#ffd23f')
    disk(c, 15, 10, 1.6, '#ffffff')
    for x in range(3, 22): put(c, x, 4, '#1d1418'); put(c, x, 5, '#2c1d22')
    out[3] = c
    return out

def mouth_textures():
    S = 24; out = {}
    c = canvas(S); arc(c, 12, 6, 7, -PI + 0.5, -0.5, '#5a2a30', 1.8); out[0] = c                 # 微笑
    c = canvas(S); ellipse(c, 12, 12, 5, 4.2, '#5a1e2a'); ellipse(c, 12, 14, 3.5, 2, '#d0677a'); ellipse(c, 12, 9.5, 3.6, 1, '#f4efe9'); out[1] = c  # 張嘴
    c = canvas(S); arc(c, 9, 10, 3.2, -PI + 0.2, -0.1, '#5a2a30', 1.6); arc(c, 15, 10, 3.2, -PI + 0.1, -0.2, '#5a2a30', 1.6); out[2] = c  # 貓嘴
    c = canvas(S); ellipse(c, 12, 12, 6, 6.5, '#4a1520'); ellipse(c, 12, 16, 4.2, 2.6, '#d0677a'); ellipse(c, 12, 7.2, 4.5, 1.2, '#f4efe9'); out['open'] = c  # 講話
    return out

def blush_texture():
    S = 24; c = canvas(S)
    for y in range(S):
        for x in range(S):
            d = math.hypot((x + .5 - 12) / 11, (y + .5 - 12) / 6)
            if d < 1: put(c, x, y, '#ff8c9a', (1 - d) * 0.75)
    for (x, y) in [(6, 10), (9, 13), (13, 11), (16, 14), (18, 10), (11, 9)]:
        put(c, x, y, '#a85a4a', .9)   # 雀斑（參考圖的感覺）
    return c

# ---------------------------------------------------------------- 材質
MATS = {}
def material(name, image=None, color=(1, 1, 1), alpha=False, emission=None, rough=0.85, metal=0.0):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if image is not None:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = image; t.interpolation = 'Closest'; t.location = (-400, 200)
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
        if alpha:
            r = nt.nodes.new('ShaderNodeMath'); r.operation = 'ROUND'; r.location = (-150, 0)
            nt.links.new(t.outputs['Alpha'], r.inputs[0]); nt.links.new(r.outputs[0], b.inputs['Alpha'])
            m.surface_render_method = 'DITHERED'
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1); b.inputs['Emission Strength'].default_value = 1.0
    MATS[name] = m
    return m

def knit(col):  # 針織橫紋
    h, w, _ = col.shape
    rows = (np.arange(h)[:, None] % 3 == 0) * 0.12
    return col * (1 - rows[:, :, None])
def plaid(col):
    h, w, _ = col.shape
    ys, xs = np.mgrid[0:h, 0:w]
    band = ((xs % 16 < 4) | (ys % 16 < 4)).astype(float)
    thin = ((xs % 16 == 9) | (ys % 16 == 9)).astype(float)
    out = col * (0.62 + 0.38 * (1 - band[:, :, None]) * (1 - thin[:, :, None]))
    out = out + thin[:, :, None] * np.array([0.35, 0.3, 0.3]) * 0.6
    return out
def shirt_print(col):
    c = col.copy()
    for y in range(22, 38):
        for x in range(22, 42):
            if (x - 32) ** 2 / 100 + (y - 30) ** 2 / 64 < 1 and not (abs(x - 32) < 5 and abs(y - 30) < 3):
                c[y, x] = c[y, x] * 0.45
    return c

def build_materials():
    material('TINT_SKIN', solid_tex('tex_skin', '#fbf1ea', 64, 0.07, 0.03, 11))
    material('TINT_HAIR', solid_tex('tex_hair', '#f0ece6', 64, 0.10, 0.30, 21, streak=0.5))
    material('TINT_OUTFIT_cotton', solid_tex('tex_cotton', '#f2f2ee', 64, 0.14, 0.25, 31))
    material('TINT_OUTFIT_tee', solid_tex('tex_tee', '#f2f2ee', 64, 0.14, 0.25, 32, extra=shirt_print))
    material('TINT_OUTFIT_plaid', solid_tex('tex_plaid', '#f0f0f0', 64, 0.10, 0.2, 33, extra=plaid))
    material('SHIRT_white', solid_tex('tex_shirt', '#ece9e2', 64, 0.18, 0.28, 41))
    material('BOW_red', solid_tex('tex_bow', '#9e2632', 32, 0.15, 0.1, 42, extra=plaid))
    material('KNIT_tan', solid_tex('tex_knit', '#c49a63', 64, 0.15, 0.2, 43, extra=knit))
    material('DENIM', solid_tex('tex_denim', '#3d4a66', 64, 0.25, 0.2, 44, streak=0.3))
    material('JOGGER_grey', solid_tex('tex_jog', '#6e6c74', 64, 0.15, 0.25, 45))
    material('SOCKS_white', solid_tex('tex_socks', '#ebe8e1', 64, 0.12, 0.25, 46, extra=knit))
    material('SHOES_leather', solid_tex('tex_shoes', '#262028', 32, 0.3, 0.1, 47), rough=0.45)
    material('METAL_dark', None, (0.06, 0.05, 0.07), rough=0.35, metal=0.6)
    material('GOLD', solid_tex('tex_gold', '#e8b83c', 32, 0.35, 0.2, 48), rough=0.35, metal=0.8)
    material('PLASTIC_pink', solid_tex('tex_pink', '#ff4f7b', 32, 0.1, 0.2, 49), rough=0.4)
    material('PINK_inner', None, (1.0, 0.45, 0.55))
    material('HALO_glow', None, (1.0, 0.85, 0.3), emission=(1.0, 0.75, 0.2))
    material('STRING_white', None, (0.95, 0.95, 0.92))
    for k, c in eye_textures().items(): material('EYE_%s' % k, to_image('tex_eye_%s' % k, c), alpha=True)
    for k, c in mouth_textures().items(): material('MOUTH_%s' % k, to_image('tex_mouth_%s' % k, c), alpha=True)
    material('BLUSH', to_image('tex_blush', blush_texture()), alpha=True)

# ---------------------------------------------------------------- 物件工具
def empty(name, loc, parent=None):
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'PLAIN_AXES'; e.empty_display_size = 0.15
    e.location = loc; COL['00_ROOT_PIVOTS'].objects.link(e)
    if parent: set_parent(e, parent)
    return e

def set_parent(obj, parent):
    bpy.context.view_layer.update()
    mw = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    obj.matrix_world = mw

def finish(obj, name, col, mat, parent, loc):
    obj.name = name; obj.data.name = name
    for c in obj.users_collection: c.objects.unlink(obj)
    COL[col].objects.link(obj)
    obj.data.materials.clear(); obj.data.materials.append(MATS[mat])
    for p in obj.data.polygons: p.use_smooth = False
    obj.location = loc
    if parent: set_parent(obj, parent)
    return obj

def bake(obj, rot=(0, 0, 0), scale=(1, 1, 1)):
    """把旋轉、縮放直接寫進網格（物件本身維持零旋轉，匯出乾淨）"""
    m = Euler(rot, 'XYZ').to_matrix().to_4x4() @ Matrix.Diagonal((*scale, 1))
    obj.data.transform(m)

def prim(kind, name, col, mat, parent, wpos, rot=(0, 0, 0), scale=(1, 1, 1), **kw):
    fn = {'cyl': bpy.ops.mesh.primitive_cylinder_add, 'cone': bpy.ops.mesh.primitive_cone_add,
          'sphere': bpy.ops.mesh.primitive_uv_sphere_add, 'ico': bpy.ops.mesh.primitive_ico_sphere_add,
          'cube': bpy.ops.mesh.primitive_cube_add, 'torus': bpy.ops.mesh.primitive_torus_add,
          'plane': bpy.ops.mesh.primitive_plane_add}[kind]
    fn(location=(0, 0, 0), **kw)
    o = bpy.context.active_object
    bake(o, rot, scale)
    return finish(o, name, col, mat, parent, W(*wpos))

def hair_shell(name, parent, radius, keep, rings=10, segs=16, scale=(1, 1, 1), center=(0, 1.5, 0)):
    """球殼頭髮：keep(theta_from_top, phi_front) 回傳 True 的面保留。phi=0 為正前方"""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=radius, location=(0, 0, 0))
    o = bpy.context.active_object
    bm = bmesh.new(); bm.from_mesh(o.data)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        th = math.acos(max(-1, min(1, c.z / radius)))
        ph = math.atan2(c.x, -c.y)   # 0 = 前方(-Y)
        if not keep(th, ph): kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(o.data); bm.free()
    bake(o, scale=scale)
    o = finish(o, name, '02_hair', 'TINT_HAIR', parent, W(*center))
    # 雙面顯示（頭髮殼內側也看得到）
    return o

# ---------------------------------------------------------------- 建模
def build():
    HY = 1.5
    root = empty('ROOT', W(0, 0, 0))
    upper = empty('PIVOT_Upper', W(0, 0.38, 0), root)
    head = empty('PIVOT_Head', W(0, 1.0, 0), upper)
    arm = {s: empty('PIVOT_Arm_' + ('L' if s > 0 else 'R'), W(s * 0.376, 0.95, 0), upper) for s in (1, -1)}
    eyep = {s: empty('PIVOT_Eye_' + ('L' if s > 0 else 'R'), W(s * 0.22, HY - 0.02, 0.565), head) for s in (1, -1)}
    mouthp = empty('PIVOT_Mouth', W(0, HY - 0.2, 0.565), head)
    LR = lambda s: 'L' if s > 0 else 'R'

    # ---- body（每個人都有）
    for s in (1, -1):
        prim('cyl', 'body_leg_' + LR(s), '01_body', 'TINT_SKIN', root, (s * 0.15, 0.24, 0), vertices=7, radius=0.115, depth=0.34)
        prim('cube', 'body_shoe_' + LR(s), '01_body', 'SHOES_leather', root, (s * 0.15, 0.055, 0.04), scale=(0.105, 0.16, 0.055))
        prim('cyl', 'body_arm_' + LR(s), '01_body', 'TINT_SKIN', arm[s], (s * 0.376, 0.72, 0), vertices=6, radius=0.075, depth=0.42)
        prim('ico', 'body_hand_' + LR(s), '01_body', 'TINT_SKIN', arm[s], (s * 0.376, 0.49, 0), subdivisions=1, radius=0.1, scale=(1, 1.1, 0.9))
        prim('sphere', 'body_ear_' + LR(s), '01_body', 'TINT_SKIN', head, (s * 0.6, HY - 0.05, 0), segments=6, ring_count=4, radius=0.1, scale=(0.5, 0.8, 1))
    prim('cyl', 'body_neck', '01_body', 'TINT_SKIN', upper, (0, 1.02, 0), vertices=7, radius=0.12, depth=0.14)
    prim('sphere', 'body_head', '01_body', 'TINT_SKIN', head, (0, HY, 0), segments=16, ring_count=10, radius=0.62, scale=(1, 0.95, 0.92))

    # ---- 臉：眼睛、嘴巴、腮紅都是貼圖平面
    face_rot = lambda yaw: (PI / 2, 0, yaw)
    for k in range(4):
        for s in (1, -1):
            o = prim('plane', 'eyes_%d_%s' % (k, LR(s)), '03_eyes', 'EYE_%d' % k, eyep[s], (s * 0.22, HY - 0.02, 0.565), rot=face_rot(s * 0.38), size=0.22)
    for k in [0, 1, 2, 'open']:
        prim('plane', 'mouth_%s' % k, '04_mouth', 'MOUTH_%s' % k, mouthp, (0, HY - 0.2, 0.57), rot=face_rot(0), size=0.22)
    for s in (1, -1):
        prim('plane', 'blush_1_' + LR(s), '01_body', 'BLUSH', head, (s * 0.35, HY - 0.13, 0.49), rot=face_rot(s * 0.62), size=0.2)

    # ---- 頭髮（5 款，各自完整）
    fringe = lambda th, ph: th < 0.42 * PI if abs(ph) < 0.95 else True
    def bangs(prefix, n=5, length=0.26, spread=0.42):
        for i in range(n):
            t = (i / (n - 1) - 0.5) * 2
            x = t * spread; z = math.sqrt(max(0.01, 0.6 ** 2 - x ** 2)) * 0.93
            prim('cone', '%s_bang%d' % (prefix, i), '02_hair', 'TINT_HAIR', head, (x, HY + 0.24 - abs(t) * 0.05, z - 0.02),
                 rot=(PI - 0.35, -t * 0.25, 0), scale=(1, 0.45, 1), vertices=4, radius1=0.12, radius2=0, depth=length + random.uniform(-0.04, 0.05))
    # 0 短髮
    hair_shell('hair_0', head, 0.67, lambda th, ph: th < 0.42 * PI or (abs(ph) > 1.0 and th < 0.6 * PI), scale=(1, 1.0, 0.95))
    bangs('hair_0')
    # 1 雙馬尾
    hair_shell('hair_1', head, 0.67, lambda th, ph: th < 0.42 * PI or (abs(ph) > 1.0 and th < 0.62 * PI), scale=(1, 1.0, 0.95))
    bangs('hair_1')
    for s in (1, -1):
        prim('ico', 'hair_1_tie_' + LR(s), '02_hair', 'PLASTIC_pink', head, (s * 0.62, HY + 0.12, -0.1), subdivisions=1, radius=0.09)
        prim('cone', 'hair_1_tail_' + LR(s), '02_hair', 'TINT_HAIR', head, (s * 0.8, HY - 0.25, -0.12), rot=(0, PI - s * 0.3, 0), vertices=6, radius1=0.19, radius2=0.03, depth=0.7)
    # 2 刺蝟頭
    hair_shell('hair_2', head, 0.665, lambda th, ph: th < 0.40 * PI or (abs(ph) > 1.1 and th < 0.58 * PI), scale=(1, 1.0, 0.95))
    up = Vector((0, 0, 1))
    for i in range(9):
        th = 0 if i == 0 else 0.72 + (i % 2) * 0.25; ph = (i / 8) * 2 * PI
        d = Vector((math.sin(th) * math.sin(ph), math.sin(th) * math.cos(ph) * 0.9 + (0 if i == 0 else 0.15), math.cos(th))).normalized()
        o = prim('cone', 'hair_2_spike%d' % i, '02_hair', 'TINT_HAIR', head, (0, HY, 0), vertices=5, radius1=0.15, radius2=0, depth=0.42)
        o.data.transform(Matrix.Translation(d * 0.62) @ up.rotation_difference(d).to_matrix().to_4x4())
    # 3 鮑伯頭（長一點、參差的髮尾）
    jag = lambda ph: 0.62 + 0.13 * ((math.sin(round(ph * 2.86) * 12.9898) * 43758.5453) % 1)
    hair_shell('hair_3', head, 0.70, lambda th, ph: (th < 0.42 * PI) or (abs(ph) > 0.85 and th < jag(ph) * PI), rings=14, segs=22, scale=(1.02, 1.0, 0.97))
    bangs('hair_3', n=6, length=0.32, spread=0.46)
    # 4 丸子頭
    hair_shell('hair_4', head, 0.67, lambda th, ph: th < 0.42 * PI or (abs(ph) > 1.0 and th < 0.6 * PI), scale=(1, 1.0, 0.95))
    bangs('hair_4')
    prim('sphere', 'hair_4_bun', '02_hair', 'TINT_HAIR', head, (0, HY + 0.62, -0.15), segments=8, ring_count=6, radius=0.25)
    prim('torus', 'hair_4_tie', '02_hair', 'PLASTIC_pink', head, (0, HY + 0.48, -0.1), rot=(0.3, 0, 0), major_segments=10, minor_segments=4, major_radius=0.15, minor_radius=0.035)

    # ---- 服裝（torso 在 PIVOT_Upper、袖子在手臂、下身在 ROOT）
    def torso(prefix, mat, top=0.3, bot=0.4, depth=0.62, cy=0.69):
        prim('cyl', prefix + '_torso', '05_outfit', mat, upper, (0, cy, 0), vertices=8, radius=bot, depth=depth)
        o = bpy.data.objects[prefix + '_torso']
        for v in o.data.vertices:
            if v.co.z > 0: v.co.x *= top / bot; v.co.y *= top / bot
    def sleeves(prefix, mat, length):
        for s in (1, -1):
            prim('cyl', '%s_arm_%s' % (prefix, LR(s)), '05_outfit', mat, arm[s], (s * 0.376, 0.95 - length / 2 - 0.01, 0), vertices=7, radius=0.108, depth=length)
    def pants(prefix, mat, length=0.24):
        for s in (1, -1):
            prim('cyl', '%s_lower_%s' % (prefix, LR(s)), '05_outfit', mat, root, (s * 0.15, 0.40 - length / 2, 0), vertices=7, radius=0.135, depth=length)
        prim('cyl', prefix + '_lower_hip', '05_outfit', mat, root, (0, 0.40, 0), vertices=8, radius=0.37, depth=0.08)

    # 0 T恤 + 牛仔短褲
    torso('outfit_0', 'TINT_OUTFIT_tee'); sleeves('outfit_0', 'TINT_OUTFIT_tee', 0.2); pants('outfit_0', 'DENIM', 0.16)
    # 1 帽T + 棉褲
    torso('outfit_1', 'TINT_OUTFIT_cotton'); sleeves('outfit_1', 'TINT_OUTFIT_cotton', 0.4); pants('outfit_1', 'JOGGER_grey', 0.3)
    prim('torus', 'outfit_1_hood', '05_outfit', 'TINT_OUTFIT_cotton', upper, (0, 1.0, -0.06), major_segments=10, minor_segments=5, major_radius=0.27, minor_radius=0.1)
    prim('cube', 'outfit_1_pocket', '05_outfit', 'TINT_OUTFIT_cotton', upper, (0, 0.55, 0.375), rot=(0.16, 0, 0), scale=(0.21, 0.025, 0.075))
    for s in (1, -1):
        prim('cyl', 'outfit_1_string_' + LR(s), '05_outfit', 'STRING_white', upper, (s * 0.08, 0.86, 0.33), vertices=4, radius=0.013, depth=0.2)
    # 2 洋裝 + 白襪
    torso('outfit_2', 'TINT_OUTFIT_cotton', 0.29, 0.35, 0.46, 0.78); sleeves('outfit_2', 'TINT_OUTFIT_cotton', 0.16)
    prim('cone', 'outfit_2_lower_skirt', '05_outfit', 'TINT_OUTFIT_cotton', root, (0, 0.42, 0), vertices=10, radius1=0.64, radius2=0.33, depth=0.46)
    prim('torus', 'outfit_2_collar', '05_outfit', 'STRING_white', upper, (0, 1.0, 0), major_segments=10, minor_segments=4, major_radius=0.25, minor_radius=0.04)
    for s in (1, -1):
        prim('cyl', 'outfit_2_lower_sock_' + LR(s), '05_outfit', 'SOCKS_white', root, (s * 0.15, 0.17, 0), vertices=7, radius=0.125, depth=0.16)
    # 3 制服：白襯衫 + 蝴蝶結 + 綁腰針織衫 + 格子褶裙 + 泡泡襪
    torso('outfit_3', 'SHIRT_white'); sleeves('outfit_3', 'SHIRT_white', 0.4)
    prim('cone', 'outfit_3_lower_skirt', '05_outfit', 'TINT_OUTFIT_plaid', root, (0, 0.36, 0), vertices=12, radius1=0.56, radius2=0.38, depth=0.32)
    sk = bpy.data.objects['outfit_3_lower_skirt']
    for v in sk.data.vertices:   # 褶子：底邊每隔一點往外推
        if v.co.z < 0:
            a = math.atan2(v.co.y, v.co.x); k = 1.0 + 0.08 * math.cos(a * 12)
            v.co.x *= k; v.co.y *= k
    for s in (1, -1):
        prim('cone', 'outfit_3_lower_sock_' + LR(s), '05_outfit', 'SOCKS_white', root, (s * 0.15, 0.17, 0), vertices=8, radius1=0.16, radius2=0.13, depth=0.2)
    prim('torus', 'outfit_3_sweater', '05_outfit', 'KNIT_tan', upper, (0, 0.44, 0.0), major_segments=10, minor_segments=5, major_radius=0.39, minor_radius=0.07)
    for s in (1, -1):
        prim('cube', 'outfit_3_sweaterarm_' + LR(s), '05_outfit', 'KNIT_tan', upper, (s * 0.12, 0.3, 0.38), rot=(0.15, 0, s * 0.35), scale=(0.07, 0.04, 0.18))
        prim('cone', 'outfit_3_bow_' + LR(s), '05_outfit', 'BOW_red', upper, (s * 0.07, 0.92, 0.32), rot=(0, s * PI / 2, 0), vertices=4, radius1=0.07, radius2=0.0, depth=0.12)
    prim('cube', 'outfit_3_bowknot', '05_outfit', 'BOW_red', upper, (0, 0.92, 0.33), scale=(0.025, 0.025, 0.03))

    # ---- 配件（acc_0 = 無）
    HYa = HY
    for s in (1, -1):
        prim('torus', 'acc_1_lens_' + LR(s), '06_acc', 'METAL_dark', head, (s * 0.22, HYa - 0.02, 0.6), rot=(PI / 2, 0, 0), major_segments=12, minor_segments=4, major_radius=0.11, minor_radius=0.015)
    prim('cube', 'acc_1_bridge', '06_acc', 'METAL_dark', head, (0, HYa, 0.6), scale=(0.05, 0.01, 0.01))
    for s in (1, -1):
        prim('cone', 'acc_2_ear_' + LR(s), '06_acc', 'TINT_HAIR', head, (s * 0.32, HYa + 0.56, 0), rot=(0, s * 0.4, 0), vertices=4, radius1=0.17, depth=0.3)
        prim('cone', 'acc_2_inner_' + LR(s), '06_acc', 'PINK_inner', head, (s * 0.33, HYa + 0.53, 0.07), rot=(0, s * 0.4, 0), vertices=4, radius1=0.09, depth=0.17)
    prim('cyl', 'acc_3_band', '06_acc', 'GOLD', head, (0, HYa + 0.62, 0), vertices=8, radius=0.24, depth=0.14, end_fill_type='NOTHING')
    for i in range(5):
        a = i / 5 * 2 * PI + PI / 2
        prim('cone', 'acc_3_tip%d' % i, '06_acc', 'GOLD', head, (math.cos(a) * 0.24, HYa + 0.76, math.sin(a) * 0.24), vertices=4, radius1=0.055, depth=0.15)
    prim('ico', 'acc_3_gem', '06_acc', 'PLASTIC_pink', head, (0, HYa + 0.62, 0.25), subdivisions=1, radius=0.05)
    prim('torus', 'acc_4_band', '06_acc', 'PLASTIC_pink', head, (0, HYa, 0), rot=(PI / 2, 0, 0), major_segments=18, minor_segments=5, major_radius=0.69, minor_radius=0.045)
    hb = bpy.data.objects['acc_4_band']
    bm = bmesh.new(); bm.from_mesh(hb.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().z < -0.02], context='FACES')
    bm.to_mesh(hb.data); bm.free()
    for s in (1, -1):
        prim('cyl', 'acc_4_cup_' + LR(s), '06_acc', 'PLASTIC_pink', head, (s * 0.66, HYa, 0), rot=(0, PI / 2, 0), vertices=10, radius=0.16, depth=0.13)
    prim('torus', 'acc_5_halo', '06_acc', 'HALO_glow', head, (0, HYa + 0.95, 0), major_segments=20, minor_segments=5, major_radius=0.3, minor_radius=0.04)

    # 頭髮殼、蝴蝶結等單面網格：雙面
    for m in MATS.values(): m.use_backface_culling = False
    return root

def default_visibility():
    """Blender 裡只顯示一組預設造型，方便看；匯出時全部都會輸出"""
    show = ('body_', 'ROOT', 'PIVOT', 'hair_0', 'eyes_0', 'mouth_0', 'blush_1', 'outfit_3', 'acc_')
    for o in bpy.data.objects:
        vis = o.name.startswith(show) and not (o.name.startswith('acc_') and not o.name.startswith('acc_4'))
        o.hide_set(not vis)

build_materials()
build()
bpy.context.view_layer.update()

glb = os.path.join(OUT, 'metabooth_avatar.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_visible=False, use_selection=False,
                          export_yup=True, export_apply=True, export_image_format='AUTO')
default_visibility()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'metabooth_avatar.blend'))
tris = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
print('OBJECTS', len(bpy.data.objects), 'FACES', tris, 'GLB', os.path.getsize(glb))
