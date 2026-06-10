from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import sqlite3
import json
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
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=bn_collateral_tracker.csv"}
    )

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
body { font-family: 'Inter', -apple-system, sans-serif; background: #0a0a0a; color: #f0f0f0; min-height: 100vh; }
.header { background: #0a0a0a; border-bottom: 1px solid #1f1f1f; padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; }
.header-left { display: flex; align-items: center; gap: 12px; }
.logo-dot { width: 10px; height: 10px; background: #e91e8c; border-radius: 50%; }
.header h1 { font-size: 15px; font-weight: 600; color: #fff; letter-spacing: -0.01em; }
.header-right { display: flex; align-items: center; gap: 8px; }
.stats { padding: 10px 24px; background: #0a0a0a; border-bottom: 1px solid #141414; display: flex; gap: 24px; flex-wrap: wrap; }
.stat { display: flex; align-items: center; gap: 6px; }
.stat-num { font-size: 18px; font-weight: 700; color: #e91e8c; }
.stat-label { font-size: 11px; color: #444; }
.filters { padding: 10px 24px; background: #0f0f0f; border-bottom: 1px solid #1a1a1a; display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.filter-label { font-size: 11px; color: #555; text-transform: uppercase; letter-spacing: 0.06em; margin-right: 2px; }
.filter-btn { font-size: 12px; padding: 4px 12px; border-radius: 20px; border: 1px solid #2a2a2a; background: transparent; color: #888; cursor: pointer; transition: all 0.15s; }
.filter-btn:hover { border-color: #444; color: #ccc; }
.filter-btn.active { background: #e91e8c; border-color: #e91e8c; color: #fff; }
.filter-sep { width: 1px; height: 20px; background: #1f1f1f; margin: 0 4px; }
.board-wrap { padding: 20px 24px; overflow-x: auto; }
.board { display: flex; gap: 14px; min-width: max-content; }
.col { width: 220px; flex-shrink: 0; }
.col-header { display: flex; align-items: center; justify-content: space-between; padding: 0 4px 10px; border-bottom: 2px solid #1f1f1f; margin-bottom: 10px; }
.col-title { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: #666; }
.col-count { font-size: 11px; color: #333; background: #1a1a1a; border-radius: 10px; padding: 1px 7px; }
.col-body { min-height: 80px; border-radius: 6px; transition: background 0.15s; }
.col-body.drag-over { background: #141414; }
.card { background: #141414; border: 1px solid #1f1f1f; border-radius: 8px; padding: 12px; margin-bottom: 8px; cursor: grab; transition: border-color 0.15s; position: relative; }
.card:hover { border-color: #2f2f2f; }
.card.dragging { opacity: 0.4; }
.card-name { font-size: 13px; font-weight: 500; color: #e8e8e8; margin-bottom: 8px; line-height: 1.3; padding-right: 40px; }
.card-tags { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 6px; }
.tag { font-size: 10px; padding: 2px 7px; border-radius: 4px; font-weight: 500; }
.tag-type { background: #1a1a1a; color: #777; border: 1px solid #252525; }
.tag-cat-product { background: #0d1f3c; color: #5b9bd5; border: 1px solid #1a3a6b; }
.tag-cat-customer { background: #0d2e1a; color: #4caf7a; border: 1px solid #1a5a30; }
.tag-cat-analyst { background: #2a1a3e; color: #9c6dd6; border: 1px solid #4a2a7a; }
.card-meta { display: flex; align-items: center; gap: 6px; }
.quarter-badge { font-size: 10px; color: #b8ff00; background: #1a1f00; border: 1px solid #2d3a00; border-radius: 4px; padding: 1px 6px; }
.card-notes { font-size: 10px; color: #555; margin-top: 6px; line-height: 1.4; }
.card-actions { position: absolute; top: 8px; right: 8px; display: none; gap: 4px; }
.card:hover .card-actions { display: flex; }
.card-btn { background: #1f1f1f; border: none; color: #666; font-size: 11px; padding: 3px 6px; border-radius: 4px; cursor: pointer; }
.card-btn:hover { background: #2a2a2a; color: #ccc; }
.card-btn.del:hover { background: #3a1010; color: #e05555; }
.add-card-btn { width: 100%; padding: 8px; background: transparent; border: 1px dashed #222; border-radius: 6px; color: #444; font-size: 12px; cursor: pointer; margin-top: 4px; transition: all 0.15s; }
.add-card-btn:hover { border-color: #e91e8c; color: #e91e8c; background: #1a0a10; }
.btn-primary { background: #e91e8c; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-primary:hover { background: #d01878; }
.btn-ghost { background: transparent; color: #888; border: 1px solid #2a2a2a; padding: 7px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; }
.btn-ghost:hover { border-color: #444; color: #ccc; }
.modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 200; align-items: center; justify-content: center; }
.modal-overlay.open { display: flex; }
.modal { background: #141414; border: 1px solid #2a2a2a; border-radius: 12px; padding: 24px; width: 420px; max-width: 95vw; max-height: 90vh; overflow-y: auto; }
.modal h2 { font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 20px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
.form-group input, .form-group select, .form-group textarea { width: 100%; background: #0f0f0f; border: 1px solid #2a2a2a; border-radius: 6px; color: #e8e8e8; font-size: 13px; padding: 8px 10px; outline: none; font-family: inherit; }
.form-group input:focus, .form-group select:focus, .form-group textarea:focus { border-color: #e91e8c; }
.form-group select option { background: #141414; }
.form-group textarea { resize: vertical; min-height: 60px; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 20px; }
.toast { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: #1f1f1f; border: 1px solid #2a2a2a; color: #ccc; font-size: 13px; padding: 10px 18px; border-radius: 8px; z-index: 300; opacity: 0; transition: opacity 0.2s; pointer-events: none; white-space: nowrap; }
.toast.show { opacity: 1; }
::-webkit-scrollbar { height: 6px; width: 6px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 3px; }
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div class="logo-dot"></div>
    <h1>BN Collateral Tracker</h1>
  </div>
  <div class="header-right">
    <button class="btn-ghost" onclick="exportCSV()">Export CSV</button>
    <button class="btn-ghost" onclick="document.getElementById('importFile').click()">Import CSV</button>
    <input type="file" id="importFile" accept=".csv" style="display:none" onchange="importCSV(event)">
    <button class="btn-primary" onclick="openModal()">+ Add Item</button>
  </div>
</div>

<div class="stats" id="statsBar"></div>

<div class="filters" id="filterBar">
  <span class="filter-label">Category</span>
  <button class="filter-btn active" data-group="category" data-val="All" onclick="setFilter('category','All',this)">All</button>
  <button class="filter-btn" data-group="category" data-val="Product" onclick="setFilter('category','Product',this)">Product</button>
  <button class="filter-btn" data-group="category" data-val="Customer" onclick="setFilter('category','Customer',this)">Customer</button>
  <button class="filter-btn" data-group="category" data-val="Analyst" onclick="setFilter('category','Analyst',this)">Analyst</button>
  <div class="filter-sep"></div>
  <span class="filter-label">Type</span>
  <button class="filter-btn active" data-group="type" data-val="All" onclick="setFilter('type','All',this)">All</button>
  <button class="filter-btn" data-group="type" data-val="Video" onclick="setFilter('type','Video',this)">Video</button>
  <button class="filter-btn" data-group="type" data-val="Pitch Deck" onclick="setFilter('type','Pitch Deck',this)">Pitch Deck</button>
  <button class="filter-btn" data-group="type" data-val="Brochure" onclick="setFilter('type','Brochure',this)">Brochure</button>
  <button class="filter-btn" data-group="type" data-val="Thought Leadership WP" onclick="setFilter('type','Thought Leadership WP',this)">WP</button>
  <div class="filter-sep"></div>
  <span class="filter-label">Quarter</span>
  <button class="filter-btn active" data-group="quarter" data-val="All" onclick="setFilter('quarter','All',this)">All</button>
  <button class="filter-btn" data-group="quarter" data-val="AMJ" onclick="setFilter('quarter','AMJ',this)">AMJ</button>
  <button class="filter-btn" data-group="quarter" data-val="JAS" onclick="setFilter('quarter','JAS',this)">JAS</button>
  <button class="filter-btn" data-group="quarter" data-val="OND" onclick="setFilter('quarter','OND',this)">OND</button>
  <button class="filter-btn" data-group="quarter" data-val="JFM" onclick="setFilter('quarter','JFM',this)">JFM</button>
  <button class="filter-btn" data-group="quarter" data-val="" onclick="setFilter('quarter','',this)">Unassigned</button>
</div>

<div class="board-wrap">
  <div class="board" id="board"></div>
</div>

<div class="modal-overlay" id="modalOverlay">
  <div class="modal">
    <h2 id="modalTitle">Add New Item</h2>
    <div class="form-group">
      <label>Name</label>
      <input type="text" id="fName" placeholder="e.g. AgentNext">
    </div>
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
    <div class="form-group">
      <label>Notes (optional)</label>
      <textarea id="fNotes" placeholder="Any context or blockers..."></textarea>
    </div>
    <div class="modal-actions">
      <button class="btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn-primary" onclick="saveCard()">Save</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const STAGES = ["Not Started","Research","Ideation","Draft","Design In Progress","Review","Closed"];
let cards = [];
let filters = { category: "All", type: "All", quarter: "All" };
let editingId = null;
let dragId = null;

async function fetchCards() {
  try {
    const res = await fetch("/api/cards");
    cards = await res.json();
    render();
  } catch(e) {
    showToast("Error loading cards");
  }
}

function render() {
  const filtered = cards.filter(function(c) {
    var catOk = filters.category === "All" || c.category === filters.category;
    var typeOk = filters.type === "All" || c.type === filters.type;
    var qOk = filters.quarter === "All" || c.quarter === filters.quarter;
    return catOk && typeOk && qOk;
  });

  var total = cards.length;
  var closed = cards.filter(function(c){ return c.stage === "Closed"; }).length;
  var inprog = cards.filter(function(c){ return c.stage !== "Not Started" && c.stage !== "Closed"; }).length;
  document.getElementById("statsBar").innerHTML =
    '<div class="stat"><span class="stat-num">'+total+'</span><span class="stat-label">Total Items</span></div>' +
    '<div class="stat"><span class="stat-num">'+inprog+'</span><span class="stat-label">In Progress</span></div>' +
    '<div class="stat"><span class="stat-num">'+closed+'</span><span class="stat-label">Closed</span></div>' +
    '<div class="stat"><span class="stat-num">'+(total-closed)+'</span><span class="stat-label">Open</span></div>';

  var board = document.getElementById("board");
  board.innerHTML = "";

  STAGES.forEach(function(stage) {
    var stageCards = filtered.filter(function(c){ return c.stage === stage; });
    var colId = "col-" + stage.replace(/[^a-zA-Z0-9]/g, "_");
    var cardsHTML = stageCards.map(cardHTML).join("");
    var col = document.createElement("div");
    col.className = "col";
    col.innerHTML =
      '<div class="col-header">' +
        '<span class="col-title">' + stage + '</span>' +
        '<span class="col-count">' + stageCards.length + '</span>' +
      '</div>' +
      '<div class="col-body" id="' + colId + '" ' +
        'ondragover="onDragOver(event)" ' +
        'ondrop="onDrop(event,\'' + stage + '\')" ' +
        'ondragleave="onDragLeave(event)">' +
        cardsHTML +
        '<button class="add-card-btn" onclick="openModal(\'' + stage + '\')">+ Add</button>' +
      '</div>';
    board.appendChild(col);
  });
}

function cardHTML(c) {
  var catClass = "tag-cat-" + c.category.toLowerCase();
  var qBadge = c.quarter ? '<div class="card-meta"><span class="quarter-badge">' + c.quarter + '</span></div>' : "";
  var notes = c.notes ? '<div class="card-notes">' + c.notes + '</div>' : "";
  return '<div class="card" draggable="true" id="card-' + c.id + '" ' +
    'ondragstart="onDragStart(event,' + c.id + ')" ondragend="onDragEnd(event)">' +
    '<div class="card-actions">' +
      '<button class="card-btn" onclick="editCard(' + c.id + ')">&#9998;</button>' +
      '<button class="card-btn del" onclick="deleteCard(' + c.id + ')">&#x2715;</button>' +
    '</div>' +
    '<div class="card-name">' + c.name + '</div>' +
    '<div class="card-tags">' +
      '<span class="tag tag-type">' + c.type + '</span>' +
      '<span class="tag ' + catClass + '">' + c.category + '</span>' +
    '</div>' +
    qBadge + notes +
    '</div>';
}

function onDragStart(e, id) {
  dragId = id;
  setTimeout(function(){ var el = document.getElementById("card-"+id); if(el) el.classList.add("dragging"); }, 0);
}
function onDragEnd(e) {
  document.querySelectorAll(".card").forEach(function(c){ c.classList.remove("dragging"); });
}
function onDragOver(e) { e.preventDefault(); e.currentTarget.classList.add("drag-over"); }
function onDragLeave(e) { e.currentTarget.classList.remove("drag-over"); }
async function onDrop(e, stage) {
  e.preventDefault();
  e.currentTarget.classList.remove("drag-over");
  if (!dragId) return;
  var card = cards.find(function(c){ return c.id === dragId; });
  if (!card || card.stage === stage) return;
  await fetch("/api/cards/" + dragId, {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(Object.assign({}, card, {stage: stage}))
  });
  dragId = null;
  await fetchCards();
  showToast("Moved to " + stage);
}

function openModal(stage) {
  editingId = null;
  document.getElementById("modalTitle").textContent = "Add New Item";
  document.getElementById("fName").value = "";
  document.getElementById("fType").value = "Video";
  document.getElementById("fCategory").value = "Product";
  document.getElementById("fStage").value = stage || "Not Started";
  document.getElementById("fQuarter").value = "";
  document.getElementById("fNotes").value = "";
  document.getElementById("modalOverlay").classList.add("open");
}
function editCard(id) {
  var c = cards.find(function(x){ return x.id === id; });
  editingId = id;
  document.getElementById("modalTitle").textContent = "Edit Item";
  document.getElementById("fName").value = c.name;
  document.getElementById("fType").value = c.type;
  document.getElementById("fCategory").value = c.category;
  document.getElementById("fStage").value = c.stage;
  document.getElementById("fQuarter").value = c.quarter || "";
  document.getElementById("fNotes").value = c.notes || "";
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
    await fetch("/api/cards/" + editingId, {
      method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload)
    });
    showToast("Updated");
  } else {
    await fetch("/api/cards", {
      method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload)
    });
    showToast("Added");
  }
  closeModal();
  fetchCards();
}
async function deleteCard(id) {
  if (!confirm("Delete this item?")) return;
  await fetch("/api/cards/" + id, { method: "DELETE" });
  await fetchCards();
  showToast("Deleted");
}

function setFilter(key, val, btn) {
  filters[key] = val;
  document.querySelectorAll(".filter-btn[data-group='" + key + "']").forEach(function(b){
    b.classList.remove("active");
  });
  btn.classList.add("active");
  render();
}

function exportCSV() { window.location.href = "/api/export"; }
async function importCSV(e) {
  var file = e.target.files[0];
  if (!file) return;
  var fd = new FormData();
  fd.append("file", file);
  var res = await fetch("/api/import", { method: "POST", body: fd });
  var data = await res.json();
  e.target.value = "";
  await fetchCards();
  showToast("Imported " + data.imported + " items");
}

function showToast(msg) {
  var t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(function(){ t.classList.remove("show"); }, 2500);
}

document.getElementById("modalOverlay").addEventListener("click", function(e){
  if (e.target === e.currentTarget) closeModal();
});

fetchCards();
</script>
</body>
</html>"""

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
