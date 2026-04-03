"use client";

import { useState, useRef, useEffect } from "react";
import { api } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { role: "user", content: text, timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const { response } = await api.chat(text);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response, timestamp: new Date() },
      ]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${e instanceof Error ? e.message : "Failed to get response"}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 180px)", gap: "1rem", paddingBottom: "1rem" }}>
      {/* Messages */}
      <div className="card" style={{ flex: 1, overflowY: "auto", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {messages.length === 0 && (
          <div className="empty-state" style={{ padding: "3rem 1rem" }}>
            <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>💬</div>
            <div>Ask the agent about its trading decisions, positions, research, or strategy.</div>
            <div style={{ fontSize: "0.8rem", marginTop: "0.75rem", color: "var(--text-muted)" }}>
              Try: &quot;Why did you sell XLE?&quot; · &quot;What&apos;s your current thesis?&quot; · &quot;Explain the risk alerts&quot;
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "80%",
              background: msg.role === "user" ? "var(--blue)" : "var(--bg-card-hover)",
              color: msg.role === "user" ? "#fff" : "var(--text)",
              padding: "0.75rem 1rem",
              borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
              fontSize: "0.9rem",
              lineHeight: 1.6,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {msg.content}
            <div style={{ fontSize: "0.65rem", opacity: 0.5, marginTop: "0.35rem", textAlign: "right" }}>
              {msg.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ alignSelf: "flex-start", display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            <span className="spinner" /> Thinking...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about trades, positions, strategy..."
          rows={2}
          disabled={loading}
          aria-label="Chat message input"
          style={{
            flex: 1,
            background: "var(--bg-card)",
            color: "var(--text)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            padding: "0.75rem 1rem",
            fontSize: "0.9rem",
            resize: "none",
            fontFamily: "inherit",
            lineHeight: 1.5,
          }}
        />
        <button
          className="primary"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{ alignSelf: "flex-end", padding: "0.75rem 1.25rem" }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
