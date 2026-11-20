export function enhanceSharing(groups, clipboard) {
  for (const group of groups) {
    const button = group.querySelector("[data-copy]");
    const input = group.querySelector("input");
    const status = group.querySelector("[data-copy-status]");
    button.hidden = false;
    button.addEventListener("click", async () => {
      try {
        await clipboard.writeText(input.value);
        status.textContent = "Lien copié.";
      } catch {
        input.focus();
        input.select();
        status.textContent = "Le lien est sélectionné. Tu peux le copier manuellement.";
      }
    });
  }
}

export function enhanceBallots(ballots) {
  for (const ballot of ballots) {
    const none = ballot.querySelector('[name="none_applies"]');
    const choices = ballot.querySelectorAll('[name="situations"]');
    none.addEventListener("change", () => {
      if (none.checked) {
        for (const choice of choices) {
          choice.checked = false;
        }
      }
    });
    for (const choice of choices) {
      choice.addEventListener("change", () => {
        if (choice.checked) {
          none.checked = false;
        }
      });
    }
  }
}

enhanceBallots(document.querySelectorAll("[data-ballot]"));
enhanceSharing(document.querySelectorAll("[data-copy-group]"), navigator.clipboard);
