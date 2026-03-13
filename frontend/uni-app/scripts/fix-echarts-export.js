const fs = require("fs");
const path = require("path");

const filePath = path.join(
  __dirname,
  "../src/wxcomponents/ec-canvas/echarts.js",
);

try {
  let content = fs.readFileSync(filePath, "utf8");

  // 1. Check if we already fixed it
  if (content.includes("export default echarts;")) {
    console.log("Already has export default.");
    // Check if it's cleaner. If it has the UMD garbage at start, we might still fail strict mode.
  }

  // 2. We want to inject
  // var echarts = {};
  // (function(root, factory) { ... })(this, function(root) { ... })

  // The original starts with !(function (t, e) {
  // logic logic
  // })(this, function (t) { ... })

  // We can replacing the start:
  // !(function (t, e) {

  // With:
  // var echarts = {};
  // !(function (t, e) {
  //    "object" == typeof exports && "undefined" != typeof module ? e(exports) : ...

  // Wait, if module exists, it uses exports.

  // Let's replace the whole header if matches
  // Header regex: /^!\s*\(function\s*\([a-z],\s*[a-z]\)\s*\{/

  if (content.match(/^!function/)) {
    content = "var echarts = {};\n" + content;
    // We need to make sure the UMD call uses our 'echarts' object if it falls through to global.
    // But simpler: just hijack the factory call?

    // Let's rely on the fact that existing UMD checks for exports.
    // If we are in ESM, exports might not be defined.
    // If we prepend: var exports = {}; var module = { exports: exports };
    // Then the UMD will think it's CommonJS and populate exports.
  } else if (content.match(/^var\s+e\s*=\s*function/)) {
    // Some versions differ.
  }

  // HACK: Shim CommonJS environment so UMD writes to our exports object
  const header = `var exports = {};
var module = { exports: exports };
var define = null; // Disable AMD
var window = { }; // Minimal window shim if needed
var global = window;
`;

  // We prepend this shim.
  // And at the end we say: var echarts = module.exports; export default echarts;

  // But wait, the file content we saw in logs:
  // !(function (t, e) { ... })(this, function (t) { ...

  // If we prepend the shim, `this` in the outer function will be `this` (module scope).

  // Let's write a robust wrapper.
  const newContent = `${header}
${content}
var echarts = module.exports;
export default echarts;
`;

  fs.writeFileSync(filePath, newContent, "utf8");
  console.log("Fixed echarts.js export.");
} catch (e) {
  console.error(e);
}
