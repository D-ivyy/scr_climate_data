import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const [
  inputDir,
  outputPath,
  concurrencyArg = "12",
  shardIndexArg = "0",
  shardCountArg = "1",
] = process.argv.slice(2);
if (!inputDir || !outputPath) {
  throw new Error("Usage: node extract_overall_damage.mjs INPUT_DIR OUTPUT_JSON [CONCURRENCY]");
}

const concurrency = Math.max(1, Number(concurrencyArg));
const shardIndex = Number(shardIndexArg);
const shardCount = Math.max(1, Number(shardCountArg));
const moduleRoot = process.env.SCR_NODE_MODULES;
if (!moduleRoot) {
  throw new Error("Set SCR_NODE_MODULES to the directory containing @oai/artifact-tool.");
}
const resolver = createRequire(import.meta.url);
const artifactEntry = resolver.resolve("@oai/artifact-tool", { paths: [moduleRoot] });
const { FileBlob, SpreadsheetFile } = await import(pathToFileURL(artifactEntry).href);

const filenames = (await fs.readdir(inputDir))
  .filter((name) => name.endsWith(".xlsx"))
  .sort()
  .filter((_, index) => index % shardCount === shardIndex);
let previousFiles = [];
try {
  previousFiles = JSON.parse(await fs.readFile(outputPath, "utf8")).files ?? [];
} catch (error) {
  if (error?.code !== "ENOENT") throw error;
}
const resultByFilename = new Map(previousFiles.map((result) => [result.filename, result]));
const pendingFilenames = filenames.filter((filename) => !resultByFilename.has(filename));
let nextIndex = 0;
let completed = 0;
let lastSaved = 0;
let saveChain = Promise.resolve();

async function saveResults() {
  const results = filenames.map((filename) => resultByFilename.get(filename)).filter(Boolean);
  const temporaryPath = `${outputPath}.tmp`;
  await fs.writeFile(temporaryPath, JSON.stringify({ files: results }, null, 2));
  await fs.rename(temporaryPath, outputPath);
}

async function checkpoint() {
  if (completed - lastSaved < 50) return;
  lastSaved = completed;
  saveChain = saveChain.then(() => saveResults());
  await saveChain;
}

function columnName(index) {
  let value = index + 1;
  let name = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    value = Math.floor((value - 1) / 26);
  }
  return name;
}

function distinctValue(values) {
  const present = values.filter((value) => value !== null && value !== "" && value !== undefined);
  const distinct = [...new Set(present)];
  if (distinct.length > 1) {
    throw new Error(`Expected one repeated total-damage value; found ${distinct.length}.`);
  }
  return distinct.length === 1 ? distinct[0] : null;
}

async function extract(filename) {
  const cellId = Number(filename.match(/Cell_(\d+)_/)?.[1]);
  try {
    const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(inputDir, filename)));
    const output = workbook.worksheets.getItem("Output");
    const used = output.getUsedRange();
    const rowCount = Number(used.address.match(/\d+$/)?.[0]);
    const headers = output.getRange(`A1:AJ1`).values[0];
    const indexes = Object.fromEntries(
      ["scenario", "timeHorizon", "adjustedTotalDamage"].map((header) => {
        const index = headers.indexOf(header);
        if (index < 0) throw new Error(`Missing required column ${header}.`);
        return [header, index];
      }),
    );
    const columns = Object.fromEntries(
      Object.entries(indexes).map(([header, index]) => {
        const column = columnName(index);
        return [header, output.getRange(`${column}2:${column}${rowCount}`).values.map((row) => row[0])];
      }),
    );
    const grouped = {};
    for (let index = 0; index < columns.scenario.length; index += 1) {
      const scenario = columns.scenario[index];
      const horizon = String(columns.timeHorizon[index]);
      if (!grouped[scenario]) grouped[scenario] = {};
      if (!grouped[scenario][horizon]) grouped[scenario][horizon] = [];
      grouped[scenario][horizon].push(columns.adjustedTotalDamage[index]);
    }
    const totals = Object.fromEntries(
      Object.entries(grouped).map(([scenario, horizons]) => [
        scenario,
        Object.fromEntries(
          Object.entries(horizons).map(([horizon, values]) => [horizon, distinctValue(values)]),
        ),
      ]),
    );
    return { filename, cellId, status: "ok", rowCount: rowCount - 1, headers, totals };
  } catch (error) {
    return { filename, cellId, status: "error", error: String(error?.stack ?? error) };
  }
}

async function worker() {
  while (true) {
    const index = nextIndex;
    nextIndex += 1;
    if (index >= pendingFilenames.length) return;
    const filename = pendingFilenames[index];
    resultByFilename.set(filename, await extract(filename));
    completed += 1;
    await checkpoint();
    if (completed % 250 === 0 || completed === pendingFilenames.length) {
      process.stdout.write(
        `${resultByFilename.size}/${filenames.length} total (${completed}/${pendingFilenames.length} this run)\n`,
      );
    }
  }
}

await Promise.all(Array.from({ length: Math.min(concurrency, pendingFilenames.length) }, () => worker()));
saveChain = saveChain.then(() => saveResults());
await saveChain;
const results = filenames.map((filename) => resultByFilename.get(filename));
const errors = results.filter((result) => result.status !== "ok");
console.log(JSON.stringify({
  files: results.length,
  reused: previousFiles.length,
  processed: pendingFilenames.length,
  errors: errors.length,
  outputPath,
}, null, 2));
