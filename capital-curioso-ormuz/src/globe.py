import math, numpy as np, skia
from lib import *

def vec(lon, lat):
    lo, la = np.radians(lon), np.radians(lat)
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], -1)

class Globe:
    def __init__(self):
        self.rings = [(n, [vec(r[:, 0], r[:, 1]) for r in rings]) for n, rings in countries('110')]

    def basis(self, lon0, lat0):
        lo, la = math.radians(lon0), math.radians(lat0)
        e = np.array([-math.sin(lo), math.cos(lo), 0])
        n = np.array([-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la)])
        v = np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])
        return e, n, v

    def proj(self, V, cx, cy, R, B):
        e, n, v = B
        x = V @ e; y = V @ n; d = V @ v
        return cx + R * x, cy - R * y, d

    def proj_pt(self, lon, lat, cx, cy, R, B, alt=0.0):
        V = vec(lon, lat) * (1 + alt)
        x, y, d = self.proj(V, cx, cy, R, B)
        return (float(x), float(y)), float(d)

    def draw(self, c, cx, cy, R, lon0, lat0, hl=None, alpha=1.0):
        B = self.basis(lon0, lat0)
        # atmosphere
        circle(c, cx, cy, R * 1.06, BLUE, 0.35 * alpha, blur=R * 0.08)
        sh = skia.GradientShader.MakeRadial((cx - R * 0.3, cy - R * 0.35), R * 1.5, [rgba('#173D86'), rgba('#0A2150'), rgba('#040E26')], [0, 0.6, 1])
        c.drawCircle(cx, cy, R, skia.Paint(AntiAlias=True, Shader=sh))
        c.save()
        c.clipPath(skia.Path.Circle(cx, cy, R), doAntiAlias=True)
        # graticule
        gp = P(rgba(SKY, 0.13 * alpha), stroke=1.2)
        for lon in range(-180, 180, 20):
            lats = np.linspace(-90, 90, 60)
            V = vec(np.full_like(lats, lon), lats)
            x, y, d = self.proj(V, cx, cy, R, B)
            self._polyline(c, x, y, d, gp)
        for lat in range(-80, 90, 20):
            lons = np.linspace(-180, 180, 120)
            V = vec(lons, np.full_like(lons, lat))
            x, y, d = self.proj(V, cx, cy, R, B)
            self._polyline(c, x, y, d, gp)
        hl = hl or {}
        landp = P(rgba('#2A4F92', alpha)); bp = P(rgba('#7FA3E8', 0.7 * alpha), stroke=1.3)
        for name, rings in self.rings:
            path = skia.Path(); used = False
            for V in rings:
                x, y, d = self.proj(V, cx, cy, R, B)
                if d.max() <= 0:
                    continue
                hid = d < 0
                if hid.any():
                    dx, dy = x - cx, y - cy
                    nr = np.hypot(dx, dy) + 1e-9
                    x = np.where(hid, cx + dx / nr * R * 1.01, x)
                    y = np.where(hid, cy + dy / nr * R * 1.01, y)
                path.moveTo(x[0], y[0])
                for i in range(1, len(x)):
                    path.lineTo(x[i], y[i])
                path.close(); used = True
            if not used:
                continue
            c.drawPath(path, landp)
            if name in hl:
                col, st = hl[name]
                c.drawPath(path, P(rgba(col, 0.6 * st * alpha), blur=12))
                c.drawPath(path, P(rgba(col, 0.9 * st * alpha)))
            c.drawPath(path, bp)
        c.restore()
        # rim light
        circle(c, cx, cy, R, SKY, 0.5 * alpha, stroke=2)
        sh2 = skia.GradientShader.MakeRadial((cx, cy), R, [rgba('#000000', 0), rgba('#000000', 0), rgba('#000000', 0.45 * alpha)], [0, 0.75, 1])
        c.drawCircle(cx, cy, R, skia.Paint(AntiAlias=True, Shader=sh2))
        return B

    def _polyline(self, c, x, y, d, p):
        path = skia.Path(); pen = False
        for i in range(len(x)):
            if d[i] > 0:
                if pen: path.lineTo(x[i], y[i])
                else: path.moveTo(x[i], y[i]); pen = True
            else:
                pen = False
        c.drawPath(path, p)

    def arc_pts(self, a, b, cx, cy, R, B, n=80, h=0.22):
        va, vb = vec(*a), vec(*b)
        om = math.acos(float(np.clip(va @ vb, -1, 1)))
        pts = []
        for i in range(n + 1):
            f = i / n
            v = (math.sin((1 - f) * om) * va + math.sin(f * om) * vb) / math.sin(om)
            v = v * (1 + h * math.sin(math.pi * f))
            x, y, d = self.proj(v[None, :], cx, cy, R, B)
            pts.append((float(x[0]), float(y[0])))
        return pts
