import {
  UI_BLOCK_INSIGHT_CARD,
  UI_BLOCK_METRIC_SUMMARY,
  UI_BLOCK_SUGGESTED_ACTIONS
} from "../../../domain/chartAgentProtocol";
import { submitCopilotChatMessage } from "../../../lib/copilotChatSubmit";
import type { ChartAgentUiBlock } from "../../../types/chart";
import { formatCellValue } from "../utils";

export function ChatUiBlocks({ blocks, uiBlockId }: { blocks: ChartAgentUiBlock[]; uiBlockId: string | undefined }) {
  if (blocks.length === 0) return null;

  return (
    <section className="chat-ui-blocks" aria-label="生成式 UI" data-ui-block-id={uiBlockId}>
      {blocks.map((block, index) => (
        <ChatUiBlock block={block} key={`${block.type}-${index}`} />
      ))}
    </section>
  );
}

function ChatUiBlock({ block }: { block: ChartAgentUiBlock }) {
  if (block.type === UI_BLOCK_METRIC_SUMMARY) {
    return (
      <article className="chat-ui-card">
        <h3>{block.title ?? "指标摘要"}</h3>
        <dl className="chat-ui-summary-grid">
          {block.items.map((item) => (
            <div className="chat-ui-summary-item" key={`${item.label}-${item.value}`}>
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
              {item.description ? <p>{item.description}</p> : null}
            </div>
          ))}
        </dl>
      </article>
    );
  }

  if (block.type === UI_BLOCK_INSIGHT_CARD) {
    return (
      <article className="chat-ui-card">
        <h3>{block.title ?? "图表洞察"}</h3>
        <p className="chat-ui-insight">{block.content}</p>
      </article>
    );
  }

  if (block.type === UI_BLOCK_SUGGESTED_ACTIONS) {
    return (
      <article className="chat-ui-card">
        <h3>{block.title ?? "建议操作"}</h3>
        <div className="chat-ui-action-list">
          {block.actions.map((action) => (
            <button
              className="chat-ui-action-chip"
              key={`${action.label}-${action.message}`}
              onClick={() => submitCopilotChatMessage(action.message)}
              title={action.message}
              type="button"
            >
              {action.label}
            </button>
          ))}
        </div>
      </article>
    );
  }

  return (
    <article className="chat-ui-card">
      <h3>{block.title ?? "数据明细"}</h3>
      <div className="chat-ui-table-wrap">
        <table className="chat-ui-table">
          <thead>
            <tr>
              {block.data.columns.map((column) => (
                <th key={column.key}>{column.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {block.data.rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {block.data.columns.map((column) => (
                  <td key={column.key}>{formatCellValue(row[column.key])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
