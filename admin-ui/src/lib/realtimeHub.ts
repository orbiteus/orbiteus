"use client";
/**
 * Cross-tab SSE hub — one EventSource per browser profile (leader tab).
 *
 * Without this, each open admin tab opens its own `/api/realtime/subscribe`
 * connection. A user with 150 tabs would hold 150 idle SSE streams.
 *
 * Strategy (docs/11-realtime.md):
 * - Leader election via localStorage heartbeat (single leader per origin).
 * - BroadcastChannel fan-out so follower tabs receive events without SSE.
 * - Leader multiplexes the union of all tab topics on one EventSource URL.
 */
import type { RealtimeMessage } from "./realtimeTypes";
import {
  buildSubscribeUrl,
  shouldClaimLeadership,
  topicsFromRealtimeMessage,
  unionTopicSets,
  type LeaderRecord,
} from "./realtimeTopics";

const CHANNEL_NAME = "orbiteus.realtime.v1";
const LEADER_KEY = "orbiteus.realtime.leader.v1";
const HEARTBEAT_MS = 2_000;
const LEADER_STALE_MS = 7_000;
const RECONNECT_DELAY_MS = 3_000;
const MAX_RECONNECT_DELAY_MS = 30_000;

type HubMessage =
  | { type: "topics"; tabId: string; topics: string[] }
  | { type: "request-topics" }
  | { type: "sse"; payload: RealtimeMessage };

type Listener = (msg: RealtimeMessage) => void;

function tabId(): string {
  const key = "orbiteus.tabId";
  let id = sessionStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(key, id);
  }
  return id;
}

function readLeader(): LeaderRecord | null {
  try {
    const raw = localStorage.getItem(LEADER_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as LeaderRecord;
    if (!parsed?.tabId || typeof parsed.ts !== "number") return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeLeader(id: string, ts: number): void {
  try {
    localStorage.setItem(LEADER_KEY, JSON.stringify({ tabId: id, ts }));
  } catch {
    /* private mode / quota */
  }
}

function clearLeaderIfOwned(id: string): void {
  const current = readLeader();
  if (current?.tabId === id) {
    try {
      localStorage.removeItem(LEADER_KEY);
    } catch {
      /* ignore */
    }
  }
}

class RealtimeHub {
  private readonly id = tabId();
  private readonly bc: BroadcastChannel | null;
  private readonly fallback: boolean;

  private isLeader = false;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private leadershipTimer: ReturnType<typeof setInterval> | null = null;

  private tabTopics = new Map<string, Set<string>>();
  private localTopics = new Set<string>();
  private topicListeners = new Map<string, Set<Listener>>();

  private es: EventSource | null = null;
  private esUrl = "";
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;

  constructor() {
    this.bc =
      typeof BroadcastChannel !== "undefined"
        ? new BroadcastChannel(CHANNEL_NAME)
        : null;
    this.fallback = !this.bc;

    this.tabTopics.set(this.id, new Set());

    if (this.bc) {
      this.bc.onmessage = (ev: MessageEvent<HubMessage>) => {
        const data = ev.data;
        if (!data || typeof data !== "object") return;
        if (data.type === "topics") {
          this.tabTopics.set(data.tabId, new Set(data.topics));
          if (this.isLeader) this.reconcileConnection();
          return;
        }
        if (data.type === "request-topics") {
          this.announceTopics();
          return;
        }
        if (data.type === "sse") {
          this.dispatchLocal(data.payload);
        }
      };
    }

    window.addEventListener("storage", this.onStorage);
    window.addEventListener("beforeunload", this.onUnload);
    window.addEventListener("pagehide", this.onUnload);

    this.leadershipTimer = setInterval(() => this.refreshLeadership(), HEARTBEAT_MS);
    this.refreshLeadership();
    this.announceTopics();
  }

  subscribe(topic: string, listener: Listener): () => void {
    let set = this.topicListeners.get(topic);
    if (!set) {
      set = new Set();
      this.topicListeners.set(topic, set);
      this.localTopics.add(topic);
      this.announceTopics();
    }
    set.add(listener);

    return () => {
      const bucket = this.topicListeners.get(topic);
      if (!bucket) return;
      bucket.delete(listener);
      if (bucket.size === 0) {
        this.topicListeners.delete(topic);
        this.localTopics.delete(topic);
        this.announceTopics();
      }
    };
  }

  private onStorage = (ev: StorageEvent) => {
    if (ev.key === LEADER_KEY) this.refreshLeadership();
  };

  private onUnload = () => {
    this.tabTopics.set(this.id, new Set());
    this.bc?.postMessage({ type: "topics", tabId: this.id, topics: [] });
    clearLeaderIfOwned(this.id);
    this.stopLeader();
  };

  private announceTopics(): void {
    const topics = [...this.localTopics].sort();
    this.tabTopics.set(this.id, new Set(topics));
    this.bc?.postMessage({ type: "topics", tabId: this.id, topics });
    if (this.isLeader) this.reconcileConnection();
  }

  private refreshLeadership(): void {
    if (this.fallback) {
      if (!this.isLeader) this.startLeader();
      return;
    }

    const now = Date.now();
    const current = readLeader();
    const wantLead = shouldClaimLeadership(current, this.id, now, LEADER_STALE_MS);

    if (wantLead) {
      writeLeader(this.id, now);
      const verify = readLeader();
      const won = verify?.tabId === this.id;
      if (won && !this.isLeader) this.startLeader();
      else if (!won && this.isLeader) this.stopLeader();
      else if (won && this.isLeader) writeLeader(this.id, now);
    } else if (this.isLeader) {
      this.stopLeader();
    }
  }

  private startLeader(): void {
    this.isLeader = true;
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    this.heartbeatTimer = setInterval(() => {
      if (!this.isLeader) return;
      writeLeader(this.id, Date.now());
    }, HEARTBEAT_MS);
    this.bc?.postMessage({ type: "request-topics" });
    this.reconcileConnection();
  }

  private stopLeader(): void {
    this.isLeader = false;
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    this.closeConnection();
  }

  private allTopics(): string[] {
    return unionTopicSets(this.tabTopics.values());
  }

  private reconcileConnection(): void {
    if (!this.isLeader) return;
    const topics = this.allTopics();
    const url = buildSubscribeUrl(topics);
    if (!url) {
      this.closeConnection();
      return;
    }
    if (url === this.esUrl && this.es) return;
    this.closeConnection();
    this.esUrl = url;
    this.connect(url);
  }

  private connect(url: string): void {
    this.es = new EventSource(url);

    this.es.addEventListener("open", () => {
      this.reconnectAttempts = 0;
    });

    this.es.addEventListener("message", (ev) => {
      try {
        const payload = JSON.parse((ev as MessageEvent).data) as RealtimeMessage;
        this.bc?.postMessage({ type: "sse", payload });
        this.dispatchLocal(payload);
      } catch {
        /* malformed */
      }
    });

    this.es.addEventListener("error", () => {
      this.es?.close();
      this.es = null;
      this.esUrl = "";
      if (!this.isLeader) return;
      this.reconnectAttempts += 1;
      const delay = Math.min(
        RECONNECT_DELAY_MS * Math.pow(1.5, this.reconnectAttempts - 1),
        MAX_RECONNECT_DELAY_MS,
      );
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
      this.reconnectTimer = setTimeout(() => {
        if (this.isLeader) this.reconcileConnection();
      }, delay);
    });
  }

  private closeConnection(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.es?.close();
    this.es = null;
    this.esUrl = "";
  }

  private dispatchLocal(msg: RealtimeMessage): void {
    const seen = new Set<Listener>();
    for (const topic of topicsFromRealtimeMessage(msg)) {
      const listeners = this.topicListeners.get(topic);
      if (!listeners) continue;
      for (const fn of listeners) {
        if (seen.has(fn)) continue;
        seen.add(fn);
        fn(msg);
      }
    }
  }
}

let hub: RealtimeHub | null = null;

export function getRealtimeHub(): RealtimeHub {
  if (typeof window === "undefined") {
    throw new Error("RealtimeHub is client-only");
  }
  if (!hub) hub = new RealtimeHub();
  return hub;
}

export function subscribeRealtimeTopic(
  topic: string,
  listener: Listener,
): () => void {
  return getRealtimeHub().subscribe(topic, listener);
}
