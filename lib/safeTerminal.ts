import { spawn } from "child_process";
import { safeResolve } from "./safePaths";

export function safeExecuteCommand(repoRoot: string, command: string, args: string[], allowedCommands: Record<string, { args: string[]; allowExtraArgs: boolean }[]>): Promise<{ stdout: string; stderr: string; exitCode: number }> {
  return new Promise((resolve, reject) => {
    const rules = allowedCommands[command];
    if (!rules) return reject(new Error("Command not allowed"));
    const isAllowed = rules.some((rule) => {
      const prefixMatches = rule.args.length <= args.length && rule.args.every((value, index) => args[index] === value);
      if (!prefixMatches) return false;
      return rule.allowExtraArgs ? true : rule.args.length === args.length;
    });
    if (!isAllowed) return reject(new Error("Command arguments not allowed"));
    const resolvedRepoRoot = safeResolve(repoRoot, "");
    const child = spawn(command, args, { cwd: resolvedRepoRoot, shell: false });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (data) => { stdout += data.toString(); });
    child.stderr.on("data", (data) => { stderr += data.toString(); });
    child.on("error", reject);
    child.on("close", (code) => { resolve({ stdout, stderr, exitCode: code }); });
  });
}