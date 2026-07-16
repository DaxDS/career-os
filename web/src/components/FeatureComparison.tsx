import "../styles/comparison.css";

const ROWS = [
  { feature: "Express Entry / NOC scoring", careerOs: true, jobscan: false, teal: false, lazyApply: false },
  { feature: "Tailored resume per job", careerOs: true, jobscan: true, teal: true, lazyApply: false },
  { feature: "Cover letter generation", careerOs: true, jobscan: false, teal: true, lazyApply: false },
  { feature: "Human review before submit", careerOs: true, jobscan: true, teal: true, lazyApply: false },
  { feature: "Quality autonomous apply", careerOs: true, jobscan: false, teal: false, lazyApply: false },
  { feature: "Volume auto-apply spam", careerOs: false, jobscan: false, teal: false, lazyApply: true },
] as const;

function Cell({ value }: { value: boolean }) {
  return <td className={value ? "compare-yes" : "compare-no"}>{value ? "✓" : "—"}</td>;
}

export function FeatureComparison() {
  return (
    <section className="comparison-section">
      <h2>How Career OS compares</h2>
      <div className="comparison-scroll">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Feature</th>
              <th>Career OS</th>
              <th>Jobscan</th>
              <th>Teal</th>
              <th>LazyApply</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.feature}>
                <td>{row.feature}</td>
                <Cell value={row.careerOs} />
                <Cell value={row.jobscan} />
                <Cell value={row.teal} />
                <Cell value={row.lazyApply} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
