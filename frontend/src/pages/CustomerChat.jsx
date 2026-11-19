import { useState, useEffect, useRef } from "react";
import { API_BASE_URL } from "../apiConfig";

export default function CustomerChat() {
  const messagesEndRef = useRef(null);
  // Phase 1 Topic 3: useState for managing state
  const [sessionId, setSessionId] = useState(() => {
    const saved = localStorage.getItem("chat_session_id");
    if (saved) return saved;
    const newId = `session_${Date.now()}`;
    localStorage.setItem("chat_session_id", newId);
    return newId;
  });

  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content: "Hello! 👋 I'm your AI Customer Support Assistant. How can I help you today with your orders, returns, shipping, or warranty?",
      time: "Just now",
      sources: [],
    },
  ]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Suggestions for demo/testing
  const sampleQuestions = [
    "What is your return policy?",
    "How long does shipping take?",
    "What are the return fees for opened items?",
    "I bought parcel 1 year ago still not arrived, this is fraud!",
  ];

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(textToSend) {
    const text = textToSend || query;
    if (!text.trim() || loading) return;

    const userMessage = {
      id: Date.now(),
      role: "user",
      content: text,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const aiMessageId = Date.now() + 1;
    const initialAiMessage = {
      id: aiMessageId,
      role: "assistant",
      content: "",
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      sources: [],
      isStreaming: true,
    };

    // Add user message and streaming assistant placeholder immediately
    setMessages((prev) => [...prev, userMessage, initialAiMessage]);
    setQuery("");
    setLoading(true);
    setError(null);

    try {
      // Connect to Server-Sent Events (SSE) streaming endpoint
      const response = await fetch(`${API_BASE_URL}/api/chat/stream/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text, session_id: sessionId }),
      });

      if (!response.ok) {
        throw new Error("Failed to connect to streaming server.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let accumulatedContent = "";
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // keep partial line in buffer

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event = JSON.parse(line.slice(6));
              if (event.type === "token") {
                accumulatedContent += event.content;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === aiMessageId
                      ? { ...msg, content: accumulatedContent }
                      : msg
                  )
                );
              } else if (event.type === "done") {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === aiMessageId
                      ? {
                          ...msg,
                          content: event.answer || accumulatedContent,
                          sources: event.sources || [],
                          cacheHit: event.cache_hit,
                          source: event.source,
                          latency: event.latency_ms,
                          severity: event.severity,
                          isStreaming: false,
                        }
                      : msg
                  )
                );
              }
            } catch (jsonErr) {
              // ignore partial line parsing
            }
          }
        }
      }

      // Process any trailing done event remaining in buffer
      if (buffer.startsWith("data: ")) {
        try {
          const event = JSON.parse(buffer.slice(6));
          if (event.type === "done") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? {
                      ...msg,
                      content: event.answer || accumulatedContent,
                      sources: event.sources || [],
                      cacheHit: event.cache_hit,
                      source: event.source,
                      latency: event.latency_ms,
                      severity: event.severity,
                      isStreaming: false,
                    }
                  : msg
              )
            );
          }
        } catch (e) {}
      }

      // Guarantee isStreaming is flipped to false when stream ends
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMessageId ? { ...msg, isStreaming: false } : msg
        )
      );
      setLoading(false);
    } catch (err) {
      // Fallback: standard POST request if streaming connection drops
      fetch(`${API_BASE_URL}/api/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text, session_id: sessionId }),
      })
        .then((res) => res.json())
        .then((data) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === aiMessageId
                ? {
                    ...msg,
                    content: data.answer,
                    sources: data.sources || [],
                    cacheHit: data.cache_hit,
                    source: data.source,
                    latency: data.latency_ms,
                    severity: data.severity,
                    isStreaming: false,
                  }
                : msg
            )
          );
          setLoading(false);
        })
        .catch((fallbackErr) => {
          setError(fallbackErr.message);
          setLoading(false);
        });
    }
  }

  function handleSubmit(e) {
    e.preventDefault(); // Phase 1 Topic 6: preventDefault
    sendMessage(query);
  }

  function handleResetChat() {
    // Clear history in Redis backend and generate fresh session ID
    fetch(`${API_BASE_URL}/api/chat/clear/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    }).catch(() => {});

    const newId = `session_${Date.now()}`;
    localStorage.setItem("chat_session_id", newId);
    setSessionId(newId);
    setMessages([
      {
        id: "welcome_new",
        role: "assistant",
        content: "New conversation started! How may I assist you with TechMart services today?",
        time: "Just now",
        sources: [],
      },
    ]);
  }

  return (
    <div className="chat-page-container">
      {/* Top Header */}
      <div className="chat-header">
        <div className="chat-header-info">
          <h2>💬 Customer Support</h2>
          <p>Ask your questions and get instant verified answers from our AI knowledge base</p>
        </div>
        <button onClick={handleResetChat} className="btn-secondary" title="Start a fresh chat session">
          🔄 New Chat
        </button>
      </div>

      {/* Suggestion Chips */}
      <div className="suggestion-chips-container">
        <span className="chips-label">Try asking:</span>
        {sampleQuestions.map((q, idx) => (
          <button
            key={idx}
            className="chip-btn"
            onClick={() => sendMessage(q)}
            disabled={loading}
          >
            {q}
          </button>
        ))}
      </div>

      {/* Messages Scroll Area */}
      <div className="messages-area">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`message-row ${msg.role === "user" ? "message-user" : "message-assistant"}`}
          >
            <div className={`message-bubble ${msg.role === "user" ? "bubble-user" : "bubble-assistant"}`}>
              {/* Message Header/Badge */}
              {msg.role === "assistant" && (
                <div className="bubble-top-meta">
                  <span className="ai-icon">🤖 SupportAI</span>
                  {msg.cacheHit && <span className="badge badge-cache">⚡ Cache Hit</span>}
                  {msg.severity === "high" && <span className="badge badge-high">⚠️ High Severity</span>}
                  {msg.latency && <span className="latency-label">({msg.latency}ms)</span>}
                </div>
              )}

              {/* Message Body */}
              <div className="bubble-text">
                {msg.isStreaming && !msg.content ? (
                  <p className="streaming-thinking">Searching knowledge base & drafting response...</p>
                ) : (
                  (msg.content || "")
                    .replace(/<scratchpad>[\s\S]*?<\/scratchpad>/gi, "")
                    .replace(/<scratchpad>[\s\S]*/gi, "")
                    .replace(/<\/?scratchpad>/gi, "")
                    .replace(/\*{3,}/g, "")
                    .replace(/^\s*\*\s*\*\*(.*?)\*\*:/gm, "• $1:")
                    .replace(/\*\*(.*?)\*\*/g, "$1")
                    .split("\n")
                    .map((line, lidx) => (
                      <p key={lidx}>{line}</p>
                    ))
                )}
                {msg.isStreaming && loading && msg.content && (
                  <span className="streaming-cursor">|</span>
                )}
              </div>

              {/* Cited Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="sources-container">
                  <p className="sources-title">Verified Sources:</p>
                  <div className="sources-list">
                    {msg.sources.map((src, sidx) => (
                      <span key={sidx} className="source-tag">
                        📄 {src.source} (Page {src.page})
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Timestamp */}
              <span className="bubble-timestamp">{msg.time}</span>
            </div>
          </div>
        ))}

        {/* Error State */}
        {error && (
          <div className="error-alert">
            <p>⚠️ {error}</p>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input Form (Phase 1 Topic 5 & 6) */}
      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Type your question (e.g. Where is my order? Return policy?)..."
          disabled={loading}
          className="chat-input"
        />
        <button type="submit" disabled={loading || !query.trim()} className="btn-send">
          {loading ? "Sending..." : "Send"}
        </button>
      </form>
    </div>
  );
}
