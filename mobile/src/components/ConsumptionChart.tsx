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

import { useDeviceConsumption } from "../api/hooks";

type RangeOption = {
  label: string;
  days: number;
  granularity: "day" | "month";
};

const RANGE_OPTIONS: RangeOption[] = [
  { label: "7 días", days: 7, granularity: "day" },
  { label: "30 días", days: 30, granularity: "day" },
  { label: "12 meses", days: 365, granularity: "month" },
];

function formatPeriod(period: string, granularity: "day" | "month"): string {
  if (granularity === "month") {
    const [year, month] = period.split("-");
    return new Date(Number(year), Number(month) - 1, 1).toLocaleDateString(undefined, {
      month: "short",
      year: "2-digit",
    });
  }
  const [year, month, day] = period.split("-");
  return new Date(Number(year), Number(month) - 1, Number(day)).toLocaleDateString(undefined, {
    day: "2-digit",
    month: "short",
  });
}

export function ConsumptionChart({ deviceId }: { deviceId: number | undefined }) {
  const [rangeIndex, setRangeIndex] = useState(0);
  const range = RANGE_OPTIONS[rangeIndex];
  const { data, isLoading } = useDeviceConsumption(deviceId, range.days, range.granularity);

  const points = data?.points ?? [];
  const chartData = points.map((point) => ({
    period: formatPeriod(point.period, range.granularity),
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

      {isLoading ? (
        <p>Cargando consumo...</p>
      ) : chartData.length === 0 ? (
        <p>
          Todavía no hay suficiente historial para graficar este rango — el consumo por{" "}
          {range.granularity === "day" ? "día" : "mes"} requiere al menos dos períodos completos de
          lecturas.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <defs>
              <linearGradient id="consumptionFillMobile" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--brand)" stopOpacity={0.35} />
                <stop offset="95%" stopColor="var(--brand)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} vertical={false} />
            <XAxis dataKey="period" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={44}
              unit=" kWh"
            />
            <Tooltip
              formatter={(value: number) => [`${value.toFixed(3)} kWh`, "Consumo"]}
              contentStyle={{ borderRadius: 8, fontSize: 13 }}
            />
            <Area
              type="monotone"
              dataKey="kwh"
              stroke="var(--brand)"
              strokeWidth={2}
              fill="url(#consumptionFillMobile)"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}
