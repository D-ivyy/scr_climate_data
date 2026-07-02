const DATA_URL = "data/example_asset_1232.json";

const COLORS = ["#2f6f9f", "#218a61", "#b7791f", "#6f5ab8", "#c2410c", "#0f8b8d"];
const RATING_SCORE = { A: 1, B: 2, C: 3, D: 4, E: 5, F: 6, G: 7 };

const state = {
  data: null,
  assetName: null,
  activeView: "physical",
  physicalScenario: null,
  physicalHorizon: null,
  transitionScenario: null,
};

function el(id) {
  return document.getElementById(id);
}

function unique(values) {
  return [...new Set(values.filter((value) => value !== null && value !== undefined && value !== ""))];
}

function sortNumeric(values) {
  return [...values].sort((a, b) => Number(a) - Number(b));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function ratingScore(value) {
  return RATING_SCORE[String(value || "").toUpperCase()] || 0;
}

function ratingBadge(value) {
  const rating = String(value || "-").toUpperCase();
  const klass = RATING_SCORE[rating] ? `rating-${rating.toLowerCase()}` : "rating-empty";
  return `<span class="rating ${klass}">${escapeHtml(rating)}</span>`;
}

function formatNumber(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  const number = Number(value);
  if (Math.abs(number) > 0 && Math.abs(number) < 0.01) {
    return number.toFixed(9);
  }
  return number.toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  });
}

function formatCompact(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  const number = Number(value);
  if (Math.abs(number) > 0 && Math.abs(number) < 0.01) {
    return number.toExponential(2);
  }
  return number.toLocaleString(undefined, { maximumFractionDigits: 3 });
}

function formatValueWithUnit(value, unit) {
  const formatted = formatNumber(value);
  if (formatted === "n/a") {
    return formatted;
  }
  return `${formatted}${unit ? ` ${unit}` : ""}`;
}

function setOptions(select, options, selected) {
  select.innerHTML = options
    .map((option) => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`)
    .join("");
  if (selected !== null && selected !== undefined) {
    select.value = String(selected);
  }
}

function currentAsset() {
  return state.data.assets.find((asset) => asset.asset_name === state.assetName) || state.data.assets[0];
}

function physicalRows(name) {
  return {
    trends: state.data.physical.trends.filter((row) => row.asset_name === name),
    hazards: state.data.physical.hazards.filter((row) => row.asset_name === name),
    indicators: state.data.physical.indicators.filter((row) => row.asset_name === name),
  };
}

function transitionRows(name) {
  return {
    trends: state.data.transition.trends.filter((row) => row.asset_name === name),
    subrisks: state.data.transition.subrisks.filter((row) => row.asset_name === name),
    rankings: state.data.transition.scenario_rankings.filter((row) => !row.asset_name || row.asset_name === name),
  };
}

function preferredValue(values, preferred, fallbackIndex = 0) {
  if (values.includes(preferred)) {
    return preferred;
  }
  return values[fallbackIndex] ?? values[0] ?? null;
}

function initialiseState() {
  const asset = state.data.assets[0];
  state.assetName = asset.asset_name;

  const physical = physicalRows(state.assetName);
  const physicalScenarios = unique(physical.trends.map((row) => row.scenario));
  const physicalHorizons = sortNumeric(unique(physical.trends.map((row) => row.horizon)));
  state.physicalScenario = preferredValue(physicalScenarios, "ssp5-8.5");
  state.physicalHorizon = preferredValue(physicalHorizons, 2100, physicalHorizons.length - 1);

  const transition = transitionRows(state.assetName);
  const transitionScenarios = unique(transition.rankings.map((row) => row.scenario));
  state.transitionScenario = preferredValue(transitionScenarios, "Net Zero 2050");

  setOptions(el("assetSelect"), state.data.assets.map((item) => item.asset_name), state.assetName);
  refreshControls();
}

function refreshControls() {
  const physical = physicalRows(state.assetName);
  const transition = transitionRows(state.assetName);
  const physicalScenarios = unique(physical.trends.map((row) => row.scenario));
  const physicalHorizons = sortNumeric(unique(physical.trends.map((row) => row.horizon)));
  const transitionScenarios = unique(transition.rankings.map((row) => row.scenario));

  if (!physicalScenarios.includes(state.physicalScenario)) {
    state.physicalScenario = preferredValue(physicalScenarios, "ssp5-8.5");
  }
  if (!physicalHorizons.map(String).includes(String(state.physicalHorizon))) {
    state.physicalHorizon = preferredValue(physicalHorizons, 2100, physicalHorizons.length - 1);
  }
  if (!transitionScenarios.includes(state.transitionScenario)) {
    state.transitionScenario = preferredValue(transitionScenarios, "Net Zero 2050");
  }

  setOptions(el("physicalScenarioSelect"), physicalScenarios, state.physicalScenario);
  setOptions(el("physicalHorizonSelect"), physicalHorizons, state.physicalHorizon);
  setOptions(el("transitionScenarioSelect"), transitionScenarios, state.transitionScenario);
}

function bindControls() {
  el("assetSelect").addEventListener("change", (event) => {
    state.assetName = event.target.value;
    refreshControls();
    render();
  });
  el("physicalScenarioSelect").addEventListener("change", (event) => {
    state.physicalScenario = event.target.value;
    render();
  });
  el("physicalHorizonSelect").addEventListener("change", (event) => {
    state.physicalHorizon = Number(event.target.value);
    render();
  });
  el("transitionScenarioSelect").addEventListener("change", (event) => {
    state.transitionScenario = event.target.value;
    render();
  });
  el("physicalTab").addEventListener("click", () => {
    state.activeView = "physical";
    render();
  });
  el("transitionTab").addEventListener("click", () => {
    state.activeView = "transition";
    render();
  });
}

function metric(label, value, detail) {
  return `
    <article class="metric">
      <span class="metric-label">${escapeHtml(label)}</span>
      <span class="metric-value">${value}</span>
      <span class="metric-detail">${escapeHtml(detail || "")}</span>
    </article>
  `;
}

function selectedPhysicalTrend(physical) {
  return physical.trends.find(
    (row) => row.scenario === state.physicalScenario && Number(row.horizon) === Number(state.physicalHorizon),
  );
}

function selectedHazards(physical) {
  return physical.hazards
    .filter((row) => row.scenario === state.physicalScenario && Number(row.horizon) === Number(state.physicalHorizon))
    .sort((a, b) => {
      const impactDiff = Number(b.adjusted_hazard_value_impact || 0) - Number(a.adjusted_hazard_value_impact || 0);
      if (impactDiff !== 0) return impactDiff;
      return ratingScore(b.hazard_rating) - ratingScore(a.hazard_rating);
    });
}

function selectedTransitionRanking(transition) {
  return transition.rankings.find((row) => row.scenario === state.transitionScenario) || transition.rankings[0];
}

function renderSummary(asset, physical, transition) {
  const trend = selectedPhysicalTrend(physical);
  const hazards = selectedHazards(physical);
  const topHazard = hazards[0];
  const topTransition = transition.rankings[0];
  const selectedTransition = selectedTransitionRanking(transition);

  el("assetSummary").innerHTML = [
    metric("Asset", escapeHtml(asset.scr_asset_id || asset.asset_name), asset.ticcs_sub_class_name || asset.ticcs_sub_class || ""),
    metric("Physical Rating", ratingBadge(trend?.adjusted_physical_exposure_rating), `${state.physicalScenario} @ ${state.physicalHorizon}`),
    metric(
      "Physical Impact",
      escapeHtml(formatNumber(trend?.adjusted_total_value_impact)),
      topHazard ? `Top hazard: ${topHazard.hazard}` : "No hazard ranking",
    ),
    metric(
      "Transition Peak",
      escapeHtml(formatNumber(topTransition?.peak_impact)),
      topTransition ? `${topTransition.scenario} @ ${topTransition.peak_year}` : "No transition ranking",
    ),
    metric(
      "Selected Driver",
      escapeHtml(selectedTransition?.peak_subrisk || "n/a"),
      selectedTransition ? `${selectedTransition.scenario} peak ${formatNumber(selectedTransition.peak_impact)}` : "",
    ),
  ].join("");
}

function renderPhysical(asset, physical) {
  const trendsByScenario = unique(physical.trends.map((row) => row.scenario)).map((scenario, index) => ({
    name: scenario,
    color: COLORS[index % COLORS.length],
    selected: scenario === state.physicalScenario,
    points: physical.trends
      .filter((row) => row.scenario === scenario)
      .sort((a, b) => Number(a.horizon) - Number(b.horizon))
      .map((row) => ({
        x: Number(row.horizon),
        y: row.adjusted_total_value_impact,
        rating: row.adjusted_physical_exposure_rating,
      })),
  }));

  el("physicalTrendKicker").textContent = `${asset.scr_asset_id || asset.asset_name} | ${state.physicalScenario}`;
  renderLineChart("physicalTrendChart", trendsByScenario, {
    yLabel: "adjustedTotalValueImpact",
    baselineZero: false,
  });

  renderHazardRanking(physical);
  renderIndicatorTable(physical);
}

function renderHazardRanking(physical) {
  const hazards = selectedHazards(physical);
  if (!hazards.length) {
    el("hazardRanking").innerHTML = `<div class="empty-state">No hazard rows for this selection.</div>`;
    return;
  }
  const maxValue = Math.max(...hazards.map((row) => Number(row.adjusted_hazard_value_impact || 0)), 0);
  el("hazardRanking").innerHTML = hazards
    .map((row) => {
      const width = maxValue > 0 ? (Number(row.adjusted_hazard_value_impact || 0) / maxValue) * 100 : 0;
      const worst = (row.worst_indicators || [])
        .slice(0, 2)
        .map((item) => `${item.rating || "-"} ${item.indicator || ""} ${formatValueWithUnit(item.value, item.unit)}`)
        .join(" | ");
      return `
        <div class="bar-row">
          <div class="bar-label">
            <span class="bar-title">${escapeHtml(row.hazard)}</span>
            <span class="bar-subtitle">Rating ${escapeHtml(row.hazard_rating || "-")} | ${escapeHtml(worst)}</span>
          </div>
          <div class="bar-track"><div class="bar-fill" style="width:${width}%; background:${COLORS[0]}"></div></div>
          <div class="bar-value">${formatNumber(row.adjusted_hazard_value_impact)}</div>
        </div>
      `;
    })
    .join("");
}

function renderIndicatorTable(physical) {
  const rows = physical.indicators
    .filter(
      (row) =>
        row.scenario === state.physicalScenario &&
        Number(row.horizon) === Number(state.physicalHorizon) &&
        row.rating,
    )
    .sort((a, b) => {
      const ratingDiff = ratingScore(b.rating) - ratingScore(a.rating);
      if (ratingDiff !== 0) return ratingDiff;
      return String(a.hazard || "").localeCompare(String(b.hazard || ""));
    })
    .slice(0, 18);

  if (!rows.length) {
    el("indicatorTable").innerHTML = `<div class="empty-state">No rated indicators for this selection.</div>`;
    return;
  }

  el("indicatorTable").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Rating</th>
          <th>Hazard</th>
          <th>Indicator</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
              <tr>
                <td>${ratingBadge(row.rating)}</td>
                <td>${escapeHtml(row.hazard || "-")}</td>
                <td>${escapeHtml(row.indicator || "-")}</td>
                <td>${escapeHtml(formatValueWithUnit(row.value, row.unit))}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderTransition(asset, transition) {
  el("transitionRankKicker").textContent = `${asset.scr_asset_id || asset.asset_name} | raw model-output values`;
  renderTransitionRanking(transition);

  const series = unique(transition.trends.map((row) => row.scenario)).map((scenario, index) => ({
    name: scenario,
    color: COLORS[index % COLORS.length],
    selected: scenario === state.transitionScenario,
    points: transition.trends
      .filter((row) => row.scenario === scenario)
      .sort((a, b) => Number(a.horizon) - Number(b.horizon))
      .map((row) => ({
        x: Number(row.horizon),
        y: row.max_adjusted_subrisk_revenue_impact,
        rating: row.transition_rating,
      })),
  }));
  renderLineChart("transitionTrendChart", series, {
    yLabel: "max adjustedSubriskRevenueImpact",
    baselineZero: true,
  });
  renderSubriskTable(transition);
}

function peakText(peak) {
  if (!peak) {
    return "n/a";
  }
  return `${formatNumber(peak.value)} @ ${peak.year}`;
}

function renderTransitionRanking(transition) {
  if (!transition.rankings.length) {
    el("transitionRanking").innerHTML = `<div class="empty-state">No transition rankings available.</div>`;
    return;
  }
  const maxPeak = Math.max(...transition.rankings.map((row) => Number(row.peak_impact || 0)), 0);
  el("transitionRanking").innerHTML = transition.rankings
    .map((row, index) => {
      const width = maxPeak > 0 ? (Number(row.peak_impact || 0) / maxPeak) * 100 : 0;
      const selected = row.scenario === state.transitionScenario ? " is-selected" : "";
      return `
        <button class="bar-row scenario-row${selected}" type="button" data-scenario="${escapeHtml(row.scenario)}">
          <div class="bar-label">
            <span class="bar-title">${index + 1}. ${escapeHtml(row.scenario)}</span>
            <span class="bar-subtitle">${escapeHtml(row.peak_subrisk)} peak @ ${escapeHtml(row.peak_year)}</span>
          </div>
          <div class="bar-track"><div class="bar-fill" style="width:${width}%; background:${COLORS[index % COLORS.length]}"></div></div>
          <div class="driver-split">
            <span>Peak ${escapeHtml(formatNumber(row.peak_impact))}</span>
            <span>Direct ${escapeHtml(peakText(row.direct_carbon_peak))}</span>
            <span>Market ${escapeHtml(peakText(row.market_demand_peak))}</span>
          </div>
        </button>
      `;
    })
    .join("");

  document.querySelectorAll(".scenario-row").forEach((row) => {
    row.addEventListener("click", () => {
      state.transitionScenario = row.dataset.scenario;
      el("transitionScenarioSelect").value = state.transitionScenario;
      render();
    });
  });
}

function renderSubriskTable(transition) {
  const rows = transition.subrisks
    .filter((row) => row.scenario === state.transitionScenario && row.adjusted_revenue_impact !== null)
    .sort((a, b) => Number(b.adjusted_revenue_impact || 0) - Number(a.adjusted_revenue_impact || 0))
    .slice(0, 18);

  if (!rows.length) {
    el("subriskTable").innerHTML = `<div class="empty-state">No subrisk rows for this scenario.</div>`;
    return;
  }

  el("subriskTable").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Rating</th>
          <th>Horizon</th>
          <th>Subrisk</th>
          <th>Indicator</th>
          <th>Impact</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
              <tr>
                <td>${ratingBadge(row.rating)}</td>
                <td>${escapeHtml(row.horizon)}</td>
                <td>${escapeHtml(row.subrisk || "-")}</td>
                <td>${escapeHtml(row.indicator || "-")}</td>
                <td>${escapeHtml(formatNumber(row.adjusted_revenue_impact))}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderLineChart(containerId, series, options) {
  const container = el(containerId);
  const xValues = sortNumeric(unique(series.flatMap((item) => item.points.map((point) => point.x))));
  const yValues = series.flatMap((item) => item.points.map((point) => point.y)).filter((value) => value !== null);

  if (!xValues.length || !yValues.length) {
    container.innerHTML = `<div class="empty-state">No trend data available.</div>`;
    return;
  }

  const width = 760;
  const height = 260;
  const margin = { top: 18, right: 22, bottom: 40, left: 76 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const yMinRaw = Math.min(...yValues);
  const yMaxRaw = Math.max(...yValues);
  const yMin = options.baselineZero ? 0 : yMinRaw - Math.abs(yMinRaw) * 0.04;
  const yMax = yMaxRaw + Math.abs(yMaxRaw || 1) * 0.08;
  const yRange = yMax - yMin || 1;

  const xFor = (value) => {
    const index = xValues.indexOf(value);
    if (xValues.length === 1) return margin.left + innerWidth / 2;
    return margin.left + (index / (xValues.length - 1)) * innerWidth;
  };
  const yFor = (value) => margin.top + innerHeight - ((Number(value) - yMin) / yRange) * innerHeight;

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => yMin + yRange * ratio);
  const grid = yTicks
    .map((tick) => {
      const y = yFor(tick);
      return `
        <line class="grid-line" x1="${margin.left}" x2="${width - margin.right}" y1="${y}" y2="${y}"></line>
        <text class="tick-label" x="${margin.left - 10}" y="${y + 4}" text-anchor="end">${escapeHtml(formatCompact(tick))}</text>
      `;
    })
    .join("");

  const xLabels = xValues
    .map((value, index) => {
      if (xValues.length > 10 && index % 3 !== 0 && index !== xValues.length - 1) return "";
      const x = xFor(value);
      return `<text class="tick-label" x="${x}" y="${height - 12}" text-anchor="middle">${escapeHtml(value)}</text>`;
    })
    .join("");

  const lines = series
    .map((item) => {
      const points = item.points.filter((point) => point.y !== null);
      const path = points.map((point, index) => `${index === 0 ? "M" : "L"} ${xFor(point.x)} ${yFor(point.y)}`).join(" ");
      const circles = points
        .map(
          (point) =>
            `<circle cx="${xFor(point.x)}" cy="${yFor(point.y)}" r="${item.selected ? 3.5 : 2.5}" fill="${item.color}"><title>${escapeHtml(item.name)} ${point.x}: ${formatNumber(point.y)} rating ${point.rating || "-"}</title></circle>`,
        )
        .join("");
      return `
        <path d="${path}" fill="none" stroke="${item.color}" stroke-width="${item.selected ? 3 : 2}" opacity="${item.selected ? 1 : 0.45}"></path>
        <g opacity="${item.selected ? 1 : 0.7}">${circles}</g>
      `;
    })
    .join("");

  const legend = series
    .map(
      (item) =>
        `<span class="legend-item"><span class="legend-swatch" style="background:${item.color}"></span>${escapeHtml(item.name)}</span>`,
    )
    .join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(options.yLabel)} trend">
      ${grid}
      <line class="axis-line" x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}"></line>
      <line class="axis-line" x1="${margin.left}" x2="${margin.left}" y1="${margin.top}" y2="${height - margin.bottom}"></line>
      ${xLabels}
      ${lines}
    </svg>
    <div class="legend">${legend}</div>
  `;
}

function renderInterpretation(asset, physical, transition) {
  const trend = selectedPhysicalTrend(physical);
  const hazards = selectedHazards(physical);
  const topHazard = hazards[0];
  const firstYearTrend = physical.trends
    .filter((row) => row.scenario === state.physicalScenario)
    .sort((a, b) => Number(a.horizon) - Number(b.horizon))[0];
  const change =
    firstYearTrend && trend?.adjusted_total_value_impact
      ? ((trend.adjusted_total_value_impact / firstYearTrend.adjusted_total_value_impact - 1) * 100).toFixed(1)
      : null;
  const selectedTransition = selectedTransitionRanking(transition);
  const topTransition = transition.rankings[0];

  el("interpretationBody").innerHTML = `
    <p><strong>Asset context:</strong> ${escapeHtml(asset.scr_asset_id || asset.asset_name)} is modeled as ${escapeHtml(asset.ticcs_sub_class_name || "an infrastructure asset")} at ${escapeHtml(asset.coordinates || "unknown coordinates")}.</p>
    <p><strong>Physical:</strong> ${escapeHtml(state.physicalScenario)} at ${escapeHtml(state.physicalHorizon)} returns overall rating ${escapeHtml(trend?.adjusted_physical_exposure_rating || "-")} and adjusted total value impact ${escapeHtml(formatNumber(trend?.adjusted_total_value_impact))}${change ? `, a ${escapeHtml(change)}% move from the first returned horizon` : ""}. ${topHazard ? `The top quantified hazard is ${escapeHtml(topHazard.hazard)}.` : ""}</p>
    <p><strong>Transition:</strong> the highest peak scenario is ${escapeHtml(topTransition?.scenario || "-")} with ${escapeHtml(formatNumber(topTransition?.peak_impact))}. The selected scenario, ${escapeHtml(selectedTransition?.scenario || "-")}, is led by ${escapeHtml(selectedTransition?.peak_subrisk || "-")} at ${escapeHtml(selectedTransition?.peak_year || "-")}.</p>
    <p><strong>Caveat:</strong> impact fields are shown as raw SCR model-output values until SCR confirms product-facing units and labels.</p>
  `;
}

function render() {
  const asset = currentAsset();
  const physical = physicalRows(asset.asset_name);
  const transition = transitionRows(asset.asset_name);

  el("physicalTab").classList.toggle("is-active", state.activeView === "physical");
  el("transitionTab").classList.toggle("is-active", state.activeView === "transition");
  el("physicalView").classList.toggle("is-hidden", state.activeView !== "physical");
  el("transitionView").classList.toggle("is-hidden", state.activeView !== "transition");
  el("physicalControls").classList.toggle("is-hidden", state.activeView !== "physical");
  el("transitionControls").classList.toggle("is-hidden", state.activeView !== "transition");

  renderSummary(asset, physical, transition);
  renderPhysical(asset, physical);
  renderTransition(asset, transition);
  renderInterpretation(asset, physical, transition);
}

async function init() {
  try {
    const response = await fetch(DATA_URL);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    state.data = await response.json();
    initialiseState();
    bindControls();
    el("dataStatus").textContent = `${state.data.meta.physical_rows} physical rows | ${state.data.meta.transition_rows} transition rows`;
    render();
  } catch (error) {
    el("dataStatus").textContent = "Data load failed";
    document.querySelector("main").innerHTML = `
      <section class="panel">
        <h2>Dashboard data could not be loaded</h2>
        <p class="lede">Run a local server from the repo root, then open /dashboard/.</p>
        <pre>${escapeHtml(error.message)}</pre>
      </section>
    `;
  }
}

document.addEventListener("DOMContentLoaded", init);
