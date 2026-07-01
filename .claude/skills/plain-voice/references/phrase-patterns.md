# Phrase patterns — extended library

When auditing a long draft, scan for these patterns. Each is stronger evidence of LLM authorship than any single word. The empirical basis is in Reinhart et al. (2025, *PNAS*) on grammatical/rhetorical features, the Washington Post July 2025 ChatGPT-message dataset analysis, and the Wikipedia "Signs of AI writing" running registry.

## Sentence-opening patterns

These telegraph "machine wrote this" within the first five words.

- "In today's [adjective] landscape, ..."
- "In an increasingly [adjective] world, ..."
- "In the digital age, ..."
- "In the realm of ..."
- "In an era where ..."
- "As we navigate the complexities of ..."
- "When it comes to ..."
- "It's important to note that ..."
- "It is widely recognized that ..."
- "Imagine a world where ..."
- "Picture this: ..."
- "Have you ever wondered ..."
- "Let's [verb] ..." (as section opener)
- "First and foremost, ..."

**Replacement strategy.** State the claim or set the scene with a concrete fact. Marine's voice is figure-first — open with the result, the data, the moment, the question. Not the throat-clearing.

## Closing-paragraph patterns

LLMs almost always end with a wrap-up paragraph that summarizes and gestures at importance. Most pieces don't need this. End on the strongest concrete point.

- "Ultimately, ..."
- "In conclusion, ..."
- "Moving forward, ..."
- "Looking ahead, ..."
- "As we look to the future, ..."
- "In the end, ..."
- "X stands as a testament to ..."
- "X represents a [paradigm shift / new chapter / turning point] in ..."
- "Only time will tell ..."
- "The implications are far-reaching."
- "This work paves the way for ..."
- "X is more than just Y; it is Z."

**Replacement strategy.** Cut the wrap-up. If you must end summarily, end on a question, a concrete next step, or a specific commitment ("We will release the dataset next quarter"). Avoid sentiment.

## Negative parallelism (the strongest current marker)

The single most recognizable AI rhetorical move. Washington Post analysis of 47,000 July 2025 ChatGPT messages found this construction in ~6% of all messages.

- "It's not X, it's Y."
- "It's not just X — it's Y."
- "Not just X, but Y."
- "X isn't merely Y; it's Z."
- "More than just X, it's Y."
- "This isn't about X. It's about Y."

**Replacement strategy.** Just state Y. The "not X" half is almost always a strawman the writer set up to knock down. If the contrast genuinely matters, use a less ornate construction: "Y, not X" or "X is part of it, but the real story is Y."

## Tricolon (rule of three)

Humans use tricolons. The tell is when they appear with mathematically even cadence as the climactic gesture of every other paragraph, especially in matched grammatical form.

- "[noun phrase], [noun phrase], and [noun phrase]"
- "It is [adj], [adj], and [adj]."
- "We must [verb], [verb], and [verb]."
- "Whether X, Y, or Z, ..."

**Audit rule.** Count tricolons in the draft. More than one per ~500 words is suspect. When you find one, ask: does the rhythm earn its weight, or is it filler? If filler, prune to two items, or replace with an asymmetric structure.

## Hedge preambles

These add zero information. They are pure register signaling. Cut all of them.

- "It's important to note that ..."
- "It's worth noting that ..."
- "It's crucial to consider ..."
- "It bears mentioning that ..."
- "It should be noted that ..."
- "One could argue that ..."
- "It is generally understood that ..."
- "Broadly speaking, ..."
- "Generally, ..."
- "Generally speaking, ..."
- "By and large, ..."
- "For the most part, ..."
- "In many cases, ..."
- "While this may vary, ..."
- "That said, ..."
- "Having said that, ..."

**Audit rule.** Strike all of them. The sentence that follows is the actual claim — promote it.

## Metaphor clichés

These have been so over-applied in LLM training data that their literal meaning has been bleached out. They now read as ornament regardless of context.

- "the rich tapestry of [X]"
- "a treasure trove of [X]"
- "through the lens of [X]"
- "at the heart of [X]"
- "at the intersection of [X and Y]"
- "the cornerstone of [X]"
- "the backbone of [X]"
- "the bedrock of [X]"
- "navigate the [complexities / uncertainty / landscape] of [X]"
- "shed light on [X]"
- "shine a spotlight on [X]"
- "paint a picture of [X]"
- "paint with a broad brush"
- "draw a parallel between"
- "speaks volumes about [X]"
- "stands as a testament to [X]"
- "embodies the spirit of [X]"
- "pave the way for [X]"
- "open the door to [X]"
- "unlock the potential of [X]"
- "tap into [X]"
- "harness the power of [X]"
- "set the stage for [X]"
- "lay the foundation for [X]"
- "redefine [X]" / "redefining [X]"
- "reimagine [X]" / "reimagining [X]"
- "a new chapter in [X]"
- "a turning point for [X]"
- "a watershed moment"
- "a perfect storm"
- "a double-edged sword"
- "the elephant in the room"
- "the tip of the iceberg"
- "low-hanging fruit"
- "the silver lining"
- "move the needle"
- "raise the bar"
- "drink from the firehose"

**Audit rule.** Replace with the literal claim or cut the sentence. If Marine's prose can survive without the metaphor, the metaphor was decoration.

## "Whether...or" constructions (overused)

LLMs love hypothetical-equating gestures. The pattern: "Whether [X] or [Y], the [Z] remains..." This is a way of seeming to cover bases without saying anything.

- "Whether X or Y, ..."
- "Be it X or Y, ..."
- "From X to Y, ..."
- "Whether you're a [role] or a [role], ..."

**Replacement strategy.** Drop the hypothetical and state who/what you actually mean.

## The "double-act" verb pair

LLMs pair near-synonymous verbs for emphasis. Humans pick one.

- "develop and refine"
- "design and develop"
- "explore and analyze"
- "investigate and understand"
- "create and curate"
- "shape and define"
- "build and maintain"
- "support and empower"
- "guide and inform"
- "deliver and execute"
- "envision and create"

**Audit rule.** Keep the more specific verb, cut the other.

## The "more than just" / "not merely" gesture

A close cousin of negative parallelism. The pattern presents the obvious reading, then "elevates" with a grander one.

- "more than just X, it's Y"
- "not merely X, but Y"
- "X is, in many ways, Y"
- "X is fundamentally Y"

**Replacement strategy.** State Y directly. If you need to acknowledge X first, do so without the rhetorical setup: "Y, in addition to X."

## Em-dash patterns

The em-dash is fine — when used sparingly. The tell is rhythm and density.

- More than one em-dash per paragraph
- Em-dashes used in place of commas in lists
- Em-dashes used to introduce a casual aside in formal writing
- Em-dashes wrapping mid-sentence parentheticals when commas would suffice

**Audit rule.** Count em-dashes per paragraph. >1 per paragraph: replace half with commas, colons, or full stops. The remaining ones should mark genuine interruption or emphatic aside.

## Markdown overuse in prose

When generating long-form prose (papers, op-eds, blog posts), avoid heavy structural markdown unless the format requires it. Specifically:

- Don't bold mid-sentence words for "emphasis."
- Don't use sub-headers every 2-3 paragraphs.
- Don't bullet-list things that are continuous reasoning.
- Don't use numbered lists for steps that are actually a single process described in prose.

**Audit rule.** If converting the piece to plain text (no formatting) would make it hard to follow, the formatting is doing too much work. The prose itself should carry the structure.

## Cadence audit checklist

When reading a draft for cadence (rhythm-level AI tells), check:

1. **Sentence-length variation.** Mark sentence lengths in a margin. If three consecutive sentences are within ±3 words of each other, break the pattern.
2. **Paragraph length variation.** Same logic. Mix 1-sentence paragraphs (rare, for emphasis) with 3-sentence and 5+ sentence paragraphs.
3. **Opener variation.** Are paragraphs all starting with the same syntactic pattern (transitional adverb + subject + verb)? Vary openers.
4. **Tricolon density.** Count tricolons. >1 per 500 words: prune.
5. **Em-dash density.** >1 per paragraph: prune.
6. **Conclusion-paragraph reflex.** Does every section end with a summary-and-gesture sentence? Cut most of them.
