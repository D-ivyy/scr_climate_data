const DATA_URL = "data/example_asset_1232.json";

const COLORS = ["#2f6f9f", "#218a61", "#b7791f", "#6f5ab8", "#c2410c", "#0f8b8d"];
const RATING_SCORE = { A: 1, B: 2, C: 3, D: 4, E: 5, F: 6, G: 7 };
const DRIVER_LABELS = {
  all: "All drivers",
  Direct_carbon_cost: "Direct carbon cost",
  Market_demand_shifts: "Market demand shifts",
};

const state = {
  data: null,
  assetName: null,
  activeView: "physical",
  physicalScenario: null,
  physicalHorizon: null,
  physicalDisplay: "percent",
  transitionScenario: null,
  transitionDriver: "all",
};

const HELP_CONTENT = {
  kpi_asset: {
    eyebrow: "Identity",
    title: "Asset Identity",
    body: [
      "This card shows SCR vendor identity and TICCS context. SCR assetId is useful metadata, but it is not the InfraSure database key.",
      "The durable join-back path is Output.assetName to scr_manifest.csv.scr_asset_name to plant_uuid. That private manifest is the bridge back to InfraSure.",
    ],
  },
  kpi_physical_rating: {
    eyebrow: "Physical",
    title: "Physical Rating",
    body: [
      "SCR ratings run from A to G. A means lowest exposure in SCR's benchmark universe, and G means highest exposure.",
      "The overall physical rating can remain A while individual hazard indicators are worse. Use this card with Hazard Ranking and Indicator Detail before making a judgment.",
    ],
  },
  kpi_physical_impact: {
    eyebrow: "Physical",
    title: "Physical Impact",
    body: [
      "This uses adjustedTotalValueImpact from the physical output for the selected scenario and horizon.",
      "The percent-style and basis-point displays are readability transforms of SCR's raw value. They are not confirmed vendor unit labels yet.",
    ],
  },
  kpi_transition_peak: {
    eyebrow: "Transition",
    title: "Transition Peak",
    body: [
      "This card ranks scenarios by peak adjustedSubriskRevenueImpact after applying the current transition driver filter.",
      "When the driver filter is All drivers, direct carbon cost and market demand shifts compete. When a specific driver is selected, the card only ranks that driver family.",
    ],
  },
  kpi_selected_driver: {
    eyebrow: "Transition",
    title: "Selected Driver",
    body: [
      "This is the subrisk family leading the selected transition scenario after the current driver filter is applied.",
      "Direct carbon cost is driven by Scope 1+2 emissions intensity and carbon price. Market demand shifts use revenue growth, inflation, and SCR-estimated Scope 3 intensity.",
    ],
  },
  physical_trend: {
    eyebrow: "Chart",
    title: "Physical Value Impact Trend",
    body: [
      "This trend uses adjustedTotalValueImpact, one point per physical scenario and future horizon.",
      "Physical horizons run from 2025 to 2100 in 5-year steps. SCR methodology describes indicator values as 10-year averages centered on the horizon, while financial impacts are average annual impacts from 2025 through the selected horizon.",
      "Use the Impact display control to inspect raw SCR values, percent-style values, or basis points. The underlying JSON keeps the raw SCR number.",
    ],
  },
  hazard_ranking: {
    eyebrow: "Physical",
    title: "Hazard Ranking",
    body: [
      "This section ranks physical hazards by adjustedHazardValueImpact for the selected scenario and horizon, then falls back to hazard rating when impacts tie.",
      "A hazard marked not quantified does not mean no exposure. It means SCR did not return a numeric hazard value impact for that hazard in this view.",
      "The worst visible indicators are included because severe indicator ratings can matter even when hazard-level value impact is blank or zero.",
    ],
  },
  indicator_detail: {
    eyebrow: "Physical",
    title: "Indicator Detail",
    body: [
      "This table shows the worst physical indicator ratings for the selected scenario and horizon.",
      "Indicator values have mixed units across hazards, such as meters, days, percent, or rating-only rows. Do not rank mixed indicators by raw magnitude alone.",
      "Rating-only rows are still meaningful severity evidence when SCR returns a rating without a numeric indicator magnitude.",
    ],
  },
  transition_ranking: {
    eyebrow: "Transition",
    title: "Scenario Ranking",
    body: [
      "This ranking uses adjustedSubriskRevenueImpact from the transition output. It is recomputed when you change the Driver selector.",
      "Direct carbon cost is not a parameter we selected in the upload CSV. It is one of the returned SCR transition subrisk families.",
      "Use All drivers to see the worst returned transition driver per scenario, or isolate Direct carbon cost and Market demand shifts to understand what is driving the peak.",
    ],
  },
  transition_trend: {
    eyebrow: "Transition",
    title: "Transition Trend",
    body: [
      "This chart follows the maximum adjusted subrisk revenue impact by scenario and horizon. With a driver selected, it follows only that subrisk family.",
      "Transition horizons run from 2025 to 2060 in 5-year steps. Missing baseline impacts can be valid model output, not parser failure.",
      "Treat the numeric impact values as raw SCR model-output values until SCR confirms the product-facing unit label.",
    ],
  },
  subrisk_drivers: {
    eyebrow: "Transition",
    title: "Subrisk Drivers",
    body: [
      "This table is row-level evidence behind the transition ranking for the selected scenario and driver filter.",
      "Direct carbon cost rows include Carbon price and scope12_intensity. Market demand shifts rows include Revenue growth, Inflation, and scope3_intensity.",
      "Scope 3 intensity is estimated by SCR from sector and country inputs in this workflow, so it should be displayed as model-derived context rather than uploaded company data.",
    ],
  },
  interpretation: {
    eyebrow: "Notes",
    title: "Interpretation Panel",
    body: [
      "This panel turns the selected chart state into a short reading. It is not a separate model result.",
      "The safest product pattern is to show overall rating, top quantified driver, top severity indicators, scenario, horizon, and the raw-value caveat together.",
    ],
  },
  join_key: {
    eyebrow: "Join Back",
    title: "Join Key",
    body: [
      "The SCR output repeats assetName on every row. That is the field we join back to our private scr_manifest.csv.",
      "The manifest then maps scr_asset_name to plant_uuid, portfolio context, and any tenant-specific asset identity. SCR assetId should be stored as vendor metadata, not used as the canonical database key.",
    ],
  },
};

function el(id) {
  return document.getElementById(id);
}

function unique(values) {
  return [...new Set(values.filter((value) => value !== null && value !== undefined && value !== ""))];
}

function driverLabel(value) {
  return DRIVER_LABELS[value] || value || "n/a";
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

function ratingMeaning(value) {
  const score = ratingScore(value);
  if (!score) return "No SCR rating";
  if (score <= 2) return "Lower exposure";
  if (score <= 4) return "Moderate exposure";
  return "Higher exposure";
}

function severityMeter(value) {
  const score = ratingScore(value);
  const tone = score >= 5 ? "high" : score >= 3 ? "mid" : "low";
  return `
    <span class="severity-meter" aria-label="${escapeHtml(ratingMeaning(value))}">
      ${[1, 2, 3, 4, 5, 6, 7]
        .map((index) => `<span class="severity-cell ${index <= score ? `is-on ${tone}` : ""}"></span>`)
        .join("")}
    </span>
  `;
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

function physicalDisplayValue(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return null;
  }
  const number = Number(value);
  if (state.physicalDisplay === "percent") {
    return number * 100;
  }
  if (state.physicalDisplay === "basis_points") {
    return number * 10000;
  }
  return number;
}

function physicalDisplayLabel() {
  if (state.physicalDisplay === "percent") {
    return "percent-style display";
  }
  if (state.physicalDisplay === "basis_points") {
    return "basis-point display";
  }
  return "raw SCR value";
}

function formatPhysicalImpact(value, options = {}) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "not quantified";
  }
  const number = Number(value);
  if (state.physicalDisplay === "percent") {
    const shown = `${(number * 100).toFixed(4)}%`;
    return options.includeRaw ? `${shown} (raw ${number.toFixed(9)})` : shown;
  }
  if (state.physicalDisplay === "basis_points") {
    const shown = `${(number * 10000).toFixed(2)} bps`;
    return options.includeRaw ? `${shown} (raw ${number.toFixed(9)})` : shown;
  }
  return `${number.toFixed(9)} raw`;
}

function formatValueWithUnit(value, unit) {
  const formatted = formatNumber(value);
  if (formatted === "n/a") {
    return formatted;
  }
  return `${formatted}${unit ? ` ${unit}` : ""}`;
}

function setOptions(select, options, selected, labelFn = (value) => value) {
  select.innerHTML = options
    .map((option) => `<option value="${escapeHtml(option)}">${escapeHtml(labelFn(option))}</option>`)
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

function transitionDriverOptions(transition) {
  return ["all", ...unique(transition.subrisks.map((row) => row.subrisk))];
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
  const transitionDrivers = transitionDriverOptions(transition);
  state.transitionScenario = preferredValue(transitionScenarios, "Net Zero 2050");
  state.transitionDriver = preferredValue(transitionDrivers, "all");

  setOptions(el("assetSelect"), state.data.assets.map((item) => item.asset_name), state.assetName);
  refreshControls();
}

function refreshControls() {
  const physical = physicalRows(state.assetName);
  const transition = transitionRows(state.assetName);
  const physicalScenarios = unique(physical.trends.map((row) => row.scenario));
  const physicalHorizons = sortNumeric(unique(physical.trends.map((row) => row.horizon)));
  const transitionScenarios = unique(transition.rankings.map((row) => row.scenario));
  const transitionDrivers = transitionDriverOptions(transition);

  if (!physicalScenarios.includes(state.physicalScenario)) {
    state.physicalScenario = preferredValue(physicalScenarios, "ssp5-8.5");
  }
  if (!physicalHorizons.map(String).includes(String(state.physicalHorizon))) {
    state.physicalHorizon = preferredValue(physicalHorizons, 2100, physicalHorizons.length - 1);
  }
  if (!transitionScenarios.includes(state.transitionScenario)) {
    state.transitionScenario = preferredValue(transitionScenarios, "Net Zero 2050");
  }
  if (!transitionDrivers.includes(state.transitionDriver)) {
    state.transitionDriver = "all";
  }

  setOptions(el("physicalScenarioSelect"), physicalScenarios, state.physicalScenario);
  setOptions(el("physicalHorizonSelect"), physicalHorizons, state.physicalHorizon);
  setOptions(el("transitionScenarioSelect"), transitionScenarios, state.transitionScenario);
  setOptions(el("transitionDriverSelect"), transitionDrivers, state.transitionDriver, driverLabel);
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
  el("physicalDisplaySelect").addEventListener("change", (event) => {
    state.physicalDisplay = event.target.value;
    render();
  });
  el("transitionScenarioSelect").addEventListener("change", (event) => {
    state.transitionScenario = event.target.value;
    render();
  });
  el("transitionDriverSelect").addEventListener("change", (event) => {
    state.transitionDriver = event.target.value;
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
  el("helpToggle").addEventListener("click", () => {
    const panel = el("helpPanel");
    const isHidden = panel.classList.toggle("is-hidden");
    el("helpToggle").classList.toggle("is-active", !isHidden);
  });
  el("contextClose").addEventListener("click", closeContextHelp);
  document.querySelector("main").addEventListener("click", (event) => {
    const button = event.target.closest("[data-help]");
    if (!button) return;
    openContextHelp(button.dataset.help);
  });
}

function openContextHelp(key) {
  const content = HELP_CONTENT[key] || {
    eyebrow: "Metric Notes",
    title: "Metric notes",
    body: ["No detailed notes are available for this dashboard element yet."],
  };
  el("contextEyebrow").textContent = content.eyebrow || "Metric Notes";
  el("contextTitle").textContent = content.title || "Metric notes";
  el("contextBody").innerHTML = (content.body || [])
    .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
    .join("");
  el("contextPanel").classList.remove("is-hidden");
  el("contextPanel").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function closeContextHelp() {
  el("contextPanel").classList.add("is-hidden");
}

function metric(label, value, detail, helpKey) {
  return `
    <article class="metric">
      <div class="metric-header">
        <span class="metric-label">${escapeHtml(label)}</span>
        ${helpKey ? `<button class="eye-button metric-eye" data-help="${escapeHtml(helpKey)}" type="button">View</button>` : ""}
      </div>
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

function filteredTransitionSubrisks(transition) {
  return transition.subrisks.filter(
    (row) => state.transitionDriver === "all" || row.subrisk === state.transitionDriver,
  );
}

function validImpact(value) {
  return value !== null && value !== undefined && !Number.isNaN(Number(value));
}

function bestImpactRow(rows) {
  return rows
    .filter((row) => validImpact(row.adjusted_revenue_impact))
    .sort((a, b) => Number(b.adjusted_revenue_impact) - Number(a.adjusted_revenue_impact))[0];
}

function transitionRankingsForDriver(transition) {
  const baseRankings = [...transition.rankings].sort(
    (a, b) => Number(b.peak_impact || 0) - Number(a.peak_impact || 0),
  );
  if (state.transitionDriver === "all") {
    return baseRankings;
  }

  const baseByScenario = new Map(baseRankings.map((row) => [row.scenario, row]));
  return unique(transition.subrisks.map((row) => row.scenario))
    .map((scenario) => {
      const best = bestImpactRow(
        transition.subrisks.filter((row) => row.scenario === scenario && row.subrisk === state.transitionDriver),
      );
      if (!best) return null;
      const base = baseByScenario.get(scenario) || {};
      return {
        ...base,
        asset_name: best.asset_name,
        scenario,
        peak_impact: best.adjusted_revenue_impact,
        peak_subrisk: best.subrisk,
        peak_year: best.horizon,
        selected_driver_peak: {
          asset_name: best.asset_name,
          rating: best.rating,
          subrisk: best.subrisk,
          value: best.adjusted_revenue_impact,
          year: best.horizon,
        },
      };
    })
    .filter(Boolean)
    .sort((a, b) => Number(b.peak_impact || 0) - Number(a.peak_impact || 0));
}

function selectedTransitionRanking(transition) {
  const rankings = transitionRankingsForDriver(transition);
  return rankings.find((row) => row.scenario === state.transitionScenario) || rankings[0];
}

function renderSummary(asset, physical, transition) {
  const trend = selectedPhysicalTrend(physical);
  const hazards = selectedHazards(physical);
  const topHazard = hazards[0];
  const transitionRankings = transitionRankingsForDriver(transition);
  const topTransition = transitionRankings[0];
  const selectedTransition = selectedTransitionRanking(transition);

  el("assetSummary").innerHTML = [
    metric(
      "Asset",
      escapeHtml(asset.scr_asset_id || asset.asset_name),
      asset.ticcs_sub_class_name || asset.ticcs_sub_class || "",
      "kpi_asset",
    ),
    metric(
      "Physical Rating",
      ratingBadge(trend?.adjusted_physical_exposure_rating),
      `${state.physicalScenario} @ ${state.physicalHorizon}`,
      "kpi_physical_rating",
    ),
    metric(
      "Physical Impact",
      escapeHtml(formatPhysicalImpact(trend?.adjusted_total_value_impact)),
      topHazard ? `Top hazard: ${topHazard.hazard}` : "No hazard ranking",
      "kpi_physical_impact",
    ),
    metric(
      "Transition Peak",
      escapeHtml(formatNumber(topTransition?.peak_impact)),
      topTransition ? `${topTransition.scenario} @ ${topTransition.peak_year}` : "No transition ranking",
      "kpi_transition_peak",
    ),
    metric(
      "Selected Driver",
      escapeHtml(driverLabel(selectedTransition?.peak_subrisk)),
      selectedTransition
        ? `${selectedTransition.scenario} peak ${formatNumber(selectedTransition.peak_impact)} | ${driverLabel(state.transitionDriver)}`
        : "",
      "kpi_selected_driver",
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
        y: physicalDisplayValue(row.adjusted_total_value_impact),
        raw: row.adjusted_total_value_impact,
        rating: row.adjusted_physical_exposure_rating,
      })),
  }));

  el("physicalTrendKicker").textContent = `${asset.scr_asset_id || asset.asset_name} | ${state.physicalScenario} | ${physicalDisplayLabel()}`;
  renderLineChart("physicalTrendChart", trendsByScenario, {
    yLabel: `adjustedTotalValueImpact (${physicalDisplayLabel()})`,
    baselineZero: false,
    valueFormatter: formatCompact,
    tooltipFormatter: (point) =>
      `${formatPhysicalImpact(point.raw, { includeRaw: true })} | rating ${point.rating || "-"}`,
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
      const rawImpact = row.adjusted_hazard_value_impact;
      const numericImpact = Number(rawImpact || 0);
      const hasImpact = rawImpact !== null && rawImpact !== undefined;
      const width = maxValue > 0 ? (numericImpact / maxValue) * 100 : 0;
      const worst = (row.worst_indicators || [])
        .slice(0, 2)
        .map((item) => {
          const magnitude = item.value === null || item.value === undefined ? "rating only" : formatValueWithUnit(item.value, item.unit);
          return `${item.rating || "-"} ${item.indicator || ""} ${magnitude}`;
        })
        .join(" | ");
      return `
        <div class="bar-row">
          <div class="bar-label">
            <span class="bar-title">${escapeHtml(row.hazard)}</span>
            <span class="bar-subtitle">${ratingBadge(row.hazard_rating)} ${severityMeter(row.hazard_rating)} ${escapeHtml(ratingMeaning(row.hazard_rating))}</span>
            <span class="bar-subtitle">${escapeHtml(worst)}</span>
          </div>
          <div class="bar-track"><div class="bar-fill ${hasImpact ? "" : "is-empty"}" style="width:${width}%; background:${COLORS[0]}"></div></div>
          <div class="bar-value">${escapeHtml(formatPhysicalImpact(rawImpact))}</div>
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
          <th>Severity</th>
          <th>Hazard</th>
          <th>Indicator</th>
          <th>Magnitude</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
              <tr>
                <td>${ratingBadge(row.rating)}</td>
                <td>${severityMeter(row.rating)}<span class="cell-note">${escapeHtml(ratingMeaning(row.rating))}</span></td>
                <td>${escapeHtml(row.hazard || "-")}</td>
                <td>${escapeHtml(row.indicator || "-")}</td>
                <td>
                  ${escapeHtml(row.value === null || row.value === undefined ? "rating only" : formatValueWithUnit(row.value, row.unit))}
                  ${row.value === null || row.value === undefined ? '<span class="cell-note">SCR did not return numeric magnitude for this row.</span>' : ""}
                </td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function transitionTrendSeries(transition) {
  if (state.transitionDriver === "all") {
    return unique(transition.trends.map((row) => row.scenario)).map((scenario, index) => ({
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
          driver: row.top_subrisk,
        })),
    }));
  }

  const rows = filteredTransitionSubrisks(transition);
  return unique(rows.map((row) => row.scenario)).map((scenario, index) => {
    const scenarioRows = rows.filter((row) => row.scenario === scenario);
    const horizons = sortNumeric(unique(scenarioRows.map((row) => row.horizon)));
    return {
      name: scenario,
      color: COLORS[index % COLORS.length],
      selected: scenario === state.transitionScenario,
      points: horizons.map((horizon) => {
        const best = bestImpactRow(scenarioRows.filter((row) => Number(row.horizon) === Number(horizon)));
        return {
          x: Number(horizon),
          y: best?.adjusted_revenue_impact ?? null,
          rating: best?.rating,
          driver: best?.subrisk,
          indicator: best?.indicator,
        };
      }),
    };
  });
}

function renderTransition(asset, transition) {
  el("transitionRankKicker").textContent = `${asset.scr_asset_id || asset.asset_name} | ${driverLabel(state.transitionDriver)} | raw model-output values`;
  renderTransitionRanking(transition);

  const series = transitionTrendSeries(transition);
  renderLineChart("transitionTrendChart", series, {
    yLabel:
      state.transitionDriver === "all"
        ? "max adjustedSubriskRevenueImpact"
        : `${driverLabel(state.transitionDriver)} adjustedSubriskRevenueImpact`,
    baselineZero: true,
    tooltipFormatter: (point) =>
      `${formatNumber(point.y)} | ${driverLabel(point.driver)} | rating ${point.rating || "-"}${point.indicator ? ` | ${point.indicator}` : ""}`,
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
  const rankings = transitionRankingsForDriver(transition);
  if (!rankings.length) {
    el("transitionRanking").innerHTML = `<div class="empty-state">No transition rankings available.</div>`;
    return;
  }
  const maxPeak = Math.max(...rankings.map((row) => Number(row.peak_impact || 0)), 0);
  el("transitionRanking").innerHTML = rankings
    .map((row, index) => {
      const width = maxPeak > 0 ? (Number(row.peak_impact || 0) / maxPeak) * 100 : 0;
      const selected = row.scenario === state.transitionScenario ? " is-selected" : "";
      return `
        <button class="bar-row scenario-row${selected}" type="button" data-scenario="${escapeHtml(row.scenario)}">
          <div class="bar-label">
            <span class="bar-title">${index + 1}. ${escapeHtml(row.scenario)}</span>
            <span class="bar-subtitle">${escapeHtml(driverLabel(row.peak_subrisk))} peak @ ${escapeHtml(row.peak_year)}</span>
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
    .filter(
      (row) =>
        row.scenario === state.transitionScenario &&
        validImpact(row.adjusted_revenue_impact) &&
        (state.transitionDriver === "all" || row.subrisk === state.transitionDriver),
    )
    .sort((a, b) => Number(b.adjusted_revenue_impact || 0) - Number(a.adjusted_revenue_impact || 0))
    .slice(0, 18);

  if (!rows.length) {
    el("subriskTable").innerHTML = `<div class="empty-state">No subrisk rows for this scenario and driver.</div>`;
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
          <th>Indicator value</th>
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
                <td>${escapeHtml(driverLabel(row.subrisk))}</td>
                <td>${escapeHtml(row.indicator || "-")}</td>
                <td>${escapeHtml(formatValueWithUnit(row.indicator_value, row.indicator_unit))}</td>
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
  const yValues = series
    .flatMap((item) => item.points.map((point) => point.y))
    .filter((value) => value !== null && value !== undefined && !Number.isNaN(Number(value)));

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
        <text class="tick-label" x="${margin.left - 10}" y="${y + 4}" text-anchor="end">${escapeHtml((options.valueFormatter || formatCompact)(tick))}</text>
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
      const points = item.points.filter(
        (point) => point.y !== null && point.y !== undefined && !Number.isNaN(Number(point.y)),
      );
      const path = points.map((point, index) => `${index === 0 ? "M" : "L"} ${xFor(point.x)} ${yFor(point.y)}`).join(" ");
      const circles = points
        .map(
          (point) =>
            `<circle cx="${xFor(point.x)}" cy="${yFor(point.y)}" r="${item.selected ? 3.5 : 2.5}" fill="${item.color}"><title>${escapeHtml(item.name)} ${point.x}: ${options.tooltipFormatter ? options.tooltipFormatter(point) : `${formatNumber(point.y)} rating ${point.rating || "-"}`}</title></circle>`,
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
  const transitionRankings = transitionRankingsForDriver(transition);
  const selectedTransition = selectedTransitionRanking(transition);
  const topTransition = transitionRankings[0];

  el("interpretationBody").innerHTML = `
    <p><strong>Asset context:</strong> ${escapeHtml(asset.scr_asset_id || asset.asset_name)} is modeled as ${escapeHtml(asset.ticcs_sub_class_name || "an infrastructure asset")} at ${escapeHtml(asset.coordinates || "unknown coordinates")}.</p>
    <p><strong>Physical:</strong> ${escapeHtml(state.physicalScenario)} at ${escapeHtml(state.physicalHorizon)} returns overall rating ${escapeHtml(trend?.adjusted_physical_exposure_rating || "-")} and adjusted total value impact ${escapeHtml(formatPhysicalImpact(trend?.adjusted_total_value_impact, { includeRaw: true }))}${change ? `, a ${escapeHtml(change)}% move from the first returned horizon` : ""}. ${topHazard ? `The top quantified hazard is ${escapeHtml(topHazard.hazard)}.` : ""}</p>
    <p><strong>Transition:</strong> with the ${escapeHtml(driverLabel(state.transitionDriver))} filter, the highest peak scenario is ${escapeHtml(topTransition?.scenario || "-")} with ${escapeHtml(formatNumber(topTransition?.peak_impact))}. The selected scenario, ${escapeHtml(selectedTransition?.scenario || "-")}, is led by ${escapeHtml(driverLabel(selectedTransition?.peak_subrisk))} at ${escapeHtml(selectedTransition?.peak_year || "-")}.</p>
    <p><strong>Caveat:</strong> physical impact can be toggled between raw, percent-style, and basis-point display. Percent-style and basis-point displays are readability conversions from the raw SCR value, not confirmed vendor unit labels.</p>
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
