"""Load DeepMimic mocap clips (CMU/SFU-derived) and project them to a 2D side view."""
import json, os, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DM = os.path.join(HERE, '..', 'mocap', 'dm')
S = 105.0                     # world units per metre (figure ~170 units tall)
_skel = json.load(open(os.path.join(DM, 'humanoid3d.txt')))['Skeleton']['Joints']
OFF = {j['Name']: np.array([j['AttachX'], j['AttachY'], j['AttachZ']]) for j in _skel}
PAR = {j['Name']: (_skel[j['Parent']]['Name'] if j['Parent'] >= 0 else None) for j in _skel}
# frame layout after dt: root pos(3) root quat(4) then per joint
LAYOUT = [('chest', 4), ('neck', 4), ('right_hip', 4), ('right_knee', 1), ('right_ankle', 4), ('right_shoulder', 4),
          ('right_elbow', 1), ('left_hip', 4), ('left_knee', 1), ('left_ankle', 4), ('left_shoulder', 4), ('left_elbow', 1)]
ORDER = ['root', 'chest', 'neck', 'right_hip', 'right_knee', 'right_ankle', 'right_shoulder', 'right_elbow', 'right_wrist',
         'left_hip', 'left_knee', 'left_ankle', 'left_shoulder', 'left_elbow', 'left_wrist']
# output joint names used by the renderer
NAMES = ['hip', 'chest', 'neck', 'head', 'rsh', 'rel', 'rhand', 'lsh', 'lel', 'lhand', 'rhp', 'rkn', 'rft', 'rtoe',
         'lhp', 'lkn', 'lft', 'ltoe']
IDX = {n: i for i, n in enumerate(NAMES)}

def qmul(a, b):
    w1, x1, y1, z1 = a; w2, x2, y2, z2 = b
    return np.array([w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2,
                     w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2])
def qrot(q, v):
    w, x, y, z = q
    R = np.array([[1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)], [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
                  [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]])
    return R @ v
def qz(a): return np.array([math.cos(a/2), 0, 0, math.sin(a/2)])

def load(name):
    """Return (fps, P) with P shape (T, len(NAMES), 3) in metres, y up, x forward, z lateral."""
    d = json.load(open(os.path.join(DM, f'humanoid3d_{name}.txt')))
    out = []
    for fr in d['Frames']:
        dt = fr[0]; v = fr[1:]
        rp = np.array(v[0:3]); rq = np.array(v[3:7]); i = 7
        loc = {'root': rq}
        for n, sz in LAYOUT:
            loc[n] = np.array(v[i:i+4]) if sz == 4 else qz(v[i]); i += sz
        loc['right_wrist'] = loc['left_wrist'] = np.array([1., 0, 0, 0])
        G, Pp = {}, {}
        for n in ORDER:
            p = PAR[n]
            if p is None: G[n] = loc[n]; Pp[n] = rp
            else: G[n] = qmul(G[p], loc[n]); Pp[n] = Pp[p] + qrot(G[p], OFF[n])
        J = np.zeros((len(NAMES), 3))
        J[IDX['hip']] = Pp['root']; J[IDX['chest']] = Pp['chest']; J[IDX['neck']] = Pp['neck']
        J[IDX['head']] = Pp['neck'] + qrot(G['neck'], np.array([0.0, 0.17, 0.0]))
        for s, side in (('r', 'right'), ('l', 'left')):
            J[IDX[s+'sh']] = Pp[side+'_shoulder']; J[IDX[s+'el']] = Pp[side+'_elbow']; J[IDX[s+'hand']] = Pp[side+'_wrist']
            J[IDX[s+'hp']] = Pp[side+'_hip']; J[IDX[s+'kn']] = Pp[side+'_knee']; J[IDX[s+'ft']] = Pp[side+'_ankle']
            J[IDX[s+'toe']] = Pp[side+'_ankle'] + qrot(G[side+'_ankle'], np.array([0.14, -0.05, 0.0]))
        out.append(J)
    return 1.0/d['Frames'][0][0], np.array(out)
