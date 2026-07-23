import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { chmodSync, existsSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, statSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test, { afterEach } from "node:test";
import { fileURLToPath } from "node:url";

import { CliError, NODE_EXECUTION_RANGE, discoverActions, loadAction, main, nodeSupport, usage } from "../src/cli.mjs";


const TEMP_ROOTS = new Set();
const GUARD_SOURCE = readFileSync(fileURLToPath(new URL("../src/guard.mjs", import.meta.url)), "utf8");
const ASSET_ROOT = fileURLToPath(new URL("../../../", import.meta.url));


function temporaryPath(prefix) {
  const root = path.join(tmpdir(), `${prefix}-${process.pid}-${Math.random().toString(16).slice(2)}`);
  TEMP_ROOTS.add(root);
  return root;
}


afterEach(() => {
  for (const root of TEMP_ROOTS) rmSync(root, { recursive: true, force: true });
  TEMP_ROOTS.clear();
});


function digest(text) {
  return `sha256:${createHash("sha256").update(text).digest("hex")}`;
}


function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}


function assertReceiptHash(receipt) {
  const { receipt: identifier, ...payload } = receipt;
  assert.equal(identifier, digest(canonical(payload)));
}


function fixture(overrides = {}) {
  const root = temporaryPath("trellis-action-cli");
  const id = overrides.id || "check-links";
  const cliRoot = path.join(root, "_handbook", "_cli");
  const scratchRoot = path.join(root, "_handbook", "_scratch");
  const actionDir = path.join(cliRoot, "actions", id);
  const docs = `_handbook/actions/${id}.md`;
  mkdirSync(actionDir, { recursive: true });
  mkdirSync(path.join(cliRoot, "src"), { recursive: true });
  mkdirSync(path.join(root, "_handbook", "actions"), { recursive: true });
  mkdirSync(scratchRoot, { recursive: true });
  mkdirSync(path.dirname(path.join(root, docs)), { recursive: true });
  writeFileSync(path.join(cliRoot, "package.json"), "{}\n");
  writeFileSync(path.join(cliRoot, "src", "guard.mjs"), GUARD_SOURCE);
  writeFileSync(path.join(scratchRoot, ".gitignore"), "*\n!.gitignore\n!README.md\n");
  writeFileSync(path.join(scratchRoot, "README.md"), "# Trellis scratch state\n");
  writeFileSync(path.join(root, docs), `# ${id}\n`);
  const run = overrides.run ?? `console.log(JSON.stringify({schema:"trellis.action-result/v1",status:"ok",summary:"ok",outputs:[{name:"result",value:{ok:true}}],verification:[{check:"result",ok:true}]}));\n`;
  const actionTest = overrides.test ?? "// focused fixture test\n";
  writeFileSync(path.join(actionDir, "run.mjs"), run);
  writeFileSync(path.join(actionDir, "run.test.mjs"), actionTest);
  const manifest = {
    format: 2,
    version: 1,
    id,
    title: "Check links",
    summary: "Find broken local links.",
    entrypoint: "run.mjs",
    test: "run.test.mjs",
    docs,
    methodConfidence: { status: "provisional", basis: ["Observed twice."], reviewTriggers: ["Review when inputs change."] },
    readiness: { status: "tests-passed", evidence: ["Focused fixture test."], validatedAt: null, validatedOn: [] },
    lifecycle: { status: "active", reason: null, replacement: null },
    inputs: [],
    outputs: [{ name: "result", type: "json", description: "Structured result." }],
    effects: { reads: [], creates: [], updates: [], temporary: [] },
    execution: { mode: "read-only", receipt: "json-v1", timeoutMs: 60000, maxOutputBytes: 1048576 },
    success: { postconditions: ["The result is reported."] },
    dependencies: [],
    digests: { entrypoint: digest(run), test: digest(actionTest) },
    ...overrides.manifest,
  };
  writeFileSync(path.join(actionDir, "action.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  return { actionDir, id, manifest, root, run, test: actionTest };
}


test("no arguments are concise while root help documents discovery, execution, and creation", async () => {
  const lines = [];
  assert.equal(await main([], { write: (line) => lines.push(line) }), 0);
  assert.equal(lines.join("\n"), usage());
  const help = [];
  assert.equal(await main(["--help"], { write: (line) => help.push(line) }), 0);
  const helpLines = help[0].split("\n");
  const commandStart = helpLines.indexOf("Manage Actions:") + 1;
  const commandEnd = helpLines.indexOf("", commandStart);
  assert.deepEqual(helpLines.slice(commandStart, commandEnd), [
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
  ]);
  assert.match(help[0], /permanently local-only/);
});


test("execution accepts only reviewed Node 22 and Node 24 ranges", () => {
  assert.equal(NODE_EXECUTION_RANGE, ">=22.23.1 <23 || >=24.18.0 <25");
  for (const version of ["22.23.1", "22.24.0", "24.18.0", "24.99.0"]) {
    assert.equal(nodeSupport(version).execution, true, version);
  }
  for (const version of ["18.20.8", "22.23.0", "22.23.1-rc.1", "23.11.1", "24.17.9", "24.18.0-rc.1", "25.0.0", "26.0.0", "invalid"]) {
    assert.equal(nodeSupport(version).execution, false, version);
  }
  assert.equal(nodeSupport("17.9.1").discovery, false);
  assert.equal(nodeSupport("18.0.0").discovery, true);
  assert.equal(nodeSupport("invalid").discovery, false);
});


test("list reports a malformed Action without hiding healthy Actions", async () => {
  const { root } = fixture();
  const broken = path.join(root, "_handbook", "_cli", "actions", "broken");
  mkdirSync(broken);
  writeFileSync(path.join(broken, "action.json"), "{not json\n");
  writeFileSync(path.join(broken, "run.mjs"), "\n");
  writeFileSync(path.join(broken, "run.test.mjs"), "\n");
  const lines = [];
  const errors = [];
  assert.equal(await main(["list"], { repoRoot: root, write: (line) => lines.push(line), writeError: (line) => errors.push(line) }), 1);
  assert.match(lines.join("\n"), /check-links/);
  assert.match(errors.join("\n"), /invalid broken/);
});


test("nested Actions use separate path segments while JSON retains canonical slash ids", async () => {
  const configured = fixture({ id: "quality/links/check-local-links" });
  const listed = [];
  assert.equal(await main(["list"], { repoRoot: configured.root, write: (line) => listed.push(line) }), 0);
  assert.match(listed.join("\n"), /quality links check-local-links/);
  assert.doesNotMatch(listed.join("\n"), /quality\/links\/check-local-links/);

  const jsonLines = [];
  assert.equal(await main(["list", "--json"], { repoRoot: configured.root, write: (line) => jsonLines.push(line) }), 0);
  const payload = JSON.parse(jsonLines[0]);
  assert.equal(payload.actions[0].id, "quality/links/check-local-links");
  assert.equal(payload.actions[0].invocation, "quality links check-local-links");

  let invoked = false;
  const stdout = JSON.stringify({ schema: "trellis.action-result/v1", status: "ok", summary: "ok", outputs: [{ name: "result", value: { ok: true } }], verification: [{ check: "result", ok: true }] });
  assert.equal(await main(["quality", "links", "check-local-links", "--json"], {
    repoRoot: configured.root,
    write: () => {},
    spawn: () => { invoked = true; return { status: 0, signal: null, stderr: "", stdout }; },
  }), 0);
  assert.equal(invoked, true);
  assert.equal((await main(["validate", "quality", "links", "check-local-links"], { repoRoot: configured.root, write: () => {} })), 0);
  await assert.rejects(main(["quality/links/check-local-links"], { repoRoot: configured.root }), /separate kebab-case path segments/);
});


test("discovery rejects malformed groups without hiding healthy nested Actions", () => {
  const configured = fixture({ id: "quality/links/check-local-links" });
  writeFileSync(path.join(configured.root, "_handbook", "_cli", "actions", "quality", "notes"), "group files are invalid\n");
  mkdirSync(path.join(configured.root, "_handbook", "_cli", "actions", "empty-group"));
  mkdirSync(path.join(configured.root, "_handbook", "_cli", "actions", "BadGroup"));
  const reserved = ["help", "list", "show", "validate", "doctor", "version", "run", "test", "plan", "show-plan", "apply", "scaffold"];
  for (const word of reserved) mkdirSync(path.join(configured.root, "_handbook", "_cli", "actions", word));
  symlinkSync(path.join(configured.root, "_handbook", "_cli", "actions", "quality"), path.join(configured.root, "_handbook", "_cli", "actions", "linked-group"));
  const result = discoverActions(configured.root);
  assert.deepEqual(result.actions.map((action) => action.id), ["quality/links/check-local-links"]);
  const findings = result.errors.map((error) => `${error.id}: ${error.error}`).join("\n");
  assert.match(findings, /quality\/notes: Action group directories may contain only Action directories/);
  assert.match(findings, /empty-group: Action group directory must not be empty/);
  assert.match(findings, /BadGroup: Action path segments must be kebab-case/);
  for (const word of reserved) assert.match(findings, new RegExp(`${word}: Action path uses a reserved top-level management word`));
  assert.match(findings, /linked-group: Action path entries must not be symlinks/);
});


test("case-insensitive sibling collisions are rejected when the filesystem can represent them", (context) => {
  const configured = fixture();
  const actionsRoot = path.join(configured.root, "_handbook", "_cli", "actions");
  mkdirSync(path.join(actionsRoot, "duplicate"));
  try { mkdirSync(path.join(actionsRoot, "DUPLICATE")); }
  catch (error) {
    if (error.code === "EEXIST") return context.skip("filesystem is case-insensitive");
    throw error;
  }
  const findings = discoverActions(configured.root).errors.filter((error) => error.id.toLowerCase() === "duplicate");
  assert.equal(findings.length, 2);
  assert.ok(findings.every((finding) => /collides case-insensitively/.test(finding.error)));
});


test("an Action leaf cannot also be a group", () => {
  const configured = fixture({ id: "quality/links/check-local-links" });
  const quality = path.join(configured.root, "_handbook", "_cli", "actions", "quality");
  writeFileSync(path.join(quality, "action.json"), "{}\n");
  const result = discoverActions(configured.root);
  assert.deepEqual(result.actions, []);
  assert.match(result.errors.map((error) => error.error).join("\n"), /may contain only regular action\.json, run\.mjs, and run\.test\.mjs files/);
});


test("help and unknown paths never execute an Action or fall through to a catchall", async () => {
  const configured = fixture({ id: "quality/links/check-local-links" });
  let invoked = false;
  const lines = [];
  assert.equal(await main(["quality", "links", "check-local-links", "--help"], {
    repoRoot: configured.root,
    write: (line) => lines.push(line),
    spawn: () => { invoked = true; throw new Error("must not execute"); },
  }), 0);
  assert.match(lines.join("\n"), /\.\/trellis quality links check-local-links/);
  assert.equal(invoked, false);
  const commandHelp = [];
  assert.equal(await main(["show", "quality", "links", "check-local-links", "--help"], { repoRoot: configured.root, write: (line) => commandHelp.push(line) }), 0);
  assert.match(commandHelp[0], /^\.\/trellis show/);
  await assert.rejects(main(["not", "an", "action"], { repoRoot: configured.root, spawn: () => { invoked = true; } }), /unknown Action: not\/an\/action.*trellis list/);
  await assert.rejects(main(["quality", "links", "check-local-links", "--", "--help"], { repoRoot: configured.root }), /undeclared Action input: --help/);
  assert.equal(invoked, false);
});


test("run remains reserved and version identifies the v4 trellis launcher", async () => {
  const configured = fixture();
  await assert.rejects(main(["run", configured.id], { repoRoot: configured.root }), /run command was removed.*Invoke an Action directly/);
  for (const argv of [["version"], ["--version"]]) {
    const lines = [];
    assert.equal(await main(argv, { repoRoot: configured.root, write: (line) => lines.push(line) }), 0);
    assert.deepEqual(lines, ["trellis 4.1.0"]);
  }
});


test("canonical asset contains only the current launchers", () => {
  assert.deepEqual(readdirSync(ASSET_ROOT).sort(), ["_handbook", "trellis"]);
  assert.deepEqual(readdirSync(path.join(ASSET_ROOT, "_handbook", "_cli", "bin")), ["trellis.mjs"]);
  for (const filename of ["trellis", "_handbook/_cli/bin/trellis.mjs"]) {
    const source = readFileSync(path.join(ASSET_ROOT, filename), "utf8");
    assert.match(source, /trellis-action-cli-format: 4/);
  }
  assert.match(readFileSync(path.join(ASSET_ROOT, "trellis"), "utf8"), /^#!\/usr\/bin\/env node\n/);
  assert.match(readFileSync(path.join(ASSET_ROOT, "trellis"), "utf8"), /_handbook\/_cli\/bin\/trellis\.mjs/);
});


test("show exposes confidence, readiness, lifecycle, inputs, and effects", async () => {
  const { root } = fixture();
  const lines = [];
  assert.equal(await main(["show", "check-links"], { repoRoot: root, write: (line) => lines.push(line) }), 0);
  const output = lines.join("\n");
  assert.match(output, /Method confidence: provisional/);
  assert.match(output, /Implementation readiness: tests-passed/);
  assert.match(output, /Lifecycle: active/);
  assert.match(output, /Creates: none/);
});


test("run passes literal named arguments without a shell", async () => {
  const { root } = fixture({ manifest: {
    inputs: [{ name: "message", type: "string", required: true, description: "Literal text." }],
  } });
  let invocation;
  const lines = [];
  const stdout = JSON.stringify({ schema: "trellis.action-result/v1", status: "ok", summary: "ok", outputs: [{ name: "result", value: { ok: true } }], verification: [{ check: "result", ok: true }] });
  assert.equal(await main(["check-links", "--json", "--", "--message", "$(touch nope); a b"], {
    repoRoot: root,
    write: (line) => lines.push(line),
    spawn: (command, args, options) => {
      invocation = { command, args, options };
      return { status: 0, signal: null, stderr: "", stdout };
    },
  }), 0);
  assert.equal(invocation.options.shell, false);
  assert.deepEqual(invocation.args.slice(-2), ["--message", "$(touch nope); a b"]);
  assert.ok(!invocation.args.includes("--allow-child-process"));
  const receipt = JSON.parse(lines[0]);
  assertReceiptHash(receipt);
  assert.equal(receipt.action.manifest, loadAction(root, "check-links").manifestDigest);
  const tampered = structuredClone(receipt);
  tampered.outputs[0].value.ok = false;
  const { receipt: original, ...tamperedPayload } = tampered;
  assert.notEqual(original, digest(canonical(tamperedPayload)));
});


test("the preloaded runtime guard uses a portable file URL", async () => {
  const configured = fixture({ id: "portable-guard-preload" });
  const stdout = JSON.stringify({ schema: "trellis.action-result/v1", status: "ok", summary: "ok", outputs: [{ name: "result", value: { ok: true } }], verification: [{ check: "result", ok: true }] });
  let runArgs;
  assert.equal(await main([configured.id], {
    repoRoot: configured.root,
    write: () => {},
    spawn: (_command, args) => {
      runArgs = args;
      return { status: 0, signal: null, stderr: "", stdout };
    },
  }), 0);
  const importIndex = runArgs.indexOf("--import");
  assert.notEqual(importIndex, -1);
  assert.equal(new URL(runArgs[importIndex + 1]).protocol, "file:");
  assert.equal(path.basename(fileURLToPath(runArgs[importIndex + 1])), "guard.mjs");
  assert.equal(runArgs.at(-1), loadAction(configured.root, configured.id).entrypoint);

  let testArgs;
  assert.equal(await main(["test", configured.id], {
    repoRoot: configured.root,
    write: () => {},
    spawn: (_command, args) => {
      testArgs = args;
      return { status: 0, signal: null, stderr: "", stdout: "" };
    },
  }), 0);
  const testImportIndex = testArgs.indexOf("--import");
  assert.equal(new URL(testArgs[testImportIndex + 1]).protocol, "file:");
  assert.equal(testArgs.at(-1), loadAction(configured.root, configured.id).test);
});


test("undeclared and positional arguments are rejected before execution", async () => {
  const { root } = fixture();
  await assert.rejects(main(["check-links", "--", "--unknown", "x"], { repoRoot: root }), /undeclared Action input/);
  await assert.rejects(main(["check-links", "--", "value"], { repoRoot: root }), /must be named/);
});


test("invalid ids, unsafe effects, linked roots, and forbidden capabilities are rejected", () => {
  const { actionDir, manifest, root } = fixture();
  assert.throws(() => loadAction(root, "../escape"), CliError);
  manifest.effects.reads = [{ path: "../secret" }];
  writeFileSync(path.join(actionDir, "action.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  assert.throws(() => loadAction(root, "check-links"), /work-folder-relative/);
  for (const unsafe of ["CON.txt", "reports/trailing.", "reports/bad<name>.txt"]) {
    manifest.effects.reads = [{ path: unsafe }];
    writeFileSync(path.join(actionDir, "action.json"), `${JSON.stringify(manifest, null, 2)}\n`);
    assert.throws(() => loadAction(root, "check-links"), /not portable/);
  }
  for (const unsafe of ["reports/$draft.txt", "reports/{draft}.txt"]) {
    manifest.effects.reads = [{ path: unsafe }];
    writeFileSync(path.join(actionDir, "action.json"), `${JSON.stringify(manifest, null, 2)}\n`);
    assert.throws(() => loadAction(root, "check-links"), /literal work-folder-relative/);
  }
  manifest.effects.reads = [{ path: "." }];
  writeFileSync(path.join(actionDir, "action.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  assert.throws(() => loadAction(root, "check-links"), /broad static scope/);
  for (const reserved of [".GIT/config", "AGENTS.md", "_handbook", "_handbook/_cli/package.json", "_HANDBOOK/_SCRATCH/README.md"]) {
    manifest.effects.reads = [{ path: reserved }];
    writeFileSync(path.join(actionDir, "action.json"), `${JSON.stringify(manifest, null, 2)}\n`);
    assert.throws(() => loadAction(root, "check-links"), /reserved path/);
  }
  manifest.effects = { reads: [], creates: [], updates: [], temporary: [], network: ["example.com"] };
  writeFileSync(path.join(actionDir, "action.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  assert.throws(() => loadAction(root, "check-links"), /unsupported fields/);
  const linkedRoot = temporaryPath("trellis-linked");
  mkdirSync(path.join(linkedRoot, "_handbook"), { recursive: true });
  symlinkSync(path.join(root, "_handbook", "_cli"), path.join(linkedRoot, "_handbook", "_cli"));
  assert.throws(() => loadAction(linkedRoot, "check-links"), /must not be a symlink/);
});


test("implementation digest drift and every extra Action file are rejected", () => {
  const { actionDir, root } = fixture();
  writeFileSync(path.join(actionDir, "run.mjs"), "console.log('changed');\n");
  assert.throws(() => loadAction(root, "check-links"), /entrypoint digest drift/);
  const fresh = fixture({ id: "helper-action" });
  writeFileSync(path.join(fresh.actionDir, "helper.mjs"), "export const value = 1;\n");
  assert.throws(() => loadAction(fresh.root, "helper-action"), /may contain only regular/);
  const data = fixture({ id: "data-action" });
  writeFileSync(path.join(data.actionDir, "data.json"), "{}\n");
  assert.throws(() => loadAction(data.root, "data-action"), /may contain only regular/);
  const nested = fixture({ id: "nested-action" });
  mkdirSync(path.join(nested.actionDir, "support"));
  assert.throws(() => loadAction(nested.root, "nested-action"), /may contain only regular/);
});


test("source screening rejects exact network imports but not ordinary prose", async () => {
  const proseRun = `// The internet module is not part of this local result.\nconsole.log(JSON.stringify({schema:"trellis.action-result/v1",status:"ok",summary:"ok",outputs:[{name:"result",value:{ok:true}}],verification:[{check:"result",ok:true}]}));\n`;
  const good = fixture({ run: proseRun });
  const envelope = JSON.stringify({ schema: "trellis.action-result/v1", status: "ok", summary: "ok", outputs: [{ name: "result", value: { ok: true } }], verification: [{ check: "result", ok: true }] });
  assert.equal(await main([good.id], { repoRoot: good.root, write: () => {}, spawn: () => ({ status: 0, signal: null, stderr: "", stdout: envelope }) }), 0);
  const bad = fixture({ id: "network-action", run: `import "node:http";\n` });
  await assert.rejects(main([bad.id], { repoRoot: bad.root }), /prohibited built-in module/);
});


test("production rejects local, absolute, file, and data module imports", async () => {
  const cases = [
    ["relative-import", `import "../outside.mjs";\n`],
    ["absolute-import", `import "/tmp/outside.mjs";\n`],
    ["file-import", `import "file:///tmp/outside.mjs";\n`],
    ["data-import", `import "data:text/javascript,export default 1";\n`],
  ];
  for (const [id, run] of cases) {
    const configured = fixture({ id, run });
    await assert.rejects(main([id], { repoRoot: configured.root }), /prohibited local or inline module/);
  }

  const allowedTest = fixture({ id: "focused-local-import", test: `import "./run.mjs";\n` });
  assert.equal(await main(["test", allowedTest.id], {
    repoRoot: allowedTest.root,
    write: () => {},
    spawn: () => ({ status: 0, signal: null, stderr: "", stdout: "" }),
  }), 0);
  const rejectedTest = fixture({ id: "focused-outside-import", test: `import "../outside.mjs";\n` });
  await assert.rejects(main(["test", rejectedTest.id], { repoRoot: rejectedTest.root }), /prohibited local or inline module/);
});


test("the runtime guard rejects computed local module imports", async () => {
  const configured = fixture({ id: "computed-local-import", run: `const parent = "..";\nawait import(parent + "/outside.mjs");\n` });
  writeFileSync(path.join(configured.root, "_handbook", "_cli", "actions", "outside.mjs"), "export default 1;\n");
  await assert.rejects(main([configured.id], { repoRoot: configured.root }), /local-only guard blocked (?:local module|reserved path)/);
});


test("the actual process guard blocks obfuscated global network access", async () => {
  const configured = fixture({ id: "hidden-network", run: `await globalThis["fetch"]("https://example.com");\n` });
  await assert.rejects(main([configured.id], { repoRoot: configured.root, write: () => {} }), /local-only guard blocked network API/);
});


test("the actual process guard blocks obfuscated process and dynamic-code APIs", async () => {
  const processRun = `const blocked = {};\nfor (const name of ["binding", "_debugEnd", "_debugProcess", "_kill", "_linkedBinding", "chdir", "dlopen", "execve", "initgroups", "kill", "loadEnvFile", "openStdin", "setegid", "seteuid", "setgid", "setgroups", "setuid", "umask"]) {\n  try {\n    process[name]();\n    blocked[name] = false;\n  } catch (error) { blocked[name] = /Trellis local-only guard/.test(error.message); }\n}\nblocked.env = process["e" + "nv"].PATH === undefined && Object.keys(process["e" + "nv"]).length === 0;\nconst ok = Object.values(blocked).every(Boolean);\nconsole.log(JSON.stringify({schema:"trellis.action-result/v1",status:ok?"ok":"failed",summary:ok?"blocked":"not blocked",outputs:[{name:"result",value:blocked}],verification:[{check:"process APIs blocked",ok}]}));\n`;
  const guarded = fixture({ id: "process-bypasses", run: processRun });
  assert.equal(await main([guarded.id], { repoRoot: guarded.root, write: () => {} }), 0);
  const dynamicVm = fixture({ id: "dynamic-vm", run: `await import("node:" + "vm");\n` });
  await assert.rejects(main([dynamicVm.id], { repoRoot: dynamicVm.root, write: () => {} }), /local-only guard blocked module: node:vm/);
  const machineInfo = fixture({ id: "machine-info", run: `import os from "node:os";\nconsole.log(os.hostname());\n` });
  await assert.rejects(main([machineInfo.id], { repoRoot: machineInfo.root }), /prohibited built-in module: node:os/);
  const sqlite = fixture({ id: "sqlite-module", run: `import "node:sqlite";\n` });
  await assert.rejects(main([sqlite.id], { repoRoot: sqlite.root }), /prohibited built-in module: node:sqlite/);
});


test("the actual filesystem guard blocks reserved, symlink, escape, and unbounded reads", async () => {
  const run = `import { globSync, openAsBlob, readFileSync } from "node:fs";\nimport { pathToFileURL } from "node:url";\nconst attempts = {\n  blob: () => openAsBlob("_handbook/_cli/package.json"),\n  encoded: () => readFileSync(new URL("_handbook/%5Fcli/package.json", pathToFileURL(process.cwd() + "/"))),\n  scratch: () => readFileSync("_handbook/_scratch/README.md"),\n  reservedLink: () => readFileSync("docs/reserved-link"),\n  outsideLink: () => readFileSync("docs/outside-link"),\n  glob: () => globSync("_handbook/_cli/*"),\n};\nconst blocked = {};\nfor (const [name, attempt] of Object.entries(attempts)) {\n  try { await attempt(); blocked[name] = false; }\n  catch (error) { blocked[name] = /Trellis local-only guard/.test(error.message); }\n}\nconst ok = Object.values(blocked).every(Boolean);\nconsole.log(JSON.stringify({schema:"trellis.action-result/v1",status:ok?"ok":"failed",summary:ok?"blocked":"not blocked",outputs:[{name:"result",value:blocked}],verification:[{check:"filesystem bypasses blocked",ok}]}));\n`;
  const configured = fixture({ id: "broad-local-read", run, manifest: {
    effects: { reads: [{ path: "docs/" }], creates: [], updates: [], temporary: [] },
  } });
  mkdirSync(path.join(configured.root, "docs"));
  const outside = temporaryPath("trellis-outside-read");
  mkdirSync(outside);
  writeFileSync(path.join(outside, "secret.txt"), "secret\n");
  symlinkSync("../_handbook/_cli/package.json", path.join(configured.root, "docs", "reserved-link"));
  symlinkSync(path.join(outside, "secret.txt"), path.join(configured.root, "docs", "outside-link"));
  const guardLines = [];
  assert.equal(await main([configured.id, "--json"], { repoRoot: configured.root, write: (line) => guardLines.push(line) }), 0, guardLines.join("\n"));

  const narrow = fixture({ id: "narrow-local-read", run: `import { readFileSync } from "node:fs";\nreadFileSync("docs/private-link");\n`, manifest: {
    effects: { reads: [{ path: "docs/" }], creates: [], updates: [], temporary: [] },
  } });
  mkdirSync(path.join(narrow.root, "docs"));
  mkdirSync(path.join(narrow.root, "private"));
  writeFileSync(path.join(narrow.root, "private", "secret.txt"), "secret\n");
  symlinkSync("../private/secret.txt", path.join(narrow.root, "docs", "private-link"));
  await assert.rejects(main([narrow.id], { repoRoot: narrow.root }), /local-only guard blocked (?:path outside declared read scopes|symlink path)/);
});


test("the actual filesystem guard allows explicitly scoped owner files", async () => {
  const run = `import { readFileSync } from "node:fs";\nconst value = readFileSync(process.argv.at(-1), "utf8");\nconsole.log(JSON.stringify({schema:"trellis.action-result/v1",status:"ok",summary:"read owner file",outputs:[{name:"content",value}],verification:[{check:"owner file read",ok:true}]}));\n`;
  const configured = fixture({ id: "read-owner-file", run, manifest: {
    inputs: [{ name: "source", type: "file", required: true, description: "Explicit local owner file." }],
    outputs: [{ name: "content", type: "text", description: "Owner file content." }],
    effects: { reads: [{ input: "source" }], creates: [], updates: [], temporary: [] },
  } });
  writeFileSync(path.join(configured.root, "owner-source.txt"), "owner content\n");
  const lines = [];
  assert.equal(await main([configured.id, "--json", "--", "--source", "owner-source.txt"], { repoRoot: configured.root, write: (line) => lines.push(line) }), 0);
  assert.deepEqual(JSON.parse(lines[0]).outputs, [{ name: "content", value: "owner content\n" }]);
});


test("nested reservation matching does not capture similarly named owner paths", async () => {
  const run = `import { readFileSync } from "node:fs";\nconst value = readFileSync("_handbook/_client/value.txt", "utf8");\nconsole.log(JSON.stringify({schema:"trellis.action-result/v1",status:"ok",summary:"read owner file",outputs:[{name:"content",value}],verification:[{check:"owner file read",ok:true}]}));\n`;
  const configured = fixture({ id: "read-client-file", run, manifest: {
    outputs: [{ name: "content", type: "text", description: "Owner file content." }],
    effects: { reads: [{ path: "_handbook/_client/value.txt" }], creates: [], updates: [], temporary: [] },
  } });
  mkdirSync(path.join(configured.root, "_handbook", "_client"));
  writeFileSync(path.join(configured.root, "_handbook", "_client", "value.txt"), "owner content\n");
  const lines = [];
  assert.equal(await main([configured.id, "--json"], { repoRoot: configured.root, write: (line) => lines.push(line) }), 0);
  assert.deepEqual(JSON.parse(lines[0]).outputs, [{ name: "content", value: "owner content\n" }]);
});


test("the actual Action process cannot write directly", async () => {
  const configured = fixture({ id: "direct-write", run: `import { writeFileSync } from "node:fs";\nwriteFileSync("forbidden.txt", "no");\n` });
  await assert.rejects(main([configured.id], { repoRoot: configured.root, write: () => {} }), /ERR_ACCESS_DENIED|restricted/);
  assert.equal(existsSync(path.join(configured.root, "forbidden.txt")), false);
});


test("actual Action processes are bounded by timeout and output cap", async () => {
  const timed = fixture({ id: "never-finishes", run: `while (true) {}\n`, manifest: {
    execution: { mode: "read-only", receipt: "json-v1", timeoutMs: 100, maxOutputBytes: 1048576 },
  } });
  await assert.rejects(main([timed.id], { repoRoot: timed.root, write: () => {} }), /exceeded 100ms|signal/);
  const loud = fixture({ id: "too-loud", run: `console.log("x".repeat(4096));\n`, manifest: {
    execution: { mode: "read-only", receipt: "json-v1", timeoutMs: 60000, maxOutputBytes: 1024 },
  } });
  await assert.rejects(main([loud.id], { repoRoot: loud.root, write: () => {} }), /exceeded 1024 output bytes/);
});


test("focused tests receive only a dedicated temporary write scope", async () => {
  const configured = fixture();
  let invocation;
  const lines = [];
  assert.equal(await main(["test", configured.id], {
    repoRoot: configured.root,
    write: (line) => lines.push(line),
    spawn(command, args, options) {
      invocation = { command, args, options };
      return { status: 0, signal: null, stderr: "", stdout: "ok\n" };
    },
  }), 0);
  const writeGrant = invocation.args.find((arg) => arg.startsWith("--allow-fs-write="));
  assert.ok(writeGrant);
  const granted = writeGrant.slice("--allow-fs-write=".length);
  assert.match(granted.replaceAll(path.sep, "/"), /\/_handbook\/_scratch\/tests\/test-[^/]+$/);
  assert.equal(invocation.options.env.TMPDIR, granted);
  assert.equal(existsSync(granted), false);
  assert.deepEqual(readdirSync(path.join(configured.root, "_handbook", "_scratch", "tests")), []);
  assert.match(lines.join("\n"), new RegExp(`Trellis test runtime: Node ${process.versions.node.replaceAll(".", "\\.")}`));
});


test("scratch policy and a regular local scratch root are required", async () => {
  const missingPolicy = fixture({ id: "missing-scratch-policy" });
  rmSync(path.join(missingPolicy.root, "_handbook", "_scratch", "README.md"));
  await assert.rejects(main(["test", missingPolicy.id], { repoRoot: missingPolicy.root }), /scratch policy is missing/);

  const linked = fixture({ id: "linked-scratch" });
  const scratch = path.join(linked.root, "_handbook", "_scratch");
  const external = temporaryPath("trellis-external-scratch");
  mkdirSync(external);
  writeFileSync(path.join(external, ".gitignore"), "*\n");
  writeFileSync(path.join(external, "README.md"), "# External scratch\n");
  rmSync(scratch, { recursive: true });
  symlinkSync(external, scratch);
  await assert.rejects(main(["test", linked.id], { repoRoot: linked.root }), /scratch directory.*symlink/i);
});


test("Draft and Untested Actions require deliberate development overrides", async () => {
  const { root } = fixture({ manifest: {
    readiness: { status: "untested", evidence: [], validatedAt: null, validatedOn: [] },
    lifecycle: { status: "draft", reason: "Incomplete.", replacement: null },
  } });
  await assert.rejects(main(["check-links"], { repoRoot: root }), /Draft/);
  let called = false;
  const stdout = JSON.stringify({ schema: "trellis.action-result/v1", status: "ok", summary: "ok", outputs: [{ name: "result", value: { ok: true } }], verification: [{ check: "result", ok: true }] });
  assert.equal(await main(["check-links", "--allow-draft", "--allow-untested"], { repoRoot: root, write: () => {}, spawn: () => { called = true; return { status: 0, signal: null, stderr: "", stdout }; } }), 0);
  assert.equal(called, true);
});


test("direct nested invocation plans changes and apply binds exact inputs and state", async () => {
  const emptyDigest = digest("");
  const { root } = fixture({ id: "records/create-output", manifest: {
    inputs: [{ name: "output", type: "path", required: true, description: "New local output file." }],
    outputs: [{ name: "file", type: "file", path: "result.txt", description: "Created file." }],
    effects: { reads: [], creates: [{ input: "output" }], updates: [], temporary: [] },
    execution: { mode: "plan-apply", receipt: "json-v1", timeoutMs: 60000, maxOutputBytes: 1048576 },
  } });
  const planEnvelope = JSON.stringify({
    schema: "trellis.action-plan/v1",
    summary: "Create an empty output file.",
    operations: [{ kind: "create", path: "result.txt", before: null, encoding: "utf8", content: "", after: emptyDigest }],
    verification: [{ check: "output path is available", ok: true }],
  });
  const lines = [];
  assert.equal(await main(["records", "create-output", "--json", "--", "--output", "result.txt"], { repoRoot: root, write: (line) => lines.push(line), spawn: () => ({ status: 0, signal: null, stderr: "", stdout: planEnvelope }) }), 0);
  const planReceipt = JSON.parse(lines[0]);
  assertReceiptHash(planReceipt);
  const plan = planReceipt.plan;
  assert.ok(plan);
  assert.equal(existsSync(path.join(root, "result.txt")), false);
  assert.equal(existsSync(path.join(root, "_handbook", "_scratch", "plans", "records", "create-output", `${plan.slice(7)}.json`)), true);
  const applied = [];
  assert.equal(await main(["apply", "records", "create-output", "--plan", plan, "--json"], { repoRoot: root, write: (line) => applied.push(line) }), 0);
  const applyReceipt = JSON.parse(applied[0]);
  assertReceiptHash(applyReceipt);
  assert.equal(applyReceipt.plan, plan);
  assert.equal(applyReceipt.operations[0].after, emptyDigest);
  assert.deepEqual(applyReceipt.outputs, [{ name: "file", value: "result.txt" }]);
  assert.deepEqual(applyReceipt.verification.map((item) => item.check), [
    "output path is available",
    "applied create result.txt matches planned digest",
  ]);
  assert.equal(readFileSync(path.join(root, "result.txt"), "utf8"), "");
});


test("broad handbook scopes are rejected while exact owner handbook scopes remain usable", async () => {
  const configured = fixture({ id: "summarize-handbook", manifest: {
    inputs: [{ name: "source", type: "directory", required: true, description: "Handbook directory to inspect." }],
    outputs: [{ name: "summary", type: "file", path: "handbook-result.txt", description: "Generated summary." }],
    effects: { reads: [{ input: "source" }], creates: [{ path: "handbook-result.txt" }], updates: [], temporary: [] },
    execution: { mode: "plan-apply", receipt: "json-v1", timeoutMs: 60000, maxOutputBytes: 1048576 },
  } });
  const content = "summary\n";
  const envelope = JSON.stringify({
    schema: "trellis.action-plan/v1",
    summary: "Summarize the handbook.",
    operations: [{ kind: "create", path: "handbook-result.txt", before: null, encoding: "utf8", content, after: digest(content) }],
    verification: [{ check: "handbook inspected", ok: true }],
  });
  const lines = [];
  await assert.rejects(main(["plan", configured.id, "--json", "--", "--source", "_handbook"], {
    repoRoot: configured.root,
    write: (line) => lines.push(line),
    spawn: () => ({ status: 0, signal: null, stderr: "", stdout: envelope }),
  }), /reserved path/);
  const ownerHandbook = path.join(configured.root, "_handbook", "actions");
  mkdirSync(ownerHandbook, { recursive: true });
  writeFileSync(path.join(ownerHandbook, "example.md"), "# Example\n");
  assert.equal(await main(["plan", configured.id, "--json", "--", "--source", "_handbook/actions"], {
    repoRoot: configured.root,
    write: (line) => lines.push(line),
    spawn: () => ({ status: 0, signal: null, stderr: "", stdout: envelope }),
  }), 0);
  const plan = JSON.parse(lines[0]).plan;
  const planFile = path.join(configured.root, "_handbook", "_scratch", "plans", configured.id, `${plan.slice(7)}.json`);
  const saved = JSON.parse(readFileSync(planFile, "utf8"));
  assert.equal(saved.inputState.entries.some(([filename]) => filename.startsWith("_handbook/_cli")), false);
  assert.equal(saved.inputState.entries.some(([filename]) => filename.startsWith("_handbook/_scratch")), false);
  assert.equal(await main(["apply", configured.id, "--plan", plan], { repoRoot: configured.root, write: () => {} }), 0);
  assert.equal(readFileSync(path.join(configured.root, "handbook-result.txt"), "utf8"), content);
});


test("update apply preserves file mode and rejects stale plans", async () => {
  const configured = fixture({ id: "normalize-record", manifest: {
    inputs: [{ name: "target", type: "file", required: true, description: "Local file to normalize." }],
    outputs: [{ name: "updated-file", type: "file", description: "Updated local file." }],
    effects: { reads: [{ input: "target" }], creates: [], updates: [{ input: "target" }], temporary: [] },
    execution: { mode: "plan-apply", receipt: "json-v1", timeoutMs: 60000, maxOutputBytes: 1048576 },
  } });
  const target = path.join(configured.root, "record.txt");
  writeFileSync(target, "before\n");
  chmodSync(target, 0o640);
  const before = digest("before\n");
  const after = digest("after\n");
  const envelope = JSON.stringify({ schema: "trellis.action-plan/v1", summary: "Normalize one record.", operations: [{ kind: "update", path: "record.txt", before, encoding: "utf8", content: "after\n", after }], verification: [{ check: "target is current", ok: true }] });
  const lines = [];
  await main(["plan", configured.id, "--", "--target", "record.txt"], { repoRoot: configured.root, write: (line) => lines.push(line), spawn: () => ({ status: 0, signal: null, stderr: "", stdout: envelope }) });
  const plan = lines.map((line) => /^Plan: (sha256:[0-9a-f]{64})$/.exec(line)?.[1]).find(Boolean);
  const review = [];
  assert.equal(await main(["show-plan", configured.id, "--plan", plan], { repoRoot: configured.root, write: (line) => review.push(line) }), 0);
  assert.match(review.join("\n"), /before\n[\s\S]*after/);
  assert.match(review.join("\n"), /Apply only after review/);
  let simulatedWindowsConflict = true;
  assert.equal(await main(["apply", configured.id, "--plan", plan], {
    repoRoot: configured.root,
    write: () => {},
    fileOperations: {
      renameSync(source, destination) {
        if (simulatedWindowsConflict && path.basename(destination) === "record.txt" && source.endsWith(".new")) {
          simulatedWindowsConflict = false;
          const error = new Error("simulated Windows destination-exists behavior");
          error.code = "EEXIST";
          throw error;
        }
        renameSync(source, destination);
      },
    },
  }), 0);
  assert.equal(simulatedWindowsConflict, false);
  assert.equal(readFileSync(target, "utf8"), "after\n");
  if (process.platform !== "win32") assert.equal(statSync(target).mode & 0o777, 0o640);

  writeFileSync(target, "before\n");
  chmodSync(target, 0o640);
  const staleLines = [];
  await main(["plan", configured.id, "--", "--target", "record.txt"], { repoRoot: configured.root, write: (line) => staleLines.push(line), spawn: () => ({ status: 0, signal: null, stderr: "", stdout: envelope }) });
  const stalePlan = staleLines.map((line) => /^Plan: (sha256:[0-9a-f]{64})$/.exec(line)?.[1]).find(Boolean);
  writeFileSync(target, "changed elsewhere\n");
  await assert.rejects(main(["apply", configured.id, "--plan", stalePlan], { repoRoot: configured.root }), /changed after planning/);
  assert.equal(readFileSync(target, "utf8"), "changed elsewhere\n");
});


test("a multi-operation apply rolls back earlier creates when a later install fails", async () => {
  const configured = fixture({ id: "multi-create", manifest: {
    inputs: [],
    outputs: [{ name: "created-files", type: "files", path: "output/", description: "Created local files." }],
    effects: { reads: [], creates: [{ path: "output/" }], updates: [], temporary: [] },
    execution: { mode: "plan-apply", receipt: "json-v1", timeoutMs: 60000, maxOutputBytes: 1048576 },
  } });
  mkdirSync(path.join(configured.root, "output"));
  const first = "first\n";
  const second = "second\n";
  const envelope = JSON.stringify({
    schema: "trellis.action-plan/v1",
    summary: "Create two outputs.",
    operations: [
      { kind: "create", path: "output/first.txt", before: null, encoding: "utf8", content: first, after: digest(first) },
      { kind: "create", path: "output/second.txt", before: null, encoding: "utf8", content: second, after: digest(second) },
    ],
    verification: [{ check: "both targets are available", ok: true }],
  });
  const lines = [];
  await main(["plan", configured.id], { repoRoot: configured.root, write: (line) => lines.push(line), spawn: () => ({ status: 0, signal: null, stderr: "", stdout: envelope }) });
  const plan = lines.map((line) => /^Plan: (sha256:[0-9a-f]{64})$/.exec(line)?.[1]).find(Boolean);
  let installs = 0;
  await assert.rejects(main(["apply", configured.id, "--plan", plan], {
    repoRoot: configured.root,
    fileOperations: {
      renameSync(source, destination) {
        if (source.endsWith(".new") && ++installs === 2) throw new Error("simulated second install failure");
        renameSync(source, destination);
      },
    },
  }), /failed and was rolled back/);
  assert.equal(existsSync(path.join(configured.root, "output", "first.txt")), false);
  assert.equal(existsSync(path.join(configured.root, "output", "second.txt")), false);
  assert.deepEqual(readdirSync(path.join(configured.root, "_handbook", "_scratch", "transactions")), []);

  let stagedFiles = 0;
  await assert.rejects(main(["apply", configured.id, "--plan", plan], {
    repoRoot: configured.root,
    fileOperations: {
      writeFileSync(filename, content, options) {
        if (++stagedFiles === 2) throw new Error("simulated staging failure");
        writeFileSync(filename, content, options);
      },
    },
  }), /staging failed before any work-folder file changed/);
  assert.deepEqual(readdirSync(path.join(configured.root, "_handbook", "_scratch", "transactions")), []);
});


test("dynamic writes protect current Trellis paths while allowing owner-controlled outputs", async () => {
  const { root } = fixture({ id: "reserved-output", manifest: {
    inputs: [{ name: "output", type: "path", required: true, description: "New local output file." }],
    outputs: [{ name: "output-file", type: "file", description: "Created local output file." }],
    effects: { reads: [], creates: [{ input: "output" }], updates: [], temporary: [] },
    execution: { mode: "plan-apply", receipt: "json-v1", timeoutMs: 60000, maxOutputBytes: 1048576 },
  } });
  await assert.rejects(main(["plan", "reserved-output", "--", "--output", "AGENTS.md"], { repoRoot: root }), /reserved path/);
  for (const output of ["_handbook/_cli/output.txt", "_handbook/_scratch/output.txt"]) {
    await assert.rejects(main(["plan", "reserved-output", "--", "--output", output], { repoRoot: root }), /reserved path/);
  }

  mkdirSync(path.join(root, "actual-output"));
  symlinkSync("actual-output", path.join(root, "alias"));
  await assert.rejects(main(["plan", "reserved-output", "--", "--output", "alias/result.txt"], { repoRoot: root }), /symlink component/);

  const output = "owner-output.txt";
  const content = "owner-controlled output\n";
  const envelope = JSON.stringify({
    schema: "trellis.action-plan/v1",
    summary: `Create ${output}.`,
    operations: [{ kind: "create", path: output, before: null, encoding: "utf8", content, after: digest(content) }],
    verification: [{ check: "owner path is available", ok: true }],
  });
  assert.equal(await main(["plan", "reserved-output", "--", "--output", output], {
    repoRoot: root,
    write: () => {},
    spawn: () => ({ status: 0, signal: null, stderr: "", stdout: envelope }),
  }), 0);
});


test("failed plan verification is not persisted", async () => {
  const configured = fixture({ id: "failed-plan", manifest: {
    outputs: [{ name: "output-file", type: "file", path: "result.txt", description: "Created file." }],
    effects: { reads: [], creates: [{ path: "result.txt" }], updates: [], temporary: [] },
    execution: { mode: "plan-apply", receipt: "json-v1", timeoutMs: 60000, maxOutputBytes: 1048576 },
  } });
  const content = "result\n";
  const envelope = JSON.stringify({
    schema: "trellis.action-plan/v1",
    summary: "Unsafe plan.",
    operations: [{ kind: "create", path: "result.txt", before: null, encoding: "utf8", content, after: digest(content) }],
    verification: [{ check: "owner precondition", ok: false, detail: "Not satisfied." }],
  });
  await assert.rejects(main(["plan", configured.id], {
    repoRoot: configured.root,
    spawn: () => ({ status: 0, signal: null, stderr: "", stdout: envelope }),
  }), /verification failed/);
  assert.equal(existsSync(path.join(configured.root, "_handbook", "_scratch", "plans")), false);
});


test("plan outputs cover every operation exactly once", async () => {
  const content = "result\n";
  const operation = { kind: "create", path: "output/result.txt", before: null, encoding: "utf8", content, after: digest(content) };
  const envelope = JSON.stringify({ schema: "trellis.action-plan/v1", summary: "Create result.", operations: [operation], verification: [{ check: "available", ok: true }] });

  const missing = fixture({ id: "missing-plan-output", manifest: {
    outputs: [{ name: "other", type: "file", path: "output/other.txt", description: "Other file." }],
    effects: { reads: [], creates: [{ path: "output/" }], updates: [], temporary: [] },
    execution: { mode: "plan-apply", receipt: "json-v1", timeoutMs: 60000, maxOutputBytes: 1048576 },
  } });
  mkdirSync(path.join(missing.root, "output"));
  await assert.rejects(main(["plan", missing.id], { repoRoot: missing.root, spawn: () => ({ status: 0, signal: null, stderr: "", stdout: envelope }) }), /not represented by a declared output/);

  const overlap = fixture({ id: "overlapping-plan-output", manifest: {
    outputs: [
      { name: "folder", type: "files", path: "output/", description: "Output folder." },
      { name: "result", type: "file", path: "output/result.txt", description: "Result file." },
    ],
    effects: { reads: [], creates: [{ path: "output/" }], updates: [], temporary: [] },
    execution: { mode: "plan-apply", receipt: "json-v1", timeoutMs: 60000, maxOutputBytes: 1048576 },
  } });
  mkdirSync(path.join(overlap.root, "output"));
  await assert.rejects(main(["plan", overlap.id], { repoRoot: overlap.root, spawn: () => ({ status: 0, signal: null, stderr: "", stdout: envelope }) }), /more than one declared output/);
});


test("planning aborts if a declared read changes during Action execution", async () => {
  const configured = fixture({ id: "mutating-plan-input", manifest: {
    inputs: [{ name: "source", type: "file", required: true, description: "Local source file." }],
    outputs: [{ name: "output-file", type: "file", path: "result.txt", description: "Created file." }],
    effects: { reads: [{ input: "source" }], creates: [{ path: "result.txt" }], updates: [], temporary: [] },
    execution: { mode: "plan-apply", receipt: "json-v1", timeoutMs: 60000, maxOutputBytes: 1048576 },
  } });
  const source = path.join(configured.root, "source.txt");
  writeFileSync(source, "before\n");
  const content = "result\n";
  const envelope = JSON.stringify({
    schema: "trellis.action-plan/v1",
    summary: "Create result.",
    operations: [{ kind: "create", path: "result.txt", before: null, encoding: "utf8", content, after: digest(content) }],
    verification: [{ check: "source parsed", ok: true }],
  });
  await assert.rejects(main(["plan", configured.id, "--", "--source", "source.txt"], {
    repoRoot: configured.root,
    spawn() {
      writeFileSync(source, "changed during planning\n");
      return { status: 0, signal: null, stderr: "", stdout: envelope };
    },
  }), /inputs changed while the plan was being created/);
  assert.equal(existsSync(path.join(configured.root, "_handbook", "_scratch", "plans")), false);
});


test("result outputs must agree with the manifest", async () => {
  const { root } = fixture();
  const bad = JSON.stringify({ schema: "trellis.action-result/v1", status: "ok", summary: "ok", outputs: [{ name: "unknown", value: true }], verification: [{ check: "reported", ok: true }] });
  await assert.rejects(main(["check-links"], { repoRoot: root, spawn: () => ({ status: 0, signal: null, stderr: "", stdout: bad }) }), /unknown or duplicated/);

  const files = fixture({ id: "scoped-files-result", manifest: {
    outputs: [{ name: "files", type: "files", path: "reports/", description: "Report files." }],
    effects: { reads: [{ path: "elsewhere.txt" }], creates: [], updates: [], temporary: [] },
  } });
  writeFileSync(path.join(files.root, "elsewhere.txt"), "elsewhere\n");
  const outside = JSON.stringify({ schema: "trellis.action-result/v1", status: "ok", summary: "ok", outputs: [{ name: "files", value: ["elsewhere.txt"] }], verification: [] });
  await assert.rejects(main([files.id], { repoRoot: files.root, spawn: () => ({ status: 0, signal: null, stderr: "", stdout: outside }) }), /verification.*must not be empty/);

  const withVerification = JSON.stringify({ schema: "trellis.action-result/v1", status: "ok", summary: "ok", outputs: [{ name: "files", value: ["elsewhere.txt"] }], verification: [{ check: "found", ok: true }] });
  await assert.rejects(main([files.id], { repoRoot: files.root, spawn: () => ({ status: 0, signal: null, stderr: "", stdout: withVerification }) }), /outside its declared directory scope/);
});


test("read-only file outputs must exist and stay inside declared read effects", async () => {
  const missing = fixture({ id: "missing-file-result", manifest: {
    outputs: [{ name: "file", type: "file", description: "Result file." }],
    effects: { reads: [{ path: "reports/" }], creates: [], updates: [], temporary: [] },
  } });
  mkdirSync(path.join(missing.root, "reports"));
  const missingEnvelope = JSON.stringify({ schema: "trellis.action-result/v1", status: "ok", summary: "ok", outputs: [{ name: "file", value: "reports/missing.txt" }], verification: [{ check: "reported", ok: true }] });
  await assert.rejects(main([missing.id], { repoRoot: missing.root, spawn: () => ({ status: 0, signal: null, stderr: "", stdout: missingEnvelope }) }), /existing regular file/);

  const outside = fixture({ id: "outside-read-result", manifest: {
    outputs: [{ name: "file", type: "file", description: "Result file." }],
    effects: { reads: [{ path: "reports/" }], creates: [], updates: [], temporary: [] },
  } });
  mkdirSync(path.join(outside.root, "reports"));
  writeFileSync(path.join(outside.root, "elsewhere.txt"), "outside\n");
  const outsideEnvelope = JSON.stringify({ schema: "trellis.action-result/v1", status: "ok", summary: "ok", outputs: [{ name: "file", value: "elsewhere.txt" }], verification: [{ check: "reported", ok: true }] });
  await assert.rejects(main([outside.id], { repoRoot: outside.root, spawn: () => ({ status: 0, signal: null, stderr: "", stdout: outsideEnvelope }) }), /outside the declared read effects/);
});


test("read-only result status matches its verification evidence", async () => {
  const configured = fixture({ id: "status-evidence" });
  for (const envelope of [
    { schema: "trellis.action-result/v1", status: "ok", summary: "mismatch", outputs: [{ name: "result", value: {} }], verification: [{ check: "failed", ok: false }] },
    { schema: "trellis.action-result/v1", status: "failed", summary: "mismatch", outputs: [{ name: "result", value: {} }], verification: [{ check: "passed", ok: true }] },
  ]) {
    await assert.rejects(main([configured.id], {
      repoRoot: configured.root,
      spawn: () => ({ status: 0, signal: null, stderr: "", stdout: JSON.stringify(envelope) }),
    }), /status must be ok exactly when every verification check passes/);
  }
});


test("scaffold creates mirrored nested Action and handbook paths only with explicit apply", async () => {
  const { root } = fixture();
  const draftDir = path.join(root, "_handbook", "_cli", "actions", "quality", "new-action");
  assert.equal(await main(["scaffold", "quality", "new-action", "--title", "New Action"], { repoRoot: root, write: () => {} }), 0);
  assert.equal(existsSync(draftDir), false);
  assert.equal(await main(["scaffold", "quality", "new-action", "--title", "New Action", "--apply"], { repoRoot: root, write: () => {} }), 0);
  const action = loadAction(root, "quality/new-action");
  assert.equal(action.docs, "_handbook/actions/quality/new-action.md");
  assert.match(readFileSync(path.join(root, action.docs), "utf8"), /\.\/trellis quality new-action/);
  assert.equal(action.lifecycle.status, "draft");
  assert.equal(action.readiness.status, "untested");
});


test("scaffold rejects case collisions and Action leaves used as group parents", async () => {
  const collision = fixture();
  mkdirSync(path.join(collision.root, "_handbook", "_cli", "actions", "Quality"));
  await assert.rejects(main(["scaffold", "quality", "new-action", "--title", "New Action", "--apply"], { repoRoot: collision.root }), /collides case-insensitively/);

  const leaf = fixture({ id: "quality" });
  await assert.rejects(main(["scaffold", "quality", "new-action", "--title", "New Action", "--apply"], { repoRoot: leaf.root }), /Action leaf cannot contain nested scaffold path/);
});


test("doctor is honest that the local-only guard is not an OS network sandbox", async () => {
  const { root } = fixture();
  const lines = [];
  assert.equal(await main(["doctor"], { repoRoot: root, write: (line) => lines.push(line) }), 0);
  assert.match(lines.join("\n"), /not an OS network sandbox/);
});
