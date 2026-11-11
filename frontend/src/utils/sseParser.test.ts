import test from "node:test";
import assert from "node:assert/strict";
import { parseSseBuffer } from "./sseParser.ts";

test("parses typed agent studio event envelopes across split chunks", () => {
  const chunk1 = `event: thought\ndata: {"thought":"Inspecting `;
  const chunk2 = `repo"}\n\nevent: token\ndata: {"token":"Hello"}\n\n`;
  const chunk3 = `event: token\ndata: {"token":" world"}\n\nevent: done\ndata: {"status":"completed","totalSteps":1,"conversationId":42,"modeUsed":"agent"}\n\n`;

  const step1 = parseSseBuffer("", chunk1);
  assert.equal(step1.events.length, 0);

  const step2 = parseSseBuffer(step1.remaining, chunk2);
  assert.deepEqual(step2.events, [
    { type: "thought", thought: "Inspecting repo" },
    { type: "token", token: "Hello" },
  ]);

  const step3 = parseSseBuffer(step2.remaining, chunk3);
  assert.equal(step3.events.length, 2);
  assert.deepEqual(step3.events[0], { type: "token", token: " world" });
  assert.deepEqual(step3.events[1], {
    type: "done",
    status: "completed",
    totalSteps: 1,
    conversationId: "42",
    modeUsed: "agent",
    tokensUsed: undefined,
    tokensRemaining: undefined,
    modelUsed: undefined,
  });
});

test("preserves legacy conversational chunk, done, and error frames", () => {
  const raw = [
    `data: {"type":"chunk","content":"Hi"}`,
    `data: {"type":"done","conversation_id":99,"mode_used":"architect"}`,
    `data: {"type":"error","error":"Rate limited"}`,
  ].join("\n\n") + "\n\n";

  const parsed = parseSseBuffer("", raw);
  assert.equal(parsed.events.length, 3);
  assert.deepEqual(parsed.events[0], { type: "chunk", content: "Hi" });
  assert.equal(parsed.events[1].type, "done");
  if (parsed.events[1].type === "done") {
    assert.equal(parsed.events[1].conversationId, "99");
    assert.equal(parsed.events[1].modeUsed, "architect");
  }
  assert.deepEqual(parsed.events[2], { type: "error", error: "Rate limited" });
});

test("handles CRLF framing, flush without trailing blank line, and future action envelopes", () => {
  const raw = `event: action_call\r\ndata: {"actionId":"act_1","tool":"read_file","args":{"path":"README.md"},"tier":1}\r\n\r\nevent: error\r\ndata: {"error":"Timeout"}`;
  const parsed = parseSseBuffer("", raw, true);
  assert.equal(parsed.remaining, "");
  assert.equal(parsed.events.length, 2);
  assert.deepEqual(parsed.events[0], {
    type: "action_call",
    actionId: "act_1",
    tool: "read_file",
    args: { path: "README.md" },
    tier: 1,
  });
  assert.deepEqual(parsed.events[1], { type: "error", error: "Timeout" });
});
