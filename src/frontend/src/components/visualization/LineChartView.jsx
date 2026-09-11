import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';

const COLORS = ['#28E99F', '#3D3B4F', '#ECFFA3', '#B9B8C2', '#D94B4B'];

export default function LineChartView({ data, xKey, valueKeys = [] }) {
  if (!data || data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
        <XAxis
          dataKey={xKey}
          tick={{ fontSize: 12, fill: '#3D3B4F' }}
          axisLine={{ stroke: '#E5E7EB' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 12, fill: '#3D3B4F' }}
          axisLine={{ stroke: '#E5E7EB' }}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#F5F5F5',
            border: '1px solid #E5E7EB',
            borderRadius: '4px',
            fontSize: '13px',
          }}
        />
        {valueKeys.length > 1 && <Legend />}
        {valueKeys.map((key, idx) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={COLORS[idx % COLORS.length]}
            strokeWidth={2}
            dot={{ r: 3, fill: COLORS[idx % COLORS.length] }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
