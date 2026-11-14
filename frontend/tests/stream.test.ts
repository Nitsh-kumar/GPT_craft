import test from 'node:test';
import assert from 'node:assert/strict';
import { readAgentStream, readChatStream } from '../src/services/stream.ts';
import type { SseEventEnvelope } from '../src/types/index.ts';

const done = 'data: {"type":"done","conversation_id":1,"model_used":"openai/gpt-oss-20b","mode_used":"standard","tokens_used":42,"tokens_remaining":4958,"usage_estimated":false}\r\n\r\n';
function stream(text: string) {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream<Uint8Array>({ start(controller) {
    for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
    controller.close();
  }});
}

test('fragmented Unicode and CRLF frames require a terminal completion', async () => {
  const chunks: string[] = [];
  const result = await readChatStream(stream('data: {"type":"chunk","content":"नमस्ते"}\r\n\r\n' + done), event => {
    if (event.type === 'chunk') chunks.push(event.content);
  });
  assert.deepEqual(chunks, ['नमस्ते']);
  assert.equal(result.tokens_remaining, 4958);
});

test('premature EOF is a failed generation', async () => {
  await assert.rejects(readChatStream(stream('data: {"type":"chunk","content":"partial"}\n\n'), () => {}), /interrupted/);
});

test('provider error and malformed completion cannot become success', async () => {
  await assert.rejects(readChatStream(stream('data: {"type":"error","error":"Provider unavailable"}\n\n'), () => {}), /Provider unavailable/);
  await assert.rejects(readChatStream(stream('data: {"type":"done"}\n\n'), () => {}), /Unsupported/);
  await assert.rejects(readChatStream(stream(done + done), () => {}), /after completion/);
});

test('readAgentStream parses typed envelopes, enforces terminal done, and releases reader', async () => {
  const events: SseEventEnvelope[] = [];
  const chunks: string[] = [];
  const agentSse = [
    'event: thought\ndata: {"thought":"Resuming edit"}\n\n',
    'event: action_result\ndata: {"actionId":"act_2","tool":"edit_workspace_file","output":"Updated"}\n\n',
    'event: token\ndata: {"token":"Done editing."}\n\n',
    'event: done\ndata: {"status":"completed","conversationId":"42","modelUsed":"openai/gpt-oss-120b","modeUsed":"agent"}\n\n',
  ].join('');

  const result = await readAgentStream(stream(agentSse), {
    onChunk: (c) => chunks.push(c),
    onEvent: (e) => events.push(e),
  });

  assert.deepEqual(chunks, ['Done editing.']);
  assert.equal(events.length, 4);
  assert.deepEqual(result, {
    conversationId: '42',
    modelUsed: 'openai/gpt-oss-120b',
    modeUsed: 'agent',
  });
});

test('readAgentStream rejects premature EOF without done and cleans up reader in finally', async () => {
  const baseStream = stream('event: token\ndata: {"token":"Partial"}\n\n');
  let cancelCalls = 0;
  let releaseCalls = 0;
  const wrappedStream = {
    getReader() {
      const realReader = baseStream.getReader();
      return {
        read: () => realReader.read(),
        cancel: async () => {
          cancelCalls += 1;
          return realReader.cancel();
        },
        releaseLock: () => {
          releaseCalls += 1;
          return realReader.releaseLock();
        },
      };
    },
  } as unknown as ReadableStream<Uint8Array>;

  await assert.rejects(readAgentStream(wrappedStream), /interrupted/);
  assert.equal(cancelCalls, 1);
  assert.equal(releaseCalls, 1);
});

test('readAgentStream rejects error envelope and cleans up reader in finally', async () => {
  const baseStream = stream('event: error\ndata: {"error":"Approval execution failed"}\n\n');
  let cancelCalls = 0;
  let releaseCalls = 0;
  const wrappedStream = {
    getReader() {
      const realReader = baseStream.getReader();
      return {
        read: () => realReader.read(),
        cancel: async () => {
          cancelCalls += 1;
          return realReader.cancel();
        },
        releaseLock: () => {
          releaseCalls += 1;
          return realReader.releaseLock();
        },
      };
    },
  } as unknown as ReadableStream<Uint8Array>;

  await assert.rejects(readAgentStream(wrappedStream), /Approval execution failed/);
  assert.equal(cancelCalls, 1);
  assert.equal(releaseCalls, 1);
});
