import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { WsClient } from "../ws-client";
import type { WsState } from "../ws-client";

// ---------------------------------------------------------------------------
// Mock WebSocket
// ---------------------------------------------------------------------------

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  url: string;
  send = vi.fn();
  close = vi.fn();

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  simulateOpen() {
    this.onopen?.();
  }

  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateClose() {
    this.onclose?.();
  }

  simulateError() {
    this.onerror?.();
  }
}

vi.stubGlobal("WebSocket", MockWebSocket);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createClient(overrides: Partial<ConstructorParameters<typeof WsClient>[0]> = {}) {
  return new WsClient({
    url: "ws://localhost:8000/ws/chat/",
    getToken: () => "test-jwt-token",
    ...overrides,
  });
}

function lastWs(): MockWebSocket {
  return MockWebSocket.instances[MockWebSocket.instances.length - 1];
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  MockWebSocket.instances = [];
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("WsClient", () => {
  // -------------------------------------------------------------------------
  // 1. Initial state
  // -------------------------------------------------------------------------
  describe("initial state", () => {
    it("is 'disconnected' before connect is called", () => {
      const client = createClient();
      expect(client.state).toBe("disconnected");
    });
  });

  // -------------------------------------------------------------------------
  // 2. connect() creates WebSocket with token in query string
  // -------------------------------------------------------------------------
  describe("connect()", () => {
    it("creates a WebSocket with token appended via ?token=", () => {
      const client = createClient();
      client.connect();

      expect(MockWebSocket.instances).toHaveLength(1);
      expect(lastWs().url).toBe("ws://localhost:8000/ws/chat/?token=test-jwt-token");
    });

    it("sets state to 'connecting' immediately", () => {
      const client = createClient();
      client.connect();

      expect(client.state).toBe("connecting");
    });

    // 3. connect() does nothing if no token
    it("does nothing when getToken returns null", () => {
      const client = createClient({ getToken: () => null });
      client.connect();

      expect(MockWebSocket.instances).toHaveLength(0);
      expect(client.state).toBe("disconnected");
    });

    // 4. connect() does nothing if already connecting/connected
    it("does nothing if already connecting", () => {
      const client = createClient();
      client.connect();
      client.connect();

      expect(MockWebSocket.instances).toHaveLength(1);
    });

    it("does nothing if already connected", () => {
      const client = createClient();
      client.connect();
      lastWs().simulateOpen();

      expect(client.state).toBe("connected");
      client.connect();

      expect(MockWebSocket.instances).toHaveLength(1);
    });
  });

  // -------------------------------------------------------------------------
  // 5. On open: state -> "connected", queued messages flushed
  // -------------------------------------------------------------------------
  describe("on open", () => {
    it("transitions state to 'connected'", () => {
      const client = createClient();
      client.connect();
      lastWs().simulateOpen();

      expect(client.state).toBe("connected");
    });

    it("flushes queued messages", () => {
      const client = createClient();
      client.send({ type: "ping", id: 1 });
      client.send({ type: "ping", id: 2 });

      client.connect();
      const ws = lastWs();
      expect(ws.send).not.toHaveBeenCalled();

      ws.simulateOpen();

      expect(ws.send).toHaveBeenCalledTimes(2);
      expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ type: "ping", id: 1 }));
      expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ type: "ping", id: 2 }));
    });
  });

  // -------------------------------------------------------------------------
  // 6. On message: parses JSON, emits event by `type` field
  // -------------------------------------------------------------------------
  describe("on message", () => {
    it("parses JSON and emits event matching the type field", () => {
      const client = createClient();
      const handler = vi.fn();
      client.on("chat.message", handler);

      client.connect();
      lastWs().simulateOpen();
      lastWs().simulateMessage({ type: "chat.message", text: "hello" });

      expect(handler).toHaveBeenCalledOnce();
      expect(handler).toHaveBeenCalledWith({ type: "chat.message", text: "hello" });
    });

    it("does not emit when type field is missing", () => {
      const client = createClient();
      const handler = vi.fn();
      client.on("chat.message", handler);

      client.connect();
      lastWs().simulateOpen();
      lastWs().simulateMessage({ text: "no type" });

      expect(handler).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // 7. On close (unintentional): state -> "reconnecting", schedules reconnect
  // -------------------------------------------------------------------------
  describe("on close (unintentional)", () => {
    it("transitions state to 'reconnecting'", () => {
      const client = createClient();
      client.connect();
      lastWs().simulateOpen();
      lastWs().simulateClose();

      expect(client.state).toBe("reconnecting");
    });

    it("schedules a reconnect attempt", () => {
      const client = createClient();
      client.connect();
      lastWs().simulateOpen();
      lastWs().simulateClose();

      expect(MockWebSocket.instances).toHaveLength(1);

      vi.advanceTimersByTime(1000);

      expect(MockWebSocket.instances).toHaveLength(2);
    });
  });

  // -------------------------------------------------------------------------
  // 8. disconnect(): intentional close, no reconnect
  // -------------------------------------------------------------------------
  describe("disconnect()", () => {
    it("transitions state to 'disconnected'", () => {
      const client = createClient();
      client.connect();
      lastWs().simulateOpen();

      client.disconnect();

      expect(client.state).toBe("disconnected");
    });

    it("calls close on the WebSocket", () => {
      const client = createClient();
      client.connect();
      const ws = lastWs();
      ws.simulateOpen();

      client.disconnect();

      expect(ws.close).toHaveBeenCalledOnce();
    });

    it("does not schedule reconnect after intentional close", () => {
      const client = createClient();
      client.connect();
      lastWs().simulateOpen();

      client.disconnect();

      vi.advanceTimersByTime(60_000);

      expect(MockWebSocket.instances).toHaveLength(1);
    });

    it("clears the message queue", () => {
      const client = createClient();
      client.send({ type: "queued" });

      client.disconnect();

      // Reconnect and verify no queued messages are sent
      client.connect();
      const ws = lastWs();
      ws.simulateOpen();

      expect(ws.send).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // 9. send() when connected: sends JSON immediately
  // -------------------------------------------------------------------------
  describe("send()", () => {
    it("sends JSON string via WebSocket when connected", () => {
      const client = createClient();
      client.connect();
      const ws = lastWs();
      ws.simulateOpen();

      client.send({ type: "chat.send", text: "hi" });

      expect(ws.send).toHaveBeenCalledOnce();
      expect(ws.send).toHaveBeenCalledWith(
        JSON.stringify({ type: "chat.send", text: "hi" }),
      );
    });

    // 10. send() when not connected: queues, sends on reconnect
    it("queues messages when not connected and sends them on reconnect", () => {
      const client = createClient();
      client.connect();
      lastWs().simulateOpen();

      // Simulate unintentional close
      lastWs().simulateClose();
      expect(client.state).toBe("reconnecting");

      // Send while reconnecting — should be queued
      client.send({ type: "chat.send", text: "queued-msg" });

      // Trigger reconnect
      vi.advanceTimersByTime(1000);
      const ws2 = lastWs();
      expect(ws2.send).not.toHaveBeenCalled();

      // Open the new connection — queue should flush
      ws2.simulateOpen();
      expect(ws2.send).toHaveBeenCalledOnce();
      expect(ws2.send).toHaveBeenCalledWith(
        JSON.stringify({ type: "chat.send", text: "queued-msg" }),
      );
    });

    it("queues messages sent before connect is called", () => {
      const client = createClient();
      client.send({ type: "early", id: 1 });

      client.connect();
      const ws = lastWs();
      ws.simulateOpen();

      expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ type: "early", id: 1 }));
    });
  });

  // -------------------------------------------------------------------------
  // 11. on() subscribes to events, returns unsubscribe function
  // -------------------------------------------------------------------------
  describe("on()", () => {
    it("subscribes to events and receives payloads", () => {
      const client = createClient();
      const handler = vi.fn();
      client.on("presence.update", handler);

      client.connect();
      lastWs().simulateOpen();
      lastWs().simulateMessage({ type: "presence.update", user_id: "u1", status: "online" });

      expect(handler).toHaveBeenCalledOnce();
      expect(handler).toHaveBeenCalledWith({
        type: "presence.update",
        user_id: "u1",
        status: "online",
      });
    });

    it("returns an unsubscribe function that stops delivery", () => {
      const client = createClient();
      const handler = vi.fn();
      const unsubscribe = client.on("chat.message", handler);

      client.connect();
      lastWs().simulateOpen();
      lastWs().simulateMessage({ type: "chat.message", text: "first" });

      expect(handler).toHaveBeenCalledOnce();

      unsubscribe();

      lastWs().simulateMessage({ type: "chat.message", text: "second" });

      expect(handler).toHaveBeenCalledOnce();
    });

    it("supports multiple handlers for the same event", () => {
      const client = createClient();
      const handler1 = vi.fn();
      const handler2 = vi.fn();
      client.on("chat.message", handler1);
      client.on("chat.message", handler2);

      client.connect();
      lastWs().simulateOpen();
      lastWs().simulateMessage({ type: "chat.message", text: "hi" });

      expect(handler1).toHaveBeenCalledOnce();
      expect(handler2).toHaveBeenCalledOnce();
    });

    it("does not fire handlers for unrelated events", () => {
      const client = createClient();
      const handler = vi.fn();
      client.on("chat.message", handler);

      client.connect();
      lastWs().simulateOpen();
      lastWs().simulateMessage({ type: "presence.update", status: "online" });

      expect(handler).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // 12. onStateChange() subscribes to state changes, returns unsubscribe
  // -------------------------------------------------------------------------
  describe("onStateChange()", () => {
    it("fires handler on each state transition", () => {
      const client = createClient();
      const stateHandler = vi.fn();
      client.onStateChange(stateHandler);

      client.connect();
      expect(stateHandler).toHaveBeenCalledWith("connecting");

      lastWs().simulateOpen();
      expect(stateHandler).toHaveBeenCalledWith("connected");

      lastWs().simulateClose();
      expect(stateHandler).toHaveBeenCalledWith("reconnecting");
    });

    it("returns an unsubscribe function that stops notifications", () => {
      const client = createClient();
      const stateHandler = vi.fn();
      const unsubscribe = client.onStateChange(stateHandler);

      client.connect();
      expect(stateHandler).toHaveBeenCalledOnce();

      unsubscribe();

      lastWs().simulateOpen();
      expect(stateHandler).toHaveBeenCalledOnce();
    });

    it("supports multiple state change handlers", () => {
      const client = createClient();
      const handler1 = vi.fn();
      const handler2 = vi.fn();
      client.onStateChange(handler1);
      client.onStateChange(handler2);

      client.connect();

      expect(handler1).toHaveBeenCalledWith("connecting");
      expect(handler2).toHaveBeenCalledWith("connecting");
    });

    it("does not fire when state remains the same", () => {
      const client = createClient({ getToken: () => null });
      const stateHandler = vi.fn();
      client.onStateChange(stateHandler);

      // State is already "disconnected", getToken returns null so setState("disconnected") is called
      // but since state hasn't changed, handler should not fire
      client.connect();

      expect(stateHandler).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // 13. Reconnect: exponential backoff, token refreshed on each attempt
  // -------------------------------------------------------------------------
  describe("reconnect with exponential backoff", () => {
    it("uses exponential backoff: 1s, 2s, 4s, 8s", () => {
      const client = createClient();
      client.connect();
      lastWs().simulateOpen();

      // First close: reconnect after 1s
      lastWs().simulateClose();
      expect(MockWebSocket.instances).toHaveLength(1);

      vi.advanceTimersByTime(999);
      expect(MockWebSocket.instances).toHaveLength(1);

      vi.advanceTimersByTime(1);
      expect(MockWebSocket.instances).toHaveLength(2);

      // Second close: reconnect after 2s
      lastWs().simulateClose();
      vi.advanceTimersByTime(1999);
      expect(MockWebSocket.instances).toHaveLength(2);

      vi.advanceTimersByTime(1);
      expect(MockWebSocket.instances).toHaveLength(3);

      // Third close: reconnect after 4s
      lastWs().simulateClose();
      vi.advanceTimersByTime(3999);
      expect(MockWebSocket.instances).toHaveLength(3);

      vi.advanceTimersByTime(1);
      expect(MockWebSocket.instances).toHaveLength(4);

      // Fourth close: reconnect after 8s
      lastWs().simulateClose();
      vi.advanceTimersByTime(7999);
      expect(MockWebSocket.instances).toHaveLength(4);

      vi.advanceTimersByTime(1);
      expect(MockWebSocket.instances).toHaveLength(5);
    });

    it("refreshes the token on each reconnect attempt", () => {
      let tokenCounter = 0;
      const client = createClient({
        getToken: () => `jwt-${++tokenCounter}`,
      });

      client.connect();
      expect(lastWs().url).toContain("token=jwt-1");
      lastWs().simulateOpen();

      // Close and reconnect
      lastWs().simulateClose();
      vi.advanceTimersByTime(1000);
      expect(lastWs().url).toContain("token=jwt-2");
      lastWs().simulateOpen();

      // Close and reconnect again
      lastWs().simulateClose();
      vi.advanceTimersByTime(1000);
      expect(lastWs().url).toContain("token=jwt-3");
    });

    it("resets backoff after a successful connection", () => {
      const client = createClient();
      client.connect();
      lastWs().simulateOpen();

      // First close + reconnect at 1s
      lastWs().simulateClose();
      vi.advanceTimersByTime(1000);
      expect(MockWebSocket.instances).toHaveLength(2);

      // Second close (without opening) — attempt increments to 1, delay = 2s
      lastWs().simulateClose();
      vi.advanceTimersByTime(2000);
      expect(MockWebSocket.instances).toHaveLength(3);

      // Open successfully — resets attempt counter
      lastWs().simulateOpen();

      // Close again — should be back to 1s
      lastWs().simulateClose();
      vi.advanceTimersByTime(999);
      expect(MockWebSocket.instances).toHaveLength(3);

      vi.advanceTimersByTime(1);
      expect(MockWebSocket.instances).toHaveLength(4);
    });
  });

  // -------------------------------------------------------------------------
  // 14. Reconnect capped at maxReconnectDelay
  // -------------------------------------------------------------------------
  describe("maxReconnectDelay", () => {
    it("caps reconnect delay at default 30s", () => {
      const client = createClient();
      client.connect();

      // Simulate many failed reconnects to exceed default cap
      // After 5 closes: delays are 1s, 2s, 4s, 8s, 16s, 30s (capped at 30s)
      for (let i = 0; i < 5; i++) {
        lastWs().simulateClose();
        vi.advanceTimersByTime(Math.min(1000 * Math.pow(2, i), 30_000));
      }

      // The 6th close: delay should be capped at 30s (2^5 * 1000 = 32000 > 30000)
      lastWs().simulateClose();
      const instancesBefore = MockWebSocket.instances.length;

      vi.advanceTimersByTime(29_999);
      expect(MockWebSocket.instances).toHaveLength(instancesBefore);

      vi.advanceTimersByTime(1);
      expect(MockWebSocket.instances).toHaveLength(instancesBefore + 1);
    });

    it("uses custom maxReconnectDelay when specified", () => {
      const client = createClient({ maxReconnectDelay: 5000 });
      client.connect();

      // After 3 closes: 1s, 2s, 4s — next would be 8s but capped at 5s
      for (let i = 0; i < 3; i++) {
        lastWs().simulateClose();
        vi.advanceTimersByTime(Math.min(1000 * Math.pow(2, i), 5000));
      }

      // 4th close: 2^3 * 1000 = 8000 > 5000 => capped at 5000
      lastWs().simulateClose();
      const instancesBefore = MockWebSocket.instances.length;

      vi.advanceTimersByTime(4999);
      expect(MockWebSocket.instances).toHaveLength(instancesBefore);

      vi.advanceTimersByTime(1);
      expect(MockWebSocket.instances).toHaveLength(instancesBefore + 1);
    });
  });

  // -------------------------------------------------------------------------
  // 15. reconnect: false disables auto-reconnect
  // -------------------------------------------------------------------------
  describe("reconnect: false", () => {
    it("does not attempt reconnect after unintentional close", () => {
      const client = createClient({ reconnect: false });
      client.connect();
      lastWs().simulateOpen();
      lastWs().simulateClose();

      // State goes to "reconnecting" (onclose else-branch) but no timer is scheduled
      vi.advanceTimersByTime(60_000);

      // Only the original WebSocket — no reconnect attempt was made
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    it("does not schedule a reconnect timer on close", () => {
      const client = createClient({ reconnect: false });
      const stateHandler = vi.fn();
      client.onStateChange(stateHandler);

      client.connect();
      lastWs().simulateOpen();
      lastWs().simulateClose();

      // No new WebSocket even after waiting a long time
      vi.advanceTimersByTime(60_000);
      expect(MockWebSocket.instances).toHaveLength(1);

      // State transitions: connecting -> connected -> reconnecting
      const states = stateHandler.mock.calls.map((call) => call[0]) as WsState[];
      expect(states).toEqual(["connecting", "connected", "reconnecting"]);
    });
  });

  // -------------------------------------------------------------------------
  // 16. Malformed messages are ignored (no throw)
  // -------------------------------------------------------------------------
  describe("malformed messages", () => {
    it("ignores messages with invalid JSON without throwing", () => {
      const client = createClient();
      const handler = vi.fn();
      client.on("chat.message", handler);

      client.connect();
      lastWs().simulateOpen();

      // Directly call onmessage with malformed data
      expect(() => {
        lastWs().onmessage?.({ data: "not-valid-json{{{" });
      }).not.toThrow();

      expect(handler).not.toHaveBeenCalled();
    });

    it("ignores messages without a type field", () => {
      const client = createClient();
      const handler = vi.fn();
      client.on("undefined", handler);

      client.connect();
      lastWs().simulateOpen();
      lastWs().simulateMessage({ payload: "no type here" });

      expect(handler).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // 17. on() handler errors don't break other handlers
  // -------------------------------------------------------------------------
  describe("handler error isolation", () => {
    it("event handler errors do not prevent other handlers from firing", () => {
      const client = createClient();
      const errorHandler = vi.fn(() => {
        throw new Error("handler boom");
      });
      const safeHandler = vi.fn();

      client.on("chat.message", errorHandler);
      client.on("chat.message", safeHandler);

      client.connect();
      lastWs().simulateOpen();

      expect(() => {
        lastWs().simulateMessage({ type: "chat.message", text: "test" });
      }).not.toThrow();

      expect(errorHandler).toHaveBeenCalledOnce();
      expect(safeHandler).toHaveBeenCalledOnce();
    });

    it("state change handler errors do not prevent other state handlers from firing", () => {
      const client = createClient();
      const errorHandler = vi.fn(() => {
        throw new Error("state handler boom");
      });
      const safeHandler = vi.fn();

      client.onStateChange(errorHandler);
      client.onStateChange(safeHandler);

      expect(() => {
        client.connect();
      }).not.toThrow();

      expect(errorHandler).toHaveBeenCalledWith("connecting");
      expect(safeHandler).toHaveBeenCalledWith("connecting");
    });
  });

  // -------------------------------------------------------------------------
  // 18. URL with existing query params uses &token= instead of ?token=
  // -------------------------------------------------------------------------
  describe("URL query parameter handling", () => {
    it("appends &token= when URL already has query params", () => {
      const client = createClient({
        url: "ws://localhost:8000/ws/chat/?room=general",
      });
      client.connect();

      expect(lastWs().url).toBe(
        "ws://localhost:8000/ws/chat/?room=general&token=test-jwt-token",
      );
    });

    it("appends ?token= when URL has no query params", () => {
      const client = createClient({
        url: "ws://localhost:8000/ws/chat/",
      });
      client.connect();

      expect(lastWs().url).toBe("ws://localhost:8000/ws/chat/?token=test-jwt-token");
    });
  });

  // -------------------------------------------------------------------------
  // Edge cases
  // -------------------------------------------------------------------------
  describe("edge cases", () => {
    it("disconnect cancels a pending reconnect timer", () => {
      const client = createClient();
      client.connect();
      lastWs().simulateOpen();
      lastWs().simulateClose();

      expect(client.state).toBe("reconnecting");

      client.disconnect();
      expect(client.state).toBe("disconnected");

      vi.advanceTimersByTime(60_000);

      // Only the original instance — no reconnect happened
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    it("connect after disconnect works correctly", () => {
      const client = createClient();
      client.connect();
      lastWs().simulateOpen();
      client.disconnect();

      expect(client.state).toBe("disconnected");

      client.connect();
      expect(MockWebSocket.instances).toHaveLength(2);
      lastWs().simulateOpen();
      expect(client.state).toBe("connected");
    });

    it("disconnect when already disconnected is a no-op", () => {
      const client = createClient();
      const stateHandler = vi.fn();
      client.onStateChange(stateHandler);

      client.disconnect();

      // State was already disconnected — no change, no handler call
      expect(stateHandler).not.toHaveBeenCalled();
    });

    it("handles WebSocket error followed by close (standard browser behavior)", () => {
      const client = createClient();
      client.connect();
      lastWs().simulateOpen();

      // Error fires first, then close
      lastWs().simulateError();
      lastWs().simulateClose();

      expect(client.state).toBe("reconnecting");

      // Should still reconnect
      vi.advanceTimersByTime(1000);
      expect(MockWebSocket.instances).toHaveLength(2);
    });

    it("reconnect attempt that gets null token stops and stays disconnected", () => {
      let tokenAvailable = true;
      const client = createClient({
        getToken: () => (tokenAvailable ? "valid-token" : null),
      });

      client.connect();
      lastWs().simulateOpen();

      // Token becomes unavailable
      tokenAvailable = false;
      lastWs().simulateClose();

      expect(client.state).toBe("reconnecting");

      // Reconnect fires — but getToken returns null
      vi.advanceTimersByTime(1000);

      // No new WebSocket created (token was null)
      expect(MockWebSocket.instances).toHaveLength(1);
      expect(client.state).toBe("disconnected");
    });
  });
});
