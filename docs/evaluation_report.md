# Evaluation Report

Evaluation of the LLM-based customer intelligence system against PDF §10 (output quality, retrieval quality, consistency).
All numbers come from `python evaluate.py`; raw results are in `eval/`.

## 1. Setup

| Item | Value |
|---|---|
| LLM | Qwen3.5-4B (Q4, via Ollama), temperature 0, thinking disabled |
| Embeddings | nomic-embed-text (via Ollama) |
| Vector DB | Chroma, cosine distance, 71 chunks from 12 policy documents |
| Hardware | MacBook Air M2, 8 GB RAM |
| Dataset | 60 hand-labeled messages (`data/messages.jsonl`) |

**Dataset composition (PDF §7):** 13 multi-intent, 13 High/Critical priority, 13 ambiguous or incomplete (≥ 10 required), 24 that require knowledge retrieval (≥ 5 required), 47 with at least one relevant policy document. It covers financial disputes, fraud, card and account issues, loans, general questions and complaints.

**Labels:** each message has expected intents and priority, set by hand. The expected routing and action were derived from those labels with the rules in `config/taxonomy.yaml`, so routing and action errors measure the LLM's extraction, not the rules.

## 2. Metrics

| PDF | Metric | How it is measured |
|---|---|---|
| §10.1 | Intent exact match | predicted intent set identical to the label |
| §10.1 | Intent precision / recall / F1 | micro-averaged over all intent labels; fairer for multi-intent messages |
| §10.1 | Priority, routing, action accuracy | predicted value equals the label |
| §10.1 | Completeness | every output field present and non-empty |
| §10.2 | Retrieval hit@1 / hit@3 | a labeled document is the first / among the top-3 retrieved chunks |
| §10.2 | Groundedness | reply cites a retrieved source file, and every number in it appears in the retrieved policy text or the customer's message |
| §10.3 | Consistency | 10 messages × 3 runs: identical intents, priority, routing and action every time |
| §10.3 | Prompt robustness | 8 reworded messages (typos, lowercase, paraphrases) must get the original's routing and action |

## 3. Results across three iterations

| Metric | v1 baseline | v2 prompt fixes | **v3 final** |
|---|---|---|---|
| Intent exact match | 66.7% | 71.7% | **73.3%** |
| Intent precision | 0.789 | 0.827 | **0.829** |
| Intent recall | **0.947** | 0.893 | 0.907 |
| Intent F1 | 0.861 | 0.859 | **0.866** |
| Priority accuracy | 73.3% | **78.3%** | **78.3%** |
| Routing accuracy | **96.7%** | 95.0% | **96.7%** |
| Action accuracy | 91.7% | 91.7% | 91.7% |
| Complete outputs | 100% | 100% | 100% |
| Replies citing a source | 100% (46/46) | 100% (51/51) | 98% (49/50) |
| Replies with no invented numbers | 100% | 100% | 100% |
| Retrieval hit@1 | 66.0% | 66.0% | 66.0% |
| Retrieval hit@3 | 83.0% | 83.0% | 83.0% |
| hit@3, "requires retrieval" subset | 83.3% | 83.3% | 83.3% |
| Consistency (stable messages) | 100% | 100% | 100% |
| Robustness (reworded cases) | 87.5% | 87.5% | 87.5% |
| Average latency | 9.6 s | 10.2 s | 10.0 s |

Retrieval does not depend on the prompt, so its numbers are identical across versions (a useful sanity check).

### What changed between versions

**v1 → v2**
- Added a priority guide to the prompt (what Critical / High / Medium / Low mean).
- Tightened the *Complaint* definition: only when anger or an escalation threat is explicit.
- Told the model to use *Unclear* only when no other intent fits.
- Added a code guard, `clean_intents()`: if *Unclear* appears next to a real intent, it is dropped.

*Effect:* the false *Complaint* labels on calm messages disappeared (precision 0.79 → 0.83) and priority improved (73% → 78%). The guard fixed a safety-critical error: a phishing victim (M012) labeled *Fraud Report + Unclear* had been sent "Request more info" instead of an escalation. But the *Unclear* wording over-corrected: the model started guessing intents for vague messages (M053, M057, M059), so routing dropped.

**v2 → v3**
- Replaced the v2 prompt sentence "use *Unclear* only when no other intent fits" with "if the message does not say what the problem is, use *Unclear* instead of guessing".
- The *Unclear* definition in `config/taxonomy.yaml` was left as in v2, so the prompt now contains both the new instruction and the older "only when no other intent fits" definition.

*Effect:* routing recovered to 96.7% and exact match reached its best value (73.3%). One vague message (M053) is handled correctly again; three (M054, M057, M059) are still guessed. The leftover v2 definition may be part of why: it still pushes the model to pick a real intent whenever one loosely fits.

Tuning stopped after v3 on purpose: every prompt change was tested on the same 60 messages, so further tuning would overfit to this set (see §6).

## 4. Error analysis (v3)

**Routing / action errors (5 of 60)**

| ID | Message | Expected | Got | Cause |
|---|---|---|---|---|
| M057 | "Something is wrong with my card or maybe the app, not sure." | Support / Request more info | Account Services / Respond | model guessed *Card Issue + Account Access* for a vague message |
| M059 | "My salary didn't come" | Support / Request more info | Account Services / Respond | model guessed *Account Information* |
| M054 | "I need to talk to someone about the transfer" | Request more info | Respond | model guessed *General Inquiry* |
| M045 | "Your customer service is terrible…" | Respond | Escalate | model rated angry complaint High → escalate rule |
| M046 | "I'm extremely disappointed. The branch staff were rude…" | Respond | Escalate | same as M045 |

M045 and M046 are arguably **label** problems rather than model errors: the priority guide added in v2 says an angry customer is High, which the model followed, but the labels (written before the guide) say Medium. The labels were deliberately not changed after seeing model output, to avoid inflating the scores.

**Intent errors** are mostly *extra* related intents that do not change routing, e.g. *Refund Request* added to a duplicate-charge complaint (M001), *Card Issue* added to ATM-fee questions (M003, M005), or *Fraud Report* added next to *Unauthorized Transaction* (M011, M016). Missed second intents (M009, M010, M027) explain the lower recall.

**Priority errors** (13) are concentrated in fraud messages (Critical vs High) and vague messages, where urgency is genuinely subjective.

**Groundedness:** no reply contained a number (fee, deadline, rate) that was not in the retrieved policy text or the customer's own message. One reply (M059) did not cite a source.

**Retrieval:** 8 of 47 messages did not have a labeled document in the top 3. These misses have not yet been analyzed individually.

## 5. Consistency and robustness

- **Consistency: 100%.** With temperature 0, the same message always produced the same intents, priority, routing and action over three runs.
- **Robustness: 7/8.** Typos, lowercase and paraphrases kept the same routing and action. The only failure was the reworded M045 ("40 minutes on hold. Your support is awful."), which, like the original, was rated High and escalated.

## 6. Limitations

- **Small, single-annotator dataset.** 60 messages labeled by one person; priority in particular is subjective.
- **Tuned on the test set.** Prompt changes were evaluated on the same 60 messages, so v3's numbers are likely optimistic for unseen messages. A held-out set would give a fairer estimate.
- **Labels predate the priority guide**, causing some disagreements that are not clear model errors (M045, M046).
- **Groundedness is a proxy.** It checks citations and numbers, not whether every sentence is supported.
- **Fictional knowledge base.** The 12 policy documents are invented ("Nova Bank"); real policies are longer and more overlapping, which would make retrieval harder.
- **Latency.** ~10 s per message on a MacBook Air (two LLM calls). Acceptable for an assistant that drafts triage for human agents, not for real-time chat.

## 7. Possible improvements

- Build a separate held-out test set and re-measure.
- Analyze the 8 retrieval misses; try larger chunks or adding the detected intent to the search query.
- Rewrite the *Unclear* definition in the taxonomy to match the v3 instruction, e.g. "the message does not say what the problem is ('it broke again', 'can you check the issue'); don't guess an intent from a vague hint". This was prepared but not evaluated, and should be measured on a held-out set rather than the same 60 messages.
- Few-shot examples in the extraction prompt (taken from outside the evaluation set) for vague messages.
- Re-label priority with a second annotator using the written priority guide.
- A larger model on a GPU server for better extraction, measured with the same `evaluate.py`.
