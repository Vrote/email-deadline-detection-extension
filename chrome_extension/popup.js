document.addEventListener("DOMContentLoaded", () => {
  const fetchBtn = document.getElementById("fetchBtn");
  const resultsDiv = document.getElementById("results");

  let allEmails = [];

  // ---- Robust Date Parser ----
  const parseDateSafe = (dateStr) => {
    if (!dateStr) return null;
    dateStr = dateStr.trim().toLowerCase();
    const now = new Date();

    // Handle "today" / "tomorrow"
    if (dateStr.includes("today")) return now;
    if (dateStr.includes("tomorrow")) {
      const t = new Date(now);
      t.setDate(now.getDate() + 1);
      return t;
    }

    // Remove suffixes like 1st, 2nd, 3rd
    dateStr = dateStr.replace(/(\d+)(st|nd|rd|th)/g, "$1");

    // Pattern 1: dd/mm/yyyy or dd/mm/yy
    let m = dateStr.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})$/);
    if (m) {
      let [_, d, mon, y] = m;
      if (y.length === 2) y = "20" + y;
      const dt = new Date(`${y}-${mon}-${d}T00:00:00`);
      return isNaN(dt) ? null : dt;
    }

    // Pattern 2: month name + day (e.g. "nov 3")
    m = dateStr.match(/^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*(\d{1,2})$/i);
    if (m) {
      const [_, monName, d] = m;
      const y = now.getFullYear();
      const dt = new Date(`${monName} ${d}, ${y}`);
      if (dt < now.setHours(0, 0, 0, 0)) dt.setFullYear(y + 1);
      return dt;
    }

    // Pattern 3: month name + day + year (e.g. "October 30, 2025")
    const dt = new Date(dateStr);
    return isNaN(dt) ? null : dt;
  };

  // ---- Render Emails ----
  const renderEmails = (emails) => {
    resultsDiv.innerHTML = "";
    if (!emails.length) {
      resultsDiv.innerHTML = "<p class='placeholder'>✨ No deadlines detected.</p>";
      return;
    }

    emails.forEach((email) => {
      const div = document.createElement("div");
      div.className = "email";
      div.innerHTML = `
        <p><b>Subject:</b> ${email.subject || "(No subject)"}</p>
        <p><b>From:</b> ${email.from || "Unknown"}</p>
        <p><b>Date:</b> ${email.date || "Unknown"}</p>
        <p class="prediction ${email.prediction === 1 ? "deadline" : "nondeadline"}">
          ${email.prediction === 1 ? "🚨 Deadline Detected" : "✅ No Deadline"}
        </p>
        <p><b>Detected Dates:</b> ${email.dates_found.length ? email.dates_found.join(", ") : "None"}</p>
      `;
      resultsDiv.appendChild(div);
    });
  };

  // ---- Fetch Emails ----
  fetchBtn.addEventListener("click", async () => {
    resultsDiv.innerHTML = "<p class='placeholder'>🔍 Analyzing your emails with AI...</p>";
    try {
      const res = await fetch("http://127.0.0.1:8000/predict_from_gmail");
      const data = await res.json();
      allEmails = data.emails || [];
      console.log("Fetched:", allEmails);
      renderEmails(allEmails); // show all emails directly
    } catch (err) {
      console.error(err);
      resultsDiv.innerHTML = "<p class='placeholder'>⚠️ Backend connection failed.</p>";
    }
  });
});
