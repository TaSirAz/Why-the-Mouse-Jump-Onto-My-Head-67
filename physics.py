"""Deterministic, display-independent desktop toy physics (pixels / seconds)."""
from dataclasses import dataclass
from math import hypot, degrees, ceil


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


def substep_count(bodies, dt, gravity=1250):
    """Keep relative travel below a small disc's diameter, including acceleration.

    Apply the entire simulation (integration AND pair contacts) at dt / count.
    Merely substepping integration would still let fast discs pass each other.
    """
    bodies = list(bodies)
    if not bodies or dt <= 0:
        return 1
    radius = max(.5, min(b.r for b in bodies))
    speed = max((hypot(b.vx, b.vy) for b in bodies if not b.held), default=0)
    return max(1, ceil((speed * dt + abs(gravity) * dt * dt) / (radius * .5)))


def constrain(body, bounds):
    """Keep pair-contact corrections inside the work area; never move a held pet."""
    if body.held:
        return
    left, top, right, bottom = bounds
    for axis, lo, hi in (("x", left + body.r, right - body.r),
                         ("y", top + body.r, bottom - body.r)):
        pos = getattr(body, axis)
        if lo > hi:
            setattr(body, axis, (lo + hi) / 2)
            setattr(body, "v" + axis, 0)
        else:
            setattr(body, axis, max(lo, min(hi, pos)))


def _land(body, previous_x, previous_y, platforms, bounce):
    """Find the first one-way window top crossed, using x at impact time."""
    if body.vy < 0 or body.y < previous_y:
        return None
    old_foot, new_foot = previous_y + body.r, body.y + body.r
    candidates = []
    for left, top, right, bottom in platforms:
        if right <= left or bottom <= top or old_foot > top + 2 or new_foot < top:
            continue
        fraction = max(0., min(1., (top - old_foot) / max(1e-9, new_foot - old_foot)))
        impact_x = previous_x + (body.x - previous_x) * fraction
        # A pet that has already walked off the edge must be allowed to fall.
        if left <= impact_x <= right and left <= body.x <= right:
            candidates.append((fraction, top))
    if not candidates:
        return None
    _, top = min(candidates)
    speed = body.vy
    body.y = top - body.r
    body.vy = -speed * bounce if speed > 100 else 0
    body.grounded = body.vy == 0
    return speed


def step(body, bounds, dt, gravity=1250, bounce=.69, drive=0, platforms=()):
    """Integrate one substep and resolve one-way window tops and screen edges."""
    if body.held or dt <= 0:
        return []
    left, top, right, bottom = bounds
    previous_x, previous_y = body.x, body.y
    body.vx += drive * dt
    body.vx *= .998 ** (dt * 120)
    body.vy += gravity * dt
    body.x += body.vx * dt
    body.y += body.vy * dt
    hits = []
    body.grounded = False
    landing_speed = _land(body, previous_x, previous_y, platforms, .58) if gravity > 0 else None
    if landing_speed is not None:
        body.vx *= .992 ** (dt * 120)
        if landing_speed > 90:
            hits.append(("y", landing_speed, body.x, body.y))
            body.spin += body.vx * .12
    for axis, lo, hi in (("x", left + body.r, right - body.r),
                         ("y", top + body.r, bottom - body.r)):
        pos = getattr(body, axis)
        velocity = getattr(body, "v" + axis)
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
                # Settle on whichever horizontal surface gravity points toward.
                supporting = axis == "y" and ((pos >= hi and gravity >= 0) or
                                               (pos <= lo and gravity < 0))
                if supporting and speed < 85:
                    body.vy = 0
                else:
                    setattr(body, "v" + axis, -velocity * bounce)
                if speed > 90:
                    hits.append((axis, speed, body.x, body.y))
                    body.spin += (body.vx * .12 if axis == "y" else -velocity * .13)
            if axis == "y" and ((pos >= hi and gravity >= 0) or (pos <= lo and gravity < 0)):
                body.grounded = body.vy == 0
                body.vx *= .983 ** (dt * 120)
    if body.grounded:
        body.angle += degrees(body.vx / max(.5, body.r)) * dt
        body.spin *= .94 ** (dt * 120)
    else:
        body.angle += body.spin * dt
        body.spin *= .998 ** (dt * 120)
    body.angle %= 360
    return hits


def collide(a, b, restitution=.78):
    """Equal-density discs; held pets have infinite mass and stay unchanged."""
    dx, dy = b.x - a.x, b.y - a.y
    distance = hypot(dx, dy)
    overlap = a.r + b.r - distance
    if overlap < 0 or (a.held and b.held):
        return 0
    nx, ny = (dx / distance, dy / distance) if distance > .0001 else (1, 0)
    ia = 0 if a.held else 1 / max(.5, a.r) ** 2
    ib = 0 if b.held else 1 / max(.5, b.r) ** 2
    total = ia + ib
    a.x -= nx * overlap * ia / total
    a.y -= ny * overlap * ia / total
    b.x += nx * overlap * ib / total
    b.y += ny * overlap * ib / total
    relative = ((0 if b.held else b.vx) - (0 if a.held else a.vx)) * nx + \
               ((0 if b.held else b.vy) - (0 if a.held else a.vy)) * ny
    if relative >= 0:
        return 0
    # Low-speed contacts settle rather than adding repeated tiny bounces.
    response = restitution if -relative > 85 else 0
    impulse = -(1 + response) * relative / total
    a.vx -= impulse * nx * ia
    a.vy -= impulse * ny * ia
    b.vx += impulse * nx * ib
    b.vy += impulse * ny * ib
    if not a.held:
        a.spin -= relative * .25
        if a.vy < -1:
            a.grounded = False
    if not b.held:
        b.spin += relative * .25
        if b.vy < -1:
            b.grounded = False
    return -relative
