import assert from "node:assert/strict";
import { test } from "node:test";
const queries = [];
globalThis.document = { querySelectorAll(selector) { queries.push(selector); return []; } };
const { enhanceBallots, enhanceSharing } = await import("../static/js/bokebi.mjs");
delete globalThis.document;

function control(properties = {}) {
  const callbacks = new Map();
  return {
    ...properties,
    addEventListener(event, callback) {
      callbacks.set(event, callback);
    },
    emit(event) {
      return callbacks.get(event)();
    },
  };
}

function copyGroup() {
  const button = control({ hidden: true });
  const input = {
    value: "https://bokebi.example/s/opaque/",
    focus() { this.focused = true; },
    select() { this.selected = true; },
  };
  const status = {};
  const children = { "[data-copy]": button, input, "[data-copy-status]": status };
  return { button, input, status, querySelector: (selector) => children[selector] };
}

test("clipboard controls copy the visible link and announce success", async () => {
  const group = copyGroup();
  const copied = [];
  enhanceSharing([group], { writeText: async (text) => copied.push(text) });
  assert.equal(group.button.hidden, false);
  await group.button.emit("click");
  assert.deepEqual(copied, [group.input.value]);
  assert.equal(group.status.textContent, "Lien copié.");
});

test("clipboard failure or absence selects the link for manual copy", async () => {
  const denied = { writeText: async () => { throw new Error("Denied"); } };
  for (const clipboard of [denied, undefined]) {
    const group = copyGroup();
    enhanceSharing([group], clipboard);
    await group.button.emit("click");
    assert.equal(group.input.focused, true);
    assert.equal(group.input.selected, true);
    assert.match(group.status.textContent, /copier manuellement/);
  }
});

test("the none option and situations are exclusive in both directions", () => {
  const none = control({ checked: false });
  const first = control({ checked: true });
  const second = control({ checked: true });
  enhanceBallots([{ querySelector: () => none, querySelectorAll: () => [first, second] }]);

  none.emit("change");
  assert.equal(first.checked, true);
  none.checked = true;
  none.emit("change");
  assert.equal(first.checked, false);
  assert.equal(second.checked, false);
  second.emit("change");
  assert.equal(none.checked, true);
  second.checked = true;
  second.emit("change");
  assert.equal(none.checked, false);
});

test("the entry module initializes only the two public enhancements", () => {
  assert.deepEqual(queries, ["[data-ballot]", "[data-copy-group]"]);
});
