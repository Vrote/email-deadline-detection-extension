document.addEventListener("DOMContentLoaded", () => {
  const fetchBtn = document.getElementById("fetchBtn");
  const resultsDiv = document.getElementById("results");

  fetchBtn.addEventListener("click", async () => {
    resultsDiv.innerHTML = "<p class='placeholder'>⏳ Fetching emails...</p>";

    try {
      const res = await fetch("http://127.0.0.1:8000/predict_from_gmail");
      const data = await res.json();

      if (!data.emails || data.emails.length === 0) {
        resultsDiv.innerHTML = "<p class='placeholder'>No deadlines found.</p>";
        return;
      }

      resultsDiv.innerHTML = "";
      data.emails.forEach(email => {
        const div = document.createElement("div");
        div.className = "email";
        div.innerHTML = `
          <p><b>Subject:</b> ${email.subject || "(No subject)"}</p>
          <p><b>From:</b> ${email.from || "Unknown"}</p>
          <p><b>Date:</b> ${email.date || "Unknown"}</p>
          <p class="prediction ${email.prediction === 1 ? 'deadline' : 'nondeadline'}">
            ${email.prediction === 1 ? "📌 Deadline" : "✔ No deadline"}
          </p>
          <p><b>Deadlines Found:</b> ${email.dates_found.length > 0 ? email.dates_found.join(", ") : "None"}</p>
        `;
        resultsDiv.appendChild(div);
      });

    } catch (err) {
      console.error(err);
      resultsDiv.innerHTML = "<p class='placeholder'>⚠️ Failed to connect to backend.</p>";
    }
  });
});
