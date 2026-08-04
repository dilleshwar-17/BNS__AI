# Backend Pre-Deployment Load Test Report

- **Generated**: 2026-08-03 11:33:59
- **Users seeded**: 30
- **Concurrency (rise)**: windowed
- **Duration**: 8.0s
- **Requests**: 35
- **Succeeded**: 35 (100.0% of total)

## Throughput

- **Requests per second**: 4.4

## Latency (ms)

| Metric | Value |
|--------|------:|
| p50 | 3862 |
| p95 | 6739 |
| p99 | 6,740 |
| min | 209 |
| mean | 3,716 |

## Errors

- **Failed requests**: 0

## Endpoint breakdown (by count)

| Endpoint | Requests | Errors | Avg ms | p95 ms |
|----------|---------:|-------:|-------:|-------:|
| cases.create | 6 | 0 | 6578 | 6740 |
| research.sessions | 5 | 0 | 4312 | 6420 |
| retrieval.search | 5 | 0 | 5270 | 6587 |
| drafting.types | 4 | 0 | 521 | 1361 |
| pleadings.types | 4 | 0 | 2156 | 3862 |
| retrieval.health | 3 | 0 | 2636 | 4290 |
| cases | 3 | 0 | 3830 | 6428 |
| reports.types | 2 | 0 | 900 | 1590 |
| auth.me | 2 | 0 | 3313 | 4649 |
| documents.list | 1 | 0 | 4159 | 4159 |

## Outcome

**Zero errors. Backend sustained the load without failure.**
