# Visual tour

<figure class="gb-figure gb-hero" markdown>
![The viewer tailing a test run: colored log levels, pytest progress, a failed test with its search match and bookmark, a finished upload progress line, and clickable links](assets/hero_light.png#only-light){ width="820" }
![The viewer tailing a test run: colored log levels, pytest progress, a failed test with its search match and bookmark, a finished upload progress line, and clickable links](assets/hero_dark.png#only-dark){ width="820" }
<figcaption>At work: a test run in the widget itself, rendered by <code>tools/make_screenshots.py</code>.</figcaption>
</figure>

Every screenshot below is the real demo window (`demo.py`) driven into the
state each section describes and rendered by `tools/make_gallery.py`. The
red boxes are painted from the real widget positions — each section
explains what the marked control does and links the API behind it.

## The whole board

![Demo with every control visible](assets/demo_screen_with_all_functions_empty_logs.png#only-light)
![Demo with every control visible](assets/demo_screen_with_all_functions_empty_logs_dark.png#only-dark)

One window, six zones: the log view with gutter on top, search and filter
bars beneath it, option checkboxes, palette and font rows, the
stats/bookmark/session strip, and the action buttons at the bottom. Start
here to orient yourself, then follow the tour in order.

## ANSI colors, isolated per line

![ANSI escape code samples](assets/demo_screen_with_ANSI_escape_code.png#only-light)
![ANSI escape code samples](assets/demo_screen_with_ANSI_escape_code_dark.png#only-dark)

`Test ANSI Colors` prints every style and color, each terminated so styles
never bleed into the next line — compare bold, dim, italic, underline,
reverse-video, strikethrough, the 8 standard and 8 bright foregrounds, and
256-color plus true-color RGB samples further down. See
[Appending](api/viewer.md#appending-content).

## Streaming, line numbers, progress bars

![Streaming logs with line numbers](assets/demo_screen_with_streaming_logs_and_number_line.png#only-light)
![Streaming logs with line numbers](assets/demo_screen_with_streaming_logs_and_number_line_dark.png#only-dark)

The log stream writes colored records around a `Test Progress Bar` run:
line 7 was written as `Downloading... 0%` through `100%`, each step
overwriting the line in place via carriage returns. The blue underlined `https://example.com` link on line 8 opens on
++ctrl++ + click, and the pale bar on line 10 is the current-line
highlight. See [Appending](api/viewer.md#appending-content) and
[Links](api/viewer.md#links).

## Search: matches, query, counter

![Highlight search with 5 matches](assets/demo_screen_with_highlight_search.png#only-light)
![Highlight search with 5 matches](assets/demo_screen_with_highlight_search_dark.png#only-dark)

Typing `Timeout` lights up all 5 matches in yellow, with the active one in
blue — the red boxes mark the query field and the `1/5` counter with its
`<` `>` steppers, beside the Regex and Match Case toggles. See
[Search & filter](api/viewer.md#search-filter).

## Bookmarks: line and list

![Bookmarked lines and bookmark list](assets/demo_screen_with_bookmarks.png#only-light)
![Bookmarked lines and bookmark list](assets/demo_screen_with_bookmarks_dark.png#only-dark)

Lines 7 and 12 glow blue and appear as `line 7: …` and `line 12: …` in the
bottom list — the two red boxes. Toggle with the button, by clicking the
gutter, or from the right-click menu; `Next BM` / `Prev BM` wrap around and
skip filtered-out lines. See [Bookmarks](api/viewer.md#bookmarks).

## Right-click menu

![Context menu](assets/demo_screen_with_context_menu.png#only-light)
![Context menu](assets/demo_screen_with_context_menu_dark.png#only-dark)

Copy, Select All, Copy Plain Text, Copy With ANSI Codes (SGR sequences
reconstructed from the real formats), Toggle Bookmark, Toggle Word Wrap,
Toggle Line Numbers, Clear, and Save to File. See
[Copy, export, sessions](api/viewer.md#copy-export-sessions).

## Selection statistics

![Text selection with live stats](assets/demo_screen_with_highlight_text_selection.png#only-light)
![Text selection with live stats](assets/demo_screen_with_highlight_text_selection_dark.png#only-dark)

Selecting lines 4 to 13 paints the selection and the red-boxed label
reports `735 chars, 100 words, 10 lines` live via `selectionStats()`.
Bookmarked lines 7 and 12 keep their blue band underneath. See
[Copy, export, sessions](api/viewer.md#copy-export-sessions).

## System fonts

![Proportional system font rendering](assets/demo_screen_with_system_fonts.png#only-light)
![Proportional system font rendering](assets/demo_screen_with_system_fonts_dark.png#only-dark)

The red box marks `System font`: the view drops monospace for Segoe UI at
9pt — proportional rendering works, alignment just stops lining up, which
is exactly why monospace is the default. Pick any family and size from the
font row, or go back with `setMonospaceFont()`. See
[Fonts & zoom](api/viewer.md#fonts-zoom).

## Word wrap: off vs on

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1rem;" markdown>

<div markdown>
**Off** — long lines scroll sideways (`Word Wrap` unchecked):

![Before word wrap](assets/demo_screen_before_wrap_text.png#only-light)
![Before word wrap](assets/demo_screen_before_wrap_text_dark.png#only-dark)
</div>

<div markdown>
**On** — the same lines reflow in place (`Word Wrap` checked):

![After word wrap](assets/demo_screen_after_wrap_text.png#only-light)
![After word wrap](assets/demo_screen_after_wrap_text_dark.png#only-dark)
</div>

</div>

Compare lines 1 and 6, whose `returned 2048 rows …` tails drop onto a
continuation row. See [Layout](api/viewer.md#layout-scroll-and-gutter).
