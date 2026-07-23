import { createHash, randomBytes } from "node:crypto";
import { spawnSync } from "node:child_process";
import {
  chmodSync,
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  realpathSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";


const DEFAULT_REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const CLI_RELATIVE_ROOT = "_handbook/_cli";
const SCRATCH_RELATIVE_ROOT = "_handbook/_scratch";
const TOOL_VERSION = "4.1.0";
export const NODE_EXECUTION_RANGE = ">=22.23.1 <23 || >=24.18.0 <25";
const NODE_EXECUTION_FLOORS = new Map([
  [22, [23, 1]],
  [24, [18, 0]],
]);
const ACTION_SEGMENT_RE = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const ACTION_ID_RE = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\/[a-z][a-z0-9]*(?:-[a-z0-9]+)*)*$/;
const INPUT_NAME_RE = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const SHA256_RE = /^sha256:[0-9a-f]{64}$/;
const EXACT_VERSION_RE = /^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;
const PACKAGE_RE = /^(?:@[a-z0-9][a-z0-9._-]*\/[a-z0-9][a-z0-9._-]*|[a-z0-9][a-z0-9._-]*)$/;
const INPUT_TYPES = new Set([
  "boolean",
  "directory",
  "file",
  "integer",
  "number",
  "path",
  "string",
  "string-list",
]);
const PATH_INPUT_TYPES = new Set(["directory", "file", "path"]);
const OUTPUT_TYPES = new Set(["boolean", "file", "files", "json", "number", "text"]);
const TOP_LEVEL_KEYS = [
  "dependencies",
  "digests",
  "docs",
  "effects",
  "entrypoint",
  "execution",
  "format",
  "id",
  "inputs",
  "lifecycle",
  "methodConfidence",
  "outputs",
  "readiness",
  "success",
  "summary",
  "test",
  "title",
  "version",
];
const EFFECT_KEYS = ["creates", "reads", "temporary", "updates"];
const ACTION_FILES = new Set(["action.json", "run.mjs", "run.test.mjs"]);
const MANAGEMENT_COMMANDS = new Set([
  "apply",
  "doctor",
  "help",
  "list",
  "plan",
  "run",
  "scaffold",
  "show",
  "show-plan",
  "test",
  "validate",
  "version",
]);
const HARD_RESERVED = new Set([
  ".claude",
  ".codex",
  ".cursor",
  ".git",
  "agents.md",
  "claude.md",
  "gemini.md",
  "trellis",
]);
const HARD_RESERVED_SUBTREES = new Set([CLI_RELATIVE_ROOT, SCRATCH_RELATIVE_ROOT]);
const SOFT_PROTECTED = new Set(["_handbook", "handbook", "instructions"]);
const SAFE_ENV = [
  "CI",
  "ComSpec",
  "LANG",
  "LC_ALL",
  "NO_COLOR",
  "PATH",
  "PATHEXT",
  "SystemRoot",
  "TEMP",
  "TERM",
  "TMP",
  "TMPDIR",
  "TZ",
];
const BLOCKED_BUILTINS = new Set([
  "child_process", "cluster", "dgram", "dns", "http", "http2", "https",
  "inspector", "module", "net", "os", "quic", "repl", "sqlite", "tls", "vm", "wasi", "worker_threads",
]);
const BLOCKED_SOURCE = [
  [/\b(?:fetch|WebSocket|EventSource)\s*\(/, "network API"],
  [/\bprocess\s*\.\s*(?:_debugEnd|_debugProcess|_kill|_linkedBinding|binding|chdir|dlopen|execve|getBuiltinModule|initgroups|kill|loadEnvFile|openStdin|setegid|seteuid|setgid|setgroups|setuid|umask)\b/, "runtime bypass API"],
];
export class CliError extends Error {}


export function usage() {
  return [
    "Examples:",
    "  ./trellis quality links check-local-links -- --root docs",
    "  ./trellis normalize-csv-export -- --source export.csv --output clean.csv",
    "  ./trellis list",
    "",
    "Run ./trellis --help for commands, safety rules, and nested Action paths.",
  ].join("\n");
}


function fullUsage() {
  return [
    "Examples:",
    "  ./trellis quality links check-local-links -- --root docs",
    "  ./trellis normalize-csv-export -- --source export.csv --output clean.csv",
    "  ./trellis show quality links check-local-links",
    "  ./trellis list --json",
    "",
    "Use an Action:",
    "  ./trellis <path segments...> [--json] [development overrides] -- [named inputs]",
    "  Read-only Actions execute. File-changing Actions create a reviewable plan.",
    "",
    "Manage Actions:",
    "  ./trellis list [--json]",
    "  ./trellis show <path segments...> [--json]",
    "  ./trellis validate [<path segments...>] [--json]",
    "  ./trellis test <path segments...>",
    "  ./trellis plan <path segments...> [runner flags] -- [named inputs]",
    "  ./trellis show-plan <path segments...> --plan <sha256> [--json]",
    "  ./trellis apply <path segments...> --plan <sha256> [runner flags]",
    "  ./trellis scaffold <path segments...> --title <title> [--apply] [--json]",
    "  ./trellis doctor [--json]",
    "  ./trellis version",
    "",
    "Action paths use separate kebab-case segments; named inputs follow --.",
    "Actions are permanently local-only. They cannot request network, environment,",
    "child-process, deletion, or direct filesystem-write capabilities.",
  ].join("\n");
}


function commandUsage(command) {
  const lines = {
    apply: "./trellis apply <path segments...> --plan <sha256> [--json] [development overrides]",
    doctor: "./trellis doctor [--json]",
    help: "./trellis help [command | path segments...]",
    list: "./trellis list [--json]",
    plan: "./trellis plan <path segments...> [--json] [development overrides] -- [named inputs]",
    run: "The run command was removed. Invoke an Action directly: ./trellis <path segments...> -- [named inputs]",
    scaffold: "./trellis scaffold <path segments...> --title <title> [--apply] [--json]",
    show: "./trellis show <path segments...> [--json]",
    "show-plan": "./trellis show-plan <path segments...> --plan <sha256> [--json]",
    test: "./trellis test <path segments...>",
    validate: "./trellis validate [<path segments...>] [--json]",
    version: "./trellis version",
  };
  return lines[command] || fullUsage();
}


export function nodeSupport(version = process.versions.node) {
  const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(version);
  if (!match) return { discovery: false, execution: false };
  const [, majorText, minorText, patchText] = match;
  const [major, minor, patchVersion] = [majorText, minorText, patchText].map(Number);
  const floor = NODE_EXECUTION_FLOORS.get(major);
  return {
    discovery: major >= 18,
    execution: Boolean(
      floor && (minor > floor[0] || minor === floor[0] && patchVersion >= floor[1]),
    ),
  };
}


function assertExecutionNode() {
  if (!nodeSupport().execution) {
    throw new CliError(
      `Action execution requires Node ${NODE_EXECUTION_RANGE}; found ${process.versions.node}. Discovery commands remain available on Node >=18.`
    );
  }
}


function hashBytes(value) {
  return `sha256:${createHash("sha256").update(value).digest("hex")}`;
}


function hashFile(filename) {
  return hashBytes(readFileSync(filename));
}


function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}


function compareText(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}


function validateActionSegments(segments, label = "Action path") {
  if (!Array.isArray(segments) || segments.length === 0) throw new CliError(`${label} is required; run ./trellis list or ./trellis --help`);
  for (const segment of segments) {
    if (!ACTION_SEGMENT_RE.test(segment)) throw new CliError(`${label} segment is invalid: ${segment}; use separate kebab-case path segments`);
  }
  if (MANAGEMENT_COMMANDS.has(segments[0])) throw new CliError(`${label} uses reserved top-level management word: ${segments[0]}`);
  return segments;
}


function actionIdFromSegments(segments, label = "Action path") {
  return validateActionSegments(segments, label).join("/");
}


function actionSegmentsFromId(actionId, label = "action id") {
  if (typeof actionId !== "string" || !ACTION_ID_RE.test(actionId)) throw new CliError(`${label} is invalid: ${actionId}`);
  return validateActionSegments(actionId.split("/"), label);
}


function actionInvocation(actionId) {
  return actionSegmentsFromId(actionId).join(" ");
}


function splitActionPath(args, label, { optional = false } = {}) {
  const optionIndex = args.findIndex((arg) => arg.startsWith("-"));
  const end = optionIndex === -1 ? args.length : optionIndex;
  const segments = args.slice(0, end);
  if (segments.length === 0 && optional) return { id: null, segments: [], rest: args.slice(end) };
  const id = actionIdFromSegments(segments, `${label} Action path`);
  return { id, segments, rest: args.slice(end) };
}


function contextualHelpIndex(args) {
  const delimiter = args.indexOf("--");
  return args.findIndex((arg, index) => (arg === "-h" || arg === "--help") && (delimiter === -1 || index < delimiter));
}


function isWithin(candidate, parent) {
  const relative = path.relative(parent, candidate);
  return relative === "" || (relative !== ".." && !relative.startsWith(`..${path.sep}`));
}


function rejectSymlink(pathname, label) {
  if (lstatSync(pathname).isSymbolicLink()) {
    throw new CliError(`${label} must not be a symlink: ${pathname}`);
  }
}


function resolveExistingFile(pathname, parent, label) {
  if (!existsSync(pathname)) throw new CliError(`${label} is missing: ${pathname}`);
  rejectSymlink(pathname, label);
  const resolved = realpathSync(pathname);
  if (!isWithin(resolved, realpathSync(parent))) {
    throw new CliError(`${label} escapes its directory: ${pathname}`);
  }
  if (!lstatSync(resolved).isFile()) throw new CliError(`${label} must be a regular file: ${pathname}`);
  return resolved;
}


function assertNoSymlinkComponents(parent, candidate, label) {
  if (!isWithin(candidate, parent)) throw new CliError(`${label} escapes the work folder`);
  let current = parent;
  const relative = path.relative(parent, candidate);
  for (const segment of relative.split(path.sep).filter(Boolean)) {
    current = path.join(current, segment);
    if (!existsSync(current)) break;
    if (lstatSync(current).isSymbolicLink()) throw new CliError(`${label} contains a symlink component: ${path.relative(parent, current)}`);
  }
}


function ensurePrivateDirectory(repoRoot, directory, label) {
  repoRoot = realpathSync(path.resolve(repoRoot));
  directory = path.resolve(directory);
  if (!isWithin(directory, repoRoot)) throw new CliError(`${label} escapes the work folder`);
  assertNoSymlinkComponents(repoRoot, directory, label);
  if (existsSync(directory)) {
    rejectSymlink(directory, label);
    if (!lstatSync(directory).isDirectory()) throw new CliError(`${label} must be a directory`);
  } else {
    const parent = path.dirname(directory);
    if (!existsSync(parent)) throw new CliError(`${label} parent is missing: ${path.relative(repoRoot, parent)}`);
    rejectSymlink(parent, `${label} parent`);
    if (!lstatSync(parent).isDirectory() || !isWithin(realpathSync(parent), repoRoot)) {
      throw new CliError(`${label} parent must be a work-folder-local directory`);
    }
    mkdirSync(directory, { mode: 0o700 });
  }
  const resolved = realpathSync(directory);
  if (!isWithin(resolved, repoRoot)) throw new CliError(`${label} resolves outside the work folder`);
  chmodSync(resolved, 0o700);
  return resolved;
}


function requireScratchRoot(repoRoot) {
  repoRoot = realpathSync(path.resolve(repoRoot));
  const directory = scratchRoot(repoRoot);
  if (!existsSync(directory)) throw new CliError(`Trellis scratch directory is missing: ${SCRATCH_RELATIVE_ROOT}`);
  assertNoSymlinkComponents(repoRoot, directory, "Trellis scratch directory");
  rejectSymlink(directory, "Trellis scratch directory");
  if (!lstatSync(directory).isDirectory() || !isWithin(realpathSync(directory), repoRoot)) {
    throw new CliError("Trellis scratch directory must be a work-folder-local directory");
  }
  resolveExistingFile(path.join(directory, ".gitignore"), directory, "Trellis scratch ignore policy");
  resolveExistingFile(path.join(directory, "README.md"), directory, "Trellis scratch policy");
  chmodSync(directory, 0o700);
  return realpathSync(directory);
}


function exactKeys(value, allowed, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new CliError(`${label} must be an object`);
  }
  const extras = Object.keys(value).filter((key) => !allowed.includes(key));
  if (extras.length) throw new CliError(`${label} has unsupported fields: ${extras.join(", ")}`);
}


function nonemptyString(value, label) {
  if (typeof value !== "string" || !value.trim()) throw new CliError(`${label} must be a non-empty string`);
  return value;
}


function stringArray(value, label, { nonempty = false } = {}) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || !item.trim())) {
    throw new CliError(`${label} must be an array of non-empty strings`);
  }
  if (nonempty && value.length === 0) throw new CliError(`${label} must not be empty`);
  if (new Set(value).size !== value.length) throw new CliError(`${label} contains duplicates`);
  return value;
}


function relativePath(value, label) {
  nonemptyString(value, label);
  const normalized = value.replaceAll("\\", "/");
  if (
    normalized.startsWith("/") ||
    /^[A-Za-z]:\//.test(normalized) ||
    normalized.split("/").includes("..") ||
    /[$*?\[\]{}\u0000-\u001F\u007F]/.test(normalized)
  ) {
    throw new CliError(`${label} must be a literal work-folder-relative path: ${value}`);
  }
  for (const segment of normalized.split("/").filter(Boolean)) {
    if (segment === ".") continue;
    const base = segment.split(".", 1)[0].toUpperCase();
    if (/[<>:"|]/.test(segment) || /[ .]$/.test(segment) || /^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/.test(base)) {
      throw new CliError(`${label} contains a path segment that is not portable across supported platforms: ${segment}`);
    }
  }
  const directoryHint = normalized.endsWith("/");
  let result = path.posix.normalize(normalized);
  if (result === "") result = ".";
  if (directoryHint && result !== ".") result = `${result.replace(/\/+$/, "")}/`;
  return result;
}


function firstPathPart(value) {
  return value.replace(/\/$/, "").split("/")[0];
}


function normalizedRelative(value) {
  let normalized = value.replaceAll("\\", "/").replace(/^\.\/+/, "").replace(/\/+$/, "").toLowerCase();
  if (!normalized) normalized = ".";
  return normalized;
}


function isHardReservedPath(value) {
  const normalized = normalizedRelative(value);
  if (HARD_RESERVED.has(firstPathPart(normalized))) return true;
  return [...HARD_RESERVED_SUBTREES].some((reserved) => normalized === reserved || normalized.startsWith(`${reserved}/`));
}


function coversHardReservedSubtree(value) {
  const normalized = normalizedRelative(value);
  if (normalized === ".") return true;
  return [...HARD_RESERVED_SUBTREES].some((reserved) => reserved.startsWith(`${normalized}/`));
}


function cliRoot(repoRoot) {
  return path.join(repoRoot, "_handbook", "_cli");
}


function scratchRoot(repoRoot) {
  return path.join(repoRoot, "_handbook", "_scratch");
}


function assertScopePathSafe(value, effect, dynamic = false) {
  const first = firstPathPart(value).toLowerCase();
  if (isHardReservedPath(value) || coversHardReservedSubtree(value)) {
    throw new CliError(`effects.${effect} cannot include reserved path: ${value}`);
  }
  if (effect !== "reads" && SOFT_PROTECTED.has(first)) {
    const explicitSingleFile = !dynamic && value !== first && !value.endsWith("/");
    if (!explicitSingleFile) {
      throw new CliError(`effects.${effect} may write a protected handbook/instruction path only as an explicit file: ${value}`);
    }
  }
}


function validateTypedValue(value, input, label) {
  switch (input.type) {
    case "boolean":
      if (typeof value !== "boolean") throw new CliError(`${label} must be boolean`);
      return value;
    case "integer":
      if (!Number.isSafeInteger(value)) throw new CliError(`${label} must be a safe integer`);
      return value;
    case "number":
      if (typeof value !== "number" || !Number.isFinite(value)) throw new CliError(`${label} must be a finite number`);
      return value;
    case "string-list":
      return stringArray(value, label);
    default:
      nonemptyString(value, label);
      return PATH_INPUT_TYPES.has(input.type) ? relativePath(value, label) : value;
  }
}


function validateInputs(value) {
  if (!Array.isArray(value)) throw new CliError("inputs must be an array");
  const names = new Set();
  return value.map((input, index) => {
    const label = `inputs[${index}]`;
    exactKeys(input, ["default", "description", "examples", "name", "required", "type"], label);
    if (!INPUT_NAME_RE.test(input.name || "")) throw new CliError(`${label}.name is invalid`);
    if (names.has(input.name)) throw new CliError(`inputs contains duplicate name: ${input.name}`);
    names.add(input.name);
    if (!INPUT_TYPES.has(input.type)) throw new CliError(`${label}.type is unsupported`);
    if (typeof input.required !== "boolean") throw new CliError(`${label}.required must be boolean`);
    nonemptyString(input.description, `${label}.description`);
    if (input.required && Object.hasOwn(input, "default")) throw new CliError(`${label} cannot be required and have a default`);
    if (Object.hasOwn(input, "default")) validateTypedValue(input.default, input, `${label}.default`);
    if (Object.hasOwn(input, "examples")) {
      if (!Array.isArray(input.examples) || input.examples.length === 0) throw new CliError(`${label}.examples must be a non-empty array`);
      for (const example of input.examples) validateTypedValue(example, input, `${label}.examples`);
    }
    return input;
  });
}


function validateOutputs(value) {
  if (!Array.isArray(value)) throw new CliError("outputs must be an array");
  const names = new Set();
  const result = [];
  for (const [index, output] of value.entries()) {
    const label = `outputs[${index}]`;
    exactKeys(output, ["description", "name", "path", "type"], label);
    if (!INPUT_NAME_RE.test(output.name || "") || names.has(output.name)) throw new CliError(`${label}.name is invalid or duplicated`);
    names.add(output.name);
    if (!OUTPUT_TYPES.has(output.type)) throw new CliError(`${label}.type is unsupported`);
    nonemptyString(output.description, `${label}.description`);
    const normalized = { ...output };
    if (Object.hasOwn(output, "path")) {
      normalized.path = relativePath(output.path, `${label}.path`);
      if (!new Set(["file", "files"]).has(output.type)) throw new CliError(`${label}.path is valid only for file or files outputs`);
      if (output.type === "file" && normalized.path.endsWith("/")) throw new CliError(`${label}.path must name one file`);
      if (output.type === "files" && !normalized.path.endsWith("/")) throw new CliError(`${label}.path must name a directory scope ending in /`);
    }
    result.push(normalized);
  }
  return result;
}


function validateScopeSpec(scope, effect, inputMap, index) {
  const label = `effects.${effect}[${index}]`;
  exactKeys(scope, ["input", "path"], label);
  if (Object.hasOwn(scope, "path") === Object.hasOwn(scope, "input")) {
    throw new CliError(`${label} must contain exactly one of path or input`);
  }
  if (Object.hasOwn(scope, "path")) {
    const value = relativePath(scope.path, `${label}.path`);
    if (value === ".") throw new CliError(`${label}.path cannot be the broad static scope '.'; bind a typed path input instead`);
    assertScopePathSafe(value, effect, false);
    return { path: value };
  }
  if (!INPUT_NAME_RE.test(scope.input || "")) throw new CliError(`${label}.input is invalid`);
  const input = inputMap.get(scope.input);
  if (!input || !PATH_INPUT_TYPES.has(input.type)) {
    throw new CliError(`${label}.input must reference a path, file, or directory input`);
  }
  return { input: scope.input };
}


function validateManifest(manifest, actionId, repoRoot, actionDir) {
  exactKeys(manifest, TOP_LEVEL_KEYS, "action manifest");
  if (manifest.format !== 2 || manifest.id !== actionId) throw new CliError(`action manifest format or id is invalid: ${actionId}`);
  if (!Number.isSafeInteger(manifest.version) || manifest.version < 1) throw new CliError("version must be a safe integer >= 1");
  nonemptyString(manifest.title, "title");
  nonemptyString(manifest.summary, "summary");
  if (manifest.entrypoint !== "run.mjs" || manifest.test !== "run.test.mjs") {
    throw new CliError("entrypoint and test must be run.mjs and run.test.mjs");
  }
  const entrypoint = resolveExistingFile(path.join(actionDir, manifest.entrypoint), actionDir, "action entrypoint");
  const test = resolveExistingFile(path.join(actionDir, manifest.test), actionDir, "action test");
  const docs = relativePath(manifest.docs, "docs");
  const expectedDocs = `_handbook/actions/${actionId}.md`;
  if (docs !== expectedDocs) throw new CliError(`docs must mirror the Action path exactly: ${expectedDocs}`);
  resolveExistingFile(path.resolve(repoRoot, docs), repoRoot, "Action documentation");

  exactKeys(manifest.methodConfidence, ["basis", "reviewTriggers", "status"], "methodConfidence");
  if (!["established", "provisional"].includes(manifest.methodConfidence.status)) throw new CliError("methodConfidence.status is invalid");
  stringArray(manifest.methodConfidence.basis, "methodConfidence.basis", { nonempty: true });
  stringArray(manifest.methodConfidence.reviewTriggers, "methodConfidence.reviewTriggers", { nonempty: true });

  exactKeys(manifest.readiness, ["evidence", "status", "validatedAt", "validatedOn"], "readiness");
  if (!["tests-passed", "untested", "validated"].includes(manifest.readiness.status)) throw new CliError("readiness.status is invalid");
  stringArray(manifest.readiness.evidence, "readiness.evidence");
  stringArray(manifest.readiness.validatedOn, "readiness.validatedOn");
  if (manifest.readiness.validatedAt !== null && (typeof manifest.readiness.validatedAt !== "string" || Number.isNaN(Date.parse(manifest.readiness.validatedAt)))) {
    throw new CliError("readiness.validatedAt must be null or an ISO date-time string");
  }

  exactKeys(manifest.lifecycle, ["reason", "replacement", "status"], "lifecycle");
  if (!["active", "deprecated", "draft"].includes(manifest.lifecycle.status)) throw new CliError("lifecycle.status is invalid");
  for (const key of ["reason", "replacement"]) {
    if (manifest.lifecycle[key] !== null && (typeof manifest.lifecycle[key] !== "string" || !manifest.lifecycle[key].trim())) throw new CliError(`lifecycle.${key} must be null or a non-empty string`);
  }

  const inputs = validateInputs(manifest.inputs);
  const inputMap = new Map(inputs.map((input) => [input.name, input]));
  const outputs = validateOutputs(manifest.outputs);
  exactKeys(manifest.effects, EFFECT_KEYS, "effects");
  const effects = {};
  for (const effect of EFFECT_KEYS) {
    if (!Array.isArray(manifest.effects[effect])) throw new CliError(`effects.${effect} must be an array`);
    effects[effect] = manifest.effects[effect].map((scope, index) => validateScopeSpec(scope, effect, inputMap, index));
    const unique = new Set(effects[effect].map(stableJson));
    if (unique.size !== effects[effect].length) throw new CliError(`effects.${effect} contains duplicates`);
  }
  if (effects.temporary.length) {
    throw new CliError("effects.temporary is reserved for runner-managed private state and must be empty in format 2");
  }

  exactKeys(manifest.execution, ["maxOutputBytes", "mode", "receipt", "timeoutMs"], "execution");
  if (!["plan-apply", "read-only"].includes(manifest.execution.mode)) throw new CliError("execution.mode is invalid");
  if (manifest.execution.receipt !== "json-v1") throw new CliError("execution.receipt must be json-v1");
  if (!Number.isInteger(manifest.execution.timeoutMs) || manifest.execution.timeoutMs < 100 || manifest.execution.timeoutMs > 300000) throw new CliError("execution.timeoutMs must be between 100 and 300000");
  if (!Number.isInteger(manifest.execution.maxOutputBytes) || manifest.execution.maxOutputBytes < 1024 || manifest.execution.maxOutputBytes > 4194304) throw new CliError("execution.maxOutputBytes must be between 1024 and 4194304");
  if (manifest.execution.mode === "read-only" && (effects.creates.length || effects.updates.length || effects.temporary.length)) {
    throw new CliError("read-only Actions cannot declare create, update, or temporary effects");
  }
  if (manifest.execution.mode === "plan-apply" && !effects.creates.length && !effects.updates.length) {
    throw new CliError("plan-apply Actions must declare at least one create or update scope");
  }
  if (manifest.execution.mode === "plan-apply" && (outputs.length === 0 || outputs.some((output) => !["file", "files"].includes(output.type)))) {
    throw new CliError("plan-apply Actions must declare at least one file/files output and no non-file outputs");
  }

  exactKeys(manifest.success, ["postconditions"], "success");
  stringArray(manifest.success.postconditions, "success.postconditions", { nonempty: true });

  if (!Array.isArray(manifest.dependencies)) throw new CliError("dependencies must be an array");
  const dependencyNames = new Set();
  for (const [index, dependency] of manifest.dependencies.entries()) {
    exactKeys(dependency, ["name", "version"], `dependencies[${index}]`);
    if (!PACKAGE_RE.test(dependency.name || "") || dependencyNames.has(dependency.name)) throw new CliError(`dependencies[${index}].name is invalid or duplicated`);
    dependencyNames.add(dependency.name);
    if (!EXACT_VERSION_RE.test(dependency.version || "")) throw new CliError(`dependencies[${index}].version must be exact semver`);
  }

  exactKeys(manifest.digests, ["entrypoint", "test"], "digests");
  for (const key of ["entrypoint", "test"]) if (!SHA256_RE.test(manifest.digests[key] || "")) throw new CliError(`digests.${key} must be sha256:<64 lowercase hex>`);
  const actualEntrypoint = hashFile(entrypoint);
  const actualTest = hashFile(test);
  if (actualEntrypoint !== manifest.digests.entrypoint) throw new CliError(`entrypoint digest drift for ${actionId}`);
  if (actualTest !== manifest.digests.test) throw new CliError(`test digest drift for ${actionId}`);

  const evidence = manifest.readiness.evidence;
  const validatedOn = manifest.readiness.validatedOn;
  if (manifest.readiness.status !== "validated" && (manifest.readiness.validatedAt !== null || validatedOn.length)) throw new CliError("only validated readiness may claim validatedAt or validatedOn");
  if (["tests-passed", "validated"].includes(manifest.readiness.status) && evidence.length === 0) throw new CliError(`${manifest.readiness.status} readiness requires evidence`);
  if (manifest.readiness.status === "validated" && (!manifest.readiness.validatedAt || validatedOn.length === 0)) throw new CliError("validated readiness requires validatedAt and validatedOn evidence");
  if (manifest.lifecycle.status === "deprecated" && !manifest.lifecycle.reason) throw new CliError("deprecated lifecycle requires a reason");
  if (manifest.lifecycle.status !== "deprecated" && manifest.lifecycle.replacement !== null) throw new CliError("only a deprecated Action may name a replacement");

  return { ...manifest, docs, effects, inputs, outputs, inputMap, actionDir, entrypoint, test, repoRoot };
}


export function loadAction(repoRoot, actionId) {
  repoRoot = realpathSync(path.resolve(repoRoot));
  const segments = actionSegmentsFromId(actionId);
  const toolsRoot = cliRoot(repoRoot);
  const actionsRoot = path.join(toolsRoot, "actions");
  const actionDir = path.join(actionsRoot, ...segments);
  if (!existsSync(actionDir)) throw new CliError(`unknown action: ${actionId}`);
  const pathDirectories = [toolsRoot, actionsRoot, ...segments.map((_, index) => path.join(actionsRoot, ...segments.slice(0, index + 1)))];
  for (const [index, pathname] of pathDirectories.entries()) {
    const label = index === 0 ? "Trellis runtime directory" : index === 1 ? "actions directory" : index === pathDirectories.length - 1 ? "action directory" : "Action group directory";
    if (!existsSync(pathname)) throw new CliError(`${label} is missing`);
    rejectSymlink(pathname, label);
    const containmentRoot = index >= 2 ? actionsRoot : repoRoot;
    if (!lstatSync(pathname).isDirectory() || !isWithin(realpathSync(pathname), realpathSync(containmentRoot))) throw new CliError(`${label} must be a work-folder-local directory`);
    if (index >= 2 && path.basename(realpathSync(pathname)) !== segments[index - 2]) {
      throw new CliError(`Action path collides case-insensitively at segment: ${segments[index - 2]}`);
    }
    if (index >= 2 && index < pathDirectories.length - 1) {
      const marker = readdirSync(pathname, { withFileTypes: true }).find((entry) => ACTION_FILES.has(entry.name));
      if (marker) throw new CliError(`Action leaf cannot contain nested Action path ${actionId}: ${path.relative(actionsRoot, pathname)}`);
    }
  }
  for (const entry of readdirSync(actionDir, { withFileTypes: true })) {
    if (!ACTION_FILES.has(entry.name) || !entry.isFile() || entry.isSymbolicLink()) {
      throw new CliError(`${actionId} action directory may contain only regular action.json, run.mjs, and run.test.mjs files; found: ${entry.name}`);
    }
  }
  for (const filename of ACTION_FILES) {
    if (!existsSync(path.join(actionDir, filename))) throw new CliError(`${actionId} action directory is missing required file: ${filename}`);
  }
  resolveExistingFile(path.join(toolsRoot, "package.json"), toolsRoot, "tool package manifest");
  const manifestPath = resolveExistingFile(path.join(actionDir, "action.json"), actionDir, "action manifest");
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  } catch (error) {
    throw new CliError(`invalid JSON in ${manifestPath}: ${error.message}`);
  }
  return { ...validateManifest(manifest, actionId, repoRoot, actionDir), manifestPath, manifestDigest: hashFile(manifestPath) };
}


export function discoverActions(repoRoot) {
  repoRoot = realpathSync(path.resolve(repoRoot));
  const actionsRoot = path.join(cliRoot(repoRoot), "actions");
  if (!existsSync(actionsRoot)) return { actions: [], errors: [] };
  rejectSymlink(actionsRoot, "actions directory");
  if (!lstatSync(actionsRoot).isDirectory() || !isWithin(realpathSync(actionsRoot), repoRoot)) {
    throw new CliError("actions directory must be a regular work-folder-local directory");
  }
  const actions = [];
  const errors = [];
  function visit(directory, segments) {
    const groupId = segments.join("/") || `${CLI_RELATIVE_ROOT}/actions`;
    let entries;
    try {
      entries = readdirSync(directory, { withFileTypes: true }).sort((left, right) => compareText(left.name, right.name));
    } catch (error) {
      errors.push({ id: groupId, error: `cannot read Action group: ${error.message}` });
      return;
    }
    if (segments.length && entries.length === 0) {
      errors.push({ id: groupId, error: "Action group directory must not be empty" });
      return;
    }
    if (segments.length && entries.some((entry) => ACTION_FILES.has(entry.name))) {
      const actionId = segments.join("/");
      try { actions.push(loadAction(repoRoot, actionId)); }
      catch (error) { errors.push({ id: actionId, error: error.message }); }
      return;
    }

    const folded = new Map();
    for (const entry of entries) {
      const key = entry.name.toLowerCase();
      const siblings = folded.get(key) || [];
      siblings.push(entry.name);
      folded.set(key, siblings);
    }
    const collisions = new Set([...folded.values()].filter((names) => names.length > 1).flat());
    for (const entry of entries) {
      const id = [...segments, entry.name].join("/");
      if (collisions.has(entry.name)) {
        errors.push({ id, error: "Action path entry collides case-insensitively with a sibling" });
        continue;
      }
      if (!ACTION_SEGMENT_RE.test(entry.name)) {
        errors.push({ id, error: "Action path segments must be kebab-case" });
        continue;
      }
      if (segments.length === 0 && MANAGEMENT_COMMANDS.has(entry.name)) {
        errors.push({ id, error: "Action path uses a reserved top-level management word" });
        continue;
      }
      if (entry.isSymbolicLink()) {
        errors.push({ id, error: "Action path entries must not be symlinks" });
        continue;
      }
      if (!entry.isDirectory()) {
        errors.push({ id, error: "Action group directories may contain only Action directories" });
        continue;
      }
      const pathname = path.join(directory, entry.name);
      if (!isWithin(realpathSync(pathname), realpathSync(actionsRoot))) {
        errors.push({ id, error: "Action path escapes the actions directory" });
        continue;
      }
      visit(pathname, [...segments, entry.name]);
    }
  }
  visit(actionsRoot, []);
  actions.sort((left, right) => compareText(left.id, right.id));
  errors.sort((left, right) => compareText(left.id, right.id) || compareText(left.error, right.error));
  return { actions, errors };
}


export function listActions(repoRoot) {
  return discoverActions(repoRoot).actions;
}


function resolvedScope(scope, action, values, effect) {
  const input = scope.input ? action.inputMap.get(scope.input) : null;
  const value = scope.path ?? values[scope.input];
  const normalized = relativePath(value, `effects.${effect}`);
  assertScopePathSafe(normalized, effect, Boolean(scope.input));
  const resolved = path.resolve(action.repoRoot, normalized);
  if (!isWithin(resolved, action.repoRoot)) throw new CliError(`effect scope escapes work folder: ${normalized}`);
  assertNoSymlinkComponents(action.repoRoot, resolved, `effect scope ${normalized}`);
  let existing = resolved;
  while (!existsSync(existing)) {
    const parent = path.dirname(existing);
    if (parent === existing) break;
    existing = parent;
  }
  if (!isWithin(realpathSync(existing), action.repoRoot)) throw new CliError(`effect scope resolves outside work folder: ${normalized}`);
  const directory = input?.type === "directory" || normalized.endsWith("/") || existsSync(resolved) && lstatSync(resolved).isDirectory();
  if (effect === "reads") {
    if (!existsSync(resolved)) throw new CliError(`read scope is missing: ${normalized}`);
    if (input?.type === "file" && !lstatSync(resolved).isFile()) throw new CliError(`input ${input.name} must be a file`);
    if (input?.type === "directory" && !lstatSync(resolved).isDirectory()) throw new CliError(`input ${input.name} must be a directory`);
  }
  return { declared: scope, path: normalized, resolved, directory };
}


function resolveEffects(action, values) {
  return Object.fromEntries(EFFECT_KEYS.map((effect) => [effect, action.effects[effect].map((scope) => resolvedScope(scope, action, values, effect))]));
}


function parseScalar(raw, input) {
  if (input.type === "boolean") {
    if (raw === true || raw === "true") return true;
    if (raw === "false") return false;
    throw new CliError(`--${input.name} must be true or false`);
  }
  if (input.type === "integer") {
    if (!/^-?[0-9]+$/.test(raw)) throw new CliError(`--${input.name} must be an integer`);
    const value = Number(raw);
    if (!Number.isSafeInteger(value)) throw new CliError(`--${input.name} must be a safe integer`);
    return value;
  }
  if (input.type === "number") {
    const value = Number(raw);
    if (!Number.isFinite(value)) throw new CliError(`--${input.name} must be a number`);
    return value;
  }
  return PATH_INPUT_TYPES.has(input.type) ? relativePath(raw, `--${input.name}`) : raw;
}


function parseNamedInputs(tokens, action) {
  const supplied = new Map();
  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    if (!token.startsWith("--") || token === "--") throw new CliError(`Action inputs must be named; found: ${token}`);
    const equal = token.indexOf("=");
    const name = token.slice(2, equal === -1 ? undefined : equal);
    const input = action.inputMap.get(name);
    if (!input) throw new CliError(`undeclared Action input: --${name}`);
    let raw = equal === -1 ? undefined : token.slice(equal + 1);
    if (raw === undefined && input.type === "boolean" && (index + 1 === tokens.length || tokens[index + 1].startsWith("--"))) raw = true;
    if (raw === undefined) {
      index += 1;
      if (index >= tokens.length) throw new CliError(`--${name} requires a value`);
      raw = tokens[index];
    }
    const value = parseScalar(raw, input);
    if (input.type === "string-list") {
      const current = supplied.get(name) || [];
      current.push(value);
      supplied.set(name, current);
    } else {
      if (supplied.has(name)) throw new CliError(`Action input supplied more than once: --${name}`);
      supplied.set(name, value);
    }
  }
  const values = {};
  for (const input of action.inputs) {
    if (supplied.has(input.name)) values[input.name] = supplied.get(input.name);
    else if (Object.hasOwn(input, "default")) values[input.name] = input.default;
    else if (input.required) throw new CliError(`missing required Action input: --${input.name}`);
  }
  return values;
}


function actionArguments(action, values) {
  const args = [];
  for (const input of action.inputs) {
    if (!Object.hasOwn(values, input.name)) continue;
    const rawValues = input.type === "string-list" ? values[input.name] : [values[input.name]];
    for (const value of rawValues) args.push(`--${input.name}`, String(value));
  }
  return args;
}


function executionOptions(args, { planRequired = false } = {}) {
  const options = { allowDeprecated: false, allowDraft: false, allowUntested: false, json: false, plan: null, inputs: [] };
  let inputs = false;
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (inputs) options.inputs.push(arg);
    else if (arg === "--") inputs = true;
    else if (arg === "--json") options.json = true;
    else if (arg === "--allow-deprecated") options.allowDeprecated = true;
    else if (arg === "--allow-draft") options.allowDraft = true;
    else if (arg === "--allow-untested") options.allowUntested = true;
    else if (arg === "--plan") {
      options.plan = args[++index];
      if (!options.plan) throw new CliError("--plan requires a hash");
    } else throw new CliError(`unknown option: ${arg}`);
  }
  if (planRequired && !options.plan) throw new CliError("apply requires --plan <sha256>");
  if (!planRequired && options.plan) throw new CliError("--plan is valid only with apply");
  if (planRequired && options.inputs.length) throw new CliError("apply uses inputs bound into the saved plan");
  return options;
}


function assertRunnable(action, options) {
  if (action.lifecycle.status === "draft" && !options.allowDraft) throw new CliError(`${action.id} is Draft; use test first or --allow-draft for deliberate development use`);
  if (action.lifecycle.status === "deprecated" && !options.allowDeprecated) throw new CliError(`${action.id} is Deprecated; review its replacement or use --allow-deprecated deliberately`);
  if (action.readiness.status === "untested" && !options.allowUntested) throw new CliError(`${action.id} is Untested; run its focused tests first or use --allow-untested deliberately`);
}


function dependencyDirectories(action) {
  const result = [];
  for (const dependency of action.dependencies) {
    const directory = path.join(cliRoot(action.repoRoot), "node_modules", ...dependency.name.split("/"));
    if (!existsSync(directory)) throw new CliError(`dependency ${dependency.name} is not installed`);
    rejectSymlink(directory, `dependency ${dependency.name}`);
    if (!lstatSync(directory).isDirectory() || !isWithin(realpathSync(directory), action.repoRoot)) {
      throw new CliError(`dependency ${dependency.name} must be a regular work-folder-local directory`);
    }
    const packageFile = resolveExistingFile(path.join(directory, "package.json"), directory, `dependency ${dependency.name}`);
    const packageManifest = JSON.parse(readFileSync(packageFile, "utf8"));
    if (packageManifest.name !== dependency.name || packageManifest.version !== dependency.version) throw new CliError(`dependency ${dependency.name} does not match exact version ${dependency.version}`);
    result.push(directory);
  }
  return result;
}


function packageName(specifier) {
  if (specifier.startsWith("@")) return specifier.split("/").slice(0, 2).join("/");
  return specifier.split("/")[0];
}


function validateSource(action, { includeTest = false } = {}) {
  const declared = new Set(action.dependencies.map((item) => item.name));
  const files = includeTest ? [action.entrypoint, action.test] : [action.entrypoint];
  for (const filename of files) {
    const source = readFileSync(filename, "utf8");
    for (const [pattern, label] of BLOCKED_SOURCE) {
      if (pattern.test(source)) throw new CliError(`${action.id} source references prohibited ${label}: ${path.basename(filename)}`);
    }
    if (!filename.endsWith(".test.mjs") && /\bprocess\s*(?:\.\s*env|\[\s*["']env["']\s*\])/.test(source)) {
      throw new CliError(`${action.id} source references prohibited process environment input: ${path.basename(filename)}`);
    }
    const importRe = /(?:from\s+|import\s+|import\s*\(|require\s*\()\s*["']([^"']+)["']/g;
    for (const match of source.matchAll(importRe)) {
      const specifier = match[1];
      const bareBuiltin = specifier.startsWith("node:") ? specifier.slice(5).split("/")[0] : specifier.split("/")[0];
      if (BLOCKED_BUILTINS.has(bareBuiltin) && !(bareBuiltin === "os" && filename === action.test)) throw new CliError(`${action.id} imports prohibited built-in module: ${specifier}`);
      if (specifier.startsWith("node:")) continue;
      if (specifier.startsWith(".") || specifier.startsWith("/") || specifier.startsWith("file:") || specifier.startsWith("data:")) {
        if (filename === action.test && specifier === "./run.mjs") continue;
        throw new CliError(`${action.id} imports prohibited local or inline module: ${specifier}`);
      }
      if (!declared.has(packageName(specifier))) throw new CliError(`${action.id} imports undeclared dependency: ${packageName(specifier)}`);
    }
  }
}


function sanitizedEnvironment(config, testRoot = null) {
  const result = {};
  for (const name of SAFE_ENV) if (process.env[name] !== undefined) result[name] = process.env[name];
  result.TRELLIS_GUARD_CONFIG = JSON.stringify(config);
  if (testRoot) {
    result.TMPDIR = testRoot;
    result.TMP = testRoot;
    result.TEMP = testRoot;
  }
  return result;
}


function hardenedNodeArgs(action, effects, dependencies, { test = false, testRoot = null } = {}) {
  const guard = path.join(cliRoot(action.repoRoot), "src", "guard.mjs");
  resolveExistingFile(guard, path.join(cliRoot(action.repoRoot), "src"), "local-only guard");
  const args = [
    "--permission",
    "--no-addons",
    "--no-global-search-paths",
    "--disable-proto=throw",
    "--disable-sigusr1",
    "--disallow-code-generation-from-strings",
  ];
  const requestedReads = [action.actionDir, guard, ...effects.reads.map((scope) => scope.resolved), ...dependencies]
    .map((pathname) => path.resolve(pathname))
    .sort((left, right) => left.length - right.length);
  const reads = [];
  for (const pathname of requestedReads) {
    if (!reads.some((parent) => isWithin(pathname, parent))) reads.push(pathname);
  }
  for (const pathname of reads) args.push(`--allow-fs-read=${pathname}`);
  if (test) {
    if (!testRoot) throw new CliError("a dedicated test directory is required");
    args.push(`--allow-fs-read=${testRoot}`);
    args.push(`--allow-fs-write=${testRoot}`);
  }
  args.push("--import", pathToFileURL(guard).href);
  return args;
}


function execute(action, nodeArgs, effects, dependencies, injected, { test = false, testRoot = null } = {}) {
  const allowedReserved = [action.actionDir, ...dependencies, ...(testRoot ? [testRoot] : [])];
  const allowedModuleFiles = test ? [action.entrypoint, action.test] : [action.entrypoint];
  const spawn = injected.spawn ?? spawnSync;
  const result = spawn(process.execPath, nodeArgs, {
    cwd: action.repoRoot,
    encoding: "utf8",
    env: sanitizedEnvironment({
      repoRoot: action.repoRoot,
      allowedReserved,
      allowedModuleFiles,
      allowedModuleRoots: dependencies,
      readScopes: effects.reads.map(({ resolved, directory }) => ({ path: resolved, directory })),
      test,
    }, testRoot),
    maxBuffer: action.execution.maxOutputBytes,
    shell: false,
    timeout: action.execution.timeoutMs,
  });
  if (result.error) {
    if (result.error.code === "ETIMEDOUT") throw new CliError(`${action.id} exceeded ${action.execution.timeoutMs}ms`);
    if (result.error.code === "ENOBUFS") throw new CliError(`${action.id} exceeded ${action.execution.maxOutputBytes} output bytes`);
    throw new CliError(`could not start Action: ${result.error.message}`);
  }
  if (result.signal) throw new CliError(`${action.id} stopped by signal ${result.signal}`);
  if (test) return result;
  if (result.status !== 0) throw new CliError(`${action.id} failed (${result.status}): ${(result.stderr || result.stdout || "no diagnostic").trim()}`);
  if ((result.stderr || "").trim()) throw new CliError(`${action.id} emitted unexpected stderr: ${result.stderr.trim()}`);
  let envelope;
  try {
    envelope = JSON.parse((result.stdout || "").trim());
  } catch {
    throw new CliError(`${action.id} must emit exactly one JSON envelope and no other stdout`);
  }
  return envelope;
}


function validateVerification(value, label) {
  if (!Array.isArray(value)) throw new CliError(`${label} must be an array`);
  if (value.length === 0) throw new CliError(`${label} must not be empty`);
  for (const [index, item] of value.entries()) {
    exactKeys(item, ["check", "detail", "ok"], `${label}[${index}]`);
    nonemptyString(item.check, `${label}[${index}].check`);
    if (typeof item.ok !== "boolean") throw new CliError(`${label}[${index}].ok must be boolean`);
    if (item.detail !== undefined) nonemptyString(item.detail, `${label}[${index}].detail`);
  }
  return value;
}


function receiptBase(action, mode, status, summary, verification) {
  return {
    schema: "trellis.action-receipt/v1",
    action: { id: action.id, version: action.version, manifest: action.manifestDigest, entrypoint: action.digests.entrypoint },
    mode,
    status,
    summary,
    inputNames: action.inputs.map((input) => input.name),
    verification,
  };
}


function finalizeReceipt(payload) {
  return { ...payload, receipt: hashBytes(stableJson(payload)) };
}


function printReceipt(receipt, write, json) {
  if (json) {
    write(JSON.stringify(receipt, null, 2));
    return;
  }
  write(`Action: ${receipt.action.id}`);
  write(`Mode: ${receipt.mode}`);
  write(`Status: ${receipt.status}`);
  write(receipt.summary);
  if (receipt.plan) write(`Plan: ${receipt.plan}`);
  for (const item of receipt.verification || []) write(`${item.ok ? "PASS" : "FAIL"}: ${item.check}${item.detail ? ` — ${item.detail}` : ""}`);
  write(`Receipt: ${receipt.receipt}`);
}


function validateReportedFile(action, effects, value, label) {
  const relative = relativePath(value, label);
  if (relative === "." || relative.endsWith("/")) throw new CliError(`${label} must name one file`);
  assertScopePathSafe(relative, "reads", true);
  const target = path.resolve(action.repoRoot, relative);
  if (!isWithin(target, action.repoRoot)) throw new CliError(`${label} escapes the work folder`);
  assertNoSymlinkComponents(action.repoRoot, target, label);
  if (!existsSync(target) || !lstatSync(target).isFile()) throw new CliError(`${label} must reference an existing regular file`);
  const resolved = realpathSync(target);
  if (!isWithin(resolved, action.repoRoot)) throw new CliError(`${label} resolves outside the work folder`);
  if (!effects.reads.some((scope) => scopeCovers(scope, target) && scopeCovers(scope, resolved))) {
    throw new CliError(`${label} is outside the declared read effects`);
  }
  return relative;
}


function validateResultOutputs(action, effects, value) {
  if (!Array.isArray(value)) throw new CliError("Action result outputs must be an array");
  const declared = new Map(action.outputs.map((output) => [output.name, output]));
  const seen = new Set();
  const result = value.map((item, index) => {
    exactKeys(item, ["name", "value"], `Action result outputs[${index}]`);
    const output = declared.get(item.name);
    if (!output || seen.has(item.name)) throw new CliError(`Action result output is unknown or duplicated: ${item.name}`);
    seen.add(item.name);
    const label = `Action result output ${item.name}`;
    if (output.type === "text" && typeof item.value !== "string") throw new CliError(`${label} must be text`);
    if (output.type === "number" && (typeof item.value !== "number" || !Number.isFinite(item.value))) throw new CliError(`${label} must be a finite number`);
    if (output.type === "boolean" && typeof item.value !== "boolean") throw new CliError(`${label} must be boolean`);
    if (output.type === "json" && (item.value === undefined || typeof item.value === "function" || typeof item.value === "symbol")) throw new CliError(`${label} must be JSON-compatible`);
    if (output.type === "file") {
      item.value = validateReportedFile(action, effects, item.value, label);
      if (output.path && item.value !== relativePath(output.path, `outputs.${output.name}.path`)) throw new CliError(`${label} does not match its declared path`);
    }
    if (output.type === "files") {
      if (!Array.isArray(item.value)) throw new CliError(`${label} must be an array of paths`);
      item.value = item.value.map((pathname) => validateReportedFile(action, effects, pathname, label));
      if (new Set(item.value).size !== item.value.length) throw new CliError(`${label} contains duplicate paths`);
      if (output.path && item.value.some((pathname) => !outputCovers(output, pathname))) {
        throw new CliError(`${label} contains a path outside its declared directory scope`);
      }
    }
    return item;
  });
  const missing = [...declared.keys()].filter((name) => !seen.has(name));
  if (missing.length) throw new CliError(`Action result omitted declared outputs: ${missing.join(", ")}`);
  return result;
}


function runReadOnly(action, values, effects, options, injected, write) {
  validateSource(action);
  const dependencies = dependencyDirectories(action);
  const args = hardenedNodeArgs(action, effects, dependencies);
  args.push(action.entrypoint, ...actionArguments(action, values));
  const envelope = execute(action, args, effects, dependencies, injected);
  exactKeys(envelope, ["outputs", "schema", "status", "summary", "verification"], "Action result");
  if (envelope.schema !== "trellis.action-result/v1" || !["failed", "ok"].includes(envelope.status)) throw new CliError("Action result schema or status is invalid");
  nonemptyString(envelope.summary, "Action result summary");
  validateVerification(envelope.verification, "Action result verification");
  const verificationPassed = envelope.verification.every((item) => item.ok);
  if ((envelope.status === "ok") !== verificationPassed) throw new CliError("Action result status must be ok exactly when every verification check passes");
  const outputs = validateResultOutputs(action, effects, envelope.outputs);
  const receipt = finalizeReceipt({ ...receiptBase(action, "read-only", envelope.status, envelope.summary, envelope.verification), outputs });
  printReceipt(receipt, write, options.json);
  return envelope.status === "ok" ? 0 : 1;
}


function scopeCovers(scope, candidate) {
  return scope.directory ? isWithin(candidate, scope.resolved) : candidate === scope.resolved;
}


function snapshot(action, readScopes) {
  const entries = new Map();
  function visit(pathname) {
    const relative = path.relative(action.repoRoot, pathname).replaceAll(path.sep, "/") || ".";
    if (isHardReservedPath(relative)) return;
    const stat = lstatSync(pathname);
    if (stat.isSymbolicLink()) throw new CliError(`plan input contains a symlink: ${relative}`);
    if (stat.isDirectory()) {
      entries.set(`${relative}/`, "directory");
      for (const child of readdirSync(pathname).sort(compareText)) visit(path.join(pathname, child));
    } else if (stat.isFile()) {
      entries.set(relative, `${hashFile(pathname)}:${stat.size}`);
    } else throw new CliError(`plan input is not a regular file or directory: ${relative}`);
  }
  for (const scope of readScopes) visit(scope.resolved);
  const value = [...entries].sort((a, b) => compareText(a[0], b[0]));
  return { digest: hashBytes(stableJson(value)), entries: value };
}


function planStateRoot(action) {
  const stateRoot = requireScratchRoot(action.repoRoot);
  const plansRoot = ensurePrivateDirectory(action.repoRoot, path.join(stateRoot, "plans"), "private Action plans");
  const segments = actionSegmentsFromId(action.id);
  let directory = plansRoot;
  for (const segment of segments) {
    directory = ensurePrivateDirectory(action.repoRoot, path.join(directory, segment), "private Action plan state");
    if (path.basename(realpathSync(directory)) !== segment) {
      throw new CliError(`private Action state path collides case-insensitively: ${segment}`);
    }
  }
  return directory;
}


function operationBytes(operation, label) {
  if (operation.encoding === "utf8") return Buffer.from(operation.content, "utf8");
  if (operation.encoding === "base64" && /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(operation.content)) return Buffer.from(operation.content, "base64");
  throw new CliError(`${label}.encoding/content is invalid`);
}


function validatePlanEnvelope(action, envelope, effects) {
  exactKeys(envelope, ["operations", "schema", "summary", "verification"], "Action plan");
  if (envelope.schema !== "trellis.action-plan/v1") throw new CliError("Action plan schema is invalid");
  nonemptyString(envelope.summary, "Action plan summary");
  validateVerification(envelope.verification, "Action plan verification");
  if (envelope.verification.some((item) => !item.ok)) throw new CliError("Action plan verification failed; no plan was saved");
  if (!Array.isArray(envelope.operations) || envelope.operations.length === 0) throw new CliError("Action plan operations must be a non-empty array");
  const seen = new Set();
  const result = {
    ...envelope,
    operations: envelope.operations.map((operation, index) => {
      const label = `Action plan operations[${index}]`;
      exactKeys(operation, ["after", "before", "content", "encoding", "kind", "path"], label);
      if (!["create", "update"].includes(operation.kind)) throw new CliError(`${label}.kind must be create or update`);
      const relative = relativePath(operation.path, `${label}.path`);
      if (relative.endsWith("/") || relative === ".") throw new CliError(`${label}.path must be a file`);
      assertScopePathSafe(relative, operation.kind === "create" ? "creates" : "updates", true);
      const target = path.resolve(action.repoRoot, relative);
      assertNoSymlinkComponents(action.repoRoot, target, `Action plan target ${relative}`);
      if (seen.has(target)) throw new CliError(`Action plan targets a path more than once: ${relative}`);
      seen.add(target);
      const scopes = operation.kind === "create" ? effects.creates : effects.updates;
      if (!scopes.some((scope) => scopeCovers(scope, target))) throw new CliError(`Action plan ${operation.kind} is outside declared scope: ${relative}`);
      if (operation.kind === "create") {
        if (operation.before !== null) throw new CliError(`${label}.before must be null for create`);
        if (existsSync(target)) throw new CliError(`create target already exists: ${relative}`);
      } else {
        if (!SHA256_RE.test(operation.before || "")) throw new CliError(`${label}.before must be a sha256 digest for update`);
        if (!existsSync(target) || lstatSync(target).isSymbolicLink() || !lstatSync(target).isFile()) throw new CliError(`update target must be a regular existing file: ${relative}`);
        if (hashFile(target) !== operation.before) throw new CliError(`update target changed before plan was saved: ${relative}`);
      }
      if (!SHA256_RE.test(operation.after || "")) throw new CliError(`${label}.after must be a sha256 digest`);
      if (typeof operation.content !== "string") throw new CliError(`${label}.content must be a string`);
      const bytes = operationBytes(operation, label);
      if (hashBytes(bytes) !== operation.after) throw new CliError(`${label}.after does not match proposed content`);
      const parent = path.dirname(target);
      if (!existsSync(parent) || lstatSync(parent).isSymbolicLink() || !lstatSync(parent).isDirectory()) throw new CliError(`target parent must already be a regular directory: ${relative}`);
      return { ...operation, path: relative };
    }),
  };
  validatePlanOutputs(action, result.operations);
  return result;
}


function outputCovers(output, operationPath) {
  if (!output.path) return false;
  if (output.type === "file") return output.path === operationPath;
  const base = output.path.replace(/\/$/, "");
  return operationPath.startsWith(`${base}/`);
}


function validatePlanOutputs(action, operations) {
  const unbound = action.outputs.filter((output) => !output.path);
  if (unbound.length) {
    if (action.outputs.length !== 1) throw new CliError("a dynamic plan output is unambiguous only when it is the sole declared output");
    if (unbound[0].type === "file" && operations.length !== 1) throw new CliError("a dynamic file output must correspond to exactly one plan operation");
    return;
  }
  for (const operation of operations) {
    const matches = action.outputs.filter((output) => outputCovers(output, operation.path));
    if (matches.length === 0) throw new CliError(`plan operation is not represented by a declared output: ${operation.path}`);
    if (matches.length > 1) throw new CliError(`plan operation belongs to more than one declared output: ${operation.path}`);
  }
  for (const output of action.outputs) {
    if (!operations.some((operation) => outputCovers(output, operation.path))) throw new CliError(`declared output is not produced by the plan: ${output.name}`);
  }
}


function planOutputs(action, operations) {
  const [only] = action.outputs;
  if (action.outputs.length === 1 && !only.path) {
    return [{ name: only.name, value: only.type === "file" ? operations[0].path : operations.map((operation) => operation.path) }];
  }
  return action.outputs.map((output) => ({
    name: output.name,
    value: output.type === "file"
      ? output.path
      : operations.filter((operation) => outputCovers(output, operation.path)).map((operation) => operation.path),
  }));
}


function createPlan(action, values, effects, options, injected, write) {
  validateSource(action);
  const dependencies = dependencyDirectories(action);
  const args = hardenedNodeArgs(action, effects, dependencies);
  args.push(action.entrypoint, "--trellis-plan", ...actionArguments(action, values));
  const stateBefore = snapshot(action, effects.reads);
  const envelope = validatePlanEnvelope(action, execute(action, args, effects, dependencies, injected), effects);
  const review = envelope.operations.map((operation) => {
    const target = path.resolve(action.repoRoot, operation.path);
    const beforeBytes = operation.kind === "update" ? readFileSync(target) : null;
    if (beforeBytes && hashBytes(beforeBytes) !== operation.before) {
      throw new CliError(`update target changed while review content was captured: ${operation.path}`);
    }
    const beforeText = beforeBytes?.toString("utf8");
    const beforeIsUtf8 = beforeBytes ? Buffer.from(beforeText, "utf8").equals(beforeBytes) : false;
    return {
      kind: operation.kind,
      path: operation.path,
      before: operation.kind === "update" ? { digest: operation.before, encoding: beforeIsUtf8 ? "utf8" : "base64", content: beforeIsUtf8 ? beforeText : beforeBytes.toString("base64") } : null,
      after: { digest: operation.after, encoding: operation.encoding, content: operation.content },
    };
  });
  const inputState = snapshot(action, effects.reads);
  if (stateBefore.digest !== inputState.digest || stableJson(stateBefore.entries) !== stableJson(inputState.entries)) {
    throw new CliError("Action inputs changed while the plan was being created; review the source and plan again");
  }
  const bound = {
    schema: "trellis.saved-plan/v1",
    action: { id: action.id, version: action.version, manifest: action.manifestDigest, entrypoint: action.digests.entrypoint },
    inputs: values,
    inputState,
    plan: envelope,
    review,
  };
  const plan = hashBytes(stableJson(bound));
  const planFile = path.join(planStateRoot(action), `${plan.slice(7)}.json`);
  if (!existsSync(planFile)) writeFileSync(planFile, `${JSON.stringify({ ...bound, planId: plan, createdAt: new Date().toISOString() }, null, 2)}\n`, { flag: "wx", mode: 0o600 });
  chmodSync(planFile, 0o600);
  const receipt = finalizeReceipt({
    ...receiptBase(action, "plan", "ok", envelope.summary, envelope.verification),
    plan,
    operations: envelope.operations.map(({ kind, path: pathname, before, after }) => ({ kind, path: pathname, before, after })),
  });
  printReceipt(receipt, write, options.json);
  return 0;
}


function readSavedPlan(action, id) {
  const normalized = id.startsWith("sha256:") ? id : `sha256:${id}`;
  if (!SHA256_RE.test(normalized)) throw new CliError("plan id must be a sha256 digest");
  const filename = path.join(planStateRoot(action), `${normalized.slice(7)}.json`);
  const resolved = resolveExistingFile(filename, path.dirname(filename), "saved Action plan");
  let saved;
  try { saved = JSON.parse(readFileSync(resolved, "utf8")); } catch (error) { throw new CliError(`saved plan is invalid JSON: ${error.message}`); }
  if (saved.schema !== "trellis.saved-plan/v1" || saved.planId !== normalized || saved.action?.id !== action.id) throw new CliError("saved plan identity is invalid");
  const { createdAt, planId, ...bound } = saved;
  if (hashBytes(stableJson(bound)) !== planId) throw new CliError("saved plan content does not match its plan id");
  return saved;
}


function showPlan(action, args, write) {
  let json = false;
  let plan = null;
  for (let index = 0; index < args.length; index += 1) {
    if (args[index] === "--json") json = true;
    else if (args[index] === "--plan") {
      plan = args[++index];
      if (!plan) throw new CliError("--plan requires a hash");
    } else throw new CliError(`unknown show-plan option: ${args[index]}`);
  }
  if (!plan) throw new CliError("show-plan requires --plan <sha256>");
  const saved = readSavedPlan(action, plan);
  if (saved.action.version !== action.version || saved.action.manifest !== action.manifestDigest || saved.action.entrypoint !== action.digests.entrypoint) throw new CliError("Action changed after this plan was created; the plan is stale");
  const payload = { schema: "trellis.action-plan-review/v1", plan: saved.planId, action: action.id, summary: saved.plan.summary, operations: saved.review };
  if (json) {
    write(JSON.stringify(payload, null, 2));
    return 0;
  }
  write(`Action: ${action.id}`);
  write(`Plan: ${saved.planId}`);
  write(saved.plan.summary);
  for (const operation of saved.review) {
    write(`\n${operation.kind.toUpperCase()}: ${operation.path}`);
    if (operation.before) {
      const before = operation.before.encoding === "base64" ? Buffer.from(operation.before.content, "base64") : Buffer.from(operation.before.content, "utf8");
      write(`--- before ${operation.before.digest} (${before.length} bytes; ${operation.before.encoding})`);
      write(operation.before.content);
    } else write("--- before: file does not exist");
    const after = operation.after.encoding === "base64" ? Buffer.from(operation.after.content, "base64") : Buffer.from(operation.after.content, "utf8");
    write(`+++ after ${operation.after.digest} (${after.length} bytes; ${operation.after.encoding})`);
    write(operation.after.encoding === "utf8" ? operation.after.content : operation.after.content);
  }
  write(`\nApply only after review: ./trellis apply ${actionInvocation(action.id)} --plan ${saved.planId}`);
  return 0;
}


function applyPlan(action, options, write, injected = {}) {
  const fileOperations = { chmodSync, copyFileSync, renameSync, rmSync, writeFileSync, ...(injected.fileOperations || {}) };
  const saved = readSavedPlan(action, options.plan);
  if (saved.action.version !== action.version || saved.action.manifest !== action.manifestDigest || saved.action.entrypoint !== action.digests.entrypoint) throw new CliError("Action changed after this plan was created; create a new plan");
  const values = {};
  for (const input of action.inputs) {
    if (Object.hasOwn(saved.inputs, input.name)) values[input.name] = validateTypedValue(saved.inputs[input.name], input, `saved input ${input.name}`);
    else if (input.required) throw new CliError(`saved plan lacks required input: ${input.name}`);
  }
  const effects = resolveEffects(action, values);
  const currentState = snapshot(action, effects.reads);
  if (currentState.digest !== saved.inputState?.digest || stableJson(currentState.entries) !== stableJson(saved.inputState?.entries)) throw new CliError("Action inputs changed after planning; create a new plan");
  const envelope = validatePlanEnvelope(action, saved.plan, effects);
  for (const operation of envelope.operations) {
    const target = path.resolve(action.repoRoot, operation.path);
    if (operation.kind === "create") {
      if (existsSync(target)) throw new CliError(`create target appeared after planning: ${operation.path}`);
    } else if (hashFile(target) !== operation.before) throw new CliError(`update target changed after planning: ${operation.path}`);
  }
  const transactionBase = ensurePrivateDirectory(
    action.repoRoot,
    path.join(requireScratchRoot(action.repoRoot), "transactions"),
    "private transaction state",
  );
  const transaction = ensurePrivateDirectory(
    action.repoRoot,
    path.join(transactionBase, `${saved.planId.slice(7, 19)}-${randomBytes(16).toString("hex")}`),
    "private Action transaction",
  );
  const staged = [];
  try {
    for (const [index, operation] of envelope.operations.entries()) {
      const target = path.resolve(action.repoRoot, operation.path);
      const stage = path.join(transaction, `${index}.new`);
      const backup = path.join(transaction, `${index}.before`);
      const mode = operation.kind === "update" ? statSync(target).mode & 0o777 : 0o600;
      fileOperations.writeFileSync(stage, operationBytes(operation, `operation ${operation.path}`), { flag: "wx", mode: 0o600 });
      fileOperations.chmodSync(stage, mode);
      if (operation.kind === "update") {
        fileOperations.copyFileSync(target, backup);
        fileOperations.chmodSync(backup, 0o600);
      }
      staged.push({ operation, target, stage, backup, displaced: path.join(transaction, `${index}.displaced`), mode });
    }
  } catch (error) {
    try {
      fileOperations.rmSync(transaction, { recursive: true, force: true });
    } catch (cleanup) {
      throw new CliError(`apply staging failed before any work-folder file changed: ${error.message}; private cleanup failed at ${path.relative(action.repoRoot, transaction)}: ${cleanup.message}`);
    }
    throw new CliError(`apply staging failed before any work-folder file changed: ${error.message}`);
  }
  const applied = [];
  let digestVerification = [];
  try {
    for (const item of staged) {
      const { operation, target, stage } = item;
      assertNoSymlinkComponents(action.repoRoot, target, `apply target ${operation.path}`);
      const parent = path.dirname(target);
      if (!existsSync(parent) || !lstatSync(parent).isDirectory() || !isWithin(realpathSync(parent), action.repoRoot)) {
        throw new CliError(`apply target parent is no longer a regular work-folder directory: ${operation.path}`);
      }
      if (operation.kind === "create" && existsSync(target)) throw new CliError(`create target appeared during apply: ${operation.path}`);
      if (operation.kind === "update" && hashFile(target) !== operation.before) throw new CliError(`update target changed during apply: ${operation.path}`);
      try {
        fileOperations.renameSync(stage, target);
      } catch (replaceError) {
        if (operation.kind !== "update") throw replaceError;
        fileOperations.renameSync(target, item.displaced);
        try {
          fileOperations.renameSync(stage, target);
        } catch (stageError) {
          fileOperations.renameSync(item.displaced, target);
          throw stageError;
        }
      }
      applied.push(item);
      if (hashFile(target) !== operation.after) throw new CliError(`digest verification failed after applying: ${operation.path}`);
    }
    digestVerification = envelope.operations.map((operation) => ({
      check: `applied ${operation.kind} ${operation.path} matches planned digest`,
      ok: hashFile(path.resolve(action.repoRoot, operation.path)) === operation.after,
    }));
    const failed = digestVerification.find((item) => !item.ok);
    if (failed) throw new CliError(`final digest verification failed: ${failed.check}`);
  } catch (error) {
    const rollbackErrors = [];
    for (const item of applied.reverse()) {
      try {
        if (item.operation.kind === "create") fileOperations.rmSync(item.target, { force: true });
        else {
          try {
            fileOperations.renameSync(item.backup, item.target);
          } catch {
            fileOperations.rmSync(item.target, { force: true });
            fileOperations.renameSync(item.backup, item.target);
          }
          fileOperations.chmodSync(item.target, item.mode);
        }
      } catch (rollback) {
        rollbackErrors.push(`${item.operation.path}: ${rollback.message}`);
      }
    }
    if (rollbackErrors.length) {
      throw new CliError(`apply failed: ${error.message}; rollback incomplete (${rollbackErrors.join("; ")}). Private recovery material remains at ${path.relative(action.repoRoot, transaction)}`);
    }
    try {
      fileOperations.rmSync(transaction, { recursive: true, force: true });
    } catch (cleanup) {
      throw new CliError(`apply failed and was rolled back, but private cleanup failed at ${path.relative(action.repoRoot, transaction)}: ${cleanup.message}`);
    }
    throw new CliError(`apply failed and was rolled back: ${error.message}`);
  }
  const verification = [
    ...envelope.verification,
    ...digestVerification,
  ];
  const status = "ok";
  const receipt = finalizeReceipt({
    ...receiptBase(action, "apply", status, `Applied ${envelope.operations.length} exact planned operation(s).`, verification),
    plan: saved.planId,
    outputs: planOutputs(action, envelope.operations),
    operations: envelope.operations.map(({ kind, path: pathname, before, after }) => ({ kind, path: pathname, before, after })),
  });
  try {
    fileOperations.rmSync(transaction, { recursive: true, force: true });
  } catch (cleanup) {
    throw new CliError(`apply completed and verified with receipt ${receipt.receipt}, but private cleanup failed at ${path.relative(action.repoRoot, transaction)}; do not reapply this plan: ${cleanup.message}`);
  }
  printReceipt(receipt, write, options.json);
  return 0;
}


function effectSummary(action) {
  if (action.execution.mode === "read-only") return "read-only";
  return [action.effects.creates.length ? "creates" : null, action.effects.updates.length ? "updates" : null].filter(Boolean).join(", ") || "plan-only";
}


function publicAction(action) {
  return {
    id: action.id,
    invocation: actionInvocation(action.id),
    title: action.title,
    summary: action.summary,
    version: action.version,
    docs: action.docs,
    methodConfidence: action.methodConfidence,
    readiness: action.readiness,
    lifecycle: action.lifecycle,
    inputs: action.inputs,
    outputs: action.outputs,
    effects: action.effects,
    execution: action.execution,
    success: action.success,
    dependencies: action.dependencies,
    digests: action.digests,
  };
}


function parseJsonFlag(args, label) {
  if (args.length === 0) return false;
  if (args.length === 1 && args[0] === "--json") return true;
  throw new CliError(`${label} accepts only --json`);
}


function resolveDiscoveredAction(repoRoot, actionId) {
  const discovered = discoverActions(repoRoot);
  const action = discovered.actions.find((candidate) => candidate.id === actionId);
  if (action) return action;
  const finding = discovered.errors
    .filter((error) => error.id === actionId || actionId.startsWith(`${error.id}/`))
    .sort((left, right) => right.id.length - left.id.length)[0];
  if (finding) throw new CliError(`invalid Action ${actionId}: ${finding.error}`);
  throw new CliError(`unknown Action: ${actionId}; run ./trellis list or ./trellis --help`);
}


function actionUsage(action) {
  const invocation = actionInvocation(action.id);
  const inputExample = action.inputs.map((input) => `--${input.name} <${input.type}>`).join(" ");
  const direct = `./trellis ${invocation}${inputExample ? ` -- ${inputExample}` : ""}`;
  return [
    "Examples:",
    `  ${direct}`,
    `  ./trellis show ${invocation}`,
    `  ./trellis test ${invocation}`,
    "",
    `${action.title} (${action.id})`,
    action.summary,
    `Mode: ${action.execution.mode === "read-only" ? "runs immediately with local reads only" : "creates a local plan for review; it does not apply changes"}.`,
    `Inputs: ${action.inputs.map((input) => `--${input.name} <${input.type}>${input.required ? "" : " (optional)"} — ${input.description}`).join("; ") || "none"}`,
    action.execution.mode === "plan-apply" ? `Apply a reviewed plan: ./trellis apply ${invocation} --plan <sha256>` : "",
  ].filter((line, index, lines) => line !== "" || index < lines.length - 1).join("\n");
}


function showAction(action, args, write) {
  const json = parseJsonFlag(args, "show");
  if (json) {
    write(JSON.stringify(publicAction(action), null, 2));
    return 0;
  }
  write(`${action.title} (${action.id})`);
  write(action.summary);
  write(`Lifecycle: ${action.lifecycle.status}${action.lifecycle.reason ? ` — ${action.lifecycle.reason}` : ""}${action.lifecycle.replacement ? `; replacement: ${action.lifecycle.replacement}` : ""}`);
  write(`Method confidence: ${action.methodConfidence.status}`);
  write(`Method basis: ${action.methodConfidence.basis.join("; ")}`);
  write(`Review triggers: ${action.methodConfidence.reviewTriggers.join("; ")}`);
  write(`Implementation readiness: ${action.readiness.status}`);
  write(`Readiness evidence: ${action.readiness.evidence.join("; ") || "none recorded"}`);
  if (action.readiness.validatedAt) write(`Validated: ${action.readiness.validatedAt} on ${action.readiness.validatedOn.join(", ")}`);
  write(`Mode: ${action.execution.mode}`);
  write(`Reads: ${action.effects.reads.map(stableJson).join(", ") || "none"}`);
  write(`Creates: ${action.effects.creates.map(stableJson).join(", ") || "none"}`);
  write(`Updates: ${action.effects.updates.map(stableJson).join(", ") || "none"}`);
  write(`Inputs: ${action.inputs.map((input) => `--${input.name} <${input.type}>${input.required ? "" : " (optional)"}${Object.hasOwn(input, "default") ? ` default=${stableJson(input.default)}` : ""}${input.examples ? ` examples=${stableJson(input.examples)}` : ""} — ${input.description}`).join("; ") || "none"}`);
  write(`Outputs: ${action.outputs.map((output) => `${output.name} <${output.type}>${output.path ? ` path=${output.path}` : ""} — ${output.description}`).join("; ") || "none"}`);
  write(`Dependencies: ${action.dependencies.map((dependency) => `${dependency.name}@${dependency.version}`).join(", ") || "none"}`);
  write(`Bounds: ${action.execution.timeoutMs}ms; ${action.execution.maxOutputBytes} stdout bytes; receipt ${action.execution.receipt}`);
  write(`Success: ${action.success.postconditions.join("; ")}`);
  write(`Docs: ${action.docs}`);
  const invocation = actionInvocation(action.id);
  if (action.execution.mode === "read-only") write(`Run: ./trellis ${invocation} -- [named inputs]`);
  else {
    write(`Plan: ./trellis ${invocation} -- [named inputs]`);
    write(`Review: ./trellis show-plan ${invocation} --plan <plan-sha256>`);
    write(`Apply: ./trellis apply ${invocation} --plan <plan-sha256>`);
  }
  write(`Test: ./trellis test ${invocation}`);
  return 0;
}


function testAction(action, args, injected, write, writeError) {
  if (args.length) throw new CliError("test accepts an Action path and no options");
  assertExecutionNode();
  validateSource(action, { includeTest: true });
  const dependencies = dependencyDirectories(action);
  const effects = { reads: [], creates: [], updates: [], temporary: [] };
  const testsRoot = ensurePrivateDirectory(
    action.repoRoot,
    path.join(requireScratchRoot(action.repoRoot), "tests"),
    "private test state",
  );
  const testRoot = ensurePrivateDirectory(
    action.repoRoot,
    path.join(testsRoot, `test-${randomBytes(16).toString("hex")}`),
    "private Action test directory",
  );
  try {
    const nodeArgs = hardenedNodeArgs(action, effects, dependencies, { test: true, testRoot });
    nodeArgs.push(action.test);
    const result = execute(action, nodeArgs, effects, dependencies, injected, { test: true, testRoot });
    if (result.stdout) write(result.stdout.trimEnd());
    if (result.stderr) writeError(result.stderr.trimEnd());
    const status = result.status ?? 1;
    if (status === 0) write(`Trellis test runtime: Node ${process.versions.node}`);
    return status;
  } finally {
    rmSync(testRoot, { recursive: true, force: true });
  }
}


function invokeAction(action, args, injected, write, { command = "direct" } = {}) {
  assertExecutionNode();
  const options = executionOptions(args, { planRequired: command === "apply" });
  assertRunnable(action, options);
  if (command === "apply") {
    if (action.execution.mode !== "plan-apply") throw new CliError(`${action.id} is read-only and cannot apply a plan`);
    return applyPlan(action, options, write, injected);
  }
  const values = parseNamedInputs(options.inputs, action);
  const effects = resolveEffects(action, values);
  if (action.execution.mode === "read-only") {
    if (command === "plan") throw new CliError(`${action.id} is read-only; invoke it directly with ./trellis ${actionInvocation(action.id)}`);
    return runReadOnly(action, values, effects, options, injected, write);
  }
  return createPlan(action, values, effects, options, injected, write);
}


export async function main(argv, injected = {}) {
  const repoRoot = realpathSync(path.resolve(injected.repoRoot ?? DEFAULT_REPO_ROOT));
  const write = injected.write ?? console.log;
  const writeError = injected.writeError ?? console.error;
  const tokens = [...argv];
  if (tokens.length === 0) {
    write(usage());
    return 0;
  }
  const command = tokens.shift();
  if (command === "-h" || command === "--help") {
    if (tokens.length) throw new CliError("--help takes no arguments at the root; use ./trellis help <command>");
    write(fullUsage());
    return 0;
  }
  if (command === "--version") {
    if (tokens.length) throw new CliError("--version takes no arguments");
    write(`trellis ${TOOL_VERSION}`);
    return 0;
  }

  if (!MANAGEMENT_COMMANDS.has(command)) {
    const parsed = splitActionPath([command, ...tokens], "invoke");
    const action = resolveDiscoveredAction(repoRoot, parsed.id);
    if (contextualHelpIndex(parsed.rest) !== -1) {
      if (parsed.rest.length !== 1) throw new CliError("Action --help cannot be combined with runner options or inputs");
      write(actionUsage(action));
      return 0;
    }
    return invokeAction(action, parsed.rest, injected, write);
  }

  const args = tokens;
  if (contextualHelpIndex(args) !== -1) {
    write(commandUsage(command));
    return 0;
  }
  if (command === "help") {
    if (args.length === 0) write(fullUsage());
    else if (args.length === 1 && MANAGEMENT_COMMANDS.has(args[0])) write(commandUsage(args[0]));
    else {
      const actionId = actionIdFromSegments(args, "help Action path");
      write(actionUsage(resolveDiscoveredAction(repoRoot, actionId)));
    }
    return 0;
  }
  if (command === "version") {
    if (args.length) throw new CliError("version takes no arguments");
    write(`trellis ${TOOL_VERSION}`);
    return 0;
  }
  if (command === "run") throw new CliError(commandUsage("run"));
  if (command === "list") {
    const json = parseJsonFlag(args, "list");
    const result = discoverActions(repoRoot);
    if (json) write(JSON.stringify({ actions: result.actions.map(publicAction), errors: result.errors }, null, 2));
    else {
      if (!result.actions.length) write("No valid Actions are available in this work folder.");
      for (const action of result.actions) write(`${actionInvocation(action.id).padEnd(36)} ${action.title} [${action.lifecycle.status}; ${action.readiness.status}; ${effectSummary(action)}]`);
      for (const error of result.errors) writeError(`invalid ${error.id}: ${error.error}`);
    }
    return result.errors.length ? 1 : 0;
  }
  if (command === "doctor") {
    const json = parseJsonFlag(args, "doctor");
    const discovered = discoverActions(repoRoot);
    const support = nodeSupport();
    const checks = [
      { check: "Node discovery runtime", ok: support.discovery, detail: process.versions.node },
      { check: "Node hardened execution runtime", ok: support.execution, detail: `requires ${NODE_EXECUTION_RANGE}` },
      { check: "Action manifests", ok: discovered.errors.length === 0, detail: `${discovered.actions.length} valid; ${discovered.errors.length} invalid` },
      { check: "Local-only boundary", ok: true, detail: "Node permissions, import guard, source screening; not an OS network sandbox" },
    ];
    if (json) write(JSON.stringify({ status: checks.every((item) => item.ok) ? "ok" : "attention", checks, errors: discovered.errors }, null, 2));
    else for (const item of checks) write(`${item.ok ? "PASS" : "ATTENTION"}: ${item.check} — ${item.detail}`);
    return checks.every((item) => item.ok) ? 0 : 1;
  }
  if (command === "validate") {
    const parsed = splitActionPath(args, "validate", { optional: true });
    const json = parseJsonFlag(parsed.rest, "validate");
    const result = parsed.id
      ? (() => { try { return { actions: [resolveDiscoveredAction(repoRoot, parsed.id)], errors: [] }; } catch (error) { return { actions: [], errors: [{ id: parsed.id, error: error.message }] }; } })()
      : discoverActions(repoRoot);
    if (json) write(JSON.stringify({ status: result.errors.length ? "findings" : "ok", actions: result.actions.map((action) => action.id), errors: result.errors }, null, 2));
    else {
      for (const action of result.actions) write(`OK: ${action.id}`);
      for (const error of result.errors) writeError(`INVALID: ${error.id} — ${error.error}`);
    }
    return result.errors.length ? 1 : 0;
  }

  if (command === "scaffold") return scaffoldAction(args, repoRoot, write);
  const parsed = splitActionPath(args, command);
  const action = resolveDiscoveredAction(repoRoot, parsed.id);
  if (command === "show") return showAction(action, parsed.rest, write);
  if (command === "show-plan") return showPlan(action, parsed.rest, write);
  if (command === "test") return testAction(action, parsed.rest, injected, write, writeError);
  if (command === "plan" || command === "apply") return invokeAction(action, parsed.rest, injected, write, { command });
  throw new CliError(`unknown management command: ${command}`);
}


function scaffoldOptions(args) {
  const options = { apply: false, json: false, title: null };
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--apply") options.apply = true;
    else if (arg === "--json") options.json = true;
    else if (arg === "--title") {
      options.title = args[++index];
      if (!options.title) throw new CliError("--title requires a value");
    } else throw new CliError(`unknown scaffold option: ${arg}`);
  }
  return options;
}


function scaffoldFiles(actionId, title) {
  const run = `const result = {\n  schema: "trellis.action-result/v1",\n  status: "failed",\n  summary: "This Draft Action has not been implemented.",\n  outputs: [],\n  verification: [{ check: "implementation exists", ok: false }],\n};\nconsole.log(JSON.stringify(result));\n`;
  const test = `import assert from "node:assert/strict";\nimport test from "node:test";\n\ntest("replace the scaffold with representative tests", () => {\n  assert.fail("Draft Action is not implemented");\n});\n`;
  const invocation = actionInvocation(actionId);
  const docs = `# ${title}\n\n<!-- trellis-capture: action format=2 -->\n\nMethod confidence: Provisional — no recurrence evidence recorded yet.\n\nImplementation readiness: Untested.\n\nLifecycle: Draft.\n\n## Purpose\n\nDefine one local, mechanical outcome.\n\n## Use When\n\nDescribe the trigger and review conditions.\n\n## Inputs\n\nList named inputs.\n\n## Outputs\n\nDescribe the result without embedding source content in receipts.\n\n## Run\n\nFrom the work-folder root, run \`./trellis ${invocation}\` after implementation and focused tests.\n\n## Effects\n\nLocal reads only in this scaffold. Network, arbitrary environment, child processes, deletion, and direct Action writes are prohibited.\n\n## Success And Failure\n\nDefine observable postconditions and detectable failures.\n\n## Verification\n\nRun \`./trellis test ${invocation}\` with separate approval.\n`;
  const manifest = {
    format: 2,
    version: 1,
    id: actionId,
    title,
    summary: "Draft local Action; define one bounded mechanical result before use.",
    entrypoint: "run.mjs",
    test: "run.test.mjs",
    docs: `_handbook/actions/${actionId}.md`,
    methodConfidence: {
      status: "provisional",
      basis: ["Scaffolded for review; no recurrence evidence recorded."],
      reviewTriggers: ["Review when the intended inputs, outcome, or local effects change."],
    },
    readiness: { status: "untested", evidence: [], validatedAt: null, validatedOn: [] },
    lifecycle: { status: "draft", reason: "Implementation and representative tests are incomplete.", replacement: null },
    inputs: [],
    outputs: [],
    effects: { reads: [], creates: [], updates: [], temporary: [] },
    execution: { mode: "read-only", receipt: "json-v1", timeoutMs: 60000, maxOutputBytes: 1048576 },
    success: { postconditions: ["The implemented Action reports an observable pass or failure condition."] },
    dependencies: [],
    digests: { entrypoint: hashBytes(run), test: hashBytes(test) },
  };
  return { docs, manifest, run, test };
}


function assertScaffoldPath(repoRoot, segments, actionDir, docsPath) {
  const actionsRoot = path.join(cliRoot(repoRoot), "actions");
  const docsRoot = path.join(repoRoot, "_handbook", "actions");
  for (const [root, pathSegments, label] of [
    [actionsRoot, segments, "Action path"],
    [docsRoot, [...segments.slice(0, -1), `${segments.at(-1)}.md`], "handbook path"],
  ]) {
    let current = root;
    if (existsSync(current)) {
      rejectSymlink(current, label);
      if (!lstatSync(current).isDirectory()) throw new CliError(`${label} root must be a directory`);
    }
    for (const [index, segment] of pathSegments.entries()) {
      if (!existsSync(current)) break;
      const entries = readdirSync(current, { withFileTypes: true });
      const folded = entries.filter((entry) => entry.name.toLowerCase() === segment.toLowerCase());
      if (folded.length > 1 || folded.length === 1 && folded[0].name !== segment) {
        throw new CliError(`${label} collides case-insensitively at segment: ${segment}`);
      }
      current = path.join(current, segment);
      if (!existsSync(current)) continue;
      rejectSymlink(current, label);
      const isLast = index === pathSegments.length - 1;
      if (!isLast && !lstatSync(current).isDirectory()) throw new CliError(`${label} parent is not a directory: ${segment}`);
      if (root === actionsRoot && !isLast) {
        const marker = readdirSync(current, { withFileTypes: true }).find((entry) => ACTION_FILES.has(entry.name));
        if (marker) throw new CliError(`Action leaf cannot contain nested scaffold path: ${segments.join("/")}`);
      }
    }
  }
  for (const [target, label] of [[actionDir, "scaffold Action directory"], [docsPath, "scaffold handbook page"]]) {
    if (!isWithin(target, repoRoot)) throw new CliError(`${label} escapes the work folder`);
    assertNoSymlinkComponents(repoRoot, target, label);
  }
}


function scaffoldAction(args, repoRoot, write) {
  const parsed = splitActionPath(args, "scaffold");
  const actionId = parsed.id;
  const segments = parsed.segments;
  const options = scaffoldOptions(parsed.rest);
  const title = nonemptyString(options.title, "scaffold --title");
  const files = scaffoldFiles(actionId, title);
  const actionDir = path.join(cliRoot(repoRoot), "actions", ...segments);
  const docsPath = path.join(repoRoot, files.manifest.docs);
  const preview = { status: options.apply ? "created" : "preview", action: actionId, files: [path.relative(repoRoot, docsPath), path.relative(repoRoot, path.join(actionDir, "action.json")), path.relative(repoRoot, path.join(actionDir, "run.mjs")), path.relative(repoRoot, path.join(actionDir, "run.test.mjs"))], manifest: files.manifest };
  if (options.apply) {
    if (existsSync(actionDir) || existsSync(docsPath)) throw new CliError("scaffold refuses to overwrite an existing Action or handbook page");
    assertScaffoldPath(repoRoot, segments, actionDir, docsPath);
    const directories = new Set();
    for (const target of [actionDir, path.dirname(docsPath)]) {
      let current = target;
      while (!existsSync(current)) {
        directories.add(current);
        current = path.dirname(current);
      }
    }
    const createdDirectories = [];
    const createdFiles = [];
    try {
      for (const directory of [...directories].sort((left, right) => left.split(path.sep).length - right.split(path.sep).length || compareText(left, right))) {
        mkdirSync(directory);
        createdDirectories.push(directory);
      }
      for (const [filename, content] of [
        [path.join(actionDir, "run.mjs"), files.run],
        [path.join(actionDir, "run.test.mjs"), files.test],
        [path.join(actionDir, "action.json"), `${JSON.stringify(files.manifest, null, 2)}\n`],
        [docsPath, files.docs],
      ]) {
        writeFileSync(filename, content, { flag: "wx" });
        createdFiles.push(filename);
      }
    } catch (error) {
      const cleanupErrors = [];
      for (const filename of createdFiles.reverse()) {
        try { rmSync(filename, { force: true }); } catch (cleanup) { cleanupErrors.push(`${path.relative(repoRoot, filename)}: ${cleanup.message}`); }
      }
      for (const directory of createdDirectories.reverse()) {
        try { rmSync(directory); } catch (cleanup) { cleanupErrors.push(`${path.relative(repoRoot, directory)}: ${cleanup.message}`); }
      }
      if (cleanupErrors.length) throw new CliError(`scaffold failed: ${error.message}; cleanup incomplete (${cleanupErrors.join("; ")})`);
      throw new CliError(`scaffold failed and left no created files: ${error.message}`);
    }
  }
  if (options.json) write(JSON.stringify(preview, null, 2));
  else {
    write(`${options.apply ? "Created" : "Would create"} Draft+Untested Action: ${actionId}`);
    for (const filename of preview.files) write(`  ${filename}`);
    if (!options.apply) write("No files changed. Add --apply to create this skeleton.");
  }
  return 0;
}
