/**
 * WebSocket Client
 * ================
 * Reusable, framework-agnostic WebSocket connection manager.
 *
 * Located in src/lib/ (not chat-specific) because notifications may reuse it.
 * Uses native WebSocket API only — no external dependencies.
 *
 * Features:
 * - Automatic reconnect with exponential backoff (1s → 30s max)
 * - JWT token in query string, refreshed on each reconnect
 * - Event emitter pattern (subscribe/unsubscribe by event type)
 * - Message queue during reconnection (buffer outgoing, replay on connect)
 * - Connection state observable
 */

export type WsState = "connecting" | "connected" | "disconnected" | "reconnecting";

export interface WsClientOptions {
  /** WebSocket URL (without token — token is appended automatically) */
  url: string;
  /** Function to get current JWT. Called on each (re)connect. */
  getToken: () => string | null;
  /** Enable automatic reconnect. Default: true */
  reconnect?: boolean;
  /** Max reconnect delay in ms. Default: 30000 */
  maxReconnectDelay?: number;
}

type EventHandler = (payload: unknown) => void;
type StateHandler = (state: WsState) => void;

export class WsClient {
  private ws: WebSocket | null = null;
  private _state: WsState = "disconnected";
  private eventHandlers = new Map<string, Set<EventHandler>>();
  private stateHandlers = new Set<StateHandler>();
  private messageQueue: string[] = [];
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;

  private readonly url: string;
  private readonly getToken: () => string | null;
  private readonly shouldReconnect: boolean;
  private readonly maxReconnectDelay: number;

  constructor(options: WsClientOptions) {
    this.url = options.url;
    this.getToken = options.getToken;
    this.shouldReconnect = options.reconnect ?? true;
    this.maxReconnectDelay = options.maxReconnectDelay ?? 30_000;
  }

  get state(): WsState {
    return this._state;
  }

  connect(): void {
    if (this.ws && (this._state === "connecting" || this._state === "connected")) {
      return;
    }

    this.intentionalClose = false;
    const token = this.getToken();
    if (!token) {
      this.setState("disconnected");
      return;
    }

    const separator = this.url.includes("?") ? "&" : "?";
    const wsUrl = `${this.url}${separator}token=${token}`;

    this.setState("connecting");

    try {
      this.ws = new WebSocket(wsUrl);
    } catch {
      this.setState("disconnected");
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempt = 0;
      this.setState("connected");
      this.flushQueue();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        const type = data?.type as string | undefined;
        if (type) {
          this.emit(type, data);
        }
      } catch {
        // Ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      this.ws = null;
      if (this.intentionalClose) {
        this.setState("disconnected");
      } else {
        this.setState("reconnecting");
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      // onclose will fire after onerror, so reconnect is handled there
    };
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.cancelReconnect();
    this.messageQueue = [];
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setState("disconnected");
  }

  send(data: Record<string, unknown>): void {
    const message = JSON.stringify(data);
    if (this.ws && this._state === "connected") {
      this.ws.send(message);
    } else {
      this.messageQueue.push(message);
    }
  }

  /**
   * Subscribe to events by type. Returns an unsubscribe function.
   */
  on<T = unknown>(event: string, handler: (payload: T) => void): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    const handlers = this.eventHandlers.get(event)!;
    const wrappedHandler = handler as EventHandler;
    handlers.add(wrappedHandler);

    return () => {
      handlers.delete(wrappedHandler);
      if (handlers.size === 0) {
        this.eventHandlers.delete(event);
      }
    };
  }

  /**
   * Subscribe to connection state changes. Returns an unsubscribe function.
   */
  onStateChange(handler: StateHandler): () => void {
    this.stateHandlers.add(handler);
    return () => {
      this.stateHandlers.delete(handler);
    };
  }

  // -------------------------------------------------------------------------
  // Private
  // -------------------------------------------------------------------------

  private setState(state: WsState): void {
    if (this._state === state) return;
    this._state = state;
    for (const handler of this.stateHandlers) {
      try {
        handler(state);
      } catch {
        // Don't let handler errors break state management
      }
    }
  }

  private emit(event: string, payload: unknown): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(payload);
        } catch {
          // Don't let handler errors break event processing
        }
      }
    }
  }

  private flushQueue(): void {
    if (!this.ws || this._state !== "connected") return;
    const queued = [...this.messageQueue];
    this.messageQueue = [];
    for (const message of queued) {
      this.ws.send(message);
    }
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect || this.intentionalClose) return;
    this.cancelReconnect();

    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (capped)
    const delay = Math.min(
      1000 * Math.pow(2, this.reconnectAttempt),
      this.maxReconnectDelay,
    );
    this.reconnectAttempt++;

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private cancelReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
