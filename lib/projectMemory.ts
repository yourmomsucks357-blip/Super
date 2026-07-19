import fs from "fs";
import path from "path";
import { safeResolve } from "./safePaths";

const allowedExtensions = [".md", ".txt", ".json", ".ts", ".tsx", ".js", ".prisma"];
const blockedFilenames = [".env", ".env.local", ".env.production"];
const blockedExtensions = [".pem", ".key", ".p12", ".sqlite", ".db"];

export function loadProjectMemory(memoryRoot: string, requestedFiles: string[]): string {
  let memoryContent = "";
  for (const file of requestedFiles) {
    const ext = path.extname(file);
    if (!allowedExtensions.includes(ext)) continue;
    const normalizedFile = path.normalize(file).replace(/\\/g, "/");
    const basename = path.basename(normalizedFile);
    const extname = path.extname(normalizedFile);
    if (blockedFilenames.includes(basename) || blockedExtensions.includes(extname)) continue;
    const filePath = safeResolve(memoryRoot, file);
    if (fs.existsSync(filePath)) {
      const fileContent = fs.readFileSync(filePath, "utf8");
      if (fileContent.length <= 1024 * 1024) memoryContent += fileContent + "\n\n";
    }
  }
  return memoryContent;
}