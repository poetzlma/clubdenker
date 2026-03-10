import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const data = [
  { month: "Jan", mitglieder: 210 },
  { month: "Feb", mitglieder: 215 },
  { month: "Mär", mitglieder: 220 },
  { month: "Apr", mitglieder: 225 },
  { month: "Mai", mitglieder: 230 },
  { month: "Jun", mitglieder: 228 },
  { month: "Jul", mitglieder: 232 },
  { month: "Aug", mitglieder: 235 },
  { month: "Sep", mitglieder: 238 },
  { month: "Okt", mitglieder: 240 },
  { month: "Nov", mitglieder: 245 },
  { month: "Dez", mitglieder: 248 },
]

export function MemberTrendChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Mitgliederentwicklung</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="mitglieder"
              stroke="oklch(0.646 0.222 41.116)"
              strokeWidth={2}
              dot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
