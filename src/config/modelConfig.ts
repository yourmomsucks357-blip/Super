import fs from "fs";
import path from "path";
import { z } from "zod";

export interface ModelConfig {
  modelName: string;
  baseUrl: string;
  temperature: number;
  top_p: number;
  max_tokens: number;
  systemPromptPath: string;
  projectRulesPath: string;
  allowedTools: string[];
  responseMode: string;
  tokenSaving: boolean;
  verbosity: string;
  allowExplanations: boolean;
  allowSummaries: boolean;
  allowNextSteps: boolean;
  strictFileListOnly: boolean;
  strictProjectScope: boolean;
  lowRestrictionCodingMode: boolean;
  allowedTerminalCommands: Record<string, { args: string[]; allowExtraArgs: boolean }[]>;
  allowFrontendFiles: boolean;
  repoRoot: string;
  projectMemoryRoot: string;
}

export const ModelConfigSchema = z.object({
  modelName: z.string(),
  baseUrl: z.string().min(1),
  temperature: z.number().min(0).max(1),
  top_p: z.number().min(0).max(1),
  max_tokens: z.number().min(1).max(4096),
  systemPromptPath: z.string(),
  projectRulesPath: z.string(),
  allowedTools: z.array(z.string()),
  responseMode: z.string(),
  tokenSaving: z.boolean(),
  verbosity: z.string(),
  allowExplanations: z.boolean(),
  allowSummaries: z.boolean(),
  allowNextSteps: z.boolean(),
  strictFileListOnly: z.boolean(),
  strictProjectScope: z.boolean(),
  lowRestrictionCodingMode: z.boolean(),
  allowedTerminalCommands: z.record(
    z.string(),
    z.array(
      z.object({
        args: z.array(z.string()),
        allowExtraArgs: z.boolean(),
      })
    )
  ),
  allowFrontendFiles: z.boolean(),
  repoRoot: z.string(),
  projectMemoryRoot: z.string(),
});

export function loadModelConfig(): ModelConfig {
  const configPath = path.join(process.cwd(), "config/model-controller.json");
  const configFile = fs.readFileSync(configPath, "utf8");
  const config = JSON.parse(configFile);
  return ModelConfigSchema.parse(config);
}