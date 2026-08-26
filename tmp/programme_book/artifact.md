# Opus Music Festival programme-book editing contract

## Reference

- Retained reference: `/Users/pyen/Downloads/節目單/節目本.docx`
- SHA-256: `57cf74b540caa8cd77dae8501eb5aa4550859fdfe950b212ab537f5929a7b45a`
- 3 A4 portrait pages; one document section.
- Render evidence: `tmp/programme_book/template-render/`
- Style evidence: `tmp/programme_book/template-style-evidence.json`

## Reference format to reproduce in the supplied programme text

- Page: A4 portrait, left/right margins approximately 0.79/0.78 in.; top/bottom 0.49/0.30 in.
- Programme and work-note headings use two consecutive, bold Garamond lines: English first, Chinese second. English headings use `Composer initial. Surname: Work title`; Chinese headings use `中文作曲家名：中文曲名`.
- Work-title punctuation follows the provided PDF: English headline-style capitalization, `op.` in lower case, diacritical marks preserved, English keys written `E-flat major`; Chinese keys written with capital note name and a space (for example `降 E 大調`).
- The text source remains the working document. The request requires content and local formatting changes, not a wholesale rebuild of the booklet artwork.

## Slots and changes

- Translate the five English paragraphs in the Artistic Director's Note into Chinese, retaining the English copy above/beside it.
- Reformat all work-note headings at paragraphs 227–362 of the source to the two-line reference pattern, English first.
- Normalize programme work titles and composer/date lines to the same convention.
- Replace the 16 `（簡介待補）` slots with concise, sourced Chinese biographies. Add a missing trumpet biography for Chuan-An Hou because he appears as the soloist in the Shostakovich programmes.
- Preserve the original source's page structure, orchestra roster, Friends of Opus placeholders, staff credits, images, headers/footers, and unrelated document parts.

## Fidelity gates

- The template and source reference must remain byte-for-byte unchanged.
- The final document must render without clipped text, overlapping text, or blank/stranded heading pages.
- Any expected pagination changes may be limited to the Artistic Director translation and completed biographies.
