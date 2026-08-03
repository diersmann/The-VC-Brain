import { gzipSync } from "node:zlib";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const dist = resolve(dirname(fileURLToPath(import.meta.url)), "../dist/assets");
if (!existsSync(dist)) {
  console.error("Bundle budget check requires a production build in frontend/dist.");
  process.exit(1);
}

const assets = readdirSync(dist)
  .filter((name) => /\.(js|css)$/.test(name))
  .map((name) => ({ name, bytes: readFileSync(join(dist, name)) }))
  .filter(({ bytes }) => statSize(bytes) > 0);
const javascript = assets.filter(({ name }) => name.endsWith(".js"));
const stylesheets = assets.filter(({ name }) => name.endsWith(".css"));
const entry = javascript.find(({ name }) => name.startsWith("index-"));

const rawJavascript = totalBytes(javascript);
const gzipJavascript = totalGzipBytes(javascript);
const rawStylesheets = totalBytes(stylesheets);
const limits = {
  rawJavascript: 450_000,
  gzipJavascript: 150_000,
  entryRawJavascript: 250_000,
  entryGzipJavascript: 80_000,
  rawStylesheets: 100_000,
};

console.log(`Bundle budget: JS ${rawJavascript} raw / ${gzipJavascript} gzip; CSS ${rawStylesheets} raw`);
if (entry) console.log(`Entry budget: ${entry.name} ${entry.bytes.length} raw / ${gzipSync(entry.bytes).length} gzip`);

const failures = [
  [rawJavascript > limits.rawJavascript, `JavaScript exceeds ${limits.rawJavascript} raw bytes`],
  [gzipJavascript > limits.gzipJavascript, `JavaScript exceeds ${limits.gzipJavascript} gzip bytes`],
  [rawStylesheets > limits.rawStylesheets, `CSS exceeds ${limits.rawStylesheets} raw bytes`],
  [entry == null, "No index entry bundle found"],
  [entry != null && entry.bytes.length > limits.entryRawJavascript, `entry JavaScript exceeds ${limits.entryRawJavascript} raw bytes`],
  [entry != null && gzipSync(entry.bytes).length > limits.entryGzipJavascript, `entry JavaScript exceeds ${limits.entryGzipJavascript} gzip bytes`],
].filter(([failed]) => failed).map(([, message]) => message);

if (failures.length) {
  console.error(failures.map((message) => `- ${message}`).join("\n"));
  process.exit(1);
}

function totalBytes(files) {
  return files.reduce((total, file) => total + file.bytes.length, 0);
}

function totalGzipBytes(files) {
  return files.reduce((total, file) => total + gzipSync(file.bytes).length, 0);
}

function statSize(bytes) {
  return bytes.length;
}
