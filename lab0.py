import collections
from kit import generate, Simulator, HARD
sim = Simulator(generate(1101, 200, 'evaluation', 'development'))
s = sim.observe()
m = s['members'][0]
for k in HARD: print(k, m['fields'][k], m['field_status'][k])

ms = s['members']   # only people who have arrived by day 0
known = [sum(x['fields'][k] is not None for k in HARD) for x in ms]
print('arrived day 0:', len(ms))
print('hard fields known -> count:', sorted(collections.Counter(known).items()))
print('fully known:', known.count(11))
print('any hard field declined:', sum(any(x['field_status'][k] == 'declined' for k in HARD) for x in ms))