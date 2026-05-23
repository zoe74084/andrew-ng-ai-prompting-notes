#!/usr/bin/env python3
"""
Build print-optimized PDF for:
  Full AI Prompting Course with Andrew Ng

Steps:
  1. Extract lesson <section> blocks from index.html
  2. Build a dedicated print HTML with cover, TOC (grouped by module), lessons
  3. Render PDF with Chrome headless (no headers/footers)
"""

import re, subprocess, os, sys

BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # output/
SRC     = os.path.join(BASE, "index.html")
PDF_OUT = os.path.join(BASE, "handouts", "andrew-ng-ai-prompting-course.pdf")
TMP     = os.path.join(BASE, "_dev", "_pdf_src.html")
CHROME  = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# ── Lesson metadata ────────────────────────────────────────────────────────────
MODULES = [
    {
        "label": "Module 1",
        "title": "AI 基礎與資訊搜尋",
        "lessons": [
            ("lesson01", "AI 新手 vs AI 進階用戶",    "AI Novice vs AI Power User"),
            ("lesson02", "Pre-trained Knowledge",       "AI 的知識來源"),
            ("lesson03", "Web Search",                  "即時資訊的獲取"),
            ("lesson04", "Deep Research",               "深度多來源研究"),
            ("lesson05", "Context 管理",                "讓 AI 更懂你的任務"),
            ("lesson06", "Reasoning Models",            "讓 AI 深度思考"),
        ],
    },
    {
        "label": "Module 2",
        "title": "AI 作為思考夥伴",
        "lessons": [
            ("lesson07", "Brainstorming",               "腦力激盪的正確姿勢"),
            ("lesson08", "Sycophancy",                  "避免 AI 只說你想聽的話"),
            ("lesson09", "Writing",                     "用 AI 寫出有深度的文章"),
            ("lesson10", "Critiquing & Editing",        "用 AI 精煉你的作品"),
        ],
    },
    {
        "label": "Module 3",
        "title": "超越文字的 AI 應用",
        "lessons": [
            ("lesson11", "Multimodal AI",               "多模態輸入輸出"),
            ("lesson12", "圖像理解",                    "讓 AI 看懂你的圖片"),
            ("lesson13", "圖像生成",                    "Diffusion Model 的邏輯"),
            ("lesson14", "用 AI 建 App",                "從想法到程式"),
            ("lesson15", "資料分析",                    "讓 AI 幫你寫 Code 跑分析"),
        ],
    },
]

# quickref + resources sections
QUICKREF_ID  = "quickref"
RESOURCES_ID = "resources"

# ── 1. Read source HTML ────────────────────────────────────────────────────────
print("Step 1 — reading index.html...")
with open(SRC, encoding="utf-8") as f:
    raw = f.read()

# ── 2. Extract CSS ────────────────────────────────────────────────────────────
print("Step 2 — extracting CSS...")
css_m = re.search(r'<style>(.*?)</style>', raw, re.DOTALL)
body_css = css_m.group(1) if css_m else ""

# Strip layout/sidebar/mobile CSS we don't need in print
for pat in [
    r'/\* ── Layout[^*]*\*/', r'\.layout\b[^{]*\{[^}]*\}',
    r'/\* ── Sidebar[^*]*\*/', r'\.sidebar\b[^{]*\{[^}]*\}',
    r'\.sidebar-header\b[^{]*\{[^}]*\}', r'\.sidebar-footer\b[^{]*\{[^}]*\}',
    r'\.nav-[a-z-]+\b[^{]*\{[^}]*\}', r'\.module-label\b[^{]*\{[^}]*\}',
    r'\.nav-divider\b[^{]*\{[^}]*\}',
    r'/\* ── Mobile[^*]*\*/', r'\.mobile-[a-z-]+\b[^{]*\{[^}]*\}',
    r'\.hamburger\b[^{]*\{[^}]*\}', r'\.sidebar-overlay\b[^{]*\{[^}]*\}',
    r'@media\s*\(max-width[^{]*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
    r'/\* ── Main[^*]*\*/', r'\.main\b[^{]*\{[^}]*\}',
]:
    body_css = re.sub(pat, '', body_css, flags=re.DOTALL)

# ── 3. Extract sections ────────────────────────────────────────────────────────
print("Step 3 — extracting lesson sections...")

def extract_section(html, sid):
    pat = rf'(<section[^>]*id="{sid}"[^>]*>.*?</section>)'
    m = re.search(pat, html, re.DOTALL)
    return m.group(1) if m else f'<!-- missing: {sid} -->'

def inject_back_btn(sec):
    """Add LESSON tag + ↑ 回目錄 button row."""
    return re.sub(
        r'(<span class="lesson-tag">)(Lesson \d+)(</span>)',
        r'<div class="lesson-top">\1\2\3<a href="#toc" class="back-btn">↑ 回目錄</a></div>',
        sec
    )

def wrap_key_points(sec):
    """Wrap h2 sections that should not split across pages (ol immediately follows)."""
    return re.sub(
        r'(<h2[^>]*>(?:本節重點|使用 Reasoning 的最佳實踐)</h2>\s*<ol[^>]*>.*?</ol>)',
        r'<div class="no-break">\1</div>',
        sec, flags=re.DOTALL
    )

lesson_html_parts = []
all_lessons_flat = []

for mod in MODULES:
    for lid, zh_title, en_subtitle in mod["lessons"]:
        sec = extract_section(raw, lid)
        sec = inject_back_btn(sec)
        sec = wrap_key_points(sec)
        lesson_html_parts.append(sec)
        all_lessons_flat.append((lid, zh_title, en_subtitle, mod["label"]))

# Quick reference
qr_sec = extract_section(raw, QUICKREF_ID)
qr_sec = inject_back_btn(qr_sec)

# Resources — inject source footer inside before </section>
res_sec = extract_section(raw, RESOURCES_ID)
_footer = (
    '\n<div class="source-footer">'
    '資料來源：整理自 <a href="https://youtu.be/8ib4Qnh2HFE">Full AI Prompting Course with Andrew Ng</a>（YouTube）'
    '&nbsp;·&nbsp;整理日期：2026-05-23'
    '</div>\n'
)
res_sec = res_sec.replace('</section>', _footer + '</section>', 1)

# ── 4. Build TOC HTML ─────────────────────────────────────────────────────────
print("Step 4 — building TOC...")
toc_html = ""
for mod in MODULES:
    toc_html += f'    <li class="toc-module"><span class="toc-module-label">{mod["label"]} — {mod["title"]}</span></li>\n'
    for lid, zh_title, en_subtitle in mod["lessons"]:
        num = lid.replace("lesson", "")
        toc_html += (
            f'    <li><a href="#{lid}">'
            f'<span class="toc-num">{num}</span>'
            f'<span class="toc-en">{zh_title}</span>'
            f'<span class="toc-zh">{en_subtitle}</span>'
            f'</a></li>\n'
        )
toc_html += (
    f'    <li style="padding-top:16px;"><a href="#{QUICKREF_ID}">'
    f'<span class="toc-num">★</span>'
    f'<span class="toc-en">核心技巧速查表</span>'
    f'<span class="toc-zh">Quick Reference</span>'
    f'</a></li>\n'
)

lesson_html = "\n\n".join(lesson_html_parts)

# ── 5. Assemble print HTML ─────────────────────────────────────────────────────
print("Step 5 — assembling print HTML...")

pdf_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>Full AI Prompting Course with Andrew Ng — 課程筆記</title>
<style>
/* ── Page Setup ── */
@page {{
  size: A4;
  margin: 16mm 18mm;
}}

/* ── Reset ── */
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", sans-serif;
  background: #fff;
  color: #1a1a1a;
  font-size: 13.5px;
  line-height: 1.75;
}}

/* ── Cover Page ── */
.cover {{
  height: 265mm;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  background: #1a1a1a;
  color: #fff;
  border-radius: 6px;
  padding: 32px;
  overflow: hidden;
  break-after: page;
  page-break-after: always;
}}
.cover-tag {{
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #d97706;
  background: rgba(217,119,6,.15);
  padding: 4px 14px;
  border-radius: 99px;
  margin-bottom: 24px;
}}
.cover h1 {{
  font-size: 34px;
  font-weight: 900;
  color: #fff;
  letter-spacing: -0.01em;
  margin-bottom: 8px;
  line-height: 1.25;
  border: none;
  padding: 0;
}}
.cover-instructor {{
  font-size: 15px;
  color: #888;
  margin-bottom: 32px;
}}
.cover-sub {{
  font-size: 16px;
  color: #aaa;
  margin-bottom: 36px;
}}
.cover-divider {{
  width: 48px;
  height: 3px;
  background: #d97706;
  border-radius: 2px;
  margin: 0 auto 32px;
}}
.cover-desc {{
  font-size: 13px;
  color: #888;
  line-height: 1.9;
  max-width: 400px;
}}
.cover-source {{
  margin-top: 36px;
  font-size: 11px;
  color: #555;
}}
.cover-source a {{ color: #d97706; text-decoration: none; }}

/* ── TOC Page ── */
.toc-page {{
  break-after: page;
  page-break-after: always;
}}
.toc-page h2 {{
  font-size: 22px;
  font-weight: 800;
  color: #111;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 3px solid #d97706;
  display: block;
  letter-spacing: normal;
  text-transform: none;
}}
.toc-page h2::before {{ display: none; }}
.toc-list {{
  list-style: none;
  padding: 0;
}}
.toc-list li {{
  margin-bottom: 0;
  border-bottom: 1px solid #f0f0ee;
}}
.toc-list a {{
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 8px 4px;
  color: #1a1a1a;
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 600;
}}
.toc-list a:hover {{ color: #d97706; }}
.toc-num {{
  font-size: 11px;
  font-weight: 700;
  color: #d97706;
  min-width: 22px;
  font-family: "SF Mono", monospace;
}}
.toc-en {{ flex: 1; }}
.toc-zh {{
  font-size: 12px;
  font-weight: 400;
  color: #888;
  margin-left: 4px;
}}
.toc-module {{
  border-bottom: none !important;
  padding: 12px 0 2px;
}}
.toc-module-label {{
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #b45309;
}}
.toc-divider {{
  height: 1px;
  background: #e5e7eb;
  border-bottom: none !important;
  margin: 8px 0;
}}

/* ── Back-to-TOC button ── */
.lesson-top {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}}
.back-btn {{
  font-size: 11px;
  font-weight: 600;
  color: #b45309;
  background: #fef3c7;
  border: 1px solid #fde68a;
  border-radius: 99px;
  padding: 3px 12px;
  text-decoration: none;
  white-space: nowrap;
  flex-shrink: 0;
}}

/* ── Lesson Section ── */
.lesson {{
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
  break-before: page;
  page-break-before: always;
}}

/* ── Module Header (hide in print — lessons already labelled) ── */
.module-header {{ display: none; }}

/* ── No-split pagination ── */
table, thead, tbody, tr,
pre,
.example-box, .tip-box, .key-rule, .warn-box, .note-box, .blue-box,
.compare-grid, .compare-card,
.qr-table,
figure, img,
.no-break {{
  break-inside: avoid;
  page-break-inside: avoid;
}}
h1, h2, h3 {{
  break-after: avoid;
  page-break-after: avoid;
  orphans: 4; widows: 4;
}}
h2 + p, h2 + ol, h2 + ul, h2 + table, h2 + pre,
h2 + .example-box, h2 + .tip-box, h2 + .key-rule,
h2 + .warn-box, h2 + .blue-box, h2 + .compare-grid,
h3 + p, h3 + ol, h3 + ul, h3 + table, h3 + pre {{
  break-before: avoid;
  page-break-before: avoid;
}}
li {{
  break-inside: avoid;
  page-break-inside: avoid;
}}

/* ── Resource List ── */
.resource-list {{ list-style: none; padding: 0; }}
.resource-list li {{ padding: 9px 0; border-bottom: 1px solid #fde68a; }}
.resource-list li:last-child {{ border-bottom: none; padding-bottom: 0; }}
.resource-list a {{ font-weight: 700; color: #92400e; font-size: 13px; text-decoration: none; }}
.resource-desc {{ font-size: 12px; color: #666; margin-top: 3px; line-height: 1.5; }}

/* ── Source footer ── */
.pdf-source {{
  margin-top: 32px;
  padding: 10px 0 4px;
  border-top: 1px solid #e5e7eb;
  font-size: 11px;
  color: #aaa;
  text-align: center;
}}
.pdf-source a {{ color: #d97706; text-decoration: none; }}

/* ── Source footer at lesson level ── */
.source-footer {{
  margin-top: 32px;
  padding: 10px 0 4px;
  border-top: 1px solid #e5e7eb;
  font-size: 11px;
  color: #aaa;
  text-align: center;
}}
.source-footer a {{ color: #d97706; text-decoration: none; }}

/* ── Inherited styles ── */
{body_css}

</style>
</head>
<body>

<!-- ══ COVER ══ -->
<div class="cover">
  <div class="cover-tag">Course Notes</div>
  <h1>Full AI Prompting Course<br>with Andrew Ng</h1>
  <div class="cover-instructor">DeepLearning.AI</div>
  <div class="cover-sub">課程筆記</div>
  <div class="cover-divider"></div>
  <div class="cover-desc">
    3 大模組 · 15 個章節<br>
    從資訊搜尋到多模態應用<br>
    AI 進階用戶的完整指南
  </div>
  <div class="cover-source">
    整理自 <a href="https://youtu.be/8ib4Qnh2HFE">Full AI Prompting Course with Andrew Ng</a>（YouTube）<br>
    整理日期：2026-05-23
  </div>
</div>

<!-- ══ TOC ══ -->
<div class="toc-page" id="toc">
  <h2>目錄 Contents</h2>
  <ul class="toc-list">
{toc_html}
  </ul>
</div>

<!-- ══ LESSONS ══ -->
{lesson_html}

<!-- ══ QUICK REF ══ -->
{qr_sec}

<!-- ══ RESOURCES ══ -->
{res_sec}

</body>
</html>"""

with open(TMP, "w", encoding="utf-8") as f:
    f.write(pdf_html)
print(f"  print HTML written ({len(pdf_html):,} chars) → {TMP}")

# ── 6. Generate PDF ────────────────────────────────────────────────────────────
print("Step 6 — generating PDF with Chrome headless...")
cmd = [
    CHROME,
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--run-all-compositor-stages-before-draw",
    "--no-pdf-header-footer",
    f"--print-to-pdf={PDF_OUT}",
    f"file://{TMP}",
]
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("Chrome stderr:", result.stderr[:600])
    sys.exit(1)

os.remove(TMP)
size_kb = os.path.getsize(PDF_OUT) // 1024
print(f"  PDF saved: {PDF_OUT} ({size_kb} KB)")
print("Done.")
