import { FastifyInstance } from "fastify";
import { loadModelConfig } from "../config/modelConfig";
import { sendToModel } from "../lib/modelClient";
import { safeResolve } from "../lib/safePaths";
import { loadProjectMemory } from "../lib/projectMemory";
import { safeExecuteCommand } from "../lib/safeTerminal";
import { z } from "zod";
import fs from "fs";
import path from "path";

const chatSchema = z.object({
  prompt: z.string().min(1),
  memoryFiles: z.array(z.string()).optional(),
});

const fileReadSchema = z.object({
  filePath: z.string().min(1),
});

const fileWriteSchema = z.object({
  filePath: z.string().min(1),
  content: z.string().min(1),
});

const terminalSchema = z.object({
  command: z.string().min(1),
  args: z.array(z.string()).default([]),
});

export async function aiController(fastify: FastifyInstance) {
  const config = loadModelConfig();
  const systemPrompt = fs.readFileSync(config.systemPromptPath, "utf8");
  const projectRules = fs.readFileSync(config.projectRulesPath, "utf8");
  const memoryPath = config.projectMemoryRoot;

  fastify.post("/chat", async (request, reply) => {
    const { prompt, memoryFiles } = chatSchema.parse(request.body);
    const memoryContent = loadProjectMemory(memoryPath, memoryFiles || []);
    const response = await sendToModel(config, systemPrompt, projectRules, memoryContent, prompt);
    return { response };
  });

  fastify.post("/file/read", async (request, reply) => {
    if (!config.allowedTools.includes("file_read")) return { error: "File read not allowed" };
    const { filePath } = fileReadSchema.parse(request.body);
    const allowedPath = safeResolve(config.repoRoot, filePath);
    if (!fs.existsSync(allowedPath)) return { error: "File not found" };
    const normalizedPath = path.normalize(filePath).replace(/\\/g, "/");
    const blockedFilenames = [".env", ".env.local", ".env.production"];
    const blockedExtensions = [".pem", ".key", ".p12", ".sqlite", ".db"];
    const basename = path.basename(normalizedPath);
    const extname = path.extname(normalizedPath);
    if (blockedFilenames.includes(basename) || blockedExtensions.includes(extname)) return { error: "File read not allowed" };
    const allowedExtensions = [".md", ".txt", ".json", ".ts", ".tsx", ".js", ".prisma"];
    if (!allowedExtensions.includes(extname)) return { error: "File extension not allowed" };
    const fileContent = fs.readFileSync(allowedPath, "utf8");
    return { content: fileContent };
  });

  fastify.post("/file/write", async (request, reply) => {
    if (!config.allowedTools.includes("file_write")) return { error: "File write not allowed" };
    const { filePath, content } = fileWriteSchema.parse(request.body);
    const allowedPath = safeResolve(config.repoRoot, filePath);
    const normalizedPath = path.normalize(filePath).replace(/\\/g, "/").replace(/^(\./)+/, "");
    const frontendPaths = ["frontend/", "client/", "web/", "app/", "pages/", "components/", "src/frontend/"];
    if (!config.allowFrontendFiles && frontendPaths.some(p => normalizedPath.startsWith(p))) return { error: "Frontend file write not allowed" };
    const blockedFilenames = [".env", ".env.local", ".env.production"];
    const blockedExtensions = [".pem", ".key", ".p12", ".sqlite", ".db"];
    const basename = path.basename(normalizedPath);
    const extname = path.extname(normalizedPath);
    if (blockedFilenames.includes(basename) || blockedExtensions.includes(extname)) return { error: "File write not allowed" };
    const allowedExtensions = [".md", ".txt", ".json", ".ts", ".tsx", ".js", ".prisma"];
    if (!allowedExtensions.includes(extname)) return { error: "File extension not allowed" };
    const dirPath = path.dirname(allowedPath);
    if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
    fs.writeFileSync(allowedPath, content);
    return { success: true };
  });

  fastify.post("/terminal", async (request, reply) => {
    if (!config.allowedTools.includes("terminal")) return { error: "Terminal not allowed" };
    const { command, args } = terminalSchema.parse(request.body);
    try {
      const result = await safeExecuteCommand(config.repoRoot, command, args, config.allowedTerminalCommands);
      return result;
    } catch (error) {
      return { error: error instanceof Error ? error.message : "Command execution failed" };
    }
  });
}