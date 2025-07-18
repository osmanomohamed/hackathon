const loader = document.getElementById("loader");
const startInput = document.getElementById("startDate");
const endInput = document.getElementById("endDate");
const metricSelect = document.getElementById("metricType");
const authorSelect = document.getElementById("authorSelect");
const runBtn = document.getElementById("runBtn");
const outliersTableBody = document.querySelector("#outliersTable tbody");

let chartInstance = null;

// Debounce helper
function debounce(fn, delay) {
  let timer = null;
  return function (...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

function showLoader(show) {
  loader.classList.toggle("hidden", !show);
  runBtn.disabled = show;
}

function populateAuthors(authors) {
  authors.forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    authorSelect.appendChild(opt);
  });
}

function renderOutliers(commits) {
  outliersTableBody.innerHTML = "";
  commits.forEach((c) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td><code>${c.sha.slice(0, 7)}</code></td><td>${c.title}</td><td>${c.total_changes}</td><td>${c.z_score}</td>`;
    outliersTableBody.appendChild(tr);
  });
}

function renderChart(data) {
  const ctx = document.getElementById("activityChart").getContext("2d");
  const labels = Object.keys(data);
  const values = Object.values(data);
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: metricSelect.value,
          backgroundColor: "#007bff",
          data: values,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true },
      },
    },
  });
}

function renderWordCloud(words) {
  const wcElem = document.getElementById("wordCloud");
  wcElem.innerHTML = ""; // clear
  const list = words.map((w) => [w.text, w.value]);
  if (list.length === 0) return;
  WordCloud(wcElem, { list });
}

function saveCache(key, data) {
  localStorage.setItem(key, JSON.stringify(data));
}

function loadCache(key) {
  const txt = localStorage.getItem(key);
  return txt ? JSON.parse(txt) : null;
}

async function fetchJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Request failed: ${resp.status}`);
  return resp.json();
}

async function runQueries() {
  const params = new URLSearchParams();
  if (startInput.value) params.append("start_date", startInput.value);
  if (endInput.value) params.append("end_date", endInput.value);

  showLoader(true);
  try {
    // Authors – only if not cached
    let authors = loadCache("authors");
    if (!authors) {
      authors = await fetchJSON(`/api/authors?${params.toString()}`);
      saveCache("authors", authors);
      populateAuthors(authors);
    }

    // Outliers
    const outliers = await fetchJSON(`/api/outliers?${params.toString()}`);
    renderOutliers(outliers);

    // Activity
    const actParams = new URLSearchParams(params);
    actParams.append("metric_type", metricSelect.value);
    if (authorSelect.value) actParams.append("author", authorSelect.value);
    const activity = await fetchJSON(`/api/activity?${actParams.toString()}`);
    renderChart(activity);

    // Word frequency
    const words = await fetchJSON(`/api/word_frequency?${params.toString()}`);
    renderWordCloud(words);

    // Save to cache so page reload shows last state
    saveCache("last_outliers", outliers);
    saveCache("last_activity", { data: activity, metric: metricSelect.value });
    saveCache("last_words", words);
  } catch (err) {
    alert(err.message);
  } finally {
    showLoader(false);
  }
}

// Restore cached visuals on load
window.addEventListener("DOMContentLoaded", () => {
  const oc = loadCache("last_outliers");
  if (oc) renderOutliers(oc);
  const ac = loadCache("last_activity");
  if (ac) {
    metricSelect.value = ac.metric;
    renderChart(ac.data);
  }
  const wc = loadCache("last_words");
  if (wc) renderWordCloud(wc);

  // populate date inputs with defaults (past year)
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const lastYear = new Date(yesterday);
  lastYear.setFullYear(yesterday.getFullYear() - 1);
  endInput.value = yesterday.toISOString().slice(0, 10);
  startInput.value = lastYear.toISOString().slice(0, 10);

  // fetch authors initially (to populate)
  fetchJSON("/api/authors")
    .then((authors) => {
      saveCache("authors", authors);
      populateAuthors(authors);
    })
    .catch(console.error);
});

runBtn.addEventListener(
  "click",
  debounce(() => runQueries(), 400)
); 