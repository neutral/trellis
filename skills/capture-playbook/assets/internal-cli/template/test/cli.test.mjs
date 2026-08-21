import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import {
  TrellisToolError,
  applyWriteOperation,
  planWriteOperation,
  runReadOperation,
  validateToolManifest,
} from "../src/core-tools.mjs";

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), "trellis-internal-cli-"));
  await writeFile(join(root, "alpha.txt"), "alpha\nbeta\n", "utf8");
  await writeFile(join(root, "same.txt"), "alpha\nbeta\n", "utf8");
  await writeFile(join(root, "config.json"), '{\n  "enabled": false,\n  "name": "demo"\n}\n', "utf8");
  return root;
}

test("validates a fixed-operation tool manifest", () => {
  const manifest = validateToolManifest(
    {
      format: 1,
      playbook: "release-review",
      id: "hash-notes",
      title: "Hash notes",
      description: "Compute a review hash.",
      operation: "file.hash",
    },
    "release-review",
    "hash-notes",
  );
  assert.equal(manifest.operation, "file.hash");
  assert.throws(
    () => validateToolManifest({ ...manifest, operation: "shell.run" }),
    TrellisToolError,
  );
});

test("hashes and compares project-local files", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  const hash = await runReadOperation("file.hash", { file: "alpha.txt" }, root);
  assert.match(hash.outputs.sha256, /^[a-f0-9]{64}$/u);
  const comparison = await runReadOperation(
    "files.compare",
    { left: "alpha.txt", right: "same.txt" },
    root,
  );
  assert.equal(comparison.outputs.equal, true);
});

test("plans and applies one exact text replacement", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  const args = { file: "alpha.txt", from: "beta", to: "gamma" };
  const plan = await planWriteOperation("text.replace", args, root);
  assert.equal(plan.summary.replacementCount, 1);
  assert.notEqual(plan.before.sha256, plan.after.sha256);

  await assert.rejects(
    applyWriteOperation("text.replace", args, root, "0".repeat(64)),
    /changed since review/u,
  );
  const receipt = await applyWriteOperation("text.replace", args, root, plan.before.sha256);
  assert.equal(receipt.status, "applied");
  assert.equal(await readFile(join(root, "alpha.txt"), "utf8"), "alpha\ngamma\n");
});

test("sets an existing JSON value with a reviewed hash", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  const args = { file: "config.json", pointer: "/enabled", value: "true" };
  const plan = await planWriteOperation("json.set", args, root);
  assert.equal(plan.summary.previous, false);
  assert.equal(plan.summary.next, true);
  await applyWriteOperation("json.set", args, root, plan.before.sha256);
  assert.equal(JSON.parse(await readFile(join(root, "config.json"), "utf8")).enabled, true);
});

test("rejects path traversal and ambiguous replacements", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  await assert.rejects(
    runReadOperation("file.hash", { file: "../outside.txt" }, root),
    /unsafe file path/u,
  );
  await assert.rejects(
    planWriteOperation("text.replace", { file: "alpha.txt", from: "a", to: "x" }, root),
    /exactly once/u,
  );
});
