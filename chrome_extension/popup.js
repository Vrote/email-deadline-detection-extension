document.addEventListener("DOMContentLoaded", () => {
  const fetchBtn = document.getElementById("fetchBtn");
  const resultsDiv = document.getElementById("results");
  const filterToday = document.getElementById("filterToday");
  const filterUpcoming = document.getElementById("filterUpcoming");

  let allEmails = []; // Store fetched emails for filtering

  // ---- Safe Date Parser ----
  const parseDateSafe = (dateStr) => {
    if (!dateStr) return null;
    try {
      // If date doesn’t contain a year, append current year
      if (!/\d{4}/.test(dateStr)) {
        dateStr = `${dateStr} ${new Date().getFullYear()}`;
      }
      const parsed = new Date(dateStr);
      return isNaN(parsed) ? null : parsed;
    } catch {
      return null;
    }
  };

  // ---- Render emails ----
  const renderEmails = (emails) => {
    resultsDiv.innerHTML = "";
    if (!emails || emails.length === 0) {
      resultsDiv.innerHTML = "<p class='placeholder'>✨ No deadlines detected.</p>";
      return;
    }

    emails.forEach(email => {
      const div = document.createElement("div");
      div.className = "email";

      div.innerHTML = `
        <p><b>Subject:</b> ${email.subject || "(No subject)"}</p>
        <p><b>From:</b> ${email.from || "Unknown"}</p>
        <p><b>Date:</b> ${email.date || "Unknown"}</p>
        <p class="prediction ${email.prediction === 1 ? 'deadline' : 'nondeadline'}">
          ${email.prediction === 1 ? "🚨 Deadline Detected" : "✅ No Deadline"}
        </p>
        <p><b>Detected Dates:</b> ${email.dates_found.length > 0 ? email.dates_found.join(", ") : "None"}</p>
      `;
      resultsDiv.appendChild(div);
    });
  };

  // ---- Apply filters ----
  const applyFilters = () => {
    let filtered = [...allEmails];
    const today = new Date().toDateString();

    // Today filter
    if (filterToday.checked) {
      filtered = filtered.filter(e =>
        e.dates_found.some(d => {
          const dt = parseDateSafe(d);
          return dt && dt.toDateString() === today;
        })
      );
    }

    // Upcoming filter
    if (filterUpcoming.checked) {
      filtered = filtered.filter(e =>
        e.dates_found.some(d => {
          const dt = parseDateSafe(d);
          return dt && dt > new Date();
        })
      );
    }

    renderEmails(filtered);
  };

  // ---- Event listeners ----
  filterToday.addEventListener("change", applyFilters);
  filterUpcoming.addEventListener("change", applyFilters);

  // ---- Fetch emails from backend ----
  fetchBtn.addEventListener("click", async () => {
    resultsDiv.innerHTML = "<p class='placeholder'>🔍 Analyzing your emails with AI...</p>";

    try {
      const res = await fetch("http://127.0.0.1:8000/predict_from_gmail");
      const data = await res.json();

      allEmails = data.emails || [];
      applyFilters(); // Render filtered emails by default

    } catch (err) {
      console.error(err);
      resultsDiv.innerHTML = "<p class='placeholder'>⚠️ Backend connection failed.</p>";
    }
  });
});
