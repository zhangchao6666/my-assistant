<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";

type Role = "user" | "assistant";

interface ChatMessage {
  role: Role;
  content: string;
  created_at?: string | null;
}

const input = ref("");
const defaultMessages: ChatMessage[] = [
  {
    role: "assistant",
    content: "你好，我是你的 AI 助手。有什么想聊的？",
  },
];
const messages = ref<ChatMessage[]>([...defaultMessages]);
const isSending = ref(false);
const isUploading = ref(false);
const errorMessage = ref("");
const uploadMessage = ref("");
const selectedFile = ref<File | null>(null);
const fileInputEl = ref<HTMLInputElement | null>(null);
const messagesEl = ref<HTMLElement | null>(null);

const canSend = computed(() => input.value.trim().length > 0 && !isSending.value);
const canClear = computed(() => !isSending.value && messages.value.length > 0);
const canUpload = computed(() => Boolean(selectedFile.value) && !isUploading.value);

function nowTimestamp() {
  return new Date().toISOString();
}

function formatTimestamp(timestamp?: string | null) {
  if (!timestamp) return "";

  const normalizedTimestamp = timestamp.includes("T")
    ? timestamp
    : `${timestamp.replace(" ", "T")}Z`;
  const date = new Date(normalizedTimestamp);

  if (Number.isNaN(date.getTime())) return timestamp;

  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function scrollToBottom() {
  await nextTick();
  messagesEl.value?.scrollTo({
    top: messagesEl.value.scrollHeight,
    behavior: "smooth",
  });
}

function appendToMessage(index: number, chunk: string) {
  const message = messages.value[index];
  if (!message) return;

  messages.value[index] = {
    ...message,
    content: message.content + chunk,
  };
}

async function loadHistory() {
  try {
    const response = await fetch("/api/chat/history");
    if (!response.ok) return;

    const data = (await response.json()) as { messages?: ChatMessage[] };
    if (data.messages?.length) {
      messages.value = data.messages;
      await scrollToBottom();
    }
  } catch {
    messages.value = [...defaultMessages];
  }
}

async function clearHistory() {
  if (isSending.value) return;

  errorMessage.value = "";

  try {
    const response = await fetch("/api/chat/history", {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error(`清空失败：${response.status}`);
    }

    messages.value = [...defaultMessages];
    await scrollToBottom();
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "清空失败，请稍后再试。";
  }
}

function chooseFile() {
  if (isUploading.value) return;
  fileInputEl.value?.click();
}

function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  selectedFile.value = target.files?.[0] ?? null;
  uploadMessage.value = "";
}

async function uploadFile() {
  const file = selectedFile.value;
  if (!file || isUploading.value) return;

  errorMessage.value = "";
  uploadMessage.value = "";
  isUploading.value = true;

  try {
    const response = await fetch(
      `/api/rag/upload?filename=${encodeURIComponent(file.name)}`,
      {
        method: "POST",
        headers: {
          "Content-Type": file.type || "text/plain; charset=utf-8",
        },
        body: await file.arrayBuffer(),
      },
    );

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `上传失败：${response.status}`);
    }

    const data = (await response.json()) as { chunks?: number };
    uploadMessage.value = `已上传 ${file.name}，写入 ${data.chunks ?? 0} 个片段。`;
    selectedFile.value = null;
    if (fileInputEl.value) {
      fileInputEl.value.value = "";
    }
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "上传失败，请稍后再试。";
  } finally {
    isUploading.value = false;
  }
}

async function readStream(response: Response, messageIndex: number) {
  if (!response.body) {
    throw new Error("浏览器不支持流式响应");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    appendToMessage(messageIndex, decoder.decode(value, { stream: true }));
    await scrollToBottom();
  }

  const remaining = decoder.decode();
  if (remaining) {
    appendToMessage(messageIndex, remaining);
  }
}

async function sendMessage() {
  const content = input.value.trim();
  if (!content || isSending.value) return;

  errorMessage.value = "";
  input.value = "";
  messages.value.push({ role: "user", content, created_at: nowTimestamp() });
  messages.value.push({ role: "assistant", content: "", created_at: nowTimestamp() });

  const assistantIndex = messages.value.length - 1;

  isSending.value = true;
  await scrollToBottom();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages: [
          {
            role: "user",
            content,
          },
        ],
      }),
    });

    if (!response.ok) {
      throw new Error(`请求失败：${response.status}`);
    }

    await readStream(response, assistantIndex);

    if (!messages.value[assistantIndex]?.content.trim()) {
      messages.value[assistantIndex] = {
        role: "assistant",
        content: "我暂时没有收到有效回复。",
        created_at: nowTimestamp(),
      };
    }
  } catch (error) {
    if (!messages.value[assistantIndex]?.content) {
      messages.value.splice(assistantIndex, 1);
    }

    errorMessage.value =
      error instanceof Error ? error.message : "发送失败，请稍后再试。";
  } finally {
    isSending.value = false;
    await scrollToBottom();
  }
}

onMounted(loadHistory);
</script>

<template>
  <main class="app-shell">
    <section class="chat-panel" aria-label="AI 对话">
      <header class="chat-header">
        <div>
          <p class="eyebrow">My Assistant</p>
          <h1>AI 对话助手</h1>
        </div>
        <button
          class="clear-button"
          type="button"
          :disabled="!canClear"
          @click="clearHistory"
        >
          清空记录
        </button>
      </header>

      <div ref="messagesEl" class="message-list">
        <article
          v-for="(message, index) in messages"
          :key="`${message.role}-${index}`"
          class="message-row"
          :class="message.role"
        >
          <div class="message-stack">
            <div class="message-bubble" :class="{ typing: isSending && !message.content }">
              {{ message.content || "思考中..." }}
            </div>
            <time v-if="message.created_at" class="message-time">
              {{ formatTimestamp(message.created_at) }}
            </time>
          </div>
        </article>
      </div>

      <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

      <section class="upload-bar" aria-label="上传知识库文件">
        <input
          ref="fileInputEl"
          class="file-input"
          type="file"
          accept=".txt,.md,.csv,.json,.log,text/*"
          @change="handleFileChange"
        />
        <button class="file-button" type="button" :disabled="isUploading" @click="chooseFile">
          选择文件
        </button>
        <span class="file-name">
          {{ selectedFile?.name || "上传文本文件用于本地 RAG" }}
        </span>
        <button class="upload-button" type="button" :disabled="!canUpload" @click="uploadFile">
          {{ isUploading ? "上传中" : "上传" }}
        </button>
        <span v-if="uploadMessage" class="upload-status">{{ uploadMessage }}</span>
      </section>

      <form class="composer" @submit.prevent="sendMessage">
        <textarea
          v-model="input"
          rows="1"
          placeholder="输入消息，按 Enter 发送"
          @keydown.enter.exact.prevent="sendMessage"
        ></textarea>
        <button type="submit" :disabled="!canSend">
          {{ isSending ? "发送中" : "发送" }}
        </button>
      </form>
    </section>
  </main>
</template>
