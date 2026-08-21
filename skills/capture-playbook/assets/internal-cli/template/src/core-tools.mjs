import { createHash, randomBytes } from "node:crypto";
import {
  chmod,
  lstat,
  open,
  readFile,
  readdir,
  realpath,
  rename,
  rm,
} from "node:fs/promises";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";

const WRITE_OPERATIONS = new Set(["text.replace", "json.set"]);
const READ_OPERATIONS = new Set(["file.hash", "files.compare"]);
const PORTABLE_ID = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/u;
const SHA256 = /^[a-f0-9]{64}$/u;
const MAX_INPUT_BYTES = 16 * 1024 * 1024;

export class TrellisToolError extends Error {
  constructor(message, code = "trellis.tool.invalid") {
    super(message);
    this.name = "TrellisToolError";
    this.code = code;
  }
}

export function hashBytes(value) {
  return createHash("sha256").update(value).digest("hex");
}

export function isWriteOperation(operation) {
  return WRITE_OPERATIONS.has(operation);
}

export function validateToolManifest(value, expectedPlaybook = null, expectedTool = null) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new TrellisToolError("tool.json must contain one object");
  }
  const allowed = new Set(["format", "playbook", "id", "title", "description", "operation"]);
  const unknown = Object.keys(value).filter((key) => !allowed.has(key));
  if (unknown.length > 0) {
    throw new TrellisToolError(`tool.json has unsupported fields: ${unknown.join(", ")}`);
  }
  if (value.format !== 1) {
    throw new TrellisToolError("tool.json format must be 1");
  }
  for (const field of ["playbook", "id"]) {
    if (typeof value[field] !== "string" || !PORTABLE_ID.test(value[field])) {
      throw new TrellisToolError(`${field} must be a portable lowercase identifier`);
    }
  }
  for (const field of ["title", "description"]) {
    if (typeof value[field] !== "string" || !/\S/u.test(value[field])) {
      throw new TrellisToolError(`${field} must be a non-blank string`);
    }
  }
  if (!READ_OPERATIONS.has(value.operation) && !WRITE_OPERATIONS.has(value.operation)) {
    throw new TrellisToolError(`unsupported operation: ${String(value.operation)}`);
  }
  if (expectedPlaybook !== null && value.playbook !== expectedPlaybook) {
    throw new TrellisToolError("tool.json playbook does not match its directory");
  }
  if (expectedTool !== null && value.id !== expectedTool) {
    throw new TrellisToolError("tool.json id does not match its directory");
  }
  return Object.freeze({ ...value });
}

function assertArgumentSet(args, required, optional = []) {
  const requiredSet = new Set(required);
  const allowed = new Set([...required, ...optional]);
  const missing = required.filter((key) => typeof args[key] !== "string" || args[key].length === 0);
  if (missing.length > 0) {
    throw new TrellisToolError(`missing argument${missing.length === 1 ? "" : "s"}: ${missing.join(", ")}`);
  }
  const unknown = Object.keys(args).filter((key) => !allowed.has(key));
  if (unknown.length > 0) {
    throw new TrellisToolError(`unsupported argument${unknown.length === 1 ? "" : "s"}: ${unknown.join(", ")}`);
  }
  for (const key of requiredSet) {
    if (args[key].includes("\u0000")) {
      throw new TrellisToolError(`argument ${key} contains NUL`);
    }
  }
}

function assertPortableRelativePath(value) {
  if (typeof value !== "string" || value.length === 0) {
    throw new TrellisToolError("file path must be a non-empty string");
  }
  if (value.includes("\u0000") || value.includes("\\") || isAbsolute(value)) {
    throw new TrellisToolError(`unsafe file path: ${value}`);
  }
  const parts = value.split("/");
  if (parts.some((part) => part === "" || part === "." || part === "..")) {
    throw new TrellisToolError(`unsafe file path: ${value}`);
  }
  return parts;
}

function isInside(parent, target) {
  const fromParent = relative(parent, target);
  return fromParent === "" || (!fromParent.startsWith(`..${sep}`) && fromParent !== ".." && !isAbsolute(fromParent));
}

async function assertNoSymlinkPath(root, parts, allowMissingLeaf = false) {
  let current = root;
  for (let index = 0; index < parts.length; index += 1) {
    current = join(current, parts[index]);
    let metadata;
    try {
      metadata = await lstat(current);
    } catch (error) {
      if (allowMissingLeaf && error?.code === "ENOENT" && index === parts.length - 1) {
        return;
      }
      throw error;
    }
    if (metadata.isSymbolicLink()) {
      throw new TrellisToolError(`refusing symlink path: ${parts.slice(0, index + 1).join("/")}`);
    }
  }
}

export async function resolveProjectFile(workRoot, value) {
  const root = await realpath(resolve(workRoot));
  const parts = assertPortableRelativePath(value);
  const target = resolve(root, ...parts);
  if (!isInside(root, target)) {
    throw new TrellisToolError(`path escapes the work root: ${value}`);
  }
  await assertNoSymlinkPath(root, parts);
  const metadata = await lstat(target);
  if (!metadata.isFile()) {
    throw new TrellisToolError(`path is not a regular file: ${value}`);
  }
  if (metadata.size > MAX_INPUT_BYTES) {
    throw new TrellisToolError(`file exceeds ${MAX_INPUT_BYTES} bytes: ${value}`);
  }
  return { root, target, metadata };
}

async function snapshot(workRoot, value) {
  const resolved = await resolveProjectFile(workRoot, value);
  const bytes = await readFile(resolved.target);
  return {
    ...resolved,
    path: value,
    bytes,
    sha256: hashBytes(bytes),
  };
}

function result(operation, outputs, verification) {
  return {
    schema: "trellis.tool-result/v1",
    status: "ok",
    operation,
    outputs,
    verification,
  };
}

export async function runReadOperation(operation, args, workRoot) {
  if (operation === "file.hash") {
    assertArgumentSet(args, ["file"]);
    const file = await snapshot(workRoot, args.file);
    return result(
      operation,
      { file: file.path, sha256: file.sha256, bytes: file.bytes.length },
      [{ check: "regular local file", ok: true }, { check: "SHA-256 computed", ok: true }],
    );
  }

  if (operation === "files.compare") {
    assertArgumentSet(args, ["left", "right"]);
    const [left, right] = await Promise.all([
      snapshot(workRoot, args.left),
      snapshot(workRoot, args.right),
    ]);
    return result(
      operation,
      {
        left: { file: left.path, sha256: left.sha256, bytes: left.bytes.length },
        right: { file: right.path, sha256: right.sha256, bytes: right.bytes.length },
        equal: left.bytes.equals(right.bytes),
      },
      [{ check: "both inputs are regular local files", ok: true }],
    );
  }

  throw new TrellisToolError(`operation requires plan/apply rather than run: ${operation}`);
}

function countOccurrences(text, needle) {
  if (needle.length === 0) {
    throw new TrellisToolError("from must not be empty");
  }
  let count = 0;
  let cursor = 0;
  while (true) {
    const found = text.indexOf(needle, cursor);
    if (found === -1) return count;
    count += 1;
    cursor = found + needle.length;
  }
}

function decodePointerSegment(segment) {
  if (/~(?:[^01]|$)/u.test(segment)) {
    throw new TrellisToolError("JSON Pointer contains an invalid escape");
  }
  const decoded = segment.replaceAll("~1", "/").replaceAll("~0", "~");
  if (["__proto__", "prototype", "constructor"].includes(decoded)) {
    throw new TrellisToolError("JSON Pointer uses a prohibited segment");
  }
  return decoded;
}

function parseJsonPointer(pointer) {
  if (pointer === "" || !pointer.startsWith("/")) {
    throw new TrellisToolError("pointer must select an existing non-root value");
  }
  return pointer.slice(1).split("/").map(decodePointerSegment);
}

function setExistingJsonValue(document, segments, value) {
  let current = document;
  for (const segment of segments.slice(0, -1)) {
    if (Array.isArray(current)) {
      if (!/^0$|^[1-9]\d*$/u.test(segment) || Number(segment) >= current.length) {
        throw new TrellisToolError(`pointer segment does not exist: ${segment}`);
      }
      current = current[Number(segment)];
    } else if (current !== null && typeof current === "object" && Object.hasOwn(current, segment)) {
      current = current[segment];
    } else {
      throw new TrellisToolError(`pointer segment does not exist: ${segment}`);
    }
  }

  const leaf = segments.at(-1);
  if (Array.isArray(current)) {
    if (!/^0$|^[1-9]\d*$/u.test(leaf) || Number(leaf) >= current.length) {
      throw new TrellisToolError(`pointer target does not exist: ${leaf}`);
    }
    const previous = current[Number(leaf)];
    current[Number(leaf)] = value;
    return previous;
  }
  if (current !== null && typeof current === "object" && Object.hasOwn(current, leaf)) {
    const previous = current[leaf];
    current[leaf] = value;
    return previous;
  }
  throw new TrellisToolError(`pointer target does not exist: ${leaf}`);
}

function jsonFormatting(text) {
  const newline = text.includes("\r\n") ? "\r\n" : "\n";
  const indentation = text.match(/\r?\n([ \t]+)\S/u)?.[1] ?? "  ";
  const trailingNewline = text.endsWith("\n");
  return { newline, indentation, trailingNewline };
}

function planPayload(operation, file, afterBytes, summary, verification) {
  return {
    schema: "trellis.tool-plan/v1",
    status: "planned",
    operation,
    file: file.path,
    before: { sha256: file.sha256, bytes: file.bytes.length },
    after: { sha256: hashBytes(afterBytes), bytes: afterBytes.length },
    summary,
    verification,
    _private: { target: file.target, metadata: file.metadata, afterBytes },
  };
}

export async function planWriteOperation(operation, args, workRoot) {
  if (operation === "text.replace") {
    assertArgumentSet(args, ["file", "from", "to"]);
    const file = await snapshot(workRoot, args.file);
    const text = file.bytes.toString("utf8");
    if (!Buffer.from(text, "utf8").equals(file.bytes)) {
      throw new TrellisToolError("text.replace requires valid UTF-8 input");
    }
    const occurrences = countOccurrences(text, args.from);
    if (occurrences !== 1) {
      throw new TrellisToolError(`from must occur exactly once; found ${occurrences}`);
    }
    const afterText = text.replace(args.from, args.to);
    const afterBytes = Buffer.from(afterText, "utf8");
    return planPayload(
      operation,
      file,
      afterBytes,
      { replacementCount: 1, changed: !afterBytes.equals(file.bytes) },
      [{ check: "source text occurs exactly once", ok: true }],
    );
  }

  if (operation === "json.set") {
    assertArgumentSet(args, ["file", "pointer", "value"]);
    const file = await snapshot(workRoot, args.file);
    const text = file.bytes.toString("utf8");
    if (!Buffer.from(text, "utf8").equals(file.bytes)) {
      throw new TrellisToolError("json.set requires valid UTF-8 input");
    }
    let document;
    let nextValue;
    try {
      document = JSON.parse(text);
    } catch (error) {
      throw new TrellisToolError(`input is not valid JSON: ${error.message}`);
    }
    try {
      nextValue = JSON.parse(args.value);
    } catch (error) {
      throw new TrellisToolError(`value is not valid JSON: ${error.message}`);
    }
    const segments = parseJsonPointer(args.pointer);
    const previous = setExistingJsonValue(document, segments, nextValue);
    const formatting = jsonFormatting(text);
    let afterText = JSON.stringify(document, null, formatting.indentation);
    if (formatting.newline !== "\n") afterText = afterText.replaceAll("\n", formatting.newline);
    if (formatting.trailingNewline) afterText += formatting.newline;
    const afterBytes = Buffer.from(afterText, "utf8");
    return planPayload(
      operation,
      file,
      afterBytes,
      { pointer: args.pointer, previous, next: nextValue, changed: !afterBytes.equals(file.bytes) },
      [{ check: "input parsed as JSON", ok: true }, { check: "pointer target exists", ok: true }],
    );
  }

  throw new TrellisToolError(`operation is read-only and must use run: ${operation}`);
}

async function atomicReplace(target, bytes, mode) {
  const parent = dirname(target);
  const temporary = join(parent, `.${target.split(sep).at(-1)}.trellis-${process.pid}-${randomBytes(8).toString("hex")}`);
  let handle;
  try {
    handle = await open(temporary, "wx", mode & 0o777);
    await handle.writeFile(bytes);
    await handle.sync();
    await handle.close();
    handle = null;
    await chmod(temporary, mode & 0o777);
    await rename(temporary, target);
  } finally {
    if (handle !== null) await handle.close().catch(() => undefined);
    await rm(temporary, { force: true }).catch(() => undefined);
  }
}

export async function applyWriteOperation(operation, args, workRoot, expectedSha256) {
  if (typeof expectedSha256 !== "string" || !SHA256.test(expectedSha256)) {
    throw new TrellisToolError("apply requires expectSha256=<64 lowercase hex characters>");
  }
  const plan = await planWriteOperation(operation, args, workRoot);
  if (plan.before.sha256 !== expectedSha256) {
    throw new TrellisToolError(
      `file changed since review: expected ${expectedSha256}, found ${plan.before.sha256}`,
      "trellis.tool.drift",
    );
  }
  if (plan.before.sha256 === plan.after.sha256) {
    return {
      schema: "trellis.tool-receipt/v1",
      status: "no-change",
      operation,
      file: plan.file,
      before: plan.before,
      after: plan.after,
      verification: [...plan.verification, { check: "no write required", ok: true }],
    };
  }
  await atomicReplace(plan._private.target, plan._private.afterBytes, plan._private.metadata.mode);
  const after = await snapshot(workRoot, plan.file);
  if (after.sha256 !== plan.after.sha256) {
    throw new TrellisToolError("post-write hash does not match the reviewed plan", "trellis.tool.verify-failed");
  }
  return {
    schema: "trellis.tool-receipt/v1",
    status: "applied",
    operation,
    file: plan.file,
    before: plan.before,
    after: plan.after,
    verification: [...plan.verification, { check: "reviewed bytes written", ok: true }],
  };
}

export async function listToolManifests(cliRoot) {
  const toolsRoot = join(cliRoot, "tools");
  let playbooks;
  try {
    playbooks = await readdir(toolsRoot, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
  const tools = [];
  for (const playbookEntry of playbooks) {
    if (playbookEntry.isSymbolicLink()) {
      throw new TrellisToolError(`tools/ contains a symlink: ${playbookEntry.name}`);
    }
    if (!playbookEntry.isDirectory() || !PORTABLE_ID.test(playbookEntry.name)) continue;
    const playbookPath = join(toolsRoot, playbookEntry.name);
    const toolEntries = await readdir(playbookPath, { withFileTypes: true });
    for (const toolEntry of toolEntries) {
      if (toolEntry.isSymbolicLink()) {
        throw new TrellisToolError(`tool group contains a symlink: ${playbookEntry.name}/${toolEntry.name}`);
      }
      if (!toolEntry.isDirectory() || !PORTABLE_ID.test(toolEntry.name)) continue;
      const toolPath = join(playbookPath, toolEntry.name);
      const entries = await readdir(toolPath, { withFileTypes: true });
      if (entries.length !== 1 || entries[0].name !== "tool.json" || !entries[0].isFile()) {
        throw new TrellisToolError(`tool folder must contain only tool.json: ${playbookEntry.name}/${toolEntry.name}`);
      }
      const manifest = validateToolManifest(
        JSON.parse(await readFile(join(toolPath, "tool.json"), "utf8")),
        playbookEntry.name,
        toolEntry.name,
      );
      tools.push(manifest);
    }
  }
  return tools.sort((left, right) => `${left.playbook}/${left.id}`.localeCompare(`${right.playbook}/${right.id}`));
}
