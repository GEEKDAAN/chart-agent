import {
  INTENT_CHANGE_CHART_TYPE,
  INTENT_CREATE_CHART,
  INTENT_UPDATE_DATA,
  INTENT_UPDATE_STYLE
} from "./protocol.js";

export type ProgressStep = {
  id: string;
  title: string;
  detail: string;
  status: "pending" | "running" | "completed" | "failed";
};

export type ProgressSnapshot = {
  progressId: string;
  sequence: number;
  isFinal?: boolean;
  steps: ProgressStep[];
};

const templates: Record<string, Array<[string, string, string, string]>> = {
  [INTENT_CREATE_CHART]: [
    ["parse_create_request", "识别图表需求", "正在识别指标、维度和时间范围", "已识别图表生成需求"],
    ["plan_data", "规划数据查询", "等待生成数据需求", "已完成指标、维度和筛选条件规划"],
    ["query_data", "查询业务数据", "等待查询数据", "已获得图表所需数据"],
    ["generate_chart", "生成图表配置", "等待生成受控 ChartSpec", "已生成图表配置"],
    ["sync_frontend", "同步到前端", "等待应用图表", "图表已同步到前端"]
  ],
  [INTENT_UPDATE_STYLE]: [
    ["parse_style_request", "识别样式修改", "正在识别颜色、系列或展示样式目标", "已识别样式修改目标"],
    ["read_current_chart", "读取当前图表", "等待读取当前 ChartSpec", "已读取当前图表上下文"],
    ["generate_style_patch", "生成样式变更", "等待生成受控样式 patch", "已生成样式变更"],
    ["sync_frontend", "同步到前端", "等待应用样式", "样式修改已同步到前端"]
  ],
  [INTENT_UPDATE_DATA]: [
    ["parse_data_request", "识别数据修改", "正在识别新增指标或数据调整目标", "已识别数据修改需求"],
    ["plan_data_update", "规划数据补充", "等待规划补充数据", "已完成补充数据规划"],
    ["query_updated_data", "查询更新数据", "等待查询更新后的数据", "已获得更新后的图表数据"],
    ["generate_data_patch", "生成数据变更", "等待生成受控数据 patch", "已生成数据变更"],
    ["sync_frontend", "同步到前端", "等待应用数据变更", "数据修改已同步到前端"]
  ],
  [INTENT_CHANGE_CHART_TYPE]: [
    ["parse_type_request", "识别图表类型", "正在识别目标图表类型", "已识别目标图表类型"],
    ["read_current_chart", "读取当前图表", "等待读取当前 ChartSpec", "已读取当前图表上下文"],
    ["validate_chart_type", "校验数据适配", "等待校验当前数据是否适合目标类型", "已完成图表类型适配校验"],
    ["generate_type_patch", "生成类型变更", "等待生成受控类型 patch", "已生成图表类型变更"],
    ["sync_frontend", "同步到前端", "等待应用类型变更", "图表类型已同步到前端"]
  ]
};

export function shouldRenderProgress(intent: string): boolean {
  return Object.prototype.hasOwnProperty.call(templates, intent);
}

export function progressSnapshots(intent: string, progressId: string, finalState: "completed" | "failed"): ProgressSnapshot[] {
  const template = templates[intent];
  if (!template) return [];

  const snapshots: ProgressSnapshot[] = [];
  for (let activeIndex = 0; activeIndex < template.length; activeIndex += 1) {
    snapshots.push({
      progressId,
      sequence: activeIndex,
      isFinal: false,
      steps: template.map(([id, title, runningDetail, completedDetail], index) => {
        if (index < activeIndex) {
          return { id, title, detail: completedDetail, status: "completed" };
        }
        if (index === activeIndex) {
          return { id, title, detail: runningDetail, status: "running" };
        }
        return { id, title, detail: runningDetail, status: "pending" };
      })
    });
  }

  snapshots.push(progressSnapshot(intent, progressId, template.length, finalState));
  return snapshots;
}

export function progressSnapshot(intent: string, progressId: string, sequence: number, state: "running" | "completed" | "failed"): ProgressSnapshot {
  const template = templates[intent] ?? templates[INTENT_CREATE_CHART];
  return {
    progressId,
    sequence,
    isFinal: state !== "running",
    steps: template.map(([id, title, runningDetail, completedDetail], index) => {
      if (state === "completed") {
        return { id, title, detail: completedDetail, status: "completed" };
      }
      if (state === "failed" && index === 0) {
        return { id, title, detail: "处理失败", status: "failed" };
      }
      if (index === 0) {
        return { id, title, detail: runningDetail, status: "running" };
      }
      return { id, title, detail: runningDetail, status: "pending" };
    })
  };
}
