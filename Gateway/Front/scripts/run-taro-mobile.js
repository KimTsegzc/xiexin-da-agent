const { spawn } = require("node:child_process");
const path = require("node:path");

const scriptName = process.argv[2];
const forwardedArgs = process.argv.slice(3);

if (!scriptName) {
  console.error("Missing target npm script name.");
  process.exit(1);
}

const taroMobileDir = path.resolve(__dirname, "..", "taro-mobile");
const npmExecutable = process.platform === "win32" ? "npm.cmd" : "npm";
const commandArgs = ["--prefix", taroMobileDir, "run", scriptName, "--", ...forwardedArgs];

const child = spawn(npmExecutable, commandArgs, {
  stdio: "inherit",
  shell: true,
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 1);
});

child.on("error", (error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});