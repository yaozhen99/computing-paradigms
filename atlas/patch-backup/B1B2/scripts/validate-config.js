const fs = require("fs");
const path = process.argv[2];
try {
  const c = JSON.parse(fs.readFileSync(path, "utf8"));
  if (!c.models || !c.agents || !c.gateway) process.exit(1);
  if (!c.gateway.auth) process.exit(1);
  process.exit(0);
} catch (e) {
  process.exit(1);
}
