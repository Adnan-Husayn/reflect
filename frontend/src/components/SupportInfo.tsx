/**
 * Support details, shown at all times and at every score.
 *
 * Deliberately not triggered by a threshold. If these appeared only above some
 * score, their appearance would itself tell the participant they had scored
 * badly — the app would be delivering a verdict through layout while claiming
 * not to interpret. Always present, they say nothing about any response.
 */
export function SupportInfo() {
  return (
    <aside className="support-info" aria-label="Mental health support">
      <h3>If you want to talk to someone</h3>
      <p>
        These lines are free, confidential and open to anyone — not only in a crisis, and whatever
        this questionnaire says.
      </p>
      <dl>
        <div>
          <dt>Tele-MANAS</dt>
          <dd>
            <a href="tel:14416">14416</a> or <a href="tel:18008914416">1800 891 4416</a>
            <span>India&rsquo;s national mental health helpline. 24/7, free, 20 languages.</span>
          </dd>
        </div>
        <div>
          <dt>KIRAN</dt>
          <dd>
            <a href="tel:18005990019">1800 599 0019</a>
            <span>Now routes into Tele-MANAS, which answers the same call.</span>
          </dd>
        </div>
      </dl>
      <p className="support-note">
        Reflect is a student project. It is not a diagnosis, not a clinical assessment, and not a
        substitute for talking to a professional.
      </p>
    </aside>
  );
}
