from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT

OUT = "/sessions/magical-bold-goodall/mnt/Medicare_Dashboard/Claude Cowork for Actuaries - Lesson 01/Guided/Process-Documentation/dashboard-process.pdf"

styles = getSampleStyleSheet()
body = ParagraphStyle('body', parent=styles['BodyText'], fontName='Helvetica',
                     fontSize=10, leading=14, spaceAfter=6, alignment=TA_LEFT)
h1 = ParagraphStyle('h1', parent=styles['Heading1'], fontName='Helvetica-Bold',
                   fontSize=18, leading=22, spaceAfter=10, textColor=colors.HexColor('#1F3A5F'))
h2 = ParagraphStyle('h2', parent=styles['Heading2'], fontName='Helvetica-Bold',
                   fontSize=13, leading=16, spaceBefore=12, spaceAfter=6,
                   textColor=colors.HexColor('#1F3A5F'))
h3 = ParagraphStyle('h3', parent=styles['Heading3'], fontName='Helvetica-Bold',
                   fontSize=11, leading=14, spaceBefore=8, spaceAfter=4)
subtitle = ParagraphStyle('sub', parent=body, fontName='Helvetica-Oblique',
                         fontSize=10, textColor=colors.HexColor('#555555'))
mono = ParagraphStyle('mono', parent=body, fontName='Courier', fontSize=9, leading=12)

doc = SimpleDocTemplate(OUT, pagesize=letter,
                        leftMargin=0.75*inch, rightMargin=0.75*inch,
                        topMargin=0.75*inch, bottomMargin=0.75*inch,
                        title="Claims PMPM Dashboard - Process Documentation",
                        author="NonSentience Health")

story = []

def P(t, s=body): story.append(Paragraph(t, s))
def SP(h=6): story.append(Spacer(1, h))

def make_table(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths, hAlign='LEFT', repeatRows=1 if header else 0)
    ts = [
        ('FONT', (0,0), (-1,-1), 'Helvetica', 9),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#B0B7C3')),
    ]
    if header:
        ts += [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F3A5F')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 9),
        ]
    t.setStyle(TableStyle(ts))
    return t

# ---------- Title block ----------
P("Claims PMPM Dashboard &mdash; Process Documentation", h1)
P("NonSentience Health &mdash; Medicare Advantage  |  Monthly Close Deliverable", subtitle)
SP(10)

# ---------- 1. Purpose ----------
P("1. Purpose", h2)
P("The Claims PMPM Dashboard presents calendar-year 2024 vs. 2025 ultimate incurred PMPM "
  "by incurred month, with quarterly, year-to-date, and full-year rollups, plus YoY trend. "
  "It is produced once per close month using (a) that month's paid claims and member month "
  "extracts, and (b) the current completion factor table. The workbook is self-contained &mdash; "
  "all aggregations, completions, and display formulas live inside the file.")

# ---------- 2. Input files ----------
P("2. Input Files", h2)
P("Two CSVs land in the close-month folder (<b>YYYYMM/</b>):")
P("<b>clms_YYYYMM.csv</b> &mdash; Paid claims through the close date. "
  "Columns: <font face='Courier'>incurred_year_month</font> (EOM date, M/D/YYYY), "
  "<font face='Courier'>plan_type</font> (HMO/PPO), "
  "<font face='Courier'>claim_type</font> (IP/Non-IP), "
  "<font face='Courier'>plan_paid</font> (USD). "
  "Grain: one row per incurred month &times; plan_type &times; claim_type (four rows per incurred month). "
  "History starts January 2024; the newest row is the close month and will be heavily undeveloped at lag 0&ndash;1.")
P("<b>mbr_YYYYMM.csv</b> &mdash; Member months through the close month. "
  "Columns: <font face='Courier'>year_month</font> (EOM date), "
  "<font face='Courier'>plan_type</font>, "
  "<font face='Courier'>member_months</font>. "
  "Grain: two rows per month (HMO + PPO).")
P("Approximate volume: HMO ~63k / PPO ~37k member months per month (~100k total MA lives).")

# ---------- 3. Workbook architecture ----------
P("3. Workbook Architecture", h2)
P("The workbook has the same structure each month. Eight tabs:")
arch = [
    ["Tab", "Role", "Notes"],
    ["controls", "Driver",
     "Single hardcoded input: Close Date (B5). Drives everything via named ranges. Inputs are in teal text throughout the file (per A2)."],
    ["cf", "Completion factor table",
     "Plan \u00d7 claim \u00d7 lag (0\u201323). Header note A1: \u201Csee 'Completion Factors' folder and use most recent\u201D."],
    ["claims", "CSV paste area for clms",
     "Header note: \u201Cdata pasted in from clms_yyyymm CSV file and formatted\u201D. Formula columns add year/month/lag/CF/ultimate."],
    ["mbr", "CSV paste area for mbr",
     "Header note: \u201Cdata pasted in from mbr_yyyymm CSV file and formatted\u201D. Formula columns add year/month."],
    ["pivot", "Pivot tables",
     "One for member months, one for ultimate_incurred; both cross-tabbed calendar year \u00d7 calendar month."],
    ["combined data", "Long-format dataset",
     "Year, month, plan_type, claim_type, member_months, ultimate_incurred. Handoff point for downstream analysis."],
    ["calcs", "Engine",
     "Month-in-YTD flags, member months by year (GETPIVOTDATA), ultimate incurred by year, PMPMs, trend, graph series."],
    ["Dashboard", "Display",
     "Presentation layer. All cells reference calcs."],
]
arch_wrapped = [arch[0]] + [[Paragraph(c, body) for c in row] for row in arch[1:]]
story.append(make_table(arch_wrapped, col_widths=[1.1*inch, 1.4*inch, 4.5*inch]))
SP(10)

# ---------- 4. Named ranges ----------
P("4. Named Ranges (defined in controls)", h2)
nr = [
    ["Name", "Formula", "Meaning"],
    ["close_date", "controls!B5 (hardcoded EOM date)", "Paid-thru date for this close cycle."],
    ["close_year", "=YEAR(close_date)", ""],
    ["close_month", "=MONTH(close_date)", ""],
    ["incurred_date", "=DATE(YEAR(close_date), MONTH(close_date)-1, 0)",
     "End of month two months before close. This is the most recent incurred month shown on the dashboard (lag 2 convention). Nov close \u2192 Sep 30; Dec close \u2192 Oct 31."],
    ["incurred_year", "=YEAR(incurred_date)", ""],
    ["incurred_month", "=MONTH(incurred_date)", "Drives the \u201Cis this month in YTD?\u201D flags in calcs."],
]
nr_wrapped = [nr[0]] + [
    [Paragraph(row[0], mono), Paragraph(row[1], mono), Paragraph(row[2], body)]
    for row in nr[1:]
]
story.append(make_table(nr_wrapped, col_widths=[1.1*inch, 2.4*inch, 3.5*inch]))
SP(10)

# ---------- 5. Core Transformations ----------
P("5. Core Transformations", h2)

P("5.1 Lag and Completion (on claims tab)", h3)
P("For each row (incurred_year_month, plan_type, claim_type, plan_paid):")
P("1.&nbsp;&nbsp;<font face='Courier'>incurred_year = YEAR(incurred_year_month)</font>")
P("2.&nbsp;&nbsp;<font face='Courier'>incurred_month = MONTH(incurred_year_month)</font>")
P("3.&nbsp;&nbsp;<font face='Courier'>lag = (YEAR(close_date) - YEAR(A)) * 12 + MONTH(close_date) - MONTH(A)</font>")
P("4.&nbsp;&nbsp;<font face='Courier'>completion_factor = VLOOKUP(plan_type &amp; claim_type &amp; lag, cf!D:E, 2, FALSE)</font>")
P("5.&nbsp;&nbsp;<font face='Courier'>ultimate_incurred = plan_paid / completion_factor</font>")
P("The CF lookup key is concatenated in <font face='Courier'>cf</font> column D (e.g., <font face='Courier'>HMOIP5</font>) so the VLOOKUP is a single-column match. Factors tail to 1.000 by about lag 10 (HMO IP fastest; Non-IP slightly later).")

P("5.2 Pivots", h3)
P("<font face='Courier'>pivot!C2:P6</font> &mdash; Sum of member_months by year \u00d7 month (HMO + PPO combined).")
P("<font face='Courier'>pivot!C20:P24</font> &mdash; Sum of ultimate_incurred by year \u00d7 month (plans and claim types combined).")
P("These are the sources for every figure on the Dashboard.")

P("5.3 calcs &mdash; Engine Layout", h3)
P("Columns E:P represent calendar months Jan&ndash;Dec. Rows encode the metric blocks:")
eng = [
    ["Block", "Rows", "Purpose"],
    ["Month-in-YTD flag", "row 2", "=IF(month > incurred_month, 0, 1) \u2014 1 if month \u2264 incurred_date, else 0."],
    ["Quarter index", "row 1", "Hard-coded 1,1,1,2,2,2,\u2026,4,4,4. Drives quarter rollups."],
    ["Quarter YTD flag", "row 3", "=IF(row2=1, row1, 0). Counts the quarter only if month is in YTD."],
    ["Member months 2024", "row 7", "GETPIVOTDATA from member pivot for all 12 months."],
    ["Member months 2025", "row 8", "Same, gated by row2 (stops at incurred_month)."],
    ["Ultimate claims 2024", "row 12", "GETPIVOTDATA from claims pivot."],
    ["Ultimate claims 2025", "row 13", "Same, gated by row2."],
    ["PMPM 2024", "row 17", "= claims_2024 / mbr_2024 (cell-level)."],
    ["PMPM 2025", "row 18", "Same, gated by row2 (returns \"\" beyond incurred_month)."],
    ["Trend '25/'24", "row 21", "= PMPM_2025 / PMPM_2024 \u2212 1, gated by row2."],
    ["CY graph series", "row 24+", "NA() for months beyond incurred_month so charts break cleanly."],
]
eng_wrapped = [eng[0]] + [[Paragraph(c, body) for c in row] for row in eng[1:]]
story.append(make_table(eng_wrapped, col_widths=[1.7*inch, 0.9*inch, 4.4*inch]))
SP(6)
P("Quarter columns (T:W) and YTD column (R) use AVERAGEIFS keyed on row 2 (in-YTD) or row 1 (quarter index). FY column (Y) uses a plain AVERAGE over all 12 months (2024 only, since 2025 FY only exists once December is in YTD).")

P("5.4 Dashboard Display", h3)
P("The Dashboard tab is a pure display layer. Every numeric cell references calcs:")
P("\u2022 Rows 24 and 25: PMPM for 2024 and 2025 across Jan\u2013Dec, YTD, Q1\u2013Q4, FY.")
P("\u2022 Row 27: YoY trend.")
P("\u2022 Title subtitle (B5): <font face='Courier'>=\"Data incurred thru \"&amp;TEXT(incurred_date,\"mmmyy\")&amp;\"; paid thru \"&amp;TEXT(close_date,\"mmmyy\")</font> &mdash; updates automatically with the close date.")
P("\u2022 Column headers (D22:O22): hardcoded Jan\u2013Dec. Q22 dynamically reads <font face='Courier'>TEXT(incurred_date,\"mmm\")&amp;\" YTD\"</font>.")

# ---------- 6. Monthly update procedure ----------
P("6. Monthly Update Procedure", h2)
P("To refresh the dashboard for a new close month:")
steps = [
    "Start from the prior month's workbook to preserve formatting, named ranges, formulas, pivots, and charts.",
    "Update the close date in controls!B5 to the new EOM date.",
    "Replace claims data &mdash; paste the new clms_YYYYMM.csv into the claims tab starting at row 7. Extend formula columns E\u2013I down to cover all new rows.",
    "Replace mbr data &mdash; paste the new mbr_YYYYMM.csv into the mbr tab starting at row 7. Extend columns D\u2013E.",
    "Confirm the CF table is current &mdash; check cf!A1 note and refresh from the Completion folder if factors have been re-estimated.",
    "Refresh the two pivots on the pivot tab (Data \u2192 Refresh All). Pivot source ranges should cover the new row count.",
    "Recalculate the workbook.",
    "Sanity-check the Dashboard: title subtitle reads correctly; 2025 row stops after incurred_month; newest incurred month looks reasonable vs. prior months; trend row only populates for months inside YTD.",
]
for i, s in enumerate(steps, 1):
    P(f"{i}. {s}")

# ---------- 7. Formatting ----------
P("7. Formatting Conventions", h2)
P("<b>Font:</b> consistent workbook-wide (default Calibri body).")
P("<b>Number formats:</b>")
P("\u2022 PMPMs: <font face='Courier'>_(\"$\"* #,##0.00_);_(\"$\"* (#,##0.00);_(\"$\"* \"-\"??_);_(@_)</font> (accounting dollars, 2 decimals).")
P("\u2022 Trend: <font face='Courier'>0.0%</font>.")
P("<b>Input cells:</b> teal font (per controls!A2).")
P("<b>Dashboard title block:</b> merged across B4:X4 (title) and B5:X5 (subtitle).")
P("<b>Column layout on Dashboard:</b> monthly block D:O, gap in P, YTD in Q, gap in R, Q1:Q4 in S:V, gap in W, FY in X.")
P("<b>Notes:</b> header-row comments in cf, claims, mbr, and controls describe source and input convention.")

# ---------- 8. Varies vs constant ----------
P("8. What Varies vs. What Stays Constant", h2)
P("<b>Varies each close:</b>")
P("\u2022 controls!B5 close date.")
P("\u2022 Contents of claims rows 7+ and mbr rows 7+.")
P("\u2022 Pivot source ranges (one additional incurred month of rows).")
P("\u2022 Dashboard row 25 populates one month further out as incurred_date advances.")
P("<b>Stays constant:</b>")
P("\u2022 Workbook structure (8 tabs, named ranges, formulas).")
P("\u2022 Completion factor table, unless the model is refreshed (see cf!A1).")
P("\u2022 calcs layout, pivot structure, Dashboard template.")
P("\u2022 Formatting, headers, dynamic subtitle formula.")

# ---------- 9. Known quirks ----------
P("9. Known Quirks / Things to Watch", h2)
P("<b>Lag 2 convention:</b> the incurred month shown is always two months before close because paid data at lag 0\u20131 is too thin for completion to be reliable. The incurred_date formula enforces this.")
P("<b>Most recent incurred months in the raw data look tiny.</b> That's the lag 0 / lag 1 trail in the CSV. It's filtered out of the dashboard by the incurred_month gate, but it's visible if you pivot the raw tabs directly.")
P("<b>FY 2025</b> only populates once December is inside YTD (i.e., after the Jan26 close, when incurred_date = Dec 31, 2025).")
P("<b>Completion factors go to 1.000 by lag ~10.</b> If incurred_year_month is beyond 23 months old, the VLOOKUP key won't exist &mdash; but in practice the CF table carries lags far enough back to cover Jan 2024.")
P("<b>Trend volatility at the newest incurred month:</b> the most recent incurred month on the dashboard is at lag 2, where completion still leans heavily on the model. Expect meaningful restatement as that month ages into lag 3 and lag 4.")

SP(12)
P("<i>Reverse-engineered from the Nov25 and Dec25 close workbooks. No external documentation was available from the prior owner.</i>", subtitle)

doc.build(story)
print("WROTE:", OUT)
