import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useDeviceConsumption, type ConsumptionRangeParams } from "../api/hooks";

type Granularity = "minute" | "hour" | "day" | "month";

type RangeOption = {
  label: string;
  days?: number;
  granularity: Granularity;
  custom?: boolean;
};

const RANGE_OPTIONS: RangeOption[] = [
  { label: "Hoy", granularity: "hour" },
  { label: "Hoy (min)", granularity: "minute" },
  { label: "7 días", days: 7, granularity: "day" },
  { label: "30 días", days: 30, granularity: "day" },
  { label: "12 meses", days: 365, granularity: "month" },
  { label: "Personalizado", granularity: "day", custom: true },
];

function formatPeriod(period: string, granularity: Granularity): string {
  if (granularity === "month") {
    const [year, month] = period.split("-");
    return new Date(Number(year), Number(month) - 1, 1).toLocaleDateString(undefined, {
      month: "short",
      year: "2-digit",
    });
  }
  if (granularity === "hour" || granularity === "minute") {
    // El backend agrupa por hora/minuto UTC ("YYYY-MM-DDTHH[:MM]") —
    // convertir a hora local antes de mostrarla, si no la gráfica queda
    // desfasada varias horas contra el reloj real del usuario.
    const [datePart, timePart] = period.split("T");
    const [year, month, day] = datePart.split("-").map(Number);
    const [hour, minute] = timePart.split(":").map(Number);
    const localDate = new Date(Date.UTC(year, month - 1, day, hour, minute || 0));
    return localDate.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  }
  const [year, month, day] = period.split("-");
  return new Date(Number(year), Number(month) - 1, Number(day)).toLocaleDateString(undefined, {
    day: "2-digit",
    month: "short",
  });
}

const todayStr = new Date().toISOString().slice(0, 10);

export function ConsumptionChart({ deviceId }: { deviceId: number | undefined }) {
  const [rangeIndex, setRangeIndex] = useState(0);
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");

  const selected = RANGE_OPTIONS[rangeIndex];
  const customReady = selected.custom === true && customStart !== "" && customEnd !== "";

  // En modo personalizado, mientras falte elegir una de las dos fechas se
  // manda una ventana vacía (days=0) en vez de disparar de una el request
  // con el rango por defecto — evita graficar algo que el usuario todavía
  // no terminó de elegir.
  const queryParams: ConsumptionRangeParams = selected.custom
    ? customReady
      ? { granularity: "day", start: customStart, end: customEnd }
      : { granularity: "day", days: 0 }
    : { granularity: selected.granularity, days: selected.days };

  const { data, isLoading } = useDeviceConsumption(deviceId, queryParams);
  const earliestDate = data?.earliest_date ?? undefined;

  const points = data?.points ?? [];
  const chartData = points.map((point) => ({
    period: formatPeriod(point.period, queryParams.granularity),
    kwh: point.kwh,
  }));

  return (
    <section className="card">
      <div className="chart-header">
        <h2>Consumo</h2>
        <div className="chart-range-toggle">
          {RANGE_OPTIONS.map((option, index) => (
            <button
              key={option.label}
              className={index === rangeIndex ? "chart-range-btn active" : "chart-range-btn"}
              onClick={() => setRangeIndex(index)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {selected.custom && (
        <div className="chart-custom-range">
          <label>
            Desde
            <input
              type="date"
              value={customStart}
              min={earliestDate}
              max={customEnd || todayStr}
              onChange={(event) => setCustomStart(event.target.value)}
            />
          </label>
          <label>
            Hasta
            <input
              type="date"
              value={customEnd}
              min={customStart || earliestDate}
              max={todayStr}
              onChange={(event) => setCustomEnd(event.target.value)}
            />
          </label>
        </div>
      )}

      {selected.custom && !customReady ? (
        <p>Elegí una fecha de inicio y una de fin para ver el consumo de ese período.</p>
      ) : isLoading ? (
        <p>Cargando consumo...</p>
      ) : chartData.length === 0 ? (
        <p>
          {selected.granularity === "hour" || selected.granularity === "minute"
            ? "Todavía no hay lecturas registradas hoy."
            : "Sin lecturas registradas en este período."}
        </p>
      ) : (
        <>
          {chartData.length === 1 && (
            <p className="chart-hint">
              Un solo punto todavía — a medida que lleguen más lecturas se va a poder ver el
              trazado completo.
            </p>
          )}
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="consumptionFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--brand, #6d28d9)" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="var(--brand, #6d28d9)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} vertical={false} />
              <XAxis
                dataKey="period"
                tick={{ fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
                minTickGap={24}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                width={52}
                unit=" kWh"
                domain={chartData.length === 1 ? [0, (max: number) => Math.max(max, 0.01)] : undefined}
              />
              <Tooltip
                formatter={(value) => [
                  `${Number(Array.isArray(value) ? value[0] : (value ?? 0)).toFixed(4)} kWh`,
                  "Consumo",
                ]}
                contentStyle={{ borderRadius: 8, fontSize: 13 }}
              />
              <Area
                type="monotone"
                dataKey="kwh"
                stroke="var(--brand, #6d28d9)"
                strokeWidth={2}
                fill="url(#consumptionFill)"
                dot={{ r: 4, strokeWidth: 2, fill: "#fff" }}
                activeDot={{ r: 6 }}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </>
      )}
    </section>
  );
}
