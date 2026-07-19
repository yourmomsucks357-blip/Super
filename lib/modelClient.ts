import { ModelConfig } from "../config/modelConfig";

export async function sendToModel(
  config: ModelConfig,
  systemPrompt: string,
  projectRules: string,
  memoryContent: string,
  userPrompt: string
): Promise<string> {
  try {
    const url = config.baseUrl + "/v1/chat/completions";
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: config.modelName,
        temperature: config.temperature,
        top_p: config.top_p,
        max_tokens: config.max_tokens,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: projectRules + "\n\n" + memoryContent + "\n\n" + userPrompt }
        ]
      })
    });

    if (!response.ok) {
      throw new Error("Model API error: " + response.statusText);
    }

    const data = await response.json();
    if (!data.choices || data.choices.length === 0 || !data.choices[0].message || typeof data.choices[0].message.content !== "string") {
      throw new Error("Invalid model API response");
    }

    return data.choices[0].message.content;
  } catch (error) {
    console.error("Error sending request to model:", error);
    throw error;
  }
}