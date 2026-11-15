import "@testing-library/jest-dom/vitest";
// jsdom has no WebGL: report it as absent so the map's documented fallback is exercised quietly.
HTMLCanvasElement.prototype.getContext = (() => null) as unknown as HTMLCanvasElement["getContext"];
