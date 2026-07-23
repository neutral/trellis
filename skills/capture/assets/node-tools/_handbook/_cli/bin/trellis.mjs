#!/usr/bin/env node
// trellis-action-cli-format: 4

import { main } from "../src/cli.mjs";

main(process.argv.slice(2))
  .then((exitCode) => {
    process.exitCode = exitCode;
  })
  .catch((error) => {
    console.error(`error: ${error.message}`);
    process.exitCode = 2;
  });
