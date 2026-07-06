<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";

type Role = "user" | "assistant";

interface ChatMessage {
  role: Role;
  content: string;
  created_at?: string | null;
}

interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

const input = ref("");
const defaultMessages: ChatMessage[] = [
  {
    role: "assistant",
    content: "你好，我是你的 AI 助手。有什么想聊的？",
  },
];
const conversations = ref<Conversation[]>([]);
const activeConversationId = ref<number | null>(null);
const editingConversationId = ref<number | null>(null);
const editingTitle = ref("");
const messages = ref<ChatMessage[]>([...defaultMessages]);
const isSending = ref(false);
const isUploading = ref(false);
const isLoadingConversations = ref(false);
const errorMessage = ref("");
const uploadMessage = ref("");
const selectedFile = ref<File | null>(null);
const fileInputEl = ref<HTMLInputElement | null>(null);
const messagesEl = ref<HTMLElement | null>(null);

const activeConversation = computed(() =>
  conversations.value.find((conversation) => conversation.id === activeConversationId.value),
);
const canSend = computed(
  () => input.value.trim().length > 0 && !isSending.value && Boolean(activeConversationId.value),
);
const canClear = computed(
  () => !isSending.value && Boolean(activeConversationId.value) && messages.value.length > 0,
);
const canSaveTitle = computed(() => editingTitle.value.trim().length > 0 && !isSending.value);
const canUpload = computed(() => Boolean(selectedFile.value) && !isUploading.value);

function nowTimestamp() {
  return new Date().toISOString();
}

function displayMessages() {
  return messages.value.length ? messages.value : defaultMessages;
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

async function refreshConversations() {
  const response = await fetch("/api/chat/conversations");
  if (!response.ok) {
    throw new Error(`加载会话失败：${response.status}`);
  }

  const data = (await response.json()) as { conversations?: Conversation[] };
  conversations.value = data.conversations ?? [];
}

async function createConversation() {
  const response = await fetch("/api/chat/conversations", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title: "新会话" }),
  });

  if (!response.ok) {
    throw new Error(`新建会话失败：${response.status}`);
  }

  const data = (await response.json()) as { conversation: Conversation };
  conversations.value = [
    data.conversation,
    ...conversations.value.filter((conversation) => conversation.id !== data.conversation.id),
  ];
  activeConversationId.value = data.conversation.id;
  editingConversationId.value = null;
  editingTitle.value = "";
  messages.value = [...defaultMessages];
  await scrollToBottom();
}

async function loadHistory(conversationId = activeConversationId.value) {
  if (!conversationId) return;

  try {
    const response = await fetch(`/api/chat/conversations/${conversationId}/history`);
    if (!response.ok) return;

    const data = (await response.json()) as { messages?: ChatMessage[] };
    messages.value = data.messages?.length ? data.messages : [...defaultMessages];
    await scrollToBottom();
  } catch {
    messages.value = [...defaultMessages];
  }
}

async function loadInitialData() {
  isLoadingConversations.value = true;
  errorMessage.value = "";

  try {
    await refreshConversations();
    if (!conversations.value.length) {
      await createConversation();
      return;
    }

    activeConversationId.value = conversations.value[0].id;
    await loadHistory(activeConversationId.value);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "加载会话失败，请稍后再试。";
    messages.value = [...defaultMessages];
  } finally {
    isLoadingConversations.value = false;
  }
}

async function startConversation() {
  if (isSending.value) return;

  errorMessage.value = "";
  uploadMessage.value = "";

  try {
    await createConversation();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "新建会话失败，请稍后再试。";
  }
}

async function selectConversation(conversationId: number) {
  if (isSending.value || conversationId === activeConversationId.value) return;

  activeConversationId.value = conversationId;
  editingConversationId.value = null;
  editingTitle.value = "";
  errorMessage.value = "";
  uploadMessage.value = "";
  await loadHistory(conversationId);
}

function beginEditConversation(conversation: Conversation) {
  if (isSending.value) return;

  editingConversationId.value = conversation.id;
  editingTitle.value = conversation.title;
}

function cancelEditConversation() {
  editingConversationId.value = null;
  editingTitle.value = "";
}

async function saveConversationTitle(conversationId: number) {
  const title = editingTitle.value.trim();
  if (!title || isSending.value) return;

  errorMessage.value = "";

  try {
    const response = await fetch(`/api/chat/conversations/${conversationId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title }),
    });

    if (!response.ok) {
      throw new Error(`修改标题失败：${response.status}`);
    }

    const data = (await response.json()) as { conversation: Conversation };
    conversations.value = conversations.value.map((conversation) =>
      conversation.id === data.conversation.id ? data.conversation : conversation,
    );
    editingConversationId.value = null;
    editingTitle.value = "";
    await refreshConversations();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "修改标题失败，请稍后再试。";
  }
}

async function deleteConversation(conversation: Conversation) {
  if (isSending.value) return;

  const confirmed = window.confirm(`确定删除「${conversation.title}」吗？此操作会删除该会话中的消息。`);
  if (!confirmed) return;

  errorMessage.value = "";

  try {
    const response = await fetch(`/api/chat/conversations/${conversation.id}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error(`删除会话失败：${response.status}`);
    }

    const deletedActiveConversation = activeConversationId.value === conversation.id;
    conversations.value = conversations.value.filter((item) => item.id !== conversation.id);

    if (editingConversationId.value === conversation.id) {
      cancelEditConversation();
    }

    if (!deletedActiveConversation) {
      await refreshConversations();
      return;
    }

    await refreshConversations();
    if (conversations.value.length) {
      activeConversationId.value = conversations.value[0].id;
      await loadHistory(activeConversationId.value);
    } else {
      await createConversation();
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "删除会话失败，请稍后再试。";
  }
}

async function clearHistory() {
  if (isSending.value || !activeConversationId.value) return;

  errorMessage.value = "";

  try {
    const response = await fetch(
      `/api/chat/conversations/${activeConversationId.value}/history`,
      { method: "DELETE" },
    );

    if (!response.ok) {
      throw new Error(`清空失败：${response.status}`);
    }

    messages.value = [...defaultMessages];
    await refreshConversations();
    await scrollToBottom();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "清空失败，请稍后再试。";
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
    errorMessage.value = error instanceof Error ? error.message : "上传失败，请稍后再试。";
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
  const conversationId = activeConversationId.value;
  if (!content || isSending.value || !conversationId) return;

  errorMessage.value = "";
  input.value = "";

  if (messages.value.length === 1 && messages.value[0].role === "assistant" && !messages.value[0].created_at) {
    messages.value = [];
  }

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
        conversation_id: conversationId,
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

    await refreshConversations();
  } catch (error) {
    if (!messages.value[assistantIndex]?.content) {
      messages.value.splice(assistantIndex, 1);
    }

    errorMessage.value = error instanceof Error ? error.message : "发送失败，请稍后再试。";
  } finally {
    isSending.value = false;
    await scrollToBottom();
  }
}

onMounted(loadInitialData);
</script>

<template>
  <main class="app-shell">
    <aside class="conversation-sidebar" aria-label="会话列表">
      <div class="sidebar-header">
        <div>
          <p class="eyebrow">My Assistant</p>
          <h1>会话</h1>
        </div>
        <button class="new-chat-button" type="button" :disabled="isSending" @click="startConversation">
          +
        </button>
      </div>

      <div class="conversation-list">
        <article
          v-for="conversation in conversations"
          :key="conversation.id"
          class="conversation-item"
          :class="{ active: conversation.id === activeConversationId }"
        >
          <div v-if="editingConversationId === conversation.id" class="conversation-edit">
            <input
              v-model="editingTitle"
              class="conversation-input"
              type="text"
              maxlength="80"
              @keydown.enter.prevent="saveConversationTitle(conversation.id)"
              @keydown.esc.prevent="cancelEditConversation"
            />
            <div class="conversation-actions">
              <button
                class="icon-button confirm"
                type="button"
                title="保存标题"
                :disabled="!canSaveTitle"
                @click="saveConversationTitle(conversation.id)"
              >
                ✓
              </button>
              <button
                class="icon-button"
                type="button"
                title="取消修改"
                @click="cancelEditConversation"
              >
                ×
              </button>
            </div>
          </div>

          <template v-else>
            <button
              class="conversation-main"
              type="button"
              :disabled="isSending"
              @click="selectConversation(conversation.id)"
            >
              <span class="conversation-title">{{ conversation.title }}</span>
              <time class="conversation-time">{{ formatTimestamp(conversation.updated_at) }}</time>
            </button>
            <div class="conversation-actions">
              <button
                class="icon-button"
                type="button"
                title="修改标题"
                :disabled="isSending"
                @click="beginEditConversation(conversation)"
              >
                ✎
              </button>
              <button
                class="icon-button danger"
                type="button"
                title="删除会话"
                :disabled="isSending"
                @click="deleteConversation(conversation)"
              >
                ×
              </button>
            </div>
          </template>
        </article>
        <p v-if="isLoadingConversations" class="sidebar-empty">加载中...</p>
        <p v-else-if="!conversations.length" class="sidebar-empty">暂无会话</p>
      </div>
    </aside>

    <section class="chat-panel" aria-label="AI 对话">
      <header class="chat-header">
        <div>
          <p class="eyebrow">当前会话</p>
          <h2>{{ activeConversation?.title || "AI 对话助手" }}</h2>
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
          v-for="(message, index) in displayMessages()"
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
