export type ProgressStep = {
  id: string;
  title: string;
  detail: string;
  status: "pending" | "running" | "completed" | "failed";
};

export type ProgressSnapshot = {
  progressId?: string;
  sequence?: number;
  isFinal?: boolean;
  steps: ProgressStep[];
};
