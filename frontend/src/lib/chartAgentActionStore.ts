import { useSyncExternalStore } from "react";

import type { ChartAgentAction } from "../types/chart";

export type ChartAgentActionSnapshot = {
  actionId: string;
  action: ChartAgentAction;
};

let latestSnapshot: ChartAgentActionSnapshot | null = null;
const seenActionIds = new Set<string>();
const listeners = new Set<() => void>();

export function publishChartAgentAction(snapshot: ChartAgentActionSnapshot) {
  if (seenActionIds.has(snapshot.actionId)) return;

  seenActionIds.add(snapshot.actionId);
  latestSnapshot = snapshot;
  for (const listener of listeners) {
    listener();
  }
}

export function useLatestChartAgentAction(): ChartAgentActionSnapshot | null {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => latestSnapshot,
    () => null,
  );
}
