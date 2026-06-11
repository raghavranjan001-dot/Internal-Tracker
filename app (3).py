from flask import Flask, jsonify, request, render_template_string, Response
from flask_cors import CORS
import sqlite3
import os
import csv
import io

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.db")

INITIAL_CARDS = [
    {"name": "LendingNext", "type": "Video", "category": "Product", "stage": "Design In Progress", "quarter": "", "notes": ""},
    {"name": "LendingNext", "type": "Pitch Deck", "category": "Product", "stage": "Draft", "quarter": "", "notes": ""},
    {"name": "PNB RM Module", "type": "Video", "category": "Customer", "stage": "Closed", "quarter": "AMJ", "notes": ""},
    {"name": "Document AI", "type": "Brochure", "category": "Product", "stage": "Closed", "quarter": "AMJ", "notes": ""},
    {"name": "Document AI", "type": "Video", "category": "Product", "stage": "Closed", "quarter": "AMJ", "notes": ""},
    {"name": "CustomerNext", "type": "Brochure", "category": "Product", "stage": "Review", "quarter": "", "notes": ""},
    {"name": "CustomerNext", "type": "Video", "category": "Product", "stage": "Design In Progress", "quarter": "", "notes": ""},
    {"name": "CustomerNext", "type": "Pitch Deck", "category": "Product", "stage": "Review", "quarter": "", "notes": ""},
    {"name": "Document AI", "type": "Pitch Deck", "category": "Product", "stage": "Closed", "quarter": "AMJ", "notes": ""},
    {"name": "LendingNext", "type": "Brochure", "category": "Product", "stage": "Closed", "quarter": "AMJ", "notes": ""},
    {"name": "AgentNext", "type": "Pitch Deck", "category": "Product", "stage": "Not Started", "quarter": "", "notes": ""},
    {"name": "OCP", "type": "Pitch Deck", "category": "Product", "stage": "Not Started", "quarter": "", "notes": ""},
    {"name": "MongoDB Draft", "type": "Brochure", "category": "Product", "stage": "Closed", "quarter": "AMJ", "notes": ""},
    {"name": "LendingNext Booth Video", "type": "Video", "category": "Product", "stage": "Closed", "quarter": "AMJ", "notes": ""},
    {"name": "AgentNext", "type": "Video", "category": "Product", "stage": "Not Started", "quarter": "", "notes": ""},
    {"name": "PNB - Influencer Video", "type": "Video", "category": "Customer", "stage": "Not Started", "quarter": "", "notes": ""},
    {"name": "CloudOps Video", "type": "Video", "category": "Product", "stage": "Not Started", "quarter": "", "notes": ""},
    {"name": "Headless Banking WP", "type": "Thought Leadership WP", "category": "Product", "stage": "Closed", "quarter": "AMJ", "notes": "Architecture approval pending from Atul"},
    {"name": "Benchmarking AI Security & Governance", "type": "Thought Leadership WP", "category": "Product", "stage": "Closed", "quarter": "AMJ", "notes": ""},
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            stage TEXT NOT NULL,
            quarter TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    count = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    if count == 0:
        for card in INITIAL_CARDS:
            conn.execute(
                "INSERT INTO cards (name, type, category, stage, quarter, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (card["name"], card["type"], card["category"], card["stage"], card["quarter"], card["notes"])
            )
    conn.commit()
    conn.close()

@app.route("/api/cards", methods=["GET"])
def get_cards():
    conn = get_db()
    cards = conn.execute("SELECT * FROM cards ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(c) for c in cards])

@app.route("/api/cards", methods=["POST"])
def add_card():
    data = request.json
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO cards (name, type, category, stage, quarter, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (data["name"], data["type"], data["category"], data["stage"], data.get("quarter", ""), data.get("notes", ""))
    )
    conn.commit()
    card = conn.execute("SELECT * FROM cards WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(card)), 201

@app.route("/api/cards/<int:card_id>", methods=["PUT"])
def update_card(card_id):
    data = request.json
    conn = get_db()
    conn.execute(
        "UPDATE cards SET name=?, type=?, category=?, stage=?, quarter=?, notes=? WHERE id=?",
        (data["name"], data["type"], data["category"], data["stage"], data.get("quarter", ""), data.get("notes", ""), card_id)
    )
    conn.commit()
    card = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    return jsonify(dict(card))

@app.route("/api/cards/<int:card_id>", methods=["DELETE"])
def delete_card(card_id):
    conn = get_db()
    conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": card_id})

@app.route("/api/export")
def export_csv():
    conn = get_db()
    cards = conn.execute("SELECT name, type, category, stage, quarter, notes FROM cards ORDER BY id").fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Type", "Category", "Stage", "Quarter", "Notes"])
    for c in cards:
        writer.writerow([c["name"], c["type"], c["category"], c["stage"], c["quarter"], c["notes"]])
    return Response(output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=bn_collateral_tracker.csv"})

@app.route("/api/import", methods=["POST"])
def import_csv():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file"}), 400
    stream = io.StringIO(f.stream.read().decode("utf-8"))
    reader = csv.DictReader(stream)
    conn = get_db()
    count = 0
    for row in reader:
        name = row.get("Name", "").strip()
        if not name:
            continue
        conn.execute(
            "INSERT INTO cards (name, type, category, stage, quarter, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (name, row.get("Type","Video"), row.get("Category","Product"),
             row.get("Stage","Not Started"), row.get("Quarter",""), row.get("Notes",""))
        )
        count += 1
    conn.commit()
    conn.close()
    return jsonify({"imported": count})

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BN Collateral Tracker</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #f4f5f7; color: #172b4d; min-height: 100vh; }

/* Header */
.header { background: #fff; border-bottom: 1px solid #dfe1e6; padding: 0 24px; height: 56px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; box-shadow: 0 1px 4px rgba(9,30,66,0.08); }
.header-brand { display: flex; align-items: center; gap: 10px; }
.brand-avatar { width: 32px; height: 32px; background: #3b5bdb; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: #fff; }
.brand-name { font-size: 14px; font-weight: 600; color: #172b4d; }
.brand-sub { font-size: 11px; color: #6b778c; }
.header-actions { display: flex; align-items: center; gap: 8px; }

/* Toolbar */
.toolbar { background: #fff; border-bottom: 1px solid #dfe1e6; padding: 10px 24px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.toolbar select { height: 34px; padding: 0 28px 0 10px; border: 1px solid #dfe1e6; border-radius: 4px; font-size: 13px; color: #172b4d; background: #fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%236b778c'/%3E%3C/svg%3E") no-repeat right 8px center; appearance: none; cursor: pointer; outline: none; }
.toolbar select:focus { border-color: #4c9aff; }
.search-box { height: 34px; padding: 0 12px; border: 1px solid #dfe1e6; border-radius: 4px; font-size: 13px; color: #172b4d; outline: none; width: 200px; }
.search-box:focus { border-color: #4c9aff; }
.toolbar-spacer { flex: 1; }

/* Buttons */
.btn-primary { height: 34px; padding: 0 16px; background: #3b5bdb; color: #fff; border: none; border-radius: 4px; font-size: 13px; font-weight: 500; cursor: pointer; white-space: nowrap; }
.btn-primary:hover { background: #2f4abf; }
.btn-outline { height: 34px; padding: 0 14px; background: #fff; color: #344563; border: 1px solid #dfe1e6; border-radius: 4px; font-size: 13px; cursor: pointer; white-space: nowrap; }
.btn-outline:hover { background: #f4f5f7; border-color: #c1c7d0; }

/* Stats */
.stats-bar { padding: 14px 24px; display: flex; gap: 12px; flex-wrap: wrap; }
.stat-card { background: #fff; border: 1px solid #dfe1e6; border-radius: 6px; padding: 12px 20px; display: flex; align-items: center; gap: 12px; min-width: 120px; box-shadow: 0 1px 2px rgba(9,30,66,0.04); }
.stat-num { font-size: 22px; font-weight: 700; color: #172b4d; }
.stat-label { font-size: 11px; color: #6b778c; line-height: 1.4; }
.stat-card.stat-total .stat-num { color: #172b4d; }
.stat-card.stat-progress .stat-num { color: #0052cc; }
.stat-card.stat-review .stat-num { color: #ff8b00; }
.stat-card.stat-closed .stat-num { color: #00875a; }

/* Board */
.board-wrap { padding: 0 24px 24px; overflow-x: auto; }
.board { display: flex; gap: 10px; min-width: max-content; align-items: flex-start; }

/* Column colours */
.col { width: 210px; flex-shrink: 0; border-radius: 6px; overflow: hidden; }
.col-not-started  { background: #f0f0f0; }
.col-research     { background: #e8f0ff; }
.col-ideation     { background: #fff3e0; }
.col-draft        { background: #fff8e1; }
.col-design       { background: #e8f5e9; }
.col-review       { background: #fce4ec; }
.col-closed       { background: #e8f5e9; }

.col-header { padding: 10px 12px 8px; display: flex; align-items: center; justify-content: space-between; }
.col-title { font-size: 12px; font-weight: 600; }
.col-not-started  .col-title { color: #42526e; }
.col-research     .col-title { color: #0052cc; }
.col-ideation     .col-title { color: #974f0c; }
.col-draft        .col-title { color: #974f0c; }
.col-design       .col-title { color: #006644; }
.col-review       .col-title { color: #ae2a19; }
.col-closed       .col-title { color: #006644; }

.col-count { font-size: 11px; font-weight: 600; color: #6b778c; background: rgba(9,30,66,0.08); border-radius: 10px; padding: 1px 7px; }
.col-body { padding: 0 8px 8px; min-height: 60px; }
.col-body.drag-over { outline: 2px dashed #4c9aff; outline-offset: -3px; border-radius: 4px; }

/* Cards */
.card { background: #fff; border-radius: 6px; padding: 10px 12px; margin-bottom: 6px; cursor: grab; border: 1px solid #dfe1e6; box-shadow: 0 1px 2px rgba(9,30,66,0.06); position: relative; transition: box-shadow 0.15s; }
.card:hover { box-shadow: 0 3px 10px rgba(9,30,66,0.12); border-color: #c1c7d0; }
.card.dragging { opacity: 0.45; }
.card-name { font-size: 13px; font-weight: 500; color: #172b4d; margin-bottom: 8px; line-height: 1.35; padding-right: 36px; }
.card-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 6px; }
.tag { font-size: 10px; padding: 2px 7px; border-radius: 3px; font-weight: 500; }
.tag-type-video          { background: #e3f2fd; color: #1565c0; }
.tag-type-pitch          { background: #f3e5f5; color: #6a1b9a; }
.tag-type-brochure       { background: #fff3e0; color: #e65100; }
.tag-type-wp             { background: #e8f5e9; color: #1b5e20; }
.tag-type-other          { background: #f1f3f4; color: #5f6368; }
.tag-cat-product  { background: #e8f0ff; color: #0052cc; }
.tag-cat-customer { background: #e3fcef; color: #006644; }
.tag-cat-analyst  { background: #fff0fc; color: #943d73; }
.card-footer { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
.quarter-badge { font-size: 10px; color: #5e4200; background: #fff7d6; border: 1px solid #f0c84a; border-radius: 3px; padding: 1px 6px; font-weight: 600; }
.note-text { font-size: 10px; color: #5e6c84; font-style: italic; }
.add-note { font-size: 10px; color: #97a0af; cursor: pointer; border: none; background: none; padding: 0; }
.add-note:hover { color: #0052cc; text-decoration: underline; }
.card-actions { position: absolute; top: 7px; right: 7px; display: none; gap: 3px; }
.card:hover .card-actions { display: flex; }
.card-btn { background: #f4f5f7; border: none; color: #6b778c; font-size: 11px; width: 22px; height: 22px; border-radius: 3px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.card-btn:hover { background: #dfe1e6; color: #172b4d; }
.card-btn.del:hover { background: #ffebe6; color: #bf2600; }

/* Add card */
.add-card-btn { width: 100%; padding: 7px; background: transparent; border: none; border-radius: 4px; color: #6b778c; font-size: 12px; cursor: pointer; text-align: left; display: flex; align-items: center; gap: 4px; }
.add-card-btn:hover { background: rgba(9,30,66,0.06); color: #172b4d; }

/* Modal */
.modal-overlay { display: none; position: fixed; inset: 0; background: rgba(9,30,66,0.45); z-index: 200; align-items: center; justify-content: center; }
.modal-overlay.open { display: flex; }
.modal { background: #fff; border-radius: 8px; padding: 24px; width: 440px; max-width: 96vw; max-height: 92vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(9,30,66,0.2); }
.modal h2 { font-size: 16px; font-weight: 600; color: #172b4d; margin-bottom: 20px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 11px; font-weight: 600; color: #6b778c; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 5px; }
.form-group input, .form-group select, .form-group textarea { width: 100%; background: #fafbfc; border: 2px solid #dfe1e6; border-radius: 4px; color: #172b4d; font-size: 13px; padding: 7px 10px; outline: none; font-family: inherit; transition: border-color 0.15s; }
.form-group input:focus, .form-group select:focus, .form-group textarea:focus { border-color: #4c9aff; background: #fff; }
.form-group textarea { resize: vertical; min-height: 64px; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 20px; border-top: 1px solid #f4f5f7; padding-top: 16px; }
.btn-modal-cancel { height: 34px; padding: 0 14px; background: #f4f5f7; color: #344563; border: none; border-radius: 4px; font-size: 13px; cursor: pointer; }
.btn-modal-cancel:hover { background: #dfe1e6; }
.btn-modal-save { height: 34px; padding: 0 18px; background: #3b5bdb; color: #fff; border: none; border-radius: 4px; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-modal-save:hover { background: #2f4abf; }

/* Toast */
.toast { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: #172b4d; color: #fff; font-size: 13px; padding: 10px 18px; border-radius: 6px; z-index: 300; opacity: 0; transition: opacity 0.2s; pointer-events: none; white-space: nowrap; box-shadow: 0 4px 12px rgba(9,30,66,0.2); }
.toast.show { opacity: 1; }

::-webkit-scrollbar { height: 6px; width: 6px; }
::-webkit-scrollbar-track { background: #f4f5f7; }
::-webkit-scrollbar-thumb { background: #c1c7d0; border-radius: 3px; }
</style>
</head>
<body>

<div class="header">
  <div class="header-brand">
    <div class="brand-avatar">BN</div>
    <div>
      <div class="brand-name">BusinessNext</div>
      <div class="brand-sub">Marketing Collateral Tracker</div>
    </div>
  </div>
  <div class="header-actions">
    <button class="btn-outline" onclick="exportCSV()">Export CSV</button>
    <button class="btn-outline" onclick="document.getElementById('importFile').click()">Import CSV</button>
    <input type="file" id="importFile" accept=".csv" style="display:none" onchange="importCSV(event)">
    <button class="btn-primary" onclick="openModal()">+ Add project</button>
  </div>
</div>

<div class="toolbar">
  <select id="fTypeFilter" onchange="applyFilters()">
    <option value="">All types</option>
    <option value="Video">Video</option>
    <option value="Pitch Deck">Pitch Deck</option>
    <option value="Brochure">Brochure</option>
    <option value="Thought Leadership WP">Thought Leadership WP</option>
    <option value="Case Study">Case Study</option>
    <option value="PPT">PPT</option>
  </select>
  <select id="fCatFilter" onchange="applyFilters()">
    <option value="">All categories</option>
    <option value="Product">Product</option>
    <option value="Customer">Customer</option>
    <option value="Analyst">Analyst</option>
  </select>
  <select id="fQtrFilter" onchange="applyFilters()">
    <option value="">All quarters</option>
    <option value="AMJ">AMJ (Apr–Jun)</option>
    <option value="JAS">JAS (Jul–Sep)</option>
    <option value="OND">OND (Oct–Dec)</option>
    <option value="JFM">JFM (Jan–Mar)</option>
    <option value="__none__">Unassigned</option>
  </select>
  <input class="search-box" id="searchBox" type="text" placeholder="Search projects..." oninput="applyFilters()">
</div>

<div class="stats-bar" id="statsBar"></div>

<div class="board-wrap">
  <div class="board" id="board"></div>
</div>

<!-- Modal -->
<div class="modal-overlay" id="modalOverlay">
  <div class="modal">
    <h2 id="modalTitle">Add New Project</h2>
    <div class="form-group">
      <label>Project Name</label>
      <input type="text" id="fName" placeholder="e.g. AgentNext">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Type</label>
        <select id="fType">
          <option>Video</option>
          <option>Pitch Deck</option>
          <option>Brochure</option>
          <option>Thought Leadership WP</option>
          <option>PPT</option>
          <option>Case Study</option>
          <option>Other</option>
        </select>
      </div>
      <div class="form-group">
        <label>Category</label>
        <select id="fCategory">
          <option>Product</option>
          <option>Customer</option>
          <option>Analyst</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Stage</label>
        <select id="fStage">
          <option>Not Started</option>
          <option>Research</option>
          <option>Ideation</option>
          <option>Draft</option>
          <option>Design In Progress</option>
          <option>Review</option>
          <option>Closed</option>
        </select>
      </div>
      <div class="form-group">
        <label>Quarter</label>
        <select id="fQuarter">
          <option value="">-- Unassigned --</option>
          <option value="AMJ">AMJ (Apr–Jun)</option>
          <option value="JAS">JAS (Jul–Sep)</option>
          <option value="OND">OND (Oct–Dec)</option>
          <option value="JFM">JFM (Jan–Mar)</option>
        </select>
      </div>
    </div>
    <div class="form-group">
      <label>Notes</label>
      <textarea id="fNotes" placeholder="Any context, blockers, or links..."></textarea>
    </div>
    <div class="modal-actions">
      <button class="btn-modal-cancel" onclick="closeModal()">Cancel</button>
      <button class="btn-modal-save" onclick="saveCard()">Save</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
var STAGES = [
  {key:"Not Started", cls:"col-not-started"},
  {key:"Research",    cls:"col-research"},
  {key:"Ideation",    cls:"col-ideation"},
  {key:"Draft",       cls:"col-draft"},
  {key:"Design In Progress", cls:"col-design"},
  {key:"Review",      cls:"col-review"},
  {key:"Closed",      cls:"col-closed"}
];

var TYPE_TAG = {
  "Video":                "tag-type-video",
  "Pitch Deck":           "tag-type-pitch",
  "Brochure":             "tag-type-brochure",
  "Thought Leadership WP":"tag-type-wp",
  "PPT":                  "tag-type-other",
  "Case Study":           "tag-type-other",
  "Other":                "tag-type-other"
};

var cards = [];
var editingId = null;
var dragId = null;

async function fetchCards() {
  try {
    var res = await fetch("/api/cards");
    cards = await res.json();
    renderAll();
  } catch(e) { showToast("Error loading data"); }
}

function getFilters() {
  return {
    type: document.getElementById("fTypeFilter").value,
    cat:  document.getElementById("fCatFilter").value,
    qtr:  document.getElementById("fQtrFilter").value,
    q:    document.getElementById("searchBox").value.toLowerCase().trim()
  };
}

function applyFilters() { renderAll(); }

function filtered(f) {
  return cards.filter(function(c) {
    if (f.type && c.type !== f.type) return false;
    if (f.cat  && c.category !== f.cat) return false;
    if (f.qtr === "__none__" && c.quarter !== "") return false;
    if (f.qtr && f.qtr !== "__none__" && c.quarter !== f.qtr) return false;
    if (f.q && c.name.toLowerCase().indexOf(f.q) === -1) return false;
    return true;
  });
}

function renderAll() {
  var f = getFilters();
  var vis = filtered(f);

  // Stats (always from full cards list)
  var total = cards.length;
  var inprog = cards.filter(function(c){ return ["Research","Ideation","Draft","Design In Progress"].indexOf(c.stage) > -1; }).length;
  var review = cards.filter(function(c){ return c.stage === "Review"; }).length;
  var closed = cards.filter(function(c){ return c.stage === "Closed"; }).length;
  document.getElementById("statsBar").innerHTML =
    '<div class="stat-card stat-total"><span class="stat-num">'+total+'</span><div class="stat-label">Total<br>projects</div></div>'+
    '<div class="stat-card stat-progress"><span class="stat-num">'+inprog+'</span><div class="stat-label">In<br>progress</div></div>'+
    '<div class="stat-card stat-review"><span class="stat-num">'+review+'</span><div class="stat-label">Awaiting<br>review</div></div>'+
    '<div class="stat-card stat-closed"><span class="stat-num">'+closed+'</span><div class="stat-label">Closed</div></div>';

  var board = document.getElementById("board");
  board.innerHTML = "";

  STAGES.forEach(function(s) {
    var sc = vis.filter(function(c){ return c.stage === s.key; });
    var colBodyId = "colbody_" + s.key.replace(/[^a-zA-Z0-9]/g,"_");
    var cardsHtml = sc.map(function(c){ return cardHTML(c); }).join("");
    var col = document.createElement("div");
    col.className = "col " + s.cls;
    col.innerHTML =
      '<div class="col-header">'+
        '<span class="col-title">'+s.key+'</span>'+
        '<span class="col-count">'+sc.length+'</span>'+
      '</div>'+
      '<div class="col-body" id="'+colBodyId+'"'+
        ' ondragover="onDragOver(event)"'+
        ' ondrop="onDrop(event,\''+s.key+'\')"'+
        ' ondragleave="onDragLeave(event)">'+
        cardsHtml+
        '<button class="add-card-btn" onclick="openModal(\''+s.key+'\')">&#43; Add</button>'+
      '</div>';
    board.appendChild(col);
  });
}

function tagClass(type) {
  return TYPE_TAG[type] || "tag-type-other";
}

function cardHTML(c) {
  var catCls = "tag-cat-" + c.category.toLowerCase();
  var qBadge = c.quarter ? '<span class="quarter-badge">Q1 '+c.quarter+'</span>' : "";
  var noteHtml = c.notes
    ? '<span class="note-text">'+c.notes+'</span>'
    : '<button class="add-note" onclick="editCard('+c.id+')">+ add note</button>';
  return '<div class="card" draggable="true" id="card-'+c.id+'"'+
    ' ondragstart="onDragStart(event,'+c.id+')"'+
    ' ondragend="onDragEnd(event)">'+
    '<div class="card-actions">'+
      '<button class="card-btn" title="Edit" onclick="editCard('+c.id+')">&#9998;</button>'+
      '<button class="card-btn del" title="Delete" onclick="deleteCard('+c.id+')">&#x2715;</button>'+
    '</div>'+
    '<div class="card-name">'+c.name+'</div>'+
    '<div class="card-tags">'+
      '<span class="tag '+tagClass(c.type)+'">'+c.type+'</span>'+
      '<span class="tag '+catCls+'">'+c.category+'</span>'+
    '</div>'+
    '<div class="card-footer">'+qBadge+noteHtml+'</div>'+
    '</div>';
}

function onDragStart(e, id) {
  dragId = id;
  setTimeout(function(){ var el=document.getElementById("card-"+id); if(el) el.classList.add("dragging"); }, 0);
}
function onDragEnd() {
  document.querySelectorAll(".card").forEach(function(c){ c.classList.remove("dragging"); });
}
function onDragOver(e) { e.preventDefault(); e.currentTarget.classList.add("drag-over"); }
function onDragLeave(e) { e.currentTarget.classList.remove("drag-over"); }
async function onDrop(e, stage) {
  e.preventDefault();
  e.currentTarget.classList.remove("drag-over");
  if (!dragId) return;
  var card = cards.find(function(c){ return c.id === dragId; });
  if (!card || card.stage === stage) { dragId=null; return; }
  await fetch("/api/cards/"+dragId, {
    method:"PUT", headers:{"Content-Type":"application/json"},
    body: JSON.stringify(Object.assign({}, card, {stage:stage}))
  });
  dragId = null;
  await fetchCards();
  showToast("Moved to " + stage);
}

function openModal(stage) {
  editingId = null;
  document.getElementById("modalTitle").textContent = "Add New Project";
  document.getElementById("fName").value = "";
  document.getElementById("fType").value = "Video";
  document.getElementById("fCategory").value = "Product";
  document.getElementById("fStage").value = stage || "Not Started";
  document.getElementById("fQuarter").value = "";
  document.getElementById("fNotes").value = "";
  document.getElementById("modalOverlay").classList.add("open");
  setTimeout(function(){ document.getElementById("fName").focus(); }, 100);
}
function editCard(id) {
  var c = cards.find(function(x){ return x.id===id; });
  if (!c) return;
  editingId = id;
  document.getElementById("modalTitle").textContent = "Edit Project";
  document.getElementById("fName").value = c.name;
  document.getElementById("fType").value = c.type;
  document.getElementById("fCategory").value = c.category;
  document.getElementById("fStage").value = c.stage;
  document.getElementById("fQuarter").value = c.quarter||"";
  document.getElementById("fNotes").value = c.notes||"";
  document.getElementById("modalOverlay").classList.add("open");
}
function closeModal() { document.getElementById("modalOverlay").classList.remove("open"); }

async function saveCard() {
  var payload = {
    name: document.getElementById("fName").value.trim(),
    type: document.getElementById("fType").value,
    category: document.getElementById("fCategory").value,
    stage: document.getElementById("fStage").value,
    quarter: document.getElementById("fQuarter").value,
    notes: document.getElementById("fNotes").value.trim()
  };
  if (!payload.name) { showToast("Name is required"); return; }
  if (editingId) {
    await fetch("/api/cards/"+editingId, {method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    showToast("Updated");
  } else {
    await fetch("/api/cards", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    showToast("Added");
  }
  closeModal();
  fetchCards();
}

async function deleteCard(id) {
  if (!confirm("Delete this item?")) return;
  await fetch("/api/cards/"+id, {method:"DELETE"});
  await fetchCards();
  showToast("Deleted");
}

function exportCSV() { window.location.href="/api/export"; }
async function importCSV(e) {
  var file = e.target.files[0]; if (!file) return;
  var fd = new FormData(); fd.append("file", file);
  var res = await fetch("/api/import",{method:"POST",body:fd});
  var data = await res.json();
  e.target.value="";
  await fetchCards();
  showToast("Imported "+data.imported+" items");
}

function showToast(msg) {
  var t=document.getElementById("toast");
  t.textContent=msg; t.classList.add("show");
  setTimeout(function(){ t.classList.remove("show"); },2500);
}

document.getElementById("modalOverlay").addEventListener("click", function(e){
  if (e.target===e.currentTarget) closeModal();
});

fetchCards();
</script>
</body>
</html>"""

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
