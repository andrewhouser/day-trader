"use client";

import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";

import styles from "./Chat.module.css";

interface Message {
  content: string;
  role: "assistant" | "user";
  timestamp: Date;
}

export function Chat() {
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { content: text, role: "user", timestamp: new Date() };
    setInput("");
    setLoading(true);
    setMessages((prev) => [...prev, userMsg]);

    try {
      const { response } = await api.chat(text);
      setMessages((prev) => [
        ...prev,
        { content: response, role: "assistant", timestamp: new Date() },
      ]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        {
          content: `Error: ${e instanceof Error ? e.message : "Failed to get response"}`,
          role: "assistant",
          timestamp: new Date(),
        },
      ]);
    } finally {
      inputRef.current?.focus();
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className={styles.container}>
      <div className={`card ${styles.messagesArea}`}>
        {messages.length === 0 && (
          <div className="empty-state">
            <div className={styles.welcomeEmoji}>💬</div>
            <div>Ask the agent about its trading decisions, positions, research, or strategy.</div>
            <div className={styles.welcomeHint}>
              Try: &quot;Why did you sell XLE?&quot; · &quot;What&apos;s your current
              thesis?&quot; · &quot;Explain the risk alerts&quot;
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            className={msg.role === "user" ? styles.userMessage : styles.assistantMessage}
            key={i}
          >
            {msg.content}
            <div className={styles.timestamp}>{msg.timestamp.toLocaleTimeString()}</div>
          </div>
        ))}
        {loading && (
          <div className={styles.thinkingRow}>
            <span className="spinner" /> Thinking...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className={styles.inputRow}>
        <textarea
          aria-label="Chat message input"
          className={styles.textarea}
          disabled={loading}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about trades, positions, strategy..."
          ref={inputRef}
          rows={2}
          value={input}
        />
        <button
          className={`primary ${styles.sendButton}`}
          disabled={loading || !input.trim()}
          onClick={handleSend}
        >
          Send
        </button>
      </div>
    </div>
  );
}
