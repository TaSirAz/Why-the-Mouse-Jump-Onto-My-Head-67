"""Deterministic, display-independent desktop toy physics (pixels / seconds)."""
from dataclasses import dataclass
from math import hypot, degrees


@dataclass
class Body:
    x: float
    y: float
    r: float = 64
    vx: float = 0
    vy: float = 0
    angle: float = 0
    spin: float = 0
    held: bool = False
    grounded: bool = False


def step(body, bounds, dt, gravity=1250, bounce=.69, drive=0):
    """Resolve screen edges. Small fixed steps prevent fast throws tunneling."""
    if body.held:
        return []
    left, top, right, bottom = bounds
    body.vx += drive * dt
    body.vx *= .998 ** (dt * 120)
    body.vy += gravity * dt
    body.x += body.vx * dt
    body.y += body.vy * dt
    hits = []
    body.grounded = False
    for axis, lo, hi in (("x", left + body.r, right - body.r),
                         ("y", top + body.r, bottom - body.r)):
        pos = getattr(body, axis)
        velocity = getattr(body, "v" + axis)
        # Also handles work areas smaller than a resized pet.
        if lo > hi:
            setattr(body, axis, (lo + hi) / 2)
            setattr(body, "v" + axis, 0)
            continue
        if pos <= lo or pos >= hi:
            wall = lo if pos <= lo else hi
            outward = velocity < 0 if pos <= lo else velocity > 0
            setattr(body, axis, wall)
            if outward:
                speed = abs(velocity)
                if axis == "y" and pos >= hi and speed < 85:
                    body.vy = 0
                else:
                    setattr(body, "v" + axis, -velocity * bounce)
                if speed > 90:
                    hits.append((axis, speed, body.x, body.y))
                    body.spin += (body.vx * .12 if axis == "y" else -velocity * .13)
            if axis == "y" and pos >= hi:
                body.grounded = abs(body.vy) < 85
                body.vx *= .983 ** (dt * 120)
    if body.grounded:
        body.angle += degrees(body.vx / body.r) * dt
        body.spin *= .94 ** (dt * 120)
    else:
        body.angle += body.spin * dt
        body.spin *= .998 ** (dt * 120)
    body.angle %= 360
    return hits


def collide(a, b, restitution=.78):
    """Equal-density discs, inverse mass proportional to 1/r²; held pets are fixed."""
    dx, dy = b.x - a.x, b.y - a.y
    distance = hypot(dx, dy)
    overlap = a.r + b.r - distance
    if overlap <= 0 or (a.held and b.held):
        return 0
    nx, ny = (dx / distance, dy / distance) if distance > .0001 else (1, 0)
    ia = 0 if a.held else 1 / (a.r * a.r)
    ib = 0 if b.held else 1 / (b.r * b.r)
    total = ia + ib
    a.x -= nx * overlap * ia / total
    a.y -= ny * overlap * ia / total
    b.x += nx * overlap * ib / total
    b.y += ny * overlap * ib / total
    relative = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
    if relative >= 0:
        return 0
    impulse = -(1 + restitution) * relative / total
    a.vx -= impulse * nx * ia
    a.vy -= impulse * ny * ia
    b.vx += impulse * nx * ib
    b.vy += impulse * ny * ib
    a.spin -= relative * .25
    b.spin += relative * .25
    return -relative
