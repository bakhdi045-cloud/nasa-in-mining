// Launcher used by Playwright's webServer. On Windows the virtualenv `python.exe` is a trampoline that starts the real
// interpreter as a child: stopping only the trampoline left the server running and the test run never exited.
// This launcher owns the child with no shared pipes and removes the whole process tree when it is stopped.
import { spawn, spawnSync } from "node:child_process";

const [command, ...args] = process.argv.slice(2);
const child = spawn(command, args, { stdio: "ignore", windowsHide: true });
let stopping = false;

function stop() {
  if (stopping) return;
  stopping = true;
  try {
    if (process.platform === "win32") spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
    else child.kill("SIGTERM");
  } catch { /* already gone */ }
}

for (const sig of ["SIGINT", "SIGTERM", "SIGBREAK", "SIGHUP"]) process.on(sig, () => { stop(); process.exit(0); });
process.on("exit", stop);
child.on("exit", (code) => process.exit(code ?? 0));
