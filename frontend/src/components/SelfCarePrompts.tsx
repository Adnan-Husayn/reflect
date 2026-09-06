import type { SelfCarePrompt } from "../types/emotion";

/**
 * Prompts come from a fixed server-side library, chosen by rule.
 *
 * Nothing here is generated, and the component composes no text of its own —
 * it renders exactly what was written and reviewed.
 */
export function SelfCarePrompts({ prompts }: { prompts: SelfCarePrompt[] }) {
  if (prompts.length === 0) return null;

  return (
    <section className="self-care" aria-labelledby="self-care-heading">
      <h3 id="self-care-heading">Worth a thought</h3>
      <ul>
        {prompts.map((prompt) => (
          <li key={prompt.key}>
            <p className="self-care-observation">{prompt.observation}</p>
            <p className="self-care-suggestion">{prompt.suggestion}</p>
          </li>
        ))}
      </ul>
      <p className="self-care-note">
        These are fixed suggestions attached to what was observed. They are not advice about your
        health, and nothing here is written in response to your particular answers.
      </p>
    </section>
  );
}
