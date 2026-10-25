import { test } from "node:test";
import assert from "node:assert/strict";
import { signed, ciTo, ciBracket, verdictStamp, verdictSentence, esc } from "../../web/js/common.js";

test("signed numbers print a true minus sign, a plus for zero and up, and a dash when missing", () => {
  assert.equal(signed(-0.0011), "\u22120.0011");
  assert.equal(signed(0.0049), "+0.0049");
  assert.equal(signed(null), "—");
  assert.equal(ciTo([-0.0022, -0.0001]), "\u22120.0022 to \u22120.0001");
  assert.equal(ciBracket([-0.0053, 0.0049]), "[\u22120.0053, +0.0049]");
});

test("a verdict the page does not know reads as no clear difference", () => {
  assert.equal(verdictStamp("clear win"), '<b class="v win">Clear win</b>');
  assert.equal(verdictStamp("clear loss"), '<b class="v loss">Clear loss</b>');
  assert.equal(verdictStamp("tie?"), '<b class="v even">No clear difference</b>');
  assert.equal(verdictSentence("clear win"), "A clear win for Bend");
});

test("esc neutralises markup in feed text", () => {
  assert.equal(esc('<img src="x">&'), "&lt;img src=&quot;x&quot;&gt;&amp;");
});
