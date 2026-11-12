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

test("parses action_call and action_result event envelopes with full action telemetry", () => {
  const raw = [
    `event: action_call\ndata: {"actionId":"call_1","tool":"read_workspace_file","args":{"path":"README.md"},"tier":1}`,
    `event: action_result\ndata: {"actionId":"call_1","tool":"read_workspace_file","output":"1: # GPTCraft"}`,
  ].join("\n\n") + "\n\n";

  const parsed = parseSseBuffer("", raw);
  assert.equal(parsed.events.length, 2);
  assert.deepEqual(parsed.events[0], {
    type: "action_call",
    actionId: "call_1",
    tool: "read_workspace_file",
    args: { path: "README.md" },
    tier: 1,
  });
  assert.deepEqual(parsed.events[1], {
    type: "action_result",
    actionId: "call_1",
    tool: "read_workspace_file",
    output: "1: # GPTCraft",
  });
});

test("parses full cyclical agent action call and action result telemetry cycle", () => {
  const stream = [
    `event: thought\ndata: {"thought":"Inspecting workspace"}`,
    `event: action_call\ndata: {"actionId":"act_42","tool":"search_workspace_symbols","args":{"query":"ChatService"},"tier":1}`,
    `event: action_result\ndata: {"actionId":"act_42","tool":"search_workspace_symbols","output":"backend/app/services/chat.py:14: class ChatService"}`,
    `event: token\ndata: {"token":"Found ChatService in chat.py"}`,
    `event: done\ndata: {"status":"completed","totalSteps":2,"conversationId":"101","modeUsed":"agent"}`,
  ].join("\n\n") + "\n\n";

  const { events } = parseSseBuffer("", stream, true);
  assert.equal(events.length, 5);
  assert.equal(events[0].type, "thought");
  assert.equal(events[1].type, "action_call");
  assert.equal(events[2].type, "action_result");
  assert.equal(events[3].type, "token");
  assert.equal(events[4].type, "done");

  if (events[1].type === "action_call") {
    assert.equal(events[1].tool, "search_workspace_symbols");
    assert.equal(events[1].tier, 1);
  }
  if (events[2].type === "action_result") {
    assert.equal(events[2].actionId, "act_42");
    assert.ok(events[2].output.includes("ChatService"));
  }
  if (events[4].type === "done") {
    assert.equal(events[4].totalSteps, 2);
  }
});

test("parses approval_required event envelope with diff, actionId, and rationale", () => {
  const raw = [
    `event: approval_required\ndata: {"actionId":"act_99","tool":"edit_workspace_file","tier":2,"parameters":{"path":"docs/notes.txt","content":"New content"},"rationale":"Updating documentation","diff":"--- a/docs/notes.txt\\n+++ b/docs/notes.txt\\n@@ -1 +1 @@\\n-Old\\n+New content"}`,
    `event: done\ndata: {"status":"interrupted","totalSteps":1,"conversationId":"202"}`,
  ].join("\n\n") + "\n\n";

  const { events } = parseSseBuffer("", raw, true);
  assert.equal(events.length, 2);
  assert.equal(events[0].type, "approval_required");
  if (events[0].type === "approval_required") {
    assert.equal(events[0].actionId, "act_99");
    assert.equal(events[0].tool, "edit_workspace_file");
    assert.equal(events[0].tier, 2);
    assert.equal(events[0].parameters.path, "docs/notes.txt");
    assert.equal(events[0].rationale, "Updating documentation");
    assert.ok(events[0].diff?.includes("+New content"));
  }
  assert.equal(events[1].type, "done");
  if (events[1].type === "done") {
    assert.equal(events[1].status, "interrupted");
    assert.equal(events[1].conversationId, "202");
  }
});
