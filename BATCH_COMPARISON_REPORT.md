# Per-Batch Comparison: H1 Baseline vs Structured Evolution
## FutureX Benchmark - 84 Tasks (Stride 6 from 503)

**Date:** May 1, 2026  
**Runs Compared:**
- H1 Baseline: `/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_full_evo_v2baseline/`
- Structured Evolution: `/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_structured_evo/`

---

## Executive Summary

**Overall Performance:**
- **Structured Evolution: 39.29%** (33/84 tasks)
- **H1 Baseline: 36.90%** (31/84 tasks)
- **Advantage: Structured Evolution +2.38%** (+2 tasks)

**Key Finding:** Structured Evolution provides a modest but consistent performance advantage over H1 baseline, winning 3/9 batches outright and tying on 4/9. However, this comes at a significant computational cost (4.6x longer evolution time per batch).

---

## Detailed Batch-by-Batch Results

| Batch | Date Range | H1 Score | Evo Score | Delta | Both OK | Gained | Lost | H1 Evo Time (s) | Evo Evo Time (s) |
|-------|------------|----------|-----------|-------|---------|--------|------|----------------|------------------|
| 1 | 01/08-01/17 | 30.0% (3/10) | 40.0% (4/10) | +10.0% | 3 | 1 | 0 | 444 | 6729 |
| 2 | 01/18-01/27 | 60.0% (6/10) | 60.0% (6/10) | +0.0% | 4 | 2 | 2 | 571 | 3081 |
| 3 | 01/29-03/02 | 50.0% (5/10) | 50.0% (5/10) | +0.0% | 4 | 1 | 1 | 589 | 2812 |
| 4 | 03/03-03/13 | 40.0% (4/10) | 30.0% (3/10) | -10.0% | 2 | 1 | 2 | 1105 | 2888 |
| 5 | 03/13-03/21 | 30.0% (3/10) | 50.0% (5/10) | +20.0% | 3 | 2 | 0 | 648 | 2103 |
| 6 | 03/23-03/26 | 30.0% (3/10) | 40.0% (4/10) | +10.0% | 3 | 1 | 0 | 665 | 1712 |
| 7 | 03/27-04/04 | 20.0% (2/10) | 20.0% (2/10) | +0.0% | 2 | 0 | 0 | 526 | 2453 |
| 8 | 04/05-04/10 | 50.0% (5/10) | 40.0% (4/10) | -10.0% | 3 | 1 | 2 | 499 | 2775 |
| 9 | 04/12-04/13 | 0.0% (0/4) | 0.0% (0/4) | +0.0% | 0 | 0 | 0 | 668 | 1888 |
| **TOTAL** | All dates | **36.9% (31/84)** | **39.3% (33/84)** | **+2.4%** | - | - | - | **5714** | **26439** |

---

## Cumulative Accuracy Trajectories

| After Batch | H1 Cumulative | Evo Cumulative | Delta | H1 (n/total) | Evo (n/total) | Tasks So Far |
|-------------|---------------|----------------|-------|--------------|---------------|--------------|
| 1 | 30.00% | 40.00% | +10.00% | 3/10 | 4/10 | 10 |
| 2 | 45.00% | 50.00% | +5.00% | 9/20 | 10/20 | 20 |
| 3 | 46.67% | 50.00% | +3.33% | 14/30 | 15/30 | 30 |
| 4 | 45.00% | 45.00% | 0.00% | 18/40 | 18/40 | 40 |
| 5 | 42.00% | 46.00% | +4.00% | 21/50 | 23/50 | 50 |
| 6 | 40.00% | 45.00% | +5.00% | 24/60 | 27/60 | 60 |
| 7 | 37.14% | 41.43% | +4.29% | 26/70 | 29/70 | 70 |
| 8 | 38.75% | 41.25% | +2.50% | 31/80 | 33/80 | 80 |
| 9 | 36.90% | 39.29% | +2.38% | 31/84 | 33/84 | 84 |

**Key Observation:** The gap starts at +10.0% after batch 1, then **narrows over time** to +2.38% by the end. Both systems converge, suggesting diminishing returns from structured evolution on later batches.

---

## Evolution Trajectories

### H1 Baseline Evolution

| Cycle | Batch | Batch Score | Cumulative Acc | Mutated | Evolution Time (s) | Cumulative Time (s) |
|-------|-------|-------------|----------------|---------|-------------------|---------------------|
| 1 | 1 | 30.0% | 30.00% | True | 444 | 444 |
| 2 | 2 | 60.0% | 45.00% | True | 571 | 1014 |
| 3 | 3 | 50.0% | 46.67% | True | 589 | 1603 |
| 4 | 4 | 40.0% | 45.00% | True | 1105 | 2708 |
| 5 | 5 | 30.0% | 42.00% | True | 648 | 3356 |
| 6 | 6 | 30.0% | 40.00% | True | 665 | 4021 |
| 7 | 7 | 20.0% | 37.14% | True | 526 | 4547 |
| 8 | 8 | 50.0% | 38.75% | True | 499 | 5046 |
| 9 | 9 | 0.0% | 36.90% | True | 668 | 5714 |

**Trend:** Early batch scores (batches 1-3) average 46.7%, but late batch scores (batches 7-9) average only 23.3%. This **-23.3% degradation** suggests H1's evolved tools may not be generalizing well to later tasks.

### Structured Evolution Trajectory

| Cycle | Batch | Batch Score | Cumulative Acc | Mutated | Evolution Time (s) | Cumulative Time (s) |
|-------|-------|-------------|----------------|---------|-------------------|---------------------|
| 1 | 1 | 40.0% | 40.00% | True | 6729 | 6729 |
| 2 | 2 | 60.0% | 50.00% | True | 3081 | 9810 |
| 3 | 3 | 50.0% | 50.00% | True | 2812 | 12622 |
| 4 | 4 | 30.0% | 45.00% | True | 2888 | 15509 |
| 5 | 5 | 50.0% | 46.00% | True | 2103 | 17612 |
| 6 | 6 | 40.0% | 45.00% | True | 1712 | 19324 |
| 7 | 7 | 20.0% | 41.43% | True | 2453 | 21777 |
| 8 | 8 | 40.0% | 41.25% | True | 2775 | 24552 |
| 9 | 9 | 0.0% | 39.29% | True | 1888 | 26439 |

**Trend:** Early batch scores average 50.0%, late batch scores average 20.0%. This **-30.0% degradation** is actually worse than H1's, but structured evolution maintains a slight cumulative lead due to its stronger early performance.

---

## Time-Based Performance Analysis

| Period | Date Range | H1 Accuracy | Evo Accuracy | Delta | Winner |
|--------|------------|-------------|--------------|-------|--------|
| Early (Batches 1-3) | 2026-01-08 to 2026-03-02 | 46.7% (14/30) | 50.0% (15/30) | +3.3% | **Evo** |
| Mid (Batches 4-6) | 2026-03-03 to 2026-03-26 | 33.3% (10/30) | 40.0% (12/30) | +6.7% | **Evo** |
| Late (Batches 7-9) | 2026-03-27 to 2026-04-13 | 29.2% (7/24) | 25.0% (6/24) | -4.2% | **H1** |

**Key Pattern:** Structured Evolution shows its strongest advantage in the **mid period (batches 4-6)** with +6.7% gain. However, it loses ground in the **late period (batches 7-9)** where H1 slightly outperforms by -4.2%.

---

## Task-Level Analysis

### Tasks Where Systems Differ

**Total breakdown:**
- Both systems solved: 24 tasks (28.6%)
- Only Structured Evo solved: 9 tasks (10.7%)
- Only H1 solved: 7 tasks (8.3%)
- Neither solved: 44 tasks (52.4%)

**Net advantage:** Structured Evolution gains 2 more tasks than H1 overall.

### Tasks Gained by Structured Evolution (n=9)

| Batch | Task ID | Evo Score | H1 Score | Evo Turns | H1 Turns | Evo Time (s) | H1 Time (s) | Date |
|-------|---------|-----------|----------|-----------|----------|--------------|-------------|------|
| 1 | futurex_past_0023_20260110 | 1.00 | 0.00 | 3 | 0 | 47.6 | 13.0 | 01/10 |
| 2 | futurex_past_0093_20260125 | 1.00 | 0.00 | 12 | 21 | 363.5 | 78.2 | 01/25 |
| 2 | futurex_past_0097_20260127 | 1.00 | 0.00 | 16 | 37 | 501.8 | 201.9 | 01/27 |
| 3 | futurex_past_0168_20260226 | 1.00 | 0.00 | 9 | 38 | 436.5 | 300.0 | 02/26 |
| 4 | futurex_past_0263_20260312 | 1.00 | 0.00 | 16 | 3 | 426.3 | 14.9 | 03/12 |
| 5 | futurex_past_0218_20260314 | 1.00 | 0.00 | 4 | 13 | 125.9 | 35.1 | 03/14 |
| 5 | futurex_past_0297_20260319 | 1.00 | 0.00 | 16 | 13 | 739.4 | 41.1 | 03/19 |
| 6 | futurex_past_0355_20260326 | 1.00 | 0.00 | 16 | 34 | 512.7 | 300.0 | 03/26 |
| 8 | futurex_past_0403_20260405 | 1.00 | 0.00 | 16 | 10 | 630.5 | 121.7 | 04/05 |

**Average on gained tasks:**
- Evo turns: 12.0 vs H1 turns: 18.8 (Evo is more efficient)
- Evo time: 420.5s vs H1 time: 122.9s (Evo takes 3.4x longer but succeeds)

**Pattern:** On tasks where Structured Evolution succeeds and H1 fails, Structured Evolution often uses fewer turns (12.0 vs 18.8) but takes significantly longer overall time (420.5s vs 122.9s). This suggests Structured Evolution has more sophisticated search strategies that take longer per turn but lead to success.

### Tasks Lost by Structured Evolution (n=7)

| Batch | Task ID | Evo Score | H1 Score | Evo Turns | H1 Turns | Evo Time (s) | H1 Time (s) | Date |
|-------|---------|-----------|----------|-----------|----------|--------------|-------------|------|
| 2 | futurex_past_0056_20260118 | 0.00 | 1.00 | 4 | 22 | 98.7 | 105.5 | 01/18 |
| 2 | futurex_past_0083_20260125 | 0.00 | 1.00 | 3 | 7 | 74.3 | 45.1 | 01/25 |
| 3 | futurex_past_0135_20260130 | 0.00 | 1.00 | 16 | 7 | 681.6 | 61.4 | 01/30 |
| 4 | futurex_past_0182_20260308 | 0.00 | 1.00 | 16 | 10 | 572.5 | 47.8 | 03/08 |
| 4 | futurex_past_0203_20260308 | 0.00 | 1.00 | 16 | 5 | 561.5 | 17.7 | 03/08 |
| 8 | futurex_past_0459_20260410 | 0.00 | 1.00 | 16 | 3 | 772.6 | 13.6 | 04/10 |
| 8 | futurex_past_0477_20260409 | 0.00 | 1.00 | 6 | 7 | 264.9 | 32.0 | 04/09 |

**Average on lost tasks:**
- Evo turns: 11.0 vs H1 turns: 8.7 (H1 is more efficient)
- Evo time: 432.3s vs H1 time: 46.2s (Evo takes 9.4x longer but still fails)

**Pattern:** On tasks where H1 succeeds and Structured Evolution fails, H1 is significantly more efficient (8.7 turns, 46.2s) while Structured Evolution exhausts more resources (11.0 turns, 432.3s) without success. This suggests certain task types favor H1's simpler, faster approach.

---

## Per-Batch Gain/Loss Breakdown

| Batch | Tasks | Both Correct | Gained by Evo | Lost by Evo | Net Change | Interpretation |
|-------|-------|--------------|---------------|-------------|------------|----------------|
| 1 | 10 | 3 | 1 | 0 | +1 (+10.0%) | **Evo advantage** |
| 2 | 10 | 4 | 2 | 2 | 0 (+0.0%) | Neutral |
| 3 | 10 | 4 | 1 | 1 | 0 (+0.0%) | Neutral |
| 4 | 10 | 2 | 1 | 2 | -1 (-10.0%) | **H1 advantage** |
| 5 | 10 | 3 | 2 | 0 | +2 (+20.0%) | **Evo advantage** |
| 6 | 10 | 3 | 1 | 0 | +1 (+10.0%) | **Evo advantage** |
| 7 | 10 | 2 | 0 | 0 | 0 (+0.0%) | Neutral |
| 8 | 10 | 3 | 1 | 2 | -1 (-10.0%) | **H1 advantage** |
| 9 | 4 | 0 | 0 | 0 | 0 (+0.0%) | Neutral |

**Batch-level wins:**
- Structured Evolution: 3 batches (1, 5, 6)
- H1: 2 batches (4, 8)
- Tied: 4 batches (2, 3, 7, 9)

---

## Key Findings

### 1. Overall Performance
- **Structured Evolution outperforms H1 baseline** by +2.38% (2 additional tasks solved)
- This represents a **modest but consistent advantage**
- 33/84 tasks solved vs 31/84 tasks solved

### 2. Batch-Level Consistency
- Structured Evolution wins **3/9 batches**
- H1 wins **2/9 batches**
- **4/9 batches are tied**
- Neither system shows dominant consistency

### 3. Maximum Divergence
- **Occurs at Batch 5** with a 20.0% gap (Structured Evolution advantage)
- This is the mid-period where Structured Evolution shows strongest performance
- Batch 5 covers tasks from 2026-03-13 to 2026-03-21

### 4. Evolution Trajectory Patterns
- **H1:** 46.7% (early) → 23.3% (late) = **-23.3% degradation**
- **Structured Evo:** 50.0% (early) → 20.0% (late) = **-30.0% degradation**
- Both systems show **significant performance degradation over time**
- **Tools are not generalizing well** to later tasks in either approach
- This suggests the evolution process may be **overfitting to early batches**

### 5. Time-Based Winner Pattern
- **Early period (batches 1-3):** Structured Evo by +3.3%
- **Mid period (batches 4-6):** Structured Evo by +6.7% ← **Strongest advantage**
- **Late period (batches 7-9):** H1 by -4.2% ← **H1 recovers**

### 6. Evolution Overhead
- H1 total evolution time: **5,714s (95.2 minutes)**
- Structured Evo total time: **26,439s (440.7 minutes)**
- **Ratio: 4.63x** (Structured Evolution takes 4.6x longer)
- Per-batch average: H1 = 635s, Structured Evo = 2,938s
- **Cost per additional task solved:** ~10,363s (172.7 minutes) per task

### 7. Cumulative Divergence Pattern
- Initial gap (after batch 1): **+10.0%**
- Maximum gap: **+10.0%** (after batch 1)
- Final gap: **+2.4%** (after batch 9)
- **Gap narrows over time** - systems converge
- Suggests **diminishing returns** from structured evolution on later batches

### 8. Task-Level Efficiency
- **On gained tasks (where Evo succeeds, H1 fails):**
  - Evo uses fewer turns (12.0 vs 18.8) but takes 3.4x longer
  - Suggests more sophisticated but slower search strategy
- **On lost tasks (where H1 succeeds, Evo fails):**
  - H1 is much more efficient (8.7 turns, 46.2s)
  - Evo exhausts resources (11.0 turns, 432.3s) without success
  - Suggests some tasks favor simpler, faster approaches

---

## Critical Questions & Answers

### Q1: At what point does structured evolution diverge from H1, and in which direction?

**Answer:** Structured evolution establishes an advantage **immediately in Batch 1** (+10.0% gap) and maintains superiority through the early and mid periods (batches 1-6). However, the gap **narrows over time** from +10.0% to +2.4% by the final batch. In the late period (batches 7-9), **H1 actually performs slightly better** (-4.2% delta), suggesting structured evolution's advantage is primarily in early/mid task ranges.

**Direction:** Structured evolution starts strong but **converges toward H1** as batches progress.

### Q2: Is H1's evolution improving its tools over time?

**Answer:** **No.** H1's evolution shows clear **degradation** rather than improvement:
- Batch scores decline from 46.7% average (early) to 23.3% average (late)
- Cumulative accuracy peaks at 46.67% after batch 3, then steadily declines to 36.90% by batch 9
- Every mutation was applied (all cycles show "mutated: True"), but this did not lead to improvement
- **Conclusion:** H1's tools are not generalizing; they may be overfitting to earlier batches

### Q3: Is there a pattern in which DATE RANGES either system does better?

**Answer:** **Yes, a clear temporal pattern emerges:**

| Time Period | Date Range | Winner | Delta | Interpretation |
|-------------|------------|--------|-------|----------------|
| Early | Jan 8 - Mar 2 | Structured Evo | +3.3% | Modest Evo advantage |
| Mid | Mar 3 - Mar 26 | Structured Evo | +6.7% | **Strongest Evo advantage** |
| Late | Mar 27 - Apr 13 | H1 | -4.2% | H1 recovers |

**Pattern interpretation:**
1. **Early tasks (January-February):** Structured evolution has a modest edge, possibly due to better initial tool design
2. **Mid tasks (March):** Structured evolution shows its **peak advantage** (+6.7%), suggesting its evolved structures handle mid-period complexity better
3. **Late tasks (April):** H1 **catches up and slightly surpasses** structured evolution, suggesting either:
   - H1's simpler tools generalize better to late-period tasks
   - Structured evolution's complex strategies become counterproductive on certain task types
   - Late-period tasks may favor speed/simplicity over sophistication

**Hypothesis:** The late-period reversal suggests structured evolution may be **overfitting** to early/mid patterns and losing generalization ability, while H1's simpler approach maintains (modest) consistency.

---

## Recommendations

### 1. Investigate Late-Period Performance Drop
**Priority: HIGH**

Both systems show severe performance degradation in late batches (batches 7-9). Investigate:
- Are late-period tasks fundamentally different?
- Is there concept drift in the FutureX benchmark over time?
- Are evolved tools overfitting to early batches?

**Action:** Analyze task characteristics (question types, required tools, search patterns) across time periods to identify what changes in late tasks.

### 2. Optimize Structured Evolution Overhead
**Priority: MEDIUM**

Structured evolution achieves +2.38% gain but at **4.6x the computational cost**. This is ~172 minutes of evolution time per additional task solved.

**Action:** Profile the structured evolution process to identify bottlenecks:
- Is the multi-agent architecture causing redundant work?
- Can parallel specialists share computation?
- Can we achieve 80% of the gains at 50% of the cost?

### 3. Hybrid Approach for Different Task Types
**Priority: MEDIUM**

The task-level analysis reveals:
- Some tasks favor structured evolution's sophisticated search (gained tasks)
- Other tasks favor H1's simpler, faster approach (lost tasks)

**Action:** Develop a **routing mechanism** that predicts task type and selects:
- Structured evolution for complex tasks
- H1 baseline for tasks that benefit from speed/simplicity

### 4. Address Evolution Overfitting
**Priority: HIGH**

Both systems show -23% to -30% performance drops from early to late batches, suggesting tools are not generalizing.

**Action:**
- Implement **regularization** in the evolution process
- Use **holdout validation** to prevent overfitting to training batches
- Consider **meta-learning** approaches that optimize for generalization across time

### 5. Investigate Batch 5 Success
**Priority: LOW**

Batch 5 shows the largest divergence (+20.0% for structured evolution).

**Action:** Deep-dive into what made batch 5 tasks particularly suited to structured evolution. Can we identify features that predict when structured evolution will excel?

---

## Conclusion

**Structured Evolution provides a modest but consistent advantage** over H1 baseline on the FutureX benchmark (+2.38%, 2 additional tasks). However, this comes at a significant computational cost (4.6x evolution time) and the advantage **narrows over time** as both systems show performance degradation on later batches.

**Key Takeaway:** Structured evolution is **not a silver bullet**. It excels in early/mid periods but loses its edge in late periods. The severe late-batch performance drop in both systems suggests a fundamental **generalization problem** that neither approach solves.

**Strategic Recommendation:** Focus on **addressing the late-period performance drop** rather than optimizing the structured evolution architecture further. A system that maintains consistent performance across time would be more valuable than one that achieves marginal early gains at high computational cost.

---

## Appendix: File Locations

- H1 results: `/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_full_evo_v2baseline/results.json`
- H1 history: `/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_full_evo_v2baseline/history.jsonl`
- Structured Evo results: `/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_structured_evo/results.json`
- Structured Evo history: `/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_structured_evo/history.jsonl`
- Analysis scripts:
  - `/home/ec2-user/A-EVOLVE-V2/a-evolve/analyze_batch_comparison.py`
  - `/home/ec2-user/A-EVOLVE-V2/a-evolve/detailed_batch_comparison.py`
  - `/home/ec2-user/A-EVOLVE-V2/a-evolve/task_level_analysis.py`
