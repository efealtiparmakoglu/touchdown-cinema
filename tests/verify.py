#!/usr/bin/env python3
"""touchdown-cinema kapilari (Blender'siz): fizik + arazi birlesimi."""

import math
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "..", "lander-cinema"))
sys.path.insert(0, os.path.join(KOK, "..", "terrain-cinema"))

import fizik as fz  # noqa: E402
import krater  # noqa: E402
import numpy as np  # noqa: E402


def main():
    ok, fail = 0, 0

    def kapil(ad, kosul, detay=""):
        nonlocal ok, fail
        if kosul:
            ok += 1
            print(f"  [ok] {ad} {detay}")
        else:
            fail += 1
            print(f"  [FAIL] {ad} {detay}")

    sim = fz.inis_sim(dt=0.005)

    # 1) temas hizi kapisi
    kapil("temas dikey hizi < 2 m/s", abs(sim["temas_dikey"]) < 2.0,
          f"({abs(sim['temas_dikey']):.2f} m/s)")

    # 2) yatay kapisi
    kapil("temas yatay hizi < 0.5 m/s", abs(sim["temas_yatay"]) < 0.5,
          f"({abs(sim['temas_yatay']):.2f} m/s)")

    # 3) son 6 saniyelik pencerede arac hala yukarda baslamali
    temas_t = sim["temas_t"]
    pencere = 6.0
    i0 = min(range(len(sim["zamanlar"])), key=lambda i: abs(sim["zamanlar"][i] - (temas_t - pencere)))
    h0 = sim["yukseklikler"][i0]
    kapil("iniş penceresi yukarida baslar", h0 > 8.0, f"(h = {h0:.1f} m)")

    # 4) iniş alanı (merkez 12 m) kratersiz — arazi fonksiyonunda
    alandaki = krater.krater_alani((0.0, 0.0), 90.0, 12)
    guvenli = all(math.hypot(cx, cy) > 12.0 for (cx, cy, _, _) in alandaki)
    kapil("inis alani temiz", guvenli and len(alandaki) >= 8,
          f"({len(alandaki)} krater, merkeze en yakin > 12 m)")

    # 5) arac ayak izi z=0'a iner: son yukseklik 0
    kapil("temas z = 0", sim["yukseklikler"][-1] <= 0.05)

    print(f"\n{'TUM KAPILAR GECTI' if fail == 0 else 'KAPILARDA FAIL VAR'}"
          f" ({ok} ok, {fail} fail)")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
