interface ChartFrameProps {
  title: string;
  /**
   * What the number is computed from — shown on screen, next to the chart,
   * not left to the report. A reader who cannot see this has been handed a
   * number they cannot evaluate.
   */
  computedFrom: string;
  children: React.ReactNode;
}

export function ChartFrame({ title, computedFrom, children }: ChartFrameProps) {
  return (
    <figure className="chart-frame">
      <figcaption>
        <h3>{title}</h3>
        <p className="chart-computed-from">{computedFrom}</p>
      </figcaption>
      <div className="chart-body">{children}</div>
    </figure>
  );
}
