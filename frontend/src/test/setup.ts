import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// @testing-library/react's automatic cleanup only registers itself when it
// finds a global `afterEach` -- this project intentionally does not enable
// Vitest's `globals` mode (tests import describe/it/expect explicitly, same
// style as the rest of the codebase), so cleanup is wired up by hand here
// instead. Without this, each test's rendered DOM leaks into the next one.
afterEach(() => {
  cleanup();
});
