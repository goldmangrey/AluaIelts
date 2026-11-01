// Build an isolated unconfigured site so tests never overwrite .env.local,
// disrupt the user's dev server, or send account operations to real Firebase.
import { mkdtemp, cp, symlink, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(import.meta.url);
const sandbox = await mkdtemp(join(tmpdir(), "alua-phase-b-tests-"));
const env = { ...process.env, ALUA_PHASE_B_TEST_APP: sandbox };
for (const key of Object.keys(env)) if (key.startsWith("NEXT_PUBLIC_")) env[key] = "";
function run(command, args, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd, env, stdio: "inherit" });
    child.on("error", reject);
    child.on("exit", (code) => code === 0 ? resolve() : reject(new Error(`Verification exited with ${code}`)));
  });
}
try {
  for (const file of ["src", "public", "package.json", "tsconfig.json", "next.config.ts", "postcss.config.mjs"])
    await cp(join(root, file), join(sandbox, file), { recursive: true });
  await symlink(join(root, "node_modules"), join(sandbox, "node_modules"), "dir");
  await run(process.execPath, [require.resolve("next/dist/bin/next"), "build", "--webpack"], sandbox);
  await run(process.execPath, [join(dirname(require.resolve("@playwright/test/package.json")), "cli.js"), "test", "--config=playwright.phase-b.config.ts"], root);
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
} finally { await rm(sandbox, { recursive: true, force: true }); }
