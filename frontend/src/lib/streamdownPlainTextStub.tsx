import { createContext, memo, type ComponentType, type ReactNode } from "react";

type ControlsConfig =
  | boolean
  | {
      table?: boolean;
      code?: boolean;
      mermaid?:
        | boolean
        | {
            download?: boolean;
            copy?: boolean;
            fullscreen?: boolean;
            panZoom?: boolean;
          };
    };

type StreamdownContextType = {
  shikiTheme: [string, string];
  controls: ControlsConfig;
  isAnimating: boolean;
  mode: "static" | "streaming";
  mermaid?: unknown;
};

type StreamdownProps = {
  children?: ReactNode;
  className?: string;
};

type BlockProps = StreamdownProps & {
  content: string;
  shouldParseIncompleteMarkdown: boolean;
  index: number;
};

export const StreamdownContext = createContext<StreamdownContextType>({
  shikiTheme: ["github-light", "github-dark"],
  controls: false,
  isAnimating: false,
  mode: "static"
});

export const defaultRehypePlugins = {};
export const defaultRemarkPlugins = {};

export function parseMarkdownIntoBlocks(markdown: string): string[] {
  return markdown ? [markdown] : [];
}

export const Block = memo(function Block({ content, className }: BlockProps) {
  return <div className={className}>{content}</div>;
});

export const Streamdown = memo(function Streamdown({ children, className }: StreamdownProps) {
  return <div className={className}>{typeof children === "string" ? children : children}</div>;
}) as ComponentType<StreamdownProps>;
