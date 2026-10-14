- B1 greedy: 120 episodes, all valid: True, mode trusted_local, overall MSMI/100 0.375
- B2 no-clarification: 120 episodes, all valid: True, mode trusted_local, overall MSMI/100 0.104
- B3 random-feasible: 120 episodes, all valid: True, mode trusted_local, overall MSMI/100 0.325
- Method: 120 episodes, all valid: True, mode trusted_local, overall MSMI/100 0.375

Seeds 1181-1200 (20 per family), families: cold_start, delayed, development, drift, shift, sparse.


**MSMI/100** (mean over seeds)

| family | B1 greedy | B2 no-clarification | B3 random-feasible | Method |
|---|---|---|---|---|
| cold_start | 0.350 | 0.050 | 0.250 | 0.350 |
| delayed | 0.425 | 0.150 | 0.375 | 0.425 |
| development | 0.500 | 0.150 | 0.500 | 0.500 |
| drift | 0.450 | 0.150 | 0.450 | 0.450 |
| shift | 0.475 | 0.125 | 0.325 | 0.475 |
| sparse | 0.050 | 0.000 | 0.050 | 0.050 |
| all | 0.375 | 0.104 | 0.325 | 0.375 |

**mutual/100** (mean over seeds)

| family | B1 greedy | B2 no-clarification | B3 random-feasible | Method |
|---|---|---|---|---|
| cold_start | 5.475 | 0.850 | 5.250 | 5.475 |
| delayed | 6.750 | 2.375 | 6.825 | 6.750 |
| development | 6.600 | 2.375 | 7.050 | 6.600 |
| drift | 6.100 | 2.375 | 6.675 | 6.100 |
| shift | 5.850 | 2.100 | 5.875 | 5.850 |
| sparse | 1.425 | 0.400 | 1.550 | 1.425 |
| all | 5.367 | 1.746 | 5.537 | 5.367 |

**coverage** (mean over seeds)

| family | B1 greedy | B2 no-clarification | B3 random-feasible | Method |
|---|---|---|---|---|
| cold_start | 0.327 | 0.070 | 0.330 | 0.327 |
| delayed | 0.383 | 0.156 | 0.384 | 0.383 |
| development | 0.387 | 0.158 | 0.387 | 0.387 |
| drift | 0.387 | 0.158 | 0.387 | 0.387 |
| shift | 0.387 | 0.159 | 0.389 | 0.387 |
| sparse | 0.160 | 0.051 | 0.159 | 0.160 |
| all | 0.338 | 0.125 | 0.339 | 0.338 |

**ask cost** (mean over seeds)

| family | B1 greedy | B2 no-clarification | B3 random-feasible | Method |
|---|---|---|---|---|
| cold_start | 233.250 | 0.000 | 233.250 | 233.250 |
| delayed | 189.750 | 0.000 | 189.750 | 189.750 |
| development | 189.750 | 0.000 | 189.750 | 189.750 |
| drift | 189.750 | 0.000 | 189.750 | 189.750 |
| shift | 189.750 | 0.000 | 189.750 | 189.750 |
| sparse | 185.400 | 0.000 | 185.400 | 185.400 |
| all | 196.275 | 0.000 | 196.275 | 196.275 |

**missing feedback** (mean over seeds)

| family | B1 greedy | B2 no-clarification | B3 random-feasible | Method |
|---|---|---|---|---|
| cold_start | 39.650 | 5.300 | 40.100 | 39.650 |
| delayed | 45.350 | 14.550 | 47.700 | 45.350 |
| development | 48.900 | 14.550 | 48.600 | 48.900 |
| drift | 48.900 | 14.550 | 48.650 | 48.900 |
| shift | 48.850 | 15.600 | 48.550 | 48.850 |
| sparse | 11.500 | 3.650 | 11.650 | 11.500 |
| all | 40.525 | 11.367 | 40.875 | 40.525 |

**median first wait (days)** (mean over seeds)

| family | B1 greedy | B2 no-clarification | B3 random-feasible | Method |
|---|---|---|---|---|
| cold_start | 7.100 | 0.000 | 6.850 | 7.100 |
| delayed | 4.050 | 0.000 | 4.100 | 4.050 |
| development | 4.050 | 0.000 | 4.150 | 4.050 |
| drift | 4.050 | 0.000 | 4.200 | 4.050 |
| shift | 4.100 | 0.000 | 4.450 | 4.100 |
| sparse | 4.250 | 0.053 | 4.050 | 4.250 |
| all | 4.600 | 0.008 | 4.633 | 4.600 |

**inference s / episode** (mean over seeds)

| family | B1 greedy | B2 no-clarification | B3 random-feasible | Method |
|---|---|---|---|---|
| cold_start | 20.173 | 18.417 | 17.051 | 18.304 |
| delayed | 16.116 | 17.226 | 16.723 | 18.184 |
| development | 15.993 | 19.016 | 16.827 | 18.032 |
| drift | 18.812 | 17.986 | 15.879 | 16.990 |
| shift | 19.481 | 18.213 | 16.849 | 17.948 |
| sparse | 18.976 | 18.890 | 17.389 | 18.978 |
| all | 18.259 | 18.291 | 16.787 | 18.073 |

**Method minus B1 greedy, paired by seed** (mean [95% bootstrap interval], wins/ties/losses)

| family | MSMI/100 | mutual/100 | coverage | ask cost |
|---|---|---|---|---|
| cold_start | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 |
| delayed | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 |
| development | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 |
| drift | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 |
| shift | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 |
| sparse | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 | +0.000 [+0.000, +0.000] 0/20/0 |
| all | +0.000 [+0.000, +0.000] 0/120/0 | +0.000 [+0.000, +0.000] 0/120/0 | +0.000 [+0.000, +0.000] 0/120/0 | +0.000 [+0.000, +0.000] 0/120/0 |
