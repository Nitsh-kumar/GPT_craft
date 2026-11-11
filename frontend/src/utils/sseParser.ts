import type { SseEventEnvelope } from '../types/index.ts';

interface RawSsePayload {
  type?: string;
  thought?: string;
  token?: string;
  content?: string;
  actionId?: string;
  tool?: string;
  args?: Record<string, unknown>;
  tier?: number;
  parameters?: Record<string, unknown>;
  rationale?: string;
  output?: string;
  status?: string;
  totalSteps?: number;
  conversationId?: string | number;
  conversation_id?: string | number;
  tokensUsed?: number;
  tokens_used?: number;
  tokensRemaining?: number;
  tokens_remaining?: number;
  modelUsed?: string;
  model_used?: string;
  modeUsed?: string;
  mode_used?: string;
  error?: string;
}

function normalizeEnvelope(eventName: string | null, data: RawSsePayload): SseEventEnvelope | null {
  const kind = eventName || data.type;
  switch (kind) {
    case 'thought':
      return typeof data.thought === 'string' ? { type: 'thought', thought: data.thought } : null;
    case 'token':
      return typeof data.token === 'string' ? { type: 'token', token: data.token } : null;
    case 'chunk':
      return typeof data.content === 'string' ? { type: 'chunk', content: data.content } : null;
    case 'action_call':
      return {
        type: 'action_call',
        actionId: String(data.actionId ?? ''),
        tool: String(data.tool ?? ''),
        args: data.args ?? {},
        tier: Number(data.tier ?? 1),
      };
    case 'approval_required':
      return {
        type: 'approval_required',
        actionId: String(data.actionId ?? ''),
        tool: String(data.tool ?? ''),
        tier: Number(data.tier ?? 2),
        parameters: data.parameters ?? {},
        rationale: String(data.rationale ?? ''),
      };
    case 'action_result':
      return {
        type: 'action_result',
        actionId: String(data.actionId ?? ''),
        tool: String(data.tool ?? ''),
        output: String(data.output ?? ''),
      };
    case 'done': {
      const rawConvId = data.conversationId ?? data.conversation_id;
      return {
        type: 'done',
        status: data.status,
        totalSteps: data.totalSteps,
        conversationId: rawConvId !== undefined && rawConvId !== null ? String(rawConvId) : undefined,
        tokensUsed: data.tokensUsed ?? data.tokens_used,
        tokensRemaining: data.tokensRemaining ?? data.tokens_remaining,
        modelUsed: data.modelUsed ?? data.model_used,
        modeUsed: data.modeUsed ?? data.mode_used,
      };
    }
    case 'error':
      return { type: 'error', error: data.error || 'Server error during generation' };
    default:
      return null;
  }
}

export function parseSseBuffer(
  existingBuffer: string,
  incomingChunk: string,
  flush = false
): { events: SseEventEnvelope[]; remaining: string } {
  const normalized = (existingBuffer + incomingChunk).replace(/\r\n/g, '\n');
  const blocks = normalized.split('\n\n');
  const remaining = flush ? '' : (blocks.pop() ?? '');
  const events: SseEventEnvelope[] = [];

  for (const rawBlock of blocks) {
    const block = rawBlock.trim();
    if (!block) continue;

    let eventName: string | null = null;
    const dataLines: string[] = [];

    for (const line of block.split('\n')) {
      if (line.startsWith(':')) continue;
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart());
      }
    }

    if (dataLines.length === 0) continue;
    try {
      const payload = JSON.parse(dataLines.join('\n')) as RawSsePayload;
      const envelope = normalizeEnvelope(eventName, payload);
      if (envelope) events.push(envelope);
    } catch {
      // Ignore malformed SSE frames to keep stream resilient
    }
  }

  return { events, remaining };
}
