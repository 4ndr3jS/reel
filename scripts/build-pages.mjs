import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
for (const [command, args] of [
  [process.platform === "win32" ? "python" : "python3", ["scripts/package-engine.py"]],
  [process.execPath, ["node_modules/vite/bin/vite.js", "build", "--config", "pages/vite.config.ts"]],
]) {
  const result = spawnSync(command, args, { cwd: root, stdio: "inherit", shell: false });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}
writeFileSync(path.join(root, "dist-pages/.nojekyll"), "");
