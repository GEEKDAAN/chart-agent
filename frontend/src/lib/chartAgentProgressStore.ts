import { useSyncExternalStore } from "react";

import type { ProgressSnapshot } from "../types/progress";

const MIN_STEP_VISIBLE_MS = 450;

const snapshots = new Map<string, ProgressSnapshot>();
const queues = new Map<string, ProgressSnapshot[]>();
const timers = new Map<string, number>();
const seenSequences = new Map<string, Set<number>>();
const listeners = new Set<() => void>();

export function publishChartAgentProgress(snapshot: ProgressSnapshot) {
  if (!snapshot.progressId) return;
  if (isDuplicate(snapshot)) return;

  const progressId = snapshot.progressId;
  if (!snapshots.has(progressId)) {
    snapshots.set(progressId, snapshot);
    notifyListeners();
    return;
  }

  const queue = queues.get(progressId) ?? [];
  queue.push(snapshot);
  queues.set(progressId, queue);
  scheduleNext(progressId);
}

function isDuplicate(snapshot: ProgressSnapshot): boolean {
  if (!snapshot.progressId || typeof snapshot.sequence !== "number") return false;
  const seen = seenSequences.get(snapshot.progressId) ?? new Set<number>();
  if (seen.has(snapshot.sequence)) return true;
  seen.add(snapshot.sequence);
  seenSequences.set(snapshot.progressId, seen);
  return false;
}

function scheduleNext(progressId: string) {
  if (timers.has(progressId)) return;

  const timer = window.setTimeout(() => {
    timers.delete(progressId);
    const queue = queues.get(progressId) ?? [];
    const next = queue.shift();
    if (!next) return;

    snapshots.set(progressId, next);
    if (queue.length === 0) {
      queues.delete(progressId);
    } else {
      queues.set(progressId, queue);
      scheduleNext(progressId);
    }
    notifyListeners();
  }, MIN_STEP_VISIBLE_MS);

  timers.set(progressId, timer);
}

function notifyListeners() {
  for (const listener of listeners) {
    listener();
  }
}

export function useChartAgentProgress(progressId: string | undefined): ProgressSnapshot | null {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => (progressId ? snapshots.get(progressId) ?? null : null),
    () => null,
  );
}
