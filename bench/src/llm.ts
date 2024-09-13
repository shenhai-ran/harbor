import { config } from "./config.ts";
import { omit, sleep } from './utils.ts';

export type LLMOptions = {
  maxTokens?: number;
  temperature?: number;
}

export type LLMConfig = {
  model: string;
  apiUrl: string;
  apiKey?: string;
  options?: LLMOptions;
};

export class LLM {
  private llm: LLMConfig;

  constructor(llm: LLMConfig) {
    this.llm = llm;
  }

  async chat(message: string, options = {}): Promise<string> {
    const maxRetries = 4;
    let retries = 0;

    while (retries < maxRetries) {
      try {
        return await this.attemptChat(message, options);
      } catch (error) {
        retries++;
        if (retries >= maxRetries) {
          throw error;
        }
        console.warn(`Attempt ${retries} failed. Retrying in ${2 ** retries} seconds...`);
        await sleep(2 ** retries * 1000); // Exponential backoff
      }
    }

    throw new Error('Max retries reached');
  }

  private async attemptChat(message: string, options = {}): Promise<string> {
    const completionOptions = {
      ...(this.llm?.options || {}),
      ...options,
    };

    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };

    if (this.llm.apiKey) {
      headers['Authorization'] = `Bearer ${this.llm.apiKey}`;
    }

    if (config.debug) {
      console.debug(`>> ${message}`);
    }

    const body = JSON.stringify({
      ...completionOptions,
      model: this.llm.model,
      messages: [
        {
          role: 'user',
          content: message,
        }
      ],
      stream: false,
    });

    const response = await fetch(`${this.llm.apiUrl}/v1/chat/completions`, {
      method: 'POST',
      headers,
      body
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch completion: ${response.statusText}`);
    }

    const data = await response.json();
    const reply = data.choices[0].message.content.trim();

    if (config.debug) {
      console.debug(`<< ${reply}`);
    }

    return reply;
  }

  toJson() {
    return omit(this.llm, ['apiKey']);
  }
}