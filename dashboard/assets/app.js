const DATA_URLS = [
  "data/scr_multi_asset_test.json",
  "data/example_asset_1232.json",
];

const COLORS = ["#2f6f9f", "#218a61", "#b7791f", "#6f5ab8", "#c2410c", "#0f8b8d"];
const RATING_SCORE = { A: 1, B: 2, C: 3, D: 4, E: 5, F: 6, G: 7 };
const DRIVER_LABELS = {
  all: "All drivers",
  Direct_carbon_cost: "Direct carbon cost",
  Market_demand_shifts: "Market demand shifts",
};
const PHYSICAL_METRICS = {
  damage: {
    field: "adjusted_total_damage",
    title: "Physical Damage Trend",
    shortLabel: "damage",
    label: "Physical damage",
    source: "adjustedTotalDamage",
    description: "adjustedTotalDamage, the closest returned SCR field to a direct property-loss or EL basis. It is not asserted as InfraSure expected loss without validation.",
  },
  value_impact: {
    field: "adjusted_total_value_impact",
    title: "Physical Combined Value Impact Trend",
    shortLabel: "combined value impact",
    label: "Physical combined value impact",
    source: "adjustedTotalValueImpact",
    description: "adjustedTotalValueImpact, combining physical damage and disruption damage-equivalent into a value-impact signal. It is not automatically an expected-loss metric.",
  },
  disruption: {
    field: "adjusted_total_disruption",
    title: "Physical Disruption Trend",
    shortLabel: "disruption",
    label: "Physical revenue/business disruption",
    source: "adjustedTotalDisruption",
    description: "adjustedTotalDisruption, SCR's physical disruption metric tied to revenue and business-continuity exposure.",
  },
};
const HAZARD_TREND_METRICS = {
  damage: {
    field: "adjusted_hazard_damage",
    title: "Hazard Damage Trend",
    shortLabel: "hazard damage",
    label: "Hazard damage",
    source: "adjustedHazardDamage",
  },
  value_impact: {
    field: "adjusted_hazard_value_impact",
    title: "Hazard Combined Value Impact Trend",
    shortLabel: "hazard combined value impact",
    label: "Hazard combined value impact",
    source: "adjustedHazardValueImpact",
    fallbackSource: "derived from available adjustedHazardDamage and adjustedHazardDisruptionDamageEquivalent components",
  },
  disruption: {
    field: "adjusted_hazard_disruption",
    title: "Hazard Disruption Trend",
    shortLabel: "hazard disruption",
    label: "Hazard disruption",
    source: "adjustedHazardDisruption",
  },
};
const DELTA_DENOMINATOR_SHARE_THRESHOLD = 0.01;
const DELTA_LARGE_RATIO_THRESHOLD = 5;
const DELTA_DIAGNOSTICS = {
  "not-quantified": {
    label: "Not quantified",
    detail: "Baseline or selected metric is missing.",
  },
  "invalid-baseline": {
    label: "Zero/invalid baseline",
    detail: "A raw factor cannot be computed from this baseline.",
  },
  flat: {
    label: "Flat",
    detail: "No meaningful change at the returned precision.",
  },
  "denominator-sensitive": {
    label: "Denominator-sensitive",
    detail: "Hazard baseline is below 1% of the overall asset baseline.",
  },
  "large-ratio": {
    label: "Large ratio",
    detail: "Absolute raw factor is 5x or greater.",
  },
  usable: {
    label: "Usable",
    detail: "No initial screening flag was triggered.",
  },
};
const HAZARD_CURVE_METRICS = [
  {
    field: "adjusted_hazard_damage",
    label: "Damage",
    source: "adjustedHazardDamage",
    color: COLORS[0],
  },
  {
    field: "adjusted_hazard_disruption",
    label: "Disruption",
    source: "adjustedHazardDisruption",
    color: COLORS[1],
  },
  {
    field: "adjusted_hazard_disruption_damage_equivalent",
    label: "Disruption equivalent",
    source: "adjustedHazardDisruptionDamageEquivalent",
    color: COLORS[2],
  },
  {
    field: "adjusted_hazard_value_impact",
    label: "Combined value impact",
    source: "adjustedHazardValueImpact",
    color: COLORS[4],
  },
];
const HAZARD_RESPONSE_FALLBACKS = [
  {
    field: "adjusted_hazard_damage",
    label: "Damage",
    source: "adjustedHazardDamage",
    color: COLORS[0],
  },
  {
    field: "adjusted_hazard_disruption",
    label: "Disruption",
    source: "adjustedHazardDisruption",
    color: COLORS[1],
  },
  {
    field: "adjusted_hazard_value_impact",
    label: "Combined value impact",
    source: "adjustedHazardValueImpact",
    color: COLORS[4],
  },
];

const state = {
  data: null,
  assetName: null,
  activeView: "physical",
  physicalScenario: null,
  physicalHorizon: null,
  physicalDisplay: "percent",
  physicalMetric: "value_impact",
  hazardTrendSelection: [],
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
      "SCR ratings run from A to G. A means lowest exposure in SCR's reference infrastructure universe, and G means highest exposure.",
      "The benchmark is not only this dashboard file, not only our database, and not only this asset's portfolio. The metadata describes a reference infrastructure universe anchored to the Expected scenario and 2035 horizon.",
      "The overall physical rating can remain A while individual hazard indicators are worse. Use this card with Hazard Ranking and Indicator Detail before making a judgment.",
    ],
  },
  kpi_physical_impact: {
    eyebrow: "Physical",
    title: "Physical Impact",
    body: [
      "This card follows the selected physical trend metric. Damage uses adjustedTotalDamage. Combined Value uses adjustedTotalValueImpact, the combined physical damage plus disruption damage-equivalent signal. Disruption uses adjustedTotalDisruption.",
      "Damage is the closest returned SCR field to a direct property-loss or EL basis, but it is not asserted as InfraSure expected loss until that mapping is validated.",
      "Combined value impact is an SCR model-output signal. Do not automatically call it expected loss (EL) without confirming the intended vendor definition and the financial application.",
      "Physical disruption is SCR's revenue/business-continuity style physical metric. It is separate from transition adjustedSubriskRevenueImpact.",
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
    title: "Physical Trend",
    body: [
      "The Trend metric toggle switches this plot among adjustedTotalDamage, adjustedTotalValueImpact, and adjustedTotalDisruption.",
      "Damage is the closest returned SCR field to a direct property-loss or EL basis, but it still needs mapping validation. Combined value impact is the physical damage plus disruption damage-equivalent signal and is not automatically expected loss. Disruption is the physical revenue/business-continuity signal.",
      "Physical horizons run from 2025 to 2100 in 5-year steps. SCR methodology describes indicator values as 10-year averages centered on the horizon, while financial impacts are average annual impacts from 2025 through the selected horizon.",
      "Use the Impact display control to inspect raw SCR values, percent-style values, or basis points. The underlying JSON keeps the raw SCR number.",
    ],
  },
  hazard_trend: {
    eyebrow: "Chart",
    title: "Hazard Trend",
    body: [
      "This chart breaks the overall physical trend into returned hazard-level metrics for the selected physical scenario.",
      "Damage uses adjustedHazardDamage. Combined Value uses adjustedHazardValueImpact when it is returned; otherwise it sums whichever adjustedHazardDamage and adjustedHazardDisruptionDamageEquivalent components are available and labels that fallback as derived. Disruption uses adjustedHazardDisruption.",
      "Only hazards with quantified returned values are drawn as lines. Other returned hazards can still have ratings and indicators, but SCR did not return a numeric value for this specific hazard metric.",
      "Use the Visible hazards buttons to show all quantified hazards, isolate one hazard on its own rescaled Y-axis, or select a smaller comparison set.",
      "Hover a plotted point to see its horizon, displayed value, raw SCR value, rating, and source. The same values are available from the keyboard by tabbing to a point.",
      "When exactly two hazards are shown, the chart uses a dual Y-axis local scale so small movement is visible for both hazards.",
      "The selected horizon still controls the Hazard Ranking and Indicator Detail sections below; this chart shows the whole numeric horizon path for the selected scenario.",
    ],
  },
  delta_test: {
    eyebrow: "Screening Test",
    title: "Climate Change Delta Test",
    body: [
      "This table compares the selected horizon with the earliest returned horizon for the same asset, scenario, and Damage/Combined Value/Disruption metric.",
      "Raw factor is selected value divided by baseline value. Percent change is the same movement expressed as (factor - 1) times 100. Loss-magnitude change is absolute selected value minus absolute baseline value and stays in the current Impact display.",
      "Baseline share compares each hazard baseline with the overall asset baseline. It is denominator context, not an assertion that hazard rows reconcile exactly to the overall asset value.",
      "Diagnostics are screening flags only: below 1% baseline share is denominator-sensitive and an absolute factor of 5x or more is a large ratio. No ceiling, cap, or logarithmic compression is applied.",
      "Current SCR physical-loss exports can use negative signed values. Raw values stay visible; selected divided by baseline is also the loss-magnitude ratio while both signs match.",
      "For Combined Value, the hazard row uses adjustedHazardValueImpact when returned; otherwise it sums whichever adjustedHazardDamage and adjustedHazardDisruptionDamageEquivalent components are available and labels the source as derived. Damage is the closest SCR basis to direct property loss, but neither field is automatically InfraSure expected loss.",
    ],
  },
  hazard_ranking: {
    eyebrow: "Physical",
    title: "Hazard Ranking",
    body: [
      "This section follows the current Damage/Combined Value/Disruption toggle and ranks physical hazards by absolute impact magnitude for the selected scenario and horizon, then falls back to hazard rating when impacts tie. Raw signed values remain visible.",
      "For Combined Value, it uses returned adjustedHazardValueImpact when available, otherwise the same labeled derived fallback used by the Hazard Trend and Delta Test. Damage is the closest returned SCR basis to direct property loss; neither is automatically InfraSure expected loss.",
      "A hazard marked not quantified does not mean no exposure. It means SCR did not return a numeric hazard value impact for that hazard in this view.",
      "Click a hazard row to open the worst returned indicators, returned horizon curves, and magnitude-response plots where the indicator magnitude varies.",
      "Magnitude-response plots are derived views: x is the returned indicator magnitude and y is the returned hazard damage, disruption, or value-impact metric across horizons. They are not a vendor-provided vulnerability function.",
      "If a hazard value does not change when filters change, first check the returned data. In the current example, Flood has the same adjustedHazardValueImpact in the raw SCR workbook across both scenarios and all future horizons.",
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
  rating_benchmark: {
    eyebrow: "Methodology",
    title: "Rating Benchmark",
    body: [
      "Based on the SCR metadata/methodology notes, A-G ratings are benchmarked against SCR's reference infrastructure universe. A is best or lowest exposure; G is worst or highest exposure.",
      "The metadata describes ratings as percentile-style exposure scores anchored to the Expected scenario at the 2035 horizon. That means the comparison is broader than this uploaded file, this portfolio, or InfraSure's current database.",
      "We should still keep the raw SCR letter and avoid converting it into a local percentile unless SCR gives the exact benchmark population and scoring thresholds for the product UI.",
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

function physicalMetricConfig() {
  return PHYSICAL_METRICS[state.physicalMetric] || PHYSICAL_METRICS.value_impact;
}

function hazardTrendMetricConfig() {
  return HAZARD_TREND_METRICS[state.physicalMetric] || HAZARD_TREND_METRICS.value_impact;
}

function finiteMetricValue(value) {
  return value !== null && value !== undefined && Number.isFinite(Number(value));
}

function hazardMetricResult(row, metricKey = state.physicalMetric) {
  if (!row) {
    return { value: null, source: null, derived: false };
  }
  if (metricKey === "damage") {
    return finiteMetricValue(row.adjusted_hazard_damage)
      ? {
          value: Number(row.adjusted_hazard_damage),
          source: "adjustedHazardDamage",
          derived: false,
        }
      : { value: null, source: "adjustedHazardDamage", derived: false };
  }
  if (metricKey === "disruption") {
    return finiteMetricValue(row.adjusted_hazard_disruption)
      ? {
          value: Number(row.adjusted_hazard_disruption),
          source: "adjustedHazardDisruption",
          derived: false,
        }
      : { value: null, source: "adjustedHazardDisruption", derived: false };
  }
  if (finiteMetricValue(row.adjusted_hazard_value_impact)) {
    return {
      value: Number(row.adjusted_hazard_value_impact),
      source: "adjustedHazardValueImpact",
      derived: false,
    };
  }
  const hasDamage = finiteMetricValue(row.adjusted_hazard_damage);
  const hasDisruptionEquivalent = finiteMetricValue(
    row.adjusted_hazard_disruption_damage_equivalent,
  );
  if (hasDamage || hasDisruptionEquivalent) {
    const availableComponents = [
      hasDamage ? "adjustedHazardDamage" : null,
      hasDisruptionEquivalent ? "adjustedHazardDisruptionDamageEquivalent" : null,
    ].filter(Boolean);
    return {
      value:
        (hasDamage ? Number(row.adjusted_hazard_damage) : 0) +
        (hasDisruptionEquivalent
          ? Number(row.adjusted_hazard_disruption_damage_equivalent)
          : 0),
      source: `derived from available components: ${availableComponents.join(" + ")}`,
      derived: true,
    };
  }
  return {
    value: null,
    source: "adjustedHazardValueImpact or derived damage + disruption equivalent",
    derived: false,
  };
}

function sortNumeric(values) {
  return [...values].sort((a, b) => Number(a) - Number(b));
}

function validChartValue(value) {
  return value !== null && value !== undefined && !Number.isNaN(Number(value));
}

function chartSeriesValues(item) {
  return item.points.map((point) => point.y).filter(validChartValue).map(Number);
}

function chartSeriesMagnitude(item) {
  const values = chartSeriesValues(item);
  if (!values.length) return 0;
  return Math.max(...values.map((value) => Math.abs(value)));
}

function dualAxisSeriesPair(series) {
  const candidates = series.filter((item) => chartSeriesValues(item).length);
  if (candidates.length !== 2) return null;
  return [...candidates].sort((a, b) => chartSeriesMagnitude(b) - chartSeriesMagnitude(a));
}

function chartAxisDomain(values, baselineZero = false) {
  const numericValues = values.filter(validChartValue).map(Number);
  const rawMin = Math.min(...numericValues);
  const rawMax = Math.max(...numericValues);
  let min = rawMin;
  let max = rawMax;

  if (baselineZero) {
    min = Math.min(0, rawMin);
    max = Math.max(0, rawMax);
    max += Math.abs(max || 1) * 0.08;
    if (min < 0) min -= Math.abs(min) * 0.08;
  } else {
    const magnitude = Math.max(Math.abs(rawMin), Math.abs(rawMax));
    const rawSpan = rawMax - rawMin;
    const noiseFloor = Math.max(magnitude * 1e-9, 1e-12);
    const span = rawSpan > noiseFloor ? rawSpan : 0;
    const padding = span > 0 ? span * 0.18 : magnitude > 0 ? magnitude * 0.02 : 1;
    min -= padding;
    max += padding;
  }

  if (min === max) {
    const padding = Math.max(Math.abs(max), 1) * 0.05;
    min -= padding;
    max += padding;
  }

  return { min, max, range: max - min || 1 };
}

function formatChartAxisValue(value, formatter, domain) {
  if (!validChartValue(value)) return "n/a";
  const range = Math.abs(domain?.range || 0);
  if (range > 0 && range < 0.1) {
    const decimals = Math.min(9, Math.max(3, Math.ceil(-Math.log10(range)) + 2));
    return Number(value).toLocaleString(undefined, {
      maximumFractionDigits: decimals,
      minimumFractionDigits: 0,
    });
  }
  return formatter(value);
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

function assetPrimaryLabel(asset) {
  return asset.manifest?.plant_name || asset.scr_asset_id || asset.asset_name;
}

function assetContextLabel(asset, includeCoordinates = false) {
  return unique([
    asset.manifest?.plant_name ? asset.scr_asset_id : null,
    asset.ticcs_sub_class_name || asset.ticcs_sub_class,
    asset.country_code,
    includeCoordinates ? asset.coordinates : null,
  ]).join(" · ");
}

function assetOptionLabel(asset) {
  const primary = assetPrimaryLabel(asset);
  const context = assetContextLabel(asset);
  return context ? `${primary} — ${context}` : primary;
}

function setAssetOptions() {
  el("assetSelect").innerHTML = state.data.assets
    .map(
      (asset) =>
        `<option value="${escapeHtml(asset.asset_name)}">${escapeHtml(assetOptionLabel(asset))}</option>`,
    )
    .join("");
  el("assetSelect").value = state.assetName;
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
  const asset =
    state.data.assets.find((item) => item.scr_asset_id === "USA_00490") ||
    state.data.assets[0];
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

  setAssetOptions();
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
  el("physicalDamageMetric").addEventListener("click", () => {
    state.physicalMetric = "damage";
    render();
  });
  el("physicalValueMetric").addEventListener("click", () => {
    state.physicalMetric = "value_impact";
    render();
  });
  el("physicalDisruptionMetric").addEventListener("click", () => {
    state.physicalMetric = "disruption";
    render();
  });
  el("hazardTrendControls").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-hazard-series]");
    if (!button) return;
    const hazard = button.dataset.hazardSeries;
    if (hazard === "all") {
      state.hazardTrendSelection = [];
    } else if (!state.hazardTrendSelection.length) {
      state.hazardTrendSelection = [hazard];
    } else if (state.hazardTrendSelection.includes(hazard)) {
      const remaining = state.hazardTrendSelection.filter((item) => item !== hazard);
      state.hazardTrendSelection = remaining.length ? remaining : [];
    } else {
      state.hazardTrendSelection = [...state.hazardTrendSelection, hazard];
    }
    render();
    const replacementButton = [...el("hazardTrendControls").querySelectorAll("button[data-hazard-series]")]
      .find((candidate) => candidate.dataset.hazardSeries === hazard);
    replacementButton?.focus();
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
    .map((row) => ({ ...row, metricResult: hazardMetricResult(row) }))
    .sort((a, b) => {
      const aQuantified = finiteMetricValue(a.metricResult.value);
      const bQuantified = finiteMetricValue(b.metricResult.value);
      if (aQuantified !== bQuantified) return aQuantified ? -1 : 1;
      const impactDiff =
        Math.abs(Number(b.metricResult.value || 0)) -
        Math.abs(Number(a.metricResult.value || 0));
      if (impactDiff !== 0) return impactDiff;
      return ratingScore(b.hazard_rating) - ratingScore(a.hazard_rating);
    });
}

function hasStaticHazardImpact(physical, hazard) {
  const values = physical.hazards
    .filter((row) => row.hazard === hazard && finiteMetricValue(hazardMetricResult(row).value))
    .map((row) => Number(hazardMetricResult(row).value).toPrecision(12));
  return values.length > 1 && unique(values).length === 1;
}

function renderWorstIndicatorChips(indicators) {
  if (!indicators?.length) {
    return `<div class="empty-state compact-empty">No indicator details returned for this hazard.</div>`;
  }
  return `
    <div class="indicator-chip-grid">
      ${indicators
        .map((item) => {
          const magnitude =
            item.value === null || item.value === undefined ? "rating only" : formatValueWithUnit(item.value, item.unit);
          return `
            <div class="indicator-chip">
              <div class="indicator-chip-rating">${ratingBadge(item.rating)} ${severityMeter(item.rating)}</div>
              <div class="indicator-chip-body">
                <span class="indicator-chip-title">${escapeHtml(item.indicator || "-")}</span>
                <span class="indicator-chip-value">${escapeHtml(magnitude)}</span>
              </div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function hazardRowsForScenario(physical, hazard) {
  return physical.hazards
    .filter((row) => row.scenario === state.physicalScenario && row.hazard === hazard)
    .sort((a, b) => Number(a.horizon) - Number(b.horizon));
}

function isEffectivelyFlat(values) {
  const numeric = values.filter((value) => validImpact(value)).map(Number);
  if (numeric.length < 2) return true;
  const min = Math.min(...numeric);
  const max = Math.max(...numeric);
  return Math.abs(max - min) <= 1e-9;
}

function paddedDomain(values, flatPadRatio = 0.1) {
  const minRaw = Math.min(...values);
  const maxRaw = Math.max(...values);
  if (isEffectivelyFlat(values)) {
    const center = values.reduce((total, value) => total + value, 0) / values.length;
    const pad = Math.max(Math.abs(center) * flatPadRatio, 1e-6);
    return { min: center - pad, max: center + pad, flat: true, center };
  }
  return { min: minRaw, max: maxRaw, flat: false, center: null };
}

function renderMiniHazardCurve(rows, metric) {
  const points = rows
    .filter((row) => validImpact(row[metric.field]))
    .map((row) => ({
      horizon: Number(row.horizon),
      raw: Number(row[metric.field]),
      shown: physicalDisplayValue(row[metric.field]),
      selected: Number(row.horizon) === Number(state.physicalHorizon),
    }));

  if (!points.length) {
    return "";
  }

  const width = 260;
  const height = 76;
  const margin = { top: 10, right: 10, bottom: 18, left: 10 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const xValues = points.map((point) => point.horizon);
  const yValues = points.map((point) => point.shown).filter((value) => validImpact(value));
  const yDomain = paddedDomain(yValues);
  const yMin = yDomain.min;
  const yMax = yDomain.max;
  const flat = yDomain.flat;
  const yRange = yMax - yMin || 1;

  const xFor = (value) => {
    const index = xValues.indexOf(value);
    if (xValues.length === 1) return margin.left + innerWidth / 2;
    return margin.left + (index / (xValues.length - 1)) * innerWidth;
  };
  const yFor = (value) => margin.top + innerHeight - ((Number(value) - yMin) / yRange) * innerHeight;
  const yPlot = (point) => (flat ? yDomain.center : point.shown);
  const path = points.map((point, index) => `${index === 0 ? "M" : "L"} ${xFor(point.horizon)} ${yFor(yPlot(point))}`).join(" ");
  const selected = points.find((point) => point.selected) || points[points.length - 1];
  const first = points[0];
  const last = points[points.length - 1];

  const circles = points
    .map((point) =>
      chartPointMarkup({
        x: xFor(point.horizon),
        y: yFor(yPlot(point)),
        radius: point.selected ? 3.5 : 2,
        color: metric.color,
        label: `${metric.label} · horizon ${point.horizon}: ${formatPhysicalImpact(point.raw, { includeRaw: true })}`,
      }),
    )
    .join("");

  return `
    <article class="hazard-curve-card">
      <div class="hazard-curve-head">
        <span>${escapeHtml(metric.label)}</span>
        <span>${escapeHtml(formatPhysicalImpact(selected.raw))}</span>
      </div>
      <svg class="hazard-sparkline" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(metric.label)} curve">
        <line class="spark-axis" x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}"></line>
        <path d="${path}" fill="none" stroke="${metric.color}" stroke-width="2.5"></path>
        <line class="spark-selected" x1="${xFor(selected.horizon)}" x2="${xFor(selected.horizon)}" y1="${margin.top}" y2="${height - margin.bottom}"></line>
        ${circles}
        <text class="spark-label" x="${margin.left}" y="${height - 4}" text-anchor="start">${escapeHtml(first.horizon)}</text>
        <text class="spark-label" x="${width - margin.right}" y="${height - 4}" text-anchor="end">${escapeHtml(last.horizon)}</text>
      </svg>
      <div class="hazard-curve-meta">
        <span>Start ${escapeHtml(formatPhysicalImpact(first.raw))}</span>
        <span>End ${escapeHtml(formatPhysicalImpact(last.raw))}</span>
      </div>
      <span class="cell-note">${escapeHtml(metric.source)} | ${flat ? "flat in returned data" : physicalDisplayLabel()}</span>
    </article>
  `;
}

function selectHazardResponseMetric(rows) {
  return HAZARD_RESPONSE_FALLBACKS.find((metric) => rows.some((row) => validImpact(row[metric.field])));
}

function responseIndicatorSeries(physical, hazard, responseMetric) {
  const rows = hazardRowsForScenario(physical, hazard);
  const responseByHorizon = new Map(
    rows.filter((row) => validImpact(row[responseMetric.field])).map((row) => [Number(row.horizon), Number(row[responseMetric.field])]),
  );
  const grouped = new Map();

  physical.indicators
    .filter(
      (row) =>
        row.scenario === state.physicalScenario &&
        row.hazard === hazard &&
        validImpact(row.value) &&
        responseByHorizon.has(Number(row.horizon)),
    )
    .forEach((row) => {
      const key = `${row.indicator || "-"}|${row.unit || ""}`;
      if (!grouped.has(key)) {
        grouped.set(key, {
          indicator: row.indicator || "-",
          unit: row.unit || "",
          points: [],
        });
      }
      grouped.get(key).points.push({
        horizon: Number(row.horizon),
        x: Number(row.value),
        y: responseByHorizon.get(Number(row.horizon)),
        rating: row.rating,
        selected: Number(row.horizon) === Number(state.physicalHorizon),
      });
    });

  return [...grouped.values()]
    .map((series) => ({
      ...series,
      points: series.points.sort((a, b) => a.x - b.x || a.horizon - b.horizon),
      uniqueXCount: unique(series.points.map((point) => point.x.toPrecision(12))).length,
      uniqueYCount: unique(series.points.map((point) => point.y.toPrecision(12))).length,
    }))
    .filter((series) => series.points.length >= 3 && series.uniqueXCount > 1)
    .sort((a, b) => b.uniqueYCount - a.uniqueYCount || b.uniqueXCount - a.uniqueXCount || a.indicator.localeCompare(b.indicator))
    .slice(0, 4);
}

function renderMagnitudeResponseCard(series, responseMetric, index) {
  const width = 260;
  const height = 112;
  const margin = { top: 12, right: 12, bottom: 26, left: 36 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const xValues = series.points.map((point) => point.x);
  const yValues = series.points.map((point) => physicalDisplayValue(point.y)).filter((value) => validImpact(value));
  const xDomain = paddedDomain(xValues, 0.08);
  const yDomain = paddedDomain(yValues, 0.12);
  const xRange = xDomain.max - xDomain.min || 1;
  const yRange = yDomain.max - yDomain.min || 1;
  const color = COLORS[(index + 2) % COLORS.length];

  const xFor = (value) => margin.left + ((Number(value) - xDomain.min) / xRange) * innerWidth;
  const yFor = (value) => margin.top + innerHeight - ((Number(value) - yDomain.min) / yRange) * innerHeight;
  const yPlot = (point) => (yDomain.flat ? yDomain.center : physicalDisplayValue(point.y));
  const path = series.points.map((point, pointIndex) => `${pointIndex === 0 ? "M" : "L"} ${xFor(point.x)} ${yFor(yPlot(point))}`).join(" ");
  const selected = series.points.find((point) => point.selected);

  const circles = series.points
    .map((point) =>
      chartPointMarkup({
        x: xFor(point.x),
        y: yFor(yPlot(point)),
        radius: point.selected ? 3.8 : 2.2,
        color,
        label: `Horizon ${point.horizon} · ${series.indicator} ${formatValueWithUnit(point.x, series.unit)} -> ${formatPhysicalImpact(point.y, { includeRaw: true })}`,
      }),
    )
    .join("");

  return `
    <article class="magnitude-card">
      <div class="magnitude-head">
        <span>${escapeHtml(series.indicator)}</span>
        ${selected ? `<span>${escapeHtml(formatValueWithUnit(selected.x, series.unit))} -> ${escapeHtml(formatPhysicalImpact(selected.y))}</span>` : ""}
      </div>
      <svg class="magnitude-plot" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(series.indicator)} magnitude response">
        <line class="spark-axis" x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}"></line>
        <line class="spark-axis" x1="${margin.left}" x2="${margin.left}" y1="${margin.top}" y2="${height - margin.bottom}"></line>
        <path d="${path}" fill="none" stroke="${color}" stroke-width="2.2"></path>
        ${circles}
        <text class="spark-label" x="${margin.left}" y="${height - 7}" text-anchor="start">${escapeHtml(formatCompact(xDomain.min))}</text>
        <text class="spark-label" x="${width - margin.right}" y="${height - 7}" text-anchor="end">${escapeHtml(formatCompact(xDomain.max))}</text>
        <text class="spark-label" x="${margin.left - 5}" y="${yFor(yDomain.max) + 4}" text-anchor="end">${escapeHtml(formatCompact(yDomain.max))}</text>
        <text class="spark-label" x="${margin.left - 5}" y="${yFor(yDomain.min) + 4}" text-anchor="end">${escapeHtml(formatCompact(yDomain.min))}</text>
      </svg>
      <div class="magnitude-meta">
        <span>x: ${escapeHtml(series.unit || "indicator magnitude")}</span>
        <span>y: ${escapeHtml(responseMetric.label)}</span>
      </div>
      <span class="cell-note">${escapeHtml(responseMetric.source)} | derived from returned scenario/horizon rows${yDomain.flat ? " | flat response" : ""}</span>
    </article>
  `;
}

function renderMagnitudeResponseCurves(physical, hazard) {
  const rows = hazardRowsForScenario(physical, hazard);
  const responseMetric = selectHazardResponseMetric(rows);
  if (!responseMetric) {
    return `<div class="empty-state compact-empty">No returned hazard damage, disruption, or value-impact metric is available for a magnitude-response plot.</div>`;
  }
  const series = responseIndicatorSeries(physical, hazard, responseMetric);
  if (!series.length) {
    return `<div class="empty-state compact-empty">No varying indicator magnitude is available for this hazard/scenario, so a magnitude-vs-${escapeHtml(responseMetric.label.toLowerCase())} curve would be misleading.</div>`;
  }
  return `
    <div class="magnitude-grid">
      ${series.map((item, index) => renderMagnitudeResponseCard(item, responseMetric, index)).join("")}
    </div>
    <p class="cell-note">These are derived response views, not confirmed SCR vulnerability functions. They join returned indicator magnitude to the returned hazard ${escapeHtml(responseMetric.label.toLowerCase())} metric across horizons.</p>
  `;
}

function renderHazardMetricCurves(physical, hazard) {
  const rows = hazardRowsForScenario(physical, hazard);
  const cards = HAZARD_CURVE_METRICS.map((metric) => renderMiniHazardCurve(rows, metric)).filter(Boolean);
  if (!cards.length) {
    return `<div class="empty-state compact-empty">SCR did not return quantified hazard-level damage or disruption curves for this hazard/scenario.</div>`;
  }
  return `
    <div class="hazard-curve-grid">
      ${cards.join("")}
    </div>
  `;
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
  const metricConfig = physicalMetricConfig();
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
      metricConfig.label,
      escapeHtml(formatPhysicalImpact(trend?.[metricConfig.field])),
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
  const metricConfig = physicalMetricConfig();
  const trendsByScenario = unique(physical.trends.map((row) => row.scenario)).map((scenario, index) => ({
    name: scenario,
    color: COLORS[index % COLORS.length],
    selected: scenario === state.physicalScenario,
    points: physical.trends
      .filter((row) => row.scenario === scenario)
      .sort((a, b) => Number(a.horizon) - Number(b.horizon))
      .map((row) => ({
        x: Number(row.horizon),
        y: physicalDisplayValue(row[metricConfig.field]),
        raw: row[metricConfig.field],
        rating: row.adjusted_physical_exposure_rating,
      })),
  }));

  el("physicalTrendTitle").textContent = metricConfig.title;
  el("physicalTrendKicker").textContent = `${asset.scr_asset_id || asset.asset_name} | ${state.physicalScenario} | ${metricConfig.shortLabel} | ${physicalDisplayLabel()}`;
  renderLineChart("physicalTrendChart", trendsByScenario, {
    yLabel: `${metricConfig.label} (${physicalDisplayLabel()})`,
    baselineZero: false,
    valueFormatter: formatCompact,
    tooltipFormatter: (point) =>
      `${formatPhysicalImpact(point.raw, { includeRaw: true })} | ${metricConfig.shortLabel} | rating ${point.rating || "-"}`,
  });

  renderHazardRanking(physical);
  renderIndicatorTable(physical);
  renderHazardTrend(asset, physical);
  renderDeltaTest(asset, physical);
}

function hazardTrendData(physical) {
  const metricConfig = hazardTrendMetricConfig();
  const rows = physical.hazards.filter((row) => row.scenario === state.physicalScenario);
  const hazardNames = unique(rows.map((row) => row.hazard)).sort((a, b) => String(a).localeCompare(String(b)));
  const quantifiedHazards = new Set(
    rows.filter((row) => finiteMetricValue(hazardMetricResult(row).value)).map((row) => row.hazard),
  );
  const derivedHazards = new Set(
    rows.filter((row) => hazardMetricResult(row).derived).map((row) => row.hazard),
  );
  const selectedRows = rows
    .filter((row) => Number(row.horizon) === Number(state.physicalHorizon))
    .map((row) => ({ ...row, metricResult: hazardMetricResult(row) }))
    .filter((row) => finiteMetricValue(row.metricResult.value));
  const topHazard = selectedRows.sort(
    (a, b) =>
      Math.abs(Number(b.metricResult.value || 0)) -
      Math.abs(Number(a.metricResult.value || 0)),
  )[0];
  const series = hazardNames
    .filter((hazard) => quantifiedHazards.has(hazard))
    .map((hazard, index) => ({
      name: hazard,
      color: COLORS[index % COLORS.length],
      selected: hazard === topHazard?.hazard,
      points: rows
        .filter((row) => row.hazard === hazard)
        .sort((a, b) => Number(a.horizon) - Number(b.horizon))
        .map((row) => {
          const result = hazardMetricResult(row);
          return {
            x: Number(row.horizon),
            y: physicalDisplayValue(result.value),
            raw: result.value,
            rating: row.hazard_rating,
            source: result.source,
            derived: result.derived,
          };
        }),
    }));

  return {
    metricConfig,
    series,
    quantifiedHazards: [...quantifiedHazards].sort((a, b) => String(a).localeCompare(String(b))),
    derivedHazards: [...derivedHazards].sort((a, b) => String(a).localeCompare(String(b))),
    unquantifiedHazards: hazardNames.filter((hazard) => !quantifiedHazards.has(hazard)),
    topHazard,
    totalHazards: hazardNames.length,
  };
}

function selectedHazardTrendSeries(series) {
  const availableNames = new Set(series.map((item) => item.name));
  const selectedNames = state.hazardTrendSelection.filter((name) => availableNames.has(name));
  if (selectedNames.length !== state.hazardTrendSelection.length) {
    state.hazardTrendSelection = selectedNames;
  }
  return {
    selectedNames,
    visibleSeries: selectedNames.length
      ? series.filter((item) => selectedNames.includes(item.name))
      : series,
  };
}

function renderHazardTrendControls(series, selectedNames) {
  const selected = new Set(selectedNames);
  const allActive = selected.size === 0;
  const buttons = [
    `<button type="button" class="series-filter-button ${allActive ? "is-active" : ""}" data-hazard-series="all" aria-pressed="${allActive}">All</button>`,
    ...series.map((item) => {
      const isActive = selected.has(item.name);
      return `
        <button
          type="button"
          class="series-filter-button ${isActive ? "is-active" : ""}"
          data-hazard-series="${escapeHtml(item.name)}"
          aria-pressed="${isActive}"
          title="${isActive ? "Remove" : allActive ? "Show only" : "Add"} ${escapeHtml(item.name)}"
        >
          <span class="series-filter-swatch" style="background:${item.color}"></span>
          ${escapeHtml(item.name)}
        </button>
      `;
    }),
  ];
  el("hazardTrendControls").innerHTML = buttons.join("");
}

function renderHazardTrend(asset, physical) {
  const {
    metricConfig,
    series,
    quantifiedHazards,
    derivedHazards,
    unquantifiedHazards,
    totalHazards,
  } = hazardTrendData(physical);

  const { selectedNames, visibleSeries } = selectedHazardTrendSeries(series);
  renderHazardTrendControls(series, selectedNames);

  el("hazardTrendTitle").textContent = metricConfig.title;
  el("hazardTrendKicker").textContent = `${asset.scr_asset_id || asset.asset_name} | ${state.physicalScenario} | ${metricConfig.shortLabel} | ${physicalDisplayLabel()}`;

  renderLineChart("hazardTrendChart", visibleSeries, {
    yLabel: `${metricConfig.label} (${physicalDisplayLabel()})`,
    baselineZero: false,
    dualAxis: true,
    dualAxisBaselineZero: false,
    highlightSelected: false,
    valueFormatter: formatCompact,
    tooltipFormatter: (point) =>
      `${formatPhysicalImpact(point.raw, { includeRaw: true })} | ${point.source || metricConfig.source} | rating ${point.rating || "-"}`,
  });

  const sourceLabel =
    state.physicalMetric === "value_impact"
      ? "combined value impact (direct adjustedHazardValueImpact or derived fallback)"
      : metricConfig.source;
  const quantifiedText = `${quantifiedHazards.length} of ${totalHazards} hazards have quantified ${sourceLabel}`;
  const topVisible = visibleSeries
    .map((item) => ({
      hazard: item.name,
      point: item.points.find((point) => Number(point.x) === Number(state.physicalHorizon)),
    }))
    .filter((item) => finiteMetricValue(item.point?.raw))
    .sort((a, b) => Math.abs(Number(b.point.raw)) - Math.abs(Number(a.point.raw)))[0];
  const topText = topVisible
    ? `Top among visible at ${state.physicalHorizon}: ${topVisible.hazard} (${formatPhysicalImpact(topVisible.point.raw)}${String(topVisible.point.source || "").startsWith("derived") ? ", derived" : ""}).`
    : `No quantified ${metricConfig.source} at ${state.physicalHorizon}.`;
  const derivedText = derivedHazards.length
    ? `Derived fallback used for: ${derivedHazards.join(", ")}.`
    : "No derived fallback was needed for the quantified hazard lines.";
  const missingText = unquantifiedHazards.length
    ? `Not quantified for this metric/scenario: ${unquantifiedHazards.join(", ")}.`
    : "All returned hazards are quantified for this metric/scenario.";
  const axisPair = dualAxisSeriesPair(visibleSeries);
  const axisText = axisPair
    ? `Dual Y-axis local scale: left is ${axisPair[0].name}; right is ${axisPair[1].name}; small horizon-to-horizon movement is intentionally visible.`
    : visibleSeries.length === 1
      ? `${visibleSeries[0].name} is shown alone on a rescaled Y-axis.`
      : "";
  const visibleText = selectedNames.length
    ? `Showing ${visibleSeries.map((item) => item.name).join(", ")} (${visibleSeries.length} of ${series.length} quantified hazards).`
    : `Showing all ${series.length} quantified hazards.`;
  el("hazardTrendNote").textContent = `${visibleText} ${quantifiedText}. ${topText} ${derivedText} ${missingText} ${axisText}`.trim();
}

function deltaDiagnostic(baseline, selected, baselineShare, isOverall) {
  if (!finiteMetricValue(baseline) || !finiteMetricValue(selected)) {
    return "not-quantified";
  }
  if (Number(baseline) === 0) {
    return "invalid-baseline";
  }
  const baselineNumber = Number(baseline);
  const selectedNumber = Number(selected);
  const magnitudeChange = Math.abs(selectedNumber) - Math.abs(baselineNumber);
  const flatTolerance = Math.max(
    Math.abs(baselineNumber),
    Math.abs(selectedNumber),
    1e-12,
  ) * 1e-9;
  if (Math.abs(magnitudeChange) <= flatTolerance) {
    return "flat";
  }
  if (
    !isOverall &&
    finiteMetricValue(baselineShare) &&
    Math.abs(Number(baselineShare)) < DELTA_DENOMINATOR_SHARE_THRESHOLD
  ) {
    return "denominator-sensitive";
  }
  const factor = selectedNumber / baselineNumber;
  if (!Number.isFinite(factor)) {
    return "invalid-baseline";
  }
  if (Math.abs(factor) >= DELTA_LARGE_RATIO_THRESHOLD) {
    return "large-ratio";
  }
  return "usable";
}

function deltaSourceLabel(baselineResult, selectedResult, metricConfig, isOverall) {
  if (isOverall) {
    return metricConfig.source;
  }
  const sources = unique([baselineResult?.source, selectedResult?.source]);
  return sources.join(" / ") || hazardTrendMetricConfig().source;
}

function deltaRecord({
  name,
  baselineResult,
  selectedResult,
  overallBaseline,
  metricConfig,
  isOverall = false,
}) {
  const baseline = baselineResult?.value;
  const selected = selectedResult?.value;
  const validPair = finiteMetricValue(baseline) && finiteMetricValue(selected);
  const validBaseline = finiteMetricValue(baseline) && Number(baseline) !== 0;
  const factor = validPair && validBaseline ? Number(selected) / Number(baseline) : null;
  const percentChange = finiteMetricValue(factor) ? (Number(factor) - 1) * 100 : null;
  const magnitudeChange = validPair
    ? Math.abs(Number(selected)) - Math.abs(Number(baseline))
    : null;
  const baselineShare = isOverall
    ? finiteMetricValue(baseline) && Number(baseline) !== 0
      ? 1
      : null
    : finiteMetricValue(baseline) &&
        finiteMetricValue(overallBaseline) &&
        Number(overallBaseline) !== 0
      ? Math.abs(Number(baseline)) / Math.abs(Number(overallBaseline))
      : null;
  const diagnosticKey = deltaDiagnostic(
    baseline,
    selected,
    baselineShare,
    isOverall,
  );
  return {
    name,
    baseline,
    selected,
    factor,
    percentChange,
    magnitudeChange,
    baselineShare,
    diagnosticKey,
    diagnostic: DELTA_DIAGNOSTICS[diagnosticKey],
    source: deltaSourceLabel(
      baselineResult,
      selectedResult,
      metricConfig,
      isOverall,
    ),
    derived: Boolean(baselineResult?.derived || selectedResult?.derived),
    isOverall,
  };
}

function deltaTestData(physical) {
  const metricConfig = physicalMetricConfig();
  const trendRows = physical.trends.filter(
    (row) => row.scenario === state.physicalScenario,
  );
  const horizons = sortNumeric(unique(trendRows.map((row) => row.horizon)));
  const baselineHorizon = horizons[0] ?? null;
  const baselineTrend = trendRows.find(
    (row) => Number(row.horizon) === Number(baselineHorizon),
  );
  const selectedTrend = trendRows.find(
    (row) => Number(row.horizon) === Number(state.physicalHorizon),
  );
  const overallBaselineResult = {
    value: finiteMetricValue(baselineTrend?.[metricConfig.field])
      ? Number(baselineTrend[metricConfig.field])
      : null,
    source: metricConfig.source,
    derived: false,
  };
  const overallSelectedResult = {
    value: finiteMetricValue(selectedTrend?.[metricConfig.field])
      ? Number(selectedTrend[metricConfig.field])
      : null,
    source: metricConfig.source,
    derived: false,
  };
  const overall = deltaRecord({
    name: "Overall asset",
    baselineResult: overallBaselineResult,
    selectedResult: overallSelectedResult,
    overallBaseline: overallBaselineResult.value,
    metricConfig,
    isOverall: true,
  });
  const hazardRows = physical.hazards.filter(
    (row) => row.scenario === state.physicalScenario,
  );
  const hazards = unique(hazardRows.map((row) => row.hazard))
    .map((hazard) => {
      const baselineRow = hazardRows.find(
        (row) =>
          row.hazard === hazard &&
          Number(row.horizon) === Number(baselineHorizon),
      );
      const selectedRow = hazardRows.find(
        (row) =>
          row.hazard === hazard &&
          Number(row.horizon) === Number(state.physicalHorizon),
      );
      return deltaRecord({
        name: hazard,
        baselineResult: hazardMetricResult(baselineRow),
        selectedResult: hazardMetricResult(selectedRow),
        overallBaseline: overallBaselineResult.value,
        metricConfig,
      });
    })
    .sort((a, b) => {
      const aQuantified = finiteMetricValue(a.baseline) && finiteMetricValue(a.selected);
      const bQuantified = finiteMetricValue(b.baseline) && finiteMetricValue(b.selected);
      if (aQuantified !== bQuantified) return aQuantified ? -1 : 1;
      const shareDiff =
        Math.abs(Number(b.baselineShare || 0)) -
        Math.abs(Number(a.baselineShare || 0));
      if (shareDiff !== 0) return shareDiff;
      return String(a.name).localeCompare(String(b.name));
    });
  return { baselineHorizon, metricConfig, rows: [overall, ...hazards] };
}

function formatDeltaFactor(value) {
  if (!finiteMetricValue(value)) return "n/a";
  return `${Number(value).toLocaleString(undefined, {
    maximumSignificantDigits: 5,
  })}x`;
}

function formatDeltaPercent(value) {
  if (!finiteMetricValue(value)) return "n/a";
  const number = Number(value);
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toLocaleString(undefined, {
    maximumFractionDigits: Math.abs(number) >= 1000 ? 1 : 2,
  })}%`;
}

function formatBaselineShare(value) {
  if (!finiteMetricValue(value)) return "n/a";
  return `${(Number(value) * 100).toLocaleString(undefined, {
    maximumFractionDigits: 4,
  })}%`;
}

function crossAssetDeltaRows() {
  return state.data.assets
    .map((asset) => {
      const test = deltaTestData(physicalRows(asset.asset_name));
      return {
        asset,
        baselineHorizon: test.baselineHorizon,
        delta: test.rows[0],
      };
    })
    .sort((a, b) => {
      const aQuantified = finiteMetricValue(a.delta.factor);
      const bQuantified = finiteMetricValue(b.delta.factor);
      if (aQuantified !== bQuantified) return aQuantified ? -1 : 1;
      const factorDiff =
        Math.abs(Number(b.delta.factor || 0)) -
        Math.abs(Number(a.delta.factor || 0));
      if (factorDiff !== 0) return factorDiff;
      return assetPrimaryLabel(a.asset).localeCompare(assetPrimaryLabel(b.asset));
    });
}

function renderCrossAssetDelta() {
  const rows = crossAssetDeltaRows();
  if (!rows.length) {
    el("deltaAssetTable").innerHTML =
      '<div class="empty-state compact-empty">No assets are available for comparison.</div>';
    return;
  }
  el("deltaAssetTable").innerHTML = `
    <table class="delta-asset-table">
      <thead>
        <tr>
          <th>Asset</th>
          <th class="numeric-cell">Baseline (earliest)</th>
          <th class="numeric-cell">Selected ${escapeHtml(state.physicalHorizon)}</th>
          <th class="numeric-cell">Raw factor</th>
          <th>Diagnostic</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            ({ asset, baselineHorizon, delta }) => `
              <tr class="${asset.asset_name === state.assetName ? "delta-current-asset" : ""}">
                <td>
                  <strong>${escapeHtml(assetPrimaryLabel(asset))}</strong>
                  <span class="cell-note">${escapeHtml(assetContextLabel(asset, true) || asset.asset_name)}</span>
                </td>
                <td class="numeric-cell">
                  ${escapeHtml(formatPhysicalImpact(delta.baseline))}
                  <span class="cell-note">${escapeHtml(baselineHorizon ?? "no baseline")}</span>
                </td>
                <td class="numeric-cell">${escapeHtml(formatPhysicalImpact(delta.selected))}</td>
                <td class="numeric-cell">${escapeHtml(formatDeltaFactor(delta.factor))}</td>
                <td>
                  <span class="diagnostic-badge diagnostic-${escapeHtml(delta.diagnosticKey)}">${escapeHtml(delta.diagnostic.label)}</span>
                  <span class="cell-note">${escapeHtml(delta.diagnostic.detail)}</span>
                </td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderDeltaTest(asset, physical) {
  const { baselineHorizon, metricConfig, rows } = deltaTestData(physical);
  el("deltaTestTitle").textContent = `${metricConfig.label}: Baseline-to-Horizon Test`;
  el("deltaTestKicker").textContent = `${asset.scr_asset_id || asset.asset_name} | ${state.physicalScenario} | ${baselineHorizon ?? "n/a"} to ${state.physicalHorizon}`;
  renderCrossAssetDelta();

  if (baselineHorizon === null) {
    el("deltaTestTable").innerHTML =
      '<div class="empty-state">No physical horizons are available for this scenario.</div>';
    el("deltaTestNote").textContent = "";
    return;
  }

  el("deltaTestTable").innerHTML = `
    <table class="delta-table">
      <thead>
        <tr>
          <th>Scope</th>
          <th>Metric source</th>
          <th class="numeric-cell">Baseline ${escapeHtml(baselineHorizon)}</th>
          <th class="numeric-cell">Selected ${escapeHtml(state.physicalHorizon)}</th>
          <th class="numeric-cell">Raw factor</th>
          <th class="numeric-cell">% change</th>
          <th class="numeric-cell">Loss-magnitude change</th>
          <th class="numeric-cell">Baseline share</th>
          <th>Diagnostic</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
              <tr class="${row.isOverall ? "delta-overall-row" : ""}">
                <td><strong>${escapeHtml(row.name)}</strong></td>
                <td class="delta-source-cell">
                  <span class="delta-source-kind ${row.derived ? "is-derived" : ""}">${row.derived ? "Derived" : "Returned"}</span>
                  <span class="cell-note">${escapeHtml(row.source)}</span>
                </td>
                <td class="numeric-cell">${escapeHtml(formatPhysicalImpact(row.baseline))}</td>
                <td class="numeric-cell">${escapeHtml(formatPhysicalImpact(row.selected))}</td>
                <td class="numeric-cell">${escapeHtml(formatDeltaFactor(row.factor))}</td>
                <td class="numeric-cell">${escapeHtml(formatDeltaPercent(row.percentChange))}</td>
                <td class="numeric-cell">${escapeHtml(formatPhysicalImpact(row.magnitudeChange))}</td>
                <td class="numeric-cell">${escapeHtml(formatBaselineShare(row.baselineShare))}</td>
                <td>
                  <span class="diagnostic-badge diagnostic-${escapeHtml(row.diagnosticKey)}">${escapeHtml(row.diagnostic.label)}</span>
                  <span class="cell-note">${escapeHtml(row.diagnostic.detail)}</span>
                </td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
  el("deltaTestNote").textContent =
    `Screening only: factor = selected / baseline; loss-magnitude change = |selected| - |baseline|; baseline share uses absolute magnitudes. ` +
    "Current SCR physical-loss exports can use negative signed values; raw values stay visible, and the factor is also the magnitude ratio while both signs match. " +
    `Below ${(DELTA_DENOMINATOR_SHARE_THRESHOLD * 100).toFixed(0)}% share is denominator-sensitive; absolute factor at or above ${DELTA_LARGE_RATIO_THRESHOLD}x is a large ratio. ` +
    "No ceiling, cap, or logarithmic compression is applied.";
}

function renderHazardRanking(physical) {
  const hazards = selectedHazards(physical);
  if (!hazards.length) {
    el("hazardRanking").innerHTML = `<div class="empty-state">No hazard rows for this selection.</div>`;
    return;
  }
  const maxValue = Math.max(
    ...hazards.map((row) => Math.abs(Number(row.metricResult.value || 0))),
    0,
  );
  el("hazardRanking").innerHTML = hazards
    .map((row, index) => {
      const rawImpact = row.metricResult.value;
      const numericImpact = Math.abs(Number(rawImpact || 0));
      const hasImpact = finiteMetricValue(rawImpact);
      const width = maxValue > 0 ? (numericImpact / maxValue) * 100 : 0;
      const indicatorCount = row.worst_indicators?.length || 0;
      const staticImpact = hasStaticHazardImpact(physical, row.hazard);
      return `
        <details class="hazard-card" ${index === 0 ? "open" : ""}>
          <summary class="hazard-summary">
            <div class="bar-label">
              <span class="bar-title">${escapeHtml(row.hazard)}</span>
              <span class="bar-subtitle">${ratingBadge(row.hazard_rating)} ${severityMeter(row.hazard_rating)} ${escapeHtml(ratingMeaning(row.hazard_rating))}</span>
            </div>
            <div class="bar-track"><div class="bar-fill ${hasImpact ? "" : "is-empty"}" style="width:${width}%; background:${COLORS[0]}"></div></div>
            <div class="bar-value">
              <span>${escapeHtml(formatPhysicalImpact(rawImpact))}</span>
              ${row.metricResult.derived ? '<span class="impact-note">derived combined value</span>' : ""}
              ${staticImpact ? '<span class="impact-note">static in SCR return</span>' : ""}
            </div>
            <span class="details-pill" aria-hidden="true"></span>
          </summary>
          <div class="hazard-detail">
            <div class="hazard-detail-header">
              <span>Worst returned indicators</span>
              <span>${escapeHtml(indicatorCount)} shown</span>
            </div>
            ${renderWorstIndicatorChips(row.worst_indicators || [])}
            <div class="hazard-detail-header hazard-curve-title">
              <span>Returned hazard curves</span>
              <span>${escapeHtml(state.physicalScenario)} | current ${escapeHtml(state.physicalHorizon)}</span>
            </div>
            ${renderHazardMetricCurves(physical, row.hazard)}
            <div class="hazard-detail-header hazard-curve-title">
              <span>Magnitude response</span>
              <span>x: indicator magnitude | y: returned metric</span>
            </div>
            ${renderMagnitudeResponseCurves(physical, row.hazard)}
          </div>
        </details>
      `;
    })
    .join("");
  bindChartPointInteractions(el("hazardRanking"));
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

function chartPointMarkup({ x, y, radius, color, label }) {
  const safeLabel = escapeHtml(label);
  return `
    <g
      class="chart-point-group"
      tabindex="0"
      focusable="true"
      role="img"
      aria-label="${safeLabel}"
      data-chart-tooltip="${safeLabel}"
    >
      <circle class="chart-point-hit" cx="${x}" cy="${y}" r="${Math.max(radius + 6, 9)}"></circle>
      <circle class="chart-point-dot" cx="${x}" cy="${y}" r="${radius}" fill="${color}"></circle>
    </g>
  `;
}

function bindChartPointInteractions(container) {
  const points = [...container.querySelectorAll(".chart-point-group")];
  if (!points.length) return;

  container.classList.add("has-chart-tooltips");
  const tooltip = document.createElement("div");
  tooltip.className = "chart-tooltip";
  tooltip.setAttribute("role", "status");
  tooltip.setAttribute("aria-live", "polite");
  tooltip.hidden = true;
  container.append(tooltip);
  let activePoint = null;

  const show = (point) => {
    activePoint = point;
    tooltip.textContent = point.dataset.chartTooltip || point.getAttribute("aria-label") || "";
    tooltip.hidden = false;

    const containerRect = container.getBoundingClientRect();
    const pointRect = point.querySelector(".chart-point-dot").getBoundingClientRect();
    const pointX = pointRect.left + pointRect.width / 2 - containerRect.left;
    const pointY = pointRect.top - containerRect.top;
    const halfWidth = tooltip.offsetWidth / 2;
    const left = Math.min(
      Math.max(pointX, halfWidth + 8),
      Math.max(halfWidth + 8, containerRect.width - halfWidth - 8),
    );
    const top = Math.max(pointY - 10, tooltip.offsetHeight + 8);
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  };

  const hide = (point) => {
    if (activePoint !== point) return;
    activePoint = null;
    tooltip.hidden = true;
  };

  const hideIfInactive = (point) => {
    if (point.matches(":hover") || document.activeElement === point) return;
    hide(point);
  };

  points.forEach((point) => {
    point.addEventListener("pointerenter", () => show(point));
    point.addEventListener("pointerleave", () => hideIfInactive(point));
    point.addEventListener("mouseenter", () => show(point));
    point.addEventListener("mouseleave", () => hideIfInactive(point));
    point.addEventListener("focus", () => show(point));
    point.addEventListener("blur", () => hideIfInactive(point));
    point.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      hide(point);
      point.blur();
    });
  });
}

function renderLineChart(containerId, series, options) {
  const container = el(containerId);
  const xValues = sortNumeric(unique(series.flatMap((item) => item.points.map((point) => point.x))));
  const yValues = series
    .flatMap((item) => item.points.map((point) => point.y))
    .filter(validChartValue);

  if (!xValues.length || !yValues.length) {
    container.innerHTML = `<div class="empty-state">No trend data available.</div>`;
    return;
  }

  const dualPair = options.dualAxis ? dualAxisSeriesPair(series) : null;
  const useDualAxis = Boolean(dualPair);
  const width = 760;
  const height = 260;
  const margin = useDualAxis
    ? { top: 24, right: 86, bottom: 40, left: 76 }
    : { top: 18, right: 22, bottom: 40, left: 76 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const yMinRaw = Math.min(...yValues);
  const yMaxRaw = Math.max(...yValues);
  const yMin = options.baselineZero ? 0 : yMinRaw - Math.abs(yMinRaw) * 0.04;
  const yMax = yMaxRaw + Math.abs(yMaxRaw || 1) * 0.08;
  const yRange = yMax - yMin || 1;
  const singleAxis = { domain: { min: yMin, max: yMax, range: yRange } };
  const leftAxis = useDualAxis
    ? { item: dualPair[0], domain: chartAxisDomain(chartSeriesValues(dualPair[0]), options.dualAxisBaselineZero === true) }
    : singleAxis;
  const rightAxis = useDualAxis
    ? { item: dualPair[1], domain: chartAxisDomain(chartSeriesValues(dualPair[1]), options.dualAxisBaselineZero === true) }
    : null;
  const tickRatios = [0, 0.25, 0.5, 0.75, 1];
  const formatAxisValue = options.valueFormatter || formatCompact;

  const xFor = (value) => {
    const index = xValues.indexOf(value);
    if (xValues.length === 1) return margin.left + innerWidth / 2;
    return margin.left + (index / (xValues.length - 1)) * innerWidth;
  };
  const yForDomain = (value, domain) =>
    margin.top + innerHeight - ((Number(value) - domain.min) / domain.range) * innerHeight;
  const axisForSeries = (item) => {
    if (!useDualAxis) return singleAxis;
    return item === rightAxis.item ? rightAxis : leftAxis;
  };
  const yForPoint = (item, value) => yForDomain(value, axisForSeries(item).domain);

  const grid = tickRatios
    .map((ratio) => {
      const leftTick = leftAxis.domain.min + leftAxis.domain.range * ratio;
      const y = yForDomain(leftTick, leftAxis.domain);
      const rightTick = rightAxis ? rightAxis.domain.min + rightAxis.domain.range * ratio : null;
      const rightTickLabel = rightAxis
        ? `<text class="tick-label" style="fill:${rightAxis.item.color}" x="${width - margin.right + 10}" y="${y + 4}" text-anchor="start">${escapeHtml(formatChartAxisValue(rightTick, formatAxisValue, rightAxis.domain))}</text>`
        : "";
      return `
        <line class="grid-line" x1="${margin.left}" x2="${width - margin.right}" y1="${y}" y2="${y}"></line>
        <text class="tick-label" ${useDualAxis ? `style="fill:${leftAxis.item.color}"` : ""} x="${margin.left - 10}" y="${y + 4}" text-anchor="end">${escapeHtml(formatChartAxisValue(leftTick, formatAxisValue, leftAxis.domain))}</text>
        ${rightTickLabel}
      `;
    })
    .join("");
  const axisLabels = useDualAxis
    ? `
      <text class="tick-label" style="fill:${leftAxis.item.color}" x="${margin.left}" y="14" text-anchor="start">${escapeHtml(leftAxis.item.name)}</text>
      <text class="tick-label" style="fill:${rightAxis.item.color}" x="${width - margin.right}" y="14" text-anchor="end">${escapeHtml(rightAxis.item.name)}</text>
    `
    : "";

  const xLabels = xValues
    .map((value, index) => {
      if (xValues.length > 10 && index % 3 !== 0 && index !== xValues.length - 1) return "";
      const x = xFor(value);
      return `<text class="tick-label" x="${x}" y="${height - 12}" text-anchor="middle">${escapeHtml(value)}</text>`;
    })
    .join("");

  const lines = series
    .map((item) => {
      const points = item.points.filter((point) => validChartValue(point.y));
      const path = points
        .map((point, index) => `${index === 0 ? "M" : "L"} ${xFor(point.x)} ${yForPoint(item, point.y)}`)
        .join(" ");
      const hasSelectedSeries = options.highlightSelected !== false && series.some((candidate) => candidate.selected);
      const isHighlighted = !hasSelectedSeries || item.selected;
      const circles = points
        .map((point) => {
          const detail = options.tooltipFormatter
            ? options.tooltipFormatter(point)
            : `${formatNumber(point.y)} | rating ${point.rating || "-"}`;
          return chartPointMarkup({
            x: xFor(point.x),
            y: yForPoint(item, point.y),
            radius: item.selected && hasSelectedSeries ? 3.5 : 2.5,
            color: item.color,
            label: `${item.name} · horizon ${point.x}: ${detail}`,
          });
        })
        .join("");
      return `
        <path d="${path}" fill="none" stroke="${item.color}" stroke-width="${item.selected && hasSelectedSeries ? 3 : 2}" opacity="${isHighlighted ? 1 : 0.45}"></path>
        <g opacity="${isHighlighted ? 1 : 0.7}">${circles}</g>
      `;
    })
    .join("");

  const legend = series
    .map(
      (item) => {
        const axisSuffix = useDualAxis ? (item === leftAxis.item ? " (left Y)" : " (right Y)") : "";
        return `<span class="legend-item"><span class="legend-swatch" style="background:${item.color}"></span>${escapeHtml(item.name)}${escapeHtml(axisSuffix)}</span>`;
      },
    )
    .join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(options.yLabel)} trend">
      ${grid}
      ${axisLabels}
      <line class="axis-line" x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}"></line>
      <line class="axis-line" x1="${margin.left}" x2="${margin.left}" y1="${margin.top}" y2="${height - margin.bottom}"></line>
      ${useDualAxis ? `<line class="axis-line" x1="${width - margin.right}" x2="${width - margin.right}" y1="${margin.top}" y2="${height - margin.bottom}"></line>` : ""}
      ${xLabels}
      ${lines}
    </svg>
    <div class="legend">${legend}</div>
    <p class="chart-interaction-hint">Hover a point to inspect its value. Keyboard users can tab to each point.</p>
  `;
  bindChartPointInteractions(container);
}

function renderInterpretation(asset, physical, transition) {
  const metricConfig = physicalMetricConfig();
  const trend = selectedPhysicalTrend(physical);
  const hazards = selectedHazards(physical);
  const topHazard = hazards[0];
  const firstYearTrend = physical.trends
    .filter((row) => row.scenario === state.physicalScenario)
    .sort((a, b) => Number(a.horizon) - Number(b.horizon))[0];
  const change =
    firstYearTrend && trend?.[metricConfig.field] && firstYearTrend?.[metricConfig.field]
      ? ((trend[metricConfig.field] / firstYearTrend[metricConfig.field] - 1) * 100).toFixed(1)
      : null;
  const transitionRankings = transitionRankingsForDriver(transition);
  const selectedTransition = selectedTransitionRanking(transition);
  const topTransition = transitionRankings[0];
  const selectedPhysicalValue = trend?.[metricConfig.field];

  el("interpretationBody").innerHTML = `
    <p><strong>Asset context:</strong> ${escapeHtml(asset.scr_asset_id || asset.asset_name)} is modeled as ${escapeHtml(asset.ticcs_sub_class_name || "an infrastructure asset")} at ${escapeHtml(asset.coordinates || "unknown coordinates")}.</p>
    <p><strong>Physical:</strong> ${escapeHtml(state.physicalScenario)} at ${escapeHtml(state.physicalHorizon)} returns overall rating ${escapeHtml(trend?.adjusted_physical_exposure_rating || "-")} and ${escapeHtml(metricConfig.label)} ${escapeHtml(formatPhysicalImpact(selectedPhysicalValue, { includeRaw: true }))}${change ? `, a ${escapeHtml(change)}% move from the first returned ${escapeHtml(metricConfig.shortLabel)} horizon` : ""}. ${topHazard ? `The top quantified hazard is ${escapeHtml(topHazard.hazard)}.` : ""}</p>
    <p><strong>Transition:</strong> with the ${escapeHtml(driverLabel(state.transitionDriver))} filter, the highest peak scenario is ${escapeHtml(topTransition?.scenario || "-")} with ${escapeHtml(formatNumber(topTransition?.peak_impact))}. The selected scenario, ${escapeHtml(selectedTransition?.scenario || "-")}, is led by ${escapeHtml(driverLabel(selectedTransition?.peak_subrisk))} at ${escapeHtml(selectedTransition?.peak_year || "-")}.</p>
    <p><strong>Caveat:</strong> physical impact can be toggled between raw, percent-style, and basis-point display. Percent-style and basis-point displays are readability conversions from the raw SCR value, not confirmed vendor unit labels. Current physical plot field: ${escapeHtml(metricConfig.description)}</p>
  `;
}

function render() {
  const asset = currentAsset();
  const physical = physicalRows(asset.asset_name);
  const transition = transitionRows(asset.asset_name);

  el("physicalTab").classList.toggle("is-active", state.activeView === "physical");
  el("transitionTab").classList.toggle("is-active", state.activeView === "transition");
  el("physicalDamageMetric").classList.toggle("is-active", state.physicalMetric === "damage");
  el("physicalValueMetric").classList.toggle("is-active", state.physicalMetric === "value_impact");
  el("physicalDisruptionMetric").classList.toggle("is-active", state.physicalMetric === "disruption");
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
    let loaded = null;
    let lastError = null;
    for (const url of DATA_URLS) {
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`${url}: HTTP ${response.status}`);
        }
        loaded = { data: await response.json(), url };
        break;
      } catch (error) {
        lastError = error;
      }
    }
    if (!loaded) throw lastError || new Error("No dashboard data source could be loaded.");
    state.data = loaded.data;
    initialiseState();
    bindControls();
    el("dataStatus").textContent = `${state.data.assets.length} assets | ${state.data.meta.physical_rows} physical rows | ${state.data.meta.transition_rows} transition rows`;
    el("dataStatus").title = `Loaded ${loaded.url}`;
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
