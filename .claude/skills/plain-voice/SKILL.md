---
name: plain-voice
description: Strip LLM-tell vocabulary, phrase patterns, and structural tics out of any prose Claude writes — papers, grants, blog posts, talk scripts, slide text, emails, manuscripts, op-eds, abstracts, letters, any free-text deliverable. Use whenever Claude is about to generate prose for Marine OR whenever Marine asks Claude to edit, review, audit, humanize, or "check for AI sound" in a draft. Trigger on phrases like "write a draft", "edit this", "does this sound AI", "humanize this", "review my draft", "rewrite", or any prose-generation task — even when LLM detection isn't explicitly mentioned. Encodes Kobak et al. (2025, Science Advances) excess vocabulary, Juzek & Ward (2025, COLING) focal words, the Wikipedia "Signs of AI writing" registry, Marine's manual additions (paradigm-shift, cadence, tapestry, testament, navigate, etc.), and hyphen-discipline rules. Apply silently — do not narrate the filtering. Default to this skill whenever in doubt about whether a draft sounds machine-written.
---

# plain-voice

A filter for the words, phrases, rhythms, and punctuation tics that make prose read as AI-written. Apply it silently — Marine should get the cleaned output, not a meta-commentary about LLM tells.

## Why this exists

Marine's voice is figure-first, claim-direct, founder-shaped. Every word in this list dilutes that. The empirical case is overwhelming — Kobak et al. analyzed 15M PubMed abstracts and found that 66% of 2024 excess style words were verbs and 14% adjectives, almost all stylistic rather than content-bearing. These words are not wrong English; they are a register that signals "this was processed by a language model." Even when they appear in human-edited text, they flatten the writer's voice toward a global average. Marine's writing should sound like Marine, not like the average of every PubMed abstract since 2023.

## The core move

When generating any prose deliverable, scan the output mentally before producing it. For each candidate word from the Tier-1 list below, ask: **is this word doing structural work in the sentence, or is it ornament?** If ornament, cut it or replace with the plain English equivalent. If structural, leave it — `crucial` is sometimes the right word for a critical-path dependency, `pivotal` is sometimes the right word for a hinge moment. The skill is not a global find-and-replace; it is a register correction.

When auditing an existing draft (Marine pastes prose and asks for review), produce the corrected draft directly. Mark inline the words you changed only if she asked for diff-style review. Default: produce the rewrite, and at the end mention how many tells were caught.

## Tier 1 — Strong tells (always flag)

These are the words that appeared with >300% increase in PubMed 2020→2024 (Juzek & Ward 2025) plus the highest-confidence markers from Kobak et al. (2025) and the post-2024 era list from the Wikipedia "Signs of AI writing" registry. If one of these appears in a draft, default to replacing it.

**Verbs (and their inflections):** delve, delves, delving, delved, showcase, showcases, showcasing, showcased, underscore, underscores, underscoring, underscored, emphasize, emphasizes, emphasizing, leverage, leverages, leveraging, harness, harnesses, harnessing, garner, garnered, garnering, bolster, bolsters, bolstered, bolstering, foster, fosters, fostering, elucidate, elucidates, elucidating, surpass, surpasses, surpassing, surpassed, navigate (figurative), navigates, navigating, embark, embarks, embarking, unveil, unveils, unveiling, unveiled, shed (light on), unpack, dive (into), comprehend, comprehends, comprehending, encompass, encompasses, encompassing, exemplify, exemplifies, illuminate, illuminates, accentuate, accentuates, demonstrate, demonstrates (when it could just be "show")

**Adjectives:** intricate, meticulous, pivotal, crucial, vital, essential, paramount, profound, compelling, groundbreaking, transformative, revolutionary, unparalleled, unprecedented (when not literally true), comprehensive, exceptional, nuanced, multifaceted, robust, vibrant, dynamic, holistic, seamless, formidable, remarkable, noteworthy, notable, invaluable, key (as filler), commendable, dependable, distinctive, foundational, impactful, innovative, quintessential, breathtaking

**Nouns:** realm, landscape, tapestry, testament, paradigm, paradigm shift, paradigm-shift, mosaic, symphony, journey, lens, era, plethora, myriad, kaleidoscope, treasure trove, epitome, intricacies, advancements, insights, complexities, nuances, interplay, exploration, endeavor, endeavors, framework (as filler), avenue, avenues, cadence (when used as ornament for "rhythm" or "pace")

**Adverbs:** meticulously, intricately, seamlessly, swiftly, notably, particularly, profoundly, exceptionally, remarkably, fundamentally

For the full 434-word style list from Kobak et al. (2025), see `references/kobak-full-list.md`. For the Tier-2 weak-tell list (words humans use that LLMs overuse), see `references/strong-tells.md`. For a programmatic grep list, see `assets/tell-words.txt`.

## Tier 2 — Phrase patterns (always cut or rewrite)

Single-word filters are necessary but not sufficient. The phrase-level constructions below are stronger AI tells than any single word, because they reproduce a rhetorical *shape* rather than just vocabulary.

**Negative parallelism (the strongest current marker):**
- "It's not X, it's Y" / "It's not just X, but Y" / "More than just X, it's Y" → just state Y directly.

**Hedge preambles:**
- "It's important to note that..." → cut.
- "It's worth noting that..." → cut.
- "It's crucial to consider..." → cut.
- "It is widely believed that..." → cut or attribute.
- "Generally speaking..." → cut.
- "While this may vary..." → cut.

**Generic openers (especially as first sentence):**
- "In today's [adjective] landscape..."
- "In an increasingly [adjective] world..."
- "In the digital age..."
- "In the realm of..."
- "In an era where..."
- "As we navigate the complexities of..."

**Wrap-up sentences (the "testament" closer):**
- "X stands as a testament to..."
- "X represents a paradigm shift in..."
- "Ultimately, X underscores the importance of..."
- "X is more than just Y; it is Z."
- "Moving forward, ..." / "In conclusion, ..."
- The "complimentary summary" — any sentence that ends a paragraph by praising or summarizing what was just said is suspect.

**Metaphor clichés:**
- "the rich tapestry of..."
- "a treasure trove of..."
- "through the lens of..." (often) — sometimes the right metaphor, but flag for review.
- "at the heart of..."
- "the cornerstone of..."
- "navigate the complexities/uncertainty/landscape of..."
- "shed light on..."
- "speaks volumes" / "speaks to" (figurative)
- "the intersection of..." (when not literally about intersection)

**Tricolon (rule of three):**
- "X, Y, and Z" lists that are perfectly balanced in length and grammatical form. Humans use tricolons too — the tell is when they appear with mathematically even cadence as the climax of every other paragraph. When you find a tricolon, ask: does it earn its rhythm, or is it filler? If filler, prune to one or two items, or replace with an asymmetric structure.

## Tier 3 — Structural and cadence tics

This is what Marine means when she says "cadence". Reinhart et al. (2025, *PNAS*) showed LLM prose has more nominalizations, fewer human subjects, and fewer epistemic stance markers than human writing. Beyond word choice, the *rhythm* gives it away.

**One-sentence dramatic paragraphs.** "Six months ago, this was impossible. Now it isn't." This rhythm — clipped, declarative, theatrical — comes from training on speech transcripts (podcasts, TED talks, marketing copy). It belongs in spoken word, not on the page of a paper or a grant. Default to paragraphs of 3-5 sentences. Use one-sentence paragraphs sparingly and only when the sentence carries real weight.

**Mathematically even sentence lengths.** Humans write in bursts and trails. Sentences run 6 words, 24 words, 11 words, 38 words — the variation is the voice. LLMs default to 18-24 words and stay there. When generating prose, vary sentence length deliberately. If three sentences in a row are within ±3 words of each other, break the pattern.

**Em-dash overuse.** One em-dash per paragraph is plenty. Two is suspect. Three is a tell. Em-dashes are not commas — use them for genuine interruption or emphatic aside, not as a rhythmic filler. When in doubt, prefer comma, colon, or period.

**Excessive markdown structure.** Bullet lists for everything, bold mid-sentence for emphasis, headers every two paragraphs. For Marine specifically: prefer prose. Use bullets only when items are genuinely parallel and discrete (an actual checklist), use bold sparingly, use headers only for documents with real sections.

**The "balanced perspective" tic.** "On one hand... on the other hand..." applied to every question, even ones with a clear answer. Marine has opinions; she should state them. If she's drafting an opinionated piece (op-ed, blog, NSF concept note pitching a position), do not water it down with reflexive balancing.

**Wrap-up paragraphs that summarize and praise.** LLMs love to end any piece with a paragraph that recaps what was just said and gestures at its importance. Most pieces don't need this. End on the strongest concrete point, not a meta-summary.

## Hyphen discipline

LLMs over-hyphenate compound modifiers and apply hyphens in positions where current style guides drop them. Marine specifically called this out. The rules:

**Keep the hyphen when:** the compound is a modifier directly before a noun.
- "data-driven approach" ✓
- "real-world data" ✓
- "high-resolution image" ✓
- "long-term project" ✓
- "well-known scientist" ✓
- "state-of-the-art method" ✓ (always — multi-word compound)

**Drop the hyphen when:** the compound is in predicate position (after the noun) and the meaning is unambiguous.
- "the approach is data driven" (some guides keep it; Marine drops it)
- "the data are real world" → recast: "the data come from real-world deployments"
- "the image is high resolution" → drop hyphen
- "this is well known" ✓ no hyphen
- "the project is long term" → drop hyphen

**Prefer the closed form** for established compounds — LLMs over-hyphenate these:
- groundbreaking (not ground-breaking)
- longstanding (not long-standing)
- ongoing (not on-going)
- nonlinear (not non-linear)
- multidisciplinary (not multi-disciplinary)
- subfield (not sub-field)
- realtime (not real-time, in technical contexts) — but "real-time monitoring" stays hyphenated as a modifier
- pretrained (not pre-trained)
- finetune, finetuning (not fine-tune in technical contexts; field is split)
- workflow (not work-flow)

**Never hyphenate** adverb-adjective compounds ending in -ly:
- "highly accurate model" (not "highly-accurate model")
- "rapidly evolving field" (not "rapidly-evolving field")
- "newly developed algorithm" (not "newly-developed algorithm")

**The paradigm-shift case specifically.** "Paradigm shift" — when it survives the Tier-1 filter at all (rarely should) — takes no hyphen as a noun: "a paradigm shift in seismology". As a modifier before a noun, it would take one: "a paradigm-shift moment". But default: cut the phrase entirely, since it's a cliché in any form.

## Marine's voice — what to keep

The point of all this isn't a sterile, stripped-down prose. Marine's voice has positive features that should stay:
- Specific, concrete nouns (not abstractions). "Nisqually liquefaction twin" beats "the geohazard system."
- Active verbs that name what was actually done. "We built X" beats "X was developed."
- Numbers where numbers belong. "15 million abstracts" beats "a vast corpus."
- One claim per sentence; one main idea per paragraph.
- Variable sentence length. Short. Then long, with subordinate clauses that carry the argument forward. Short again.
- Direct opinions when she has them. "I don't believe X" beats "Some have questioned X."
- French rhythm influence is welcome — slightly longer sentences with more subordination than American English defaults, but punctuated by short emphatic ones.

## Audit workflow (when Marine pastes a draft)

When Marine pastes prose and asks for an audit:

1. Read the draft once for sense — what is she actually saying?
2. Scan for Tier-1 single words. Replace or cut.
3. Scan for Tier-2 phrases. Rewrite the surrounding sentence, not just the phrase.
4. Read aloud (mentally) for Tier-3 cadence. Check sentence-length variation, em-dash count, tricolon density.
5. Check hyphens against the rules above.
6. Produce the rewritten draft. Below it, list the changes by category (e.g. "Removed: 3 instances of 'delve', 1 'tapestry', 2 hedge preambles. Reduced em-dashes from 7 to 2. Broke up 4 tricolons.").
7. If Marine pasted >500 words and the audit found <5 tells, say so directly — sometimes a draft is already clean and the right answer is "this reads as your voice, ship it."

## Generation workflow (when Marine asks for new prose)

When Marine asks Claude to draft something:

1. Plan the piece — what is the claim, who is the audience, what is the call to action?
2. Draft naturally without checking the filter first — the filter is for the second pass, not the first.
3. Before producing the output, do a one-pass mental scan against Tier-1, Tier-2, and Tier-3.
4. Produce the cleaned draft.
5. Do not narrate the filter pass. Marine does not need to hear "I avoided 'delve'."

The exception: if Marine asked for an unusual register (e.g. "make this sound like a TED talk", "write the dramatic version", "make it persuasive"), some tier-2 patterns might be appropriate. Even then, never use Tier-1 single-word ornaments. The cliché vocabulary is always wrong; the rhetorical structures sometimes have a place in deliberately persuasive writing.

## Reference files

- `references/strong-tells.md` — Top 150 highest-precision words with replacements column. Read when Marine asks for plain alternatives to a specific LLM word.
- `references/kobak-full-list.md` — All 434 style-marker words from Kobak et al. (2025), organized by part of speech. Read when Marine wants the comprehensive list or asks "is X on the list?"
- `references/phrase-patterns.md` — Extended phrase-pattern library beyond the Tier-2 list above. Read when auditing a long draft.
- `assets/tell-words.txt` — Plain-text grep list (one word per line). Use programmatically via `grep -wif assets/tell-words.txt draft.md` when Marine wants a fast scan of a long document.

## Provenance

The empirical basis for this skill:

- Kobak, D., González-Márquez, R., Horvát, E.-Á., & Lause, J. (2025). Delving into LLM-assisted writing in biomedical publications through excess vocabulary. *Science Advances*, 11(27), eadt3813. (15M PubMed abstracts; 900 excess words annotated; 379 style markers in 2024.)
- Juzek, T. S., & Ward, Z. B. (2025). Why does ChatGPT "delve" so much? Exploring the sources of lexical overrepresentation in LLMs. *Proceedings of COLING 2025*, 6397-6411. (21 focal words validated against ChatGPT-3.5.)
- Liang, W. et al. (2024). Monitoring AI-modified content at scale: A case study on the impact of ChatGPT on AI conference peer reviews. *arXiv:2403.07183*.
- Reinhart, A. et al. (2025). Do LLMs write like humans? Variation in grammatical and rhetorical styles. *PNAS*. (Grammatical and rhetorical features beyond lexicon.)
- Geng, M., & Trotta, R. (2025). Human-LLM coevolution: Evidence from academic writing. *arXiv:2502.09606*. (Documented that "delve" frequency dropped after public awareness — confirms the list will drift.)
- Wikipedia "Signs of AI writing" registry (WikiProject AI Cleanup) — running era-by-era list, especially valuable for the mid-2024+ vocabulary shift away from "delve" toward "vibrant", "enduring", "fostering", "align with".
- Marine's manual additions: paradigm-shift, cadence, tapestry, testament, mosaic, symphony, kaleidoscope, treasure trove, navigate (figurative), unpack, dive into, embark, journey, lens.

The list will drift. Geng & Trotta showed it's already drifting — `delve` is past its peak, while subtler tells like `vibrant`, `bolster`, `align with`, `enduring`, `fostering` are still active. Revisit this skill every 6-12 months against the current Berens lab CSV and the Wikipedia registry.
