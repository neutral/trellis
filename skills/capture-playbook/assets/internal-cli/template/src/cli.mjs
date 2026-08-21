import { lstat, readFile, readdir, realpath } from "node:fs/promises";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import {
  TrellisToolError,
  applyWriteOperation,
  isWriteOperation,
  listToolManifests,
  planWriteOperation,
  runReadOperation,
  validateToolManifest,
} from "./core-tools.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const cliRoot = resolve(here, "..");
const PORTABLE_ID = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/u;

function isInside(parent, target) {
  const fromParent = relative(parent, target);
  return fromParent === "" || (!fromParent.startsWith(`..${sep}`) && fromParent !== ".." && !isAbsolute(fromParent));
}

function printUsage() {
  console.log(`Trellis private Playbook CLI

Usage:
  trellis list
  trellis show <playbook> <tool>
  trellis run <playbook> <tool> -- key=value ...
  trellis plan <playbook> <tool> -- key=value ...
  trellis apply <playbook> <tool> -- expectSha256=<sha256> key=value ...

Tools select fixed local-file operations. The Playbook documents the exact command and approval boundary.`);
}

function parseArguments(values) {
  const divider = values.indexOf("--");
  const commandValues = divider === -1 ? values : values.slice(0, divider);
  const inputValues = divider === -1 ? [] : values.slice(divider + 1);
  const inputs = {};
  for (const value of inputValues) {
    const separator = value.indexOf("=");
    if (separator <= 0) throw new TrellisToolError(`input must use key=value: ${value}`);
    const key = value.slice(0, separator);
    const item = value.slice(separator + 1);
    if (!/^[A-Za-z][A-Za-z0-9]*$/u.test(key)) throw new TrellisToolError(`invalid input name: ${key}`);
    if (Object.hasOwn(inputs, key)) throw new TrellisToolError(`duplicate input: ${key}`);
    inputs[key] = item;
  }
  return { commandValues, inputs };
}

async function loadConfiguration() {
  let config;
  const configPath = join(cliRoot, "trellis.json");
  try {
    const metadata = await lstat(configPath);
    if (metadata.isSymbolicLink() || !metadata.isFile()) {
      throw new TrellisToolError("trellis.json must be a regular file, not a symlink");
    }
    config = JSON.parse(await readFile(configPath, "utf8"));
  } catch (error) {
    throw new TrellisToolError(`cannot read trellis.json: ${error.message}`);
  }
  if (
    config === null ||
    typeof config !== "object" ||
    Array.isArray(config) ||
    config.format !== 1 ||
    typeof config.workRoot !== "string" ||
    config.workRoot.length === 0
  ) {
    throw new TrellisToolError("trellis.json must declare format 1 and a relative workRoot");
  }
  if (isAbsolute(config.workRoot) || config.workRoot.includes("\u0000")) {
    throw new TrellisToolError("trellis.json workRoot must be a project-local relative path");
  }
  const workRoot = await realpath(resolve(cliRoot, config.workRoot));
  const cliPhysical = await realpath(cliRoot);
  if (!isInside(workRoot, cliPhysical)) {
    throw new TrellisToolError("_cli must remain inside its configured work root");
  }
  return { workRoot };
}

async function loadTool(playbook, tool) {
  if (!PORTABLE_ID.test(playbook) || !PORTABLE_ID.test(tool)) {
    throw new TrellisToolError("playbook and tool must be portable lowercase identifiers");
  }
  const toolDirectory = join(cliRoot, "tools", playbook, tool);
  const manifestPath = join(toolDirectory, "tool.json");
  let manifest;
  try {
    for (const segment of [
      join(cliRoot, "tools"),
      join(cliRoot, "tools", playbook),
      toolDirectory,
      manifestPath,
    ]) {
      const metadata = await lstat(segment);
      if (metadata.isSymbolicLink()) {
        throw new TrellisToolError(`internal tool path must not contain a symlink: ${segment}`);
      }
    }
    const entries = await readdir(toolDirectory, { withFileTypes: true });
    if (entries.length !== 1 || entries[0].name !== "tool.json" || !entries[0].isFile()) {
      throw new TrellisToolError("an internal tool folder must contain only tool.json");
    }
    manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  } catch (error) {
    throw new TrellisToolError(`cannot read ${playbook}/${tool}/tool.json: ${error.message}`);
  }
  return validateToolManifest(manifest, playbook, tool);
}

function publicPlan(plan, manifest) {
  const { _private: ignored, ...visible } = plan;
  return { ...visible, tool: { playbook: manifest.playbook, id: manifest.id, title: manifest.title } };
}

function writeJson(value) {
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
}

export async function main(argv) {
  try {
    const { commandValues, inputs } = parseArguments(argv);
    const [command, playbook, tool, ...extra] = commandValues;

    if (command === undefined || command === "help" || command === "--help" || command === "-h") {
      printUsage();
      return 0;
    }

    if (command === "list") {
      if (commandValues.length !== 1 || Object.keys(inputs).length !== 0) {
        throw new TrellisToolError("list accepts no arguments");
      }
      const tools = await listToolManifests(cliRoot);
      writeJson({ schema: "trellis.tool-list/v1", tools });
      return 0;
    }

    if (!["show", "run", "plan", "apply"].includes(command)) {
      throw new TrellisToolError(`unknown command: ${command}`);
    }
    if (playbook === undefined || tool === undefined || extra.length !== 0) {
      throw new TrellisToolError(`${command} requires <playbook> <tool>`);
    }

    const manifest = await loadTool(playbook, tool);
    if (command === "show") {
      if (Object.keys(inputs).length !== 0) throw new TrellisToolError("show accepts no key=value inputs");
      writeJson({ schema: "trellis.tool-description/v1", tool: manifest });
      return 0;
    }

    const { workRoot } = await loadConfiguration();
    if (command === "run") {
      if (isWriteOperation(manifest.operation)) {
        throw new TrellisToolError("write operations require plan and a separately reviewed apply");
      }
      const output = await runReadOperation(manifest.operation, inputs, workRoot);
      writeJson({ ...output, tool: { playbook, id: tool } });
      return 0;
    }

    if (!isWriteOperation(manifest.operation)) {
      throw new TrellisToolError("read-only operations use run rather than plan/apply");
    }
    if (command === "plan") {
      const plan = await planWriteOperation(manifest.operation, inputs, workRoot);
      writeJson(publicPlan(plan, manifest));
      return 0;
    }

    const expectedSha256 = inputs.expectSha256;
    const operationInputs = { ...inputs };
    delete operationInputs.expectSha256;
    const receipt = await applyWriteOperation(
      manifest.operation,
      operationInputs,
      workRoot,
      expectedSha256,
    );
    writeJson({ ...receipt, tool: { playbook, id: tool } });
    return 0;
  } catch (error) {
    const code = error instanceof TrellisToolError ? error.code : "trellis.tool.failure";
    process.stderr.write(`${JSON.stringify({ schema: "trellis.tool-error/v1", code, message: error.message })}\n`);
    return 2;
  }
}
