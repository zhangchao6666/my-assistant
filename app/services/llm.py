from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

class LLM:

    def chat(self, messages: list[dict]) -> str:

        response = client.chat.completions.create(
            model="qwen3.6",
            messages=messages
        )

        return response.choices[0].message.content