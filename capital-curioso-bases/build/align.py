# Alinea el texto exacto del guion con los tiempos de Whisper y genera words.json + timeline.json
import json, re, unicodedata, difflib, sys
SCRIPT = open('guion.txt', encoding='utf-8').read().split()
raw = json.load(open('build/words_raw.json'))
patch = json.load(open('build/words_patch.json'))  # re-transcripción del tramo 24-30 s
raw = [w for w in raw if not (patch[0][1] - 0.05 <= w[1] < patch[-1][2] - 0.05)] + patch
raw.sort(key=lambda w: w[1])
merged = []
for w in raw:  # unir "-Bolling", "-Henderson" con la palabra anterior
    if w[0].startswith('-') and merged:
        merged[-1] = [merged[-1][0] + w[0], merged[-1][1], w[2]]
    else:
        merged.append(list(w))
def norm(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s)
fix = {'christie': 'kristi', 'bowling': 'bolling'}
A = [norm(w) for w in SCRIPT]
B = [norm(w[0]) for w in merged]
B = [fix.get(b, b) for b in B]
B = [b.replace('anacostiabowling', 'anacostiabolling') for b in B]
times = [None] * len(SCRIPT)
sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        for k in range(i2 - i1):
            times[i1 + k] = merged[j1 + k][1:3]
    elif tag == 'replace' and (i2 - i1) == (j2 - j1):
        for k in range(i2 - i1):
            times[i1 + k] = merged[j1 + k][1:3]
    elif tag == 'replace':
        s, e = merged[j1][1], merged[j2 - 1][2]
        n = i2 - i1
        for k in range(n):
            times[i1 + k] = [s + (e - s) * k / n, s + (e - s) * (k + 1) / n]
# rellenar huecos interpolando
for i, t in enumerate(times):
    if t is None:
        prev = next(times[j][1] for j in range(i - 1, -1, -1) if times[j])
        nxt = next(times[j][0] for j in range(i + 1, len(times)) if times[j])
        times[i] = [prev, nxt]
        print('interpolada:', SCRIPT[i], file=sys.stderr)
words = [[w, round(t[0], 3), round(t[1], 3)] for w, t in zip(SCRIPT, times)]
json.dump(words, open('build/words.json', 'w'), ensure_ascii=False)

def at(word, n=0, end=False):
    k = norm(word); c = 0
    for w in words:
        if norm(w[0]) == k:
            if c == n:
                return w[2] if end else w[1]
            c += 1
    raise KeyError(word)

DUR = float(sys.argv[1])
T = {
  'dur': round(DUR + 1.1, 2),
  's2': at('casas', 0, True) + 0.25, 's3': at('pero') - 0.12, 's4': at('único', 0, True) + 0.35,
  's5': at('generales', 0, True) + 0.1,
}
# s6/s7... calculadas explícitamente
iy = [i for i, w in enumerate(words) if norm(w[0]) == 'ejercito'][0] - 3
T['s6'] = words[iy][1] - 0.1            # "Y el secretario del Ejército"
T['s7'] = at('también') - 0.25
T['s8'] = at('ya', 1) - 0.25           # "Ya son al menos ocho nombres"
T['s9'] = at('tres') - 0.3
T['s10'] = at('protección') - 0.45
ys = [w for w in words if norm(w[0]) == 'y']
T['s11'] = ys[-1][1] - 0.2               # "Y sígueme en Capital Curioso"
ev = {
  # escena 1
  'hook_x': at('duermen'), 'hook_base': at('casas'),
  # escena 2
  'b_name': at('secretario'), 'b_house': at('dejó'), 'b_wash': at('washington'), 'b_arrow': at('mudó'),
  'b_base': at('base'), 'b_quote': at('razón') - 0.3, 'b_threat': at('amenazas'), 'b_iran': at('irán'),
  'b_stamp': at('confirmó'),
  # escena 4
  'rubio': at('marco'), 'hegseth': at('pete'), 'mcnair': at('fort'), 'fila': at('fila'), 'rent': at('generales') + 0.15,
  # escena 5
  'noem': at('kristi'), 'cg_house': at('casa', 0), 'jbab': at('base', 1),
  # escena 6
  'driscoll': at('dan'), 'myer': at('base', 2), 'cemetery': at('junto'),
  # escena 7
  'miller': at('stephen'), 'bondi': at('pam'), 'blanche': at('todd'), 'unknown': at('revelado') - 0.3,
  # escena 8
  'count': at('ya', 1), 'eight': at('ocho'), 'motives': at('motivos'),
  'm_iran': at('irán', 1), 'm_cart': at('carteles'), 'm_viol': at('violencia'),
  # escena 9
  'lines': at('pocos'), 'wh': at('casa', 1), 'generals': at('casas', 1),
  # escena 10
  'p_prot': at('protección'), 'p_gob': at('gobierno'), 'p_cta': at('te'),
  # escena 11
  'follow': at('sígueme'), 'cc': at('capital'),
}
T.update({k: round(v, 3) for k, v in ev.items()})
T = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in T.items()}
json.dump(T, open('build/timeline.json', 'w'), indent=1)
print(json.dumps(T))
