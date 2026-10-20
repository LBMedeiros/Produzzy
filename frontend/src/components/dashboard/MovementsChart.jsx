const WIDTH = 360
const HEIGHT = 190
const PADDING = { bottom: 26, left: 26, right: 6, top: 10 }
const BAR_WIDTH = 11
const BAR_GAP = 3

const weekdayFormatter = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'UTC',
  weekday: 'short',
})

// "2026-10-20" → "Seg" (the API already sends local calendar days).
function formatWeekday(isoDate) {
  const label = weekdayFormatter.format(new Date(`${isoDate}T12:00:00Z`))

  return label.replace('.', '').replace(/^./, (letter) => letter.toUpperCase())
}

// Round the axis up to a multiple of 4 so the four gridlines are integers.
function getAxisMax(days) {
  const highest = Math.max(0, ...days.flatMap((day) => [day.entries, day.exits]))

  return Math.max(4, Math.ceil(highest / 4) * 4)
}

// Entries × exits per day over the last 7 days, drawn to scale.
function MovementsChart({ days }) {
  const plotWidth = WIDTH - PADDING.left - PADDING.right
  const plotHeight = HEIGHT - PADDING.top - PADDING.bottom
  const max = getAxisMax(days)
  const ticks = [0, max / 4, max / 2, (max * 3) / 4, max]
  const y = (value) => PADDING.top + plotHeight - (value / max) * plotHeight
  const slot = plotWidth / Math.max(days.length, 1)
  const totals = days.reduce(
    (sum, day) => ({ entries: sum.entries + day.entries, exits: sum.exits + day.exits }),
    { entries: 0, exits: 0 },
  )

  return (
    <svg
      aria-label={`Últimos 7 dias: ${totals.entries} entradas e ${totals.exits} saídas.`}
      className="movements-chart"
      role="img"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
    >
      {ticks.map((tick) => (
        <g key={tick}>
          <line
            className="movements-chart__grid"
            x1={PADDING.left}
            x2={WIDTH - PADDING.right}
            y1={y(tick)}
            y2={y(tick)}
          />
          <text
            className="movements-chart__tick"
            textAnchor="end"
            x={PADDING.left - 6}
            y={y(tick) + 4}
          >
            {tick}
          </text>
        </g>
      ))}

      {days.map((day, index) => {
        const center = PADDING.left + slot * index + slot / 2
        const isToday = index === days.length - 1

        return (
          <g key={day.date}>
            <title>
              {`${isToday ? 'Hoje' : formatWeekday(day.date)}: ${day.entries} entradas, ${day.exits} saídas`}
            </title>
            <rect
              className="movements-chart__bar movements-chart__bar--in"
              height={y(0) - y(day.entries)}
              rx="3"
              width={BAR_WIDTH}
              x={center - BAR_WIDTH - BAR_GAP / 2}
              y={y(day.entries)}
            />
            <rect
              className="movements-chart__bar movements-chart__bar--out"
              height={y(0) - y(day.exits)}
              rx="3"
              width={BAR_WIDTH}
              x={center + BAR_GAP / 2}
              y={y(day.exits)}
            />
            <text
              className={`movements-chart__day${isToday ? ' is-today' : ''}`}
              textAnchor="middle"
              x={center}
              y={HEIGHT - 8}
            >
              {isToday ? 'Hoje' : formatWeekday(day.date)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

export default MovementsChart
