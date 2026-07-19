import path from "path";

export function safeResolve(basePath: string, filePath: string): string {
  const resolvedBase = path.resolve(basePath);
  const resolvedTarget = path.resolve(resolvedBase, filePath);
  if (resolvedTarget === resolvedBase || resolvedTarget.startsWith(resolvedBase + path.sep)) {
    return resolvedTarget;
  }
  throw new Error("Invalid file path");
}