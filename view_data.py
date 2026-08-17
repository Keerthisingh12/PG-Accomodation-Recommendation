"""
view_data.py
─────────────────────────────────────────────────────
Generates a beautiful, styled HTML table from the PG Dataset CSV.

Usage:
    python view_data.py
    
Output:
    Opens data_view.html in your default browser.
"""

import os
import webbrowser
import pandas as pd

# ── Load & clean data ────────────────────────────────────────────
DATA_PATH   = os.path.join("data", "raw", "PG Dataset.csv")
OUTPUT_PATH = "data_view.html"

df = pd.read_csv(DATA_PATH)

COLUMN_LABELS = {
    "PG_ID":                   "ID",
    "Location":                "Location",
    "Latitude":                "Lat",
    "Longitude":               "Lng",
    "Distance_From_Center_KM": "Distance (KM)",
    "Rent":                    "Rent (₹)",
    "Sharing":                 "Sharing Type",
    "Gender":                  "Gender",
    "Meals_Per_Day":           "Meals/Day",
    "Weekend_Food":            "Weekend Food",
    "WiFi":                    "WiFi",
    "AC":                      "AC",
    "Laundry":                 "Laundry",
    "Parking":                 "Parking",
    "Housekeeping":            "Housekeeping",
    "Lift":                    "Lift",
    "Security":                "Security",
    "CCTV":                    "CCTV",
    "Power_Backup":            "Power Backup",
    "Drinking_Water":          "Drinking Water",
    "Floors":                  "Floors",
    "Food_Type":               "Food Type",
    "Pets_Allowed":            "Pets",
    "Visitors_Allowed":        "Visitors",
    "Smoking_Area":            "Smoking",
    "Curfew_Time":             "Curfew",
    "Available_From":          "Available From",
    "Availability":            "Status",
}

df.rename(columns=COLUMN_LABELS, inplace=True)

BADGE_COLS = {"WiFi","AC","Laundry","Parking","Housekeeping","Lift","Security",
              "CCTV","Power Backup","Drinking Water","Pets","Visitors","Smoking",
              "Weekend Food","Status"}

def badge(val):
    v = str(val).strip()
    if v in ("Yes", "Available"):
        return f'<span class="badge badge-yes">{v}</span>'
    if v in ("No", "Not Available"):
        return f'<span class="badge badge-no">{v}</span>'
    return v

headers_html = "".join(f"<th>{col}</th>" for col in df.columns)

rows_html = ""
for _, row in df.iterrows():
    cells = ""
    for col in df.columns:
        val = row[col]
        if col in BADGE_COLS:
            cells += f"<td>{badge(val)}</td>"
        else:
            cells += f"<td>{val}</td>"
    rows_html += f"<tr>{cells}</tr>\n"

total = len(df)

html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>PG Dataset Viewer</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; }
    .header { background: linear-gradient(135deg, #1a1f2e 0%, #16213e 50%, #0f3460 100%); padding: 2rem 2.5rem; border-bottom: 1px solid #2d3748; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; }
    .header-left h1 { font-size: 1.75rem; font-weight: 700; background: linear-gradient(90deg, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .header-left p { color: #94a3b8; font-size: 0.875rem; margin-top: 0.25rem; }
    .stats-row { display: flex; gap: 1rem; flex-wrap: wrap; }
    .stat-chip { background: rgba(96,165,250,0.1); border: 1px solid rgba(96,165,250,0.25); border-radius: 999px; padding: 0.35rem 1rem; font-size: 0.8rem; color: #93c5fd; font-weight: 600; }
    .toolbar { padding: 1rem 2.5rem; background: #161b27; border-bottom: 1px solid #2d3748; display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
    .search-box { position: relative; flex: 1; max-width: 380px; }
    .search-box input { width: 100%; background: #1e2535; border: 1px solid #374151; border-radius: 8px; padding: 0.55rem 0.9rem 0.55rem 2.4rem; color: #e2e8f0; font-size: 0.875rem; outline: none; transition: border-color 0.2s; }
    .search-box input:focus { border-color: #60a5fa; }
    .search-box::before { content: "🔍"; position: absolute; left: 0.7rem; top: 50%; transform: translateY(-50%); font-size: 0.85rem; }
    .filter-select { background: #1e2535; border: 1px solid #374151; border-radius: 8px; padding: 0.55rem 0.9rem; color: #e2e8f0; font-size: 0.875rem; outline: none; cursor: pointer; }
    .filter-select:focus { border-color: #60a5fa; }
    .row-count { margin-left: auto; color: #64748b; font-size: 0.8rem; }
    .table-wrapper { padding: 1.5rem 2.5rem; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; background: #161b27; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.4); }
    thead { background: linear-gradient(90deg, #1e2a45, #1a2340); position: sticky; top: 0; z-index: 10; }
    thead th { padding: 0.85rem 0.9rem; text-align: left; font-weight: 600; color: #93c5fd; white-space: nowrap; border-bottom: 2px solid #2d3748; cursor: pointer; user-select: none; transition: background 0.15s; }
    thead th:hover { background: rgba(96,165,250,0.08); }
    thead th.sort-asc::after  { content: " ↑"; color: #60a5fa; }
    thead th.sort-desc::after { content: " ↓"; color: #60a5fa; }
    tbody tr { border-bottom: 1px solid #1e2535; transition: background 0.12s; }
    tbody tr:hover { background: rgba(96,165,250,0.05); }
    tbody tr:nth-child(even) { background: rgba(255,255,255,0.02); }
    td { padding: 0.65rem 0.9rem; white-space: nowrap; color: #cbd5e1; }
    td:first-child { color: #64748b; font-size: 0.75rem; }
    .badge { display: inline-block; padding: 0.2rem 0.55rem; border-radius: 999px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.02em; }
    .badge-yes { background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.25); }
    .badge-no  { background: rgba(239,68,68,0.12); color: #f87171; border: 1px solid rgba(239,68,68,0.2); }
    .no-results { text-align: center; padding: 3rem; color: #475569; }
    .pagination { display: flex; justify-content: center; align-items: center; gap: 0.5rem; padding: 1rem 2.5rem 0; flex-wrap: wrap; }
    .page-btn { background: #1e2535; border: 1px solid #374151; color: #94a3b8; border-radius: 7px; padding: 0.4rem 0.75rem; font-size: 0.8rem; cursor: pointer; transition: all 0.15s; }
    .page-btn:hover { border-color: #60a5fa; color: #60a5fa; }
    .page-btn.active { background: #1d4ed8; border-color: #3b82f6; color: #fff; }
    .page-btn:disabled { opacity: 0.3; cursor: default; }
    .page-info { color: #64748b; font-size: 0.8rem; }
    .footer { padding: 1.25rem 2.5rem; text-align: center; color: #374151; font-size: 0.75rem; border-top: 1px solid #1e2535; margin-top: 1.5rem; }
  </style>
</head>
<body>
  <div class="header">
    <div class="header-left">
      <h1>🏠 PG Dataset Viewer</h1>
      <p>Bangalore Paying Guest Listings — Raw Data Explorer</p>
    </div>
    <div class="stats-row">
      <span class="stat-chip">📋 TOTAL_PLACEHOLDER Total PGs</span>
      <span class="stat-chip">📍 Bangalore</span>
    </div>
  </div>
  <div class="toolbar">
    <div class="search-box">
      <input type="text" id="searchInput" placeholder="Search by location, gender, sharing type…" oninput="filterTable()"/>
    </div>
    <select class="filter-select" id="genderFilter" onchange="filterTable()">
      <option value="">All Genders</option>
      <option>Boys</option><option>Girls</option><option>Co-ed</option>
    </select>
    <select class="filter-select" id="sharingFilter" onchange="filterTable()">
      <option value="">All Sharing</option>
      <option>Single</option><option>Double</option><option>Triple</option>
    </select>
    <select class="filter-select" id="statusFilter" onchange="filterTable()">
      <option value="">All Status</option>
      <option>Available</option><option>Not Available</option>
    </select>
    <span class="row-count" id="rowCount">TOTAL_PLACEHOLDER rows</span>
  </div>
  <div class="table-wrapper">
    <table id="pgTable">
      <thead><tr>HEADERS_PLACEHOLDER</tr></thead>
      <tbody id="tableBody">ROWS_PLACEHOLDER</tbody>
    </table>
    <div class="no-results" id="noResults" style="display:none;">No PGs match your filters.</div>
  </div>
  <div class="pagination" id="pagination"></div>
  <div class="footer">Generated from <code>data/raw/PG Dataset.csv</code> &nbsp;•&nbsp; TOTAL_PLACEHOLDER records</div>
<script>
  const ROWS_PER_PAGE = 25;
  let currentPage = 1, sortCol = -1, sortAsc = true, filteredRows = [];
  const tbody = document.getElementById("tableBody");
  const allRows = Array.from(tbody.querySelectorAll("tr"));
  const noResults = document.getElementById("noResults");
  const rowCountEl = document.getElementById("rowCount");
  const pagination = document.getElementById("pagination");
  const ths = document.querySelectorAll("thead th");

  ths.forEach((th, i) => {
    th.addEventListener("click", () => {
      ths.forEach(h => h.classList.remove("sort-asc","sort-desc"));
      if (sortCol === i) { sortAsc = !sortAsc; } else { sortCol = i; sortAsc = true; }
      th.classList.add(sortAsc ? "sort-asc" : "sort-desc");
      filteredRows.sort((a,b) => {
        const at = a.cells[i].textContent.trim(), bt = b.cells[i].textContent.trim();
        const an = parseFloat(at), bn = parseFloat(bt);
        if (!isNaN(an) && !isNaN(bn)) return sortAsc ? an-bn : bn-an;
        return sortAsc ? at.localeCompare(bt) : bt.localeCompare(at);
      });
      currentPage = 1; renderPage();
    });
  });

  function filterTable() {
    const s = document.getElementById("searchInput").value.toLowerCase();
    const g = document.getElementById("genderFilter").value.toLowerCase();
    const sh = document.getElementById("sharingFilter").value.toLowerCase();
    const st = document.getElementById("statusFilter").value.toLowerCase();
    filteredRows = allRows.filter(row => {
      const t = row.textContent.toLowerCase();
      return (!s || t.includes(s)) && (!g || t.includes(g)) && (!sh || t.includes(sh)) && (!st || t.includes(st));
    });
    currentPage = 1; renderPage();
  }

  function renderPage() {
    const start = (currentPage-1)*ROWS_PER_PAGE, end = start+ROWS_PER_PAGE;
    allRows.forEach(r => r.style.display="none");
    filteredRows.slice(start, end).forEach(r => r.style.display="");
    rowCountEl.textContent = filteredRows.length + " rows";
    noResults.style.display = filteredRows.length===0 ? "block" : "none";
    renderPagination();
  }

  function renderPagination() {
    const tp = Math.ceil(filteredRows.length/ROWS_PER_PAGE);
    pagination.innerHTML = "";
    if (tp <= 1) return;
    const btn = (lbl, pg, dis=false, act=false) => {
      const b = document.createElement("button");
      b.className = "page-btn"+(act?" active":""); b.textContent = lbl; b.disabled = dis;
      b.onclick = () => { currentPage=pg; renderPage(); }; pagination.appendChild(b);
    };
    btn("← Prev", currentPage-1, currentPage===1);
    let prev=null;
    for (let p=Math.max(1,currentPage-2); p<=Math.min(tp,currentPage+2); p++) {
      if (prev!==null && p-prev>1) { const d=document.createElement("span"); d.className="page-info"; d.textContent="…"; pagination.appendChild(d); }
      btn(p, p, false, p===currentPage); prev=p;
    }
    btn("Next →", currentPage+1, currentPage===tp);
    const inf=document.createElement("span"); inf.className="page-info";
    inf.textContent = "Page "+currentPage+" of "+tp; pagination.appendChild(inf);
  }

  filteredRows = allRows.slice(); renderPage();
</script>
</body>
</html>""".replace("TOTAL_PLACEHOLDER", str(total)).replace("HEADERS_PLACEHOLDER", headers_html).replace("ROWS_PLACEHOLDER", rows_html)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅  Generated: {OUTPUT_PATH}  ({total} rows)")
webbrowser.open(f"file://{os.path.abspath(OUTPUT_PATH)}")
