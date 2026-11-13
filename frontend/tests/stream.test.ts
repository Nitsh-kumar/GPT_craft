import test from 'node:test';
import assert from 'node:assert/strict';
import { readChatStream } from '../src/services/stream.ts';

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
