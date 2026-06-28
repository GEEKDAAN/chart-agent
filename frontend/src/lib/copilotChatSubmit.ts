const COPILOT_CHAT_TEXTAREA_SELECTOR = "textarea";
const COPILOT_CHAT_BUTTON_SELECTOR = "button";
const DEFER_SEND_MS = 0;

export function submitCopilotChatMessage(message: string): boolean {
  const textarea = document.querySelector<HTMLTextAreaElement>(COPILOT_CHAT_TEXTAREA_SELECTOR);
  if (!textarea) return false;

  setTextAreaValue(textarea, message);
  textarea.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: message }));

  window.setTimeout(() => {
    findLastEnabledButton()?.click();
  }, DEFER_SEND_MS);
  return true;
}

function setTextAreaValue(textarea: HTMLTextAreaElement, value: string): void {
  const valueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set;
  if (valueSetter) {
    valueSetter.call(textarea, value);
    return;
  }
  textarea.value = value;
}

function findLastEnabledButton(): HTMLButtonElement | undefined {
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>(COPILOT_CHAT_BUTTON_SELECTOR)).filter(
    (button) => !button.disabled
  );
  return buttons[buttons.length - 1];
}
