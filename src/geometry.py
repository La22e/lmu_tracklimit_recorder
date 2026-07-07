import math


def compute_both_edges(x, z, heading, path_lateral, track_edge, history):
    te = abs(track_edge)

    if history:
        prev_x, prev_z = history[-1]
        dx = x - prev_x
        dz = z - prev_z
        d = math.hypot(dx, dz)
        if d > 0.01:
            rx = dz / d
            rz = -dx / d
            center_x = x - path_lateral * rx
            center_z = z - path_lateral * rz
            perp_x = -dz / d
            perp_z = dx / d
            left_ex = center_x + te * perp_x
            left_ez = center_z + te * perp_z
            right_ex = center_x - te * perp_x
            right_ez = center_z - te * perp_z
            history.append((x, z))
            if len(history) > 30:
                history.pop(0)
            return left_ex, left_ez, right_ex, right_ez

    history.append((x, z))
    if len(history) > 30:
        history.pop(0)
    center_x = x - path_lateral * math.cos(heading)
    center_z = z + path_lateral * math.sin(heading)
    dist_left = max(0.0, path_lateral + te)
    dist_right = max(0.0, te - path_lateral)
    left_ex = x + dist_left * (-math.cos(heading))
    left_ez = z + dist_left * math.sin(heading)
    right_ex = x + dist_right * math.cos(heading)
    right_ez = z + dist_right * (-math.sin(heading))
    return left_ex, left_ez, right_ex, right_ez


def detect_laps(rows, track_length):
    laps = []
    cur = [rows[0]]
    for r in rows[1:]:
        if r[2] < cur[-1][2] - track_length * 0.4:
            if len(cur) >= 5:
                laps.append(cur)
            cur = []
        cur.append(r)
    if len(cur) >= 5:
        laps.append(cur)
    return laps


def average_side(rows, track_length, step=2.0, smooth_half=2, min_lap_points=5):
    laps = detect_laps(rows, track_length)
    if not laps:
        return None

    num = max(2, int(track_length / step) + 1)
    grid = [track_length * i / (num - 1) for i in range(num)]

    sum_x = [0.0] * num
    sum_z = [0.0] * num
    cnt = [0] * num

    for lap in laps:
        clean = [lap[0]]
        for r in lap[1:]:
            if r[2] > clean[-1][2]:
                clean.append(r)
        if len(clean) < min_lap_points:
            continue
        ds = [r[2] for r in clean]
        xs = [r[0] for r in clean]
        zs = [r[1] for r in clean]
        idx = 0
        n = len(ds)
        for i, d in enumerate(grid):
            if d <= ds[0]:
                vx, vz = xs[0], zs[0]
            elif d >= ds[-1]:
                vx, vz = xs[-1], zs[-1]
            else:
                while idx < n - 1 and ds[idx + 1] < d:
                    idx += 1
                if idx >= n - 1:
                    vx, vz = xs[-1], zs[-1]
                else:
                    t = (d - ds[idx]) / (ds[idx + 1] - ds[idx])
                    vx = xs[idx] + t * (xs[idx + 1] - xs[idx])
                    vz = zs[idx] + t * (zs[idx + 1] - zs[idx])
            sum_x[i] += vx
            sum_z[i] += vz
            cnt[i] += 1

    avg_x = [sum_x[i] / cnt[i] if cnt[i] > 0 else 0.0 for i in range(num)]
    avg_z = [sum_z[i] / cnt[i] if cnt[i] > 0 else 0.0 for i in range(num)]
    sm_x = avg_x[:]
    sm_z = avg_z[:]
    for i in range(num):
        lo = max(0, i - smooth_half)
        hi = min(num, i + smooth_half + 1)
        valid = [(avg_x[j], avg_z[j]) for j in range(lo, hi) if cnt[j] > 0]
        if valid:
            sm_x[i] = sum(v[0] for v in valid) / len(valid)
            sm_z[i] = sum(v[1] for v in valid) / len(valid)

    result = []
    for i in range(num):
        if cnt[i] > 0:
            result.append((sm_x[i], sm_z[i], grid[i]))
    return result


def rdp_simplify(pts, epsilon=0.5):
    if len(pts) <= 2:
        return list(range(len(pts)))
    dx = pts[-1][0] - pts[0][0]
    dz = pts[-1][1] - pts[0][1]
    line_len = math.hypot(dx, dz)
    if line_len < 1e-9:
        return [0, len(pts) - 1]
    max_dist = 0
    max_idx = 0
    for i in range(1, len(pts) - 1):
        cross = abs(dz * pts[i][0] - dx * pts[i][1] + pts[-1][0] * pts[0][1] - pts[-1][1] * pts[0][0])
        d = cross / line_len
        if d > max_dist:
            max_dist = d
            max_idx = i
    if max_dist < epsilon:
        return [0, len(pts) - 1]
    left = rdp_simplify(pts[:max_idx + 1], epsilon)
    right = rdp_simplify(pts[max_idx:], epsilon)
    return left[:-1] + [max_idx + i for i in right]
