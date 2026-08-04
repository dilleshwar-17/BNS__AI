# Backend Pre-Deployment Load Test Report

- **Generated**: 2026-08-03 12:06:19
- **Users seeded**: 300
- **Concurrency (rise)**: windowed
- **Duration**: 62.2s
- **Requests**: 235
- **Succeeded**: 35 (14.9% of total)

## Throughput

- **Requests per second**: 3.8

## Latency (ms)

| Metric | Value |
|--------|------:|
| p50 | 30881 |
| p95 | 58857 |
| p99 | 59,607 |
| min | 1360 |
| mean | 30,863 |

## Errors

- **Failed requests**: 200

## Endpoint breakdown (by count)

| Endpoint | Requests | Errors | Avg ms | p95 ms |
|----------|---------:|-------:|-------:|-------:|
| cases.create | 32 | 32 | 36175 | 58761 |
| reports.types | 26 | 18 | 27590 | 58857 |
| retrieval.health | 23 | 12 | 19883 | 58292 |
| documents.list | 22 | 22 | 33375 | 58447 |
| drafting.types | 21 | 14 | 25379 | 58389 |
| retrieval.search | 20 | 20 | 35243 | 59607 |
| chat.list | 20 | 20 | 36478 | 59065 |
| pleadings.types | 19 | 10 | 20437 | 58826 |
| cases | 19 | 19 | 35470 | 59695 |
| auth.me | 18 | 18 | 33971 | 58922 |
| research.sessions | 15 | 15 | 36351 | 59023 |

## Outcome

**200 errors observed** — review endpoint breakdown above.
