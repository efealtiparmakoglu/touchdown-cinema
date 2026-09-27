#!/usr/bin/env python3
# Blender icinde: blender --background --python inis.py -- --scene scenes/dokunma.json [--gif 48]
"""touchdown-cinema — final: lander-cinema araci, terrain-cinema Ay
yuzeyine, lander-cinema fiziginin son saniyeleriyle iner.

Fizik: lander-cinema/fizik.inis_sim() — kaysiz gercek zaman. Toz sadece
temas anindan itibaren yatay sayilir (ayda havasiz: yayilma balistik).
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys

import bpy
import numpy as np
from mathutils import Vector

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
sys.path.insert(0, os.path.join(BURASI, "..", "lander-cinema"))
sys.path.insert(0, os.path.join(BURASI, "..", "terrain-cinema"))

import lander  # noqa: E402
import lander_render  # noqa: E402
import krater  # noqa: E402
import fizik as fz  # noqa: E402


def kamera_kur(konum, hedef, lens=45):
    cam = bpy.data.cameras.new("Cam")
    cam.lens = lens
    co = bpy.data.objects.new("kamera", cam)
    bpy.context.collection.objects.link(co)
    co.location = konum
    yon = Vector(hedef) - Vector(konum)
    co.rotation_euler = yon.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = co
    return co


def yuzey_kur(cfg):
    hz = cfg.get("hat", {})
    kraterler = krater.krater_alani(tuple(hz.get("merkez", [0, 0])),
                                    hz.get("alan", 200) * 0.45,
                                    hz.get("krater", 12),
                                    hz.get("tohum", 5))
    seg = hz.get("segman", 200)
    alan = hz.get("alan", 200)
    xs = np.linspace(-alan / 2, alan / 2, seg)
    ys = np.linspace(-alan / 2, alan / 2, seg)
    X, Y = np.meshgrid(xs, ys)
    Z = krater.yuzey(X, Y, kraterler, tohum=hz.get("tohum", 5))
    verts = np.stack((X.ravel(), Y.ravel(), Z.ravel()), axis=1)
    faces = []
    for i in range(seg - 1):
        for j in range(seg - 1):
            a = i * seg + j
            faces.append((a, a + 1, a + seg + 1, a + seg))
    mesh = bpy.data.meshes.new("AyYuzeyi")
    mesh.from_pydata(verts.tolist(), [], faces)
    mesh.update()
    for p in mesh.polygons:
        p.use_smooth = True
    obj = bpy.data.objects.new("AyYuzeyi", mesh)
    bpy.context.collection.objects.link(obj)
    m = bpy.data.materials.new("Regolit")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    renk = cfg.get("zemin", {}).get("color", (0.155, 0.15, 0.14))
    b.inputs["Base Color"].default_value = (*renk, 1)
    b.inputs["Roughness"].default_value = 0.97
    obj.data.materials.append(m)
    return obj


def toz_havuzu_kur(adet=18):
    m = bpy.data.materials.new("AyTozu")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (0.62, 0.60, 0.56, 1)
    vol.inputs["Density"].default_value = 0.8
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(vol.outputs["Volume"], outn.inputs["Volume"])
    havuz = []
    for i in range(adet):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.7, segments=14,
                                             ring_count=10, location=(0, 0, -60))
        p = bpy.context.active_object
        p.name = f"Toz{i}"
        p.data.materials.append(m)
        p.visible_shadow = False
        havuz.append({"obj": p, "mat": m, "aci": i / adet * 2 * math.pi})
    return havuz


def toz_guncelle(havuz, temas_sonrasi, merkez=(0, 0, 0.2)):
    """Temas anindan itibaren yatay sayilan regolit tozu (havasiz ay)."""
    for i, h in enumerate(havuz):
        if temas_sonrasi is None:
            h["obj"].location = (0, 0, -60)
            continue
        yas = temas_sonrasi * 5.5
        aci = h["aci"]
        mesafe = 1.2 + 7.5 * min(1.0, yas)
        x = merkez[0] + math.cos(aci) * mesafe
        y = merkez[1] + math.sin(aci) * mesafe * 0.9
        z = merkez[2] + min(1.5, yas * 0.5) * math.sin(aci * 3)
        h["obj"].location = (x, y, z)
        olcek = min(5.0, 0.9 + 1.5 * yas)
        h["obj"].scale = (olcek * 1.3, olcek, olcek * 0.5)
        for dugum in h["mat"].node_tree.nodes:
            if dugum.type == "VOLUME_PRINCIPLED":
                yog = 0.45 if yas > 0.02 else 0.0
                yog *= max(0.1, 1.0 - min(1.0, yas / 3.0))
                dugum.inputs["Density"].default_value = yog


def dunya_kure(cfg, kok):
    d = cfg.get("dunya", {})
    konum = Vector(d.get("konum", [-210, 380, 150]))
    r = d.get("yaricap", 34)
    m = bpy.data.materials.new("Dunya")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.015, 0.06, 0.24, 1)
    b.inputs["Roughness"].default_value = 0.9
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=48, ring_count=32,
                                         location=tuple(konum))
    k = bpy.context.active_object
    k.name = "Dunya"
    bpy.ops.object.shade_smooth()
    k.data.materials.append(m)
    k.parent = kok
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r * 0.98, segments=48,
                                         ring_count=32,
                                         location=(konum.x, konum.y,
                                                   konum.z + r * 0.55))
    kutup = bpy.context.active_object
    kutup.name = "DunyaKutup"
    bpy.ops.object.shade_smooth()
    mk = bpy.data.materials.new("DunyaKutup")
    mk.use_nodes = True
    bk = mk.node_tree.nodes["Principled BSDF"]
    bk.inputs["Base Color"].default_value = (0.85, 0.87, 0.9, 1)
    bk.inputs["Roughness"].default_value = 0.9
    kutup.data.materials.append(mk)
    kutup.parent = kok
    # Dunya'yi aydinlatan ek gunes (uzayda gorsun diye)
    ld = bpy.data.lights.new("DunyaIsik", "SUN")
    ld.energy = 3.0
    ld.color = (1.0, 1.0, 1.0)
    lo = bpy.data.objects.new("DunyaIsik", ld)
    bpy.context.collection.objects.link(lo)
    lo.rotation_euler = konum.to_track_quat("Z", "Y").to_euler()


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--gif", type=int, default=0)
    ap.add_argument("--fps", type=int, default=12)
    a = ap.parse_args(args)

    cfg = json.load(open(a.scene, encoding="utf-8"))
    if os.environ.get("HIZLI") == "1":
        cfg["render"] = {**cfg.get("render", {}), "width": 800, "height": 450,
                         "samples": 32}
        cfg["output"] = "/tmp/onizleme_td_" + os.path.basename(a.scene).replace(".json", ".png")
        print("  [HIZLI] onizleme ->", cfg["output"])

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = lander_render.sahne_kur(cfg)
    lander_render.zemin_kur(cfg)

    yuzey_kur(cfg)
    kok = bpy.data.objects.new("Sefer", None)
    bpy.context.collection.objects.link(kok)
    refs = lander.kur()
    dunya_kure(cfg, kok)

    sim = fz.inis_sim(dt=0.005)
    T, H, THR = sim["zamanlar"], sim["yukseklikler"], sim["throttle"]
    temas_t = sim["temas_t"]
    pencere = cfg["sefer"].get("son_saniye", 6.0)
    t_basla = temas_t - pencere

    def durum(t):
        tt = max(T[0], min(T[-1], t_basla + t))
        i = min(range(len(T)), key=lambda k: abs(T[k] - tt))
        return H[i], THR[i], (t + pencere) >= temas_t + 0.0, tt

    havuz = toz_havuzu_kur()

    cam_cfg = cfg["camera"]
    cam_obj = kamera_kur(cam_cfg["position"], cam_cfg["look_at"],
                         cam_cfg.get("lens", 45))

    if a.gif:
        cfg["render"] = {**cfg.get("render", {}), "width": 1280, "height": 720,
                         "samples": 48}
        out = os.path.splitext(cfg["output"])[0] + ".gif"
    else:
        out = cfg["output"]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    if not a.gif:
        t = cfg["sefer"].get("an", pencere + 0.6)
        h, thr, temas_oldu, tt = durum(t)
        refs["kok"].location.z = h
        lander.motor_pozu(refs, thr if h > 0.05 else 0.0, t)
        lander.gimbal_pozu(refs, 1.5)
        toz_guncelle(havuz, (t + pencere) - temas_t if temas_oldu else None)
        sc.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print(f"== BİTTİ -> {out} (t={t:.1f}, h={h:.2f})")
        return

    tmp = out + ".frames"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for f in range(a.gif):
        t = f / a.fps
        h, thr, temas_oldu, tt = durum(t)
        refs["kok"].location.z = h
        lander.motor_pozu(refs, thr if h > 0.05 else 0.0, t)
        lander.rcs_pozu(refs, t, aktif_araliklar=((0.0, 0.8),))
        toz_guncelle(havuz, (t + pencere) - temas_t if temas_oldu else None)
        sc.render.filepath = f"{tmp}/f{f:05d}.png"
        bpy.ops.render.render(write_still=True)
        print(f"  kare {f + 1}/{a.gif} h={h:.2f}")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
                    "-i", f"{tmp}/f%05d.png",
                    "-vf", "palettegen=max_colors=256:stats_mode=diff",
                    f"{tmp}/pal.png"], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
                    "-i", f"{tmp}/f%05d.png", "-i", f"{tmp}/pal.png",
                    "-lavfi", "paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle",
                    "-loop", "0", out], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"== BİTTİ -> {out}")


if __name__ == "__main__":
    main()
