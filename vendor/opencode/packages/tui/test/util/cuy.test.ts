import { expect, test } from "bun:test"
import { monthlyLimit, recovery, workspaceName, starters } from "../../src/util/cuy"

test("workspace display strips credentials, path, query and fragment", () => {
  expect(workspaceName("https://user:secret@workspace.example/serving-endpoints?token=secret#secret")).toBe("workspace.example")
  expect(workspaceName(undefined)).toContain("Sin workspace")
  expect(workspaceName("secret")).not.toContain("secret")
})

test("budget distinguishes disabled, invalid and configured limits", () => {
  expect(monthlyLimit("0")).toBe("Sin límite mensual")
  expect(monthlyLimit("NaN")).toBe("Límite no disponible")
  expect(monthlyLimit("12.5")).toContain("12.50")
})

test("Databricks errors give actionable recovery without repeating payloads", () => {
  const error = recovery('Type validation failed: Value {"content": [{"secret": "sensitive"}]}')
  expect(error?.message).toContain("/models")
  expect(error?.message).not.toContain("sensitive")
  expect(recovery("HTTP 401 secret")?.message).toContain("--renovar-token")
  expect(recovery("HTTP 403")?.title).toBe("Acceso denegado")
  expect(recovery("HTTP 429")?.message).toContain("Esperá")
  expect(recovery("Unknown failure")).toBeUndefined()
})

test("understand and review templates select the read-only agent", () => {
  expect(starters.filter((item) => item.value !== "cambiar").every((item) => item.agent === "plan")).toBe(true)
  expect(starters.find((item) => item.value === "cambiar")?.description).toContain("permisos")
})
