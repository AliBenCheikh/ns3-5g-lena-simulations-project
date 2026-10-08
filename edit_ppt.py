"""Build the revised supervisor-meeting deck from Meeting.pptx.

Reads ``Meeting.pptx`` and writes ``Meeting_revised.pptx``; the original file is
never modified. All additions are native PowerPoint shapes and tables in the
deck's own style (Cambria titles, Calibri body, navy/teal palette), so the
result stays fully editable.

What the script does
--------------------
1. Edits nine existing slides: title, agenda, and the survey slides whose
   takeaways overclaimed or contradicted the reviewers. It also restores the
   missing dark card on slide 34, where white text sat on a white background.
2. Adds twenty new slides: executive diagnosis, cross-survey synthesis,
   paper audit, reviewer matrix, revision plan, positioning, research
   directions, datasets, experimental infrastructure, protocol, next steps,
   references, and an appendix divider.
3. Reorders the deck into one storyline and moves detailed survey slides to
   an appendix. No original slide is deleted.
4. Renumbers every slide and adds speaker notes to modified and new slides.

Usage: ``python3 edit_ppt.py [source.pptx] [output.pptx]``
The analysis behind the content is in ``docs/research_review.md``.
"""

import copy
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

SRC = "Meeting.pptx"
DST = "Meeting_revised.pptx"

# Palette and fonts taken from the existing deck.
NAVY = "12394D"
NAVY_BG = "0B2B3C"
TEAL = "1A8A99"
TEAL_LIGHT = "2BB3A3"
CARD = "F0F5F7"
TAKEAWAY = "E6F4F2"
BODY = "2A3F4C"
MUTED = "5F7A8A"
ON_DARK = "C3D3DD"
WHITE = "FFFFFF"
RED = "B03A2E"
AMBER = "C46A1B"
GREEN_TINT = "D4EDDA"
AMBER_TINT = "FFF3CD"
RED_TINT = "F8D7DA"
SERIF = "Cambria"
SANS = "Calibri"
FOOTER = "RS2M Department · Télécom SudParis · Palaiseau, France"


# --------------------------------------------------------------------------
# Low-level helpers
# --------------------------------------------------------------------------

def rgb(hex_color):
    return RGBColor.from_string(hex_color)


def style_run(run, size, color, bold=False, italic=False, font=SANS):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font
    run.font.color.rgb = rgb(color)


def add_text(slide, x, y, w, h, paragraphs, size=12.5, color=BODY, bold=False,
             font=SANS, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT,
             space_after=0, name=None, spacing=None):
    """Add a zero-inset text box.

    ``paragraphs`` is a list; each item is a string or a list of
    ``(text, {overrides})`` runs, where overrides may set size, color, bold,
    italic and font.
    """
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, para in enumerate(paragraphs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if space_after:
            p.space_after = Pt(space_after)
        runs = [(para, {})] if isinstance(para, str) else para
        for text, opts in runs:
            r = p.add_run()
            r.text = text
            style_run(r, opts.get("size", size), opts.get("color", color),
                      opts.get("bold", bold), opts.get("italic", False),
                      opts.get("font", font))
            if spacing:
                # Letter-spaced labels, as in the deck's own headers (spc in 1/100 pt).
                r._r.get_or_add_rPr().set("spc", str(spacing))
    return box


def add_box(slide, x, y, w, h, fill, rounded=True, line=None):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if rounded:
        shp.adjustments[0] = 0.08
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(fill)
    if line:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(1.25)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def add_circle_number(slide, x, y, d, label, fill=TEAL, size=14):
    circ = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    circ.fill.solid()
    circ.fill.fore_color.rgb = rgb(fill)
    circ.line.fill.background()
    circ.shadow.inherit = False
    add_text(slide, x, y, d, d, [str(label)], size=size, color=WHITE, bold=True,
             font=SERIF, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)


def add_arrow(slide, x1, y1, x2, y2, color=TEAL, width=1.75):
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1),
                                      Inches(x2), Inches(y2))
    conn.line.color.rgb = rgb(color)
    conn.line.width = Pt(width)
    ln = conn.line._get_or_add_ln()
    etree.SubElement(ln, qn("a:tailEnd"), type="triangle", w="med", len="med")
    return conn


def add_table(slide, x, y, col_widths, rows, row_heights=None, size=11,
              header_size=11.5, header_fill=NAVY, zebra=True, cell_colors=None,
              bold_first_col=False):
    """Native table. ``rows[0]`` is the header. A cell is a string or a list of
    runs as in add_text. ``cell_colors`` maps (row, col) to (fill, text, bold)."""
    n_rows, n_cols = len(rows), len(col_widths)
    total_w = sum(col_widths)
    heights = row_heights or [0.4] * n_rows
    gframe = slide.shapes.add_table(n_rows, n_cols, Inches(x), Inches(y),
                                    Inches(total_w), Inches(sum(heights)))
    table = gframe.table
    table.first_row = True
    table.horz_banding = False
    for c, w in enumerate(col_widths):
        table.columns[c].width = Inches(w)
    for r, h in enumerate(heights):
        table.rows[r].height = Inches(h)
    cell_colors = cell_colors or {}
    for r, row in enumerate(rows):
        for c in range(n_cols):
            cell = table.cell(r, c)
            content = row[c] if c < len(row) else ""
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            if r == 0:
                fill, tcolor, tbold, tsize = header_fill, WHITE, True, header_size
            else:
                fill = CARD if (zebra and r % 2 == 1) else WHITE
                tcolor, tbold, tsize = BODY, bold_first_col and c == 0, size
                if bold_first_col and c == 0:
                    tcolor = NAVY
            if (r, c) in cell_colors:
                fill, tcolor, tbold = cell_colors[(r, c)]
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(fill)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            runs = [(content, {})] if isinstance(content, str) else content
            for text, opts in runs:
                run = p.add_run()
                run.text = text
                style_run(run, opts.get("size", tsize), opts.get("color", tcolor),
                          opts.get("bold", tbold), opts.get("italic", False))
    return table


def header(slide, label, title):
    add_text(slide, 0.7, 0.45, 11.9, 0.35, [label], size=14, color=TEAL_LIGHT, bold=True,
             spacing=200)
    add_text(slide, 0.7, 0.86, 11.9, 0.7, [title], size=27, color=NAVY, bold=True, font=SERIF)


def takeaway(slide, text, y=6.12):
    add_box(slide, 0.7, y, 11.9, 0.55, TAKEAWAY)
    add_text(slide, 0.95, y, 11.45, 0.55,
             [[("Takeaway  ", {"bold": True, "color": TEAL}), (text, {"color": NAVY})]],
             size=14, anchor=MSO_ANCHOR.MIDDLE)


def footer(slide, dark=False):
    color = ON_DARK if dark else MUTED
    add_text(slide, 0.7, 6.95, 7.0, 0.3, [FOOTER], size=11, color=color)
    add_text(slide, 12.1, 6.95, 0.5, 0.3, ["0"], size=11, color=color, name="PageNumber",
             align=PP_ALIGN.RIGHT)


def section_label(slide, x, y, w, text, color=TEAL):
    add_text(slide, x, y, w, 0.3, [text], size=12, color=color, bold=True, spacing=100)


# Body placeholder copied from an existing notes page: this deck's notes master
# has no body placeholder, so notes pages created for new slides lack one.
_NOTES_BODY = {"element": None}


def notes_frame(slide):
    notes = slide.notes_slide
    if notes.notes_text_frame is None:
        body = copy.deepcopy(_NOTES_BODY["element"])
        sp_tree = notes.shapes._spTree
        used = [int(e.get("id")) for e in sp_tree.iter(qn("p:cNvPr"))]
        body.find(".//" + qn("p:cNvPr")).set("id", str(max(used, default=1) + 1))
        sp_tree.append(body)
    return notes.notes_text_frame


def set_notes(slide, text):
    notes_frame(slide).text = text


def append_notes(slide, text):
    tf = notes_frame(slide)
    existing = tf.text.strip()
    tf.text = (existing + "\n\n" + text) if existing else text


def replace_runs(shape, texts):
    """Write ``texts`` into the runs of the first paragraph, keeping the run
    formatting; surplus runs are emptied."""
    runs = shape.text_frame.paragraphs[0].runs
    for i, run in enumerate(runs):
        run.text = texts[i] if i < len(texts) else ""


def shape_by_name(slide, name):
    for shp in slide.shapes:
        if shp.name == name:
            return shp
    raise KeyError(f"{name} not found on slide")


def new_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[0])


def bullets(slide, x, y, w, h, items, size=12.5, color=BODY, bullet_color=TEAL, gap=4):
    """Bullet list drawn with a coloured en dash so it renders the same in
    PowerPoint and LibreOffice."""
    paras = [[("–  ", {"color": bullet_color, "bold": True}), (item, {})] for item in items]
    return add_text(slide, x, y, w, h, paras, size=size, color=color, space_after=gap)


# --------------------------------------------------------------------------
# Edits to existing slides (indices refer to the original 1-based numbering)
# --------------------------------------------------------------------------

def edit_existing(prs):
    s = {i + 1: slide for i, slide in enumerate(prs.slides)}

    # Slide 1: title
    replace_runs(shape_by_name(s[1], "Text 5"),
                 ["Research landscape · audit · next steps"])
    replace_runs(shape_by_name(s[1], "Text 8"), ["Landscape, paper audit and next steps", ""])
    append_notes(s[1], "Revised deck. Storyline: why the problem matters, what the three surveys "
                 "jointly say, what my rejected Offline Safe-CQL paper shows and misses, what the "
                 "reviewers reveal, which directions are worth pursuing, how to validate them, and "
                 "the decisions I need from you today. Detailed survey slides are in the appendix.")

    # Slide 2: agenda rewritten into the A→H story
    sl = s[2]
    replace_runs(shape_by_name(sl, "Text 2"), ["Today's storyline"])
    replace_runs(shape_by_name(sl, "Text 4"), ["WHERE I STAND"])
    replace_runs(shape_by_name(sl, "Text 15"), ["WHAT I WILL BUILD"])
    replace_runs(shape_by_name(sl, "Text 26"), ["VALIDATE & DECIDE"])
    cards = {
        "Text 8": "Research landscape",
        "Text 9": "Three surveys, read for what they imply for my work, not summarised one by one.",
        "Text 13": "Paper & reviewer audit",
        "Text 14": "What Offline Safe-CQL shows, what it does not, and what three reviewers flagged.",
        "Text 19": "Research directions",
        "Text 20": "Ranked directions; recommended core: constrained offline→online learning.",
        "Text 24": "Datasets & simulators",
        "Text 25": "What each dataset supports; ns-3 5G-LENA staged set-up.",
        "Text 30": "Evaluation protocol",
        "Text 31": "Baselines per claim, tail metrics, seeds and confidence intervals.",
        "Text 35": "Decisions & publication",
        "Text 36": "What I need you to decide today; target venues.",
    }
    for name, text in cards.items():
        replace_runs(shape_by_name(sl, name), [text])
    for name in ("Shape 16", "Shape 21", "Shape 27", "Shape 32"):
        card_shape = shape_by_name(sl, name)
        card_shape.fill.solid()
        card_shape.fill.fore_color.rgb = rgb("123A4E")
    set_notes(sl, "Six parts. First, where I stand: what the three surveys jointly imply, then a "
              "critical audit of my rejected paper and of the reviews. Second, what I will build: "
              "ranked research directions and the datasets/simulators to support them. Third, how "
              "I will validate and what I need decided today. The survey details from the previous "
              "version are kept in the appendix.")

    # Slide 8: link URLLC targets to the paper's slice
    replace_runs(shape_by_name(s[8], "Text 3"),
                 ["  ", "3GPP targets (1 ms, 1−10⁻⁵) are a baseline; my paper's slice (20 ms, 3 % "
                  "budget) is latency-sensitive, not URLLC-grade."])
    append_notes(s[8], "Link to my paper: the 'URLLC' slice in the Colosseum dataset has a 20 ms "
                 "threshold and I allowed 3 % violations, i.e. 97 % reliability. Haque gives "
                 "99.999 % at 1 ms (PDF p. 1) and 1−10⁻⁵ to 1−10⁻⁹ (p. 2). In the revision I will "
                 "call it a latency-sensitive slice, or justify the URLLC label.")

    # Slide 12: scoped takeaway
    replace_runs(shape_by_name(s[12], "Text 3"),
                 ["Takeaway  ", "The RL works reviewed here are trained online, in simulation: "
                  "none learns from network logs under a URLLC constraint."])

    # Slide 17: expectation-only caveat
    replace_runs(shape_by_name(s[17], "Text 3"),
                 ["Takeaway  ", "Offline training protects users while learning, but the "
                  "constraint still holds only in expectation and on the data's support."])
    append_notes(s[17], "Revision note: this is exactly the limit of Safe-CQL. Being offline "
                 "removes training-time exposure, but the final Lagrangian policy satisfies the "
                 "budget only on average (Lu, Section II-H, PDF p. 11), and only for actions the "
                 "logs support.")

    # Slide 19: correct the timescale claim (Reviewer 2)
    replace_runs(shape_by_name(s[19], "Text 3"),
                 ["Takeaway  ", "Placement fixes what the agent sees and controls: a 5 s decision "
                  "period is a Non-RT (rApp) loop, not a Near-RT xApp."])
    append_notes(s[19], "Revision note: Reviewer 2 is right. Lu (PDF p. 14) gives 10 ms to 1 s for "
                 "the Near-RT RIC and more than 1 s for the Non-RT RIC. My decision step is 5 s, so "
                 "either I present the agent as an rApp (slice configuration through A1/O1) or I "
                 "redesign the loop for 1 s or less.")

    # Slide 20: notes link to Reviewer 1
    append_notes(s[20], "Revision note: Reviewer 1's Markov comment belongs here. My state "
                 "excludes the current configuration; in my logs the configuration never changes "
                 "within a reservation, so the previous action cannot be learned from. I must state "
                 "the decision model explicitly (contextual bandit or POMDP with history).")

    # Slide 34: restore the missing dark card and nuance the position
    sl = s[34]
    text24 = shape_by_name(sl, "Text 24")
    card = add_box(sl, 7.35, 2.15, 5.25, 3.75, NAVY)
    sp_tree = sl.shapes._spTree
    sp_tree.remove(card._element)
    text24._element.addprevious(card._element)
    text24.top, text24.height = Inches(2.4), Inches(1.0)
    section_label(sl, 7.6, 3.55, 4.75, "WHAT THE AUDIT ADDS", color=TEAL_LIGHT)
    bullets(sl, 7.6, 3.9, 4.8, 1.9, [
        "Learned from static configuration logs: one-step effects only",
        "Constraint met on average (3 % budget), not per window or on the tail",
        "Offline O-RAN work exists outside these surveys (Yang et al. 2024; 2OffRAN 2025)",
    ], size=12.5, color=ON_DARK, bullet_color=TEAL_LIGHT)
    append_notes(sl, "Revision note: the dark card was missing in the previous version, which "
                 "made the white text invisible. The bottom of the card lists what the audit "
                 "changes in my claim.")
    return s


# --------------------------------------------------------------------------
# New slides
# --------------------------------------------------------------------------

def slide_exec_diagnosis(prs):
    sl = new_slide(prs)
    header(sl, "Executive diagnosis", "Five conclusions that should drive the next six months")
    rows = [
        ("The data, not the algorithm, is the binding limit",
         "Configurations are fixed for each reservation: no action switch is ever observed "
         "(paper p. 5; Lu p. 48)."),
        ("“Safe” means a CMDP constraint met on average, by proxy",
         "No tail, per-window or deployment guarantee, and λ has not converged in Fig. 3."),
        ("A static configuration may match the agent",
         "(39 PRB, RR) stays at or below 3 % violations at every load in Fig. 1: test it first."),
        ("Two positioning errors are cheap to fix",
         "5 s steps form a Non-RT loop (Lu p. 14); a 20 ms / 97 % slice is not URLLC "
         "(Haque p. 1–2)."),
        ("Thesis core: constrained offline→online learning on decision-logged data",
         "ns-3 5G-LENA with logged switching policies; traces become traffic and calibration inputs."),
    ]
    for i, (head, detail) in enumerate(rows):
        y = 1.8 + i * 0.84
        add_circle_number(sl, 0.7, y + 0.03, 0.42, i + 1)
        add_text(sl, 1.3, y, 11.2, 0.8,
                 [[(head, {"bold": True, "color": NAVY, "size": 15})],
                  [(detail, {"color": MUTED})]], size=12.5)
    takeaway(sl, "Fix the claims now; move the RL contribution to data I can control.")
    footer(sl)
    set_notes(sl, "These five points summarise the whole deck. One: the decisive weakness is the "
              "dataset, where each reservation keeps one configuration, so sequential effects cannot "
              "be learned. Two: safety is a constraint in the optimisation, met on average and "
              "measured with off-policy proxies. Three: from my own Fig. 1, the static (39, RR) "
              "configuration is already within budget at every load, so it may match the agent; this "
              "is a one-day check. Four: the timescale and URLLC claims must be corrected. Five: my "
              "recommended thesis core is constrained offline-to-online learning in a simulator "
              "where I log decisions myself.\nLikely question: is the paper dead? Not necessarily; "
              "it depends on the static-baseline result (slide 20).")
    return sl


def slide_survey_table(prs):
    sl = new_slide(prs)
    header(sl, "Cross-survey synthesis", "Three lenses on one problem, and what each one gives me")
    rows = [
        ["Survey", "Scope and methods", "Architecture and evidence", "Open problems", "Use for my work"],
        [[("Haque et al. 2025", {"bold": True, "color": NAVY})],
         "URLLC across PHY, MAC and cross-layer: mini-slots, grant-free, HARQ, multi-connectivity; "
         "ML mostly supervised, RL online (Table IX)",
         "3GPP Rel-15 to 17; 6G: ≤ 0.1 ms, 99.99999 %; analytical and simulation evidence",
         "Sub-ms latency; latency–reliability trade-off analysis; fast adaptation (§XI, p. 29)",
         "Defines the target: shows my 20 ms / 97 % slice is latency-sensitive, not URLLC"],
        [[("Lu et al. 2026", {"bold": True, "color": NAVY})],
         "DRL for O-RAN: MDP / POMDP / CMDP, offline (BCQ, CQL, IQL), safe RL, MARL, deployment",
         "RIC loops (> 1 s, 10 ms–1 s, < 10 ms); Colosseum, ns-O-RAN, OpenRAN Gym; "
         "decision-centred data (Eq. 32)",
         "Offline→online under constraints; runtime assurance; trustworthy twins; benchmarks (§XII)",
         "Backs Reviewer 2 (timescale, static data) and sets my core direction"],
        [[("Adhikari et al. 2024", {"bold": True, "color": NAVY})],
         "eMBB/URLLC sharing: puncturing, superposition, OMA/NOMA/RSMA, slicing, flexible TTI, DRL, FL",
         "Slot / mini-slot multiplexing; simulation-based; “offline” means optimisation",
         "Low-complexity models, joint optimisation, ML validity under change (§V, p. 25–26)",
         "Coexistence assumptions to state; report across loads; Alsenwi et al. as a baseline"],
    ]
    add_table(sl, 0.7, 1.75, [1.75, 2.85, 2.6, 2.45, 2.25], rows,
              row_heights=[0.4, 1.25, 1.25, 1.25], size=11)
    takeaway(sl, "None of the three covers constraint-aware learning from logged RAN decisions; "
                 "Yang et al. 2024 and 2OffRAN must still be cited.")
    footer(sl)
    set_notes(sl, "One row per survey, with the columns reduced to what drives decisions. Page "
              "numbers refer to the supplied PDFs. Haque fixes what must be guaranteed, Adhikari "
              "how services share resources, Lu who decides, when, and from which data. The full "
              "comparison table, with limitations and datasets, is in docs/research_review.md, "
              "Deliverable 2.\nCaveat: absence from a survey is not a gap. Yang et al. (2024) "
              "already apply CQL/IQL to RAN slicing offline, and 2OffRAN (ICMLCN 2025) does offline "
              "RL with off-policy evaluation for handover.")
    return sl


def slide_survey_implications(prs):
    sl = new_slide(prs)
    header(sl, "Cross-survey synthesis", "Four implications for my research decisions")
    cards = [
        ("Configure, don't schedule",
         "URLLC decisions live at ≤ 1 ms (Haque, Adhikari); RIC loops start at 10 ms (Lu p. 14). "
         "An xApp or rApp can only set the slice quotas and scheduler policies that shape the URLLC tail."),
        ("Keep constraints explicit, and on the tail",
         "Lu (§II-H, §VIII-A) favours CMDPs over penalties; Haque (§XI) asks for latency–reliability "
         "analysis. Constrain P(ℓ > L) or a CVaR, not a window mean."),
        ("Data must be decision-centred",
         "Logs need (s, a, r, s′, Δt, z), the behaviour policy and the control location (Lu Eq. 32, "
         "p. 48). KPM-only traces calibrate simulators; they do not train sequential policies."),
        ("Report across loads and seeds",
         "URLLC QoS depends on its own load (Adhikari §III-C); the formulation changes the winner "
         "(PandORA, Lu p. 16); benchmarks need seeds and CIs (Lu p. 56)."),
    ]
    for i, (head, text) in enumerate(cards):
        x = 0.7 + (i % 2) * 6.05
        y = 1.8 + (i // 2) * 2.12
        add_box(sl, x, y, 5.85, 1.95, CARD)
        add_circle_number(sl, x + 0.25, y + 0.22, 0.42, i + 1)
        add_text(sl, x + 0.85, y + 0.22, 4.8, 0.45, [head], size=15, color=NAVY, bold=True)
        add_text(sl, x + 0.85, y + 0.7, 4.8, 1.2, [text], size=12.5, color=BODY)
    takeaway(sl, "Implication: a configuration-level controller with tail constraints, trained on "
                 "decision logs I generate.")
    footer(sl)
    set_notes(sl, "These are my synthesis, not statements of any single survey. Point 1 is the "
              "structural tension the surveys expose: the URLLC literature decides per TTI or "
              "mini-slot, while RIC applications act at 10 ms or slower. The defensible role of my "
              "agent is to configure, not to schedule. Point 3 is Lu's own requirement for DRL "
              "datasets, and it is the reason the Colosseum traces are not enough.")
    return sl


def slide_paper_summary(prs):
    sl = new_slide(prs)
    header(sl, "Part D · My rejected paper", "Offline Safe-CQL: what was built and claimed")
    steps = ["Colosseum twinning traces (225k transitions)", "Audit: scheduler drives the tail",
             "CMDP: max eMBB s.t. E[c] ≤ 0.03", "CQL Q_r + tabular ĉ(a, load) + adaptive λ",
             "OPE on the held-out cluster"]
    for i, text in enumerate(steps):
        x = 0.7 + i * 2.44
        dark = i == 3
        add_box(sl, x, 1.8, 2.12, 0.8, NAVY if dark else WHITE, line=None if dark else TEAL)
        add_text(sl, x + 0.08, 1.8, 1.96, 0.8, [text], size=12, color=WHITE if dark else NAVY,
                 bold=True, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
        if i < len(steps) - 1:
            add_arrow(sl, x + 2.14, 2.2, x + 2.42, 2.2)
    section_label(sl, 0.7, 2.9, 5.0, "FORMULATION")
    bullets(sl, 0.7, 3.25, 5.4, 2.7, [
        "State: 12 KPM features; current configuration excluded",
        "Action: 4 PRB splits × {RR, PF} = 8",
        "Step: 5 s window; γ = 0.7; cost treated as immediate (γ_c = 0)",
        "Cost: share of URLLC packets above 20 ms; budget d = 0.03",
        "Data: 1 BS, 50 PRB, 8 UEs; train on clusters 2–3, test on 1",
    ], size=12.5)
    section_label(sl, 6.5, 2.9, 6.0, "RESULT ON THE HELD-OUT CLUSTER (TABLE II)")
    rows = [["Method", "Thr. matching", "Cost matching", "Thr. tabular", "Cost tabular"],
            ["BC", "7.76 ± 0.10", "0.041 ± 0.002", "7.49 ± 0.05", "0.057 ± 0.002"],
            ["CQL (λ = 0)", "7.81 ± 0.04", "0.040 ± 0.002", "7.40 ± 0.03", "0.049 ± 0.002"],
            ["Safe-CQL", "7.65 ± 0.05", "0.030 ± 0.000", "7.31 ± 0.05", "0.030 ± 0.001"]]
    add_table(sl, 6.5, 3.25, [1.3, 1.2, 1.2, 1.2, 1.2], rows,
              row_heights=[0.42, 0.42, 0.42, 0.42], size=11, header_size=11, bold_first_col=True)
    add_text(sl, 6.5, 5.1, 6.1, 0.6, ["Throughput in Mbps; cost = URLLC violation rate. "
                                     "Safe-CQL: 2 seeds; BC and CQL: 5 seeds."],
             size=11, color=MUTED)
    takeaway(sl, "Claim: 25–47 % fewer violations for 1–2 % less eMBB throughput, with no online "
                 "exploration.")
    footer(sl)
    set_notes(sl, "Reminder of the rejected paper. The pipeline audits the Colosseum commercial "
              "traffic twinning traces, finds that the scheduler (not the PRB split) drives the "
              "URLLC latency tail, formulates a CMDP and trains CQL with a tabular cost model and an "
              "adaptive Lagrange multiplier. Numbers are copied from Table II of the paper. Note "
              "the asymmetry in seeds and the cost sitting exactly at the budget.")
    return sl


def verdict_cell(text):
    color = {"Supported": TEAL, "Partly": AMBER}.get(text, RED)
    return [(text, {"bold": True, "color": color})]


def slide_claim_audit(prs):
    sl = new_slide(prs)
    header(sl, "Part D · Audit", "Which claims the evidence actually supports")
    rows = [["Claim in the paper", "Evidence available", "Verdict"],
            ["No unsafe exploration during training", "Trained only on logged transitions (§V)",
             verdict_cell("Supported")],
            ["25–47 % fewer URLLC violations", "OPE proxies only; Safe-CQL with 2 seeds; no CIs; "
             "cost exactly at the budget", verdict_cell("Partly")],
            ["λ “converges near 12.9”", "Fig. 3: λ still rising and training cost ≈ 0.032 > d at "
             "epoch 100", verdict_cell("Not supported")],
            ["Near-RT RIC xApp", "5 s decision period; the Near-RT loop is 10 ms–1 s (Lu p. 14)",
             verdict_cell("Not supported")],
            ["URLLC SLA", "L_max = 20 ms, 3 % budget, LTE 10 MHz testbed (Haque p. 1–2)",
             verdict_cell("Overstated")],
            ["Sequential RL is needed", "γ_c = 0, “near-immediate” effects, no action switch in "
             "the data", verdict_cell("Not shown")],
            ["Beats simple configuration rules", "No static baseline; (39, RR) ≤ 0.03 in every "
             "load bin of Fig. 1", verdict_cell("Untested")]]
    add_table(sl, 0.7, 1.75, [3.6, 6.4, 1.9], rows,
              row_heights=[0.4] + [0.5] * 7, size=12, header_size=12, bold_first_col=True)
    takeaway(sl, "The strongest claims rest on off-policy proxies and on a missing static baseline.")
    footer(sl)
    set_notes(sl, "My own reviewer-style audit, in addition to the three reviews. The λ point comes "
              "from Fig. 3 of the paper: the curve in (a) is still increasing at epoch 100 and the "
              "cost in (b) is still above the 0.03 budget, so the text should not say 'converges'. "
              "The 'sequential RL is needed' row matters: with an immediate cost and no observed "
              "action switches, a contextual-bandit formulation may be the honest one.\nLikely "
              "question: why not just rerun Safe-CQL with more seeds? Yes, that is part of the plan "
              "(P1), but it does not fix the data problem.")
    return sl


def slide_safe_ladder(prs):
    sl = new_slide(prs)
    header(sl, "Part D · Audit", "What “safe” means in Safe-CQL, and what it does not")
    rungs = [
        ("YES", TEAL, "Constraint inside the optimisation", "CMDP with an adaptive Lagrange multiplier (Eq. 7, 8, 12)"),
        ("YES", TEAL, "No exposure of users during training", "Offline by construction"),
        ("PARTLY", AMBER, "Constraint met on held-out data", "On average, by OPE proxy: 0.030 ± 0.001 at d = 0.03"),
        ("NO", RED, "Converged primal–dual solution", "Fig. 3: λ still rising at epoch 100"),
        ("NO", RED, "Per-window or tail-latency guarantee", "Expected-rate constraint only (Eq. 6–7)"),
        ("NO", RED, "Safety at deployment", "No shield, fallback, shadow mode or online test"),
    ]
    for i, (chip, color, head, detail) in enumerate(rungs):
        y = 1.8 + i * 0.7
        add_box(sl, 0.7, y + 0.08, 1.05, 0.42, color)
        add_text(sl, 0.7, y + 0.08, 1.05, 0.42, [chip], size=11.5, color=WHITE, bold=True,
                 anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
        add_text(sl, 1.95, y + 0.02, 5.3, 0.62,
                 [[(head, {"bold": True, "color": NAVY, "size": 13.5})],
                  [(detail, {"color": MUTED, "size": 12})]], size=12)
    add_box(sl, 7.55, 1.8, 5.05, 4.1, NAVY)
    section_label(sl, 7.85, 2.0, 4.5, "SUGGESTED WORDING", color=TEAL_LIGHT)
    add_text(sl, 7.85, 2.4, 4.5, 1.5,
             ["“Constraint-aware offline policy learning with empirical, average-case constraint "
              "satisfaction on held-out traces.”"], size=16, color=WHITE, bold=True, font=SERIF)
    section_label(sl, 7.85, 3.75, 4.5, "WHY", color=TEAL_LIGHT)
    add_text(sl, 7.85, 4.1, 4.5, 1.4,
             ["Lagrangian methods satisfy the constraint only in expectation and only at "
              "convergence (Lu §II-H, p. 11). A safety claim at deployment needs a shield, a "
              "fallback or an online test."], size=12.5, color=ON_DARK)
    takeaway(sl, "Safety holds at the optimisation level; it is not demonstrated at the deployment level.")
    footer(sl)
    set_notes(sl, "The prompt for this slide: separate a reward penalty, a constraint in the "
              "optimisation, empirical satisfaction, a formal guarantee, and training versus "
              "deployment safety. Safe-CQL has the constraint in the optimisation and is trivially "
              "safe during training. Satisfaction is only average and measured through proxies; "
              "there is no guarantee and nothing at deployment time.\nLikely question: is CQL "
              "itself a safety mechanism? No. CQL is conservative about value estimates of "
              "unsupported actions, which reduces extrapolation error but does not bound "
              "constraint violations.")
    return sl


def severity_cell(text):
    color = {"Critical": RED, "High": AMBER}.get(text, TEAL)
    return [(text, {"bold": True, "color": color})]


def slide_reviewers_12(prs):
    sl = new_slide(prs)
    header(sl, "Part E · Reviewers", "Reviewers 1 and 2: formulation and data are the real issues")
    rows = [["Comment", "Concern", "My verdict", "Severity", "Required change"],
            [[("R1 · ", {"bold": True, "color": TEAL}),
              ("State drops the PRB split and scheduler: Markov property violated (POMDP)", {})],
             "Mathematical formulation",
             "Partly justified: aₜ₋₁ = aₜ in these logs, so it cannot be learned from",
             severity_cell("High"),
             "State the bandit vs POMDP choice; test aₜ₋₁ on data with switches"],
            [[("R1 · ", {"bold": True, "color": TEAL}),
              ("Tabular cost over 3 load bins is too coarse for URLLC tails", {})],
             "Safety modelling",
             "Partly: robust for rare events, but not a tail metric",
             severity_cell("Medium"),
             "State-conditional cost model; bin sensitivity; p99/p99.9; CVaR variant"],
            [[("R2 · ", {"bold": True, "color": TEAL}),
              ("5 s steps belong to the Non-RT RIC, not the Near-RT RIC (10 ms–1 s)", {})],
             "Architecture",
             "Justified (Lu p. 14)",
             severity_cell("High"),
             "Reposition as an rApp / slow xApp, or redesign for ≤ 1 s"],
            [[("R2 · ", {"bold": True, "color": TEAL}),
              ("Static data: configuration fixed for each reservation, no causal effect of decisions", {})],
             "Dataset and methodology",
             "Justified; the paper admits it (p. 5)",
             severity_cell("Critical"),
             "Reframe as a one-step policy, or generate switching data"]]
    add_table(sl, 0.7, 1.75, [3.4, 1.75, 2.75, 1.0, 3.0], rows,
              row_heights=[0.4, 0.95, 0.85, 0.85, 0.95], size=11.5)
    takeaway(sl, "Reviewer 2's static-data point is the root cause; Reviewer 1's Markov point "
                 "follows from it.")
    footer(sl)
    set_notes(sl, "I do not simply agree with every comment. Reviewer 1's Markov point is formally "
              "right, but calling it fatal is overstated, and his fix (add the previous action) is "
              "impossible on these logs because the previous action always equals the current one. "
              "His tabular-cost point is partly contestable: the KPMs arrive at about 4 Hz, so "
              "high-resolution channel dynamics are not observable in this dataset anyway. "
              "Reviewer 2's two points are justified; the static data is the most fundamental "
              "issue, and Lu (p. 48) says the same about KPM-only traces.\nLikely question: can "
              "we argue that the configurations were randomised per reservation, like an "
              "experiment? Partly. That supports one-step effect estimates, but the paper itself "
              "shows configuration–load confounding (p. 4), and it gives nothing about switching.")
    return sl


def slide_reviewer_3(prs):
    sl = new_slide(prs)
    header(sl, "Part E · Reviewers", "Reviewer 3: baselines, novelty and writing")
    rows = [["Comment", "Concern", "My verdict", "Severity", "Required change"],
            [[("R3 · ", {"bold": True, "color": TEAL}), ("Only a BC baseline", {})],
             "Baselines", "Justified: CQL with λ = 0 is an ablation, not a competitor",
             severity_cell("High"),
             "Static and oracle rules, CQL + penalty, BCQ-Lag, CPQ, COptiDICE"],
            [[("R3 · ", {"bold": True, "color": TEAL}), ("Offline and safe CQL well studied: incremental", {})],
             "Novelty", "Justified: the paper says the algorithm is not novel (p. 2)",
             severity_cell("High"), "Narrow the claim, or move to offline→online"],
            [[("R3 · ", {"bold": True, "color": TEAL}), ("Writing errors; AI-style prose", {})],
             "Presentation", "Justified: “γ = 0.7 (Fig. 2).” on p. 4; “[?]” not in my copy",
             severity_cell("Medium"), "Full proofreading; align the text with the figures"]]
    add_table(sl, 0.7, 1.75, [2.0, 1.15, 2.4, 0.95, 2.25], rows,
              row_heights=[0.4, 1.05, 1.05, 1.05], size=11)
    add_box(sl, 9.75, 1.75, 2.85, 4.15, CARD)
    section_label(sl, 9.95, 1.9, 2.5, "SCORES (1–5)", color=TEAL)
    score_rows = [["", "R1", "R2", "R3"],
                  ["Relevance", "4", "4", "3"],
                  ["Technical", "3", "2", "2"],
                  ["Novelty", "3", "2", "2"],
                  ["Presentation", "5", "3", "2"]]
    add_table(sl, 9.95, 2.3, [1.15, 0.45, 0.45, 0.45], score_rows,
              row_heights=[0.38] * 5, size=11.5, header_size=11.5, bold_first_col=True)
    add_text(sl, 9.95, 4.35, 2.5, 1.5,
             ["Technical and novelty scores agree across reviewers; presentation scores do not "
              "(5 vs 2)."], size=11.5, color=MUTED)
    takeaway(sl, "Technical scores of 3, 2 and 2 agree: the paper needs new evidence, not only rewriting.")
    footer(sl)
    set_notes(sl, "Reviewer 3 is the harshest on writing. Two defects are visible in my copy: "
              "Section V-B starts with the fragment 'γ = 0.7 (Fig. 2).' and there is 'cost;In short' "
              "on p. 6. The missing reference '[?]' is not in the PDF I have, so the reviewed "
              "version may differ. On novelty: CPQ (Xu et al., AAAI 2022) is already a safe offline "
              "Q-learning method, and Yang et al. (2024) apply CQL and IQL to RAN slicing.")
    return sl


def slide_root_cause(prs):
    sl = new_slide(prs)
    header(sl, "Part E · Root cause", "Static logs cannot identify sequential decisions")
    section_label(sl, 0.7, 1.75, 6.0, "WHAT THE LOGS CONTAIN VS WHAT A POLICY DOES")
    labels = [("Reservation A", ["(21, PF)"] * 5, False),
              ("Reservation B", ["(39, RR)"] * 5, False),
              ("Learned policy", ["(21, PF)", "(39, RR)", "(39, RR)", "(21, PF)", "(39, RR)"], True)]
    for r, (label, cells, policy) in enumerate(labels):
        y = 2.15 + r * 0.8 + (0.2 if policy else 0)
        add_text(sl, 0.7, y, 1.35, 0.55, [label], size=12, color=NAVY, bold=True,
                 anchor=MSO_ANCHOR.MIDDLE)
        for c, text in enumerate(cells):
            x = 2.1 + c * 0.93
            fill = WHITE if policy else CARD
            add_box(sl, x, y, 0.85, 0.55, fill, line=TEAL if policy else None)
            add_text(sl, x, y, 0.85, 0.55, [text], size=10.5, color=NAVY, bold=True,
                     anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
            if policy and c > 0 and text != cells[c - 1]:
                add_text(sl, x - 0.24, y + 0.6, 0.4, 0.3, ["?"], size=14, color=RED, bold=True,
                         align=PP_ALIGN.CENTER)
    add_text(sl, 0.7, 5.05, 6.0, 0.85,
             [[("?", {"color": RED, "bold": True}),
               ("  A switch between configurations: never observed in 1,116 reservations, so its "
                "transition and its value are extrapolated.", {})]], size=12, color=BODY)
    add_box(sl, 7.0, 1.75, 5.6, 4.15, CARD)
    section_label(sl, 7.25, 1.9, 5.1, "THE TRACES SUPPORT", color=TEAL)
    bullets(sl, 7.25, 2.25, 5.15, 1.3, [
        "Association between (configuration, load) and KPIs",
        "Scheduler dominance of the latency tail within logged configurations",
        "One-step policy value on the logged support",
    ], size=12)
    section_label(sl, 7.25, 3.55, 5.1, "THEY CANNOT SUPPORT", color=RED)
    bullets(sl, 7.25, 3.9, 5.15, 1.2, [
        "Transitions after a switch, hence multi-step value",
        "OPE of switching policies (matching covers ≈ 40 %)",
        "Causal claims under configuration–load confounding",
    ], size=12, bullet_color=RED)
    add_text(sl, 7.25, 5.1, 5.15, 0.75,
             ["“A static set of KPMs is not enough to reconstruct a sequential decision problem.” "
              "(Lu §X-C, p. 48)"], size=11.5, color=MUTED, font=SERIF)
    takeaway(sl, "Use these traces for one-step analysis and calibration; train sequential "
                 "policies on data with logged switches.")
    footer(sl)
    set_notes(sl, "This is the core scientific problem. Each reservation of the dataset keeps one "
              "configuration, which the paper acknowledges on p. 5: no estimator observes a "
              "mid-episode switch. A learned policy switches configurations from one window to the "
              "next, which is never in the data. The same property holds for the ColO-RAN dataset "
              "according to its maintainers. Lu writes that production traces are useful for "
              "system identification, calibration or traffic generation, but not as a complete DRL "
              "benchmark unless paired with decision logs (p. 48).")
    return sl


def slide_static_baseline(prs):
    sl = new_slide(prs)
    header(sl, "Part E · A missing baseline", "A static configuration may already meet the budget")
    fig1 = [("(9, RR)", [0.00, 0.00, 0.03, 0.02]), ("(9, PF)", [0.02, 0.02, 0.27, 0.18]),
            ("(21, RR)", [0.00, 0.00, 0.03, 0.03]), ("(21, PF)", [0.05, 0.04, 0.19, 0.11]),
            ("(30, RR)", [0.18, 0.00, 0.04, 0.03]), ("(30, PF)", [0.03, 0.04, 0.21, 0.19]),
            ("(39, RR)", [0.00, 0.02, 0.03, 0.03]), ("(39, PF)", [0.05, 0.03, 0.18, 0.21])]
    rows = [["Action", "low", "med−", "med+", "high"]]
    colors = {}
    for r, (name, vals) in enumerate(fig1, start=1):
        rows.append([name] + [f"{v:.2f}" for v in vals])
        highlight = name == "(39, RR)"
        colors[(r, 0)] = (TAKEAWAY if highlight else WHITE, NAVY, True)
        for c, v in enumerate(vals, start=1):
            tint = GREEN_TINT if v <= 0.03 else (AMBER_TINT if v <= 0.10 else RED_TINT)
            colors[(r, c)] = (tint, BODY, highlight)
    add_table(sl, 0.7, 1.75, [1.4, 1.0, 1.0, 1.0, 1.0], rows,
              row_heights=[0.4] + [0.4] * 8, size=12, header_size=12, cell_colors=colors)
    add_text(sl, 0.7, 5.45, 5.4, 0.5,
             ["URLLC violation rate per action and load, read from Fig. 1 of the paper. "
              "Green ≤ 0.03 (the budget)."], size=11, color=MUTED)
    add_box(sl, 6.65, 1.75, 5.95, 4.15, CARD)
    section_label(sl, 6.9, 1.9, 5.5, "HYPOTHESIS TO VERIFY", color=TEAL)
    points = [
        "(39, RR) stays ≤ 0.03 at every load level, so it is feasible for d = 0.03 under any load mix.",
        "eMBB throughput rises with eMBB PRBs (r = +0.73), and RR matches or beats PF in "
        "throughput (paper p. 3–4).",
        "So “always (39, RR)” is plausibly near-optimal under the paper's own tabular model.",
    ]
    for i, text in enumerate(points):
        y = 2.3 + i * 0.85
        add_circle_number(sl, 6.9, y, 0.38, i + 1, size=12)
        add_text(sl, 7.45, y - 0.03, 4.95, 0.8, [text], size=12.5, color=BODY)
    add_text(sl, 6.9, 4.9, 5.5, 0.95,
             [[("P0 test (≈ 1 day): ", {"bold": True, "color": NAVY}),
               ("evaluate always-(39, RR) and a per-load constrained oracle on cluster 1 with the "
                "same estimators. If they match Safe-CQL, the paper becomes an audit paper.", {})]],
             size=12.5, color=BODY)
    takeaway(sl, "Before adding any algorithm, check that learning beats the best fixed configuration.")
    footer(sl)
    set_notes(sl, "The table reproduces the values printed in Fig. 1 of my paper. Every RR row is "
              "within budget except (30, RR) at low load (0.18), which probably comes from few "
              "samples; the paper does not show cell counts. (39, RR) gives the most eMBB PRBs and "
              "is within budget everywhere. This is a hypothesis, not a result: I have not yet "
              "computed its throughput on the held-out cluster. The per-load oracle is a small "
              "linear programme over the empirical reward and cost tables (8 actions × load bins). "
              "Also note: Fig. 1 has four load levels while Eq. 10 describes three; this must be "
              "made consistent.")
    return sl


def slide_revision_plan(prs):
    sl = new_slide(prs)
    header(sl, "Part E · Revision plan", "Prioritised revision plan")
    pri = {"P0": RED, "P1": AMBER, "P2": TEAL, "P3": MUTED}

    def p(code):
        return [(code, {"bold": True, "color": pri[code]})]

    rows = [["Priority", "Action", "Answers", "Effort"],
            [p("P0"), "Static and per-load oracle baselines on the held-out cluster", "R3, audit", "1–2 days"],
            [p("P0"), "Reposition: rApp / slow xApp; “latency-sensitive slice”; qualify “safe”", "R2, audit", "2–3 days"],
            [p("P1"), "Decision model: contextual bandit vs CMDP, with an empirical test", "R1, R2", "1 week"],
            [p("P1"), "Safe offline baselines (BCQ-Lag, CPQ, COptiDICE via OSRL); CQL + penalty sweep", "R3", "1–2 weeks"],
            [p("P1"), "≥ 5 seeds for every method, bootstrap CIs, fix the Fig. 3 claim, state the selection protocol", "Statistics", "3–5 days"],
            [p("P2"), "State-conditional cost model, bin sensitivity, p99/p99.9, CVaR variant", "R1", "1–2 weeks"],
            [p("P2"), "Full proofreading pass", "R3", "2 days"],
            [p("P3"), "Data with configuration switches from ns-3 5G-LENA", "R1, R2", "1–3 months"]]
    add_table(sl, 0.7, 1.75, [1.1, 7.6, 1.6, 1.6], rows,
              row_heights=[0.4] + [0.46] * 8, size=12, header_size=12)
    takeaway(sl, "If P0 shows the static rule matches Safe-CQL, the paper becomes an audit paper "
                 "and the RL moves to simulation.")
    footer(sl)
    set_notes(sl, "Ordered by scientific importance and cost. P0 items can be done this month and "
              "decide the fate of the paper. P1 items answer the reviewers directly. P3 is the "
              "bridge to the thesis core. Effort estimates are mine, assuming the existing "
              "pipeline.\nLikely question: which venue for a revised version? See slide 29.")
    return sl


def slide_positioning(prs):
    sl = new_slide(prs)
    header(sl, "Part F · Positioning", "Where the paper stands in the research landscape")
    rows = [["Research direction", "Survey evidence", "What my paper does", "Remaining limitation", "Opportunity"],
            ["Offline RL for O-RAN", "Lu §II-G, §IX-A; 2OffRAN", "CQL trained on logs", "Static configurations", "Decision-logged data"],
            ["Safe / constrained RL", "Lu §II-H, §VIII-A; SafeSlice", "CMDP + adaptive λ, offline", "Mean-rate, myopic cost; no shield", "Chance / CVaR constraint + shield"],
            ["eMBB/URLLC coexistence", "Adhikari §III, §V; Haque §V", "Slice PRBs + scheduler", "LTE, 20 ms, no mini-slots", "NR numerologies in 5G-LENA"],
            ["RIC placement and timescale", "Lu §III, p. 14", "Claims Near-RT", "5 s is a Non-RT loop", "100 ms–1 s loop, or rApp framing"],
            ["Offline→online adaptation", "Lu §XII-A, p. 54", "Not addressed", "—", "Thesis core"],
            ["Benchmarks and reproducibility", "Lu §X-D, §XII-G", "2–5 seeds, one dataset", "No CIs, no code release", "≥ 10 seeds, CIs, released code"]]
    add_table(sl, 0.7, 1.75, [2.45, 2.45, 2.25, 2.4, 2.35], rows,
              row_heights=[0.4] + [0.6] * 6, size=11.5, header_size=11.5, bold_first_col=True)
    takeaway(sl, "Addressed: offline RL with a constraint. Not addressed: switching dynamics, tails, "
                 "timescale, offline→online.")
    footer(sl)
    set_notes(sl, "Built from the three surveys plus verified related work. 2OffRAN (Navarro et al., "
              "ICMLCN 2025) trains a handover agent offline and evaluates it with off-policy methods; "
              "SafeSlice (Nagib et al., ICMLCN 2025) does safe slicing online with action "
              "projection. I have only read their abstracts and the survey descriptions, so I am "
              "not making detailed comparisons yet.")
    return sl


def slide_directions(prs):
    sl = new_slide(prs)
    header(sl, "Part F · Research directions", "Ranked research directions")
    rows = [["#", "Direction", "Novelty", "Importance", "Feasibility", "Credibility", "Alignment", "Total"],
            ["1", "Constrained offline→online slice-configuration control with tail-latency constraints", "3", "5", "3", "4", "5", "20"],
            ["2", "Honest revision of Safe-CQL: constrained one-step policy from traces + audit", "2", "3", "5", "3", "5", "18"],
            ["3", "Trace-calibrated ns-3 5G-LENA twin with policy-level fidelity", "3", "4", "3", "4", "4", "18"],
            ["4", "Off-policy evaluation and support diagnostics for configuration policies", "3", "3", "4", "3", "4", "17"]]
    colors = {(1, c): (TAKEAWAY, NAVY, True) for c in range(8)}
    add_table(sl, 0.7, 1.75, [0.45, 5.65, 0.95, 1.1, 1.1, 1.1, 1.0, 0.55], rows,
              row_heights=[0.4] + [0.62] * 4, size=12, header_size=11.5, cell_colors=colors)
    section_label(sl, 0.7, 4.75, 11.9, "SET ASIDE FOR NOW", color=TEAL)
    add_text(sl, 0.7, 5.1, 11.9, 0.85,
             ["Multi-xApp MARL (premature before single-cell credibility) · LLM / agentic control "
              "(weak alignment) · mini-slot puncturing dApp (sub-10 ms, outside RIC reach) · "
              "RIS/UAV coexistence (different expertise)."], size=12.5, color=BODY)
    takeaway(sl, "Do 2 now, build 3 as the enabler, and make 1 the thesis core.")
    footer(sl)
    set_notes(sl, "Scores are my judgement on a 1–5 scale: novelty evidence, scientific importance, "
              "feasibility, experimental credibility, alignment with my current work. Novelty "
              "scores are provisional until a systematic search is done. Details for each "
              "direction (question, contribution, data, baselines, risks, effort) are in "
              "docs/research_review.md, Deliverable 4.")
    return sl


def slide_core_direction(prs):
    sl = new_slide(prs)
    header(sl, "Part F · Recommended core", "Core direction: constrained offline-to-online control")
    add_box(sl, 0.7, 1.75, 6.0, 1.75, NAVY)
    section_label(sl, 0.95, 1.9, 5.5, "RESEARCH QUESTION", color=TEAL_LIGHT)
    add_text(sl, 0.95, 2.25, 5.55, 1.2,
             ["Can a policy pre-trained on logged slice-configuration decisions be fine-tuned "
              "online with bounded cumulative tail-latency violations under traffic shift, faster "
              "than constrained RL from scratch?"], size=14, color=WHITE, bold=True, font=SERIF)
    section_label(sl, 0.7, 3.7, 6.0, "EXPECTED CONTRIBUTIONS")
    contribs = ["Decision-logged eMBB / latency-sensitive dataset generator with known behaviour "
                "propensities",
                "Support-aware shield and chance / CVaR latency constraint for offline→online "
                "fine-tuning",
                "Evidence on cumulative violations and sample efficiency against online baselines"]
    for i, text in enumerate(contribs):
        y = 4.08 + i * 0.62
        add_circle_number(sl, 0.7, y, 0.38, i + 1, size=12)
        add_text(sl, 1.25, y - 0.02, 5.45, 0.6, [text], size=12.5, color=BODY)
    add_box(sl, 7.0, 1.75, 5.6, 4.15, CARD)
    section_label(sl, 7.25, 1.9, 5.1, "FORMULATION CHANGES", color=TEAL)
    bullets(sl, 7.25, 2.25, 5.15, 1.7, [
        "Constraint P(ℓ > L_max) ≤ ε, or a CVaR, instead of a mean rate",
        "Quantile cost critic with a pessimistic (upper-bound) estimate",
        "Decision period 100 ms–1 s; aₜ₋₁ and switching cost in the state",
        "Shield: choose among actions whose cost upper bound is ≤ d",
    ], size=12)
    section_label(sl, 7.25, 3.6, 5.1, "RISKS", color=RED)
    bullets(sl, 7.25, 3.95, 5.15, 1.0, [
        "Simulated latency tail may differ from the testbed's",
        "Slicing in 5G-LENA needs custom scheduler code",
        "Tail metrics need many packets per condition",
    ], size=12, bullet_color=RED)
    add_text(sl, 7.25, 5.1, 5.15, 0.7,
             ["Novelty to verify: Nagib et al. 2023, SafeSlice 2025, Yang et al. 2024, 2OffRAN "
              "2025, FISOR 2024."], size=11, color=MUTED)
    takeaway(sl, "Lu names this pipeline as the first open direction (§XII-A, p. 54); Safe-CQL "
                 "becomes its offline stage.")
    footer(sl)
    set_notes(sl, "Why this direction: it reuses everything I built (audit, CQL, Lagrangian, cost "
              "model) as the offline stage, and it fixes the two fundamental objections, static "
              "data and timescale, by generating my own decision logs in ns-3 5G-LENA with "
              "randomised switching behaviour policies whose propensities I know. The online stage "
              "is where safety becomes measurable: cumulative violations while fine-tuning. "
              "Feasibility: four to six months for a first paper if the simulator set-up (slide 27) "
              "is ready in the first two. Main failure mode: offline pre-training gives little "
              "gain because online constrained learning is already fast in simulation; that would "
              "still be a reportable result.")
    return sl


def slide_datasets(prs):
    sl = new_slide(prs)
    header(sl, "Part G · Data", "Datasets: what each one can and cannot support")
    rows = [["Dataset", "Content (checked against documentation)", "Actions logged?", "Best use"],
            ["ns-3 5G-LENA decision logs (to build)", "(s, a, r, s′, Δt, z) with behaviour propensities, as in Lu Eq. 32",
             [("Yes, with switches", {"bold": True, "color": TEAL})], "Offline RL; counterfactual evaluation"],
            ["Open RAN Commercial Traffic Twinning (WINES)", "1 BS, 50 PRBs, 8 static UEs; 5 PRB splits × {RR, PF}; 3 clusters; "
             "PHY/MAC KPMs + MGEN latency; CC-BY-SA-4.0",
             [("Static per reservation", {"bold": True, "color": RED})], "Traffic driver, calibration, one-step analysis"],
            ["ColO-RAN (Colosseum)", "3 slices (eMBB / MTC / URLLC); RR, WF or PF per slice; 250 ms logs",
             [("Static per experiment", {"bold": True, "color": RED})], "Cross-dataset generalisation"],
            ["Colosseum COMMAG", "4 BSs, 15 PRBs, 3 slices, 40 UEs; configurations tr0–tr5",
             [("Static configurations", {"bold": True, "color": RED})], "Multi-cell sanity checks"],
            ["Public O-RAN dataset catalogue (Couto et al. 2024)", "Survey of public O-RAN datasets",
             "Varies", "Search for further candidates"]]
    add_table(sl, 0.7, 1.75, [2.75, 4.65, 1.95, 2.55], rows,
              row_heights=[0.4, 0.62, 0.8, 0.62, 0.62, 0.62], size=11.5, header_size=11.5,
              bold_first_col=True)
    add_text(sl, 0.7, 5.55, 11.9, 0.45,
             ["Slice labels in the Colosseum datasets are slice IDs assigned per UE; “URLLC” "
              "there is not 3GPP URLLC traffic."], size=11.5, color=MUTED)
    takeaway(sl, "None of the datasets checked logs action switches: generate them in simulation, "
                 "use the traces to calibrate.")
    footer(sl)
    set_notes(sl, "Verified from the dataset documentation: the twinning dataset uses one base "
              "station with 10 MHz (50 PRBs), 8 static UEs, UEs 1–4 on the eMBB slice and UEs 5–8 on "
              "the URLLC slice, traffic twinned from LTE traces of three base stations in Madrid, "
              "and CC-BY-SA-4.0. The ColO-RAN and COMMAG details come from their repositories and "
              "maintainer comments; I still need to check their licences. Observational traces "
              "without logged scheduler actions only allow association and one-step analysis on "
              "the logged support.")
    return sl


def slide_realism(prs):
    sl = new_slide(prs)
    header(sl, "Part G · Infrastructure", "Five levels of experimental realism are not equivalent")
    levels = [("1", "Abstract RL environment", "Analytical queues and rates. Fast, but no PHY/MAC realism.", None),
              ("2", "Trace-driven", "Replays logged KPMs. Real data, but no counterfactuals.", "Current paper"),
              ("3", "Calibrated simulator", "ns-3 + 5G-LENA with trace-driven traffic. Counterfactuals and NR models.", "Next paper (minimum)"),
              ("4", "Simulator + RIC loop", "NORI or ns-O-RAN with an OSC Near-RT RIC over E2. Real interfaces and loop delay.", "Journal version"),
              ("5", "Software / physical testbed", "srsRAN or OAI + RIC, Colosseum. Real stacks; costly, small scale.", "Optional")]
    base = 5.85
    for i, (num, name, text, tag) in enumerate(levels):
        x = 0.7 + i * 2.42
        h = 1.95 + i * 0.42
        y = base - h
        highlight = tag in ("Next paper (minimum)",)
        add_box(sl, x, y, 2.25, h, NAVY if highlight else CARD)
        tcolor = WHITE if highlight else NAVY
        add_text(sl, x + 0.18, y + 0.15, 1.95, 0.75,
                 [[(f"{num}  ", {"color": TEAL_LIGHT if highlight else TEAL}), (name, {})]],
                 size=14, color=tcolor, bold=True, font=SERIF)
        add_text(sl, x + 0.18, y + 0.9, 1.95, h - 1.0, [text], size=12,
                 color=ON_DARK if highlight else BODY)
        if tag:
            add_text(sl, x, y - 0.38, 2.25, 0.3, [tag.upper()], size=11,
                     color=RED if tag == "Current paper" else TEAL, bold=True, align=PP_ALIGN.CENTER)
    takeaway(sl, "Minimum for the next paper: level 3, calibrated on level-2 traces; level 4 "
                 "strengthens a journal version.")
    footer(sl)
    set_notes(sl, "The levels must not be presented as interchangeable. My paper is at level 2. "
              "Level 3 gives counterfactuals and switching, which level 2 cannot. Level 4 adds the "
              "real E2 interface and loop timing: ns-O-RAN (Lacava et al., WNS3 2023) connects "
              "ns-3 to the OSC Near-RT RIC through e2sim but, at publication, only handover control; "
              "NORI (SBrT 2025) claims 5G-LENA support and E2 metric collection. I have only read "
              "their abstracts. Claiming O-RAN realism from level 3 alone would be wrong, since "
              "5G-LENA does not implement the O-RAN architecture.")
    return sl


def slide_architecture(prs):
    sl = new_slide(prs)
    header(sl, "Part G · Infrastructure", "Stage 1 set-up: ns-3 5G-LENA with a Python control loop")
    add_box(sl, 0.7, 1.75, 5.2, 2.75, CARD)
    add_text(sl, 0.95, 1.88, 4.8, 0.35, ["ns-3 + 5G-LENA (C++)"], size=14, color=NAVY, bold=True, font=SERIF)
    inner = [("Traffic", "eMBB video or full buffer + latency-sensitive Poisson small packets; load from the twinning traces"),
             ("gNB", "Numerology μ = 1–2; two slices via RB masks or BWPs; RR / PF / QoS schedulers"),
             ("Measurement", "Per-packet latency, slice throughput, buffer occupancy")]
    for i, (head, text) in enumerate(inner):
        y = 2.3 + i * 0.72
        add_box(sl, 0.95, y, 4.7, 0.64, WHITE)
        add_text(sl, 1.1, y + 0.05, 4.45, 0.58,
                 [[(head + ": ", {"bold": True, "color": TEAL}), (text, {})]], size=11.5, color=BODY,
                 anchor=MSO_ANCHOR.MIDDLE)
    add_box(sl, 7.4, 1.75, 5.2, 2.75, NAVY)
    add_text(sl, 7.65, 1.88, 4.8, 0.35, ["Python agent (PyTorch)"], size=14, color=WHITE, bold=True, font=SERIF)
    bullets(sl, 7.65, 2.35, 4.8, 2.1, [
        "Policy: CQL-Lagrangian, then online fine-tuning",
        "Shield: keep actions whose cost upper bound is ≤ d",
        "Logger: (s, a, r, s′, Δt, z, π_b) for every decision",
        "Inference time measured on the target CPU",
    ], size=12.5, color=ON_DARK, bullet_color=TEAL_LIGHT, gap=6)
    add_arrow(sl, 5.95, 2.6, 7.35, 2.6)
    add_text(sl, 5.95, 2.15, 1.4, 0.4, ["KPMs every 0.1–1 s"], size=10.5, color=TEAL, bold=True,
             align=PP_ALIGN.CENTER)
    add_arrow(sl, 7.35, 3.6, 5.95, 3.6)
    add_text(sl, 5.95, 3.68, 1.4, 0.55, ["PRB quota, scheduler"], size=10.5, color=TEAL, bold=True,
             align=PP_ALIGN.CENTER)
    add_text(sl, 5.95, 3.0, 1.4, 0.35, ["ns3-ai / ns3-gym"], size=10.5, color=MUTED, align=PP_ALIGN.CENTER)
    stages = [("Stage 0 · now–1 mo", "Revise the paper on existing data"),
              ("Stage 1 · 1–3 mo", "This set-up; decision-logged datasets"),
              ("Stage 2 · 3–6 mo", "Offline→online under traffic shifts"),
              ("Stage 3 · 6–12 mo", "E2 via NORI / ns-O-RAN + OSC RIC")]
    for i, (head, text) in enumerate(stages):
        x = 0.7 + i * 3.0
        add_box(sl, x, 4.7, 2.85, 0.85, WHITE if i != 1 else TAKEAWAY, line=TEAL)
        add_text(sl, x + 0.12, 4.75, 2.65, 0.8,
                 [[(head, {"bold": True, "color": NAVY})], [(text, {"color": BODY})]], size=11.5)
    add_text(sl, 0.7, 5.65, 11.9, 0.35,
             [[("Engineering risks: ", {"bold": True, "color": RED}),
               ("run time for tail statistics, reconfiguration during a run, 5G-LENA / ns-3 version drift.", {})]],
             size=11.5, color=BODY)
    takeaway(sl, "This set-up produces decision logs with known propensities, exactly what the "
                 "trace dataset lacks.")
    footer(sl)
    set_notes(sl, "Verified facts: 5G-LENA v4.1 (July 2025) works with ns-3.45 and offers RR, PF and "
              "MR schedulers with temporal fairness, a 5QI-aware QoS scheduler, OFDMA and TDMA, and "
              "several numerologies. An RL scheduler example with ns3-gym came out of GSoC 2024. "
              "Slicing is not a built-in feature: it must be emulated with bandwidth parts or a "
              "custom RB-mask scheduler, which is engineering work. Data flow: ns-3 aggregates KPMs "
              "every decision period, passes them through shared memory to the Python agent, and "
              "applies the returned slice quota and scheduler at the next slot boundary.")
    return sl


def slide_protocol(prs):
    sl = new_slide(prs)
    header(sl, "Part G · Protocol", "Evaluation protocol: each claim gets its comparison")
    rows = [["Claim", "Essential comparison"],
            ["Learning beats configuration rules", "Best static feasible configuration; per-load oracle; QoS scheduler"],
            ["Better than existing safe offline RL", "CQL-Lag, BCQ-Lag, CPQ, COptiDICE, CQL + penalty sweep"],
            ["The constraint matters", "Same method with λ = 0"],
            ["Offline pre-training helps safe online learning", "PPO-Lag / SAC-Lag from scratch; offline only; unconstrained fine-tuning"],
            ["Each component matters", "Ablations: cost model, shield, aₜ₋₁, history length"]]
    add_table(sl, 0.7, 1.75, [2.9, 4.1], rows, row_heights=[0.4] + [0.74] * 5, size=12,
              header_size=12, bold_first_col=True)
    add_box(sl, 7.95, 1.75, 4.65, 4.15, CARD)
    section_label(sl, 8.2, 1.9, 4.2, "METRICS", color=TEAL)
    bullets(sl, 8.2, 2.22, 4.25, 2.2, [
        "eMBB throughput: mean and 5th percentile",
        "Latency p50 / p99 / p99.9, with packet counts",
        "Deadline-miss rate P(ℓ > L_max)",
        "Violation frequency and severity: E[(c − d)⁺], CVaR",
        "Cumulative violations while fine-tuning",
        "Inference time on the target CPU",
    ], size=11.5, gap=2)
    section_label(sl, 8.2, 4.1, 4.2, "STATISTICS AND DATA HYGIENE", color=TEAL)
    bullets(sl, 8.2, 4.42, 4.25, 1.1, [
        "≥ 10 seeds (simulation), ≥ 5 (offline); bootstrap 95 % CIs",
        "Leave-one-cluster-out and time-block splits",
        "Hyperparameters chosen on validation data only",
    ], size=11.5, gap=2)
    takeaway(sl, "Separate mean from tail performance, and empirical safety from guarantees.")
    footer(sl)
    set_notes(sl, "Baselines are chosen per claim rather than all at once. OSRL (Liu et al. 2023) "
              "provides BCQ-Lag, CPQ and COptiDICE implementations. For statistics I will follow "
              "Agarwal et al. (NeurIPS 2021): interquartile mean and bootstrap confidence intervals, "
              "plus the fraction of seeds that violate the budget. p99.9 needs at least about 10⁴ "
              "packets per condition. Trace-driven results only support associational and one-step "
              "conclusions; causal statements require the simulator.")
    return sl


def slide_next_steps(prs):
    sl = new_slide(prs)
    header(sl, "Part H · Next steps", "Decisions and next steps to agree today")
    cols = [("NOW · ≤ 4 WEEKS", ["P0: static and oracle baselines",
                                 "Reposition: rApp, latency-sensitive slice, qualified “safe”",
                                 "≥ 5 seeds, CIs; OSRL baselines",
                                 "Systematic related-work search"]),
            ("MEDIUM TERM · 1–6 MONTHS", ["ns-3 5G-LENA two-slice scenario with per-packet latency",
                                         "Decision-logged dataset generator",
                                         "Trace calibration with policy-level fidelity",
                                         "Offline→online constrained experiments"]),
            ("LONGER TERM · 6–18 MONTHS", ["E2 loop via NORI / ns-O-RAN + OSC RIC",
                                           "Testbed validation (srsRAN or Colosseum)",
                                           "Multi-cell and multi-xApp extension",
                                           "Runtime assurance: shield + fallback"])]
    for i, (head, items) in enumerate(cols):
        x = 0.7 + i * 4.03
        add_box(sl, x, 1.75, 3.85, 2.55, CARD if i else NAVY)
        add_text(sl, x + 0.22, 1.88, 3.45, 0.3, [head], size=12,
                 color=TEAL_LIGHT if i == 0 else TEAL, bold=True)
        bullets(sl, x + 0.22, 2.25, 3.45, 2.0, items, size=12,
                color=ON_DARK if i == 0 else BODY, bullet_color=TEAL_LIGHT if i == 0 else TEAL, gap=3)
    section_label(sl, 0.7, 4.45, 11.9, "QUESTIONS FOR MY SUPERVISORS", color=TEAL)
    add_text(sl, 0.7, 4.78, 11.9, 0.8,
             ["1. Quick revision of the paper, or fold it into the simulator paper?   "
              "2. Thesis scope: configuration level (rApp / xApp) or scheduling level (dApp)?   "
              "3. Is LTE-twinned data acceptable as the main evidence?   "
              "4. Colosseum access, or commit to ns-3 + NORI?"], size=12.5, color=BODY)
    add_text(sl, 0.7, 5.55, 11.9, 0.45,
             [[("Venue fit (deadlines not checked): ", {"bold": True, "color": NAVY}),
               ("revised paper → ICMLCN, NetSoft, CNSM, ICC/Globecom workshops; core paper → IEEE "
                "TMLCN, TNSM, TCCN, OJ-COMS.", {})]], size=12, color=BODY)
    takeaway(sl, "Agree today on the thesis scope, and on the fate of the paper once the P0 test is done.")
    footer(sl)
    set_notes(sl, "What I need from this meeting: a decision on the four questions. My "
              "recommendation: configuration-level scope; run P0 before deciding the paper's fate; "
              "use the LTE traces as traffic and calibration input, not as the main evidence; start "
              "with ns-3 5G-LENA and add E2 later. Venues are suggestions based on where comparable "
              "work appeared (SafeSlice and 2OffRAN at ICMLCN 2025); I have not checked current "
              "deadlines and acceptance is not guaranteed anywhere.")
    return sl


def slide_references(prs):
    sl = new_slide(prs)
    header(sl, "References", "References")
    refs = [
        "[1] Haque et al., “A Comprehensive Survey of 5G URLLC and Challenges in the 6G Era,” IEEE COMST, 2025.",
        "[2] Lu et al., “Deep Reinforcement Learning for 6G AI-RAN: A Comprehensive Survey,” arXiv, 2026.",
        "[3] Adhikari, Jaseemuddin, Anpalagan, “Resource Allocation for Co-Existence of eMBB and URLLC Services in 6G Wireless Networks: A Survey,” IEEE Access, vol. 12, 2024.",
        "[4] Ben Cheikh, Chaouchi, Laouiti, Yellas, “Offline Safe RL for eMBB/URLLC Resource Allocation in O-RAN using Real Network Traces,” manuscript (rejected).",
        "[5] Bonati et al., “Twinning Commercial Network Traces on Experimental Open RAN Platforms,” ACM WiNTECH (MobiCom), 2024.",
        "[6] Polese et al., “ColO-RAN: Developing ML-based xApps for Open RAN Closed-loop Control,” IEEE TMC, 2022.",
        "[7] Kumar et al., “Conservative Q-Learning for Offline RL,” NeurIPS, 2020.",
        "[8] Xu et al., “Constraints Penalized Q-learning for Safe Offline RL,” AAAI, 2022.",
        "[9] Liu et al., “Datasets and Benchmarks for Offline Safe RL” (OSRL/DSRL), 2023.",
        "[10] Zheng et al., “Safe Offline RL with Feasibility-Guided Diffusion Model” (FISOR), ICLR, 2024.",
        "[11] Yang et al., “Advancing RAN Slicing with Offline Reinforcement Learning,” 2024.",
        "[12] Navarro et al., “2OffRAN: Offline Off-Policy RL for Safe Handover in O-RAN,” IEEE ICMLCN, 2025.",
        "[13] Nagib et al., “SafeSlice: Enabling SLA-compliant O-RAN Slicing via Safe DRL,” IEEE ICMLCN, 2025.",
        "[14] Nagib et al., “Safe and Accelerated DRL-based O-RAN Slicing: A Hybrid Transfer Learning Approach,” IEEE JSAC, 2023.",
        "[15] Alsenwi et al., “Intelligent Resource Slicing for eMBB and URLLC Coexistence in 5G and Beyond: A DRL Based Approach,” IEEE TWC, 2021.",
        "[16] Lacava et al., “ns-O-RAN: Simulating O-RAN 5G Systems in ns-3,” WNS3, 2023.",
        "[17] “Enabling NS-3 Simulations Integrated with Latest Versions of Open RAN Near-RT RICs” (NORI), SBrT, 2025.",
        "[18] CTTC, 5G-LENA ns-3 NR module, v4.1, 2025.",
        "[19] Tsampazi et al., “PandORA: Automated Design and Comprehensive Evaluation of DRL Agents for Open RAN,” IEEE TMC, 2024.",
        "[20] Agarwal et al., “Deep RL at the Edge of the Statistical Precipice,” NeurIPS, 2021.",
        "[21] Couto et al., “A Survey of Public Datasets for O-RAN,” Annals of Telecommunications, 2024.",
    ]
    half = 11
    for col, chunk in enumerate((refs[:half], refs[half:])):
        add_text(sl, 0.7 + col * 6.1, 1.75, 5.8, 5.0, chunk, size=10.5, color=BODY, space_after=4)
    footer(sl)
    set_notes(sl, "Survey page numbers cited on the slides refer to the PDF pages of the supplied "
              "files. References [11], [12], [16] and [17] were checked at abstract level only.")
    return sl


def slide_appendix_divider(prs):
    sl = new_slide(prs)
    sl.background.fill.solid()
    sl.background.fill.fore_color.rgb = rgb(NAVY_BG)
    add_text(sl, 0.9, 2.3, 11.0, 0.4, ["Appendix"], size=16, color=TEAL_LIGHT, bold=True)
    add_text(sl, 0.9, 2.8, 11.0, 0.95, ["Detailed survey material"], size=36, color=WHITE,
             bold=True, font=SERIF)
    add_text(sl, 0.9, 3.85, 10.5, 1.0,
             ["Original slides kept intact for reference: survey structures, URLLC PHY/MAC detail, "
              "DRL methods and O-RAN use cases, coexistence mechanisms and results."],
             size=16, color=ON_DARK)
    footer(sl, dark=True)
    set_notes(sl, "Everything after this divider is the survey material from the previous version, "
              "unchanged, for questions.")
    return sl


# --------------------------------------------------------------------------
# Ordering and numbering
# --------------------------------------------------------------------------

def reorder(prs, ordered_slides):
    sld_id_lst = prs.slides._sldIdLst
    by_part = {}
    for sld_id in list(sld_id_lst):
        by_part[prs.part.related_part(sld_id.rId)] = sld_id
    for sld_id in list(sld_id_lst):
        sld_id_lst.remove(sld_id)
    for slide in ordered_slides:
        sld_id_lst.append(by_part[slide.part])


def renumber(prs):
    for number, slide in enumerate(prs.slides, start=1):
        for shp in slide.shapes:
            if not shp.has_text_frame:
                continue
            is_number = shp.name == "PageNumber" or (
                shp.left > Inches(11.9) and shp.top > Inches(6.8)
                and shp.text_frame.text.strip().isdigit())
            if is_number:
                replace_runs(shp, [str(number)])


def modify_presentation(src=SRC, dst=DST):
    if src == dst:
        raise SystemExit("Refusing to overwrite the source deck; choose another output name.")
    prs = Presentation(src)
    _NOTES_BODY["element"] = prs.slides[0].notes_slide.notes_placeholder._element
    orig = edit_existing(prs)

    new = {
        "exec": slide_exec_diagnosis(prs),
        "table": slide_survey_table(prs),
        "implications": slide_survey_implications(prs),
        "paper": slide_paper_summary(prs),
        "audit": slide_claim_audit(prs),
        "safe": slide_safe_ladder(prs),
        "rev12": slide_reviewers_12(prs),
        "rev3": slide_reviewer_3(prs),
        "root": slide_root_cause(prs),
        "static": slide_static_baseline(prs),
        "plan": slide_revision_plan(prs),
        "position": slide_positioning(prs),
        "directions": slide_directions(prs),
        "core": slide_core_direction(prs),
        "data": slide_datasets(prs),
        "realism": slide_realism(prs),
        "arch": slide_architecture(prs),
        "protocol": slide_protocol(prs),
        "next": slide_next_steps(prs),
        "refs": slide_references(prs),
        "appendix": slide_appendix_divider(prs),
    }

    main = [orig[1], orig[2], new["exec"],
            orig[3], orig[8], orig[12], orig[17], orig[19], orig[20], orig[26], orig[34],
            new["table"], new["implications"],
            new["paper"], new["audit"], new["safe"], new["rev12"], new["rev3"], new["root"],
            new["static"], new["plan"],
            new["position"], new["directions"], new["core"],
            new["data"], new["realism"], new["arch"], new["protocol"],
            new["next"], new["refs"], new["appendix"]]
    appendix = [orig[i] for i in (4, 5, 6, 7, 9, 10, 11, 13, 14, 15, 16, 18, 21, 22, 23, 24,
                                  25, 27, 28, 29, 30, 31, 32, 33)]
    ordered = main + appendix
    assert len(ordered) == len(prs.slides), "every slide must appear exactly once"
    reorder(prs, ordered)
    renumber(prs)
    # The survey overview pointed to the structure maps (old slides 4–6), now in the appendix.
    for link, target in (("Text 10", 4), ("Text 19", 5), ("Text 28", 6)):
        replace_runs(shape_by_name(orig[3], link), [f"Slide {ordered.index(orig[target]) + 1}  →"])
    prs.save(dst)
    print(f"Saved {dst} ({len(prs.slides)} slides; {len(main)} main incl. divider, "
          f"{len(appendix)} appendix)")


if __name__ == "__main__":
    args = sys.argv[1:]
    modify_presentation(*(args[:2] if args else []))
