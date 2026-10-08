# Oral script: supervisor meeting (`Meeting_revised.pptx`)

How to use this script:

- Slides 1–31 form the talk. Each has a full spoken script and a target duration; the total is about 45 minutes.
- Slides 32–55 are the appendix. Each has a short answer to use only if a supervisor asks about that topic.
- Text in *[brackets]* is a stage direction, not something to say.
- Page numbers refer to the PDF pages of the surveys.

---

## Part A–C: where I stand

### Slide 1 — Title (≈ 0:45)

Good morning, and thank you for your time.

Today's meeting has a slightly different purpose from a usual progress update. I want to use it to make decisions.

I will cover three things:

- what the three recent surveys I read imply for my thesis;
- an honest audit of my rejected Offline Safe-CQL paper, including what the reviewers got right;
- the research direction and experimental set-up I propose for the next six months.

At the end I will ask you four concrete questions.

### Slide 2 — Today's storyline (≈ 1:00)

The talk has six parts, grouped in three columns.

The first column is "where I stand". It covers the research landscape from the three surveys, then the audit of my paper and of the reviews.

The second column is "what I will build". It covers the research directions I ranked, and the datasets and simulators that could support them.

The third column is "validate and decide". It covers the evaluation protocol, and the decisions I need from you.

I have deliberately not presented the three surveys one after the other. I kept only the findings that change what I should do. All the detailed survey slides from my previous version are still in the appendix if you want to go deeper.

### Slide 3 — Executive diagnosis (≈ 2:00)

If you remember only one slide, it should be this one. These are five conclusions, and the rest of the talk supports them.

**First: the data, not the algorithm, is the binding limit.** In the Colosseum dataset I used, each experiment keeps a single configuration from start to finish. My paper admits it on page 5. As a consequence, the data never shows what happens when the controller switches from one configuration to another. Lu et al. make exactly this point about KPM-only traces on page 48.

**Second: "safe" in my paper means something narrow.** It means a constrained-MDP constraint, satisfied on average, and measured with off-policy proxies. There is no tail guarantee, no per-window guarantee and nothing at deployment. On top of that, my own Fig. 3 shows that the Lagrange multiplier had not converged.

**Third: a static configuration might do as well as my agent.** In my own Fig. 1, the configuration with 39 eMBB PRBs and round-robin stays within the 3 % budget at every load level. I have to test that first.

**Fourth: two positioning errors are cheap to fix.** A 5-second decision step is a Non-RT loop, not Near-RT. And a 20-millisecond slice with 97 % reliability is not URLLC.

**Fifth: the direction I propose for the thesis core.** It is constrained offline-to-online learning, on decision logs I generate myself in ns-3 5G-LENA.

The takeaway: fix the claims now, and move the RL contribution to data I can control.

### Slide 4 — Three complementary surveys (≈ 1:15)

These are the three surveys. Each one looks at the problem through a different lens.

**Haque et al., IEEE Communications Surveys and Tutorials, 2025.** It tells us what must be guaranteed: URLLC requirements across PHY, MAC and cross-layer design, with ML and 6G perspectives.

**Lu et al., an arXiv survey from 2026.** It tells us how a learning agent can actually control the RAN in O-RAN: MDP modelling, offline and safe RL, and the path from training to deployment.

**Adhikari et al., IEEE Access, 2024.** It is about how eMBB and URLLC share the same resources, which is exactly my application setting.

I will now show only the few findings from each survey that matter for my decisions. Their full structure maps are in the appendix, on slides 32 to 34.

### Slide 5 — URLLC as a family of requirements (≈ 1:15)

From Haque et al., one point matters most.

URLLC is not a single requirement but a family of latency and reliability points that depends on the use case. The table on the left shows the range: from 1 millisecond at 99.9999 % for discrete automation, to tens of milliseconds for process monitoring.

The baseline 3GPP target is 1 millisecond at 1 minus 10 to the minus 5. The survey also stresses why this is hard:

- short packets lose coding gain;
- redundancy costs latency;
- end-to-end latency includes queuing, processing and the core network, not just the radio link.

Here is why this matters for me. The slice called "URLLC" in my paper uses a 20-millisecond threshold, and I allowed 3 % violations. That is 97 % reliability. It is a latency-sensitive slice, not a URLLC-grade service, and I need to say so in the revision.

### Slide 6 — ML for URLLC (≈ 1:00)

Haque et al. classify ML for URLLC into four families:

- supervised learning, to predict events before they happen, such as decoding failures or URLLC arrivals;
- unsupervised learning, including a DNN trained with a primal-dual method that learns Lagrange multipliers. That is conceptually close to my Lagrangian approach, but it learns a static allocation, not a sequential policy;
- reinforcement learning, for bandwidth sharing and puncturing;
- federated RL, including coordination of two O-RAN xApps.

The takeaway: the RL works reviewed here are all trained online in simulation. None of them learns from network logs under a URLLC constraint.

### Slide 7 — Offline RL and constrained RL (≈ 1:30)

This slide from Lu et al. contains the two technical ingredients of my paper.

**On the left, offline RL.** The policy learns only from a fixed dataset collected by some behaviour policy. The central risk is distribution shift: the critic overestimates actions that the dataset barely contains, and bootstrapping amplifies the error. CQL, the method I used, answers this by pushing down the Q-values of unsupported actions.

**On the right, constrained MDPs with a Lagrangian.** Keeping the SLA as an explicit constraint avoids hand-tuned penalty weights.

The limit, written explicitly by Lu on page 11, is important for me: a Lagrangian method satisfies the constraint only in expectation, and only at convergence.

So, the revised takeaway. Training offline protects users while the policy is learning. But the final constraint still holds only on average, and only on the data's support. This is exactly where my safety claim stops.

### Slide 8 — O-RAN as the DRL environment (≈ 1:15)

This slide shows where a learning agent sits in O-RAN, and at what timescale:

- the Non-RT RIC runs rApps with loops longer than 1 second;
- the Near-RT RIC runs xApps between 10 milliseconds and 1 second;
- dApps, still at research stage, act below 10 milliseconds inside the DU.

This is the slide where Reviewer 2 is simply right. In my paper, the agent decides every 5 seconds. According to Lu, page 14, a 5-second loop is a Non-RT loop, an rApp, not a Near-RT xApp.

I have two options:

- present it honestly as an rApp that configures slices through A1 or O1;
- redesign the loop for 1 second or less.

I will come back to this choice at the end.

### Slide 9 — Turning RAN problems into MDPs (≈ 1:00)

Lu et al. compare DRL papers along five dimensions:

- the decision model;
- the observations;
- the actions;
- the reward and constraints;
- the temporal structure.

Their key evidence is PandORA. Changing only the reward, the action space or the decision period changes which DRL agent comes out best. In other words, the formulation matters as much as the algorithm.

This is where Reviewer 1's Markov comment belongs. My state excludes the current configuration. And in my logs the configuration never changes within an experiment, so the previous action cannot be learned from. I must state my decision model explicitly: either a contextual bandit or a POMDP with history.

### Slide 10 — From training to deployment (≈ 1:00)

Lu et al. distinguish three training strategies:

- offline, from logs;
- online, but only in simulators, emulators or testbeds, never on a live network;
- hybrid, which pre-trains offline or in simulation, then adapts under constraints and safety shields.

The recommended pipeline is at the bottom: network logs, then offline pre-training, then off-policy evaluation, then shadow mode, then constrained fine-tuning with a shield.

My paper covers only the first three boxes. The survey's first research direction is precisely the full pipeline: conservative offline RL followed by constrained online fine-tuning. Keep this picture in mind; it becomes my proposal later.

### Slide 11 — Open challenges, and the opening for my thesis (≈ 1:15)

Adhikari et al. list five open challenges for eMBB and URLLC coexistence:

- under-utilisation when resources are reserved for sporadic URLLC traffic;
- missing low-complexity models;
- eMBB loss that can only be minimised, which calls for joint optimisation;
- the costs of RIS and UAV helpers;
- the validity of ML results, since DRL is better but complex and tied to simulators.

On the right is my position. Safe-CQL is a joint, low-complexity, 8-action policy, learned offline, with the latency constraint explicit.

The bottom of the card shows what the audit adds to that claim:

- I learned from static configuration logs, so only one-step effects are supported;
- the constraint is met on average, not per window or on the tail;
- offline work in O-RAN does exist outside these surveys, namely Yang et al. 2024 for slicing and 2OffRAN in 2025 for handover.

So the claim "nobody learns from logs" is only true within these three surveys.

### Slide 12 — Three lenses, one table (≈ 1:30)

This table compresses the three surveys into what drives my decisions.

- **Haque** defines the target. It is the reason I must call my slice latency-sensitive rather than URLLC.
- **Lu** gives me the architecture, the timescales and the data requirements. It supports Reviewer 2 on both the timescale and the static data, and its future directions set my core proposal.
- **Adhikari** tells me which coexistence assumptions I must state. It also says to report results across loads, and it gives a natural baseline, Alsenwi et al., a DRL approach with URLLC constraints, trained online.

One caveat, for honesty: absence from a survey is not a research gap. Before claiming novelty, I must cite and compare with Yang et al. and 2OffRAN, which are outside these surveys.

### Slide 13 — Four implications for my research decisions (≈ 1:45)

Here is my own synthesis: four implications.

**One: configure, don't schedule.** URLLC decisions in Haque and Adhikari happen at the millisecond or mini-slot scale, and RIC loops start at 10 milliseconds. So an xApp or rApp cannot schedule URLLC packets. It can only set the slice quotas and scheduler policies that shape the URLLC latency tail. That is the honest framing for my work.

**Two: keep constraints explicit, and on the tail.** I should constrain the probability that latency exceeds the threshold, or a CVaR, instead of a window-average violation rate.

**Three: data must be decision-centred.** Lu requires logs with state, action, reward, next state, timing and context, plus the behaviour policy and the control location. KPM-only traces can calibrate a simulator, but they cannot train a sequential policy.

**Four: report across loads and seeds,** because URLLC performance depends on its own load, and the formulation can change which method wins.

Put together: a configuration-level controller, with tail constraints, trained on decision logs I generate myself.

---

## Part D–E: my paper, the audit and the reviewers

### Slide 14 — Offline Safe-CQL: what was built (≈ 1:45)

A quick reminder of the rejected paper.

The pipeline at the top has five steps:

1. I used the Colosseum commercial-traffic twinning traces, about 225,000 transitions.
2. I audited them and found that the MAC scheduler, not the PRB split, drives the URLLC latency tail.
3. I formulated a constrained MDP: maximise eMBB throughput subject to an average violation rate of at most 3 %.
4. I trained CQL with a tabular cost model per action and load level, and an adaptive Lagrange multiplier.
5. I evaluated on a held-out cluster with three off-policy estimators.

On the left are the formulation details. The state has 12 KPM features, without the current configuration. There are 8 actions: four PRB splits times two schedulers. The step is 5 seconds, with gamma 0.7. The cost is the share of URLLC packets above 20 milliseconds.

On the right is Table II. Safe-CQL reaches a cost of 0.030, against 0.040 to 0.057 for the baselines, for 1 to 2 % less throughput. That is the claim of 25 to 47 % fewer violations.

Please notice two details. Safe-CQL has 2 seeds while the others have 5, and its cost sits exactly at the budget. I will come back to both.

### Slide 15 — Claim audit (≈ 1:45)

Before looking at the reviews, I audited my own paper as a reviewer would. I went claim by claim.

- **"No unsafe exploration during training": supported.** The policy is trained only on logs.
- **"25 to 47 % fewer violations": partly supported.** The numbers come from off-policy proxies, with two seeds and no confidence intervals.
- **"Lambda converges near 12.9": not supported by my own figure.** In Fig. 3, lambda is still rising at epoch 100 and the training cost is still around 0.032, above the 0.03 budget.
- **"Near-RT xApp": not supported,** because of the 5-second step.
- **"URLLC SLA": overstated.** The threshold is 20 milliseconds, the budget 3 %, on an LTE testbed.
- **"Sequential RL is needed": not shown.** The cost is treated as immediate, and no action switch exists in the data, so a contextual-bandit formulation may be the honest one.
- **"Beats simple rules": untested.** There is no static baseline.

In short, the strongest claims rest on proxies and on a missing baseline.

### Slide 16 — What "safe" means in Safe-CQL (≈ 1:30)

The word "safe" was at the centre of the criticism, so I want to be precise about it.

The ladder on the left goes from weak to strong meanings of safety.

- **Yes:** the constraint is inside the optimisation.
- **Yes:** users are not exposed during training, because it is offline.
- **Partly:** the constraint is met on held-out data, but only on average and through proxies.
- **No:** a converged primal–dual solution.
- **No:** any per-window or tail guarantee.
- **No:** any safety at deployment, because there is no shield, no fallback and no online test.

I also want to answer one likely question now. CQL by itself is not a safety mechanism. It is conservative about value estimates, which reduces extrapolation error, but it does not bound constraint violations.

So I propose the wording on the right: "constraint-aware offline policy learning with empirical, average-case constraint satisfaction on held-out traces". It is less attractive, but it is defensible.

### Slide 17 — Reviewers 1 and 2 (≈ 2:00)

Now the reviews. I did not simply accept every comment; for each one I give a verdict.

**Reviewer 1, first comment.** My state drops the current PRB split and scheduler, so the Markov property is violated. Formally, this is right. But calling it a "fatal flaw" is overstated. And the proposed fix, adding the previous action to the state, is impossible on these logs, because the previous action always equals the current one. Partly justified.

**Reviewer 1, second comment.** The tabular cost over load bins is too coarse for URLLC tails. Partly justified. The tabular model is robust for rare events, but a window-average violation rate is indeed not a tail metric. I would contest one part, though: the KPMs arrive at about 4 Hz, so high-resolution channel dynamics are not observable in this dataset anyway.

**Reviewer 2, first comment.** Five-second steps are Non-RT. Justified.

**Reviewer 2, second comment.** The data is static: the configuration is fixed per experiment, so the causal effect of decisions is not captured. Justified, and it is the most critical comment. My paper even admits it on page 5.

My reading is that Reviewer 2's static-data point is the root cause, and Reviewer 1's Markov point follows from it.

### Slide 18 — Reviewer 3 (≈ 1:15)

Reviewer 3 raised three points.

- **Only a behaviour-cloning baseline: justified.** Unconstrained CQL is an ablation, not a competitor. I need static rules and existing safe offline RL methods such as BCQ-Lagrangian, CPQ and COptiDICE.
- **Novelty is incremental: justified.** My own paper says the algorithm is not novel.
- **Writing errors: justified for what I can see.** Section V-B starts with the fragment "gamma equals 0.7, Fig. 2", and there are inconsistencies between the text and the figures. The missing reference he mentions is not in my copy, so he may have reviewed a different version.

On the right are the scores. The technical scores, 3, 2 and 2, agree across reviewers; only the presentation score varies widely. So the paper needs new evidence, not just rewriting.

### Slide 19 — Root cause: static logs (≈ 1:45)

This slide explains the core scientific problem visually.

The first two rows are what the logs contain. Each reservation keeps one configuration for its whole duration, for example (21, PF) all the way, or (39, RR) all the way.

The third row is what a learned policy actually does. It switches configuration from one window to the next. Each red question mark is a transition that never appears in 1,116 reservations. Its effect, and therefore its value, is extrapolated.

On the right, I separate what the traces can and cannot support.

- **They support:** association between configuration, load and KPIs; the dominance of the scheduler on the latency tail within the logged configurations; and one-step policy value on the logged support.
- **They cannot support:** transitions after a switch, off-policy evaluation of switching policies, and causal claims, because configuration and load are confounded.

As Lu writes: "a static set of KPMs is not enough to reconstruct a sequential decision problem."

So I should use these traces for one-step analysis and calibration, and train sequential policies on data with logged switches.

### Slide 20 — A missing baseline (≈ 1:45)

This is the most uncomfortable slide, and probably the most important one.

The table reproduces my own Fig. 1: the URLLC violation rate for each action and each load level. Green means within the 3 % budget.

Look at the highlighted row, (39, RR): 0.00, 0.02, 0.03, 0.03. It is within budget at every load level. It also gives eMBB the most PRBs. And my paper shows that throughput rises with eMBB PRBs, and that round-robin matches or beats proportional fair on throughput.

So the fixed rule "always (39, RR)" is plausibly near-optimal under my own tabular model.

I want to be clear that this is a hypothesis; I have not computed it yet. It is a one-day test: evaluate always-(39, RR), and a per-load constrained oracle, on the held-out cluster with the same estimators. If they match Safe-CQL, the RL contribution of this paper disappears, and the paper becomes an audit paper.

Before adding any algorithm, I must check that learning beats the best fixed configuration.

### Slide 21 — Prioritised revision plan (≈ 1:30)

Here is the revision plan, ordered by importance and cost.

**P0, this month:**

- the static and oracle baselines, which decide the paper's fate;
- the repositioning: rApp or slow xApp, "latency-sensitive slice", and a qualified notion of "safe".

**P1, answering the reviewers directly:**

- make the decision model explicit, contextual bandit versus constrained MDP;
- add the safe offline RL baselines through the OSRL library;
- use at least five seeds for every method, with bootstrap confidence intervals;
- fix the Fig. 3 claim and state the hyperparameter-selection protocol.

**P2:**

- a state-conditional cost model with tail metrics;
- a full proofreading pass.

**P3:**

- generate data with configuration switches in ns-3 5G-LENA, which is the bridge to the thesis core.

To summarise the logic: if P0 shows that the static rule matches Safe-CQL, the paper becomes an audit paper and the reinforcement-learning contribution moves to simulation.

---

## Part F: research directions

### Slide 22 — Positioning matrix (≈ 1:15)

This matrix places the paper against six research directions from the surveys.

- **Offline RL for O-RAN:** addressed directly, but limited by static configurations.
- **Safe and constrained RL:** addressed with a constrained MDP, but with a mean-rate, myopic cost and no shield.
- **eMBB/URLLC coexistence:** addressed at slice level, but on LTE, with 20 milliseconds and no mini-slots.
- **RIC timescale:** the paper claims Near-RT, but it is Non-RT.
- **Offline-to-online adaptation:** not addressed at all, and that is my opportunity.
- **Benchmarks and reproducibility:** weak, with two to five seeds and no released code.

In one sentence: I addressed offline RL with a constraint, but not switching dynamics, tails, the right timescale or offline-to-online learning.

### Slide 23 — Ranked research directions (≈ 1:30)

I scored four candidate directions from 1 to 5 on five criteria: novelty, importance, feasibility, credibility and alignment with my current work.

**First, with 20 points:** constrained offline-to-online slice-configuration control with tail-latency constraints.

**Second and third, with 18 points:**

- the honest revision of Safe-CQL, which is very feasible but has limited novelty;
- a trace-calibrated ns-3 5G-LENA twin, evaluated by whether it ranks policies correctly.

**Fourth:** off-policy evaluation and support diagnostics.

I deliberately set aside some fashionable topics. Multi-xApp MARL is premature. LLM-based control is poorly aligned with my work. Mini-slot puncturing works below 10 milliseconds, outside RIC reach. RIS/UAV coexistence requires a different expertise.

The plan: do number 2 now, build number 3 as the enabler, and make number 1 the thesis core. The novelty scores are provisional until I complete a systematic literature search.

### Slide 24 — Core direction (≈ 2:00)

Here is the core direction in detail.

The research question: can a policy pre-trained on logged slice-configuration decisions be fine-tuned online with a bounded cumulative tail-latency violation, under traffic shift, faster than constrained RL trained from scratch?

I expect three contributions:

1. a generator of decision-logged datasets for eMBB and latency-sensitive traffic, with known behaviour propensities;
2. a support-aware shield, combined with a chance or CVaR latency constraint, for offline-to-online fine-tuning;
3. evidence on cumulative violations and sample efficiency against online baselines.

The formulation changes are on the right:

- a tail constraint instead of a mean rate;
- a quantile cost critic with a pessimistic estimate;
- a decision period between 100 milliseconds and 1 second, with the previous action in the state;
- a shield that only allows actions whose cost upper bound respects the budget.

The main risks:

- the simulated latency tail may not match a real testbed;
- slicing in 5G-LENA requires custom scheduler code;
- tail metrics need many packets.

And one honest failure mode: offline pre-training might bring little gain, which would still be a reportable result.

Lu names this exact pipeline as the first open direction, on page 54. My Safe-CQL work becomes its offline stage, so nothing I built is lost.

---

## Part G: data, infrastructure and protocol

### Slide 25 — Datasets (≈ 1:30)

I checked the candidate datasets against their documentation.

- **The Colosseum commercial-traffic twinning dataset**, the one I used. One base station, 50 PRBs, 8 static UEs, five PRB splits times two schedulers, three clusters, PHY/MAC KPMs plus application latency, under a CC-BY-SA licence. Actions are static per reservation.
- **The ColO-RAN dataset**, with three slices and per-slice schedulers. Also static per experiment, according to its maintainers.
- **The COMMAG dataset**, with four base stations and three slices. Also static configurations.

I also note that the "URLLC" label in these datasets is a slice ID assigned per UE, not 3GPP URLLC traffic.

So the only dataset with logged action switches is the one I would build in ns-3 5G-LENA, with the full decision tuple and behaviour propensities, as Lu recommends.

The strategy: generate decision logs in simulation, and use the real traces to drive and calibrate the traffic.

### Slide 26 — Five levels of realism (≈ 1:30)

These five levels of experimental realism are not equivalent, and I want to avoid presenting them as if they were.

1. An abstract RL environment is fast but has no PHY or MAC realism.
2. A trace-driven environment uses real data but has no counterfactuals. That is where my current paper is.
3. A calibrated simulator, ns-3 with 5G-LENA and trace-driven traffic, gives counterfactuals and NR models. That is the minimum for the next paper.
4. A simulator connected to a real RIC over E2, with NORI or ns-O-RAN, adds real interfaces and loop delays. That would strengthen a journal version.
5. A software or physical testbed, with srsRAN, OAI or Colosseum, is the most realistic but also costly and small-scale.

One important point: claiming O-RAN realism at level 3 would be wrong, because 5G-LENA does not implement the O-RAN architecture.

### Slide 27 — Stage 1 set-up (≈ 1:45)

Concretely, here is the Stage 1 set-up.

**On the left, ns-3 with 5G-LENA:**

- eMBB traffic plus latency-sensitive small packets, with the load taken from the twinning traces;
- a gNB with numerology 1 or 2, two slices implemented through RB masks or bandwidth parts, and round-robin, proportional-fair or QoS schedulers;
- per-packet latency and throughput measurements.

**On the right, a Python agent:**

- a CQL-Lagrangian policy, then online fine-tuning;
- a shield;
- a logger that records every decision with its behaviour probability.

The two sides communicate through ns3-ai shared memory, or ns3-gym. Every 0.1 to 1 second, KPMs go to the agent and a PRB quota and scheduler choice come back.

At the bottom are the stages:

- Stage 0, revise the paper, now;
- Stage 1, this set-up, in months 1 to 3;
- Stage 2, offline-to-online under traffic shifts, in months 3 to 6;
- Stage 3, the E2 integration with an O-RAN RIC, in months 6 to 12.

What I have verified: 5G-LENA version 4.1 supports these schedulers and numerologies. Slicing is not built in, which is real engineering work.

This set-up produces exactly what the trace dataset lacks: decision logs with known propensities.

### Slide 28 — Evaluation protocol (≈ 1:30)

The evaluation protocol follows one rule: each claim gets its own essential comparison.

- **"Learning beats configuration rules"** needs the best static configuration, a per-load oracle and a QoS scheduler.
- **"Better than existing safe offline RL"** needs CQL-Lagrangian, BCQ-Lagrangian, CPQ and COptiDICE.
- **"The constraint matters"** needs the same method with lambda equal to zero.
- **"Offline pre-training helps"** needs constrained online RL from scratch.
- **"Each component matters"** needs ablations.

On the right are the metrics:

- eMBB throughput, mean and 5th percentile;
- latency percentiles up to p99.9, with packet counts;
- deadline-miss rate;
- the frequency and severity of violations;
- cumulative violations during fine-tuning;
- inference time.

For statistics: at least ten seeds in simulation, bootstrap confidence intervals, leave-one-cluster-out splits, and hyperparameters chosen on validation data only.

In short: separate mean performance from tail performance, and empirical safety from guarantees.

---

## Part H: decisions

### Slide 29 — Decisions and next steps (≈ 2:00)

To finish, the plan and the decisions.

**Now, within four weeks:**

- the static and oracle baselines;
- the repositioning;
- seeds, confidence intervals and the safe offline baselines;
- a systematic related-work search.

**Medium term, one to six months:**

- the 5G-LENA scenario;
- the decision-logged dataset generator;
- the trace calibration;
- the offline-to-online experiments.

**Longer term:**

- E2 integration with a RIC;
- testbed validation;
- multi-cell extensions;
- runtime assurance.

And here are the four questions I need you to answer today:

1. Should I do a quick revision of the current paper, or fold it into the simulator paper? My suggestion is to decide after the one-day static-baseline test.
2. Is the thesis scope configuration-level, rApp or xApp, or scheduling-level, dApp? I recommend configuration-level.
3. Is LTE-twinned data acceptable as main evidence in a 5G/6G thesis? I suggest using it as a traffic and calibration input only.
4. Can we get Colosseum access, or should I commit to ns-3 and NORI?

For venues, I list where comparable work appeared, ICMLCN for example, but I have not checked deadlines.

Thank you. I am happy to take your questions.

### Slide 30 — References (≈ 0:15)

*[Show briefly, do not read.]*

These are the references cited in the slides. Survey page numbers refer to the PDF pages. A few recent works, Yang et al., 2OffRAN, ns-O-RAN and NORI, I checked only at abstract level, and I will read them fully before any novelty claim.

### Slide 31 — Appendix divider (≈ 0:05)

*[Only if needed.]*

Everything after this slide is the detailed survey material from my previous version, kept unchanged in case you have questions.

---

## Appendix: answers if asked

### Slide 32 — Haque et al.: structure of the survey

This is the structure of the Haque survey. It moves from URLLC requirements and history, through verticals, design challenges and the PHY, MAC and cross-layer techniques, to machine learning and 6G research directions in Section XI.

### Slide 33 — Lu et al.: taxonomy of RL methods

This is Lu's taxonomy of RL methods. It covers model-free value-based and policy-gradient methods, model-based methods, offline RL with BCQ, CQL and IQL, safe and constrained RL, multi-agent and federated RL, meta-learning, and sim-to-real. My work sits in the offline and safe branches.

### Slide 34 — Adhikari et al.: structure of the survey

This is Adhikari's structure. It covers the basics of coexistence, namely puncturing and OMA/NOMA; resource allocation through slicing, scheduling, TTI, ML and federated learning, and RIS/UAV; the 6G applications; and the research challenges.

### Slide 35 — Why URLLC is a different kind of service

Machine-type traffic changes the requirements: VoIP tolerates 50 milliseconds, while automation needs 1 millisecond. NGMN defines reliability as the share of packets delivered within the deadline. The timeline shows how URLLC emerged from ultra-low-latency and ultra-reliable research, up to 3GPP Releases 15 to 17.

### Slide 36 — Three design challenges

Haque names three design challenges:

- control-signalling overhead, where grant-free access avoids the request-and-grant handshake;
- coexistence with eMBB, because URLLC pre-empts eMBB immediately;
- resource optimisation, where joint models of queuing delay, end-to-end delay and error probability are still missing.

### Slide 37 — PHY layer tools

Every PHY tool buys latency or reliability at some cost:

- mini-slots and wider numerologies add control overhead;
- short-packet designs make detection harder;
- polar codes increase decoding complexity;
- massive MIMO requires antennas;
- mmWave suffers from blockage.

### Slide 38 — MAC and cross-layer

Scheduling is where the trade-off is decided:

- pre-emption serves URLLC immediately while eMBB pays;
- only one HARQ retransmission fits in 1 millisecond;
- multi-connectivity gives more than ten times better outage for about twice the resources;
- classical LTE schedulers react too coarsely to deadlines.

### Slide 39 — ML is the main lever for 6G URLLC

6G raises the bar to 0.1 milliseconds and 99.99999 % reliability. Haque argues for proactive design, meaning predicted arrivals and queue trends in the state, for data-driven receivers, for fast adaptation with MAML, and for co-design of communication and control.

### Slide 40 — Why DRL for 6G AI-RAN

Lu's argument: RAN control is sequential, stochastic, partially observable and multi-objective, and it has no optimal-action labels. That makes it a reinforcement-learning problem rather than a prediction problem. O-RAN opens the control loop to such agents.

### Slide 41 — Five contributions of the Lu survey

The Lu survey contributes five things:

- an O-RAN-aware MDP framework;
- a use-case taxonomy;
- advanced methods, including foundation models;
- trustworthy DRL;
- the deployment pipeline, from sim-to-real through to RLOps.

### Slide 42 — DRL foundations

This slide covers the basics: MDP and POMDP; value-based methods such as DQN and its variants; and policy-gradient methods such as PPO, which is the most used in O-RAN, and SAC. The O-RAN-specific point is that E2 telemetry is sampled, aggregated and delayed, so a Near-RT agent faces a POMDP.

### Slide 43 — Beyond one agent and one simulator

This covers four extensions:

- multi-agent RL, with centralised training and decentralised execution;
- federated RL, either horizontal across sites or vertical across stakeholders;
- meta-RL for fast adaptation;
- the sim-to-real gap, defined as the return lost on the real network by a policy optimised in simulation.

### Slide 44 — Use cases

Lu classifies nine use-case domains. Resource management, slicing and traffic steering are the most mature. The works closest to my setting are Sohaib et al., Eskandari et al., SafeSlice and Zangooei et al., and they are all trained online.

### Slide 45 — Representative DRL formulations (Lu, Table IV)

This table gives the state, action, reward and timescale typically used for each O-RAN use case. It is useful if you ask how my formulation compares with the usual slicing formulations.

### Slide 46 — Multi-agent and federated DRL in O-RAN

Several learning xApps acting on shared resources can conflict, for example traffic steering versus energy saving. Proposed answers include hierarchical control, where an rApp sets the goals and an xApp executes, and federated learning across vendors. Game theory warns that agents that look good locally can be unstable or unfair together.

### Slide 47 — Foundation models and agentic AI

The survey positions LLMs and foundation models around DRL, not instead of it. They help with representation, intent translation and orchestration, while latency-critical radio actions stay with deterministic, auditable policies. Decision transformers and world models are another way to exploit offline logs.

### Slide 48 — Trustworthy DRL

Lu defines five dimensions of trustworthy DRL: safety, fairness, explainability, robustness and verification. The safety examples are SafeSlice and 2OffRAN, the latter being offline training validated by off-policy evaluation. The principle I take from it: limits stay explicit constraints, and the reward carries only the objective.

### Slide 49 — What the survey asks of every DRL study

Lu asks every DRL study for four things:

- a sim-to-real strategy;
- logged data with delays, context and the behaviour policy;
- reproducibility, meaning several seeds and confidence intervals;
- standards alignment, meaning actions expressible through E2 RAN Control, with a fallback.

### Slide 50 — Why coexistence deserves its own survey

eMBB and URLLC differ in traffic, priority, packet length and targets. 6G makes it harder with massive URLLC and services that need both rate and reliability. Adhikari is the first survey dedicated to their joint resource allocation.

### Slide 51 — Sharing a slot

URLLC can puncture eMBB, which means no interference but lost eMBB rate. It can also be superposed on eMBB, which shares power. NOMA is more efficient than OMA, but successive interference cancellation adds delay that conflicts with URLLC.

### Slide 52 — The rate-loss model

How URLLC load is charged to eMBB can be linear, convex or threshold-based. This is a modelling assumption that every coexistence study, mine included, should state. In my case, slices are separated by PRBs, so there is no puncturing.

### Slide 53 — Optimisation-based allocation

The approaches include optimisation, slicing, scheduling and flexible TTI. Two results to remember. Joint link adaptation and scheduling bring URLLC from 1.3 to 1 millisecond at the 99.999th percentile, for about 10 % less eMBB. And short TTIs help only at low URLLC load, which is why results must be reported across loads.

### Slide 54 — Learning-based allocation

All the learning-based coexistence works reviewed here are trained online. Alsenwi et al. is the closest to mine: DRL under URLLC constraints, keeping eMBB reliability above 90 %. Watch the vocabulary: "offline" in this survey means offline optimisation with perfect CSI, not offline RL.

### Slide 55 — Better channels and target applications

RIS improves URLLC admission and eMBB throughput, but its phase optimisation adds latency. The table shows application requirements, from 1 millisecond for factory automation to 25 milliseconds for medium-voltage smart grids. Channel improvement mainly helps eMBB; its URLLC latency cost is still unanalysed.
