"""Deterministic, display-independent desktop toy physics (pixels / seconds)."""
from dataclasses import dataclass, field
from math import hypot, degrees, ceil, sin, cos, radians


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
    # Distances to the rendered alpha bounds; None keeps circular geometry.
    extents: tuple | None = None
    support: tuple | None = None
    surface_contacts: set = field(default_factory=set, repr=False)
    pair_contacts: set = field(default_factory=set, repr=False)


def visible_extents(body):
    return body.extents if body.extents is not None else (body.r,) * 4


def rotated_extents(points, angle=0, scale=1, squash=0):
    """Transform centered alpha-outline points just like the sprite painter.

    Points are in source-image pixels relative to its center. Distances may be
    signed for an asymmetric silhouette whose center is outside its alpha bounds.
    """
    c, s = cos(radians(angle)), sin(radians(angle))
    transformed = [(scale * (x * (1 + squash) * c - y * (1 - squash) * s),
                    scale * (x * (1 + squash) * s + y * (1 - squash) * c))
                   for x, y in points]
    if not transformed:
        return None
    xs, ys = zip(*transformed)
    return -min(xs), -min(ys), max(xs), max(ys)


@dataclass
class ImpactGate:
    """Debounce visual HIT effects independently from physical impulses."""
    minimum_speed: float = 120
    cooldown: float = .15
    last_time: float = float("-inf")
    last_contacts: dict = field(default_factory=dict, repr=False)

    def accept(self, speed, now, contact=None):
        if speed < self.minimum_speed or now - self.last_time < self.cooldown:
            return False
        if contact is not None and now - self.last_contacts.get(contact, float("-inf")) < self.cooldown:
            return False
        self.last_time = now
        if contact is not None:
            self.last_contacts[contact] = now
            if len(self.last_contacts) > 64:
                self.last_contacts = {key: stamp for key, stamp in self.last_contacts.items()
                                      if now - stamp < self.cooldown}
        return True


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
    el, et, er, eb = visible_extents(body)
    if body.support is not None:
        support_left, support_top, support_right = body.support
        if support_left <= body.x <= support_right and body.y + eb > support_top:
            body.y = support_top - eb
            body.vy = min(0, body.vy)
            body.grounded = body.vy == 0
    for axis, lo, hi in (("x", left + el, right - er),
                         ("y", top + et, bottom - eb)):
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
    eb = visible_extents(body)[3]
    old_foot, new_foot = previous_y + eb, body.y + eb
    candidates = []
    for left, top, right, bottom in platforms:
        if right <= left or bottom <= top or old_foot > top + 2 or new_foot < top:
            continue
        fraction = max(0., min(1., (top - old_foot) / max(1e-9, new_foot - old_foot)))
        impact_x = previous_x + (body.x - previous_x) * fraction
        # A pet that has already walked off the edge must be allowed to fall.
        if left <= impact_x <= right and left <= body.x <= right:
            candidates.append((fraction, top, left, right))
    if not candidates:
        return None
    _, top, left, right = min(candidates)
    speed = body.vy
    body.y = top - eb
    body.vy = -speed * bounce if speed > 100 else 0
    body.grounded = body.vy == 0
    if body.grounded:
        body.support = (left, top, right)
    return speed, top


def _window_walls(body, previous_x, previous_y, rectangles, platforms, bounce, contacts, previous_contacts):
    """Sweep side/underside entry only; bodies already inside are never ejected."""
    el, et, er, eb = visible_extents(body)
    dx, dy = body.x - previous_x, body.y - previous_y
    candidates = []
    for left, top, right, bottom in rectangles:
        if left >= right or top >= bottom:
            continue
        if (previous_x + er > left and previous_x - el < right and
                previous_y + eb > top and previous_y - et < bottom):
            continue
        if dx > 0 and previous_x + er <= left and body.x + er >= left:
            fraction = (left - previous_x - er) / dx
            y = previous_y + dy * fraction
            if y + eb > top + .001 and y - et < bottom - .001:
                candidates.append((fraction, "x", left - er, "left", (left, top, right, bottom)))
        elif dx < 0 and previous_x - el >= right and body.x - el <= right:
            fraction = (right - previous_x + el) / dx
            y = previous_y + dy * fraction
            if y + eb > top + .001 and y - et < bottom - .001:
                candidates.append((fraction, "x", right + el, "right", (left, top, right, bottom)))
        if dy < 0 and previous_y - et >= bottom and body.y - et <= bottom:
            fraction = (bottom - previous_y + et) / dy
            x = previous_x + dx * fraction
            if x + er > left + .001 and x - el < right - .001:
                candidates.append((fraction, "y", bottom + et, "bottom", (left, top, right, bottom)))
    if not candidates:
        return []
    fraction, axis, position, side, rectangle = min(candidates)
    # A top encountered first must retain its one-way landing behavior.
    if dy > 0:
        for left, top, right, bottom in platforms:
            if previous_y + eb <= top and body.y + eb >= top:
                top_fraction = (top - previous_y - eb) / dy
                x = previous_x + dx * top_fraction
                if top_fraction <= fraction and left <= x <= right:
                    return []
    key = ("window", axis, side, rectangle)
    contacts.add(key)
    velocity = getattr(body, "v" + axis)
    speed = abs(velocity)
    setattr(body, axis, position)
    setattr(body, "v" + axis, -velocity * bounce)
    if speed > 90 and key not in previous_contacts:
        body.spin += -velocity * .13 if axis == "x" else body.vx * .12
        return [(axis, speed, body.x, body.y)]
    return []


def step(body, bounds, dt, gravity=1250, bounce=.69, drive=0, platforms=(), window_walls=()):
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
    previous_contacts = body.surface_contacts
    contacts = set()
    body.grounded = False
    body.support = None
    hits.extend(_window_walls(body, previous_x, previous_y, window_walls, platforms,
                              bounce, contacts, previous_contacts))
    landing_speed = _land(body, previous_x, previous_y, platforms, .58) if gravity > 0 else None
    if landing_speed is not None:
        landing_speed, platform_top = landing_speed
        key = ("platform", platform_top)
        contacts.add(key)
        body.vx *= .992 ** (dt * 120)
        if landing_speed > 90 and key not in previous_contacts:
            hits.append(("y", landing_speed, body.x, body.y))
            body.spin += body.vx * .12
    el, et, er, eb = visible_extents(body)
    for axis, lo, hi in (("x", left + el, right - er),
                         ("y", top + et, bottom - eb)):
        pos = getattr(body, axis)
        velocity = getattr(body, "v" + axis)
        if lo > hi:
            setattr(body, axis, (lo + hi) / 2)
            setattr(body, "v" + axis, 0)
            continue
        if pos <= lo or pos >= hi:
            key = (axis, "low" if pos <= lo else "high")
            contacts.add(key)
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
                if speed > 90 and key not in previous_contacts:
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
    body.surface_contacts = contacts
    return hits


def collide(a, b, restitution=.78):
    """Equal-density discs; held pets have infinite mass and stay unchanged."""
    dx, dy = b.x - a.x, b.y - a.y
    distance = hypot(dx, dy)
    overlap = a.r + b.r - distance
    key_a, key_b = id(b), id(a)
    if overlap < -2:
        a.pair_contacts.discard(key_a)
        b.pair_contacts.discard(key_b)
    if overlap < 0 or (a.held and b.held):
        return 0
    fresh = key_a not in a.pair_contacts or key_b not in b.pair_contacts
    a.pair_contacts.add(key_a)
    b.pair_contacts.add(key_b)
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
    response = restitution if fresh and -relative > 85 else 0
    impulse = -(1 + response) * relative / total
    a.vx -= impulse * nx * ia
    a.vy -= impulse * ny * ia
    b.vx += impulse * nx * ib
    b.vy += impulse * ny * ib
    if not a.held:
        if fresh and -relative > 85:
            a.spin -= relative * .25
        if a.vy < -1:
            a.grounded = False
    if not b.held:
        if fresh and -relative > 85:
            b.spin += relative * .25
        if b.vy < -1:
            b.grounded = False
    return -relative if fresh else 0
