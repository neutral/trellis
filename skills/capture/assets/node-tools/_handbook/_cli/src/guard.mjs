import fs from "node:fs";
import { registerHooks, syncBuiltinESMExports } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";


let config = {};
try {
  config = JSON.parse(process.env.TRELLIS_GUARD_CONFIG || "{}");
} finally {
  delete process.env.TRELLIS_GUARD_CONFIG;
}


const BLOCKED_BUILTINS = new Set([
  "child_process",
  "cluster",
  "dgram",
  "dns",
  "http",
  "http2",
  "https",
  "inspector",
  "module",
  "net",
  "os",
  "quic",
  "repl",
  "sqlite",
  "tls",
  "vm",
  "wasi",
  "worker_threads",
]);


function bareBuiltin(specifier) {
  return specifier.startsWith("node:") ? specifier.slice(5) : specifier;
}


function blockedBuiltin(specifier) {
  const name = bareBuiltin(specifier).split("/")[0];
  if (name === "os" && config.test === true) return false;
  return BLOCKED_BUILTINS.has(name);
}


function within(candidate, parent) {
  const relative = path.relative(parent, candidate);
  return relative === "" || (relative !== ".." && !relative.startsWith(`..${path.sep}`));
}


const allowedModuleFiles = (config.allowedModuleFiles || []).map((item) => path.resolve(item));
const allowedModuleRoots = (config.allowedModuleRoots || []).map((item) => path.resolve(item));


registerHooks({
  resolve(specifier, context, nextResolve) {
    if (blockedBuiltin(specifier)) {
      throw new Error(`Trellis local-only guard blocked module: ${specifier}`);
    }
    if (specifier.startsWith("data:")) {
      throw new Error("Trellis local-only guard blocked inline data module");
    }
    // Node's hook resolver treats a raw Windows drive letter as a URL scheme.
    const resolved = nextResolve(path.isAbsolute(specifier) ? pathToFileURL(specifier).href : specifier, context);
    if (resolved.url?.startsWith("data:")) {
      throw new Error("Trellis local-only guard blocked inline data module");
    }
    if (resolved.url?.startsWith("file:")) {
      const filename = path.resolve(fileURLToPath(resolved.url));
      const allowed = allowedModuleFiles.includes(filename) || allowedModuleRoots.some((root) => within(filename, root));
      if (!allowed) throw new Error(`Trellis local-only guard blocked local module: ${filename}`);
    }
    return resolved;
  },
});


const originalGetBuiltinModule = process.getBuiltinModule?.bind(process);
if (originalGetBuiltinModule) {
  Object.defineProperty(process, "getBuiltinModule", {
    configurable: false,
    enumerable: true,
    writable: false,
    value(specifier) {
      if (blockedBuiltin(specifier)) {
        throw new Error(`Trellis local-only guard blocked module: ${specifier}`);
      }
      return originalGetBuiltinModule(specifier);
    },
  });
}


for (const name of ["fetch", "WebSocket", "EventSource"]) {
  Object.defineProperty(globalThis, name, {
    configurable: false,
    enumerable: false,
    writable: false,
    value() {
      throw new Error(`Trellis local-only guard blocked network API: ${name}`);
    },
  });
}


for (const name of [
  "binding",
  "_debugEnd",
  "_debugProcess",
  "_kill",
  "_linkedBinding",
  "chdir",
  "dlopen",
  "execve",
  "initgroups",
  "kill",
  "loadEnvFile",
  "openStdin",
  "setegid",
  "seteuid",
  "setgid",
  "setgroups",
  "setuid",
  "umask",
]) {
  Object.defineProperty(process, name, {
    configurable: false,
    enumerable: true,
    writable: false,
    value() {
      throw new Error(`Trellis local-only guard blocked process API: ${name}`);
    },
  });
}

const repoRoot = config.repoRoot ? path.resolve(config.repoRoot) : null;
const allowedReserved = (config.allowedReserved || []).map((item) => path.resolve(item));
const readScopes = (config.readScopes || []).map((scope) => ({ path: path.resolve(scope.path), directory: scope.directory === true }));
const reservedNames = new Set([".git", ".codex", ".claude", ".cursor"]);
const reservedSubtrees = new Set(["_handbook/_cli", "_handbook/_scratch"]);
const reservedFiles = new Set(["trellis", "agents.md", "claude.md", "gemini.md"]);
const originalRealpathSync = fs.realpathSync.bind(fs);
const originalLstatSync = fs.lstatSync.bind(fs);


function rejectExistingSymlink(pathname) {
  const bases = [repoRoot, ...allowedReserved].filter((base) => base && within(pathname, base)).sort((left, right) => right.length - left.length);
  const base = bases[0] || path.parse(pathname).root;
  let current = base;
  for (const segment of path.relative(base, pathname).split(path.sep).filter(Boolean)) {
    current = path.join(current, segment);
    try {
      if (originalLstatSync(current).isSymbolicLink()) {
        throw new Error(`Trellis local-only guard blocked symlink path: ${current}`);
      }
    } catch (error) {
      if (error.message?.startsWith("Trellis local-only guard")) throw error;
      break;
    }
  }
}


function isReservedPathname(pathname) {
  const relative = path.relative(repoRoot, pathname).replaceAll(path.sep, "/").replace(/^\.\/+/, "").replace(/\/+$/, "").toLowerCase();
  if (!relative || relative === "." || relative === ".." || relative.startsWith("../")) return false;
  const [first] = relative.split("/");
  if (reservedNames.has(first) || reservedFiles.has(relative)) return true;
  return [...reservedSubtrees].some((reserved) => relative === reserved || relative.startsWith(`${reserved}/`));
}


function scopeCovers(scope, candidate) {
  return scope.directory ? within(candidate, scope.path) : candidate === scope.path;
}


function assertReadable(target) {
  if (!repoRoot || typeof target !== "string" && !Buffer.isBuffer(target) && !(target instanceof URL)) {
    return;
  }
  let pathname;
  try {
    if (target instanceof URL) {
      if (target.protocol !== "file:") throw new Error(`Trellis local-only guard blocked non-file URL: ${target.protocol}`);
      pathname = path.resolve(fileURLToPath(target));
    } else pathname = path.resolve(target.toString());
  } catch {
    throw new Error("Trellis local-only guard could not validate a filesystem path");
  }
  let resolved = null;
  try {
    resolved = originalRealpathSync(pathname);
  } catch {
    // Some metadata calls intentionally target a missing path. Lexical checks still apply.
    rejectExistingSymlink(pathname);
  }
  const candidates = [pathname, resolved].filter(Boolean);
  if (!within(pathname, repoRoot)) {
    throw new Error(`Trellis local-only guard blocked path outside the work folder: ${pathname}`);
  }
  if (resolved && !within(resolved, repoRoot)) {
    throw new Error(`Trellis local-only guard blocked path escaping the work folder: ${path.relative(repoRoot, pathname)}`);
  }
  if (allowedReserved.some((allowed) => candidates.every((candidate) => within(candidate, allowed)))) return;
  for (const candidate of candidates) {
    const relative = path.relative(repoRoot, candidate);
    if (isReservedPathname(candidate)) {
      throw new Error(`Trellis local-only guard blocked reserved path: ${relative}`);
    }
  }
  if (!readScopes.some((scope) => candidates.every((candidate) => scopeCovers(scope, candidate)))) {
    throw new Error(`Trellis local-only guard blocked path outside declared read scopes: ${path.relative(repoRoot, pathname)}`);
  }
}


for (const name of [
  "access",
  "accessSync",
  "createReadStream",
  "exists",
  "existsSync",
  "lstat",
  "lstatSync",
  "open",
  "openAsBlob",
  "openSync",
  "opendir",
  "opendirSync",
  "readFile",
  "readFileSync",
  "readdir",
  "readdirSync",
  "readlink",
  "readlinkSync",
  "realpath",
  "realpathSync",
  "stat",
  "statSync",
  "statfs",
  "statfsSync",
]) {
  const original = fs[name]?.bind(fs);
  if (!original) continue;
  fs[name] = (target, ...args) => {
    assertReadable(target);
    return original(target, ...args);
  };
}

for (const name of ["access", "lstat", "open", "opendir", "readFile", "readdir", "readlink", "realpath", "stat", "statfs"]) {
  const original = fs.promises[name]?.bind(fs.promises);
  if (!original) continue;
  fs.promises[name] = async (target, ...args) => {
    assertReadable(target);
    return original(target, ...args);
  };
}

for (const name of ["glob", "globSync", "watch", "watchFile"]) {
  if (!fs[name]) continue;
  fs[name] = () => {
    throw new Error(`Trellis local-only guard blocked unbounded filesystem API: ${name}`);
  };
}

for (const name of ["glob", "watch"]) {
  if (!fs.promises[name]) continue;
  fs.promises[name] = () => {
    throw new Error(`Trellis local-only guard blocked unbounded filesystem API: promises.${name}`);
  };
}

if (fs.ReadStream) {
  const OriginalReadStream = fs.ReadStream;
  fs.ReadStream = class TrellisReadStream extends OriginalReadStream {
    constructor(target, ...args) {
      assertReadable(target);
      super(target, ...args);
    }
  };
}

syncBuiltinESMExports();

if (config.test !== true) {
  const emptyEnvironment = new Proxy(Object.create(null), {
    set() {
      throw new Error("Trellis local-only guard blocked process environment mutation");
    },
    defineProperty() {
      throw new Error("Trellis local-only guard blocked process environment mutation");
    },
    deleteProperty() {
      throw new Error("Trellis local-only guard blocked process environment mutation");
    },
  });
  Object.defineProperty(process, "env", {
    configurable: false,
    enumerable: true,
    writable: false,
    value: emptyEnvironment,
  });
}
