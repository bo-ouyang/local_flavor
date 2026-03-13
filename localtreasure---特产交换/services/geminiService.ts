import { GoogleGenAI } from "@google/genai";

// Initialize Gemini Client
// WARNING: process.env.API_KEY must be set in the environment.
// In a real production app, ensure backend proxy or strict quotas.
const getClient = () => {
  const apiKey = process.env.API_KEY;
  if (!apiKey) {
    console.error("API Key not found");
    return null;
  }
  return new GoogleGenAI({ apiKey });
};

export const generateProductDescription = async (
  title: string,
  category: string,
  tags: string,
  imageBase64?: string
): Promise<string> => {
  const client = getClient();
  if (!client) return "无法连接到AI服务，请手动输入描述。";

  try {
    const prompt = `
      我正在上架一个特产到交换平台。
      产品名称: ${title}
      类别: ${category}
      关键词: ${tags}
      
      请帮我写一段吸引人的产品描述（100字以内）。
      重点突出：产地特色、口感/工艺、以及适合交换的场景。
      语气：真诚、热情、像是一个懂行的当地人在推荐。
      不要包含Markdown格式，只返回纯文本。
    `;

    const response = await client.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: prompt,
      config: {
        thinkingConfig: { thinkingBudget: 0 } // Fast response needed
      }
    });

    return response.text || "AI 生成描述失败，请重试。";
  } catch (error) {
    console.error("Gemini Error:", error);
    return "AI 服务暂时不可用，请稍后再试。";
  }
};