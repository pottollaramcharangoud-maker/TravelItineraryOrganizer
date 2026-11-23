const CATEGORIES = ["Leisure", "Business", "Adventure", "Family", "Cultural", "Solo"];
const STATUSES = ["Planned", "Booked", "In Progress", "Completed", "Cancelled"];
const STORAGE_KEY = "travel-itinerary-organizer-trips";
const PAGE_SIZE = 12;

let trips = loadTrips();
let filtered = [];
let page = 1;
let selectedId = null;
let editingId = null;
let sortKey = "id";
let sortDir = 1;

const el = (id) => document.getElementById(id);

function loadTrips() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch (error) {
    console.warn("Storage read failed", error);
  }
  const seeded = makeSampleTrips();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(seeded));
  return seeded;
}

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(trips));
}

function makeSampleTrips() {
  let state = 52;
  const random = () => {
    state = (state * 1103515245 + 12345) & 0x7fffffff;
    return state / 0x7fffffff;
  };
  const pick = (list) => list[Math.floor(random() * list.length)];
  const places = ["Paris, France", "Tokyo, Japan", "New York, USA", "London, UK", "Dubai, UAE", "Bangkok, Thailand", "Rome, Italy", "Sydney, Australia", "Singapore", "Istanbul, Turkey", "Goa, India", "Jaipur, India", "Kerala, India", "Himalayas, Nepal", "Bali, Indonesia", "Barcelona, Spain", "Amsterdam, Netherlands", "Seoul, South Korea", "Cairo, Egypt", "Cape Town, South Africa"];
  const notes = ["Flight and hotel booked", "Awaiting visa approval", "Weekend getaway with friends", "Conference attendance", "Family vacation planned", "Budget under review", "Adventure trekking expedition", "Museums and local cuisine", "Beach resort stay", "Client meetings scheduled"];
  const today = new Date();
  const iso = (date) => date.toISOString().slice(0, 10);
  const shift = (days) => {
    const date = new Date(today);
    date.setDate(date.getDate() + days);
    return date;
  };
  const rows = [];
  for (let i = 1; i <= 40; i++) {
    const start = shift(Math.floor(random() * 276) - 75);
    const duration = Math.floor(random() * 21) + 1;
    const end = new Date(start);
    end.setDate(end.getDate() + (i === 20 ? 0 : duration));
    let cost = Math.round((80 + random() * 4720) * 100) / 100;
    if (i === 5) cost = 0;
    if (i === 12) cost = 10000;
    rows.push({
      id: i,
      destination: pick(places),
      start_date: iso(start),
      end_date: iso(end),
      category: pick(CATEGORIES),
      notes: pick(notes),
      estimated_cost: cost,
      status: pick(STATUSES),
      created_at: new Date().toISOString().slice(0, 19)
    });
  }
  return rows;
}

function parseDate(value) {
  const parts = String(value).split("-").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return null;
  return new Date(parts[0], parts[1] - 1, parts[2]);
}

function timing(trip) {
  if (trip.status === "Cancelled" || trip.status === "Completed") return trip.status;
  const start = parseDate(trip.start_date);
  const end = parseDate(trip.end_date);
  if (!start || !end) return "Invalid";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (end < today) return "Overdue";
  if (start > today) return "Upcoming";
  return "Ongoing";
}

function durationDays(trip) {
  const start = parseDate(trip.start_date);
  const end = parseDate(trip.end_date);
  if (!start || !end) return 0;
  return Math.round((end - start) / 86400000) + 1;
}

function warnings() {
  const result = [];
  trips.forEach((trip) => {
    const state = timing(trip);
    if (state === "Overdue") result.push([trip, "Overdue: trip ended on " + trip.end_date]);
    if (state === "Invalid") result.push([trip, "Invalid or missing date range"]);
    if (trip.estimated_cost > 10000) result.push([trip, "Cost " + fmtMoney(trip.estimated_cost) + " exceeds limit 10000.00"]);
    if (durationDays(trip) <= 0) result.push([trip, "Non-positive trip duration"]);
  });
  return result;
}

function summary() {
  const costs = trips.map((trip) => Number(trip.estimated_cost) || 0);
  const byCategory = {};
  const byStatus = {};
  const byTiming = {};
  trips.forEach((trip) => {
    byCategory[trip.category] = (byCategory[trip.category] || 0) + 1;
    byStatus[trip.status] = (byStatus[trip.status] || 0) + 1;
    const state = timing(trip);
    byTiming[state] = (byTiming[state] || 0) + 1;
  });
  return {
    total: trips.length,
    totalCost: costs.reduce((a, b) => a + b, 0),
    average: costs.length ? costs.reduce((a, b) => a + b, 0) / costs.length : 0,
    min: costs.length ? Math.min(...costs) : 0,
    max: costs.length ? Math.max(...costs) : 0,
    days: trips.reduce((sum, trip) => sum + durationDays(trip), 0),
    byCategory,
    byStatus,
    byTiming,
    warningCount: warnings().length,
    top: [...trips].sort((a, b) => b.estimated_cost - a.estimated_cost).slice(0, 5)
  };
}

function fmtMoney(value) {
  return Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function toast(message) {
  const node = el("toast");
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("show"), 2800);
}

function similarity(left, right) {
  const a = String(left).toLowerCase();
  const b = String(right).toLowerCase();
  if (a === b) return 1;
  if (!a.length || !b.length) return 0;
  const row = Array.from({ length: b.length + 1 }, (_, index) => index);
  for (let i = 1; i <= a.length; i++) {
    let previous = row[0];
    row[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const saved = row[j];
      row[j] = Math.min(row[j] + 1, row[j - 1] + 1, previous + (a[i - 1] === b[j - 1] ? 0 : 1));
      previous = saved;
    }
  }
  return 1 - row[b.length] / Math.max(a.length, b.length);
}

function getFiltered() {
  const keyword = el("keyword").value.trim().toLowerCase();
  const category = el("categoryFilter").value;
  const status = el("statusFilter").value;
  filtered = trips.filter((trip) => {
    if (keyword) {
      const haystack = (trip.destination + " " + String(trip.notes || "")).toLowerCase();
      if (!haystack.includes(keyword)) {
        if (keyword.length < 3) return false;
        const words = haystack.split(/\W+/).filter(Boolean);
        const score = Math.max(0, ...words.map((word) => similarity(keyword, word)));
        if (score < 0.72) return false;
      }
    }
    if (category && trip.category !== category) return false;
    if (status && trip.status !== status) return false;
    return true;
  });
  filtered.sort((a, b) => {
    let left = a[sortKey];
    let right = b[sortKey];
    if (sortKey === "timing") {
      left = timing(a);
      right = timing(b);
    }
    if (sortKey === "estimated_cost" || sortKey === "id") return (left - right) * sortDir;
    return String(left).localeCompare(String(right)) * sortDir;
  });
  return filtered;
}

function renderTable() {
  const rows = getFiltered();
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  if (page > pages) page = pages;
  const visible = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const body = el("tripTable").querySelector("tbody");
  body.innerHTML = visible.map((trip) => {
    const state = timing(trip);
    return "<tr data-id='" + trip.id + "' class='" + (trip.id === selectedId ? "selected" : "") + "'>" +
      "<td>" + trip.id + "</td><td>" + escapeHtml(trip.destination) + "</td><td>" + trip.start_date + "</td><td>" + trip.end_date + "</td>" +
      "<td>" + trip.category + "</td><td>" + fmtMoney(trip.estimated_cost) + "</td><td>" + trip.status + "</td>" +
      "<td><span class='tag " + state + "'>" + state + "</span></td></tr>";
  }).join("") || "<tr><td colspan='8' style='text-align:center;color:#64748b'>No records found</td></tr>";
  el("pageLabel").textContent = "Page " + page + " of " + pages;
  el("countLabel").textContent = rows.length + " of " + trips.length + " records";
  el("prevPage").disabled = page <= 1;
  el("nextPage").disabled = page >= pages;
  el("editBtn").disabled = selectedId === null;
  el("deleteBtn").disabled = selectedId === null;
  body.querySelectorAll("tr[data-id]").forEach((row) => {
    row.addEventListener("click", () => {
      selectedId = Number(row.dataset.id);
      renderTable();
    });
    row.addEventListener("dblclick", () => openModal(true));
  });
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[char]));
}

function renderSummary() {
  const data = summary();
  const metrics = [
    ["Total records", data.total],
    ["Total cost", fmtMoney(data.totalCost)],
    ["Average cost", fmtMoney(data.average)],
    ["Min / Max", fmtMoney(data.min) + " / " + fmtMoney(data.max)],
    ["Planned days", data.days],
    ["Active warnings", data.warningCount]
  ];
  el("metrics").innerHTML = metrics.map(([label, value]) => "<div class='metric'><span>" + label + "</span><strong>" + value + "</strong></div>").join("");
  el("charts").innerHTML = [
    ["By category", data.byCategory],
    ["By status", data.byStatus],
    ["By timing", data.byTiming]
  ].map(([title, counts]) => chartHtml(title, counts)).join("");
  el("topTable").querySelector("tbody").innerHTML = data.top.map((trip) =>
    "<tr><td>" + escapeHtml(trip.destination) + "</td><td>" + trip.category + "</td><td>" + fmtMoney(trip.estimated_cost) + "</td><td>" + trip.status + "</td></tr>"
  ).join("");
  el("warningPill").textContent = data.warningCount;
}

function chartHtml(title, counts) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = entries.length ? entries[0][1] : 1;
  const rows = entries.map(([label, value]) =>
    "<div class='barrow'><span>" + label + "</span><div class='bartrack'><div class='barfill' style='width:" + (value / max * 100) + "%'></div></div><span>" + value + "</span></div>"
  ).join("") || "<div class='barrow'><span>No data</span></div>";
  return "<div class='chart'><h3>" + title + "</h3>" + rows + "</div>";
}

function renderWarnings() {
  const rows = warnings();
  el("warningTable").querySelector("tbody").innerHTML = rows.map(([trip, message]) =>
    "<tr><td>" + trip.id + "</td><td>" + escapeHtml(trip.destination) + "</td><td>" + message + "</td></tr>"
  ).join("") || "<tr><td colspan='3' style='text-align:center;color:#15803d'>No warnings detected</td></tr>";
  el("warningPill").textContent = rows.length;
}

function render() {
  renderTable();
  renderSummary();
  renderWarnings();
}

function openModal(edit) {
  const trip = edit ? trips.find((item) => item.id === selectedId) : null;
  if (edit && !trip) return;
  editingId = trip ? trip.id : null;
  el("modalTitle").textContent = edit ? "Edit trip #" + trip.id : "Add trip";
  el("fDestination").value = trip ? trip.destination : "";
  el("fStart").value = trip ? trip.start_date : "";
  el("fEnd").value = trip ? trip.end_date : "";
  el("fCategory").value = trip ? trip.category : CATEGORIES[0];
  el("fStatus").value = trip ? trip.status : STATUSES[0];
  el("fCost").value = trip ? trip.estimated_cost : "0";
  el("fNotes").value = trip ? trip.notes : "";
  el("formError").textContent = "";
  el("modal").classList.add("open");
  el("fDestination").focus();
}

function closeModal() {
  el("modal").classList.remove("open");
}

function nextId() {
  return trips.reduce((max, trip) => Math.max(max, trip.id), 0) + 1;
}

function saveTrip(event) {
  event.preventDefault();
  const destination = el("fDestination").value.trim();
  const start = el("fStart").value;
  const end = el("fEnd").value;
  const cost = Number(el("fCost").value);
  const error = el("formError");
  if (!destination) { error.textContent = "Destination is required."; return; }
  if (!start || !end) { error.textContent = "Start and end dates are required."; return; }
  if (end < start) { error.textContent = "End date cannot be before start date."; return; }
  if (!Number.isFinite(cost) || cost < 0) { error.textContent = "Estimated cost must be a non-negative number."; return; }
  const data = {
    destination,
    start_date: start,
    end_date: end,
    category: el("fCategory").value,
    notes: el("fNotes").value.trim(),
    estimated_cost: cost,
    status: el("fStatus").value
  };
  if (editingId) {
    const trip = trips.find((item) => item.id === editingId);
    Object.assign(trip, data);
    toast("Trip #" + editingId + " updated");
  } else {
    data.id = nextId();
    data.created_at = new Date().toISOString().slice(0, 19);
    trips.push(data);
    toast("Trip #" + data.id + " added");
  }
  persist();
  closeModal();
  render();
}

function deleteTrip() {
  const trip = trips.find((item) => item.id === selectedId);
  if (!trip) return;
  if (!confirm("Delete trip #" + trip.id + " - " + trip.destination + "?")) return;
  trips = trips.filter((item) => item.id !== trip.id);
  selectedId = null;
  persist();
  render();
  toast("Trip deleted");
}

function download(name, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

function csvCell(value) {
  return "\"" + String(value).replace(/"/g, "\"\"") + "\"";
}

function exportData() {
  const kind = el("exportKind").value;
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  const columns = ["id", "destination", "start_date", "end_date", "category", "notes", "estimated_cost", "status", "created_at"];
  if (kind === "csv") {
    const lines = [columns.join(",")];
    trips.forEach((trip) => lines.push(columns.map((key) => csvCell(trip[key])).join(",")));
    download("itinerary_" + stamp + ".csv", lines.join("\n"), "text/csv");
  } else if (kind === "json") {
    download("itinerary_" + stamp + ".json", JSON.stringify(trips, null, 2), "application/json");
  } else {
    const data = summary();
    const lines = ["# Travel Itinerary Organizer - Summary", "", "Generated: " + new Date().toISOString(), "", "## Key Metrics", "",
      "- Total records: " + data.total, "- Total cost: " + fmtMoney(data.totalCost), "- Average cost: " + fmtMoney(data.average),
      "- Active warnings: " + data.warningCount, "", "## Trips", "", "| ID | Destination | Start | End | Category | Cost | Status |", "|---|---|---|---|---|---|---|"];
    trips.forEach((trip) => lines.push("| " + [trip.id, trip.destination, trip.start_date, trip.end_date, trip.category, fmtMoney(trip.estimated_cost), trip.status].join(" | ") + " |"));
    download("itinerary_" + stamp + ".md", lines.join("\n"), "text/markdown");
  }
  toast("Report downloaded");
}

function parseCsv(text) {
  const lines = text.replace(/\r/g, "").split("\n").filter((line) => line.trim());
  if (!lines.length) return [];
  const split = (line) => {
    const cells = [];
    let current = "";
    let quoted = false;
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === "\"") {
        if (quoted && line[i + 1] === "\"") { current += "\""; i++; }
        else quoted = !quoted;
      } else if (char === "," && !quoted) { cells.push(current); current = ""; }
      else current += char;
    }
    cells.push(current);
    return cells;
  };
  const headers = split(lines[0]).map((value) => value.trim());
  return lines.slice(1).map((line) => {
    const row = {};
    split(line).forEach((value, index) => { row[headers[index]] = value; });
    return row;
  });
}

function importCsv(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    const rows = parseCsv(reader.result);
    let valid = 0;
    let rejected = 0;
    let next = nextId();
    rows.forEach((row) => {
      const cost = Number(row.estimated_cost);
      const start = row.start_date;
      const end = row.end_date;
      if (!row.destination || !start || !end || end < start || !Number.isFinite(cost) || cost < 0 || !CATEGORIES.includes(row.category) || !STATUSES.includes(row.status)) {
        rejected++;
        return;
      }
      trips.push({
        id: next++,
        destination: row.destination,
        start_date: start,
        end_date: end,
        category: row.category,
        notes: row.notes || "",
        estimated_cost: cost,
        status: row.status,
        created_at: new Date().toISOString().slice(0, 19)
      });
      valid++;
    });
    persist();
    render();
    toast("Imported " + valid + ", rejected " + rejected);
  };
  reader.readAsText(file);
  event.target.value = "";
}

function seedData() {
  if (!confirm("Replace the current dataset with 40 sample records?")) return;
  trips = makeSampleTrips();
  selectedId = null;
  page = 1;
  persist();
  render();
  toast("Seeded 40 sample records");
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === name));
  document.querySelectorAll(".panel").forEach((panel) => panel.classList.toggle("active", panel.id === "panel-" + name));
}

function init() {
  el("fCategory").innerHTML = CATEGORIES.map((item) => "<option>" + item + "</option>").join("");
  el("fStatus").innerHTML = STATUSES.map((item) => "<option>" + item + "</option>").join("");
  el("categoryFilter").innerHTML = "<option value=''>All categories</option>" + CATEGORIES.map((item) => "<option>" + item + "</option>").join("");
  el("statusFilter").innerHTML = "<option value=''>All statuses</option>" + STATUSES.map((item) => "<option>" + item + "</option>").join("");

  el("addBtn").addEventListener("click", () => openModal(false));
  el("editBtn").addEventListener("click", () => openModal(true));
  el("deleteBtn").addEventListener("click", deleteTrip);
  el("cancelBtn").addEventListener("click", closeModal);
  el("tripForm").addEventListener("submit", saveTrip);
  el("seedBtn").addEventListener("click", seedData);
  el("importBtn").addEventListener("click", () => el("importFile").click());
  el("importFile").addEventListener("change", importCsv);
  el("exportBtn").addEventListener("click", exportData);

  el("keyword").addEventListener("input", () => { page = 1; renderTable(); });
  el("categoryFilter").addEventListener("change", () => { page = 1; renderTable(); });
  el("statusFilter").addEventListener("change", () => { page = 1; renderTable(); });
  el("clearBtn").addEventListener("click", () => {
    el("keyword").value = "";
    el("categoryFilter").value = "";
    el("statusFilter").value = "";
    page = 1;
    renderTable();
  });
  el("prevPage").addEventListener("click", () => { if (page > 1) { page--; renderTable(); } });
  el("nextPage").addEventListener("click", () => { page++; renderTable(); });
  document.querySelectorAll("th[data-sort]").forEach((header) => {
    header.addEventListener("click", () => {
      const key = header.dataset.sort;
      sortDir = sortKey === key ? -sortDir : 1;
      sortKey = key;
      renderTable();
    });
  });
  document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => switchTab(tab.dataset.tab)));
  el("modal").addEventListener("click", (event) => { if (event.target === el("modal")) closeModal(); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeModal(); });

  render();
}

init();
