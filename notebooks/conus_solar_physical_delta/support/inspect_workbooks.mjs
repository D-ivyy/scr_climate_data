import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const [inputDir, outputPath] = process.argv.slice(2);
if (!inputDir || !outputPath) {
  throw new Error("Usage: node inspect_workbooks.mjs INPUT_DIR OUTPUT_JSON");
}

const moduleRoot = process.env.SCR_NODE_MODULES;
if (!moduleRoot) {
  throw new Error("Set SCR_NODE_MODULES to the directory containing @oai/artifact-tool.");
}
const resolver = createRequire(import.meta.url);
const artifactEntry = resolver.resolve("@oai/artifact-tool", { paths: [moduleRoot] });
const { FileBlob, SpreadsheetFile } = await import(pathToFileURL(artifactEntry).href);

const hazardMetricFields = [
  "adjustedHazardDamage",
  "adjustedHazardDisruption",
  "adjustedHazardDisruptionDamageEquivalent",
  "adjustedHazardValueImpact",
  "adjustedHazardExposureRating",
];
const totalMetricFields = [
  "adjustedTotalDamage",
  "adjustedTotalDisruption",
  "adjustedTotalDisruptionDamageEquivalent",
  "adjustedTotalValueImpact",
  "adjustedPhysicalExposureRating",
];
const rawAdjustedPairs = [
  ["hazardDamage", "adjustedHazardDamage"],
  ["hazardDisruption", "adjustedHazardDisruption"],
  ["hazardDisruptionDamageEquivalent", "adjustedHazardDisruptionDamageEquivalent"],
  ["hazardValueImpact", "adjustedHazardValueImpact"],
  ["totalDamage", "adjustedTotalDamage"],
  ["totalDisruption", "adjustedTotalDisruption"],
  ["totalDisruptionDamageEquivalent", "adjustedTotalDisruptionDamageEquivalent"],
  ["totalValueImpact", "adjustedTotalValueImpact"],
];
const present = (value) => value !== null && value !== "" && value !== undefined;

function distinctMetrics(rows, fields) {
  const result = {};
  for (const field of fields) {
    const values = [...new Set(rows.map((row) => row[field]).filter(present))];
    if (values.length > 1) {
      throw new Error(`Repeated ${field} values disagree within one asset/scenario/horizon/hazard group.`);
    }
    result[field] = values.length === 1 ? values[0] : null;
  }
  return result;
}

const filenames = (await fs.readdir(inputDir)).filter((name) => name.endsWith(".xlsx")).sort();
const files = [];
for (const filename of filenames) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(inputDir, filename)));
  const output = workbook.worksheets.getItem("Output");
  const values = output.getUsedRange().values;
  const headers = values[0];
  const rows = values.slice(1).map((row) =>
    Object.fromEntries(headers.map((header, index) => [header, row[index]])),
  );
  const grouped = {};
  for (const scenario of [...new Set(rows.map((row) => row.scenario))]) {
    grouped[scenario] = {};
    for (const horizon of [...new Set(rows.map((row) => String(row.timeHorizon)))]) {
      const horizonRows = rows.filter(
        (row) => row.scenario === scenario && String(row.timeHorizon) === horizon,
      );
      grouped[scenario][horizon] = {
        total: distinctMetrics(horizonRows, totalMetricFields),
        hazards: Object.fromEntries(
          [...new Set(horizonRows.map((row) => row.hazard))].map((hazard) => [
            hazard,
            distinctMetrics(
              horizonRows.filter((row) => row.hazard === hazard),
              hazardMetricFields,
            ),
          ]),
        ),
      };
    }
  }
  const rawAdjusted = {};
  for (const [raw, adjusted] of rawAdjustedPairs) {
    const pairs = rows.filter((row) => present(row[raw]) && present(row[adjusted]));
    rawAdjusted[`${raw}|${adjusted}`] = {
      pairs: pairs.length,
      equal: pairs.filter((row) => row[raw] === row[adjusted]).length,
      different: pairs.filter((row) => row[raw] !== row[adjusted]).length,
    };
  }
  files.push({
    filename,
    cellId: Number(filename.match(/Cell_(\d+)_/)?.[1]),
    outputRange: output.getUsedRange().address,
    rowCount: rows.length,
    columnCount: headers.length,
    headers,
    coordinates: [...new Set(rows.map((row) => row.geolocationCoordinates))],
    assetIds: [...new Set(rows.map((row) => row.assetId))],
    assetNames: [...new Set(rows.map((row) => row.assetName))],
    ticcsSubClass: [...new Set(rows.map((row) => row.ticcsSubClass))],
    ticcsSubClassName: [...new Set(rows.map((row) => row.ticcsSubClassName))],
    scenarios: [...new Set(rows.map((row) => row.scenario))],
    horizons: [...new Set(rows.map((row) => String(row.timeHorizon)))],
    hazards: [...new Set(rows.map((row) => row.hazard))],
    indicators: [...new Set(rows.map((row) => row.indicator))],
    rawAdjusted,
    grouped,
  });
}

await fs.writeFile(outputPath, JSON.stringify({ files }, null, 2));
console.log(JSON.stringify({ files: files.length, outputPath }, null, 2));
