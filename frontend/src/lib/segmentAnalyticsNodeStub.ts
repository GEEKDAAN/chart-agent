type Callback = (error?: Error | null) => void;

function resolveCallback(callback?: Callback): Promise<void> {
  callback?.(null);
  return Promise.resolve();
}

export class Analytics {
  constructor(_options?: unknown) {}

  track(_event?: unknown, callback?: Callback): Promise<void> {
    return resolveCallback(callback);
  }

  identify(_event?: unknown, callback?: Callback): Promise<void> {
    return resolveCallback(callback);
  }

  page(_event?: unknown, callback?: Callback): Promise<void> {
    return resolveCallback(callback);
  }

  group(_event?: unknown, callback?: Callback): Promise<void> {
    return resolveCallback(callback);
  }

  alias(_event?: unknown, callback?: Callback): Promise<void> {
    return resolveCallback(callback);
  }

  screen(_event?: unknown, callback?: Callback): Promise<void> {
    return resolveCallback(callback);
  }

  flush(callback?: Callback): Promise<void> {
    return resolveCallback(callback);
  }

  closeAndFlush(callback?: Callback): Promise<void> {
    return resolveCallback(callback);
  }
}
