import { Presupuesto } from "../../../../../../plugin/presupuesto.js"
import { Auditoria } from "../../../../../../plugin/auditoria.js"
import { Secretos } from "../../../../../../plugin/secretos.js"

declare const CUY_DISTRIBUCION: boolean
declare const CUY_PRESUPUESTO_USD: number

export const bundled = typeof CUY_DISTRIBUCION !== "undefined" && CUY_DISTRIBUCION
export const budget = typeof CUY_PRESUPUESTO_USD === "undefined" ? 10 : CUY_PRESUPUESTO_USD
export const plugins = [Presupuesto, Auditoria, Secretos]
