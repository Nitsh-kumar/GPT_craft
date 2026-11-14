export interface StreamStart {
  type: 'start'; conversation_id: number; model_used: string; mode_used: string;
}
export interface StreamDone {
  type: 'done'; conversation_id: number; model_used: string; mode_used: string;
  tokens_used: number; tokens_remaining: number; usage_estimated: boolean;
}
export type ChatEvent = StreamStart | StreamDone | { type: 'chunk'; content: string };

function parseEvent(data: string): ChatEvent {
  const value: unknown = JSON.parse(data);
  if (!value || typeof value !== 'object' || !('type' in value)) throw new Error('Invalid chat stream event.');
  const event = value as Record<string, unknown>;
  if (event.type === 'error') throw new Error(typeof event.error === 'string' ? event.error : 'AI generation failed.');
  if (event.type === 'chunk' && typeof event.content === 'string') return event as { type: 'chunk'; content: string };
  if ((event.type === 'start' || event.type === 'done') && typeof event.conversation_id === 'number'
      && typeof event.model_used === 'string' && typeof event.mode_used === 'string') {
    if (event.type === 'done' && (typeof event.tokens_used !== 'number' || typeof event.tokens_remaining !== 'number')) {
      throw new Error('Invalid completion event.');
    }
    return event as unknown as StreamStart | StreamDone;
  }
  throw new Error('Unsupported chat stream event.');
}

/** Reads fragmented UTF-8/CRLF SSE frames and requires an explicit completion. */
export async function readChatStream(body: ReadableStream<Uint8Array>, onEvent: (event: ChatEvent) => void): Promise<StreamDone> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let completed: StreamDone | undefined;
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      // Normalize only complete CRLF pairs (a pair can straddle reader chunks).
      buffer = buffer.replace(/\r\n/g, '\n');
      if (buffer.length > 1_000_000) throw new Error('Chat stream frame is too large.');
      let end: number;
      while ((end = buffer.indexOf('\n\n')) >= 0) {
        const frame = buffer.slice(0, end);
        buffer = buffer.slice(end + 2);
        const data = frame.split('\n').filter(line => line.startsWith('data:'))
          .map(line => line.slice(5).trimStart()).join('\n');
        if (!data) continue;
        if (completed) throw new Error('Unexpected event after completion.');
        const event = parseEvent(data);
        if (event.type === 'done') completed = event;
        onEvent(event);
      }
      if (done) break;
    }
    if (!completed || buffer.trim()) throw new Error('Generation was interrupted before completion. Please retry.');
    return completed;
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}
