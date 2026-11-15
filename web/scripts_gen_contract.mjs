// Generates src/contract.gen.ts from contract/mining_case.schema.json (the Pydantic schema is the source of truth).
import { readFileSync, writeFileSync } from "node:fs";
import { compile } from "json-schema-to-typescript";

const schema = JSON.parse(readFileSync(new URL("../contract/mining_case.schema.json", import.meta.url), "utf-8"));
const ts = await compile(schema, "MiningCase", {
  bannerComment: "/* Generated from contract/mining_case.schema.json by `npm run contract`. Do not edit. */",
  additionalProperties: false,
  unreachableDefinitions: true,
  style: { printWidth: 120 },
});
const out = process.argv[2] ?? new URL("./src/contract.gen.ts", import.meta.url);
writeFileSync(out, ts);
console.log("written", String(out));
