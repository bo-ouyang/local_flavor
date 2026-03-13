const fs = require("fs");
const path = require("path");

const filePath = path.join(
  __dirname,
  "../src/wxcomponents/ec-canvas/echarts.js",
);

try {
  if (!fs.existsSync(filePath)) {
    console.error("File not found:", filePath);
    process.exit(1);
  }

  let content = fs.readFileSync(filePath, "utf8");
  let lines = content.split("\n");
  let newLines = [];

  for (let line of lines) {
    if (line.startsWith("+")) {
      newLines.push(line.substring(1));
    } else {
      newLines.push(line);
    }
  }

  let newContent = newLines.join("\n");

  // Remove BOM if present
  if (newContent.charCodeAt(0) === 0xfeff) {
    newContent = newContent.slice(1);
  }

  // Ensure export
  if (
    !newContent.includes("export default echarts") &&
    !newContent.includes("module.exports")
  ) {
    newContent += "\nexport default echarts;\n";
  }

  fs.writeFileSync(filePath, newContent, "utf8");
  console.log("Successfully cleaned echarts.js");
} catch (error) {
  console.error("Error cleaning file:", error);
}
