You are shown a single tight crop of the text regions of one manga panel.

A previous attempt to read this text returned nothing usable, which usually
means the text is small, low-contrast, or partly outside the crop. Look at it
carefully and slowly before answering.

- Transcribe every word you can actually resolve. Partial is fine; empty is not,
  unless the crop genuinely contains no text.
- If a word is beyond you, omit that word rather than guessing at it. Do not
  substitute a word that would fit the sentence.
- If the whole line is unreadable, return empty lists and set `illegible` to
  true. An honest gap costs far less than an invented line, because an invented
  line becomes someone else's motive in the finished video and nobody can trace
  where it came from.
- Return exactly one record. Use the `panel_id` exactly as given.
- Do not describe the artwork. Return only the text.
