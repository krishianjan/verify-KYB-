// Monochrome status mapping — meaning is carried by tonal intensity, not hue.
// Heavier (solid ink) = worse / higher severity; lighter = better / calmer.

type Tone = "solid" | "mid" | "outline" | "muted";

export function decisionMeta(action: string): { label: string; tone: Tone } {
  switch (action) {
    case "auto_approve":
    case "approve":
      return { label: "Auto-approve", tone: "outline" };
    case "manual_review":
    case "review":
      return { label: "Manual review", tone: "mid" };
    case "provisional_review":
      return { label: "Provisional review", tone: "mid" };
    case "reject":
      return { label: "Reject", tone: "solid" };
    default:
      return { label: action, tone: "muted" };
  }
}

export function severityTone(sev: string): Tone {
  switch (sev) {
    case "high":
      return "solid";
    case "medium":
      return "mid";
    case "low":
      return "outline";
    default:
      return "muted";
  }
}

export function matchTone(cat: string | null | undefined): Tone {
  switch (cat) {
    case "EXACT":
    case "SIMILAR":
      return "solid";
    case "PARTIAL":
      return "mid";
    case "NONE":
      return "outline";
    default:
      return "muted";
  }
}

// Score grade (0..100, higher = better) -> tonal weight.
export function gradeTone(rating: string): Tone {
  if (rating === "PENDING") return "muted";
  if (rating === "A" || rating === "B") return "solid";
  if (rating === "C" || rating === "D") return "mid";
  return "outline"; // F
}

export function ratingWord(rating: string | null | undefined): string {
  switch (rating) {
    case "low":
      return "Low risk";
    case "medium":
      return "Medium risk";
    case "high":
      return "High risk";
    default:
      return "—";
  }
}
