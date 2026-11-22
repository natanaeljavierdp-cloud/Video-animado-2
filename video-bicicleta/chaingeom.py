"""Chain path geometry for the drivetrain (pure python, no bpy).

Plane: X (forward) / Z (up). Lateral offset Y handled separately.
Motion order of the loop:  ring(CW) -> lower pulley T(CW) -> upper pulley G(CCW) -> cog(CW) -> ring
CW is clockwise when looking with +X right and +Z up.
"""
import math

P = 0.0127  # chain pitch (1/2")


def pitch_r(n):
    return P / (2 * math.sin(math.pi / n))


class Circle:
    def __init__(self, cx, cz, n, wrap, name):
        self.cx, self.cz, self.n, self.wrap, self.name = cx, cz, n, wrap, name
        self.r = pitch_r(n)


def _vel(circle, ang):
    # velocity direction of the chain at polar angle ang on a circle with wrap dir
    nx, nz = math.cos(ang), math.sin(ang)
    if circle.wrap > 0:  # CW
        return (nz, -nx)
    return (-nz, nx)


def tangent(A, B):
    """Return (angA, angB, pA, pB) of the tangent segment leaving A and arriving at B
    consistent with wrap directions."""
    dx, dz = B.cx - A.cx, B.cz - A.cz
    D = math.hypot(dx, dz)
    base = math.atan2(dz, dx)
    best = None
    for sa in (1, -1):
        for sb in (1, -1):
            ra, rb = A.r * sa, B.r * sb
            c = -(rb - ra) / D
            if abs(c) > 1:
                continue
            for sgn in (1, -1):
                ang = base + sgn * math.acos(c)
                nx, nz = math.cos(ang), math.sin(ang)
                pa = (A.cx + ra * nx, A.cz + ra * nz)
                pb = (B.cx + rb * nx, B.cz + rb * nz)
                ux, uz = pb[0] - pa[0], pb[1] - pa[1]
                L = math.hypot(ux, uz)
                ux, uz = ux / L, uz / L
                angA = math.atan2(pa[1] - A.cz, pa[0] - A.cx)
                angB = math.atan2(pb[1] - B.cz, pb[0] - B.cx)
                va = _vel(A, angA)
                vb = _vel(B, angB)
                score = (va[0] * ux + va[1] * uz) + (vb[0] * ux + vb[1] * uz)
                if best is None or score > best[0]:
                    best = (score, angA, angB, pa, pb)
    return best[1:]


class Path:
    """Closed path made of arcs (on circles) and lines. Param length on arcs uses the
    polygon (chord) metric so rollers spaced P sit exactly on pitch points."""

    def __init__(self, circles):
        self.circles = circles
        k = len(circles)
        tans = [tangent(circles[i], circles[(i + 1) % k]) for i in range(k)]
        self.segs = []
        for i, C in enumerate(circles):
            a_in = tans[i - 1][1]
            a_out = tans[i][0]
            # sweep in wrap direction: CW => decreasing angle
            if C.wrap > 0:
                sweep = (a_in - a_out) % (2 * math.pi)
            else:
                sweep = (a_out - a_in) % (2 * math.pi)
            plen = sweep * C.n * P / (2 * math.pi)
            self.segs.append(("arc", C, a_in, sweep, plen))
            pa, pb = tans[i][2], tans[i][3]
            L = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
            self.segs.append(("line", pa, pb, L, C, circles[(i + 1) % k]))
        self.length = sum(s[4] if s[0] == "arc" else s[3] for s in self.segs)

    def point(self, s):
        """returns (x, z, seg_owner_name, frac_info). s in [0, length)."""
        s = s % self.length
        for sg in self.segs:
            L = sg[4] if sg[0] == "arc" else sg[3]
            if s <= L:
                if sg[0] == "arc":
                    C, a0, sweep = sg[1], sg[2], sg[3]
                    da = s / (C.n * P / (2 * math.pi))
                    a = a0 - da if C.wrap > 0 else a0 + da
                    return (C.cx + C.r * math.cos(a), C.cz + C.r * math.sin(a), C.name, 0.0, a)
                pa, pb = sg[1], sg[2]
                f = s / L if L > 0 else 0
                return (pa[0] + (pb[0] - pa[0]) * f, pa[1] + (pb[1] - pa[1]) * f,
                        sg[4].name + ">" + sg[5].name, f, None)
            s -= L
        sg = self.segs[0]
        return self.point(0)


# ---------------- frame / drivetrain layout -----------------
BB = (0.0, 0.27)
REAR = (-0.41, 0.34)
FRONT = (0.59, 0.34)
WHEEL_R = 0.338
CAGE_LEN = 0.068  # upper->lower pulley distance
JOCKEY_N = 11


def upper_pulley_pos(n_cog):
    rc = pitch_r(n_cog)
    # slant parallelogram keeps a constant gap below the cog
    return (REAR[0] + 0.006 + 0.10 * (rc - pitch_r(11)) * 0.0,
            REAR[1] - rc - pitch_r(JOCKEY_N) - 0.008)


def build_path(n_ring, n_cog, phi, r_ring=None, r_cog=None):
    """phi: cage angle (rad) of lower pulley around upper pulley, measured from straight down,
    positive = swings forward."""
    gx, gz = upper_pulley_pos(n_cog if r_cog is None else 11)
    if r_cog is not None:
        gz = REAR[1] - r_cog - pitch_r(JOCKEY_N) - 0.008
    tx, tz = gx + CAGE_LEN * math.sin(phi), gz - CAGE_LEN * math.cos(phi)
    ring = Circle(BB[0], BB[1], n_ring, +1, "ring")
    if r_ring is not None:
        ring.r = r_ring
    T = Circle(tx, tz, JOCKEY_N, +1, "T")
    G = Circle(gx, gz, JOCKEY_N, -1, "G")
    cog = Circle(REAR[0], REAR[1], n_cog, +1, "cog")
    if r_cog is not None:
        cog.r = r_cog
    return Path([ring, T, G, cog])


def solve_phi(n_ring, n_cog, target_len, r_ring=None, r_cog=None):
    lo, hi = -0.6, 1.6
    flo = build_path(n_ring, n_cog, lo, r_ring, r_cog).length - target_len
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        fm = build_path(n_ring, n_cog, mid, r_ring, r_cog).length - target_len
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


if __name__ == "__main__":
    for nr, nc in [(34, 11), (34, 13), (50, 11), (50, 13), (34, 34), (50, 34)]:
        for phi in (0.0, 0.6, 1.2):
            pth = build_path(nr, nc, phi)
            print(nr, nc, phi, round(pth.length / P, 2))
