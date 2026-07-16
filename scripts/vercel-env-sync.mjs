import { execSync, spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

/** Push a trimmed secret to Vercel production without shell echo corruption. */
export function syncVercelEnv(name, value) {
  const trimmed = value?.trim();
  if (!trimmed) {
    console.log(`  skip ${name} (empty)`);
    return;
  }

  console.log(`  sync ${name} → production (${trimmed.length} chars)`);
  try {
    execSync(`npx vercel env rm ${name} production -y`, {
      cwd: ROOT,
      stdio: "ignore",
      shell: true,
    });
  } catch {
    /* not set yet */
  }

  const result = spawnSync("npx", ["vercel", "env", "add", name, "production"], {
    cwd: ROOT,
    input: trimmed,
    stdio: ["pipe", "inherit", "inherit"],
    shell: true,
  });

  if (result.status !== 0) {
    throw new Error(`Vercel env add failed for ${name} (exit ${result.status})`);
  }
}

export { ROOT };
