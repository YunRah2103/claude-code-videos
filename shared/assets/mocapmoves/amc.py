"""Minimal CMU ASF/AMC reader + forward kinematics (numpy only).

joints(asf, amc) -> (names, pos[frames, joints, 3], parent index per joint) in ASF units, Y up, 120 fps.
"""
import numpy as np


def _rot(ax, deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    if ax == 'x': return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if ax == 'y': return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def _euler(vals, order):
    """ASF/AMC convention: angles applied in `order`, i.e. R = R_last ... R_first."""
    R = np.eye(3)
    for ax, v in zip(order, vals):
        R = _rot(ax, v) @ R
    return R


def parse_asf(path):
    txt = open(path).read().split('\n')
    bones, hier, i = {}, {}, 0
    root_order, root_axis = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz'], 'xyz'
    while i < len(txt):
        ln = txt[i].strip()
        if ln.startswith(':root'):
            while not txt[i + 1].strip().startswith(':'):
                i += 1; p = txt[i].split()
                if p[0] == 'order': root_order = [x.lower() for x in p[1:]]
                if p[0] == 'axis': root_axis = p[1].lower()
        elif ln == 'begin' and bones is not None:
            b = {'dof': [], 'axis': np.zeros(3), 'axorder': 'xyz'}
            while txt[i + 1].strip() != 'end':
                i += 1; p = txt[i].split()
                if p[0] == 'name': b['name'] = p[1]
                elif p[0] == 'direction': b['dir'] = np.array(list(map(float, p[1:4])))
                elif p[0] == 'length': b['len'] = float(p[1])
                elif p[0] == 'axis': b['axis'] = np.array(list(map(float, p[1:4]))); b['axorder'] = p[4].lower()
                elif p[0] == 'dof': b['dof'] = [x.lower() for x in p[1:]]
            bones[b['name']] = b
        elif ln.startswith(':hierarchy'):
            i += 2
            while txt[i].strip() != 'end':
                p = txt[i].split(); hier[p[0]] = p[1:]; i += 1
        i += 1
    for b in bones.values():
        b['C'] = _euler(b['axis'], b['axorder'])
    return bones, hier, root_order, root_axis


def parse_amc(path):
    frames, cur = [], None
    for ln in open(path):
        ln = ln.strip()
        if not ln or ln[0] in '#:':
            continue
        if ln.isdigit():
            cur = {}; frames.append(cur); continue
        p = ln.split(); cur[p[0]] = list(map(float, p[1:]))
    return frames


def joints(asf, amc):
    bones, hier, rorder, raxis = parse_asf(asf)
    frames = parse_amc(amc)
    order = []
    def walk(n):
        for c in hier.get(n, []):
            order.append((n, c)); walk(c)
    walk('root')
    names = ['root'] + [c for _, c in order]
    idx = {n: k for k, n in enumerate(names)}
    out = np.zeros((len(frames), len(names), 3))
    par = [-1] + [idx[p] for p, _ in order]
    for f, fr in enumerate(frames):
        r = dict(zip(rorder, fr['root']))
        Rg = {'root': _euler([r.get('r' + a[-1], 0) for a in raxis], raxis)}
        pos = {'root': np.array([r['tx'], r['ty'], r['tz']])}
        for pa, c in order:
            b = bones[c]
            vals = dict(zip(b['dof'], fr.get(c, [])))
            L = _euler([vals.get('r' + a, 0.0) for a in b['axorder']], b['axorder'])
            Rg[c] = Rg[pa] @ b['C'] @ L @ b['C'].T
            pos[c] = pos[pa] + Rg[c] @ (b['dir'] * b['len'])
        for n, p in pos.items():
            out[f, idx[n]] = p
    return names, out, par
